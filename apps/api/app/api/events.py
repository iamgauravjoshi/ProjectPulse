from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.api.dependencies import get_database_session
from app.domain.events import EventKind
from app.domain.manual_state import StateError
from app.services.event_extraction import extract_meeting, extraction_view
from app.services.event_provider import EventProvider, get_event_provider
from app.services.meetings import find_meeting
from app.services.relevance_provider import RelevanceProvider, get_relevance_provider

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/meetings/{meeting_id}/events", tags=["events"]
)
Database = Annotated[Session, Depends(get_database_session)]
Provider = Annotated[EventProvider, Depends(get_event_provider)]
Relevance = Annotated[RelevanceProvider, Depends(get_relevance_provider)]


@router.get("")
def get_events(
    project_id: UUID,
    meeting_id: UUID,
    session: Database,
    provider: Provider,
    relevance: Relevance,
    page: Annotated[int, Query(ge=1, le=400)] = 1,
    kind: EventKind | Literal["ALL"] = "ALL",
) -> dict[str, Any]:
    return extraction_view(
        session, project_id, meeting_id, provider, relevance, page=page, kind=str(kind)
    )


@router.post("")
async def extract_events(
    project_id: UUID,
    meeting_id: UUID,
    request: Request,
    session: Database,
    provider: Provider,
    relevance: Relevance,
) -> dict[str, Any]:
    # Reject client-controlled interpretations; this endpoint derives its input server-side.
    await run_in_threadpool(find_meeting, session, project_id, meeting_id)
    async for part in request.stream():
        if part:
            raise StateError(
                "EVENT_BODY", "Event extraction uses server context; send no body.", 413
            )
    return await run_in_threadpool(
        extract_meeting, session, project_id, meeting_id, provider, relevance
    )
