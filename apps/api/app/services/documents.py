from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, Document, DocumentChunk
from app.domain.chunks import chunk_segments
from app.domain.document_parse import parse_document
from app.domain.manual_state import StateError
from app.repositories.audit import AuditRepository
from app.services.project_access import LOCAL_DEMO_ACTOR_ID, require_project_access


def document_view(
    doc: Document, *, duplicate: bool = False, detail: bool = False
) -> dict[str, Any]:
    view = {
        "id": str(doc.id),
        "projectId": str(doc.project_id),
        "filename": doc.filename,
        "format": doc.format,
        "byteSize": doc.byte_size,
        "createdAt": doc.created_at.isoformat(),
        "uploadedBy": str(doc.uploaded_by),
        "duplicate": duplicate,
        "segmentCount": len(doc.segments),
        "indexStatus": doc.index_status,
        "indexError": doc.index_error,
        "indexedChunks": doc.indexed_chunks,
    }
    if detail:
        view["segments"] = doc.segments
    return view


def find_document(
    session: Session, project_id: UUID, document_id: UUID, *, lock: bool = False
) -> Document:
    require_project_access(session, project_id)
    query = select(Document).where(Document.project_id == project_id, Document.id == document_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    doc = session.scalar(query)
    if doc is None:
        raise StateError("DOCUMENT_NOT_FOUND", "Document not found.", 404)
    return doc


def list_documents(session: Session, project_id: UUID) -> list[dict[str, Any]]:
    require_project_access(session, project_id)
    return [
        document_view(x)
        for x in session.scalars(
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at.desc(), Document.id)
        )
    ]


def upload_document(
    session: Session, project_id: UUID, filename: str, raw: bytes
) -> dict[str, Any]:
    require_project_access(session, project_id)
    digest = sha256(raw).hexdigest()
    query = select(Document).where(
        Document.project_id == project_id, Document.content_hash == digest
    )
    existing = session.scalar(query)
    if existing:
        return document_view(existing, duplicate=True)
    name, extension, segments = parse_document(filename, raw)
    try:
        specs = chunk_segments(segments)
    except ValueError:
        raise StateError(
            "CHUNK_BUDGET", "Document has too many sections. Split it before uploading."
        ) from None
    try:
        with session.begin_nested():
            doc = Document(
                project_id=project_id,
                filename=name,
                format=extension,
                content_hash=digest,
                raw_bytes=raw,
                segments=segments,
                byte_size=len(raw),
                uploaded_by=LOCAL_DEMO_ACTOR_ID,
            )
            session.add(doc)
            session.flush()
            session.add_all(
                [DocumentChunk(project_id=project_id, document_id=doc.id, **spec) for spec in specs]
            )
            AuditRepository(session, project_id).append(
                AuditEvent(
                    project_id=project_id,
                    actor_id=LOCAL_DEMO_ACTOR_ID,
                    action="DOCUMENT_UPLOADED",
                    entity_type="document",
                    entity_id=doc.id,
                    payload={"filename": name, "contentHash": digest, "byteSize": len(raw)},
                )
            )
    except IntegrityError:
        existing = session.scalar(query)
        if existing:
            return document_view(existing, duplicate=True)
        raise
    session.commit()
    return document_view(doc)


def delete_document(session: Session, project_id: UUID, document_id: UUID) -> None:
    with session.begin_nested():
        doc = find_document(session, project_id, document_id, lock=True)
        AuditRepository(session, project_id).append(
            AuditEvent(
                project_id=project_id,
                actor_id=LOCAL_DEMO_ACTOR_ID,
                action="DOCUMENT_DELETED",
                entity_type="document",
                entity_id=doc.id,
                payload={"filename": doc.filename, "contentHash": doc.content_hash},
            )
        )
        session.delete(doc)
        session.flush()
    session.commit()
