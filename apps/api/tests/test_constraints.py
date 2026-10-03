from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models import (
    Commitment,
    Decision,
    Dependency,
    Milestone,
    OpenQuestion,
    ProjectMember,
    Requirement,
    Risk,
    User,
)

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "model,values",
    [
        (Requirement, {"title": "   "}),
        (Requirement, {"phase": 0}),
        (Requirement, {"status": "CONFIRMED"}),
        (Requirement, {"version": 0}),
        (Requirement, {"source_kind": "AI"}),
        (Decision, {"decision_status": "CERTAIN"}),
        (Decision, {"decision_status": "CONFIRMED"}),
        (Decision, {"decision_status": "SUPERSEDED"}),
        (Commitment, {"confidence": 1.5}),
        (Commitment, {"confidence": -0.1}),
        (Commitment, {"status": "MAYBE"}),
        (Risk, {"severity": "EXTREME"}),
        (Risk, {"status": "DONE"}),
        (Dependency, {"status": "MAYBE"}),
        (OpenQuestion, {"status": "MAYBE"}),
    ],
)
def test_invalid_canonical_values_rejected(db_session, two_projects, model, values):
    project, _, _ = two_projects
    fields = {"project_id": project.id, "title": "Baseline", **values}
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(model(**fields))
        db_session.flush()


@pytest.mark.parametrize(
    "model,field",
    [
        (Commitment, "owner_id"),
        (Commitment, "said_by"),
        (Dependency, "owner_id"),
        (Decision, "made_by"),
        (OpenQuestion, "owner_id"),
    ],
)
def test_owner_must_be_member_of_same_project(db_session, two_projects, model, field):
    _, second, user = two_projects
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(model(project_id=second.id, title="Cross-project owner", **{field: user.id}))
        db_session.flush()


def test_cross_project_dependencies_rejected(db_session, two_projects):
    first, second, _ = two_projects
    dependency = Dependency(project_id=first.id, title="Credentials")
    db_session.add(dependency)
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            Commitment(project_id=second.id, title="Deploy", dependency_id=dependency.id)
        )
        db_session.flush()


def test_cross_project_decision_supersession_rejected(db_session, two_projects):
    first, second, _ = two_projects
    decision = Decision(project_id=first.id, title="Sync export")
    db_session.add(decision)
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            Decision(project_id=second.id, title="Async export", supersedes_decision_id=decision.id)
        )
        db_session.flush()


def test_self_supersession_rejected(db_session, two_projects):
    first, _, _ = two_projects
    decision_id = uuid4()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            Decision(
                id=decision_id,
                project_id=first.id,
                title="Self reference",
                supersedes_decision_id=decision_id,
            )
        )
        db_session.flush()


def test_duplicate_membership_and_non_normalized_email_rejected(db_session, two_projects):
    first, _, user = two_projects
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(ProjectMember(project_id=first.id, user_id=user.id, role="QA"))
        db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(User(display_name="Other", email="UPPER@example.test"))
        db_session.flush()


def test_confirmed_decision_and_distinct_speaker_owner_allowed(db_session, two_projects):
    first, _, user = two_projects
    other = User(display_name="Speaker", email="speaker@example.test")
    db_session.add(other)
    db_session.flush()
    db_session.add(ProjectMember(project_id=first.id, user_id=other.id, role="QA"))
    db_session.flush()
    decision = Decision(
        project_id=first.id,
        title="PostgreSQL",
        decision_status="CONFIRMED",
        confirmed_at=datetime.now(UTC),
        made_by=user.id,
    )
    commitment = Commitment(
        project_id=first.id, title="Send credentials", said_by=other.id, owner_id=user.id
    )
    db_session.add_all([decision, commitment])
    db_session.flush()
    assert commitment.said_by != commitment.owner_id
    assert decision.decision_status == "CONFIRMED"


def test_cross_project_blocked_milestone_rejected(db_session, two_projects):
    first, second, _ = two_projects
    milestone = Milestone(project_id=first.id, title="Launch", milestone_date=date(2026, 11, 24))
    db_session.add(milestone)
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            Dependency(project_id=second.id, title="Review", blocked_milestone_id=milestone.id)
        )
        db_session.flush()


def test_invalid_stakeholder_role_rejected(db_session, two_projects):
    _, second, user = two_projects
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(ProjectMember(project_id=second.id, user_id=user.id, role="UNRECOGNIZED"))
        db_session.flush()
