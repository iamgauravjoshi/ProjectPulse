from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, make_url
from sqlalchemy.orm import Session

from app.config import get_settings


def create_database_engine(database_url: str) -> Engine:
    if make_url(database_url).drivername != "postgresql+psycopg":
        raise ValueError("PostgreSQL with the psycopg driver is required")
    return create_engine(
        database_url,
        connect_args={"connect_timeout": 3},
        pool_pre_ping=True,
        pool_timeout=3,
    )


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    if not url:
        raise ValueError("DATABASE_URL is not configured")
    return create_database_engine(url)


@contextmanager
def session_scope() -> Iterator[Session]:
    with Session(get_engine(), expire_on_commit=False) as session, session.begin():
        yield session
