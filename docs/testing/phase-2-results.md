# Phase 2 checkpoint results

Started and accepted 3 October 2026 (Asia/Calcutta). All Phase 2 steps and phase-wide
acceptance are complete. Earlier checkpoints below record the evidence and blockers
at that time; the final acceptance section closes the live Gemini blocker.

Feature: [canonical project memory](../features/project-memory.md).
Branch: `phase/2-project-memory`. Base: latest verified Phase 1 `main`, commit
`70789d3`, whose [GitHub CI passed](https://github.com/iamgauravjoshi/ProjectPulse/actions/runs/37127914246).
The Phase 1 dependency audit fix and its Windows compatibility checks are retained.

## Purple theme checkpoint

Implemented: shared purple accent/soft surface tokens, neutral purple canvas/text/
borders, stakeholder avatars using the shared token and a purple P favicon. Existing
warning badges remain amber for distinct meaning. No data/API behavior changed.

Acceptance: normal text contrast is at least 4.5:1 for white on accent, accent on
soft surface, muted text on canvas and primary text on white. Browser and build
checks passed: lint/type/format, production build, 25 frontend unit tests and all
19 browser tests. Desktop/mobile captures were refreshed and visually inspected.
Text contrast ratios are 7.10:1 (white on accent), 6.19:1 (accent on soft),
4.98:1 (muted on canvas) and 13.99:1 (primary on white). No regressions found.
Gemini is the user-selected embedding provider for the later indexing step.

## STEP 2.1a COMPLETE — Scoped manual-state API

Implemented: create/list/get/edit/delete for all six canonical record types;
strict editable-field schemas; server-owned provenance, actor and confirmation
metadata; same-project references; row locks and expected-version checks;
atomic audit/state mutations; sanitized missing/hidden/reference/stale errors.
No schema or seed modification. The browser editor follows in Step 2.1b.

Testing: **103 backend tests passed** (4 unit/HTTP, 99 real PostgreSQL integration),
including 46 new API scenarios. Each record type completes create → read → edit →
delete; all three mutations attribute audit events to the human actor. Invalid
fields and spoofed metadata cannot write; hidden/missing projects and outside record
IDs are protected. Cross-project/unknown owner and dependency references fail.
Stale edits/deletes retain newer values; in-use deletes require explicit unlinking.
Injected audit failures roll back create/edit/delete. A proposal is not inferred
confirmed; an explicit human confirmation creates a timestamp, and returning it to
review removes that timestamp. Ruff lint/format and mypy pass.

Regression review: all Phase 0/1 backend tests remain passing. Foundation browser
smoke passed both cases against the updated API before this checkpoint is pushed. Next step:
2.1b, browser editor and full manual-state E2E acceptance.

## STEP 2.1b COMPLETE — Manual-state browser editor

Implemented bookmarkable six-category editing, scoped relation selectors, explicit
confirmation/deletion, persisted-state refresh and success feedback. Failed writes
preserve drafts; stale writes require explicit reload. Keyboard focus returns to
the opener, and mobile dialogs stay within the viewport. Same-origin transport
checks browser Origin against incoming Host with malformed/cross-origin rejection.

Acceptance: **35 frontend unit tests**, **27 browser tests** (8 new) passed, including
real PostgreSQL create → edit → reload → delete for all six record types. Tests use
unique temporary records, clean them up and verify the seeded SSO phase/three
confirmed decisions remain intact. Audit history remains truthful; the overview
regression test now accepts the actual latest audit actions rather than assuming
the original seed action is always among the ten latest events. All static checks
and production webpack build pass. Turbopack now fails in this cloud environment
when its CSS worker binds a socket (EPERM); the supported webpack builder succeeds.
No application build configuration was changed to conceal that environment issue.
Next checkpoint: Step 2.2 document upload and parsing.

## STEP 2.2 COMPLETE — Project document evidence

Added reversible `0003_documents`, four local open-source parsers, provenance-bearing
text segments, bounded raw-byte upload, same-project reads/deletes, hash deduplication
and atomic audit. Preserved the existing local database/volume with an additive
migration. The browser library supports upload/read/delete, errors, duplicate and
empty feedback, retry and mobile layout. Original bytes are retained in PostgreSQL;
no uploaded content writes canonical state or reaches an AI provider in this step.

Validation: **129 backend tests passed**, including 26 new parsing/PG scenarios.
Schema metadata matches migrated tables; upgrade/downgrade/reapply regressions pass.
All 35 frontend unit tests, lint/types/format and production webpack build pass.
The full 33-case browser run passed 32 cases; the malformed upload case exposed an
ambiguous alert selector due to Next's route announcer. Naming the library alert
fixed that case; all **6 document browser cases passed** on the corrected build,
with the other 27 regression cases already passing. The stream-size guard was
strengthened to check incoming chunk size before accumulation; all 26 document
backend cases passed again. Next: Step 2.3 chunks and Gemini indexing.

## STEP 2.3 IMPLEMENTED — Gemini vector indexing

Added reversible `0004_chunks`, 768-dimensional pgvector storage, source offsets/
page/section metadata, immediate text chunks on new uploads, bounded Gemini REST
provider and explicit indexing UI. Older documents lazily gain chunks when indexed.
Missing key/provider errors retain NULL vectors and honest unavailable/failed status;
retry is explicit. Identical uploads/indexing reuse prior state; deleting evidence
cascades chunks. Provider calls release database locks; deletion during the call
cannot resurrect evidence. Complete vectors/status/index audit save atomically.

Checks: **148 backend tests passed** (19 new chunk/provider/vector scenarios), Ruff
lint/format and strict mypy pass. Provider contract tests verify batching, modern
REST config fields, tasks, dimensions, normalization and safe failures with synthetic
responses. Actual PostgreSQL verifies vectors, scope, cascade, retries, schema
metadata and rollback. All 35 frontend unit tests/static checks and webpack build
pass; **9 document/foundation browser checks pass**, including real unavailable
indexing while evidence remains readable. Browser API explicitly receives an empty
key so automatic tests do not incur external calls.

Live Gemini acceptance remains **pending**: no server key or Google API egress is
configured. Synthetic provider tests are not a live semantic-quality verification.
Keep Phase 2 off main until remaining search and live integration acceptance are
complete. Next implementation checkpoint: Step 2.4 bounded context search.

## STEP 2.4 IMPLEMENTED — Bounded project context search

Implemented internal `searchProjectContext` and a scoped read endpoint, parameterized
current-state text retrieval, actual PostgreSQL cosine retrieval, rank fusion,
model/project/index filters, bounded candidates/excerpts/results and source offsets.
Confirmed decisions remain distinct from other decision states and evidence. Current
baseline/evidence and membership are read after the external query call. No full
project history reaches Gemini, and search performs no state/audit write.

UI: bookmarkable context view, loading/error/retry/empty feedback, explicit semantic
status, separate baseline/evidence cards and links to current records/original source
sections. Queries persist on error; invalid/cross-project payloads are rejected.
Source viewers scroll to cited sections. Synthetic PDF/DOCX browser inputs are made
unique per run so duplicate testing cannot remove a previously uploaded fixture.

Validation: **162 backend tests passed**, including 14 new retrieval scenarios.
These cover real cosine nearest neighbors and irrelevant-vector exclusion, other
projects, current confirmed state, text search before indexing, deleted evidence,
provider fallback, no charge without indexed vectors, query/result/excerpt budgets,
per-document diversity and state changes during a slow query embedding. Ruff checks,
strict mypy and Alembic drift check pass. **37 frontend unit tests and all 37 browser
tests passed**, including the full manual baseline → upload → unavailable indexing →
search → citation → baseline flow and cleanup. Frontend lint/type/format and
production webpack build pass. Full npm audit reports **0 vulnerabilities**.

The final context source anchor and feedback presentation received focused follow-up
browser/static checks; screenshots use synthetic temporary records and are inspected
on desktop/mobile. Setup docs explain phase checkout, additive migrations, browser
usage, server-only Gemini credentials and the remaining live acceptance procedure.

## Acceptance status at the context-search checkpoint — awaiting live verification

All implemented Phase 2 paths pass automated acceptance/regression checks. Gemini
provider contract/vector retrieval tests use synthetic provider responses and real
PostgreSQL; they do **not** establish live Gemini quality or successful authentication.
This cloud runtime reports no secret bindings and restricted package-manager-only
HTTP destinations. To close the phase, configure `GEMINI_API_KEY` server-side and
allow `generativelanguage.googleapis.com`, restart the API, then successfully index a
small document and retrieve a relevant paraphrase with a verified source citation.
No baseline state may change. The exact procedure is in the local setup guide.

Keep the draft phase PR unmerged and main unchanged until that live check passes.
No Phase 3 implementation has started. Turbopack's environment-specific socket EPERM
remains documented; webpack production acceptance passed without changing the normal
build command. CI still verifies the normal build on GitHub runners.

## Indexing correction checkpoint — Laptop invalid-vector report

User reported failed indexing for TXT/PDF after configuring a key on their laptop.
The cloud executor remains separate and has no key/Google destination configured;
local `.env` is sufficient for the laptop backend and requires process restart.

Found a batch REST request mismatch: the adapter nested task/dimension configuration,
while the official `google-genai` 2.28.0 serializer writes `taskType` and
`outputDimensionality` directly on each `requests[]` entry. Corrected both document
and query embeddings. Validation still strictly rejects incompatible/nonfinite/zero
vectors; dimension mismatches now report safe actual/expected counts. No slicing,
padding, fake vectors, database migration or document deletion was introduced.

Regression transport now emulates 3072 defaults when the dimension field is missing,
instead of returning 768 regardless of request shape. New real PostgreSQL scenarios
for TXT and PDF retain failed evidence/chunks and successfully retry through the
actual Gemini adapter with corrected synthetic responses. **165 backend tests pass**;
Ruff lint/format and strict mypy (44 source files) pass. All **9 document/foundation
browser regressions pass** against the updated backend. Frontend code is unchanged.

Added the opt-in `uv run python -m app.check_gemini` diagnostic and a detailed
[laptop setup/recovery guide](../development/gemini-setup.md). The probe checks
both retrieval tasks using synthetic text and prints only key presence/source,
model, dimensions and sanitized failure status. In this cloud executor it correctly
reports missing configuration without sending a request. No SDK was added to the
project dependencies; its serializer was inspected in an isolated temporary install.

At this correction checkpoint, live authentication/indexing/paraphrase verification
still had to run on the user's laptop. That blocker is closed by the user-reported
verification below; automated provider responses remain explicitly synthetic.

## Final Phase 2 acceptance — complete

After receiving the laptop connectivity/indexing recovery procedure, the user
reported "All done". This records **user-reported laptop verification** of the
document/query 768-dimension probe, indexing existing TXT/PDF documents, paraphrase
retrieval, source citation checks and unchanged baseline. The agent did not receive
the private key or independently execute live Google calls on the laptop.

The final code checkpoint is `2ad73f76b66d452a6b663493270dfa0732b3eae9`.
Both [PR CI](https://github.com/iamgauravjoshi/ProjectPulse/actions/runs/37142835278)
and [branch CI](https://github.com/iamgauravjoshi/ProjectPulse/actions/runs/37142832269)
passed on that exact commit, including **165 backend tests, 37 frontend unit tests
and 37 browser tests**, static/database checks, the normal production build and
Windows frontend compatibility/dependency checks. This final acceptance checkpoint
changes documentation only; its CI must pass before merge.

All four project-memory steps and the purple theme are complete. The final
checkpoint is pushed to `phase/2-project-memory` and merged through
[PR #2](https://github.com/iamgauravjoshi/ProjectPulse/pull/2) after checks pass,
under the authorized completed-phase workflow. The phase branch is retained.
No Phase 3 implementation has started. Production authentication, deployment,
large-scale relevance benchmarking and a native executable remain outside scope.
