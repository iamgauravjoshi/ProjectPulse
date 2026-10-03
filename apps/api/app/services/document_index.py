from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, DocumentChunk
from app.domain.chunks import chunk_segments
from app.domain.manual_state import StateError
from app.repositories.audit import AuditRepository
from app.services.documents import document_view, find_document
from app.services.embeddings import EmbeddingProvider, normalized_vector
from app.services.project_access import LOCAL_DEMO_ACTOR_ID


def chunks_for(session: Session, project_id: UUID, document_id: UUID) -> list[DocumentChunk]:
    return list(
        session.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.project_id == project_id, DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
    )


def index_document(
    session: Session, project_id: UUID, document_id: UUID, provider: EmbeddingProvider
) -> dict[str, Any]:
    with session.begin_nested():
        doc = find_document(session, project_id, document_id, lock=True)
        chunks = chunks_for(session, project_id, document_id)
        if (
            doc.index_status == "INDEXED"
            and chunks
            and all(x.embedding is not None and x.embedding_model == provider.model for x in chunks)
        ):
            return document_view(doc)
        if not chunks:
            try:
                specs = chunk_segments(doc.segments)
            except ValueError:
                raise StateError("CHUNK_BUDGET", "Document exceeds the indexing budget.") from None
            chunks = [
                DocumentChunk(project_id=project_id, document_id=document_id, **spec)
                for spec in specs
            ]
            session.add_all(chunks)
        doc.index_status = "PENDING"
        doc.index_error = None
        doc.indexed_chunks = 0
        session.flush()
        texts = [x.raw_text for x in chunks]
    # Release DB locks before making any external calls.
    session.commit()
    try:
        vectors = provider.embed(texts)
        if len(vectors) != len(texts):
            raise StateError(
                "EMBEDDING_INVALID", "Embedding provider returned invalid vectors.", 503
            )
        vectors = [normalized_vector(x) for x in vectors]
    except StateError as error:
        with session.begin_nested():
            doc = find_document(session, project_id, document_id, lock=True)
            doc.index_status = "UNAVAILABLE" if error.code == "EMBEDDINGS_UNAVAILABLE" else "FAILED"
            doc.index_error = error.code
        session.commit()
        raise
    with session.begin_nested():
        doc = find_document(session, project_id, document_id, lock=True)
        chunks = chunks_for(session, project_id, document_id)
        if doc.index_status == "INDEXED" and all(
            x.embedding_model == provider.model for x in chunks
        ):
            return document_view(doc)
        if len(chunks) != len(vectors):
            raise StateError("INDEX_CHANGED", "Document indexing changed. Reload and retry.", 409)
        for chunk, vector in zip(chunks, vectors, strict=True):
            chunk.embedding = vector
            chunk.embedding_model = provider.model
        doc.index_status = "INDEXED"
        doc.index_error = None
        doc.indexed_chunks = len(chunks)
        AuditRepository(session, project_id).append(
            AuditEvent(
                project_id=project_id,
                actor_id=LOCAL_DEMO_ACTOR_ID,
                action="DOCUMENT_INDEXED",
                entity_type="document",
                entity_id=document_id,
                payload={"chunks": len(chunks), "model": provider.model, "dimensions": 768},
            )
        )
        session.flush()
    session.commit()
    return document_view(doc)
