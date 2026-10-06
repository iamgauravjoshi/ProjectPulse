"""Comparison history and proposed deltas, independent of canonical tables."""

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


class DeltaComparisonRun(ProjectOwned, Base):
    __tablename__ = "delta_comparison_runs"
    __table_args__ = (
        UniqueConstraint("project_id", "meeting_id", "id", "extraction_id"),
        UniqueConstraint("project_id", "meeting_id", "cache_key"),
        ForeignKeyConstraint(
            ["project_id", "meeting_id", "extraction_id"],
            [
                "event_extractions.project_id",
                "event_extractions.meeting_id",
                "event_extractions.id",
            ],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["project_id", "created_by"], ["project_members.project_id", "project_members.user_id"]
        ),
        CheckConstraint(
            "length(cache_key) = 64 AND length(context_fingerprint) = 64", name="fingerprints"
        ),
        CheckConstraint(
            "api_calls >= 0 AND input_tokens >= 0 AND output_tokens >= 0 AND latency_ms >= 0 "
            "AND usage_reported_calls BETWEEN 0 AND api_calls",
            name="usage_bounds",
        ),
        CheckConstraint(
            "(processing_token IS NULL) = (processing_started_at IS NULL)", name="processing_lease"
        ),
        Index("ix_delta_runs_project_meeting_created", "project_id", "meeting_id", "created_at"),
    )
    meeting_id: Mapped[UUID]
    extraction_id: Mapped[UUID]
    created_by: Mapped[UUID]
    cache_key: Mapped[str] = mapped_column(String(64))
    context_fingerprint: Mapped[str] = mapped_column(String(64))
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    comparator_version: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(80))
    api_calls: Mapped[int] = mapped_column(default=0, server_default="0")
    input_tokens: Mapped[int] = mapped_column(default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(default=0, server_default="0")
    usage_reported_calls: Mapped[int] = mapped_column(default=0, server_default="0")
    latency_ms: Mapped[int] = mapped_column(default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(String(80))
    processing_token: Mapped[UUID | None]
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectDelta(ProjectOwned, Base):
    __tablename__ = "project_deltas"
    __table_args__ = (
        UniqueConstraint("project_id", "meeting_id", "run_id", "candidate_id"),
        ForeignKeyConstraint(
            ["project_id", "meeting_id", "run_id", "extraction_id"],
            [
                "delta_comparison_runs.project_id",
                "delta_comparison_runs.meeting_id",
                "delta_comparison_runs.id",
                "delta_comparison_runs.extraction_id",
            ],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["project_id", "meeting_id", "candidate_id", "extraction_id"],
            [
                "project_event_candidates.project_id",
                "project_event_candidates.meeting_id",
                "project_event_candidates.id",
                "project_event_candidates.extraction_id",
            ],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "outcome IN ('SAME','CHANGE','NEW','UNCLEAR') AND status = 'CANDIDATE'",
            name="comparison_only",
        ),
        CheckConstraint(
            "confidence BETWEEN 0 AND 1 AND length(trim(reason)) BETWEEN 1 AND 1600",
            name="comparison_bounds",
        ),
        CheckConstraint(
            "(target_id IS NULL) = (target_version IS NULL) "
            "AND (target_version IS NULL OR target_version >= 1)",
            name="target_version",
        ),
        CheckConstraint(
            "(outcome NOT IN ('SAME','CHANGE') OR target_id IS NOT NULL) "
            "AND (outcome <> 'NEW' OR target_id IS NULL)",
            name="target_outcome",
        ),
        Index("ix_project_deltas_run_outcome", "project_id", "meeting_id", "run_id", "outcome"),
    )
    meeting_id: Mapped[UUID]
    extraction_id: Mapped[UUID]
    run_id: Mapped[UUID]
    candidate_id: Mapped[UUID]
    outcome: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="CANDIDATE", server_default="CANDIDATE")
    target_id: Mapped[UUID | None]
    target_version: Mapped[int | None]
    target_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    reason: Mapped[str] = mapped_column(String(1600))
    confidence: Mapped[float]
