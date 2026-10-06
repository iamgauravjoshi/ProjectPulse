from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_database_session
from app.db.models import (
    AuditEvent,
    DeltaComparisonRun,
    ProjectDelta,
    ProjectEventCandidate,
    Requirement,
)
from app.domain.deltas import ComparisonBatch
from app.domain.manual_state import StateError
from app.main import app
from app.repositories.audit import AuditRepository
from app.services.delta_context import comparison_context
from app.services.delta_provider import DeltaProviderResult, get_delta_provider
from app.services.demo_seed import DEMO_PROJECT_ID, seed_demo
from app.services.event_provider import get_event_provider
from app.services.relevance_provider import get_relevance_provider
from tests.test_event_extraction import ROOT, FakeEvents, FakeRelevance, meeting

pytestmark = pytest.mark.integration


class FakeDeltas:
    model = "synthetic-phase6-comparison"
    available = True
    calls = 0
    fail = False
    malformed = False
    hook = None
    missing_usage = False

    def compare(self, sources, context):
        self.calls += 1
        if self.hook:
            self.hook()
        if self.fail:
            raise StateError("DELTA_PROVIDER_FAILED", "Synthetic comparison outage", 503)
        target = next(r for r in context.records if r.kind == "REQUIREMENT_CHANGE")
        items = [
            {
                "id": str(s.id),
                "outcome": "CHANGE",
                "targetId": str(target.id),
                "reason": "Synthetic scope comparison; not confirmed.",
                "confidence": 0.9,
                "changes": [{"field": "phase", "proposedText": "1"}],
            }
            for s in sources
        ]
        if self.malformed:
            items[0]["targetId"] = str(uuid4())
        return DeltaProviderResult(
            ComparisonBatch.model_validate({"items": items}),
            None if self.missing_usage else 120,
            None if self.missing_usage else 60,
        )


@pytest.fixture
def delta_client(db_session):
    seed_demo(db_session)
    provider, events, relevance = FakeDeltas(), FakeEvents(), FakeRelevance()
    overrides = {
        get_database_session: lambda: db_session,
        get_delta_provider: lambda: provider,
        get_event_provider: lambda: events,
        get_relevance_provider: lambda: relevance,
    }
    app.dependency_overrides.update(overrides)
    try:
        with TestClient(app) as client:
            yield client, provider, events
    finally:
        for key in overrides:
            app.dependency_overrides.pop(key, None)


def extracted(client, count=1):
    path = meeting(client, ["SSO should move to Phase 1."] * count)
    for _ in range((count + 19) // 20):
        assert client.post(path + "/events").status_code == 200
    return path


def test_versioned_previous_values_citations_cache_and_no_canonical_writes(
    db_session, delta_client
):
    client, provider, _ = delta_client
    path = extracted(client)
    baseline = client.get(f"/api/v1/projects/{DEMO_PROJECT_ID}/workspace").json()

    def unlocked():
        assert not db_session.in_transaction()

    provider.hook = unlocked
    response = client.post(path + "/deltas")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["counts"] == {
        "eligible": 1,
        "processed": 1,
        "pending": 0,
        "same": 0,
        "change": 1,
        "new": 0,
        "unclear": 0,
    }
    item = data["items"][0]
    assert item["changes"] == [{"field": "phase", "previousValue": 2, "proposedText": "1"}]
    assert item["target"]["version"] == 1 and item["status"] == "CANDIDATE"
    assert item["evidence"][0]["quote"] == "SSO should move to Phase 1."
    assert data["run"]["apiCalls"] == data["run"]["usageReportedCalls"] == 1
    audits = db_session.scalar(select(func.count()).select_from(AuditEvent))
    assert client.get(path + "/deltas").json()["items"] == data["items"]
    assert client.post(path + "/deltas").json()["items"] == data["items"]
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


def test_prerequisites_and_body_rejection(delta_client):
    client, provider, _ = delta_client
    for texts, analyzed, expected in [
        ([], False, "NO_TRANSCRIPT"),
        (["SSO Phase 1."], False, "ANALYZE_RELEVANCE"),
        (["SSO Phase 1."], True, "EXTRACT_EVENTS"),
    ]:
        path = meeting(client, texts, analyze=analyzed)
        assert client.get(path + "/deltas").json()["prerequisite"] == expected
        assert client.post(path + "/deltas").status_code == 409
        assert client.post(path + "/deltas", json={"targetId": str(uuid4())}).status_code == 413
    assert provider.calls == 0


def test_missing_key_pending_recovery(delta_client):
    client, provider, _ = delta_client
    path = extracted(client)
    provider.available = False
    first = client.post(path + "/deltas").json()
    assert (
        first["run"]["lastError"] == "DELTA_PROVIDER_UNAVAILABLE"
        and first["counts"]["pending"] == 1
    )
    assert first["items"] == [] and provider.calls == 0
    provider.available = True
    assert client.post(path + "/deltas").json()["counts"]["processed"] == 1


@pytest.mark.parametrize(
    "mode,error", [("fail", "DELTA_PROVIDER_FAILED"), ("malformed", "DELTA_OUTPUT_INVALID")]
)
def test_failure_preserves_pending_and_retry(delta_client, mode, error):
    client, provider, _ = delta_client
    path = extracted(client)
    setattr(provider, mode, True)
    data = client.post(path + "/deltas").json()
    assert data["run"]["lastError"] == error and data["items"] == []
    assert data["counts"]["pending"] == 1 and not data["run"]["processing"]
    setattr(provider, mode, False)
    assert client.post(path + "/deltas").json()["counts"]["pending"] == 0


def test_bounded_batches_and_stable_partial_results(delta_client):
    client, provider, _ = delta_client
    path = extracted(client, 21)
    first = client.post(path + "/deltas").json()
    assert first["counts"]["processed"] == 20 and first["counts"]["pending"] == 1
    provider.fail = True
    failed = client.post(path + "/deltas").json()
    assert failed["items"] == first["items"] and failed["counts"]["pending"] == 1
    provider.fail = False
    final = client.post(path + "/deltas").json()
    assert final["counts"]["processed"] == 21 and provider.calls == 3
    assert [i["id"] for i in final["items"][:20]] == [i["id"] for i in first["items"]]


def test_zero_event_completion_and_partial_source_coverage(delta_client):
    client, provider, events = delta_client
    events.empty = True
    path = extracted(client)
    data = client.post(path + "/deltas").json()
    assert data["counts"]["eligible"] == data["counts"]["pending"] == 0
    assert data["run"] and provider.calls == 0
    events.empty = False
    path = meeting(client, ["SSO Phase 1."] * 21)
    client.post(path + "/events")
    data = client.post(path + "/deltas").json()
    assert data["sourcePending"] == 1 and data["counts"]["eligible"] == 20
    client.post(path + "/events")
    assert client.get(path + "/deltas").json()["counts"]["pending"] == 1


def test_context_change_during_request_discard_and_stale_read(db_session, delta_client):
    client, provider, _ = delta_client
    path = extracted(client)

    def changed():
        record = db_session.scalar(
            select(Requirement).where(Requirement.project_id == DEMO_PROJECT_ID)
        )
        record.version += 1
        record.phase = 3
        db_session.commit()

    provider.hook = changed
    data = client.post(path + "/deltas").json()
    assert data["items"] == [] and data["stale"]
    assert data["run"]["lastError"] == "DELTA_CONTEXT_CHANGED"
    assert client.post(path + "/deltas").status_code == 409
    provider.hook = None
    client.post(path + "/relevance")
    client.post(path + "/events")
    refreshed = client.post(path + "/deltas").json()
    assert not refreshed["stale"] and refreshed["items"][0]["changes"][0]["previousValue"] == 3


def test_candidate_evidence_change_during_request_discard(db_session, delta_client):
    client, provider, _ = delta_client
    path = extracted(client)

    def changed():
        candidate = db_session.scalar(select(ProjectEventCandidate))
        candidate.title = "Changed interpretation"
        db_session.commit()

    provider.hook = changed
    data = client.post(path + "/deltas").json()
    assert data["items"] == [] and data["run"]["lastError"] == "DELTA_INPUT_CHANGED"


def test_active_and_expired_leases(db_session, delta_client):
    client, provider, _ = delta_client
    path = extracted(client)
    provider.available = False
    client.post(path + "/deltas")
    run = db_session.scalar(select(DeltaComparisonRun))
    run.processing_token = uuid4()
    run.processing_started_at = datetime.now(UTC)
    db_session.commit()
    provider.available = True
    assert client.post(path + "/deltas").status_code == 409
    run.processing_started_at = datetime.now(UTC) - timedelta(seconds=60)
    db_session.commit()
    assert client.post(path + "/deltas").json()["counts"]["processed"] == 1


def test_superseded_lease_discards_batch(db_session, delta_client):
    client, provider, _ = delta_client
    path = extracted(client)

    def superseded():
        run = db_session.scalar(select(DeltaComparisonRun))
        run.processing_token = uuid4()
        db_session.commit()

    provider.hook = superseded
    assert client.post(path + "/deltas").status_code == 409
    assert db_session.scalar(select(func.count()).select_from(ProjectDelta)) == 0


def test_audit_failure_rolls_back_all_comparisons(db_session, delta_client, monkeypatch):
    client, provider, _ = delta_client
    path = extracted(client)
    original = AuditRepository.append

    def fail(self, event):
        if event.action == "DELTA_COMPARISON_FINISHED":
            raise RuntimeError("Synthetic audit outage")
        return original(self, event)

    monkeypatch.setattr(AuditRepository, "append", fail)
    with pytest.raises(RuntimeError):
        client.post(path + "/deltas")
    assert db_session.scalar(select(func.count()).select_from(ProjectDelta)) == 0


def test_scope_filters_and_page_validation(delta_client):
    client, _, _ = delta_client
    path = extracted(client)
    client.post(path + "/deltas")
    assert client.get(path + "/deltas?outcome=SAME").json()["filteredCount"] == 0
    assert client.get(path + "/deltas?outcome=CHANGE").json()["filteredCount"] == 1
    for query in ["page=0", "page=401", "outcome=CONFIRMED"]:
        assert client.get(path + "/deltas?" + query).status_code == 422
    assert (
        client.get(path.replace(str(DEMO_PROJECT_ID), str(uuid4())) + "/deltas").status_code == 404
    )
    assert client.get(ROOT + f"/{uuid4()}/deltas").status_code == 404
    assert (
        client.post(path.replace(str(DEMO_PROJECT_ID), str(uuid4())) + "/deltas").status_code == 404
    )


def test_meeting_deletion_cascades_comparisons(db_session, delta_client):
    client, _, _ = delta_client
    path = extracted(client)
    client.post(path + "/deltas")
    assert client.delete(path).status_code == 204
    assert db_session.scalar(select(func.count()).select_from(ProjectDelta)) == 0
    assert db_session.scalar(select(func.count()).select_from(DeltaComparisonRun)) == 0


def test_database_rejects_cross_candidate_and_confirmed_status(db_session, delta_client):
    client, _, _ = delta_client
    path = extracted(client)
    client.post(path + "/deltas")
    delta = db_session.scalar(select(ProjectDelta))
    for changes in [{"status": "CONFIRMED"}, {"candidate_id": uuid4()}, {"extraction_id": uuid4()}]:
        with pytest.raises(IntegrityError), db_session.begin_nested():
            for field, value in changes.items():
                setattr(delta, field, value)
            db_session.flush()


def test_context_versions_confirmed_decisions_and_truncation(db_session, delta_client):
    context, first = comparison_context(db_session, DEMO_PROJECT_ID)
    assert context.complete and all(r.version >= 1 for r in context.records)
    assert all(
        r.values["decisionStatus"] == "CONFIRMED" for r in context.records if r.kind == "DECISION"
    )
    record = db_session.scalar(select(Requirement).where(Requirement.project_id == DEMO_PROJECT_ID))
    record.description = "x" * 21000
    record.version += 1
    db_session.flush()
    context, second = comparison_context(db_session, DEMO_PROJECT_ID)
    assert (
        not context.complete
        and second != first
        and record.id not in {r.id for r in context.records}
    )


def test_missing_usage_remains_unknown(delta_client):
    client, provider, _ = delta_client
    provider.missing_usage = True
    path = extracted(client)
    data = client.post(path + "/deltas").json()
    assert data["run"]["usageReportedCalls"] == data["run"]["inputTokens"] == 0
