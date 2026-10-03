"""Bounded scoped retrieval; canonical truth and source evidence remain distinct."""

import re
from typing import Any
from uuid import UUID

from sqlalchemy import case, literal, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.db.models import Document, DocumentChunk
from app.domain.manual_state import RecordKind, StateError
from app.services.embeddings import EmbeddingProvider, normalized_vector
from app.services.manual_state import SPECS, projection
from app.services.project_access import require_project_access

STOP_WORDS = {
    "what",
    "is",
    "the",
    "a",
    "an",
    "for",
    "to",
    "of",
    "and",
    "in",
    "we",
    "our",
    "does",
    "how",
    "which",
    "can",
    "are",
    "about",
    "was",
}
STATUSES = {
    RecordKind.REQUIREMENTS: ["ACTIVE"],
    RecordKind.DECISIONS: ["CONFIRMED"],
    RecordKind.MILESTONES: ["PLANNED", "AT_RISK"],
    RecordKind.RISKS: ["OPEN"],
    RecordKind.COMMITMENTS: ["OPEN", "IN_PROGRESS"],
    RecordKind.DEPENDENCIES: ["PENDING", "READY", "BLOCKED"],
}
FACT_KEYS = {
    "status",
    "phase",
    "decisionStatus",
    "impactArea",
    "date",
    "severity",
    "ownerId",
    "dueDate",
    "dependencyId",
    "blockedMilestoneId",
}


def terms_for(query: str) -> list[str]:
    return list(dict.fromkeys(x for x in re.findall(r"\w+", query.lower()) if x not in STOP_WORDS))[
        :8
    ]


def excerpt(text: str, terms: list[str]) -> str:
    positions = [text.lower().find(term) for term in terms if term in text.lower()]
    start = max(0, min(positions) - 100) if positions else 0
    return text[start : start + 600]


def lexical_score(columns: list[Any], terms: list[str]) -> ColumnElement[int]:
    score: ColumnElement[int] = literal(0)
    for term in terms:
        condition = columns[0].icontains(term, autoescape=True)
        for column in columns[1:]:
            condition = condition | column.icontains(term, autoescape=True)
        score = score + case((condition, 1), else_=0)
    return score


def evidence_view(chunk: DocumentChunk, doc: Document, terms: list[str]) -> dict[str, Any]:
    return {
        "kind": "document",
        "id": str(chunk.id),
        "projectId": str(chunk.project_id),
        "documentId": str(doc.id),
        "title": doc.filename,
        "excerpt": excerpt(chunk.raw_text, terms),
        "canonical": False,
        "page": chunk.page,
        "section": chunk.section,
        "segmentIndex": chunk.metadata_json["segmentIndex"],
        "start": chunk.metadata_json["start"],
        "end": chunk.metadata_json["end"],
    }


def search_project_context(
    session: Session, project_id: UUID, query: str, provider: EmbeddingProvider, limit: int = 8
) -> dict[str, Any]:
    require_project_access(session, project_id)
    query = query.strip()
    if not query or len(query) > 400 or not 1 <= limit <= 8:
        raise StateError("INVALID_QUERY", "Enter a query of 1–400 characters and a limit of 1–8.")
    has_vectors = (
        session.scalar(
            select(DocumentChunk.id)
            .join(
                Document,
                (Document.project_id == DocumentChunk.project_id)
                & (Document.id == DocumentChunk.document_id),
            )
            .where(
                DocumentChunk.project_id == project_id,
                Document.index_status == "INDEXED",
                DocumentChunk.embedding_model == provider.model,
                DocumentChunk.embedding.is_not(None),
            )
            .limit(1)
        )
        is not None
    )
    semantic_status = "unavailable" if not provider.available else "not_indexed"
    session.commit()
    vector: list[float] | None = None
    if provider.available and has_vectors:
        try:
            vectors = provider.embed([query], query=True)
            if len(vectors) != 1:
                raise StateError("EMBEDDING_INVALID", "Invalid query embedding.", 503)
            vector = normalized_vector(vectors[0])
            semantic_status = "ready"
        except StateError:
            semantic_status = "failed"
    # Read current baseline/evidence after any external call, rechecking membership.
    require_project_access(session, project_id)
    terms = terms_for(query)
    candidates: dict[str, dict[str, Any]] = {}
    ranks: dict[str, float] = {}

    def add(item: dict[str, Any], rank: int, weight: float = 1) -> None:
        key = f"{item['kind']}:{item['id']}"
        candidates[key] = item
        ranks[key] = ranks.get(key, 0) + weight / (60 + rank)

    if terms:
        for kind, spec in SPECS.items():
            model = spec.model
            status = getattr(model, "decision_status" if kind == RecordKind.DECISIONS else "status")
            score = lexical_score([model.title, model.description], terms)
            records = session.scalars(
                select(model)
                .where(model.project_id == project_id, status.in_(STATUSES[kind]), score > 0)
                .order_by(score.desc(), model.updated_at.desc(), model.id)
                .limit(8)
            )
            for rank, record in enumerate(records, 1):
                dto = projection(kind, record)
                add(
                    {
                        "kind": "record",
                        "id": str(record.id),
                        "projectId": str(project_id),
                        "entityType": kind.value,
                        "title": record.title,
                        "excerpt": excerpt(record.description, terms),
                        "canonical": True,
                        "facts": {k: v for k, v in dto.items() if k in FACT_KEYS},
                    },
                    rank,
                    1.2,
                )
        score = lexical_score([Document.filename, DocumentChunk.raw_text], terms)
        rows = session.execute(
            select(DocumentChunk, Document)
            .join(
                Document,
                (Document.project_id == DocumentChunk.project_id)
                & (Document.id == DocumentChunk.document_id),
            )
            .where(DocumentChunk.project_id == project_id, score > 0)
            .order_by(score.desc(), DocumentChunk.id)
            .limit(16)
        )
        for rank, (chunk, doc) in enumerate(rows, 1):
            add(evidence_view(chunk, doc, terms), rank)
    if vector is not None:
        distance = DocumentChunk.embedding.cosine_distance(vector)
        rows = session.execute(
            select(DocumentChunk, Document)
            .join(
                Document,
                (Document.project_id == DocumentChunk.project_id)
                & (Document.id == DocumentChunk.document_id),
            )
            .where(
                DocumentChunk.project_id == project_id,
                Document.index_status == "INDEXED",
                DocumentChunk.embedding_model == provider.model,
                DocumentChunk.embedding.is_not(None),
                distance < 0.6,
            )
            .order_by(distance, DocumentChunk.id)
            .limit(16)
        )
        for rank, (chunk, doc) in enumerate(rows, 1):
            add(evidence_view(chunk, doc, terms), rank)
    matches: list[dict[str, Any]] = []
    per_doc: dict[str, int] = {}
    for key in sorted(candidates, key=lambda key: (-ranks[key], key)):
        item = candidates[key]
        if item["kind"] == "document":
            doc_id = item["documentId"]
            if per_doc.get(doc_id, 0) >= 2:
                continue
            per_doc[doc_id] = per_doc.get(doc_id, 0) + 1
        matches.append(item)
        if len(matches) == limit:
            break
    return {
        "projectId": str(project_id),
        "query": query,
        "semanticStatus": semantic_status,
        "matches": matches,
    }


# Internal tool name from the product brief; implementation follows Python naming conventions.
searchProjectContext = search_project_context
