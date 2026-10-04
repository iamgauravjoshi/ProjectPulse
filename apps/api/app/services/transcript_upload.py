from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MeetingParticipant, Utterance
from app.domain.manual_state import StateError
from app.services.meetings import audit, detail, find_meeting
from app.services.transcript_adapters import (
    FileTranscriptSource,
    TranscriptAdapter,
)


def upload_transcript(
    session: Session,
    project_id: UUID,
    meeting_id: UUID,
    filename: str,
    raw: bytes,
    adapter: TranscriptAdapter[FileTranscriptSource],
) -> dict[str, Any]:
    find_meeting(session, project_id, meeting_id)
    parsed = adapter.parse(FileTranscriptSource(filename, raw))
    digest = sha256(raw).hexdigest()
    with session.begin_nested():
        meeting = find_meeting(session, project_id, meeting_id, lock=True)
        if meeting.transcript_hash == digest:
            return {**detail(session, project_id, meeting_id), "duplicate": True}
        if meeting.transcript_hash:
            raise StateError(
                "TRANSCRIPT_EXISTS",
                "This meeting has a transcript. Create another meeting for a different source.",
                409,
            )
        existing = session.scalars(
            select(MeetingParticipant).where(
                MeetingParticipant.project_id == project_id,
                MeetingParticipant.meeting_id == meeting_id,
            )
        ).all()
        participants = {x.speaker_key: x for x in existing}
        new_keys = {x.speaker_key for x in parsed.utterances if x.speaker_key} - participants.keys()
        if len(participants) + len(new_keys) > 100:
            raise StateError(
                "PARTICIPANT_LIMIT", "Registered and transcript speakers exceed 100 participants."
            )
        for row in parsed.utterances:
            if row.speaker_key and row.speaker_key not in participants:
                participant = MeetingParticipant(
                    project_id=project_id,
                    meeting_id=meeting_id,
                    speaker_key=row.speaker_key,
                    display_name=row.speaker,
                )
                session.add(participant)
                session.flush()
                participants[row.speaker_key] = participant
        session.add_all(
            [
                Utterance(
                    project_id=project_id,
                    meeting_id=meeting_id,
                    participant_id=participants[row.speaker_key].id if row.speaker_key else None,
                    sequence=sequence,
                    speaker_label=row.speaker,
                    timestamp_ms=row.timestamp_ms,
                    end_ms=row.end_ms,
                    text=row.text,
                    confidence=row.confidence,
                )
                for sequence, row in enumerate(parsed.utterances)
            ]
        )
        meeting.transcript_filename = parsed.filename
        meeting.transcript_format = parsed.format
        meeting.transcript_hash = digest
        meeting.transcript_bytes = raw
        audit(
            session,
            meeting,
            "TRANSCRIPT_UPLOADED",
            {
                "filename": parsed.filename,
                "contentHash": digest,
                "utteranceCount": len(parsed.utterances),
                "byteSize": len(raw),
            },
        )
        session.flush()
    session.commit()
    return {**detail(session, project_id, meeting_id), "duplicate": False}
