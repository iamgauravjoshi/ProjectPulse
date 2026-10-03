import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.dependencies import get_read_session
from app.db.models import AuditEvent, Project, ProjectMember, Requirement, User
from app.main import app
from app.services.demo_seed import DEMO_PROJECT_ID, seed_demo
from app.services.project_reads import LOCAL_DEMO_ACTOR_ID

pytestmark = pytest.mark.integration


@pytest.fixture
def project_client(db_session):
    app.dependency_overrides[get_read_session] = lambda: db_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_read_session, None)


def test_project_list_reads_seed_without_writes(db_session, project_client):
    seed_demo(db_session)
    response = project_client.get("/api/v1/projects")
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(DEMO_PROJECT_ID),
            "name": "Client Portal Modernization",
            "description": "Modernize the client portal while keeping project decisions traceable.",
        }
    ]
    project_client.get("/api/v1/projects")
    assert db_session.scalar(select(func.count()).select_from(AuditEvent)) == 1


def test_project_list_excludes_outside_memberships(db_session, project_client):
    seed_demo(db_session)
    other = Project(name="Private project")
    outsider = User(display_name="Outside user", email="outside@example.test")
    db_session.add_all([other, outsider])
    db_session.flush()
    db_session.add(ProjectMember(project_id=other.id, user_id=outsider.id, role="TECH_LEAD"))
    db_session.flush()
    response = project_client.get(f"/api/v1/projects?actor_id={outsider.id}")
    assert [p["id"] for p in response.json()] == [str(DEMO_PROJECT_ID)]


def test_project_list_is_empty_without_actor_membership(project_client):
    assert project_client.get("/api/v1/projects").json() == []


def test_workspace_projects_all_baseline_types_without_writes(db_session, project_client):
    seed_demo(db_session)
    response = project_client.get(f"/api/v1/projects/{DEMO_PROJECT_ID}/workspace")
    assert response.status_code == 200
    body = response.json()
    assert body["project"]["id"] == str(DEMO_PROJECT_ID)
    assert body["requirements"][0]["phase"] == 2
    assert body["milestones"][0]["date"] == "2026-11-24"
    assert body["commitments"][0]["dueDate"] is None
    assert len(body["members"]) == 4
    assert len(body["decisions"]) == 3
    assert all(record["decisionStatus"] == "CONFIRMED" for record in body["decisions"])
    for field in [
        "requirements",
        "decisions",
        "commitments",
        "risks",
        "milestones",
        "dependencies",
        "questions",
    ]:
        assert body[field] and all(row["projectId"] == str(DEMO_PROJECT_ID) for row in body[field])
    assert "payload" not in body["activity"][0]
    assert db_session.scalar(select(func.count()).select_from(AuditEvent)) == 1


def test_workspace_unavailable_and_missing_return_same_404(db_session, project_client):
    from uuid import uuid4

    other = Project(name="Hidden workspace")
    db_session.add(other)
    db_session.flush()
    hidden = project_client.get(f"/api/v1/projects/{other.id}/workspace")
    absent = project_client.get(f"/api/v1/projects/{uuid4()}/workspace")
    assert hidden.status_code == absent.status_code == 404
    assert hidden.json() == absent.json()


def test_workspace_isolation_and_empty_project(db_session, project_client):
    seed_demo(db_session)
    other = Project(name="Empty assigned workspace")
    db_session.add(other)
    db_session.flush()
    db_session.add(
        ProjectMember(project_id=other.id, user_id=LOCAL_DEMO_ACTOR_ID, role="PRODUCT_OWNER")
    )
    db_session.flush()
    body = project_client.get(f"/api/v1/projects/{other.id}/workspace").json()
    assert body["requirements"] == [] and body["decisions"] == [] and body["activity"] == []
    db_session.add(Requirement(project_id=other.id, title="Private requirement"))
    db_session.flush()
    baseline = project_client.get(f"/api/v1/projects/{DEMO_PROJECT_ID}/workspace").json()
    assert [row["title"] for row in baseline["requirements"]] == ["Single sign-on"]
