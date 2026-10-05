"""Scoped, audited extraction with stable results and no canonical writes."""

import json
import time
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AuditEvent,
    EventCandidateEvidence,
    EventExtraction,
    ExtractedSegment,
    Meeting,
    MeetingParticipant,
    ProjectEventCandidate,
    RelevanceAnalysis,
    Utterance,
    UtteranceRelevance,
)
from app.domain.events import (
    EXTRACTOR_VERSION,
    MAX_WINDOW_TEXT,
    MAX_WINDOWS,
    EventWindow,
    SourceSegment,
    validate_extraction,
    validate_inputs,
)
from app.domain.manual_state import StateError
from app.repositories.audit import AuditRepository
from app.services.event_provider import EventProvider, EventProviderResult
from app.services.meetings import find_meeting
from app.services.project_access import LOCAL_DEMO_ACTOR_ID
from app.services.relevance_analysis import cache_key as relevance_key
from app.services.relevance_context import project_context
from app.services.relevance_provider import RelevanceProvider

PAGE_SIZE = 100
LEASE_SECONDS = 45


def current_relevance(
    session: Session, meeting: Meeting, fingerprint: str, provider: RelevanceProvider
) -> RelevanceAnalysis | None:
    return session.scalar(
        select(RelevanceAnalysis).where(
            RelevanceAnalysis.project_id == meeting.project_id,
            RelevanceAnalysis.meeting_id == meeting.id,
            RelevanceAnalysis.cache_key
            == relevance_key(meeting.transcript_hash or "", fingerprint, provider.model),
        )
    )


def extraction_key(relevance_id: UUID, fingerprint: str, model: str) -> str:
    return sha256(
        json.dumps([str(relevance_id), fingerprint, model, EXTRACTOR_VERSION]).encode()
    ).hexdigest()


def audit(session: Session, run: EventExtraction, action: str, payload: dict[str, Any]) -> None:
    AuditRepository(session, run.project_id).append(
        AuditEvent(
            project_id=run.project_id,
            actor_id=LOCAL_DEMO_ACTOR_ID,
            action=action,
            entity_type="event_extraction",
            entity_id=run.id,
            payload={"meetingId": str(run.meeting_id), **payload},
        )
    )


def extraction_view(
    session: Session,
    project_id: UUID,
    meeting_id: UUID,
    provider: EventProvider,
    relevance_provider: RelevanceProvider,
    *,
    page: int = 1,
    kind: str = "ALL",
) -> dict[str, Any]:
    meeting = find_meeting(session, project_id, meeting_id)
    _, fingerprint = project_context(session, project_id)
    relevance = current_relevance(session, meeting, fingerprint, relevance_provider)
    query = select(EventExtraction).where(
        EventExtraction.project_id == project_id, EventExtraction.meeting_id == meeting_id
    )
    run = (
        session.scalar(
            query.where(
                EventExtraction.cache_key
                == extraction_key(relevance.id, fingerprint, provider.model)
            )
        )
        if relevance
        else None
    )
    if run is None:
        run = session.scalar(
            query.order_by(EventExtraction.created_at.desc(), EventExtraction.id).limit(1)
        )
    selected_relevance_id = (
        run.relevance_analysis_id if run else relevance.id if relevance else None
    )
    groups: dict[str, int] = (
        {
            outcome: count
            for outcome, count in session.execute(
                select(UtteranceRelevance.outcome, func.count())
                .where(
                    UtteranceRelevance.project_id == project_id,
                    UtteranceRelevance.meeting_id == meeting_id,
                    UtteranceRelevance.analysis_id == selected_relevance_id,
                )
                .group_by(UtteranceRelevance.outcome)
            )
        }
        if selected_relevance_id
        else {}
    )
    eligible = groups.get("RELEVANT", 0)
    processed = no_event = 0
    if run:
        processed = (
            session.scalar(
                select(func.count())
                .select_from(ExtractedSegment)
                .where(
                    ExtractedSegment.project_id == project_id,
                    ExtractedSegment.extraction_id == run.id,
                )
            )
            or 0
        )
        no_event = (
            session.scalar(
                select(func.count())
                .select_from(ExtractedSegment)
                .where(
                    ExtractedSegment.project_id == project_id,
                    ExtractedSegment.extraction_id == run.id,
                    ExtractedSegment.event_count == 0,
                )
            )
            or 0
        )
    base_candidates = select(ProjectEventCandidate).where(
        ProjectEventCandidate.project_id == project_id,
        ProjectEventCandidate.meeting_id == meeting_id,
        ProjectEventCandidate.extraction_id == (run.id if run else None),
    )
    total_events = session.scalar(select(func.count()).select_from(base_candidates.subquery())) or 0
    low = (
        session.scalar(
            select(func.count()).select_from(
                base_candidates.where(ProjectEventCandidate.confidence < 0.65).subquery()
            )
        )
        or 0
    )
    filtered = (
        base_candidates.where(ProjectEventCandidate.kind == kind)
        if kind != "ALL"
        else base_candidates
    )
    filtered_count = session.scalar(select(func.count()).select_from(filtered.subquery())) or 0
    rows = session.execute(
        filtered.add_columns(Utterance, MeetingParticipant.user_id)
        .join(
            Utterance,
            (Utterance.project_id == ProjectEventCandidate.project_id)
            & (Utterance.meeting_id == ProjectEventCandidate.meeting_id)
            & (Utterance.id == ProjectEventCandidate.utterance_id),
        )
        .outerjoin(
            MeetingParticipant,
            (MeetingParticipant.project_id == Utterance.project_id)
            & (MeetingParticipant.meeting_id == Utterance.meeting_id)
            & (MeetingParticipant.id == Utterance.participant_id),
        )
        .order_by(Utterance.sequence, ProjectEventCandidate.ordinal, ProjectEventCandidate.id)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    evidence_by_candidate: dict[UUID, list[dict[str, Any]]] = {}
    if rows:
        evidence_rows = session.execute(
            select(EventCandidateEvidence, Utterance)
            .join(
                Utterance,
                (Utterance.project_id == EventCandidateEvidence.project_id)
                & (Utterance.meeting_id == EventCandidateEvidence.meeting_id)
                & (Utterance.id == EventCandidateEvidence.utterance_id),
            )
            .where(
                EventCandidateEvidence.project_id == project_id,
                EventCandidateEvidence.meeting_id == meeting_id,
                EventCandidateEvidence.candidate_id.in_([c.id for c, _, _ in rows]),
            )
            .order_by(Utterance.sequence)
        ).all()
        for evidence, source in evidence_rows:
            evidence_by_candidate.setdefault(evidence.candidate_id, []).append(
                {
                    "utteranceId": str(source.id),
                    "sequence": source.sequence,
                    "speaker": source.speaker_label,
                    "speakerId": str(source.participant_id) if source.participant_id else None,
                    "timestampMs": source.timestamp_ms,
                    "quote": evidence.quote,
                }
            )
    total_sources = (
        session.scalar(
            select(func.count())
            .select_from(Utterance)
            .where(Utterance.project_id == project_id, Utterance.meeting_id == meeting_id)
        )
        or 0
    )
    return {
        "projectId": str(project_id),
        "meetingId": str(meeting_id),
        "prerequisite": "NO_TRANSCRIPT"
        if not meeting.transcript_hash
        else "ANALYZE_RELEVANCE"
        if relevance is None
        else None,
        "currentRelevanceId": str(relevance.id) if relevance else None,
        "relevance": {
            "total": total_sources,
            "relevant": eligible,
            "ignored": groups.get("IGNORED", 0),
            "uncertain": groups.get("UNCERTAIN", 0),
            "pending": total_sources - sum(groups.values()),
        },
        "stale": bool(
            run
            and (
                relevance is None
                or run.cache_key != extraction_key(relevance.id, fingerprint, provider.model)
            )
        ),
        "counts": {
            "eligible": eligible,
            "processed": processed,
            "pending": eligible - processed,
            "candidates": total_events,
            "noEvent": no_event,
            "lowConfidence": low,
        },
        "extraction": None
        if run is None
        else {
            "id": str(run.id),
            "relevanceAnalysisId": str(run.relevance_analysis_id),
            "model": run.model,
            "extractorVersion": run.extractor_version,
            "createdAt": run.created_at.isoformat(),
            "contextComplete": run.context_snapshot.get("complete", False),
            "lastError": run.last_error,
            "apiCalls": run.api_calls,
            "inputTokens": run.input_tokens,
            "outputTokens": run.output_tokens,
            "usageReportedCalls": run.usage_reported_calls,
            "latencyMs": run.latency_ms,
            "processing": run.processing_token is not None
            and run.processing_started_at is not None
            and run.processing_started_at > datetime.now(UTC) - timedelta(seconds=LEASE_SECONDS),
        },
        "items": [
            {
                "id": str(c.id),
                "projectId": str(c.project_id),
                "meetingId": str(c.meeting_id),
                "extractionId": str(c.extraction_id),
                "primaryUtteranceId": str(u.id),
                "sequence": u.sequence,
                "speaker": u.speaker_label,
                "saidByUserId": str(said_by) if said_by else None,
                "kind": c.kind,
                "statement": c.statement,
                "status": c.status,
                "title": c.title,
                "description": c.description,
                "confidence": c.confidence,
                "ownerMention": c.owner_mention,
                "dueDateText": c.due_date_text,
                "needsReview": c.confidence < 0.65,
                "evidence": evidence_by_candidate.get(c.id, []),
            }
            for c, u, said_by in rows
        ],
        "page": page,
        "pageSize": PAGE_SIZE,
        "filteredCount": filtered_count,
    }


def extract_meeting(
    session: Session,
    project_id: UUID,
    meeting_id: UUID,
    provider: EventProvider,
    relevance_provider: RelevanceProvider,
) -> dict[str, Any]:
    token = uuid4()
    windows: list[EventWindow] = []
    with session.begin_nested():
        meeting = find_meeting(session, project_id, meeting_id, lock=True)
        if not meeting.transcript_hash:
            raise StateError(
                "EVENT_NO_TRANSCRIPT", "Upload a transcript before extracting events.", 409
            )
        context, fingerprint = project_context(session, project_id)
        relevance = current_relevance(session, meeting, fingerprint, relevance_provider)
        if relevance is None:
            raise StateError(
                "EVENT_RELEVANCE_REQUIRED",
                "Analyze relevance against the current project baseline first.",
                409,
            )
        if not 1 <= len(provider.model) <= 80:
            raise StateError("EVENT_CONFIGURATION", "Choose a bounded event model name.", 503)
        key = extraction_key(relevance.id, fingerprint, provider.model)
        run = session.scalar(
            select(EventExtraction)
            .where(
                EventExtraction.project_id == project_id,
                EventExtraction.meeting_id == meeting_id,
                EventExtraction.cache_key == key,
            )
            .with_for_update()
        )
        eligible_ids = set(
            session.scalars(
                select(UtteranceRelevance.utterance_id).where(
                    UtteranceRelevance.project_id == project_id,
                    UtteranceRelevance.meeting_id == meeting_id,
                    UtteranceRelevance.analysis_id == relevance.id,
                    UtteranceRelevance.outcome == "RELEVANT",
                )
            )
        )
        new = run is None
        if run is None:
            run = EventExtraction(
                project_id=project_id,
                meeting_id=meeting_id,
                relevance_analysis_id=relevance.id,
                created_by=LOCAL_DEMO_ACTOR_ID,
                cache_key=key,
                context_fingerprint=fingerprint,
                extractor_version=EXTRACTOR_VERSION,
                model=provider.model,
                context_snapshot=context.model_dump(mode="json", by_alias=True),
                eligible_segments=len(eligible_ids),
            )
            session.add(run)
            session.flush()
        if (
            run.processing_token
            and run.processing_started_at
            and run.processing_started_at > datetime.now(UTC) - timedelta(seconds=LEASE_SECONDS)
        ):
            raise StateError(
                "EVENT_BUSY", "Event extraction is already running. Refresh shortly.", 409
            )
        done = set(
            session.scalars(
                select(ExtractedSegment.utterance_id).where(
                    ExtractedSegment.project_id == project_id,
                    ExtractedSegment.extraction_id == run.id,
                )
            )
        )
        utterances = list(
            session.scalars(
                select(Utterance)
                .where(Utterance.project_id == project_id, Utterance.meeting_id == meeting_id)
                .order_by(Utterance.sequence)
            )
        )
        characters = 0
        for index, u in enumerate(utterances):
            if u.id not in eligible_ids or u.id in done:
                continue
            previous = utterances[index - 1] if index else None
            window = EventWindow(
                source=SourceSegment(
                    id=u.id, sequence=u.sequence, speaker=u.speaker_label, text=u.text
                ),
                previous=SourceSegment(
                    id=previous.id,
                    sequence=previous.sequence,
                    speaker=previous.speaker_label,
                    text=previous.text[-1200:],
                )
                if previous
                else None,
            )
            size = len(window.source.text) + (len(window.previous.text) if window.previous else 0)
            if len(windows) >= MAX_WINDOWS or characters + size > MAX_WINDOW_TEXT:
                break
            windows.append(window)
            characters += size
        run.eligible_segments = len(eligible_ids)
        run.processing_token = None
        run.processing_started_at = None
        run.last_error = None
        if windows:
            validate_inputs(windows, context)
            if not provider.available:
                run.last_error = "EVENT_PROVIDER_UNAVAILABLE"
            else:
                run.processing_token = token
                run.processing_started_at = datetime.now(UTC)
                run.api_calls += 1
        if new or windows:
            audit(
                session,
                run,
                "EVENT_EXTRACTION_STARTED",
                {
                    "eligibleSegments": len(eligible_ids),
                    "batchSegments": len(windows),
                    "errorCode": run.last_error,
                },
            )
        session.flush()
        run_id = run.id
    session.commit()  # Never hold database locks across the model request.
    if not windows or not provider.available:
        return extraction_view(session, project_id, meeting_id, provider, relevance_provider)
    started = time.monotonic()
    result: EventProviderResult | None = None
    error: str | None = None
    try:
        result = provider.extract(windows, context)
        validate_extraction(result.batch.model_dump(mode="json", by_alias=True), windows)
    except StateError as exc:
        error = exc.code
    except Exception:
        error = "EVENT_PROVIDER_FAILED"
    try:
        with session.begin_nested():
            find_meeting(session, project_id, meeting_id, lock=True)
            run = session.scalar(
                select(EventExtraction)
                .where(
                    EventExtraction.id == run_id,
                    EventExtraction.project_id == project_id,
                    EventExtraction.meeting_id == meeting_id,
                )
                .with_for_update()
            )
            if run is None or run.processing_token != token:
                raise StateError(
                    "EVENT_SUPERSEDED",
                    "This extraction attempt was superseded. Refresh the meeting.",
                    409,
                )
            _, current_fingerprint = project_context(session, project_id)
            changed = current_fingerprint != fingerprint
            run.processing_token = None
            run.processing_started_at = None
            run.latency_ms += max(0, int((time.monotonic() - started) * 1000))
            run.last_error = "EVENT_CONTEXT_CHANGED" if changed else error
            if result is not None and error is None and not changed:
                for item in result.batch.items:
                    session.add(
                        ExtractedSegment(
                            project_id=project_id,
                            meeting_id=meeting_id,
                            extraction_id=run.id,
                            utterance_id=item.id,
                            event_count=len(item.events),
                        )
                    )
                session.flush()
                for item in result.batch.items:
                    for ordinal, event in enumerate(item.events):
                        candidate = ProjectEventCandidate(
                            project_id=project_id,
                            meeting_id=meeting_id,
                            extraction_id=run.id,
                            utterance_id=item.id,
                            ordinal=ordinal,
                            kind=event.kind.value,
                            statement=event.statement.value,
                            title=event.title,
                            description=event.description,
                            confidence=event.confidence,
                            owner_mention=event.owner_mention,
                            due_date_text=event.due_date_text,
                        )
                        session.add(candidate)
                        session.flush()
                        session.add_all(
                            [
                                EventCandidateEvidence(
                                    project_id=project_id,
                                    meeting_id=meeting_id,
                                    candidate_id=candidate.id,
                                    utterance_id=e.utterance_id,
                                    quote=e.quote,
                                )
                                for e in event.evidence
                            ]
                        )
                if result.input_tokens is not None and result.output_tokens is not None:
                    run.input_tokens += result.input_tokens
                    run.output_tokens += result.output_tokens
                    run.usage_reported_calls += 1
            session.flush()
            audit(
                session,
                run,
                "EVENT_EXTRACTION_FAILED" if run.last_error else "EVENTS_EXTRACTED",
                {
                    "segments": len(windows) if not run.last_error else 0,
                    "errorCode": run.last_error,
                    "model": run.model,
                },
            )
    except Exception:
        with session.begin_nested():
            failed = session.scalar(
                select(EventExtraction)
                .where(
                    EventExtraction.id == run_id,
                    EventExtraction.project_id == project_id,
                    EventExtraction.meeting_id == meeting_id,
                )
                .with_for_update()
            )
            if failed is not None and failed.processing_token == token:
                failed.processing_token = None
                failed.processing_started_at = None
                failed.last_error = "EVENT_SAVE_FAILED"
        session.commit()
        raise
    session.commit()
    return extraction_view(session, project_id, meeting_id, provider, relevance_provider)
