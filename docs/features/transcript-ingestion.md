# Meetings and speaker-attributed transcript ingestion

Status: Phase 3 in progress on `phase/3-meeting-transcript-ingestion`.

Meetings are evidence, not confirmed baseline changes. A meeting belongs to one
project, has a title and optional timezone-aware start time, and records its human
creator. Participants have stable meeting-local IDs, distinct speaker keys and
optional explicit links to existing project members. Repeated display names are
allowed; membership is never inferred from a name.

Utterances retain a stable UUID, meeting ID, zero-based source sequence, speaker
label snapshot, optional participant ID, optional elapsed milliseconds, optional
end time, original text and optional confidence. Missing time/speaker identity stays
unknown. Project/meeting composite foreign keys enforce isolation in PostgreSQL.
Meeting deletion cascades evidence and participants, while retaining its audit.

## Checkpoints

1. Meeting/participant/utterance schema and scoped audited API; additive migration.
2. Deterministic, bounded structured text/JSON/VTT upload and source provenance.
3. Meeting management, participants, upload and source-linked browser viewer.
4. File adapter contract with future provider boundaries, without external bots.
5. Phase-wide regression/E2E acceptance and completed-phase merge.

Live streaming is optional in the brief and deferred. No AI interpretation,
canonical mutation, meeting bot, external conferencing adapter or audio transcription
is included. The existing fixed local demo actor remains a prototype limitation.

## API implemented in Step 3.1

`/api/v1/projects/{projectId}/meetings` supports list (latest 200) and create.
`/{meetingId}` supports scoped detail and confirmed client-side deletion.
`/{meetingId}/participants` adds a named speaker key and optional project member ID.
Participants are capped at 100 and immutable once a transcript is uploaded.
Writes attribute audit events to the server-owned actor in the same transaction.

Migration `0005_meetings` adds three tables and indexes; preserve your `.env`,
canonical data and database volume. Run `uv run alembic upgrade head` from `apps/api`.
Downgrade checks run only on the guarded disposable test database.
