from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.common import ProjectOwned


class DocumentChunk(ProjectOwned, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("project_id", "document_id", "chunk_index"),
        ForeignKeyConstraint(
            ["project_id", "document_id"],
            ["documents.project_id", "documents.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "chunk_index >= 0 AND length(raw_text) > 0 AND length(raw_text) <= 1000",
            name="chunk_bounds",
        ),
        CheckConstraint(
            "(embedding IS NULL) = (embedding_model IS NULL)", name="embedding_provenance"
        ),
    )
    document_id: Mapped[UUID]
    chunk_index: Mapped[int]
    page: Mapped[int | None]
    section: Mapped[str | None] = mapped_column(String(240))
    raw_text: Mapped[str]
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))
    embedding_model: Mapped[str | None] = mapped_column(String(80))
