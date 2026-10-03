from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_database_session
from app.domain.manual_state import RecordKind, RecordUpdate
from app.services import manual_state

router = APIRouter(prefix="/api/v1/projects/{project_id}/state", tags=["manual project state"])
DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.get("/{kind}")
def records(project_id: UUID, kind: RecordKind, session: DatabaseSession) -> list[dict[str, Any]]:
    return manual_state.read_records(session, project_id, kind)


@router.get("/{kind}/{record_id}")
def record(
    project_id: UUID, kind: RecordKind, record_id: UUID, session: DatabaseSession
) -> dict[str, Any]:
    return manual_state.read_record(session, project_id, kind, record_id)


@router.post("/{kind}", status_code=201)
def create(
    project_id: UUID, kind: RecordKind, values: dict[str, Any], session: DatabaseSession
) -> dict[str, Any]:
    return manual_state.create_record(session, project_id, kind, values)


@router.put("/{kind}/{record_id}")
def update(
    project_id: UUID,
    kind: RecordKind,
    record_id: UUID,
    command: RecordUpdate,
    session: DatabaseSession,
) -> dict[str, Any]:
    return manual_state.update_record(
        session, project_id, kind, record_id, command.expected_version, command.values
    )


@router.delete("/{kind}/{record_id}", status_code=204)
def delete(
    project_id: UUID,
    kind: RecordKind,
    record_id: UUID,
    session: DatabaseSession,
    expected_version: Annotated[int, Query(alias="expectedVersion", ge=1)],
) -> Response:
    manual_state.delete_record(session, project_id, kind, record_id, expected_version)
    return Response(status_code=204)
