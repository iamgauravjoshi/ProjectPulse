"""Project-scoped document evidence."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_documents"
down_revision: str | None = "0002_canonical"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(240), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("raw_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("segments", postgresql.JSONB(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
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
        sa.UniqueConstraint("project_id", "id"),
        sa.UniqueConstraint("project_id", "content_hash"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["project_id", "uploaded_by"], ["project_members.project_id", "project_members.user_id"]
        ),
        sa.CheckConstraint("byte_size > 0 AND byte_size <= 5242880", name="byte_size_bounds"),
    )
    op.create_index("ix_documents_project_id", "documents", ["project_id"])


def downgrade() -> None:
    op.drop_table("documents")
