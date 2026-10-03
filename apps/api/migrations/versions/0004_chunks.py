"""Provenance-preserving vector document chunks."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy.dialects import postgresql

revision: str = "0004_chunks"
down_revision: str | None = "0003_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("index_status", sa.String(20), nullable=False, server_default="PENDING"),
    )
    op.add_column("documents", sa.Column("index_error", sa.String(80), nullable=True))
    op.add_column(
        "documents", sa.Column("indexed_chunks", sa.Integer(), nullable=False, server_default="0")
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page", sa.Integer()),
        sa.Column("section", sa.String(240)),
        sa.Column("raw_text", sa.String(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("embedding", Vector(768)),
        sa.Column("embedding_model", sa.String(80)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "document_id", "chunk_index"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["project_id", "document_id"],
            ["documents.project_id", "documents.id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "chunk_index >= 0 AND length(raw_text) > 0 AND length(raw_text) <= 1000",
            name="chunk_bounds",
        ),
        sa.CheckConstraint(
            "(embedding IS NULL) = (embedding_model IS NULL)", name="embedding_provenance"
        ),
    )
    op.create_index("ix_document_chunks_project_id", "document_chunks", ["project_id"])


def downgrade() -> None:
    op.drop_table("document_chunks")
    for column in ["indexed_chunks", "index_error", "index_status"]:
        op.drop_column("documents", column)
