import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.dependencies import get_database_session
from app.db.models import AuditEvent, Project, ProjectMember, RelevanceAnalysis, UtteranceRelevance
from app.domain.manual_state import StateError
from app.domain.relevance import ClassificationBatch, SegmentClassification
from app.main import app
from app.repositories.audit import AuditRepository
from app.services.demo_seed import DEMO_PROJECT_ID, seed_demo
from app.services.project_access import LOCAL_DEMO_ACTOR_ID
from app.services.relevance_provider import ProviderResult, get_relevance_provider

ROOT = f"/api/v1/projects/{DEMO_PROJECT_ID}/meetings"


class FakeRelevance:
    model = "synthetic-relevance-model"
    available = True
    calls = 0
    fail = False
    malformed = False
    confidence = 0.9
    hook = None
    contexts = None

    def classify(self, segments, context):
        self.calls += 1
        self.contexts = context
        if self.hook:
            self.hook()
        if self.fail:
            raise StateError("RELEVANCE_PROVIDER_FAILED", "Synthetic error", 503)
        ids = [s.id for s in segments]
        if self.malformed:
            ids = [uuid4()]
        return ProviderResult(
            ClassificationBatch(
                items=[
                    SegmentClassification(
                        id=id,
                        relevant=True,
                        confidence=self.confidence,
                        reason="Selected project delivery discussion.",
                        relatedEntityTypes=["risk"],
                    )
                    for id in ids
                ]
            ),
            100,
            50,
        )


@pytest.fixture
def relevance_client(db_session):
    seed_demo(db_session)
    provider = FakeRelevance()
    app.dependency_overrides[get_database_session] = lambda: db_session
    app.dependency_overrides[get_relevance_provider] = lambda: provider
    try:
        with TestClient(app) as client:
            yield client, provider
    finally:
        app.dependency_overrides.pop(get_database_session, None)
        app.dependency_overrides.pop(get_relevance_provider, None)


def meeting(client, texts):
    m = client.post(ROOT, json={"title": "QA relevance"}).json()
    path = f"{ROOT}/{m['id']}"
    response = client.post(
        path + "/transcript",
        params={"filename": "relevance.json"},
        content=json.dumps([{"text": s} for s in texts]).encode(),
    )
    assert response.status_code == 201, response.text
    return path


pytestmark = pytest.mark.integration


def test_metrics_rules_ai_cache_audit_and_baseline_preservation(db_session, relevance_client):
    client, provider = relevance_client
    baseline = client.get(f"/api/v1/projects/{DEMO_PROJECT_ID}/workspace").json()
    path = meeting(
        client,
        [
            "I went hiking this weekend.",
            "Move the launch to November 10.",
            "The login button fails QA.",
        ],
    )
    empty = client.get(path + "/relevance").json()
    assert empty["analysis"] is None and empty["counts"]["pending"] == 3
    result = client.post(path + "/relevance").json()
    assert result["counts"] == {
        "total": 3,
        "analyzed": 3,
        "relevant": 2,
        "ignored": 1,
        "uncertain": 0,
        "pending": 0,
    }
    assert result["ignoredPercent"] == 33 and result["analysis"]["apiCalls"] == 1
    assert (
        result["analysis"]["inputTokens"] == 100 and result["analysis"]["usageReportedCalls"] == 1
    )
    assert len(result["items"]) == 3 and result["items"][0]["outcome"] == "IGNORED"
    count = db_session.scalar(select(func.count()).select_from(AuditEvent))
    again = client.post(path + "/relevance").json()
    assert again["analysis"]["id"] == result["analysis"]["id"] and provider.calls == 1
    assert db_session.scalar(select(func.count()).select_from(AuditEvent)) == count
    after = client.get(f"/api/v1/projects/{DEMO_PROJECT_ID}/workspace").json()
    for key in [
        "requirements",
        "decisions",
        "commitments",
        "risks",
        "milestones",
        "dependencies",
        "questions",
        "members",
    ]:
        assert baseline[key] == after[key]
    assert all(
        f.type.value != "decision" or "provisional" not in f.description
        for f in provider.contexts.facts
    )


def test_missing_provider_is_partial_without_false_ignored_count(relevance_client):
    client, provider = relevance_client
    provider.available = False
    path = meeting(client, ["Good morning.", "SSO stays in Phase 2.", "The login button fails QA."])
    result = client.post(path + "/relevance").json()
    assert result["counts"]["analyzed"] == 2 and result["counts"]["pending"] == 1
    assert result["counts"]["ignored"] == 1 and result["analysis"]["apiCalls"] == 0
    assert result["analysis"]["lastError"] == "RELEVANCE_UNAVAILABLE"
    provider.available = True
    recovered = client.post(path + "/relevance").json()
    assert recovered["counts"]["pending"] == 0 and provider.calls == 1


@pytest.mark.parametrize("mode", ["fail", "malformed"])
def test_failed_or_invalid_batch_saves_no_model_classifications(relevance_client, mode):
    client, provider = relevance_client
    setattr(provider, mode, True)
    path = meeting(
        client, ["Good morning.", "The login button fails QA.", "This change needs approval."]
    )
    result = client.post(path + "/relevance").json()
    assert (
        result["counts"]["analyzed"] == 1
        and result["counts"]["ignored"] == 1
        and result["counts"]["pending"] == 2
    )
    assert result["analysis"]["lastError"] in {"RELEVANCE_INVALID", "RELEVANCE_PROVIDER_FAILED"}
    assert len(result["items"]) == 1
    setattr(provider, mode, False)
    assert client.post(path + "/relevance").json()["counts"]["analyzed"] == 3


def test_low_confidence_never_counts_as_ignored_or_relevant(relevance_client):
    client, provider = relevance_client
    provider.confidence = 0.5
    result = client.post(meeting(client, ["The login button fails QA."]) + "/relevance").json()
    assert result["counts"] == {
        "total": 1,
        "analyzed": 1,
        "relevant": 0,
        "ignored": 0,
        "uncertain": 1,
        "pending": 0,
    }
    assert result["items"][0]["outcome"] == "UNCERTAIN"


def test_no_transcript_and_invalid_filters_fail_without_analysis(db_session, relevance_client):
    client, _ = relevance_client
    m = client.post(ROOT, json={"title": "No transcript"}).json()
    path = f"{ROOT}/{m['id']}/relevance"
    assert client.post(path).status_code == 409
    assert client.get(path, params={"page": 0}).status_code == 422
    assert client.get(path, params={"outcome": "FAKE"}).status_code == 422
    assert db_session.scalar(select(func.count()).select_from(RelevanceAnalysis)) == 0


def test_context_edit_marks_stale_then_creates_fresh_analysis(relevance_client):
    client, provider = relevance_client
    path = meeting(client, ["SSO stays in Phase 2."])
    first = client.post(path + "/relevance").json()
    client.post(
        f"/api/v1/projects/{DEMO_PROJECT_ID}/state/requirements",
        json={"title": "New current requirement", "status": "ACTIVE", "phase": 1},
    )
    assert client.get(path + "/relevance").json()["stale"]
    second = client.post(path + "/relevance").json()
    assert not second["stale"] and first["analysis"]["id"] != second["analysis"]["id"]
    assert provider.calls == 0


def test_context_changed_during_ai_discards_stale_batch(relevance_client):
    client, provider = relevance_client
    path = meeting(client, ["The login button fails QA."])
    provider.hook = lambda: client.post(
        f"/api/v1/projects/{DEMO_PROJECT_ID}/state/risks",
        json={"title": "New risk", "status": "OPEN", "severity": "HIGH"},
    )
    result = client.post(path + "/relevance").json()
    assert result["stale"] and result["analysis"]["lastError"] == "RELEVANCE_CONTEXT_CHANGED"
    assert result["counts"]["pending"] == 1 and result["items"] == []


def test_busy_lease_and_explicit_expired_lease_recovery(db_session, relevance_client):
    client, provider = relevance_client
    provider.available = False
    path = meeting(client, ["The login button fails QA."])
    initial = client.post(path + "/relevance").json()
    run = db_session.get(RelevanceAnalysis, initial["analysis"]["id"])
    run.processing_token = uuid4()
    run.processing_started_at = datetime.now(UTC)
    db_session.flush()
    provider.available = True
    assert client.post(path + "/relevance").status_code == 409
    run.processing_started_at = datetime.now(UTC) - timedelta(seconds=50)
    db_session.flush()
    result = client.post(path + "/relevance").json()
    assert result["counts"]["pending"] == 0 and provider.calls == 1


def test_analysis_scope_and_cascade_with_retained_audit(db_session, relevance_client):
    client, _ = relevance_client
    path = meeting(client, ["Good morning.", "SSO stays in Phase 2."])
    result = client.post(path + "/relevance").json()
    other = Project(name="Other")
    db_session.add(other)
    db_session.flush()
    hidden = f"/api/v1/projects/{other.id}/meetings/{path.rsplit('/', 1)[-1]}/relevance"
    assert client.get(hidden).status_code == 404 and client.post(hidden).status_code == 404
    db_session.add(ProjectMember(project_id=other.id, user_id=LOCAL_DEMO_ACTOR_ID, role="QA"))
    db_session.flush()
    assert client.get(hidden).status_code == 404 and client.post(hidden).status_code == 404
    assert client.delete(path).status_code == 204
    assert client.get(path + "/relevance").status_code == 404
    assert db_session.scalar(select(func.count()).select_from(RelevanceAnalysis)) == 0
    assert db_session.scalar(select(func.count()).select_from(UtteranceRelevance)) == 0
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.entity_id == result["analysis"]["id"])
        )
        == 1
    )


def test_initial_audit_failure_rolls_back_analysis_and_rule_results(
    db_session, relevance_client, monkeypatch
):
    client, _ = relevance_client
    path = meeting(client, ["Good morning."])

    def fail(*args):
        raise RuntimeError("Synthetic audit failure")

    monkeypatch.setattr(AuditRepository, "append", fail)
    with pytest.raises(RuntimeError):
        client.post(path + "/relevance")
    assert db_session.scalar(select(func.count()).select_from(RelevanceAnalysis)) == 0
    assert db_session.scalar(select(func.count()).select_from(UtteranceRelevance)) == 0


def test_rule_results_pagination_filter_counts_and_source_order(relevance_client):
    client, provider = relevance_client
    path = meeting(
        client, ["Good morning." if i % 2 else "SSO stays in Phase 2." for i in range(205)]
    )
    result = client.post(path + "/relevance").json()
    assert (
        result["counts"]["analyzed"] == 205
        and result["counts"]["relevant"] == 103
        and result["counts"]["ignored"] == 102
    )
    assert len(result["items"]) == 100 and provider.calls == 0
    last = client.get(path + "/relevance", params={"page": 3}).json()
    assert [x["sequence"] for x in last["items"]] == list(range(200, 205))
    ignored = client.get(path + "/relevance", params={"outcome": "IGNORED", "page": 2}).json()
    assert ignored["filteredCount"] == 102 and len(ignored["items"]) == 2


def test_ai_batches_are_bounded_and_continue_explicitly(relevance_client):
    client, provider = relevance_client
    path = meeting(client, ["The login button fails QA."] * 45)
    first = client.post(path + "/relevance").json()
    assert first["counts"]["analyzed"] == 40 and first["counts"]["pending"] == 5
    second = client.post(path + "/relevance").json()
    assert (
        second["counts"]["analyzed"] == 45
        and second["analysis"]["apiCalls"] == 2
        and provider.calls == 2
    )


def test_selected_owned_deployment_context_changes_relevance(db_session, relevance_client):
    from app.db.models import User

    client, provider = relevance_client
    raj = User(display_name="Raj", email="raj-relevance@example.test")
    db_session.add(raj)
    db_session.flush()
    db_session.add(ProjectMember(project_id=DEMO_PROJECT_ID, user_id=raj.id, role="TECH_LEAD"))
    db_session.flush()
    commitment = client.post(
        f"/api/v1/projects/{DEMO_PROJECT_ID}/state/commitments",
        json={
            "title": "Critical Friday deployment",
            "status": "OPEN",
            "ownerId": str(raj.id),
            "dueDate": "2026-10-09",
        },
    ).json()
    path = meeting(client, ["Raj is off Friday."])
    first = client.post(path + "/relevance").json()
    assert first["counts"]["relevant"] == 1 and provider.calls == 0
    update = client.put(
        f"/api/v1/projects/{DEMO_PROJECT_ID}/state/commitments/{commitment['id']}",
        json={
            "expectedVersion": commitment["version"],
            "values": {
                "title": commitment["title"],
                "status": "DONE",
                "ownerId": str(raj.id),
                "dueDate": "2026-10-09",
            },
        },
    )
    assert update.status_code == 200
    assert client.get(path + "/relevance").json()["stale"]
    second = client.post(path + "/relevance").json()
    assert second["counts"]["ignored"] == 1 and provider.calls == 0


def test_rule_only_analysis_accepts_full_transcript_bound(relevance_client):
    client, provider = relevance_client
    path = meeting(client, ["Good morning."] * 10000)
    result = client.post(path + "/relevance").json()
    assert result["counts"]["total"] == result["counts"]["ignored"] == 10000
    assert result["counts"]["pending"] == 0 and provider.calls == 0
    last = client.get(path + "/relevance", params={"page": 100}).json()
    assert last["items"][-1]["sequence"] == 9999


def test_capped_context_is_explicit_and_fingerprinted(db_session, relevance_client):
    from app.db.models import Requirement
    from app.services.relevance_context import project_context

    client, _ = relevance_client
    _, before = project_context(db_session, DEMO_PROJECT_ID)
    for i in range(65):
        db_session.add(
            Requirement(
                project_id=DEMO_PROJECT_ID,
                title=f"Extra requirement {i}",
                status="ACTIVE",
                phase=1,
                description="x" * 500,
            )
        )
    db_session.flush()
    context, after = project_context(db_session, DEMO_PROJECT_ID)
    assert not context.complete and len(context.facts) <= 60
    assert sum(len(f.model_dump_json(by_alias=True)) for f in context.facts) <= 12000
    assert before != after


def test_final_audit_failure_rolls_back_model_results_and_releases_lease(
    db_session, relevance_client, monkeypatch
):
    client, provider = relevance_client
    path = meeting(client, ["Good morning.", "The login button fails QA."])
    original = AuditRepository.append

    def fail_model_event(repository, event):
        if event.payload.get("aiSegments"):
            raise RuntimeError("Synthetic final audit failure")
        return original(repository, event)

    monkeypatch.setattr(AuditRepository, "append", fail_model_event)
    with pytest.raises(RuntimeError):
        client.post(path + "/relevance")
    saved = client.get(path + "/relevance").json()
    assert saved["counts"]["ignored"] == 1 and saved["counts"]["pending"] == 1
    assert len(saved["items"]) == 1 and not saved["analysis"]["processing"]
    assert saved["analysis"]["lastError"] == "RELEVANCE_SAVE_FAILED"
    monkeypatch.setattr(AuditRepository, "append", original)
    assert client.post(path + "/relevance").json()["counts"]["pending"] == 0
