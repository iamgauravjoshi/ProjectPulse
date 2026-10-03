from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.api.dependencies import get_database_session
from app.domain.document_parse import MAX_BYTES
from app.domain.manual_state import StateError
from app.services import documents
from app.services.document_index import index_document
from app.services.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.project_access import require_project_access

router = APIRouter(prefix="/api/v1/projects/{project_id}/documents", tags=["documents"])
Database = Annotated[Session, Depends(get_database_session)]


@router.get("")
def list_documents(project_id: UUID, session: Database) -> list[dict[str, Any]]:
    return documents.list_documents(session, project_id)


@router.post("", status_code=201)
async def upload_document(
    project_id: UUID,
    request: Request,
    session: Database,
    filename: Annotated[str, Query(min_length=1, max_length=240)],
) -> dict[str, Any]:
    await run_in_threadpool(require_project_access, session, project_id)
    body = bytearray()
    async for part in request.stream():
        if len(body) + len(part) > MAX_BYTES:
            raise StateError("DOCUMENT_SIZE", "Files must be no larger than 5 MiB.", 413)
        body.extend(part)
    return await run_in_threadpool(
        documents.upload_document, session, project_id, filename, bytes(body)
    )


@router.get("/{document_id}")
def get_document(project_id: UUID, document_id: UUID, session: Database) -> dict[str, Any]:
    return documents.document_view(
        documents.find_document(session, project_id, document_id), detail=True
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(project_id: UUID, document_id: UUID, session: Database) -> Response:
    documents.delete_document(session, project_id, document_id)
    return Response(status_code=204)


@router.post("/{document_id}/index")
def index(
    project_id: UUID,
    document_id: UUID,
    session: Database,
    provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
) -> dict[str, Any]:
    return index_document(session, project_id, document_id, provider)
