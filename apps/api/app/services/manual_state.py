from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.common import CanonicalRecord
from app.db.models import (
    AuditEvent,
    Commitment,
    Decision,
    Dependency,
    Milestone,
    ProjectMember,
    Requirement,
    Risk,
)
from app.domain.manual_state import (
    CommitmentFields,
    DecisionFields,
    DependencyFields,
    ManualFields,
    MilestoneFields,
    RecordKind,
    RequirementFields,
    RiskFields,
    StateError,
)
from app.domain.workspace import (
    CanonicalView,
    CommitmentView,
    DecisionView,
    DependencyView,
    MilestoneView,
    RequirementView,
    RiskView,
)
from app.repositories.audit import AuditRepository
from app.services.project_access import LOCAL_DEMO_ACTOR_ID, require_project_access


@dataclass(frozen=True)
class RecordSpec:
    model: type[Requirement | Decision | Milestone | Risk | Commitment | Dependency]
    fields: type[ManualFields]
    view: type[CanonicalView]
    entity: str


SPECS = {
    RecordKind.REQUIREMENTS: RecordSpec(
        Requirement, RequirementFields, RequirementView, "requirement"
    ),
    RecordKind.DECISIONS: RecordSpec(Decision, DecisionFields, DecisionView, "decision"),
    RecordKind.MILESTONES: RecordSpec(Milestone, MilestoneFields, MilestoneView, "milestone"),
    RecordKind.RISKS: RecordSpec(Risk, RiskFields, RiskView, "risk"),
    RecordKind.COMMITMENTS: RecordSpec(Commitment, CommitmentFields, CommitmentView, "commitment"),
    RecordKind.DEPENDENCIES: RecordSpec(Dependency, DependencyFields, DependencyView, "dependency"),
}


def projection(kind: RecordKind, record: CanonicalRecord) -> dict[str, Any]:
    return SPECS[kind].view.model_validate(record).model_dump(mode="json", by_alias=True)


def record_query(kind: RecordKind, project_id: UUID, record_id: UUID) -> Any:
    model = SPECS[kind].model
    return select(model).where(model.project_id == project_id, model.id == record_id)


def find_record(
    session: Session, kind: RecordKind, project_id: UUID, record_id: UUID, *, lock: bool = False
) -> CanonicalRecord:
    query = record_query(kind, project_id, record_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    record: CanonicalRecord | None = session.scalar(query)
    if record is None:
        raise StateError("RECORD_NOT_FOUND", "Record not found.", 404)
    return record


def read_records(session: Session, project_id: UUID, kind: RecordKind) -> list[dict[str, Any]]:
    require_project_access(session, project_id)
    model = SPECS[kind].model
    records = session.scalars(
        select(model).where(model.project_id == project_id).order_by(model.created_at, model.id)
    )
    return [projection(kind, record) for record in records]


def read_record(
    session: Session, project_id: UUID, kind: RecordKind, record_id: UUID
) -> dict[str, Any]:
    require_project_access(session, project_id)
    return projection(kind, find_record(session, kind, project_id, record_id))


def validated_values(
    session: Session, project_id: UUID, kind: RecordKind, payload: dict[str, Any]
) -> dict[str, Any]:
    try:
        values = SPECS[kind].fields.model_validate(payload).model_dump()
    except ValidationError:
        raise StateError("INVALID_RECORD", "Check the record fields and try again.") from None
    owner = values.get("owner_id")
    if (
        owner
        and session.scalar(
            select(ProjectMember.id).where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == owner
            )
        )
        is None
    ):
        raise StateError("INVALID_REFERENCE", "Choose an owner from this project's members.")
    for field, model in (("dependency_id", Dependency), ("blocked_milestone_id", Milestone)):
        key = values.get(field)
        if (
            key
            and session.scalar(
                select(model.id).where(model.project_id == project_id, model.id == key)
            )
            is None
        ):
            raise StateError("INVALID_REFERENCE", "Choose a related record from this project.")
    return values


def decision_metadata(record: CanonicalRecord) -> None:
    if isinstance(record, Decision):
        if record.decision_status in ("CONFIRMED", "SUPERSEDED"):
            record.confirmed_at = record.confirmed_at or datetime.now(UTC)
        else:
            record.confirmed_at = None


def append_audit(
    session: Session,
    project_id: UUID,
    kind: RecordKind,
    record_id: UUID,
    action: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> None:
    AuditRepository(session, project_id).append(
        AuditEvent(
            project_id=project_id,
            actor_id=LOCAL_DEMO_ACTOR_ID,
            action=f"MANUAL_STATE_{action}",
            entity_type=SPECS[kind].entity,
            entity_id=record_id,
            payload={"before": before, "after": after},
        )
    )


def create_record(
    session: Session, project_id: UUID, kind: RecordKind, payload: dict[str, Any]
) -> dict[str, Any]:
    require_project_access(session, project_id)
    values = validated_values(session, project_id, kind, payload)
    with session.begin_nested():
        record = SPECS[kind].model(
            project_id=project_id,
            source_kind="MANUAL",
            source_label="Human-established baseline",
            **values,
        )
        if isinstance(record, Decision):
            record.made_by = LOCAL_DEMO_ACTOR_ID
        decision_metadata(record)
        session.add(record)
        session.flush()
        result = projection(kind, record)
        append_audit(session, project_id, kind, record.id, "CREATED", None, result)
    session.commit()
    return result


def update_record(
    session: Session,
    project_id: UUID,
    kind: RecordKind,
    record_id: UUID,
    expected_version: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    require_project_access(session, project_id)
    values = validated_values(session, project_id, kind, payload)
    with session.begin_nested():
        record = find_record(session, kind, project_id, record_id, lock=True)
        check_version(record, expected_version)
        before = projection(kind, record)
        for field, value in values.items():
            setattr(record, field, value)
        record.version += 1
        record.source_kind = "MANUAL"
        record.source_label = "Human-established baseline"
        decision_metadata(record)
        session.flush()
        result = projection(kind, record)
        append_audit(session, project_id, kind, record.id, "UPDATED", before, result)
    session.commit()
    return result


def check_version(record: CanonicalRecord, expected_version: int) -> None:
    if record.version != expected_version:
        raise StateError(
            "STALE_VERSION", "This record changed. Reload it before trying again.", 409
        )


def delete_record(
    session: Session, project_id: UUID, kind: RecordKind, record_id: UUID, expected_version: int
) -> None:
    require_project_access(session, project_id)
    try:
        with session.begin_nested():
            record = find_record(session, kind, project_id, record_id, lock=True)
            check_version(record, expected_version)
            before = projection(kind, record)
            session.delete(record)
            session.flush()
            append_audit(session, project_id, kind, record_id, "DELETED", before, None)
    except IntegrityError:
        raise StateError(
            "RECORD_IN_USE", "Remove references to this record before deleting it.", 409
        ) from None
    session.commit()
