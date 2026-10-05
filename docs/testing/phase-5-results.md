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

Next: Step 5.2 scoped runs/candidates/evidence, explicit processing API and real
PostgreSQL migration/integration checks.
