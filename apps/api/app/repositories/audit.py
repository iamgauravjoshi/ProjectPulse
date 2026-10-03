from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.audit import AuditEvent


class AuditRepository:
    """Append/read only. There is deliberately no update or delete operation."""

    def __init__(self, session: Session, project_id: UUID) -> None:
        self.session = session
        self.project_id = project_id

    def append(self, event: AuditEvent) -> AuditEvent:
        if event.project_id != self.project_id:
            raise ValueError("Audit event belongs to a different project")
        self.session.add(event)
        self.session.flush()
        return event

    def list(self) -> Sequence[AuditEvent]:
        return self.session.scalars(
            select(AuditEvent)
            .where(AuditEvent.project_id == self.project_id)
            .order_by(AuditEvent.created_at, AuditEvent.id)
        ).all()
