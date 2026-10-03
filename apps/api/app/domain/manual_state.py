import datetime as dt
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.domain.statuses import (
    CommitmentStatus,
    DecisionStatus,
    DependencyStatus,
    MilestoneStatus,
    RequirementStatus,
    RiskStatus,
    Severity,
)


class RecordKind(StrEnum):
    REQUIREMENTS = "requirements"
    DECISIONS = "decisions"
    MILESTONES = "milestones"
    RISKS = "risks"
    COMMITMENTS = "commitments"
    DEPENDENCIES = "dependencies"


class ManualFields(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        str_strip_whitespace=True,
        use_enum_values=True,
    )
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=20_000)


class RequirementFields(ManualFields):
    status: RequirementStatus = RequirementStatus.ACTIVE
    phase: int = Field(default=1, ge=1, strict=True)


class DecisionFields(ManualFields):
    decision_status: DecisionStatus = DecisionStatus.DISCUSSION
    impact_area: str = Field(default="", max_length=120)


class MilestoneFields(ManualFields):
    status: MilestoneStatus = MilestoneStatus.PLANNED
    milestone_date: dt.date = Field(alias="date")


class RiskFields(ManualFields):
    status: RiskStatus = RiskStatus.OPEN
    severity: Severity = Severity.MEDIUM


class CommitmentFields(ManualFields):
    status: CommitmentStatus = CommitmentStatus.OPEN
    owner_id: UUID | None = None
    due_date: dt.date | None = None
    dependency_id: UUID | None = None


class DependencyFields(ManualFields):
    status: DependencyStatus = DependencyStatus.PENDING
    owner_id: UUID | None = None
    blocked_milestone_id: UUID | None = None


class RecordUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="forbid")
    expected_version: int = Field(ge=1, strict=True)
    values: dict[str, Any]


class StateError(Exception):
    def __init__(self, code: str, message: str, status: int = 422) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)
