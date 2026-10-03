# Phase 0 checkpoint results

Date: 3 October 2026 (Asia/Calcutta). Phase 0 complete.
Historical baseline: [current-state assessment](../architecture/current-state.md).

## Step 0.2 — Architecture proposal

Implemented: finalized [architecture](../architecture/proposed-architecture.md),
[data model](../architecture/data-model.md), [testing strategy](strategy.md), and
[foundation ADR](../decisions/ADR-001-foundation.md). No application/schema code
was introduced in this checkpoint.

Acceptance walkthroughs:

| Scenario | Design trace | Result |
| --- | --- | --- |
| SSO Phase 2 → Phase 1 request | Requirement baseline → utterance evidence → scope candidate/delta → explicit review → versioned update + audit | Supports the required flow without automatic mutation |
| November 24 → November 10 proposal | Milestone date → meeting evidence → timeline delta → review; old date persists until confirmed | Proposal remains distinct from truth |
| John promises credentials | Utterance speaker attribution → candidate owner resolution → review → commitment | Speaker and owner remain separate fields |
| Dev/QA propose one retry | Provisional decision → membership/required-role review → missing product owner → unresolved review | Missing reviewer blocks confirmation |
| Async/sync CSV disagreement | Separate decision/evidence records → conflict record → review | Supersession cannot silently erase conflict history |
| Another project's evidence ID | Project-scoped lookup and composite foreign key → reject | Design prevents cross-project linkage |
| Invalid/unavailable AI response | Adapter validation/error → failed detector status → partial results retained | Does not update canonical state or discard unrelated results |

Review confirmed one backend, one relational/vector database, server-side secrets,
bounded retrieval, adapters at integration boundaries, explicit migration stages,
separate interpretation/evidence/truth, and foundation checks without model keys.

Verification: documentation links, fenced blocks, whitespace and phase scope are
checked before the completion report. Mermaid receives source review; visual
rendering is not claimed. Unit/integration/browser tests are not applicable to
this documentation-only step. Existing application checks remain unavailable
until Step 0.3a creates the manifests.

Environment prerequisite: managed local Docker daemon reports 28.4.0; Compose is
2.40.3. HTTP network policy is now observed `enforced` with the package-manager
preset. This does not prove individual package downloads or PostgreSQL startup.

Regressions: no application behavior exists yet; changes are documentation only.
Next checkpoint: Step 0.3a, reproducible technical skeleton.

## Step 0.3a — Reproducible technical skeleton

Implemented: Next.js/React/TypeScript/Tailwind frontend, FastAPI `/health/live`,
npm/uv lockfiles, ESLint/Prettier/TypeScript and Ruff/mypy/pytest configuration,
ignored artifacts, environment examples, and setup README.

Checks executed:

| Check | Command (in corresponding app directory) | Result |
| --- | --- | --- |
| Locked frontend install | `npm ci --offline --cache /tmp/contextboard-npm --no-audit --no-fund` | Passed, 373 packages |
| Frontend production build | `NEXT_TELEMETRY_DISABLED=1 npm run build` | Passed, Next.js 16.3.8 |
| Frontend lint/type/format | `npm run lint`, `npm run typecheck`, `npm run format:check` | All passed |
| Locked backend install | `uv sync --frozen --offline` | Passed |
| Backend lint/format/type | `uv run --no-sync ruff check .`, `uv run --no-sync ruff format --check .`, `uv run --no-sync mypy` | All passed |
| API contract unit test | `uv run --no-sync pytest -m 'not integration' -q` | 1 passed, no warnings |

The test proves liveness works with no database configuration. Reviewed frontend
source/configuration contains no server-side secrets or database credentials.
The technical page does not implement Phase 1 workspace behavior.

Environment notes: dependency downloads and TestClient required the execution
tool's network permission (including the event-loop socket used by TestClient).
An initial restricted test process stalled; it was stopped and rerun successfully
with that permission. uv uses `/tmp/contextboard-uv` because the environment's
default home cache is read-only. Downloads preserve proxy/TLS verification.
The installed ESLint dependency emits an upstream deprecation notice during install;
lint executes without warnings. Backend TestClient uses the supported `httpx2`
dependency to avoid a Starlette deprecation warning.

Acceptance: reproducible locked installs, working production build, all static
checks and no-database liveness test pass. Regression review: only Phase 0 skeleton
behavior introduced; no product features or canonical writes exist yet. No database
migrations/integration/browser tests are claimed for this checkpoint.
Next checkpoint: Step 0.3b, PostgreSQL and migration plumbing.

## Step 0.3b — PostgreSQL and migration plumbing

Implemented: localhost PostgreSQL 17/pgvector 0.8.1 Compose service pinned to image
digest, environment settings, SQLAlchemy engine/session handling, Alembic plumbing,
`0001_vector`, safe `/health/ready`, and guarded disposable-database fixtures.
The database is local, and the integration database is `contextboard_test`.

Executed `alembic upgrade head` and `alembic current` against the fresh development
database: `0001_vector (head)`. Ran Ruff lint/format, mypy and
`TEST_DATABASE_URL=.../contextboard_test uv run --no-sync pytest -q`:
**2 unit/HTTP tests and 3 real-PostgreSQL integration tests passed, no warnings**.

Integration checks verify extension installation, full rollback/reapply, readiness
before/after migration, refusal to take ownership of pre-existing pgvector, and
connection return after an exception. The rejection check leaves the pre-existing
extension intact. Unit checks cover database-independent liveness and sanitized
503 responses. Alembic configuration was updated to avoid its legacy-path warning.

Acceptance: migrations, supported rollback, readiness/failure behavior and session
cleanup verified. README includes database and isolated-test setup. Regression
review: liveness still succeeds without using the database; no workspace/AI feature
or canonical model has been introduced. Next: Step 0.3c, canonical schema and scoped
repositories.

## Step 0.3c — Canonical schema and scoped repositories

Implemented: `0002_canonical` creates 11 tables for users, projects, membership,
requirements, decisions, commitments, risks, milestones, dependencies, open questions
and audit events. Models are split by responsibility. Shared constraints enforce
nonblank titles, valid statuses/provenance, positive versions and in-project foreign
keys. Decision confirmation requires a timestamp; speaker and owner are separate.

Internal repositories require project scope and expose a minimal versioned manual
rename operation. Audit access is append/read only. The caller owns transactions;
no public CRUD or AI write path is implemented.

Checks: Ruff lint/format and mypy pass. Real PostgreSQL run of `pytest -q` reports
**2 unit/HTTP tests and 43 integration tests passed, no warnings**. Tests cover:

- All seven canonical record types round-trip with provenance/version/UTC timestamps.
- Another project cannot read, rename or add records through scoped repositories.
- Cross-project owners, speakers, dependencies, milestones and supersession are rejected.
- Invalid statuses, roles, phases, provenance, confidence, versions and blank titles fail.
- Confirmed timestamps, self-supersession, duplicate memberships and normalized email constraints.
- Version increments, stale-write rejection, distinct speaker/owner and audit scope.
- Full transaction failure rolls back project, canonical record and audit event.
- Base and canonical migrations downgrade/reapply, and model/schema/type/default comparison is clean.

Development database migrated to `0002_canonical`; `alembic check` reports no new
upgrade operations. Migration SQL and dependency order reviewed. Acceptance met;
existing health checks continue to pass. No seed or later-phase feature introduced.
Next: Step 0.3d, deterministic demo seed.

## Step 0.3d — Deterministic demo seed

Implemented: explicit `uv run python -m app.seed` command and transactional service
with stable UUIDs for one Client Portal Modernization project, four stakeholders,
nine canonical baseline records and one seed audit event. Baseline launch is
24 November 2026; SSO stays Phase 2. Credentials belong to John with no fabricated
due date/speaker/confidence. Decisions establish PostgreSQL, synchronous CSV export
and three payment retries. Security review is a pending dependency, risk and question.

Checks: Ruff lint/format, mypy and all backend tests pass:
**2 unit/HTTP tests and 46 PostgreSQL integration tests, no warnings**. New tests
verify exact values/counts/provenance, repeated seed preserving manually edited
phase/version/source, and rollback of every inserted record after a mid-seed failure.

Ran the CLI twice against the development database and verified one project, SSO
Phase 2 and three baseline confirmed decisions. No duplicates or reset occurred.
All source labels identify a human-established demo baseline; no fabricated meetings
or AI interpretations exist. Acceptance met and prior schema/repository/health tests
remain passing. Next: Step 0.3e, full foundation verification and phase report.

## Step 0.3e — Full foundation verification

Implemented: Playwright desktop/mobile and real-API smoke tests, production server
startup/teardown, CI workflow, favicon, and completed setup/check documentation.
Frontend type checking now explicitly runs `next typegen` so a first build is not
a prerequisite. Test setup additionally refuses populated test databases before
any migration operation; a regression test verifies the refusal preserves data.

Final executed checks:

| Check | Result |
| --- | --- |
| Fresh frontend locked install from cache (`npm ci --offline ...`) | Passed, 373 packages |
| `npm run typecheck` with generated Next types removed beforehand | Passed; regenerates types then checks TypeScript |
| `npm run lint`, `npm run format:check` | Passed |
| `NEXT_TELEMETRY_DISABLED=1 npm run build` | Passed, production build |
| `uv sync --frozen --offline` | Passed |
| Ruff lint/format and mypy | Passed, 23 application source files type-checked |
| `TEST_DATABASE_URL=.../contextboard_test uv run --no-sync pytest -q` | 49 passed: 2 unit/HTTP + 47 PostgreSQL integration |
| `alembic check` | No schema upgrade operations detected |
| `UV_CACHE_DIR=/tmp/contextboard-uv PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e` | 2 passed |

The browser run uses actual Chromium, production Next.js on port 3010 and FastAPI
on port 8010. It verifies title/content, desktop/mobile visibility, no horizontal
overflow or browser errors, and healthy liveness/readiness against migrated
PostgreSQL. Both application processes stop after the run.

An initial browser run failed because of a missing favicon resource (404); adding
the routed SVG favicon resolved it. The passing rerun retains strict console-error
checks. A mobile screenshot was visually inspected for readable type and spacing.
The SVG is valid XML. Runtime color-variable notices are tooling messages, not
browser errors. The installed ESLint version emits a deprecation notice on install;
lint itself is clean. No external CI run is claimed.

Reviewed all 63 reviewable repository files: no whitespace diagnostics, local
documentation links resolve, code is split by responsibility, and `.env`, virtual
environment, npm dependencies and build/test artifacts are ignored. No product
feature or live provider operation from a later phase was introduced.

Acceptance: every foundation gate passes. Regression review: liveness remains
database-independent, unsafe test database use is rejected, source provenance is
explicit, and seed edits/transaction semantics remain verified.

## PHASE 0 COMPLETE

Implemented: architecture, reproducible frontend/backend tooling, PostgreSQL and
pgvector, explicit migrations, project-scoped repositories, deterministic demo
seed, health contracts, browser smoke checks and CI configuration.

Files changed: `apps/web/` (shell/config/lockfile/browser tests), `apps/api/`
(health/config/domain/models/repositories/migrations/seed/tests/lockfile),
`compose.yaml`, `.env.example`, `.gitignore`, `.github/workflows/checks.yml`,
`README.md`, and architecture/testing/decision/roadmap documents.

Database changes: `0001_vector` enables pgvector; `0002_canonical` adds 11 relational
tables with named checks, scoped foreign keys and indexes. Development database
has one seeded demo project. The isolated test database is separate and empty of
canonical data outside test transactions. Destructive rollback checks did not touch
the development database.

Tests: Unit/HTTP **2 passed**; integration **47 passed**; E2E **2 passed**.
Build/static/format checks passed. No application test warnings in the final backend run.

Manual verification: CLI seed run twice; baseline project/SSO/decision counts checked;
migration SQL/foreign keys/dependency order reviewed; mobile screenshot inspected;
localhost binding and ignored secrets/artifacts checked.

Known limitations: local prototype with no production authentication or public
business endpoints. Workspace, documents, transcripts, embeddings, AI providers,
review/governance workflow and task integration remain in their later phases.
One primary stakeholder role per member. Audit is append-only through repository
interfaces, not tamper-proof at database privilege level. Extension ownership guard
requires online migrations; offline SQL generation is not supported for that first
revision. Remote CI execution and visual Mermaid rendering are unverified.

Documentation: [setup](../../README.md), [architecture](../architecture/proposed-architecture.md),
[data model](../architecture/data-model.md), [strategy](strategy.md),
[ADR](../decisions/ADR-001-foundation.md), [plan](../architecture/phase-0-plan.md),
and [future roadmap](../roadmap/future-features.md).

Ready for next phase: **Yes**. Next proposed step: Phase 1, Step 1.1, app shell.
Stop at this phase boundary; no Phase 1 implementation has begun.
