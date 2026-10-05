"""Audited, cached relevance interpretations, with bounded explicit AI batches."""

import json
import time
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, RelevanceAnalysis, Utterance, UtteranceRelevance
from app.domain.manual_state import StateError
from app.domain.relevance import (
    CLASSIFIER_VERSION,
    CONFIDENCE_THRESHOLD,
    MAX_AI_SEGMENTS,
    MAX_AI_TEXT,
    RelevanceClassification,
    Segment,
    validate_batch,
)
from app.repositories.audit import AuditRepository
from app.services.meetings import find_meeting
from app.services.project_access import LOCAL_DEMO_ACTOR_ID
from app.services.relevance_context import contextual_rule, project_context
from app.services.relevance_provider import ProviderResult, RelevanceProvider

PAGE_SIZE = 100
LEASE_SECONDS = 45


def cache_key(transcript_hash: str, fingerprint: str, model: str) -> str:
    return sha256(
        json.dumps([transcript_hash, fingerprint, model, CLASSIFIER_VERSION]).encode()
    ).hexdigest()


def append_audit(
    session: Session, run: RelevanceAnalysis, action: str, payload: dict[str, Any]
) -> None:
    AuditRepository(session, run.project_id).append(
        AuditEvent(
            project_id=run.project_id,
            actor_id=LOCAL_DEMO_ACTOR_ID,
            action=action,
            entity_type="relevance_analysis",
            entity_id=run.id,
            payload={"meetingId": str(run.meeting_id), **payload},
        )
    )


def result_record(
    run: RelevanceAnalysis, utterance_id: UUID, classification: RelevanceClassification, method: str
) -> UtteranceRelevance:
    outcome = (
        "UNCERTAIN"
        if classification.confidence < CONFIDENCE_THRESHOLD
        else "RELEVANT"
        if classification.relevant
        else "IGNORED"
    )
    return UtteranceRelevance(
        project_id=run.project_id,
        meeting_id=run.meeting_id,
        analysis_id=run.id,
        utterance_id=utterance_id,
        outcome=outcome,
        method=method,
        relevant=classification.relevant,
        confidence=classification.confidence,
        reason=classification.reason,
        related_entity_types=[str(x) for x in classification.related_entity_types],
    )


def analysis_view(
    session: Session,
    project_id: UUID,
    meeting_id: UUID,
    provider: RelevanceProvider,
    *,
    page: int = 1,
    outcome: str = "ALL",
) -> dict[str, Any]:
    meeting = find_meeting(session, project_id, meeting_id)
    _, fingerprint = project_context(session, project_id)
    key = cache_key(meeting.transcript_hash or "", fingerprint, provider.model)
    query = select(RelevanceAnalysis).where(
        RelevanceAnalysis.project_id == project_id, RelevanceAnalysis.meeting_id == meeting_id
    )
    run = session.scalar(query.where(RelevanceAnalysis.cache_key == key))
    if run is None:
        run = session.scalar(
            query.order_by(RelevanceAnalysis.created_at.desc(), RelevanceAnalysis.id).limit(1)
        )
    total = (
        session.scalar(
            select(func.count())
            .select_from(Utterance)
            .where(Utterance.project_id == project_id, Utterance.meeting_id == meeting_id)
        )
        or 0
    )
    response: dict[str, Any] = {
        "projectId": str(project_id),
        "meetingId": str(meeting_id),
        "analysis": None,
        "stale": False,
        "counts": {
            "total": total,
            "analyzed": 0,
            "relevant": 0,
            "ignored": 0,
            "uncertain": 0,
            "pending": total,
        },
        "ignoredPercent": None,
        "items": [],
        "page": page,
        "pageSize": PAGE_SIZE,
        "filteredCount": 0,
    }
    if run is None:
        return response
    counts: dict[str, int] = {
        outcome: count
        for outcome, count in session.execute(
            select(UtteranceRelevance.outcome, func.count())
            .where(
                UtteranceRelevance.project_id == project_id,
                UtteranceRelevance.analysis_id == run.id,
            )
            .group_by(UtteranceRelevance.outcome)
        )
    }
    analyzed = sum(counts.values())
    response["counts"] = {
        "total": total,
        "analyzed": analyzed,
        "relevant": counts.get("RELEVANT", 0),
        "ignored": counts.get("IGNORED", 0),
        "uncertain": counts.get("UNCERTAIN", 0),
        "pending": total - analyzed,
    }
    response["ignoredPercent"] = (
        (counts.get("IGNORED", 0) * 200 + analyzed) // (2 * analyzed) if analyzed else None
    )
    response["stale"] = run.cache_key != key
    response["analysis"] = {
        "id": str(run.id),
        "model": run.model,
        "classifierVersion": run.classifier_version,
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
    }
    results = (
        select(UtteranceRelevance, Utterance)
        .join(
            Utterance,
            (Utterance.project_id == UtteranceRelevance.project_id)
            & (Utterance.meeting_id == UtteranceRelevance.meeting_id)
            & (Utterance.id == UtteranceRelevance.utterance_id),
        )
        .where(
            UtteranceRelevance.project_id == project_id, UtteranceRelevance.analysis_id == run.id
        )
    )
    if outcome != "ALL":
        results = results.where(UtteranceRelevance.outcome == outcome)
    response["filteredCount"] = counts.get(outcome, 0) if outcome != "ALL" else analyzed
    rows = session.execute(
        results.order_by(Utterance.sequence).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    ).all()
    response["items"] = [
        {
            "utteranceId": str(u.id),
            "sequence": u.sequence,
            "speaker": u.speaker_label,
            "text": u.text[:400],
            "outcome": r.outcome,
            "relevant": r.relevant,
            "confidence": r.confidence,
            "reason": r.reason,
            "relatedEntityTypes": r.related_entity_types,
            "method": r.method,
        }
        for r, u in rows
    ]
    return response


def analyze_meeting(
    session: Session, project_id: UUID, meeting_id: UUID, provider: RelevanceProvider
) -> dict[str, Any]:
    token = uuid4()
    segments: list[Segment] = []
    with session.begin_nested():
        meeting = find_meeting(session, project_id, meeting_id, lock=True)
        if not meeting.transcript_hash:
            raise StateError(
                "RELEVANCE_NO_TRANSCRIPT", "Upload a transcript before analyzing relevance.", 409
            )
        context, fingerprint = project_context(session, project_id)
        key = cache_key(meeting.transcript_hash, fingerprint, provider.model)
        run = session.scalar(
            select(RelevanceAnalysis)
            .where(
                RelevanceAnalysis.project_id == project_id,
                RelevanceAnalysis.meeting_id == meeting_id,
                RelevanceAnalysis.cache_key == key,
            )
            .with_for_update()
        )
        utterances = list(
            session.scalars(
                select(Utterance)
                .where(Utterance.project_id == project_id, Utterance.meeting_id == meeting_id)
                .order_by(Utterance.sequence)
            )
        )
        if run is None:
            run = RelevanceAnalysis(
                project_id=project_id,
                meeting_id=meeting_id,
                created_by=LOCAL_DEMO_ACTOR_ID,
                cache_key=key,
                context_fingerprint=fingerprint,
                transcript_hash=meeting.transcript_hash,
                classifier_version=CLASSIFIER_VERSION,
                model=provider.model[:80],
                context_snapshot=context.model_dump(mode="json", by_alias=True),
                total_segments=len(utterances),
            )
            session.add(run)
            session.flush()
            rule_results = []
            for u in utterances:
                rule_result = contextual_rule(u.text, context)
                if rule_result:
                    rule_results.append(result_record(run, u.id, rule_result, "CONTEXT_RULE"))
            session.add_all(rule_results)
            session.flush()
            append_audit(
                session,
                run,
                "RELEVANCE_ANALYZED",
                {"ruleSegments": len(rule_results), "contextFingerprint": fingerprint},
            )
        if (
            run.processing_token
            and run.processing_started_at
            and run.processing_started_at > datetime.now(UTC) - timedelta(seconds=LEASE_SECONDS)
        ):
            raise StateError(
                "RELEVANCE_BUSY", "Relevance analysis is already running. Refresh shortly.", 409
            )
        done = set(
            session.scalars(
                select(UtteranceRelevance.utterance_id).where(
                    UtteranceRelevance.analysis_id == run.id,
                    UtteranceRelevance.project_id == project_id,
                )
            )
        )
        characters = 0
        for index, u in enumerate(utterances):
            if u.id in done:
                continue
            previous = utterances[index - 1].text[-800:] if index else ""
            size = len(u.text) + len(previous)
            if len(segments) >= MAX_AI_SEGMENTS or characters + size > MAX_AI_TEXT:
                break
            segments.append(Segment(id=u.id, text=u.text, previous_text=previous))
            characters += size
        if not segments:
            run.last_error = None
        elif not provider.available:
            run.last_error = "RELEVANCE_UNAVAILABLE"
        else:
            run.processing_token = token
            run.processing_started_at = datetime.now(UTC)
            run.api_calls += 1
            run.last_error = None
        session.flush()
        run_id = run.id
    session.commit()  # Release every DB lock before making the provider request.
    if not segments or not provider.available:
        return analysis_view(session, project_id, meeting_id, provider)
    started = time.monotonic()
    result: ProviderResult | None = None
    error: str | None = None
    try:
        result = provider.classify(segments, context)
        validate_batch(result.batch.model_dump(mode="json", by_alias=True), segments)
    except StateError as exc:
        error = exc.code
    except Exception:
        error = "RELEVANCE_PROVIDER_FAILED"
    try:
        with session.begin_nested():
            find_meeting(session, project_id, meeting_id, lock=True)
            run = session.scalar(
                select(RelevanceAnalysis)
                .where(
                    RelevanceAnalysis.id == run_id,
                    RelevanceAnalysis.project_id == project_id,
                    RelevanceAnalysis.meeting_id == meeting_id,
                )
                .with_for_update()
            )
            if run is None or run.processing_token != token:
                raise StateError(
                    "RELEVANCE_SUPERSEDED",
                    "This analysis attempt was superseded. Refresh the meeting.",
                    409,
                )
            _, current_fingerprint = project_context(session, project_id)
            changed = current_fingerprint != fingerprint
            run.processing_token = None
            run.processing_started_at = None
            run.latency_ms += max(0, int((time.monotonic() - started) * 1000))
            run.last_error = "RELEVANCE_CONTEXT_CHANGED" if changed else error
            if result is not None and error is None and not changed:
                session.add_all(
                    [result_record(run, item.id, item, "GEMINI") for item in result.batch.items]
                )
                if result.input_tokens is not None and result.output_tokens is not None:
                    run.input_tokens += result.input_tokens
                    run.output_tokens += result.output_tokens
                    run.usage_reported_calls += 1
            session.flush()
            append_audit(
                session,
                run,
                "RELEVANCE_ANALYSIS_FAILED" if run.last_error else "RELEVANCE_ANALYZED",
                {
                    "aiSegments": len(segments) if not run.last_error else 0,
                    "errorCode": run.last_error,
                    "model": run.model,
                },
            )
    except Exception:
        # Release our lease even when result/audit persistence fails. This updates
        # operational metadata only; the result savepoint has already rolled back.
        with session.begin_nested():
            failed_run = session.scalar(
                select(RelevanceAnalysis)
                .where(
                    RelevanceAnalysis.id == run_id,
                    RelevanceAnalysis.project_id == project_id,
                    RelevanceAnalysis.meeting_id == meeting_id,
                )
                .with_for_update()
            )
            if failed_run is not None and failed_run.processing_token == token:
                failed_run.processing_token = None
                failed_run.processing_started_at = None
                failed_run.last_error = "RELEVANCE_SAVE_FAILED"
        session.commit()
        raise
    session.commit()
    return analysis_view(session, project_id, meeting_id, provider)
