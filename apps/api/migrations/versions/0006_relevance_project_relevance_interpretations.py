"""Project relevance interpretations"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_relevance"
down_revision: str | None = "0005_meetings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        op.f("uq_utterances_project_id_meeting_id_id"),
        "utterances",
        ["project_id", "meeting_id", "id"],
    )
    op.create_table(
        "relevance_analyses",
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("cache_key", sa.String(length=64), nullable=False),
        sa.Column("context_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("transcript_hash", sa.String(length=64), nullable=False),
        sa.Column("classifier_version", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("context_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("total_segments", sa.Integer(), nullable=False),
        sa.Column("api_calls", sa.Integer(), server_default="0", nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("usage_reported_calls", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.String(length=80), nullable=True),
        sa.Column("processing_token", sa.Uuid(), nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint(
            "(processing_token IS NULL) = (processing_started_at IS NULL)",
            name=op.f("ck_relevance_analyses_processing_lease"),
        ),
        sa.CheckConstraint(
            "length(cache_key) = 64 AND length(context_fingerprint) = 64 "
            "AND length(transcript_hash) = 64",
            name=op.f("ck_relevance_analyses_fingerprints"),
        ),
        sa.CheckConstraint(
            "total_segments BETWEEN 1 AND 10000 AND api_calls >= 0 AND input_tokens >= 0 "
            "AND output_tokens >= 0 AND usage_reported_calls BETWEEN 0 AND api_calls "
            "AND latency_ms >= 0",
            name=op.f("ck_relevance_analyses_analysis_bounds"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "created_by"],
            ["project_members.project_id", "project_members.user_id"],
            name=op.f("fk_relevance_analyses_project_id_created_by_project_members"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "meeting_id"],
            ["meetings.project_id", "meetings.id"],
            name=op.f("fk_relevance_analyses_project_id_meeting_id_meetings"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_relevance_analyses_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_relevance_analyses")),
        sa.UniqueConstraint(
            "project_id",
            "meeting_id",
            "cache_key",
            name=op.f("uq_relevance_analyses_project_id_meeting_id_cache_key"),
        ),
        sa.UniqueConstraint(
            "project_id",
            "meeting_id",
            "id",
            name=op.f("uq_relevance_analyses_project_id_meeting_id_id"),
        ),
    )
    op.create_index(
        op.f("ix_relevance_analyses_project_id"), "relevance_analyses", ["project_id"], unique=False
    )
    op.create_index(
        "ix_relevance_analyses_project_meeting_created",
        "relevance_analyses",
        ["project_id", "meeting_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "utterance_relevance",
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("utterance_id", sa.Uuid(), nullable=False),
        sa.Column("relevant", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("related_entity_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint(
            "(confidence < 0.65 AND outcome = 'UNCERTAIN') OR (confidence >= 0.65 "
            "AND ((relevant AND outcome = 'RELEVANT') "
            "OR (NOT relevant AND outcome = 'IGNORED')))",
            name=op.f("ck_utterance_relevance_outcome_consistency"),
        ),
        sa.CheckConstraint(
            "method IN ('RULE', 'CONTEXT_RULE', 'GEMINI')",
            name=op.f("ck_utterance_relevance_method_values"),
        ),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 1", name=op.f("ck_utterance_relevance_score_bounds")
        ),
        sa.CheckConstraint(
            "length(trim(reason)) BETWEEN 1 AND 500",
            name=op.f("ck_utterance_relevance_reason_bounds"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "meeting_id", "analysis_id"],
            [
                "relevance_analyses.project_id",
                "relevance_analyses.meeting_id",
                "relevance_analyses.id",
            ],
            name=op.f(
                "fk_utterance_relevance_project_id_meeting_id_analysis_id_relevance_analyses"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "meeting_id", "utterance_id"],
            ["utterances.project_id", "utterances.meeting_id", "utterances.id"],
            name=op.f("fk_utterance_relevance_project_id_meeting_id_utterance_id_utterances"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_utterance_relevance_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_utterance_relevance")),
        sa.UniqueConstraint(
            "analysis_id",
            "utterance_id",
            name=op.f("uq_utterance_relevance_analysis_id_utterance_id"),
        ),
    )
    op.create_index(
        "ix_utterance_relevance_analysis_outcome",
        "utterance_relevance",
        ["analysis_id", "outcome"],
        unique=False,
    )
    op.create_index(
        op.f("ix_utterance_relevance_project_id"),
        "utterance_relevance",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_utterance_relevance_project_meeting_utterance",
        "utterance_relevance",
        ["project_id", "meeting_id", "utterance_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_utterance_relevance_project_meeting_utterance", table_name="utterance_relevance"
    )
    op.drop_index(op.f("ix_utterance_relevance_project_id"), table_name="utterance_relevance")
    op.drop_index("ix_utterance_relevance_analysis_outcome", table_name="utterance_relevance")
    op.drop_table("utterance_relevance")
    op.drop_index("ix_relevance_analyses_project_meeting_created", table_name="relevance_analyses")
    op.drop_index(op.f("ix_relevance_analyses_project_id"), table_name="relevance_analyses")
    op.drop_table("relevance_analyses")
    op.drop_constraint(op.f("uq_utterances_project_id_meeting_id_id"), "utterances", type_="unique")
