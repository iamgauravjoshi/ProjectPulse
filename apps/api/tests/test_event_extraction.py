import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_database_session
from app.config import get_settings
from app.db.models import (
    AuditEvent,
    EventCandidateEvidence,
    EventExtraction,
    ExtractedSegment,
    Project,
    ProjectEventCandidate,
    ProjectMember,
    Requirement,
    UtteranceRelevance,
)
from app.domain.demo_identity import demo_id
from app.domain.events import ExtractedEvent, ExtractionBatch, SegmentEvents
from app.domain.manual_state import StateError
from app.domain.relevance import ClassificationBatch, SegmentClassification
from app.main import app
from app.repositories.audit import AuditRepository
from app.services.demo_seed import DEMO_PROJECT_ID, seed_demo
from app.services.event_provider import EventProviderResult, GeminiEvents, get_event_provider
from app.services.project_access import LOCAL_DEMO_ACTOR_ID
from app.services.relevance_provider import ProviderResult, get_relevance_provider

pytestmark = pytest.mark.integration
ROOT = f"/api/v1/projects/{DEMO_PROJECT_ID}/meetings"


class FakeRelevance:
    model = "synthetic-phase5-relevance"
    available = True

    def classify(self, segments, context):
        return ProviderResult(
            ClassificationBatch(
                items=[
                    SegmentClassification(
                        id=s.id,
                        relevant=True,
                        confidence=0.9,
                        reason="Synthetic delivery classification",
                        relatedEntityTypes=["requirement"],
                    )
                    for s in segments
                ]
            )
        )


class FakeEvents:
    model = "synthetic-phase5-events"
    available = True
    calls = 0
    fail = False
    malformed = False
    empty = False
    confidence = 0.9
    hook = None
    windows = None

    def extract(self, windows, context):
        self.calls += 1
        self.windows = windows
        if self.hook:
            self.hook()
        if self.fail:
            raise StateError("EVENT_PROVIDER_FAILED", "Synthetic outage", 503)
        result = ExtractionBatch(
            items=[
                SegmentEvents(
                    id=w.source.id,
                    events=[]
                    if self.empty
                    else [
                        ExtractedEvent(
                            kind="REQUIREMENT_CHANGE",
                            statement="PROPOSAL",
                            title="Synthetic SSO scope event",
                            description="Source interpretation awaiting future human review.",
                            confidence=self.confidence,
                            ownerMention=None,
                            dueDateText=None,
                            evidence=[{"utteranceId": w.source.id, "quote": w.source.text[:500]}],
                        )
                    ],
                )
                for w in windows
            ]
        )
        if self.malformed:
            result.items[0].events[0].evidence[0].utterance_id = uuid4()
        return EventProviderResult(result, 120, 60)


@pytest.fixture
def event_client(db_session):
    seed_demo(db_session)
    provider = FakeEvents()
    relevance = FakeRelevance()
    app.dependency_overrides[get_database_session] = lambda: db_session
    app.dependency_overrides[get_relevance_provider] = lambda: relevance
    app.dependency_overrides[get_event_provider] = lambda: provider
    try:
        with TestClient(app) as client:
            yield client, provider, relevance
    finally:
        for key in [get_database_session, get_relevance_provider, get_event_provider]:
            app.dependency_overrides.pop(key, None)


def meeting(client, texts, *, analyze=True):
    created = client.post(ROOT, json={"title": "Synthetic Phase 5 test"}).json()
    path = f"{ROOT}/{created['id']}"
    if texts:
        assert (
            client.post(
                path + "/transcript",
                params={"filename": "events.json"},
                content=json.dumps([{"speaker": "Sarah", "text": s} for s in texts]).encode(),
            ).status_code
            == 201
        )
        if analyze:
            assert client.post(path + "/relevance").status_code == 200
    return path


def test_cited_candidates_cache_usage_baseline_and_no_database_lock(db_session, event_client):
    client, provider, _ = event_client
    baseline = client.get(f"/api/v1/projects/{DEMO_PROJECT_ID}/workspace").json()
    path = meeting(client, ["Good morning.", "SSO should move to Phase 1."])

    def unlocked():
        assert not db_session.in_transaction()

    provider.hook = unlocked
    first = client.post(path + "/events")
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["counts"] == {
        "eligible": 1,
        "processed": 1,
        "pending": 0,
        "candidates": 1,
        "noEvent": 0,
        "lowConfidence": 0,
    }
    assert result["relevance"]["ignored"] == 1 and result["extraction"]["apiCalls"] == 1
    assert (
        result["extraction"]["inputTokens"] == 120
        and result["extraction"]["usageReportedCalls"] == 1
    )
    item = result["items"][0]
    assert (
        item["status"] == "CANDIDATE" and item["statement"] == "PROPOSAL" and item["sequence"] == 1
    )
    assert (
        item["evidence"][0]["quote"] == "SSO should move to Phase 1."
        and item["ownerMention"] is None
    )
    audits = db_session.scalar(select(func.count()).select_from(AuditEvent))
    assert client.get(path + "/events").json()["items"] == result["items"]
    assert client.post(path + "/events").json()["items"] == result["items"]
    assert (
        provider.calls == 1
        and db_session.scalar(select(func.count()).select_from(AuditEvent)) == audits
    )
    after = client.get(f"/api/v1/projects/{DEMO_PROJECT_ID}/workspace").json()
    for key in [
        "project",
        "members",
        "requirements",
        "decisions",
        "commitments",
        "risks",
        "milestones",
        "dependencies",
        "questions",
    ]:
        assert baseline[key] == after[key]


def test_prerequisites_and_client_body_rejection(event_client):
    client, provider, _ = event_client
    empty = meeting(client, [])
    assert client.get(empty + "/events").json()["prerequisite"] == "NO_TRANSCRIPT"
    assert client.post(empty + "/events").status_code == 409
    unclassified = meeting(client, ["SSO remains Phase 2."], analyze=False)
    assert client.get(unclassified + "/events").json()["prerequisite"] == "ANALYZE_RELEVANCE"
    assert client.post(unclassified + "/events").status_code == 409
    assert (
        client.post(unclassified + "/events", json={"createdBy": str(uuid4())}).status_code == 413
    )
    assert provider.calls == 0


def test_missing_provider_retains_pending_and_explicit_retry(event_client):
    client, provider, _ = event_client
    path = meeting(client, ["SSO remains Phase 2."])
    provider.available = False
    first = client.post(path + "/events").json()
    assert first["counts"]["pending"] == 1 and first["items"] == []
    assert first["extraction"]["lastError"] == "EVENT_PROVIDER_UNAVAILABLE" and provider.calls == 0
    provider.available = True
    second = client.post(path + "/events").json()
    assert (
        second["extraction"]["id"] == first["extraction"]["id"]
        and second["counts"]["processed"] == 1
    )


@pytest.mark.parametrize("mode", ["fail", "malformed"])
def test_failure_has_no_partial_candidates_and_recovers(event_client, mode):
    client, provider, _ = event_client
    path = meeting(client, ["SSO remains Phase 2."] * 2)
    setattr(provider, mode, True)
    result = client.post(path + "/events").json()
    assert (
        result["counts"]["processed"] == 0
        and result["items"] == []
        and result["extraction"]["lastError"]
    )
    setattr(provider, mode, False)
    recovered = client.post(path + "/events").json()
    assert recovered["counts"]["processed"] == 2 and recovered["extraction"]["apiCalls"] == 2


def test_empty_event_results_are_completed_not_pending(event_client):
    client, provider, _ = event_client
    provider.empty = True
    path = meeting(client, ["SSO remains Phase 2."])
    result = client.post(path + "/events").json()
    assert result["counts"]["processed"] == result["counts"]["noEvent"] == 1
    assert result["counts"]["pending"] == result["counts"]["candidates"] == 0
    client.post(path + "/events")
    assert provider.calls == 1


def test_low_confidence_candidates_are_flagged_and_never_confirmed(event_client):
    client, provider, _ = event_client
    provider.confidence = 0.4
    path = meeting(client, ["SSO remains Phase 2."])
    result = client.post(path + "/events").json()
    assert result["counts"]["lowConfidence"] == 1 and result["items"][0]["needsReview"]
    assert result["items"][0]["status"] == "CANDIDATE"


def test_current_relevance_only_skips_uncertain_and_pending(db_session, event_client):
    client, provider, _ = event_client
    path = meeting(client, ["SSO remains Phase 2.", "SSO moves Phase 1."])
    result = db_session.scalar(
        select(UtteranceRelevance).where(UtteranceRelevance.outcome == "RELEVANT")
    )
    result.confidence = 0.4
    result.outcome = "UNCERTAIN"
    db_session.flush()
    extracted = client.post(path + "/events").json()
    assert extracted["counts"]["eligible"] == extracted["counts"]["processed"] == 1
    assert extracted["relevance"]["uncertain"] == 1 and provider.calls == 1


def test_more_relevance_results_extend_same_run_without_reprocessing(db_session, event_client):
    client, provider, _ = event_client
    path = meeting(client, ["The login control failed QA."] * 45)
    first = client.post(path + "/events").json()
    assert first["counts"]["eligible"] == 40 and first["counts"]["processed"] == 20
    assert client.post(path + "/relevance").json()["counts"]["relevant"] == 45
    second = client.post(path + "/events").json()
    assert second["extraction"]["id"] == first["extraction"]["id"]
    assert second["counts"]["eligible"] == 45 and second["counts"]["processed"] == 40
    third = client.post(path + "/events").json()
    assert third["counts"]["processed"] == 45 and provider.calls == 3


def test_character_budget_single_call_and_explicit_continuation(event_client):
    client, provider, _ = event_client
    path = meeting(client, ["SSO " + "x" * 5996] * 4)
    first = client.post(path + "/events").json()
    assert 1 <= first["counts"]["processed"] < 4 and provider.calls == 1
    assert (
        sum(
            len(w.source.text) + (len(w.previous.text) if w.previous else 0)
            for w in provider.windows
        )
        <= 20000
    )
    final = client.post(path + "/events").json()
    assert final["counts"]["processed"] == 4 and provider.calls == 2


def test_pagination_kind_filters_source_order_and_cache(event_client):
    client, provider, _ = event_client
    path = meeting(client, ["SSO remains Phase 2."] * 105)
    for _ in range(6):
        result = client.post(path + "/events").json()
    assert result["counts"]["processed"] == 105 and len(result["items"]) == 100
    last = client.get(path + "/events?page=2&kind=REQUIREMENT_CHANGE").json()
    assert [x["sequence"] for x in last["items"]] == list(range(100, 105)) and last[
        "filteredCount"
    ] == 105
    assert client.get(path + "/events?kind=RISK").json()["items"] == []
    assert client.get(path + "/events?page=401").status_code == 422
    assert client.get(path + "/events?kind=CONFIRMED").status_code == 422
    assert provider.calls == 6


def test_context_staleness_and_inflight_change_discard_results(db_session, event_client):
    client, provider, _ = event_client
    path = meeting(client, ["SSO remains Phase 2."])

    def change():
        db_session.add(
            Requirement(
                project_id=DEMO_PROJECT_ID, title="Changed baseline", status="ACTIVE", phase=1
            )
        )
        db_session.flush()

    provider.hook = change
    failed = client.post(path + "/events").json()
    assert failed["stale"] and failed["extraction"]["lastError"] == "EVENT_CONTEXT_CHANGED"
    assert failed["counts"]["processed"] == 0
    assert client.post(path + "/events").status_code == 409
    provider.hook = None
    client.post(path + "/relevance")
    refreshed = client.post(path + "/events").json()
    assert not refreshed["stale"] and refreshed["extraction"]["id"] != failed["extraction"]["id"]


def test_busy_lease_and_expired_recovery(db_session, event_client):
    client, provider, _ = event_client
    path = meeting(client, ["SSO remains Phase 2."])
    provider.available = False
    first = client.post(path + "/events").json()
    run = db_session.get(EventExtraction, UUID(first["extraction"]["id"]))
    run.processing_token = uuid4()
    run.processing_started_at = datetime.now(UTC)
    db_session.flush()
    provider.available = True
    assert client.post(path + "/events").status_code == 409
    run.processing_started_at = datetime.now(UTC) - timedelta(seconds=50)
    db_session.flush()
    assert client.post(path + "/events").json()["counts"]["processed"] == 1


@pytest.mark.parametrize("final", [False, True])
def test_audit_failure_rolls_back_candidates_and_releases_lease(
    db_session, event_client, monkeypatch, final
):
    client, provider, _ = event_client
    path = meeting(client, ["SSO remains Phase 2."])
    append = AuditRepository.append

    def fail(self, record):
        if record.action == ("EVENTS_EXTRACTED" if final else "EVENT_EXTRACTION_STARTED"):
            raise RuntimeError("Synthetic audit failure")
        return append(self, record)

    monkeypatch.setattr(AuditRepository, "append", fail)
    with pytest.raises(RuntimeError):
        client.post(path + "/events")
    assert db_session.scalar(select(func.count()).select_from(ProjectEventCandidate)) == 0
    assert db_session.scalar(select(func.count()).select_from(ExtractedSegment)) == 0
    run = db_session.scalar(select(EventExtraction))
    if final:
        assert run.processing_token is None and run.last_error == "EVENT_SAVE_FAILED"
        monkeypatch.setattr(AuditRepository, "append", append)
        assert client.post(path + "/events").json()["counts"]["processed"] == 1
    else:
        assert run is None and provider.calls == 0


def test_project_meeting_isolation_and_cascade(db_session, event_client):
    client, provider, _ = event_client
    path = meeting(client, ["SSO remains Phase 2."])
    client.post(path + "/events")
    other = Project(name="Other project")
    db_session.add(other)
    db_session.flush()
    hidden = path.replace(str(DEMO_PROJECT_ID), str(other.id))
    for member in [False, True]:
        if member:
            db_session.add(
                ProjectMember(project_id=other.id, user_id=LOCAL_DEMO_ACTOR_ID, role="QA")
            )
            db_session.flush()
        assert client.get(hidden + "/events").status_code == 404
        assert client.post(hidden + "/events").status_code == 404
    assert client.delete(path).status_code == 204
    for model in [EventExtraction, ExtractedSegment, ProjectEventCandidate, EventCandidateEvidence]:
        assert db_session.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize(
    "change",
    [{"status": "CONFIRMED"}, {"kind": "UNKNOWN"}, {"confidence": 1.5}, {"owner_mention": ""}],
)
def test_database_rejects_invalid_candidate_values(db_session, event_client, change):
    client, _, _ = event_client
    path = meeting(client, ["SSO remains Phase 2."])
    result = client.post(path + "/events").json()
    candidate = db_session.get(ProjectEventCandidate, UUID(result["items"][0]["id"]))
    with pytest.raises(IntegrityError), db_session.begin_nested():
        for key, value in change.items():
            setattr(candidate, key, value)
        db_session.flush()


def test_database_rejects_cross_meeting_evidence(db_session, event_client):
    client, _, _ = event_client
    first = meeting(client, ["SSO remains Phase 2."])
    second = meeting(client, ["SSO moves Phase 1."])
    result = client.post(first + "/events").json()
    second_source = client.get(second).json()["utterances"][0]["id"]
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            EventCandidateEvidence(
                project_id=DEMO_PROJECT_ID,
                meeting_id=UUID(first.rsplit("/", 1)[-1]),
                candidate_id=UUID(result["items"][0]["id"]),
                utterance_id=UUID(second_source),
                quote="SSO moves Phase 1.",
            )
        )
        db_session.flush()


def test_deleting_source_during_provider_call_is_safe(db_session, event_client):
    client, provider, _ = event_client
    path = meeting(client, ["SSO remains Phase 2."])
    provider.hook = lambda: client.delete(path)
    assert client.post(path + "/events").status_code == 404
    assert db_session.scalar(select(func.count()).select_from(ProjectEventCandidate)) == 0


def test_superseded_lease_cannot_persist_old_response(db_session, event_client):
    client, provider, _ = event_client
    path = meeting(client, ["SSO remains Phase 2."])

    def replace_lease():
        run = db_session.scalar(select(EventExtraction))
        run.processing_token = uuid4()
        db_session.flush()

    provider.hook = replace_lease
    assert client.post(path + "/events").status_code == 409
    assert db_session.scalar(select(func.count()).select_from(ProjectEventCandidate)) == 0


def test_provider_model_change_marks_prior_run_stale(event_client):
    client, provider, _ = event_client
    path = meeting(client, ["SSO remains Phase 2."])
    initial = client.post(path + "/events").json()
    provider.model = "synthetic-other-model"
    assert client.get(path + "/events").json()["stale"]
    latest = client.post(path + "/events").json()
    assert not latest["stale"] and latest["extraction"]["id"] != initial["extraction"]["id"]


def test_production_provider_without_key_never_fabricates_candidates(event_client, monkeypatch):
    client, _, _ = event_client
    path = meeting(client, ["SSO remains Phase 2."])
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    try:
        app.dependency_overrides.pop(get_event_provider)
        assert not GeminiEvents().available
        result = client.post(path + "/events").json()
        assert result["extraction"]["lastError"] == "EVENT_PROVIDER_UNAVAILABLE"
        assert result["counts"]["pending"] == 1 and result["items"] == []
        assert result["extraction"]["apiCalls"] == 0
    finally:
        get_settings.cache_clear()


def test_linked_speaker_is_distinct_from_owner_and_neighbor_quote_persists(event_client):
    client, provider, _ = event_client
    created = client.post(ROOT, json={"title": "Linked provenance"}).json()
    path = f"{ROOT}/{created['id']}"
    assert (
        client.post(
            path + "/participants",
            json={
                "displayName": "Sarah",
                "speakerKey": "id:sarah-source",
                "userId": str(demo_id("sarah")),
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            path + "/transcript",
            params={"filename": "provenance.json"},
            content=json.dumps(
                [
                    {
                        "speaker": "Sarah",
                        "speakerId": "sarah-source",
                        "text": "John will review SSO tomorrow.",
                    },
                    {
                        "speaker": "Sarah",
                        "speakerId": "sarah-source",
                        "text": "SSO review is a commitment.",
                    },
                ]
            ).encode(),
        ).status_code
        == 201
    )
    assert client.post(path + "/relevance").status_code == 200
    original = provider.extract

    def attributed(windows, context):
        result = original(windows, context)
        last = result.batch.items[-1].events[0]
        last.owner_mention = "John"
        last.due_date_text = "tomorrow"
        last.evidence.append(
            last.evidence[0].model_copy(
                update={"utterance_id": windows[-1].previous.id, "quote": windows[-1].previous.text}
            )
        )
        return result

    provider.extract = attributed
    result = client.post(path + "/events").json()
    event = result["items"][-1]
    assert event["saidByUserId"] == str(demo_id("sarah"))
    assert event["ownerMention"] == "John" and event["dueDateText"] == "tomorrow"
    assert [e["sequence"] for e in event["evidence"]] == [0, 1]
    assert client.get(path + "/events").json()["items"] == result["items"]
