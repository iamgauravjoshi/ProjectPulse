"""Meeting interpretations stored independently from canonical project records."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.common import ProjectOwned


class RelevanceAnalysis(ProjectOwned, Base):
    __tablename__ = "relevance_analyses"
    __table_args__ = (
        UniqueConstraint("project_id", "meeting_id", "id"),
        UniqueConstraint("project_id", "meeting_id", "cache_key"),
        ForeignKeyConstraint(
            ["project_id", "meeting_id"], ["meetings.project_id", "meetings.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["project_id", "created_by"], ["project_members.project_id", "project_members.user_id"]
        ),
        CheckConstraint(
            "total_segments BETWEEN 1 AND 10000 AND api_calls >= 0 AND "
            "input_tokens >= 0 AND output_tokens >= 0 AND "
            "usage_reported_calls BETWEEN 0 AND api_calls AND latency_ms >= 0",
            name="analysis_bounds",
        ),
        CheckConstraint(
            "length(cache_key) = 64 AND length(context_fingerprint) = 64 "
            "AND length(transcript_hash) = 64",
            name="fingerprints",
        ),
        CheckConstraint(
            "(processing_token IS NULL) = (processing_started_at IS NULL)", name="processing_lease"
        ),
        Index(
            "ix_relevance_analyses_project_meeting_created",
            "project_id",
            "meeting_id",
            "created_at",
        ),
    )
    meeting_id: Mapped[UUID]
    created_by: Mapped[UUID]
    cache_key: Mapped[str] = mapped_column(String(64))
    context_fingerprint: Mapped[str] = mapped_column(String(64))
    transcript_hash: Mapped[str] = mapped_column(String(64))
    classifier_version: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(80))
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    total_segments: Mapped[int]
    api_calls: Mapped[int] = mapped_column(default=0, server_default="0")
    input_tokens: Mapped[int] = mapped_column(default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(default=0, server_default="0")
    usage_reported_calls: Mapped[int] = mapped_column(default=0, server_default="0")
    latency_ms: Mapped[int] = mapped_column(default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(String(80))
    processing_token: Mapped[UUID | None]
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UtteranceRelevance(ProjectOwned, Base):
    __tablename__ = "utterance_relevance"
    __table_args__ = (
        UniqueConstraint("analysis_id", "utterance_id"),
        ForeignKeyConstraint(
            ["project_id", "meeting_id", "analysis_id"],
            [
                "relevance_analyses.project_id",
                "relevance_analyses.meeting_id",
                "relevance_analyses.id",
            ],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["project_id", "meeting_id", "utterance_id"],
            ["utterances.project_id", "utterances.meeting_id", "utterances.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="score_bounds"),
        CheckConstraint("length(trim(reason)) BETWEEN 1 AND 500", name="reason_bounds"),
        CheckConstraint("method IN ('RULE', 'CONTEXT_RULE', 'GEMINI')", name="method_values"),
        CheckConstraint(
            "(confidence < 0.65 AND outcome = 'UNCERTAIN') OR (confidence "
            ">= 0.65 AND ((relevant AND outcome = 'RELEVANT') "
            "OR (NOT relevant AND outcome = 'IGNORED')))",
            name="outcome_consistency",
        ),
        Index("ix_utterance_relevance_analysis_outcome", "analysis_id", "outcome"),
        Index(
            "ix_utterance_relevance_project_meeting_utterance",
            "project_id",
            "meeting_id",
            "utterance_id",
        ),
    )
    meeting_id: Mapped[UUID]
    analysis_id: Mapped[UUID]
    utterance_id: Mapped[UUID]
    relevant: Mapped[bool]
    confidence: Mapped[float]
    reason: Mapped[str] = mapped_column(String(500))
    related_entity_types: Mapped[list[str]] = mapped_column(JSONB)
    outcome: Mapped[str] = mapped_column(String(20))
    method: Mapped[str] = mapped_column(String(20))
