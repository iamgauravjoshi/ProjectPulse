from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.api.dependencies import get_database_session
from app.domain.deltas import DeltaOutcome
from app.domain.manual_state import StateError
from app.services.delta_comparison import compare_meeting, delta_view
from app.services.delta_provider import DeltaProvider, get_delta_provider
from app.services.event_provider import EventProvider, get_event_provider
from app.services.meetings import find_meeting
from app.services.relevance_provider import RelevanceProvider, get_relevance_provider

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/meetings/{meeting_id}/deltas", tags=["deltas"]
)
Database = Annotated[Session, Depends(get_database_session)]
Provider = Annotated[DeltaProvider, Depends(get_delta_provider)]
Events = Annotated[EventProvider, Depends(get_event_provider)]
Relevance = Annotated[RelevanceProvider, Depends(get_relevance_provider)]


@router.get("")
def get_deltas(
    project_id: UUID,
    meeting_id: UUID,
    session: Database,
    provider: Provider,
    events: Events,
    relevance: Relevance,
    page: Annotated[int, Query(ge=1, le=400)] = 1,
    outcome: DeltaOutcome | Literal["ALL"] = "ALL",
) -> dict[str, Any]:
    return delta_view(
        session,
        project_id,
        meeting_id,
        provider,
        events,
        relevance,
        page=page,
        outcome=str(outcome),
    )


@router.post("")
async def compare_deltas(
    project_id: UUID,
    meeting_id: UUID,
    request: Request,
    session: Database,
    provider: Provider,
    events: Events,
    relevance: Relevance,
) -> dict[str, Any]:
    await run_in_threadpool(find_meeting, session, project_id, meeting_id)
    async for part in request.stream():
        if part:
            raise StateError("DELTA_BODY", "Comparison uses server context; send no body.", 413)
    return await run_in_threadpool(
        compare_meeting, session, project_id, meeting_id, provider, events, relevance
    )
