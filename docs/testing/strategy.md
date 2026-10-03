# Testing strategy

See [architecture](../architecture/proposed-architecture.md) and
[Phase 0 results](phase-0-results.md) and [Phase 1 results](phase-1-results.md).
Every implementation checkpoint must record
commands, actual results, acceptance review and regressions before advancement.

## Test levels

| Level | Tool and scope | Phase 0 gate |
| --- | --- | --- |
| Unit/HTTP contract | pytest, FastAPI TestClient; later pure parsing/state logic | Liveness without database; safe readiness failure behavior |
| Integration | pytest + actual PostgreSQL/pgvector + Alembic | Migrate/rollback/reapply, schema drift, constraints, scoped repositories, transaction rollback and seed idempotency |
| Browser E2E | Playwright Chromium | Technical frontend page and real backend readiness; product flows start in later phases |
| Static | ESLint, tsc, Prettier; Ruff, mypy | Build, lint, format and type checks for implemented source |

Documentation-only checkpoints use link/fence/whitespace validation and a design
walkthrough. These do not count as executed application tests. Do not repeat
known failing absent-manifest commands until the manifests exist.

## Database isolation and safeguards

Use a dedicated local test database with a name ending in `_test`; never run
destructive migration checks against the demo/development database. Before any
migration operation, reject a test database that already contains canonical data.
Tests must
require an explicitly supplied `TEST_DATABASE_URL`, validate its name, and fail
clearly if missing. No silent skips or fallback to SQLite.

Initialize a migrated empty database for integration tests, rollback each data test,
and run migration downgrade/reapply tests only in that disposable database.
Migration tests run sequentially. Do not truncate an external database or delete a
volume as an implicit cleanup. Test two projects and outsider user IDs to verify
scoped reads/updates and foreign-key rejection. Test an intentional mid-transaction
failure to prove no partial state or audit record persists.

Use Alembic schema comparison after migrations to detect model/schema drift.
Verify named checks and composite foreign keys by attempting invalid writes, not
just inspecting the model declaration. Check no inferred transcript evidence or
model-generated canonical state exists in the seed.

## Frontend and API execution

Use a production frontend build for the Phase 0 browser smoke when feasible.
Playwright tests live under `apps/web/tests/e2e` so their npm dependencies resolve
within the frontend application. It starts the frontend/backend on local test ports with controlled
configuration. Assert visible content, health status and no browser console errors.
Browser reports/failure screenshots are generated artifacts and ignored by Git.
Explicit synthetic-demo documentation captures live under `docs/features/images`.

Phase 1 adds Vitest domain tests under `apps/web/tests/unit`, isolated from
Playwright by its configured include. Run `npm test`. Check confirmed-versus-
provisional counts, source project IDs, owners, filters and calendar rules. Browser
tests cover the live seeded overview plus deterministic fixtures for loading,
empty/error states, review-required and overdue records. Feature acceptance includes
overview → follow-up → review inbox while the canonical baseline stays unchanged.

Verify liveness remains usable without a database. Readiness uses a short connection
timeout and reports 503 for unavailable or unmigrated databases without exposing
internal exception details. No model key is required for foundation testing.

## Later AI and integration tests

Keep labeled fixtures under `tests/fixtures/ai-evaluation/` when AI phases begin.
Cover irrelevant talk, ambiguous ownership, proposals versus confirmations,
scope/timeline changes, conflicts/non-conflicts, risks and question quality.
The relevance phase adds 30–50 manually labeled utterances and tracks false
positives/negatives. Strict schemas validate mocked model responses in CI.

Live-provider evaluations are optional explicit commands, separate from CI;
record provider/model, prompt version, usage, latency and qualitative failures.
They require server-side keys and must not print secrets or sensitive transcripts.
External task APIs are mocked for retry/idempotency tests.

Later critical browser scenarios cover baseline → transcript → evidence-backed
candidate → explicit confirmation → canonical update, rejection preserving state,
missing reviewer, and conflicting side meetings routed to review.

## Reporting and completion

Write exact commands and counts to the phase results after each step. A check
blocked by environment setup is blocked, not passed. At feature boundaries, run
that feature's end-to-end flow. At Phase 0 completion, report build/static results,
actual unit/integration/browser counts, verified migrations/seed, limitations and
readiness for Phase 1. Stop before implementing the next major phase.
