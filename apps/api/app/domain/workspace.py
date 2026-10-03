import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str


class ReadView(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class CanonicalView(ReadView):
    id: UUID
    project_id: UUID
    title: str
    description: str
    source_kind: str
    source_label: str
    version: int
    updated_at: dt.datetime


class RequirementView(CanonicalView):
    status: str
    phase: int


class DecisionView(CanonicalView):
    decision_status: str
    impact_area: str
    made_by: UUID | None
    confirmed_at: dt.datetime | None


class CommitmentView(CanonicalView):
    status: str
    owner_id: UUID | None
    said_by: UUID | None
    due_date: dt.date | None
    dependency_id: UUID | None


class RiskView(CanonicalView):
    status: str
    severity: str


class MilestoneView(CanonicalView):
    status: str
    date: dt.date = Field(validation_alias="milestone_date")


class DependencyView(CanonicalView):
    status: str
    owner_id: UUID | None
    blocked_milestone_id: UUID | None


class QuestionView(CanonicalView):
    status: str
    owner_id: UUID | None


class MemberView(ReadView):
    id: UUID
    name: str
    role: str


class ActivityView(ReadView):
    id: UUID
    action: str
    entity_type: str
    created_at: dt.datetime


class WorkspaceSnapshot(ReadView):
    project: ProjectSummary
    members: list[MemberView]
    requirements: list[RequirementView]
    decisions: list[DecisionView]
    commitments: list[CommitmentView]
    risks: list[RiskView]
    milestones: list[MilestoneView]
    dependencies: list[DependencyView]
    questions: list[QuestionView]
    activity: list[ActivityView]
    generated_at: dt.datetime
