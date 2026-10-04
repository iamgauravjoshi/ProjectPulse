from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.api.dependencies import get_database_session
from app.domain.manual_state import StateError
from app.domain.meetings import MeetingFields, ParticipantFields
from app.domain.transcripts import MAX_TRANSCRIPT_BYTES
from app.services import meetings
from app.services.project_access import require_project_access
from app.services.transcript_upload import upload_transcript

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


@router.post("/{meeting_id}/transcript", status_code=201)
async def upload(
    project_id: UUID,
    meeting_id: UUID,
    request: Request,
    session: Database,
    filename: Annotated[str, Query(min_length=1, max_length=240)],
) -> dict[str, Any]:
    await run_in_threadpool(require_project_access, session, project_id)
    await run_in_threadpool(meetings.find_meeting, session, project_id, meeting_id)
    body = bytearray()
    async for part in request.stream():
        if len(body) + len(part) > MAX_TRANSCRIPT_BYTES:
            raise StateError("TRANSCRIPT_SIZE", "Transcripts must be no larger than 2 MiB.", 413)
        body.extend(part)
    return await run_in_threadpool(
        upload_transcript, session, project_id, meeting_id, filename, bytes(body)
    )
