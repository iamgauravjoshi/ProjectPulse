from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.dependencies import get_database_session
from app.db.models import (
    AuditEvent,
    Dependency,
    Milestone,
    Project,
    ProjectMember,
    Requirement,
    User,
)
from app.main import app
from app.repositories.audit import AuditRepository
from app.services.demo_seed import DEMO_PROJECT_ID, demo_id, seed_demo
from app.services.project_access import LOCAL_DEMO_ACTOR_ID

pytestmark = pytest.mark.integration
ROOT = f"/api/v1/projects/{DEMO_PROJECT_ID}/state"
EXAMPLES = {
    "requirements": {"title": "New SSO scope", "phase": 2},
    "decisions": {"title": "New design choice", "decisionStatus": "CONFIRMED"},
    "milestones": {"title": "New checkpoint", "date": "2026-11-12"},
    "risks": {"title": "New delivery risk", "severity": "HIGH"},
    "commitments": {"title": "New delivery", "ownerId": str(demo_id("john"))},
    "dependencies": {"title": "New approval", "blockedMilestoneId": str(demo_id("launch"))},
}


@pytest.fixture
def state_client(db_session):
    seed_demo(db_session)
    app.dependency_overrides[get_database_session] = lambda: db_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_database_session, None)


def audit_count(session):
    return session.scalar(select(func.count()).select_from(AuditEvent))


@pytest.mark.parametrize("kind", EXAMPLES)
def test_all_six_record_types_create_read_edit_delete_and_audit(db_session, state_client, kind):
    response = state_client.post(f"{ROOT}/{kind}", json=EXAMPLES[kind])
    assert response.status_code == 201, response.text
    record = response.json()
    assert record["sourceKind"] == "MANUAL" and record["version"] == 1
    assert record["projectId"] == str(DEMO_PROJECT_ID)
    if kind == "decisions":
        assert record["confirmedAt"] and record["madeBy"] == str(LOCAL_DEMO_ACTOR_ID)
    if kind == "commitments":
        assert record["saidBy"] is None and record["dueDate"] is None
    url = f"{ROOT}/{kind}/{record['id']}"
    assert state_client.get(url).json() == record
    assert any(row["id"] == record["id"] for row in state_client.get(f"{ROOT}/{kind}").json())
    revised = {**EXAMPLES[kind], "title": "Edited human baseline"}
    response = state_client.put(url, json={"expectedVersion": 1, "values": revised})
    assert response.status_code == 200, response.text
    assert response.json()["version"] == 2
    assert response.json()["title"] == "Edited human baseline"
    assert state_client.delete(f"{url}?expectedVersion=2").status_code == 204
    assert state_client.get(url).status_code == 404
    events = db_session.scalars(
        select(AuditEvent)
        .where(AuditEvent.entity_id == record["id"])
        .order_by(AuditEvent.created_at, AuditEvent.id)
    ).all()
    assert {event.action for event in events} == {
        "MANUAL_STATE_CREATED",
        "MANUAL_STATE_UPDATED",
        "MANUAL_STATE_DELETED",
    }
    assert all(event.actor_id == LOCAL_DEMO_ACTOR_ID for event in events)
    changed = next(event for event in events if event.action == "MANUAL_STATE_UPDATED")
    assert changed.payload["before"]["version"] == 1 and changed.payload["after"]["version"] == 2


@pytest.mark.parametrize(
    "kind, values",
    [
        ("requirements", {"title": " "}),
        ("requirements", {"title": "a" * 241}),
        ("requirements", {"title": "Valid", "phase": 0}),
        ("requirements", {"title": "Valid", "phase": True}),
        ("requirements", {"title": "Valid", "phase": "2"}),
        ("requirements", {"title": "Valid", "status": "CONFIRMED"}),
        ("requirements", {"title": "Valid", "description": "a" * 20_001}),
        ("requirements", {"title": "Valid", "sourceKind": "SEED"}),
        ("requirements", {"title": "Valid", "projectId": str(uuid4())}),
        ("requirements", {"title": "Valid", "actorId": str(uuid4())}),
        ("requirements", {"title": "Valid", "version": 100}),
        ("decisions", {"title": "Valid", "decisionStatus": "APPROVED"}),
        ("decisions", {"title": "Valid", "confirmedAt": "2026-01-01T00:00:00Z"}),
        ("milestones", {"title": "Valid", "date": "2026-02-30"}),
        ("milestones", {"title": "Valid"}),
        ("risks", {"title": "Valid", "severity": "SEVERE"}),
        ("commitments", {"title": "Valid", "saidBy": str(demo_id("john"))}),
        ("commitments", {"title": "Valid", "confidence": 1}),
        ("dependencies", {"title": "Valid", "ownerId": "bad"}),
    ],
)
def test_invalid_or_browser_owned_metadata_cannot_write(db_session, state_client, kind, values):
    before = audit_count(db_session)
    assert state_client.post(f"{ROOT}/{kind}", json=values).status_code == 422
    assert audit_count(db_session) == before


def test_stale_edit_and_delete_preserve_newer_values_and_audit(db_session, state_client):
    url = f"{ROOT}/requirements/{demo_id('sso')}"
    revised = {"title": "Human scope", "phase": 1}
    assert state_client.put(url, json={"expectedVersion": 1, "values": revised}).status_code == 200
    before = audit_count(db_session)
    response = state_client.put(url, json={"expectedVersion": 1, "values": {**revised, "phase": 3}})
    assert response.status_code == 409 and response.json()["error"]["code"] == "STALE_VERSION"
    assert state_client.delete(f"{url}?expectedVersion=1").status_code == 409
    assert state_client.get(url).json()["phase"] == 1
    assert audit_count(db_session) == before


@pytest.mark.parametrize("method", ["get", "post", "put", "delete"])
def test_inaccessible_and_missing_projects_are_equivalent(db_session, state_client, method):
    hidden = Project(name="Outside workspace")
    db_session.add(hidden)
    db_session.flush()

    def request(project_id):
        url = f"/api/v1/projects/{project_id}/state/requirements"
        if method == "post":
            return state_client.post(url, json={"title": "Unauthorized"})
        if method == "get":
            return state_client.get(url)
        url += f"/{uuid4()}"
        if method == "put":
            return state_client.put(
                url, json={"expectedVersion": 1, "values": {"title": "Unauthorized"}}
            )
        return state_client.delete(f"{url}?expectedVersion=1")

    first, second = request(hidden.id), request(uuid4())
    assert first.status_code == second.status_code == 404
    assert first.json() == second.json()
    assert audit_count(db_session) == 1


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_other_project_record_id_cannot_be_read_or_changed(db_session, state_client, method):
    other = Project(name="Other assigned workspace")
    db_session.add(other)
    db_session.flush()
    db_session.add(
        ProjectMember(project_id=other.id, user_id=LOCAL_DEMO_ACTOR_ID, role="PRODUCT_OWNER")
    )
    record = Requirement(project_id=other.id, title="Other requirement")
    db_session.add(record)
    db_session.flush()
    url = f"{ROOT}/requirements/{record.id}"
    if method == "get":
        response = state_client.get(url)
    elif method == "put":
        response = state_client.put(
            url, json={"expectedVersion": 1, "values": {"title": "Bad edit"}}
        )
    else:
        response = state_client.delete(f"{url}?expectedVersion=1")
    assert response.status_code == 404
    assert db_session.get(Requirement, record.id).title == "Other requirement"
    assert audit_count(db_session) == 1


@pytest.mark.parametrize(
    "kind, field",
    [
        ("commitments", "ownerId"),
        ("commitments", "dependencyId"),
        ("dependencies", "ownerId"),
        ("dependencies", "blockedMilestoneId"),
    ],
)
def test_unknown_references_are_rejected(db_session, state_client, kind, field):
    response = state_client.post(
        f"{ROOT}/{kind}", json={"title": "Invalid link", field: str(uuid4())}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REFERENCE"
    assert audit_count(db_session) == 1


def test_dependency_delete_is_blocked_until_commitment_is_unlinked(db_session, state_client):
    dependency = state_client.post(
        f"{ROOT}/dependencies", json={"title": "Human dependency"}
    ).json()
    commitment = state_client.post(
        f"{ROOT}/commitments", json={"title": "Human delivery", "dependencyId": dependency["id"]}
    ).json()
    before = audit_count(db_session)
    url = f"{ROOT}/dependencies/{dependency['id']}?expectedVersion=1"
    rejected = state_client.delete(url)
    assert rejected.status_code == 409 and rejected.json()["error"]["code"] == "RECORD_IN_USE"
    assert audit_count(db_session) == before
    assert (
        state_client.put(
            f"{ROOT}/commitments/{commitment['id']}",
            json={
                "expectedVersion": 1,
                "values": {"title": "Human delivery", "dependencyId": None},
            },
        ).status_code
        == 200
    )
    assert state_client.delete(url).status_code == 204


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_audit_failure_rolls_back_canonical_mutation(
    db_session, state_client, monkeypatch, operation
):
    def fail(self, event):
        raise RuntimeError("Simulated audit failure")

    monkeypatch.setattr(AuditRepository, "append", fail)
    with pytest.raises(RuntimeError, match="Simulated audit failure"):
        if operation == "create":
            state_client.post(f"{ROOT}/requirements", json={"title": "Must roll back"})
        elif operation == "update":
            state_client.put(
                f"{ROOT}/requirements/{demo_id('sso')}",
                json={"expectedVersion": 1, "values": {"title": "Must roll back", "phase": 1}},
            )
        else:
            state_client.delete(f"{ROOT}/requirements/{demo_id('sso')}?expectedVersion=1")
    assert db_session.scalar(select(func.count()).select_from(Requirement)) == 1
    assert db_session.get(Requirement, demo_id("sso")).title == "Single sign-on"
    assert db_session.get(Requirement, demo_id("sso")).phase == 2
    assert audit_count(db_session) == 1


@pytest.mark.parametrize(
    "kind, field",
    [
        ("commitments", "ownerId"),
        ("commitments", "dependencyId"),
        ("dependencies", "ownerId"),
        ("dependencies", "blockedMilestoneId"),
    ],
)
def test_existing_other_project_references_cannot_be_linked(db_session, state_client, kind, field):
    other = Project(name="Hidden source")
    owner = User(display_name="Other owner", email="other-owner@example.test")
    db_session.add_all([other, owner])
    db_session.flush()
    db_session.add(ProjectMember(project_id=other.id, user_id=owner.id, role="TECH_LEAD"))
    milestone = Milestone(project_id=other.id, title="Hidden date", milestone_date="2026-12-01")
    dependency = Dependency(project_id=other.id, title="Hidden dependency")
    db_session.add_all([milestone, dependency])
    db_session.flush()
    reference = (
        owner.id
        if field == "ownerId"
        else dependency.id
        if field == "dependencyId"
        else milestone.id
    )
    response = state_client.post(
        f"{ROOT}/{kind}", json={"title": "Invalid link", field: str(reference)}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REFERENCE"
    assert audit_count(db_session) == 1


def test_human_confirmation_is_not_inferred_and_reclassification_removes_timestamp(state_client):
    decision = state_client.post(
        f"{ROOT}/decisions", json={"title": "A proposal", "decisionStatus": "PROPOSAL"}
    ).json()
    assert decision["confirmedAt"] is None
    response = state_client.put(
        f"{ROOT}/decisions/{decision['id']}",
        json={
            "expectedVersion": 1,
            "values": {"title": "A confirmed baseline", "decisionStatus": "CONFIRMED"},
        },
    )
    assert response.json()["confirmedAt"] is not None
    response = state_client.put(
        f"{ROOT}/decisions/{decision['id']}",
        json={
            "expectedVersion": 2,
            "values": {"title": "Requires review", "decisionStatus": "REVIEW_REQUIRED"},
        },
    )
    assert response.json()["confirmedAt"] is None
