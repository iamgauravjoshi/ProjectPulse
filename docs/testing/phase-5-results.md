# Phase 5 checkpoint results

Started 5 October 2026 (Asia/Calcutta). Branch:
`phase/5-project-event-extraction`, based on completed main `eabde14`.
Feature and acceptance plan: [event extraction](../features/event-extraction.md).

## Step 5.1 — complete

Added strict seven-kind event contracts, proposal/statement/question/negation
distinctions, source windows, exact primary/neighbor quote validation and literal
nullable owner/date mentions. Added provider-independent `EventProvider` and a
bounded Gemini REST adapter, using the existing server-only key and independently
configurable `GEMINI_EVENT_MODEL`. Missing configuration and malformed, blocked,
truncated, foreign-source or partial responses fail safely. No canonical write,
new dependency, API, persistence or UI is introduced at this checkpoint.

Added 16 manually labeled synthetic examples covering every event kind, missing
ownership/dates, relative dates, negation, proposals, speaker/owner distinction,
Unicode and no-event output. These exercise contracts; no live quality is inferred.

Validation commands from `apps/api`, using the existing Python 3.12 environment:

- `.venv/Scripts/python.exe -m pytest -m "not integration" -q --tb=short`:
  **134 passed**, including **26 new extraction cases**; 173 database cases excluded.
- `.venv/Scripts/python.exe -m ruff check .`: passed.
- `.venv/Scripts/python.exe -m ruff format --check .`: passed.
- `.venv/Scripts/python.exe -m mypy`: passed, **60 source files**.

Regression review confirms earlier non-database suites pass; existing identities,
canonical records, database volumes and configuration secrets remain untouched.
Live Gemini quality is not tested; provider transport tests use synthetic responses.
Checkpoint publication uses the authenticated GitHub connector because local Git
push credentials were unavailable in the preceding maintenance checkpoint. Its
published Git tree must equal the tested local tree. Main remains unchanged.

Step 5.1 published as `725dc8c`; both CI jobs passed (run `37355202369`).

## Step 5.2 — complete

Migration `0007_events` adds extraction runs, completed segments (including zero
events), candidate records and exact evidence links. Composite foreign keys enforce
project/meeting isolation; candidates have only CANDIDATE status. GET/POST meeting
events use server context and current RELEVANT source classifications. Each action
processes at most one bounded batch. Saved IDs are stable, completed segments are
cached, stale context is labeled, and active leases prevent duplicate processing.
Database locks are released before provider calls. Changed context, malformed output,
source deletion, superseded leases and audit failures cannot partially save candidates.

- Complete real-PostgreSQL API suite: **331 passed in 113.40 seconds**, including
  **24 new integration cases** plus the Step 5.1 contract tests.
- Full migration downgrade/reapply and migrated-schema/model comparison passed.
- Ruff check and format check passed (**91 files**); mypy passed (**63 source files**).
- Regression review: existing API suites pass; integration assertions verify
  canonical categories are unchanged and cross-project access is rejected.

The suite completed without failures. Development database and existing volumes
have not been reset or migrated by these tests. Provider cases use injection; live
Gemini semantic quality remains unverified. Next: Step 5.3 UI and phase acceptance.

Step 5.2 published as `bdfad0d`; both CI jobs passed (run `37357087101`).

## Step 5.3 — complete, 6 October 2026

Added the shared-design-system Project Event Candidates panel, server proxy and
validated browser contracts. Extraction requires current relevance, handles one
batch per explicit action, and exposes pending/processed/no-event coverage without
claiming full-meeting completion. Saved candidates show kind, statement, confidence,
review notice, independent speaker provenance, literal owner/date wording and exact
primary/neighbor citations. Filters, pagination, stale context, usage, empty/error
states and keyboard/mobile flows are implemented. No confirmation/application flow
or canonical write is introduced.

Added `app.check_events`: default validates 16 labeled contracts without an AI call;
`--live` performs one explicitly requested synthetic smoke evaluation, reports field
mismatches/usage and preserves project data. The live quality procedure is documented;
no successful live model evaluation is claimed by this report.

Final local acceptance:

- Full API regression suite against disposable PostgreSQL: **333 passed in 41.96s**,
  including **26 event integration cases** and **26 event contract cases**.
- Ruff check and format check passed (**93 files**); mypy passed (**64 source files**).
- Development database `alembic check`: no pending schema differences after additive
  migration `0007_events`. Full test-database downgrade/reapply and schema checks pass.
- Frontend ESLint, typecheck, Prettier and production Next.js build: passed.
- Frontend unit suite: **61 passed**, including **12 event boundary cases**.
- Feature-wide production-browser regression: **70 passed in 2.9 minutes**, including
  **9 new event scenarios**. Browser scenarios inject only the test event provider;
  normal relevance/document missing-key behavior is still exercised.
- Screenshot capture scenario: passed; desktop and 375px mobile panels visually
  reviewed. Images are in `docs/features/images/events-{desktop,mobile}.png`.
- `npm audit --audit-level=high`: **0 vulnerabilities**.
- Default fixture-check command: **16 examples valid**, no model called. Missing-key
  live-mode check reports `EVENT_PROVIDER_UNAVAILABLE`, zero evaluated; expected
  nonzero exit. Production missing-key API behavior is independently tested.
- Original **31 pre-existing records** retain their table fingerprints before and
  after the additive development migration and browser scenarios. Existing seed
  identities, canonical values, `.env` and database volumes are preserved.

An initial browser outage assertion matched duplicated relevance/transcript text;
the selector now targets source evidence and passes in the full suite. One concurrent
unit run timed out in the existing deep-brace glob regression; the independent full
unit rerun passed. No timeout increase or unrelated implementation change was made.

Regression review confirms saved IDs/cache, partial batches, zero-event completion,
literal provenance, active/expired/superseded leases, context changes, source deletion,
cross-project/meeting isolation and audit/save rollback. Live semantic accuracy remains
unverified; summaries require human judgment. Current local demo identity is unchanged.

## Completion delivery

Implementation, acceptance and documentation are complete for all three phase steps.
The final tested checkpoint is delivered through
[PR #7](https://github.com/iamgauravjoshi/ProjectPulse/pull/7). Publication verifies its
Git tree matches the committed local tree. Merge requires successful `foundation`
and `windows-frontend-audit` jobs on the final PR head. Main receives only the completed
phase; `phase/5-project-event-extraction` is retained for history. Stop after that merge.
Phase 6 is not authorized.
