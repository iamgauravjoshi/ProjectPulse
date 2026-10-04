from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, Meeting, MeetingParticipant, ProjectMember, Utterance
from app.domain.manual_state import StateError
from app.domain.meetings import MeetingFields, ParticipantFields
from app.repositories.audit import AuditRepository
from app.services.project_access import LOCAL_DEMO_ACTOR_ID, require_project_access


def audit(session: Session, meeting: Meeting, action: str, payload: dict[str, Any]) -> None:
    AuditRepository(session, meeting.project_id).append(
        AuditEvent(
            project_id=meeting.project_id,
            actor_id=LOCAL_DEMO_ACTOR_ID,
            action=action,
            entity_type="meeting",
            entity_id=meeting.id,
            payload=payload,
        )
    )


def find_meeting(
    session: Session, project_id: UUID, meeting_id: UUID, *, lock: bool = False
) -> Meeting:
    require_project_access(session, project_id)
    query = select(Meeting).where(Meeting.project_id == project_id, Meeting.id == meeting_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    meeting = session.scalar(query)
    if meeting is None:
        raise StateError("MEETING_NOT_FOUND", "Meeting not found.", 404)
    return meeting


def meeting_view(meeting: Meeting) -> dict[str, Any]:
    return {
        "id": str(meeting.id),
        "projectId": str(meeting.project_id),
        "title": meeting.title,
        "startedAt": meeting.started_at.isoformat() if meeting.started_at else None,
        "createdAt": meeting.created_at.isoformat(),
        "createdBy": str(meeting.created_by),
        "transcriptFilename": meeting.transcript_filename,
        "transcriptFormat": meeting.transcript_format,
        "hasTranscript": meeting.transcript_hash is not None,
    }


def list_meetings(session: Session, project_id: UUID) -> list[dict[str, Any]]:
    require_project_access(session, project_id)
    return [
        meeting_view(x)
        for x in session.scalars(
            select(Meeting)
            .where(Meeting.project_id == project_id)
            .order_by(Meeting.created_at.desc(), Meeting.id)
            .limit(200)
        )
    ]


def create_meeting(session: Session, project_id: UUID, fields: MeetingFields) -> dict[str, Any]:
    require_project_access(session, project_id)
    with session.begin_nested():
        meeting = Meeting(
            project_id=project_id, created_by=LOCAL_DEMO_ACTOR_ID, **fields.model_dump()
        )
        session.add(meeting)
        session.flush()
        audit(session, meeting, "MEETING_CREATED", {"title": meeting.title})
    session.commit()
    return meeting_view(meeting)


def participant_view(participant: MeetingParticipant) -> dict[str, Any]:
    return {
        "id": str(participant.id),
        "meetingId": str(participant.meeting_id),
        "displayName": participant.display_name,
        "speakerKey": participant.speaker_key,
        "userId": str(participant.user_id) if participant.user_id else None,
    }


def detail(session: Session, project_id: UUID, meeting_id: UUID) -> dict[str, Any]:
    meeting = find_meeting(session, project_id, meeting_id)
    participants = session.scalars(
        select(MeetingParticipant)
        .where(
            MeetingParticipant.project_id == project_id, MeetingParticipant.meeting_id == meeting_id
        )
        .order_by(MeetingParticipant.created_at, MeetingParticipant.id)
    ).all()
    utterances = session.scalars(
        select(Utterance)
        .where(Utterance.project_id == project_id, Utterance.meeting_id == meeting_id)
        .order_by(Utterance.sequence)
    ).all()
    return {
        **meeting_view(meeting),
        "participants": [participant_view(x) for x in participants],
        "utterances": [
            {
                "id": str(x.id),
                "meetingId": str(x.meeting_id),
                "sequence": x.sequence,
                "speaker": x.speaker_label,
                "speakerId": str(x.participant_id) if x.participant_id else None,
                "timestampMs": x.timestamp_ms,
                "endMs": x.end_ms,
                "text": x.text,
                "confidence": x.confidence,
            }
            for x in utterances
        ],
    }


def add_participant(
    session: Session, project_id: UUID, meeting_id: UUID, fields: ParticipantFields
) -> dict[str, Any]:
    with session.begin_nested():
        meeting = find_meeting(session, project_id, meeting_id, lock=True)
        if meeting.transcript_hash:
            raise StateError(
                "TRANSCRIPT_LOCKED",
                "Participants cannot change after a transcript is uploaded.",
                409,
            )
        if (
            fields.user_id
            and session.scalar(
                select(ProjectMember.user_id).where(
                    ProjectMember.project_id == project_id, ProjectMember.user_id == fields.user_id
                )
            )
            is None
        ):
            raise StateError("PARTICIPANT_MEMBER", "Choose a member of this project.")
        count = (
            session.scalar(
                select(func.count())
                .select_from(MeetingParticipant)
                .where(
                    MeetingParticipant.project_id == project_id,
                    MeetingParticipant.meeting_id == meeting_id,
                )
            )
            or 0
        )
        if count >= 100:
            raise StateError("PARTICIPANT_LIMIT", "A meeting supports at most 100 participants.")
        if session.scalar(
            select(MeetingParticipant.id).where(
                MeetingParticipant.project_id == project_id,
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.speaker_key == fields.speaker_key,
            )
        ):
            raise StateError(
                "SPEAKER_KEY_EXISTS",
                "This speaker key is already registered. Use a distinct key.",
                409,
            )
        participant = MeetingParticipant(
            project_id=project_id, meeting_id=meeting_id, **fields.model_dump()
        )
        session.add(participant)
        session.flush()
        audit(
            session,
            meeting,
            "MEETING_PARTICIPANT_ADDED",
            {"participantId": str(participant.id), "speakerKey": participant.speaker_key},
        )
    session.commit()
    return participant_view(participant)


def delete_meeting(session: Session, project_id: UUID, meeting_id: UUID) -> None:
    with session.begin_nested():
        meeting = find_meeting(session, project_id, meeting_id, lock=True)
        audit(
            session,
            meeting,
            "MEETING_DELETED",
            {"title": meeting.title, "transcriptHash": meeting.transcript_hash},
        )
        session.delete(meeting)
        session.flush()
    session.commit()
