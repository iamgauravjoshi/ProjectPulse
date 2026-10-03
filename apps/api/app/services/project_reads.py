from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.common import CanonicalRecord
from app.db.models import (
    AuditEvent,
    Commitment,
    Decision,
    Dependency,
    Milestone,
    OpenQuestion,
    Project,
    ProjectMember,
    Requirement,
    Risk,
    User,
)
from app.domain.workspace import (
    ActivityView,
    CanonicalView,
    CommitmentView,
    DecisionView,
    DependencyView,
    MemberView,
    MilestoneView,
    ProjectSummary,
    QuestionView,
    RequirementView,
    RiskView,
    WorkspaceSnapshot,
)
from app.repositories.canonical import CanonicalRepository

# Development-only identity. Never read an actor ID from a browser request.
LOCAL_DEMO_ACTOR_ID = uuid5(NAMESPACE_URL, "https://contextboard.local/demo/sarah")


def list_projects(session: Session) -> list[ProjectSummary]:
    projects = session.scalars(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == LOCAL_DEMO_ACTOR_ID)
        .order_by(Project.name, Project.id)
    ).all()
    return [ProjectSummary.model_validate(project) for project in projects]


def _records[Record: CanonicalRecord, View: CanonicalView](
    session: Session, project_id: UUID, model: type[Record], view: type[View]
) -> list[View]:
    return [
        view.model_validate(record)
        for record in CanonicalRepository(session, model, project_id).list()
    ]


def read_workspace(session: Session, project_id: UUID) -> WorkspaceSnapshot | None:
    project = session.scalar(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(Project.id == project_id, ProjectMember.user_id == LOCAL_DEMO_ACTOR_ID)
    )
    if project is None:
        return None
    members = session.execute(
        select(User, ProjectMember.role)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .where(ProjectMember.project_id == project_id)
        .order_by(User.display_name)
    ).all()
    activity = session.scalars(
        select(AuditEvent)
        .where(AuditEvent.project_id == project_id)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id)
        .limit(10)
    ).all()
    return WorkspaceSnapshot(
        project=ProjectSummary.model_validate(project),
        members=[
            MemberView(id=user.id, name=user.display_name, role=role) for user, role in members
        ],
        requirements=_records(session, project_id, Requirement, RequirementView),
        decisions=_records(session, project_id, Decision, DecisionView),
        commitments=_records(session, project_id, Commitment, CommitmentView),
        risks=_records(session, project_id, Risk, RiskView),
        milestones=_records(session, project_id, Milestone, MilestoneView),
        dependencies=_records(session, project_id, Dependency, DependencyView),
        questions=_records(session, project_id, OpenQuestion, QuestionView),
        activity=[ActivityView.model_validate(event) for event in activity],
        generated_at=datetime.now(UTC),
    )
