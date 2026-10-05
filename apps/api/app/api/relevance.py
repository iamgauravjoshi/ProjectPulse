from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_database_session
from app.services.relevance_analysis import analysis_view, analyze_meeting
from app.services.relevance_provider import RelevanceProvider, get_relevance_provider

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/meetings/{meeting_id}/relevance",
    tags=["project relevance"],
)
Database = Annotated[Session, Depends(get_database_session)]
Provider = Annotated[RelevanceProvider, Depends(get_relevance_provider)]


@router.get("")
def read(
    project_id: UUID,
    meeting_id: UUID,
    session: Database,
    provider: Provider,
    page: Annotated[int, Query(ge=1, le=100)] = 1,
    outcome: Literal["ALL", "RELEVANT", "IGNORED", "UNCERTAIN"] = "ALL",
) -> dict[str, Any]:
    return analysis_view(session, project_id, meeting_id, provider, page=page, outcome=outcome)


@router.post("")
def analyze(
    project_id: UUID, meeting_id: UUID, session: Database, provider: Provider
) -> dict[str, Any]:
    return analyze_meeting(session, project_id, meeting_id, provider)
