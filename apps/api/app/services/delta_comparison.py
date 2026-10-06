"""Scoped comparison transactions; provider calls never hold database locks."""

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
    DeltaComparisonRun,
    EventCandidateEvidence,
    ProjectDelta,
    ProjectEventCandidate,
    Utterance,
)
from app.domain.deltas import (
    COMPARATOR_VERSION,
    MAX_CANDIDATES,
    MAX_INPUT_CHARACTERS,
    ComparisonSource,
    validate_comparison_inputs,
    validate_comparisons,
)
from app.domain.manual_state import StateError
from app.repositories.audit import AuditRepository
from app.services.delta_context import comparison_context
from app.services.delta_provider import DeltaProvider, DeltaProviderResult
from app.services.event_extraction import extraction_view
from app.services.event_provider import EventProvider
from app.services.meetings import find_meeting
from app.services.project_access import LOCAL_DEMO_ACTOR_ID
from app.services.relevance_provider import RelevanceProvider

PAGE_SIZE = 100
LEASE_SECONDS = 45


def comparison_key(extraction_id: UUID, fingerprint: str, model: str) -> str:
    return sha256(
        json.dumps([str(extraction_id), fingerprint, model, COMPARATOR_VERSION]).encode()
    ).hexdigest()


def active(run: DeltaComparisonRun) -> bool:
    return bool(
        run.processing_token
        and run.processing_started_at
        and run.processing_started_at > datetime.now(UTC) - timedelta(seconds=LEASE_SECONDS)
    )


def audit(session: Session, run: DeltaComparisonRun, action: str, payload: dict[str, Any]) -> None:
    AuditRepository(session, run.project_id).append(
        AuditEvent(
            project_id=run.project_id,
            actor_id=LOCAL_DEMO_ACTOR_ID,
            action=action,
            entity_type="delta_comparison",
            entity_id=run.id,
            payload={"meetingId": str(run.meeting_id), **payload},
        )
    )


def source_inputs(
    session: Session, project_id: UUID, meeting_id: UUID, candidates: list[ProjectEventCandidate]
) -> list[ComparisonSource]:
    if not candidates:
        return []
    quotes: dict[UUID, list[dict[str, Any]]] = {}
    for evidence in session.scalars(
        select(EventCandidateEvidence)
        .where(
            EventCandidateEvidence.project_id == project_id,
            EventCandidateEvidence.meeting_id == meeting_id,
            EventCandidateEvidence.candidate_id.in_([c.id for c in candidates]),
        )
        .order_by(EventCandidateEvidence.utterance_id)
    ):
        quotes.setdefault(evidence.candidate_id, []).append(
            {"utteranceId": evidence.utterance_id, "quote": evidence.quote}
        )
    return [
        ComparisonSource.model_validate(
            {
                "id": c.id,
                "kind": c.kind,
                "statement": c.statement,
                "title": c.title,
                "description": c.description,
                "confidence": c.confidence,
                "evidence": quotes.get(c.id, []),
            }
        )
        for c in candidates
    ]


def delta_view(
    session: Session,
    project_id: UUID,
    meeting_id: UUID,
    provider: DeltaProvider,
    events: EventProvider,
    relevance: RelevanceProvider,
    *,
    page: int = 1,
    outcome: str = "ALL",
) -> dict[str, Any]:
    find_meeting(session, project_id, meeting_id)
    _, fingerprint = comparison_context(session, project_id)
    source = extraction_view(session, project_id, meeting_id, events, relevance)
    current_id = (
        UUID(source["extraction"]["id"])
        if source["extraction"] and not source["stale"] and source["prerequisite"] is None
        else None
    )
    query = select(DeltaComparisonRun).where(
        DeltaComparisonRun.project_id == project_id, DeltaComparisonRun.meeting_id == meeting_id
    )
    run = (
        session.scalar(
            query.where(
                DeltaComparisonRun.cache_key
                == comparison_key(current_id, fingerprint, provider.model)
            )
        )
        if current_id
        else None
    )
    if run is None:
        run = session.scalar(
            query.order_by(DeltaComparisonRun.created_at.desc(), DeltaComparisonRun.id).limit(1)
        )
    selected_id = run.extraction_id if run else current_id
    base = select(ProjectDelta).where(
        ProjectDelta.project_id == project_id,
        ProjectDelta.meeting_id == meeting_id,
        ProjectDelta.run_id == (run.id if run else None),
    )
    groups: dict[str, int] = {
        outcome: count
        for outcome, count in session.execute(
            base.with_only_columns(ProjectDelta.outcome, func.count()).group_by(
                ProjectDelta.outcome
            )
        ).all()
    }
    eligible = (
        session.scalar(
            select(func.count())
            .select_from(ProjectEventCandidate)
            .where(
                ProjectEventCandidate.project_id == project_id,
                ProjectEventCandidate.meeting_id == meeting_id,
                ProjectEventCandidate.extraction_id == selected_id,
            )
        )
        or 0
    )
    processed = sum(groups.values())
    filtered = base.where(ProjectDelta.outcome == outcome) if outcome != "ALL" else base
    filtered_count = session.scalar(select(func.count()).select_from(filtered.subquery())) or 0
    rows = session.execute(
        filtered.add_columns(ProjectEventCandidate, Utterance)
        .join(
            ProjectEventCandidate,
            (ProjectEventCandidate.project_id == ProjectDelta.project_id)
            & (ProjectEventCandidate.meeting_id == ProjectDelta.meeting_id)
            & (ProjectEventCandidate.id == ProjectDelta.candidate_id),
        )
        .join(
            Utterance,
            (Utterance.project_id == ProjectEventCandidate.project_id)
            & (Utterance.meeting_id == ProjectEventCandidate.meeting_id)
            & (Utterance.id == ProjectEventCandidate.utterance_id),
        )
        .order_by(Utterance.sequence, ProjectEventCandidate.ordinal, ProjectDelta.id)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    evidence_map: dict[UUID, list[dict[str, Any]]] = {}
    if rows:
        for evidence, utterance in session.execute(
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
                EventCandidateEvidence.candidate_id.in_([c.id for _, c, _ in rows]),
            )
            .order_by(Utterance.sequence)
        ):
            evidence_map.setdefault(evidence.candidate_id, []).append(
                {
                    "utteranceId": str(utterance.id),
                    "sequence": utterance.sequence,
                    "speaker": utterance.speaker_label,
                    "timestampMs": utterance.timestamp_ms,
                    "quote": evidence.quote,
                }
            )
    return {
        "projectId": str(project_id),
        "meetingId": str(meeting_id),
        "prerequisite": source["prerequisite"] or ("EXTRACT_EVENTS" if not current_id else None),
        "currentExtractionId": str(current_id) if current_id else None,
        "stale": bool(
            run
            and (
                current_id is None
                or run.cache_key != comparison_key(current_id, fingerprint, provider.model)
            )
        ),
        "sourcePending": source["counts"]["pending"] + source["relevance"]["pending"],
        "counts": {
            "eligible": eligible,
            "processed": processed,
            "pending": eligible - processed,
            "same": groups.get("SAME", 0),
            "change": groups.get("CHANGE", 0),
            "new": groups.get("NEW", 0),
            "unclear": groups.get("UNCLEAR", 0),
        },
        "run": None
        if run is None
        else {
            "id": str(run.id),
            "extractionId": str(run.extraction_id),
            "model": run.model,
            "comparatorVersion": run.comparator_version,
            "createdAt": run.created_at.isoformat(),
            "contextComplete": run.context_snapshot["complete"],
            "lastError": run.last_error,
            "apiCalls": run.api_calls,
            "inputTokens": run.input_tokens,
            "outputTokens": run.output_tokens,
            "usageReportedCalls": run.usage_reported_calls,
            "latencyMs": run.latency_ms,
            "processing": active(run),
        },
        "items": [
            {
                "id": str(d.id),
                "candidateId": str(c.id),
                "projectId": str(d.project_id),
                "meetingId": str(d.meeting_id),
                "runId": str(d.run_id),
                "extractionId": str(d.extraction_id),
                "kind": c.kind,
                "statement": c.statement,
                "title": c.title,
                "primaryUtteranceId": str(c.utterance_id),
                "outcome": d.outcome,
                "status": d.status,
                "reason": d.reason,
                "confidence": d.confidence,
                "target": d.target_snapshot,
                "changes": d.changes,
                "evidence": evidence_map.get(c.id, []),
            }
            for d, c, _ in rows
        ],
        "page": page,
        "pageSize": PAGE_SIZE,
        "filteredCount": filtered_count,
    }


def compare_meeting(
    session: Session,
    project_id: UUID,
    meeting_id: UUID,
    provider: DeltaProvider,
    events: EventProvider,
    relevance: RelevanceProvider,
) -> dict[str, Any]:
    token = uuid4()
    with session.begin_nested():
        find_meeting(session, project_id, meeting_id, lock=True)
        context, fingerprint = comparison_context(session, project_id)
        view = extraction_view(session, project_id, meeting_id, events, relevance)
        if view["prerequisite"] or view["stale"] or view["extraction"] is None:
            raise StateError(
                "DELTA_EVENTS_REQUIRED",
                "Analyze relevance and extract events for the current baseline first.",
                409,
            )
        if not 1 <= len(provider.model) <= 80:
            raise StateError("DELTA_CONFIGURATION", "Choose a bounded comparison model name.", 503)
        extraction_id = UUID(view["extraction"]["id"])
        key = comparison_key(extraction_id, fingerprint, provider.model)
        run = session.scalar(
            select(DeltaComparisonRun)
            .where(
                DeltaComparisonRun.project_id == project_id,
                DeltaComparisonRun.meeting_id == meeting_id,
                DeltaComparisonRun.cache_key == key,
            )
            .with_for_update()
        )
        new = run is None
        if run is None:
            run = DeltaComparisonRun(
                project_id=project_id,
                meeting_id=meeting_id,
                extraction_id=extraction_id,
                created_by=LOCAL_DEMO_ACTOR_ID,
                cache_key=key,
                context_fingerprint=fingerprint,
                context_snapshot=context.model_dump(mode="json"),
                comparator_version=COMPARATOR_VERSION,
                model=provider.model,
            )
            session.add(run)
            session.flush()
        if active(run):
            raise StateError("DELTA_BUSY", "Comparison is already running. Refresh shortly.", 409)
        done = select(ProjectDelta.candidate_id).where(
            ProjectDelta.project_id == project_id,
            ProjectDelta.meeting_id == meeting_id,
            ProjectDelta.run_id == run.id,
        )
        candidates = list(
            session.scalars(
                select(ProjectEventCandidate)
                .join(
                    Utterance,
                    (Utterance.project_id == ProjectEventCandidate.project_id)
                    & (Utterance.meeting_id == ProjectEventCandidate.meeting_id)
                    & (Utterance.id == ProjectEventCandidate.utterance_id),
                )
                .where(
                    ProjectEventCandidate.project_id == project_id,
                    ProjectEventCandidate.meeting_id == meeting_id,
                    ProjectEventCandidate.extraction_id == extraction_id,
                    ProjectEventCandidate.id.not_in(done),
                )
                .order_by(Utterance.sequence, ProjectEventCandidate.ordinal)
                .limit(MAX_CANDIDATES)
            )
        )
        sources: list[ComparisonSource] = []
        characters = 0
        for source in source_inputs(session, project_id, meeting_id, candidates):
            size = len(source.model_dump_json(by_alias=True))
            if characters + size > MAX_INPUT_CHARACTERS:
                break
            sources.append(source)
            characters += size
        input_hash = sha256(
            json.dumps(
                [s.model_dump(mode="json", by_alias=True) for s in sources], sort_keys=True
            ).encode()
        ).hexdigest()
        run.processing_token = None
        run.processing_started_at = None
        run.last_error = None
        if sources:
            validate_comparison_inputs(sources, context)
            if not provider.available:
                run.last_error = "DELTA_PROVIDER_UNAVAILABLE"
            else:
                run.processing_token = token
                run.processing_started_at = datetime.now(UTC)
                run.api_calls += 1
        if new or sources:
            audit(
                session,
                run,
                "DELTA_COMPARISON_STARTED",
                {"batchCandidates": len(sources), "errorCode": run.last_error},
            )
        session.flush()
        run_id = run.id
    session.commit()
    if not sources or not provider.available:
        return delta_view(session, project_id, meeting_id, provider, events, relevance)
    started = time.monotonic()
    result: DeltaProviderResult | None = None
    error: str | None = None
    try:
        result = provider.compare(sources, context)
        validate_comparisons(result.batch.model_dump(mode="json", by_alias=True), sources, context)
    except StateError as exc:
        error = exc.code
    except Exception:
        error = "DELTA_PROVIDER_FAILED"
    try:
        with session.begin_nested():
            find_meeting(session, project_id, meeting_id, lock=True)
            run = session.scalar(
                select(DeltaComparisonRun)
                .where(
                    DeltaComparisonRun.id == run_id,
                    DeltaComparisonRun.project_id == project_id,
                    DeltaComparisonRun.meeting_id == meeting_id,
                )
                .with_for_update()
            )
            if run is None or run.processing_token != token:
                raise StateError(
                    "DELTA_SUPERSEDED", "This comparison was superseded. Refresh the meeting.", 409
                )
            _, current_fingerprint = comparison_context(session, project_id)
            now = extraction_view(session, project_id, meeting_id, events, relevance)
            changed = (
                current_fingerprint != fingerprint
                or now["stale"]
                or now["extraction"] is None
                or now["extraction"]["id"] != str(extraction_id)
            )
            current_candidates = list(
                session.scalars(
                    select(ProjectEventCandidate).where(
                        ProjectEventCandidate.project_id == project_id,
                        ProjectEventCandidate.meeting_id == meeting_id,
                        ProjectEventCandidate.id.in_([s.id for s in sources]),
                    )
                )
            )
            by_id = {c.id: c for c in current_candidates}
            current_sources = source_inputs(
                session, project_id, meeting_id, [by_id[s.id] for s in sources if s.id in by_id]
            )
            current_hash = sha256(
                json.dumps(
                    [s.model_dump(mode="json", by_alias=True) for s in current_sources],
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            run.processing_token = None
            run.processing_started_at = None
            run.latency_ms += max(0, int((time.monotonic() - started) * 1000))
            run.last_error = (
                "DELTA_CONTEXT_CHANGED"
                if changed
                else "DELTA_INPUT_CHANGED"
                if current_hash != input_hash
                else error
            )
            if result is not None and run.last_error is None:
                targets = {r.id: r for r in context.records}
                for item in result.batch.items:
                    target = targets.get(item.target_id) if item.target_id else None
                    session.add(
                        ProjectDelta(
                            project_id=project_id,
                            meeting_id=meeting_id,
                            extraction_id=extraction_id,
                            run_id=run.id,
                            candidate_id=item.id,
                            outcome=item.outcome.value,
                            reason=item.reason,
                            confidence=item.confidence,
                            target_id=target.id if target else None,
                            target_version=target.version if target else None,
                            target_snapshot=target.model_dump(mode="json") if target else None,
                            changes=[
                                {
                                    "field": c.field,
                                    "previousValue": target.values.get(c.field) if target else None,
                                    "proposedText": c.proposed_text,
                                }
                                for c in item.changes
                            ],
                        )
                    )
                if result.input_tokens is not None and result.output_tokens is not None:
                    run.input_tokens += result.input_tokens
                    run.output_tokens += result.output_tokens
                    run.usage_reported_calls += 1
            audit(
                session,
                run,
                "DELTA_COMPARISON_FINISHED",
                {"batchCandidates": len(sources), "errorCode": run.last_error},
            )
            session.flush()
        session.commit()
    except Exception:
        session.rollback()
        raise
    return delta_view(session, project_id, meeting_id, provider, events, relevance)
