from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text

from app.db.base import Base
from app.db.models import AuditEvent, Project, Requirement
from app.db.session import get_engine, session_scope
from app.main import app

pytestmark = pytest.mark.integration


def test_pgvector_migration_rollback_reapply(database_engine, migration_config):
    with database_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT extversion FROM pg_extension WHERE extname='vector'")
            ).scalar_one()
            == "0.8.1"
        )
    command.downgrade(migration_config, "base")
    with database_engine.connect() as connection:
        assert not connection.execute(
            text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')")
        ).scalar_one()
    with TestClient(app) as client:
        assert client.get("/health/ready").status_code == 503
    command.upgrade(migration_config, "head")
    with TestClient(app) as client:
        assert client.get("/health/ready").json() == {"status": "ok"}


def test_refuses_preexisting_vector_extension(database_engine, migration_config):
    command.downgrade(migration_config, "base")
    with database_engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION vector"))
    try:
        with pytest.raises(RuntimeError, match="refusing to take ownership"):
            command.upgrade(migration_config, "head")
        with database_engine.connect() as connection:
            assert connection.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')")
            ).scalar_one()
    finally:
        with database_engine.begin() as connection:
            connection.execute(text("DROP EXTENSION vector"))
        command.upgrade(migration_config, "head")


def test_session_scope_returns_connection_after_exception(database_engine):
    with (
        pytest.raises(RuntimeError, match="simulated operation failure"),
        session_scope() as session,
    ):
        session.execute(text("SELECT 1"))
        raise RuntimeError("simulated operation failure")
    assert get_engine().pool.checkedout() == 0


def test_migrated_schema_matches_models(database_engine):
    with database_engine.connect() as connection:
        context = MigrationContext.configure(
            connection, opts={"compare_type": True, "compare_server_default": True}
        )
        assert compare_metadata(context, Base.metadata) == []


def test_populated_test_database_is_rejected_without_deleting_data(
    db_session, two_projects, database_guard
):
    first, _, _ = two_projects
    with pytest.raises(pytest.fail.Exception, match="database must be empty"):
        database_guard(db_session.connection())
    assert db_session.get(Project, first.id).name == "First project"


def test_canonical_migration_downgrade_reapply(database_engine, migration_config):
    command.downgrade(migration_config, "0001_vector")
    assert "requirements" not in inspect(database_engine).get_table_names()
    command.upgrade(migration_config, "head")
    assert "requirements" in inspect(database_engine).get_table_names()


def test_session_scope_rolls_back_canonical_and_audit(database_engine):
    project_id, record_id, audit_id = uuid4(), uuid4(), uuid4()
    with pytest.raises(RuntimeError), session_scope() as session:
        session.add(Project(id=project_id, name="Rolled back project"))
        session.flush()
        session.add(Requirement(id=record_id, project_id=project_id, title="Rolled back SSO"))
        session.add(
            AuditEvent(
                id=audit_id,
                project_id=project_id,
                action="CREATE",
                entity_type="requirement",
                entity_id=record_id,
            )
        )
        session.flush()
        raise RuntimeError("simulated write failure")
    with database_engine.connect() as connection:
        assert (
            connection.execute(select(Project.id).where(Project.id == project_id)).first() is None
        )
        assert (
            connection.execute(select(Requirement.id).where(Requirement.id == record_id)).first()
            is None
        )
        assert (
            connection.execute(select(AuditEvent.id).where(AuditEvent.id == audit_id)).first()
            is None
        )
