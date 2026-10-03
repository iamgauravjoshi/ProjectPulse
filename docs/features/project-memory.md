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
