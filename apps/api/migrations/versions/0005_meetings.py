"""Meetings participants and speaker attributed utterances"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_meetings"
down_revision: str | None = "0004_chunks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meetings",
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("transcript_hash", sa.String(length=64), nullable=True),
        sa.Column("transcript_filename", sa.String(length=240), nullable=True),
        sa.Column("transcript_format", sa.String(length=10), nullable=True),
        sa.Column("transcript_bytes", sa.LargeBinary(), nullable=True),
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
            "(transcript_hash IS NULL AND transcript_bytes IS NULL AND transcript_filename "
            "IS NULL AND transcript_format IS NULL) OR (transcript_hash IS NOT NULL AND "
            "length(transcript_hash) = 64 AND "
            "transcript_bytes IS NOT NULL AND octet_length(transcript_bytes) BETWEEN 1 AND "
            "2097152 AND transcript_filename IS NOT NULL AND transcript_format IS NOT NULL AND "
            "transcript_format IN ('txt', "
            "'json', 'vtt'))",
            name=op.f("ck_meetings_transcript_provenance"),
        ),
        sa.CheckConstraint(
            "length(trim(title)) BETWEEN 1 AND 240", name=op.f("ck_meetings_title_bounds")
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "created_by"],
            ["project_members.project_id", "project_members.user_id"],
            name=op.f("fk_meetings_project_id_created_by_project_members"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_meetings_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meetings")),
        sa.UniqueConstraint("project_id", "id", name=op.f("uq_meetings_project_id_id")),
    )
    op.create_index(op.f("ix_meetings_project_id"), "meetings", ["project_id"], unique=False)
    op.create_table(
        "meeting_participants",
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("speaker_key", sa.String(length=160), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
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
            "length(trim(display_name)) BETWEEN 1 AND 120 AND length(trim(speaker_key)) "
            "BETWEEN 1 AND 160",
            name=op.f("ck_meeting_participants_speaker_bounds"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "meeting_id"],
            ["meetings.project_id", "meetings.id"],
            name=op.f("fk_meeting_participants_project_id_meeting_id_meetings"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["project_members.project_id", "project_members.user_id"],
            name=op.f("fk_meeting_participants_project_id_user_id_project_members"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_meeting_participants_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meeting_participants")),
        sa.UniqueConstraint(
            "project_id",
            "meeting_id",
            "id",
            name=op.f("uq_meeting_participants_project_id_meeting_id_id"),
        ),
        sa.UniqueConstraint(
            "project_id",
            "meeting_id",
            "speaker_key",
            name=op.f("uq_meeting_participants_project_id_meeting_id_speaker_key"),
        ),
    )
    op.create_index(
        op.f("ix_meeting_participants_project_id"),
        "meeting_participants",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_meeting_participants_project_id_user_id",
        "meeting_participants",
        ["project_id", "user_id"],
        unique=False,
    )
    op.create_table(
        "utterances",
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("speaker_label", sa.String(length=120), nullable=False),
        sa.Column("timestamp_ms", sa.BigInteger(), nullable=True),
        sa.Column("end_ms", sa.BigInteger(), nullable=True),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
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
            "confidence IS NULL OR confidence BETWEEN 0 AND 1",
            name=op.f("ck_utterances_confidence_bounds"),
        ),
        sa.CheckConstraint(
            "end_ms IS NULL OR (timestamp_ms IS NOT NULL AND end_ms >= timestamp_ms AND "
            "end_ms <= 604800000)",
            name=op.f("ck_utterances_end_bounds"),
        ),
        sa.CheckConstraint(
            "sequence BETWEEN 0 AND 9999 AND length(trim(text)) BETWEEN 1 AND 6000 AND "
            "length(speaker_label) BETWEEN 1 AND 120",
            name=op.f("ck_utterances_utterance_bounds"),
        ),
        sa.CheckConstraint(
            "timestamp_ms IS NULL OR timestamp_ms BETWEEN 0 AND 604800000",
            name=op.f("ck_utterances_timestamp_bounds"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "meeting_id", "participant_id"],
            [
                "meeting_participants.project_id",
                "meeting_participants.meeting_id",
                "meeting_participants.id",
            ],
            name=op.f("fk_utterances_project_id_meeting_id_participant_id_meeting_participants"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "meeting_id"],
            ["meetings.project_id", "meetings.id"],
            name=op.f("fk_utterances_project_id_meeting_id_meetings"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_utterances_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_utterances")),
        sa.UniqueConstraint(
            "project_id",
            "meeting_id",
            "sequence",
            name=op.f("uq_utterances_project_id_meeting_id_sequence"),
        ),
    )
    op.create_index(op.f("ix_utterances_project_id"), "utterances", ["project_id"], unique=False)
    op.create_index(
        "ix_utterances_project_id_meeting_id_participant_id",
        "utterances",
        ["project_id", "meeting_id", "participant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_utterances_project_id_meeting_id_participant_id", table_name="utterances")
    op.drop_index(op.f("ix_utterances_project_id"), table_name="utterances")
    op.drop_table("utterances")
    op.drop_index("ix_meeting_participants_project_id_user_id", table_name="meeting_participants")
    op.drop_index(op.f("ix_meeting_participants_project_id"), table_name="meeting_participants")
    op.drop_table("meeting_participants")
    op.drop_index(op.f("ix_meetings_project_id"), table_name="meetings")
    op.drop_table("meetings")
