from collections.abc import Iterator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.domain.errors import WorkspaceUnavailable


def get_read_session() -> Iterator[Session]:
    try:
        engine = get_engine()
    except (SQLAlchemyError, ValueError):
        raise WorkspaceUnavailable from None
    try:
        with Session(engine) as session:
            yield session
    except SQLAlchemyError:
        raise WorkspaceUnavailable from None
