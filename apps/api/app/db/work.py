from datetime import date
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.common import CanonicalRecord, canonical_constraints, enum_check
from app.domain.statuses import CommitmentStatus, DependencyStatus, QuestionStatus


class Dependency(CanonicalRecord, Base):
    __tablename__ = "dependencies"
    __table_args__ = canonical_constraints(
        enum_check("status", DependencyStatus),
        ForeignKeyConstraint(
            ["project_id", "owner_id"], ["project_members.project_id", "project_members.user_id"]
        ),
        ForeignKeyConstraint(
            ["project_id", "blocked_milestone_id"], ["milestones.project_id", "milestones.id"]
        ),
    )
    status: Mapped[str] = mapped_column(
        String(20), default=DependencyStatus.PENDING, server_default=DependencyStatus.PENDING.value
    )
    owner_id: Mapped[UUID | None]
    blocked_milestone_id: Mapped[UUID | None]


class Commitment(CanonicalRecord, Base):
    __tablename__ = "commitments"
    __table_args__ = canonical_constraints(
        enum_check("status", CommitmentStatus),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="confidence_range"
        ),
        ForeignKeyConstraint(
            ["project_id", "said_by"], ["project_members.project_id", "project_members.user_id"]
        ),
        ForeignKeyConstraint(
            ["project_id", "owner_id"], ["project_members.project_id", "project_members.user_id"]
        ),
        ForeignKeyConstraint(
            ["project_id", "dependency_id"], ["dependencies.project_id", "dependencies.id"]
        ),
    )
    status: Mapped[str] = mapped_column(
        String(20), default=CommitmentStatus.OPEN, server_default=CommitmentStatus.OPEN.value
    )
    said_by: Mapped[UUID | None]
    owner_id: Mapped[UUID | None]
    due_date: Mapped[date | None]
    dependency_id: Mapped[UUID | None]
    confidence: Mapped[float | None]


class OpenQuestion(CanonicalRecord, Base):
    __tablename__ = "open_questions"
    __table_args__ = canonical_constraints(
        enum_check("status", QuestionStatus),
        ForeignKeyConstraint(
            ["project_id", "owner_id"], ["project_members.project_id", "project_members.user_id"]
        ),
    )
    status: Mapped[str] = mapped_column(
        String(20), default=QuestionStatus.OPEN, server_default=QuestionStatus.OPEN.value
    )
    owner_id: Mapped[UUID | None]
