from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.common import ProjectOwned


class Meeting(ProjectOwned, Base):
    __tablename__ = "meetings"
    __table_args__ = (
        UniqueConstraint("project_id", "id"),
        ForeignKeyConstraint(
            ["project_id", "created_by"], ["project_members.project_id", "project_members.user_id"]
        ),
        CheckConstraint("length(trim(title)) BETWEEN 1 AND 240", name="title_bounds"),
        CheckConstraint(
            "(transcript_hash IS NULL AND transcript_bytes IS NULL AND transcript_filename "
            "IS NULL AND transcript_format IS NULL) OR (transcript_hash IS NOT NULL AND "
            "length(transcript_hash) = 64 AND "
            "transcript_bytes IS NOT NULL AND octet_length(transcript_bytes) BETWEEN 1 AND "
            "2097152 AND transcript_filename IS NOT NULL AND transcript_format IS NOT NULL AND "
            "transcript_format IN ('txt', "
            "'json', 'vtt'))",
            name="transcript_provenance",
        ),
    )
    title: Mapped[str] = mapped_column(String(240))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID]
    transcript_hash: Mapped[str | None] = mapped_column(String(64))
    transcript_filename: Mapped[str | None] = mapped_column(String(240))
    transcript_format: Mapped[str | None] = mapped_column(String(10))
    transcript_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)


class MeetingParticipant(ProjectOwned, Base):
    __tablename__ = "meeting_participants"
    __table_args__ = (
        UniqueConstraint("project_id", "meeting_id", "id"),
        UniqueConstraint("project_id", "meeting_id", "speaker_key"),
        ForeignKeyConstraint(
            ["project_id", "meeting_id"], ["meetings.project_id", "meetings.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["project_id", "user_id"], ["project_members.project_id", "project_members.user_id"]
        ),
        CheckConstraint(
            "length(trim(display_name)) BETWEEN 1 AND 120 AND length(trim(speaker_key)) "
            "BETWEEN 1 AND 160",
            name="speaker_bounds",
        ),
        Index("ix_meeting_participants_project_id_user_id", "project_id", "user_id"),
    )
    meeting_id: Mapped[UUID]
    display_name: Mapped[str] = mapped_column(String(120))
    speaker_key: Mapped[str] = mapped_column(String(160))
    user_id: Mapped[UUID | None]


class Utterance(ProjectOwned, Base):
    __tablename__ = "utterances"
    __table_args__ = (
        UniqueConstraint("project_id", "meeting_id", "sequence"),
        UniqueConstraint("project_id", "meeting_id", "id"),
        ForeignKeyConstraint(
            ["project_id", "meeting_id"], ["meetings.project_id", "meetings.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["project_id", "meeting_id", "participant_id"],
            [
                "meeting_participants.project_id",
                "meeting_participants.meeting_id",
                "meeting_participants.id",
            ],
        ),
        CheckConstraint(
            "sequence BETWEEN 0 AND 9999 AND length(trim(text)) BETWEEN 1 AND 6000 AND "
            "length(speaker_label) BETWEEN 1 AND 120",
            name="utterance_bounds",
        ),
        CheckConstraint(
            "timestamp_ms IS NULL OR timestamp_ms BETWEEN 0 AND 604800000", name="timestamp_bounds"
        ),
        CheckConstraint(
            "end_ms IS NULL OR (timestamp_ms IS NOT NULL AND end_ms >= timestamp_ms AND "
            "end_ms <= 604800000)",
            name="end_bounds",
        ),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1", name="confidence_bounds"
        ),
        Index(
            "ix_utterances_project_id_meeting_id_participant_id",
            "project_id",
            "meeting_id",
            "participant_id",
        ),
    )
    meeting_id: Mapped[UUID]
    participant_id: Mapped[UUID | None]
    sequence: Mapped[int]
    speaker_label: Mapped[str] = mapped_column(String(120))
    timestamp_ms: Mapped[int | None] = mapped_column(BigInteger)
    end_ms: Mapped[int | None] = mapped_column(BigInteger)
    text: Mapped[str]
    confidence: Mapped[float | None]
