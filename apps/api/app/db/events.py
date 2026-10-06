"""Cited extraction candidates stored separately from confirmed project state."""

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
from app.domain.events import EventKind, StatementKind


class EventExtraction(ProjectOwned, Base):
    __tablename__ = "event_extractions"
    __table_args__ = (
        UniqueConstraint("project_id", "meeting_id", "id"),
        UniqueConstraint("project_id", "meeting_id", "cache_key"),
        ForeignKeyConstraint(
            ["project_id", "meeting_id", "relevance_analysis_id"],
            [
                "relevance_analyses.project_id",
                "relevance_analyses.meeting_id",
                "relevance_analyses.id",
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
            "eligible_segments BETWEEN 0 AND 10000 AND api_calls >= 0 AND input_tokens >= 0 "
            "AND output_tokens >= 0 AND usage_reported_calls BETWEEN 0 AND api_calls "
            "AND latency_ms >= 0",
            name="extraction_bounds",
        ),
        CheckConstraint(
            "(processing_token IS NULL) = (processing_started_at IS NULL)", name="processing_lease"
        ),
        Index(
            "ix_event_extractions_project_meeting_created", "project_id", "meeting_id", "created_at"
        ),
        Index(
            "ix_event_extractions_relevance", "project_id", "meeting_id", "relevance_analysis_id"
        ),
    )
    meeting_id: Mapped[UUID]
    relevance_analysis_id: Mapped[UUID]
    created_by: Mapped[UUID]
    cache_key: Mapped[str] = mapped_column(String(64))
    context_fingerprint: Mapped[str] = mapped_column(String(64))
    extractor_version: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(80))
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    eligible_segments: Mapped[int]
    api_calls: Mapped[int] = mapped_column(default=0, server_default="0")
    input_tokens: Mapped[int] = mapped_column(default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(default=0, server_default="0")
    usage_reported_calls: Mapped[int] = mapped_column(default=0, server_default="0")
    latency_ms: Mapped[int] = mapped_column(default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(String(80))
    processing_token: Mapped[UUID | None]
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExtractedSegment(ProjectOwned, Base):
    __tablename__ = "extracted_segments"
    __table_args__ = (
        UniqueConstraint("project_id", "meeting_id", "extraction_id", "utterance_id"),
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
            ["project_id", "meeting_id", "utterance_id"],
            ["utterances.project_id", "utterances.meeting_id", "utterances.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("event_count BETWEEN 0 AND 4", name="event_count_bounds"),
        Index(
            "ix_extracted_segments_project_meeting_source",
            "project_id",
            "meeting_id",
            "utterance_id",
        ),
    )
    meeting_id: Mapped[UUID]
    extraction_id: Mapped[UUID]
    utterance_id: Mapped[UUID]
    event_count: Mapped[int]


class ProjectEventCandidate(ProjectOwned, Base):
    __tablename__ = "project_event_candidates"
    __table_args__ = (
        UniqueConstraint("project_id", "meeting_id", "id"),
        UniqueConstraint("project_id", "meeting_id", "id", "extraction_id"),
        UniqueConstraint("project_id", "meeting_id", "extraction_id", "utterance_id", "ordinal"),
        ForeignKeyConstraint(
            ["project_id", "meeting_id", "extraction_id", "utterance_id"],
            [
                "extracted_segments.project_id",
                "extracted_segments.meeting_id",
                "extracted_segments.extraction_id",
                "extracted_segments.utterance_id",
            ],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "kind IN (" + ", ".join(repr(x.value) for x in EventKind) + ")", name="kind_values"
        ),
        CheckConstraint(
            "statement IN (" + ", ".join(repr(x.value) for x in StatementKind) + ")",
            name="statement_values",
        ),
        CheckConstraint("status = 'CANDIDATE'", name="candidate_only"),
        CheckConstraint(
            "confidence BETWEEN 0 AND 1 AND ordinal BETWEEN 0 AND 3", name="event_bounds"
        ),
        CheckConstraint(
            "length(trim(title)) BETWEEN 1 AND 240 AND "
            "length(trim(description)) BETWEEN 1 AND 1600",
            name="text_bounds",
        ),
        CheckConstraint(
            "owner_mention IS NULL OR length(trim(owner_mention)) BETWEEN 1 AND 120",
            name="owner_bounds",
        ),
        CheckConstraint(
            "due_date_text IS NULL OR length(trim(due_date_text)) BETWEEN 1 AND 120",
            name="date_wording_bounds",
        ),
        Index(
            "ix_event_candidates_extraction_kind",
            "project_id",
            "meeting_id",
            "extraction_id",
            "kind",
        ),
    )
    meeting_id: Mapped[UUID]
    extraction_id: Mapped[UUID]
    utterance_id: Mapped[UUID]
    ordinal: Mapped[int]
    kind: Mapped[str] = mapped_column(String(30))
    statement: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="CANDIDATE", server_default="CANDIDATE")
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(String(1600))
    confidence: Mapped[float]
    owner_mention: Mapped[str | None] = mapped_column(String(120))
    due_date_text: Mapped[str | None] = mapped_column(String(120))


class EventCandidateEvidence(ProjectOwned, Base):
    __tablename__ = "event_candidate_evidence"
    __table_args__ = (
        UniqueConstraint("project_id", "meeting_id", "candidate_id", "utterance_id"),
        ForeignKeyConstraint(
            ["project_id", "meeting_id", "candidate_id"],
            [
                "project_event_candidates.project_id",
                "project_event_candidates.meeting_id",
                "project_event_candidates.id",
            ],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["project_id", "meeting_id", "utterance_id"],
            ["utterances.project_id", "utterances.meeting_id", "utterances.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("length(trim(quote)) BETWEEN 1 AND 500", name="quote_bounds"),
        Index(
            "ix_event_evidence_project_meeting_source", "project_id", "meeting_id", "utterance_id"
        ),
    )
    meeting_id: Mapped[UUID]
    candidate_id: Mapped[UUID]
    utterance_id: Mapped[UUID]
    quote: Mapped[str] = mapped_column(String(500))
