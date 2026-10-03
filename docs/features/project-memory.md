# Canonical project memory

Status: Phase 2 started on `phase/2-project-memory`, based on verified Phase 1.

## Purpose and user problem

Maintain a trusted, manually editable project baseline and retrieve relevant
document evidence. Users need structured state before comparing future meeting
statements with it. Documents remain evidence; uploads do not silently change truth.

## Scope and checkpoints

1. Theme checkpoint: switch shared tokens, avatars and favicon to purple; verify
   text contrast and existing browser flows, document and push before CRUD work.
2. Step 2.1: create/read/update/delete requirements, decisions, milestones, risks,
   commitments and dependencies. First validate the scoped transactional API; then
   implement the browser editor and feature E2E flow. Push each tested checkpoint.
3. Step 2.2: validate/parse/store PDF, DOCX, TXT and Markdown documents; handle empty,
   malformed, oversized and duplicate uploads, scoped lists and deletion.
4. Step 2.3: provenance-preserving chunks and pgvector embeddings, provider interface,
   model metadata and repeatable indexing without changing canonical records.
5. Step 2.4: bounded project context search combining structured matches and semantic
   document retrieval; return source locations and verify project isolation.

## Acceptance criteria

- Human-initiated CRUD covers all six required record types and persists on reload.
- Backend membership checks precede every read/write; hidden/missing records share
  the same response, and references cannot point into another project.
- Writes and append-only audit events commit together; stale versions are rejected.
- Invalid forms, unavailable backend, successful save and explicit delete confirmation
  have clear UI feedback; new/edit dialogs support keyboard focus and Escape.
- Confirmed decisions remain distinct from proposals; no AI-generated state is added.
- Valid document uploads preserve page/section text and project/document identities.
- Deleting a document removes its chunks/index entries; duplicates do not re-embed.
- Context search is bounded, relevant, project-scoped and honest when embeddings
  are unconfigured or unavailable. No fabricated vectors or relevance claims.
- Full phase E2E and static/database checks pass before merge into `main`.

## Non-goals

No transcripts, event extraction, AI state mutation, governance automation, external
task writes, production identity or executable desktop application in this phase.

## Architecture

FastAPI owns validation, membership checks, SQLAlchemy transactions, audit and
document/search services. Next.js provides typed forms and thin same-origin transport.
Domain logic lives outside React. Provider calls remain behind a backend interface;
parsing uses open-source libraries, embeddings use configured server-side credentials.

## Data model changes

Manual CRUD uses existing canonical tables. Later steps add project documents and
source-preserving chunks, content hashes, vector fields and embedding model metadata
through explicit Alembic revisions. Existing seed identities and edits are preserved.

## API changes

Project-scoped canonical write routes, then document upload/list/delete/index routes
and bounded context search. Exact request contracts are recorded at each checkpoint.

Step 2.1a implements `/api/v1/projects/{projectId}/state/{kind}` for the six
whitelisted kinds: `requirements`, `decisions`, `milestones`, `risks`, `commitments`,
`dependencies`. GET lists records; POST creates human baseline records. GET/PUT/
DELETE at `/{recordId}` handle individual records. PUT accepts
`{expectedVersion, values}` (complete editable fields), and DELETE requires the
`expectedVersion` query parameter. Server-owned IDs, provenance, speaker/confidence,
actor and confirmation timestamps cannot be submitted as editable fields.

Create/edit/delete and their actor-attributed audit events commit together. Updates
and deletes lock the row and reject stale versions with 409. Cross-project IDs are
hidden; invalid references return 422. Referenced records cannot be deleted until
their links are removed (409). Manual confirmation is explicit through the status;
proposals remain unconfirmed. The local actor is still the seeded product owner.

## UI changes

Purple shared tokens and favicon; a manual project-state editor; document library;
source-aware context search. Existing overview/attention views refresh after writes.

## AI behavior

Embeddings support retrieval only. Uploaded documents and search results cannot
change canonical state. Live provider checks require a configured key and allowed
network destination; mocked provider tests are reported separately from live results.

## Edge cases

Empty baseline, missing owners/dates, stale edits, constrained deletes, references
outside a project, malformed/empty files, duplicate upload, parser failure, provider
failure, incompatible embedding models and documents with no extractable text.

## Security considerations

Fixed local demo actor remains development-only. Never accept actor/source/version
metadata as authoritative from the browser. Validate upload formats and bounded
sizes, keep keys server-side, use fixed proxy destinations, and sanitize failures.
Preserve existing local database credentials and volumes. No public deployment.

## Testing performed

Phase 1 was verified on the latest `main`: GitHub CI passed, including Windows
dependency/audit checks. Current Phase 2 commands, results and regressions are in
[phase-2-results.md](../testing/phase-2-results.md).

## Known limitations

Phase 2 is in progress. Live embeddings require a server-side provider key; this
environment currently reports no configured provider credentials. No production auth.

## Future improvements

Use this confirmed baseline and source-aware retrieval for transcript relevance,
project deltas, evidence-backed review and decision governance in later phases.

### Manual-state browser editor

`view=state` is bookmarkable; `kind` selects one of the six record types. Create and
edit dialogs expose only editable fields, with project-scoped relation options.
Unassigned owners/dates stay unresolved. Decisions default to Discussion; explicit
Confirmed establishes human truth. Delete asks for confirmation and retains audit
history. The overview reloads persisted state after each successful mutation.
Failures preserve the draft; stale versions offer an explicit reload before editing
again. Mutation requests are never automatically retried. Radix dialogs trap focus,
support Escape and restore focus; mobile forms scroll within the viewport.

The same-origin Next transport checks incoming browser Origin against Host (Next
may internally rewrite request URLs), validates UUID/kind/version and bounds JSON
bodies to 64 KiB. Backend membership and field/reference/version checks remain the
final authority. Authentication is still the fixed local demo member; production
identity and deployment remain outside Phase 2.

### Documents: storage, API and safeguards

Migration `0003_documents` stores project-owned evidence: immutable content SHA-256,
original bytes (PostgreSQL BYTEA), sanitized display filename, uploader, timestamps
and parsed page/section/text segments (JSONB). This small local application avoids
object-storage infrastructure; BYTEA is suitable only for the bounded demo budget.
A unique `(project_id, content_hash)` prevents duplicates, including concurrent
uploads. Upload and delete each append an atomic audit event; duplicate upload
returns the existing document without another event. Canonical state is untouched.

`GET/POST /api/v1/projects/{id}/documents` lists/uploads. POST sends raw file bytes
with the filename query parameter, allowing streaming size enforcement before a
multipart parser could spool arbitrary input. `GET/DELETE /documents/{documentId}`
returns traceable extracted text or deletes evidence. Original binary bytes are
retained but never exposed by the JSON API. UUIDs, membership and project ownership
are checked; no filesystem extraction, path writes or client-supplied project scope.

Parsers: pypdf (PDF pages), python-docx (headings/paragraphs/tables), UTF-8 decoding
(TXT/Markdown headings). Limits: 5 MiB upload, 200,000 extracted characters, 200 PDF
pages, bounded PDF stream decompression/page tree/form invocations, DOCX zip entry/
expanded-size/compression-ratio limits. Encrypted, malformed, blank and image-only
PDFs fail clearly. OCR, legacy `.doc`, rich rendering and unbounded files are outside
scope. DOCX section headings are retained; page numbers are unavailable because DOCX
pagination requires a rendering engine. Text is rendered as escaped text, never
uploaded HTML. A document can be uploaded again after deletion; retained audit
history records both events.

`view=documents` provides upload progress, errors, duplicate feedback, a source-text
viewer with page/section labels and explicit delete confirmation. Empty and retry
states remain usable on mobile. Gemini indexing follows as a separate checkpoint.
