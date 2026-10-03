from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.common import CanonicalRecord, canonical_constraints, enum_check
from app.domain.statuses import DecisionStatus


class Decision(CanonicalRecord, Base):
    __tablename__ = "decisions"
    __table_args__ = canonical_constraints(
        enum_check("decision_status", DecisionStatus),
        CheckConstraint(
            "decision_status NOT IN ('CONFIRMED', 'SUPERSEDED') OR confirmed_at IS NOT NULL",
            name="confirmed_timestamp",
        ),
        CheckConstraint(
            "supersedes_decision_id IS NULL OR supersedes_decision_id <> id", name="not_self"
        ),
        ForeignKeyConstraint(
            ["project_id", "made_by"], ["project_members.project_id", "project_members.user_id"]
        ),
        ForeignKeyConstraint(
            ["project_id", "supersedes_decision_id"], ["decisions.project_id", "decisions.id"]
        ),
    )
    decision_status: Mapped[str] = mapped_column(
        String(30),
        default=DecisionStatus.DISCUSSION,
        server_default=DecisionStatus.DISCUSSION.value,
    )
    impact_area: Mapped[str] = mapped_column(String(120), default="", server_default="")
    made_by: Mapped[UUID | None]
    supersedes_decision_id: Mapped[UUID | None]
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
