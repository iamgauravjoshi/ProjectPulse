from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_database_session
from app.services.context_search import search_project_context
from app.services.embeddings import EmbeddingProvider, get_embedding_provider

router = APIRouter(prefix="/api/v1/projects/{project_id}/context", tags=["context"])


@router.get("/search")
def search(
    project_id: UUID,
    query: Annotated[str, Query(min_length=1, max_length=400)],
    session: Annotated[Session, Depends(get_database_session)],
    provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    limit: Annotated[int, Query(ge=1, le=8)] = 8,
) -> dict[str, Any]:
    return search_project_context(session, project_id, query, provider, limit)
