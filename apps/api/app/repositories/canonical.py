from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.common import CanonicalRecord


class CanonicalRepository[Record: CanonicalRecord]:
    """Internal manual-state access; never expose this repository to AI detectors.

    The caller owns the transaction. Project scoping is mandatory, but actor
    authentication and later governance belong to the service/API boundary.
    """

    def __init__(self, session: Session, model: type[Record], project_id: UUID) -> None:
        self.session = session
        self.model = model
        self.project_id = project_id

    def get(self, record_id: UUID) -> Record | None:
        return self.session.scalar(
            select(self.model).where(
                self.model.project_id == self.project_id, self.model.id == record_id
            )
        )

    def list(self) -> Sequence[Record]:
        return self.session.scalars(
            select(self.model)
            .where(self.model.project_id == self.project_id)
            .order_by(self.model.created_at, self.model.id)
        ).all()

    def add(self, record: Record) -> Record:
        if record.project_id != self.project_id:
            raise ValueError("Record belongs to a different project")
        self.session.add(record)
        self.session.flush()
        return record

    def rename(self, record_id: UUID, title: str, expected_version: int) -> Record | None:
        """Minimal internal update path with row locking and stale-write protection."""
        record = self.session.scalar(
            select(self.model)
            .where(self.model.project_id == self.project_id, self.model.id == record_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if record is None:
            return None
        if record.version != expected_version:
            raise ValueError("Canonical record version has changed")
        if not title.strip():
            raise ValueError("Title cannot be blank")
        record.title = title.strip()
        record.version += 1
        self.session.flush()
        return record
