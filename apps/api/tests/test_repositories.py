from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models import (
    AuditEvent,
    Commitment,
    Decision,
    Dependency,
    Milestone,
    OpenQuestion,
    Requirement,
    Risk,
)
from app.repositories.audit import AuditRepository
from app.repositories.canonical import CanonicalRepository

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "model,values",
    [
        (Requirement, {"phase": 2}),
        (Decision, {"decision_status": "PROVISIONAL"}),
        (Commitment, {}),
        (Risk, {"severity": "HIGH"}),
        (Milestone, {"milestone_date": date(2026, 11, 24)}),
        (Dependency, {}),
        (OpenQuestion, {}),
    ],
)
def test_canonical_roundtrip(db_session, two_projects, model, values):
    project, _, _ = two_projects
    repository = CanonicalRepository(db_session, model, project.id)
    item = repository.add(model(project_id=project.id, title="Trusted baseline", **values))
    db_session.expire_all()
    fetched = repository.get(item.id)
    assert fetched.title == "Trusted baseline"
    assert fetched.source_kind == "MANUAL"
    assert fetched.version == 1
    assert fetched.created_at.utcoffset().total_seconds() == 0
    assert len(repository.list()) == 1


def test_project_scope_blocks_read_update_and_add(db_session, two_projects):
    first, second, _ = two_projects
    owner = CanonicalRepository(db_session, Requirement, first.id)
    item = owner.add(Requirement(project_id=first.id, title="SSO", phase=2))
    outsider = CanonicalRepository(db_session, Requirement, second.id)
    assert outsider.get(item.id) is None
    assert outsider.list() == []
    assert outsider.rename(item.id, "Hijacked", expected_version=1) is None
    with pytest.raises(ValueError, match="different project"):
        outsider.add(Requirement(project_id=first.id, title="Wrong scope"))
    assert owner.get(item.id).title == "SSO"


def test_update_version_and_stale_write_protection(db_session, two_projects):
    first, _, _ = two_projects
    repo = CanonicalRepository(db_session, Requirement, first.id)
    item = repo.add(Requirement(project_id=first.id, title="SSO"))
    updated = repo.rename(item.id, "Single sign-on", expected_version=1)
    assert updated.version == 2
    assert updated.title == "Single sign-on"
    with pytest.raises(ValueError, match="version has changed"):
        repo.rename(item.id, "Stale title", expected_version=1)
    assert repo.get(item.id).title == "Single sign-on"
    with pytest.raises(ValueError, match="cannot be blank"):
        repo.rename(item.id, "  ", expected_version=2)


def test_audit_scope_and_transaction_rollback(db_session, two_projects):
    first, second, _ = two_projects
    item_id, event_id = uuid4(), uuid4()
    with pytest.raises(RuntimeError), db_session.begin_nested():
        CanonicalRepository(db_session, Requirement, first.id).add(
            Requirement(id=item_id, project_id=first.id, title="Must roll back")
        )
        AuditRepository(db_session, first.id).append(
            AuditEvent(
                id=event_id,
                project_id=first.id,
                action="MANUAL_CREATE",
                entity_type="requirement",
                entity_id=item_id,
            )
        )
        raise RuntimeError("simulated transaction failure")
    assert db_session.scalar(select(Requirement).where(Requirement.id == item_id)) is None
    assert db_session.scalar(select(AuditEvent).where(AuditEvent.id == event_id)) is None
    with pytest.raises(ValueError, match="different project"):
        AuditRepository(db_session, second.id).append(
            AuditEvent(project_id=first.id, action="CREATE", entity_type="requirement")
        )
    event = AuditRepository(db_session, first.id).append(
        AuditEvent(project_id=first.id, action="CREATE", entity_type="requirement")
    )
    assert [row.id for row in AuditRepository(db_session, first.id).list()] == [event.id]
    assert AuditRepository(db_session, second.id).list() == []
