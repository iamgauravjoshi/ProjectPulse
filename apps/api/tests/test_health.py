from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api import dependencies, health
from app.main import app


def test_liveness_without_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    def forbidden_engine():
        raise AssertionError("Liveness must not access the database")

    monkeypatch.setattr(health, "get_engine", forbidden_engine)
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_failure_hides_database_details(monkeypatch):
    def unavailable_engine():
        raise OperationalError("private connection string", {}, Exception("secret"))

    monkeypatch.setattr(health, "get_engine", unavailable_engine)
    with TestClient(app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "DATABASE_UNAVAILABLE", "message": "Database is not ready."}
    }


def test_workspace_dependency_failure_hides_database_details(monkeypatch):
    def unavailable_engine():
        raise OperationalError("private database URL", {}, Exception("secret"))

    monkeypatch.setattr(dependencies, "get_engine", unavailable_engine)
    with TestClient(app) as client:
        response = client.get("/api/v1/projects")
    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "WORKSPACE_UNAVAILABLE",
            "message": "Workspace is temporarily unavailable.",
        }
    }
