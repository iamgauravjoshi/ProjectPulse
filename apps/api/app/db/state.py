from datetime import date

from sqlalchemy import CheckConstraint, Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.common import CanonicalRecord, canonical_constraints, enum_check
from app.domain.statuses import MilestoneStatus, RequirementStatus, RiskStatus, Severity


class Requirement(CanonicalRecord, Base):
    __tablename__ = "requirements"
    __table_args__ = canonical_constraints(
        enum_check("status", RequirementStatus), CheckConstraint("phase > 0", name="phase_positive")
    )
    status: Mapped[str] = mapped_column(
        String(20), default=RequirementStatus.ACTIVE, server_default=RequirementStatus.ACTIVE.value
    )
    phase: Mapped[int] = mapped_column(default=1, server_default="1")


class Risk(CanonicalRecord, Base):
    __tablename__ = "risks"
    __table_args__ = canonical_constraints(
        enum_check("status", RiskStatus), enum_check("severity", Severity)
    )
    status: Mapped[str] = mapped_column(
        String(20), default=RiskStatus.OPEN, server_default=RiskStatus.OPEN.value
    )
    severity: Mapped[str] = mapped_column(
        String(20), default=Severity.MEDIUM, server_default=Severity.MEDIUM.value
    )


class Milestone(CanonicalRecord, Base):
    __tablename__ = "milestones"
    __table_args__ = canonical_constraints(enum_check("status", MilestoneStatus))
    status: Mapped[str] = mapped_column(
        String(20), default=MilestoneStatus.PLANNED, server_default=MilestoneStatus.PLANNED.value
    )
    milestone_date: Mapped[date] = mapped_column("date", Date)
