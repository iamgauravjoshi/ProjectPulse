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
