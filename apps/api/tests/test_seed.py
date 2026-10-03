import pytest
from sqlalchemy import func, select

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
from app.services import demo_seed
from app.services.demo_seed import DEMO_PROJECT_ID, demo_id, seed_demo

pytestmark = pytest.mark.integration


def counts(session):
    return {
        model.__tablename__: session.scalar(select(func.count()).select_from(model))
        for model in [
            Project,
            User,
            ProjectMember,
            Requirement,
            Decision,
            Commitment,
            Risk,
            Milestone,
            Dependency,
            OpenQuestion,
            AuditEvent,
        ]
    }


def test_demo_seed_baseline_and_provenance(db_session):
    assert seed_demo(db_session) == DEMO_PROJECT_ID
    assert db_session.get(Project, DEMO_PROJECT_ID).name == "Client Portal Modernization"
    assert counts(db_session) == {
        "projects": 1,
        "users": 4,
        "project_members": 4,
        "requirements": 1,
        "decisions": 3,
        "commitments": 1,
        "risks": 1,
        "milestones": 1,
        "dependencies": 1,
        "open_questions": 1,
        "audit_events": 1,
    }
    assert db_session.get(Requirement, demo_id("sso")).phase == 2
    assert db_session.get(Milestone, demo_id("launch")).milestone_date.isoformat() == "2026-11-24"
    commitment = db_session.get(Commitment, demo_id("credentials"))
    assert commitment.owner_id == demo_id("john")
    assert commitment.due_date is None
    assert commitment.said_by is None
    assert commitment.confidence is None
    for model in [Requirement, Decision, Commitment, Risk, Milestone, Dependency, OpenQuestion]:
        for record in db_session.scalars(select(model)).all():
            assert record.source_kind == "SEED"
            assert record.source_label == "Human-established demo baseline"
    assert all(d.decision_status == "CONFIRMED" for d in db_session.scalars(select(Decision)))
    assert (
        db_session.get(Decision, demo_id("csv-export")).description
        == "CSV export remains synchronous."
    )
    assert "three" in db_session.get(Decision, demo_id("payment-retries")).description
    assert db_session.get(Dependency, demo_id("security-review")).status == "PENDING"


def test_repeated_seed_preserves_edits_and_counts(db_session):
    seed_demo(db_session)
    before = counts(db_session)
    requirement = db_session.get(Requirement, demo_id("sso"))
    requirement.phase = 1
    requirement.version = 2
    requirement.source_kind = "MANUAL"
    db_session.flush()
    seed_demo(db_session)
    assert counts(db_session) == before
    db_session.expire_all()
    assert db_session.get(Requirement, demo_id("sso")).phase == 1
    assert db_session.get(Requirement, demo_id("sso")).version == 2
    assert db_session.get(Requirement, demo_id("sso")).source_kind == "MANUAL"


def test_seed_failure_rolls_back_every_record(db_session, monkeypatch):
    original = demo_seed._ensure

    def failing_ensure(session, model, label, **values):
        if label == "credentials":
            raise RuntimeError("simulated seed failure")
        return original(session, model, label, **values)

    monkeypatch.setattr(demo_seed, "_ensure", failing_ensure)
    with pytest.raises(RuntimeError), db_session.begin_nested():
        seed_demo(db_session)
    assert all(count == 0 for count in counts(db_session).values())
