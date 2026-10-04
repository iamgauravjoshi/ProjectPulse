from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_database_session
from app.db.models import AuditEvent, Meeting, MeetingParticipant, Project, ProjectMember, Utterance
from app.main import app
from app.repositories.audit import AuditRepository
from app.services.demo_seed import DEMO_PROJECT_ID, seed_demo
from app.services.project_access import LOCAL_DEMO_ACTOR_ID

ROOT = f"/api/v1/projects/{DEMO_PROJECT_ID}/meetings"


@pytest.fixture
def client(db_session):
    seed_demo(db_session)
    app.dependency_overrides[get_database_session] = lambda: db_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_database_session, None)


@pytest.mark.integration
def test_meeting_participants_repeated_names_and_audited_cascade(db_session, client):
    before = client.get(f"/api/v1/projects/{DEMO_PROJECT_ID}/workspace").json()
    result = client.post(ROOT, json={"title": "Planning", "startedAt": "2026-10-04T09:00:00+05:30"})
    assert result.status_code == 201
    meeting = result.json()
    path = f"{ROOT}/{meeting['id']}"
    for key in ["sarah-1", "sarah-2"]:
        r = client.post(path + "/participants", json={"displayName": "Sarah", "speakerKey": key})
        assert r.status_code == 201, r.text
    assert (
        client.post(
            path + "/participants", json={"displayName": "Different", "speakerKey": "sarah-1"}
        ).status_code
        == 409
    )
    detail = client.get(path).json()
    assert len(detail["participants"]) == 2 and detail["utterances"] == []
    assert detail["participants"][0]["id"] != detail["participants"][1]["id"]
    db_session.add(
        Utterance(
            project_id=DEMO_PROJECT_ID,
            meeting_id=meeting["id"],
            participant_id=detail["participants"][0]["id"],
            sequence=0,
            speaker_label="Sarah",
            text="Evidence",
            timestamp_ms=None,
            confidence=None,
        )
    )
    db_session.flush()
    assert len(client.get(path).json()["utterances"]) == 1
    assert len(client.get(ROOT).json()) == 1
    after = client.get(f"/api/v1/projects/{DEMO_PROJECT_ID}/workspace").json()
    for key in ["requirements", "decisions", "milestones", "risks", "commitments", "dependencies"]:
        assert before[key] == after[key]
    assert client.delete(path).status_code == 204
    assert client.get(path).status_code == 404
    assert db_session.scalar(select(func.count()).select_from(MeetingParticipant)) == 0
    assert db_session.scalar(select(func.count()).select_from(Utterance)) == 0
    events = db_session.scalars(
        select(AuditEvent).where(AuditEvent.entity_id == meeting["id"])
    ).all()
    assert len(events) == 4 and all(x.actor_id == LOCAL_DEMO_ACTOR_ID for x in events)


@pytest.mark.integration
@pytest.mark.parametrize(
    "values",
    [
        {"title": " "},
        {"title": "x", "createdBy": str(uuid4())},
        {"title": "x", "startedAt": "2026-10-04T09:00:00"},
    ],
)
def test_invalid_meeting_fields_cannot_write(client, values):
    assert client.post(ROOT, json=values).status_code == 422
    assert client.get(ROOT).json() == []


@pytest.mark.integration
def test_participant_member_and_project_isolation(db_session, client):
    meeting = client.post(ROOT, json={"title": "Scoped"}).json()
    path = f"{ROOT}/{meeting['id']}"
    assert (
        client.post(
            path + "/participants",
            json={"displayName": "Unknown", "speakerKey": "a", "userId": str(uuid4())},
        ).status_code
        == 422
    )
    assert (
        client.post(
            path + "/participants",
            json={"displayName": "Sarah", "speakerKey": "a", "userId": str(LOCAL_DEMO_ACTOR_ID)},
        ).status_code
        == 201
    )
    hidden = Project(name="Other")
    db_session.add(hidden)
    db_session.flush()
    hidden_path = f"/api/v1/projects/{hidden.id}/meetings/{meeting['id']}"
    assert client.get(hidden_path).status_code == 404
    assert (
        client.post(
            f"/api/v1/projects/{hidden.id}/meetings", json={"title": "No access"}
        ).status_code
        == 404
    )
    db_session.add(
        ProjectMember(project_id=hidden.id, user_id=LOCAL_DEMO_ACTOR_ID, role="PRODUCT_OWNER")
    )
    db_session.flush()
    assert client.get(hidden_path).status_code == 404
    assert client.delete(hidden_path).status_code == 404
    assert (
        client.post(
            hidden_path + "/participants", json={"displayName": "No", "speakerKey": "a"}
        ).status_code
        == 404
    )


@pytest.mark.integration
@pytest.mark.parametrize("operation", ["create", "participant", "delete"])
def test_meeting_audit_failure_rolls_back(db_session, client, monkeypatch, operation):
    meeting = client.post(ROOT, json={"title": "Before"}).json() if operation != "create" else None

    def fail(*args, **kwargs):
        raise RuntimeError("audit failure")

    monkeypatch.setattr(AuditRepository, "append", fail)
    with pytest.raises(RuntimeError):
        if operation == "create":
            client.post(ROOT, json={"title": "Rollback"})
        elif operation == "participant":
            client.post(
                f"{ROOT}/{meeting['id']}/participants",
                json={"displayName": "Sarah", "speakerKey": "a"},
            )
        else:
            client.delete(f"{ROOT}/{meeting['id']}")
    assert db_session.scalar(select(func.count()).select_from(Meeting)) == (
        0 if operation == "create" else 1
    )
    assert db_session.scalar(select(func.count()).select_from(MeetingParticipant)) == 0


@pytest.mark.integration
@pytest.mark.parametrize(
    "values",
    [
        {"sequence": -1},
        {"timestamp_ms": -1},
        {"confidence": 1.1},
        {"text": " "},
        {"end_ms": 2, "timestamp_ms": None},
    ],
)
def test_utterance_database_bounds(db_session, client, values):
    meeting = client.post(ROOT, json={"title": "Bounds"}).json()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            Utterance(
                project_id=DEMO_PROJECT_ID,
                meeting_id=meeting["id"],
                speaker_label="Unknown speaker",
                **{"text": "Evidence", "sequence": 0, **values},
            )
        )
        db_session.flush()


@pytest.mark.integration
def test_utterance_cannot_reference_participant_in_another_meeting(db_session, client):
    a = client.post(ROOT, json={"title": "A"}).json()
    b = client.post(ROOT, json={"title": "B"}).json()
    speaker = client.post(
        f"{ROOT}/{a['id']}/participants", json={"displayName": "Sarah", "speakerKey": "a"}
    ).json()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            Utterance(
                project_id=DEMO_PROJECT_ID,
                meeting_id=b["id"],
                participant_id=speaker["id"],
                speaker_label="Sarah",
                text="Evidence",
                sequence=0,
            )
        )
        db_session.flush()


@pytest.mark.integration
def test_partial_transcript_provenance_rejected(db_session, client):
    meeting = client.post(ROOT, json={"title": "Provenance"}).json()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        record = db_session.get(Meeting, meeting["id"])
        record.transcript_bytes = b"Evidence"
        record.transcript_filename = "x.txt"
        record.transcript_format = "txt"
        db_session.flush()
