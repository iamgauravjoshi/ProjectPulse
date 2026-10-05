import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, make_url, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.base import Base
from app.db.models import Project, ProjectMember, User
from app.db.session import create_database_engine, get_engine


def pytest_make_parametrize_id(config, val, argname):
    # Binary fixtures otherwise produce multi-megabyte IDs. Windows rejects
    # PYTEST_CURRENT_TEST values longer than 32767 characters before tests run.
    if isinstance(val, bytes):
        return f"{argname}-{len(val)}-bytes"
    return None


@pytest.fixture(scope="session")
def database_url():
    value = os.environ.get("TEST_DATABASE_URL")
    if not value or not (make_url(value).database or "").endswith("_test"):
        pytest.fail("Integration tests require explicit TEST_DATABASE_URL ending in _test")
    if make_url(value).drivername != "postgresql+psycopg":
        pytest.fail("Integration tests require PostgreSQL with psycopg")
    return value


@pytest.fixture(scope="session")
def migration_config(database_url):
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    get_engine.cache_clear()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    yield config
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_engine.cache_clear()
    get_settings.cache_clear()
    if previous is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous


@pytest.fixture(scope="session")
def database_engine(database_url, migration_config):
    engine = create_database_engine(database_url)
    try:
        with engine.connect() as connection:
            require_empty_database(connection)
        command.upgrade(migration_config, "head")
        yield engine
    finally:
        engine.dispose()


def require_empty_database(connection):
    existing = set(inspect(connection).get_table_names())
    for table in Base.metadata.sorted_tables:
        if (
            table.name in existing
            and connection.execute(select(1).select_from(table).limit(1)).first()
        ):
            pytest.fail(
                "Integration test database must be empty; refusing destructive migration checks"
            )


@pytest.fixture
def database_guard():
    return require_empty_database


@pytest.fixture
def db_session(database_engine):
    with database_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, expire_on_commit=False) as session:
            yield session
        transaction.rollback()


@pytest.fixture
def two_projects(db_session):
    first = Project(name="First project")
    second = Project(name="Second project")
    user = User(display_name="Owner", email="owner@example.test")
    db_session.add_all([first, second, user])
    db_session.flush()
    db_session.add(ProjectMember(project_id=first.id, user_id=user.id, role="TECH_LEAD"))
    db_session.flush()
    return first, second, user
