from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_read_session
from app.domain.errors import ProjectNotFound
from app.domain.workspace import ProjectSummary, WorkspaceSnapshot
from app.services.project_reads import list_projects, read_workspace

router = APIRouter(prefix="/api/v1/projects", tags=["workspace"])


@router.get("")
def projects(session: Annotated[Session, Depends(get_read_session)]) -> list[ProjectSummary]:
    return list_projects(session)


@router.get("/{project_id}/workspace")
def workspace(
    project_id: UUID, session: Annotated[Session, Depends(get_read_session)]
) -> WorkspaceSnapshot:
    result = read_workspace(session, project_id)
    if result is None:
        raise ProjectNotFound
    return result
