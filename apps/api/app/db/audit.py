from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.common import ProjectOwned


class AuditEvent(ProjectOwned, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        UniqueConstraint("project_id", "id"),
        CheckConstraint("length(trim(action)) > 0", name="action_not_blank"),
        CheckConstraint("length(trim(entity_type)) > 0", name="entity_type_not_blank"),
        ForeignKeyConstraint(
            ["project_id", "actor_id"], ["project_members.project_id", "project_members.user_id"]
        ),
    )
    actor_id: Mapped[UUID | None]
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[UUID | None]
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
