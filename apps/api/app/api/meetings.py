from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_database_session
from app.domain.meetings import MeetingFields, ParticipantFields
from app.services import meetings

router = APIRouter(prefix="/api/v1/projects/{project_id}/meetings", tags=["meetings"])
Database = Annotated[Session, Depends(get_database_session)]


@router.get("")
def list_meetings(project_id: UUID, session: Database) -> list[dict[str, Any]]:
    return meetings.list_meetings(session, project_id)


@router.post("", status_code=201)
def create_meeting(project_id: UUID, fields: MeetingFields, session: Database) -> dict[str, Any]:
    return meetings.create_meeting(session, project_id, fields)


@router.get("/{meeting_id}")
def get_meeting(project_id: UUID, meeting_id: UUID, session: Database) -> dict[str, Any]:
    return meetings.detail(session, project_id, meeting_id)


@router.post("/{meeting_id}/participants", status_code=201)
def add_participant(
    project_id: UUID, meeting_id: UUID, fields: ParticipantFields, session: Database
) -> dict[str, Any]:
    return meetings.add_participant(session, project_id, meeting_id, fields)


@router.delete("/{meeting_id}", status_code=204)
def delete_meeting(project_id: UUID, meeting_id: UUID, session: Database) -> Response:
    meetings.delete_meeting(session, project_id, meeting_id)
    return Response(status_code=204)
