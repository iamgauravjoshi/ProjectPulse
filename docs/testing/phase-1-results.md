# Phase 1 checkpoint results

Product and command examples use the current ProjectPulse naming. Historical
executions used the original development identifiers before the product rename.

Date: 3 October 2026 (Asia/Calcutta). **Phase 1 complete**.
Feature: [project workspace](../features/project-workspace.md).

## STEP 1.1 COMPLETE — App shell

Implemented: sidebar, accessible Radix project selector/help dialog/mobile drawer,
top navigation, bookmarkable project/view URLs, keyboard and focus behavior,
loading/empty/error/retry/unavailable-project states, server-scoped project list,
validated frontend contracts and a same-origin transport proxy.

Current behavior: the local demo actor sees the seeded project through FastAPI;
navigation reaches labeled content shells. Overview records follow in Step 1.2.
The proxy is transport only; data access and membership queries remain in FastAPI.

Checks executed:

| Check | Command | Result |
| --- | --- | --- |
| Frontend lint/type/format | `npm run lint`, `npm run typecheck`, `npm run format:check` | Passed |
| Production build | `NEXT_TELEMETRY_DISABLED=1 npm run build` | Passed |
| Backend lint/format/type | Ruff lint/format and mypy | Passed |
| Backend tests | `TEST_DATABASE_URL=.../projectpulse_test uv run --no-sync pytest -q` | 53 passed: 3 unit/HTTP + 50 PostgreSQL integration |
| Browser tests | `UV_CACHE_DIR=/tmp/projectpulse-uv PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e` | 10 passed |

New backend tests verify list projection, no new audit writes on reads, membership
filtering, ignoring a browser-supplied actor ID, empty membership and sanitized
dependency failure. Existing migration/seed/constraint tests remain passing.
Browser tests cover keyboard selection/history, active navigation, help dialog
Escape/focus return, mobile navigation, slow fetch/skeleton, error/retry, empty and
malformed lists, unavailable project and unknown-view recovery.

Acceptance review: shell navigation and selector work, all required shell states
are tested, responsive layout has no overflow, and no canonical writes were added.
Database changes: none. Regression review: API health, schema and seed remain
verified; the Phase 0 page test now asserts the real workspace title/shell instead
of the replaced technical placeholder. No AI or CRUD feature implemented.

Documentation updated: feature purpose/scope/architecture/API/state criteria and
this checkpoint report. Next proposed step: 1.2, populated project overview.

## STEP 1.2 COMPLETE — Project overview

Implemented: scoped workspace projection, strict Pydantic/Zod contracts, all six
canonical categories, stakeholder badges, real audit activity, milestone date,
baseline/current-state counts, decision/commitment/risk views with search and status
filters, and explicit empty meeting/review areas. Project-specific loading/error/
retry and malformed/cross-project response rejection are supported.

Backend tests: **56 passed (3 unit/HTTP + 53 PostgreSQL integration)**. New coverage
checks every projection category and scope, empty assigned project, hidden/missing
project equivalence, no audit writes on reads, and no raw audit payload exposure.
Frontend domain tests: **6 passed**, covering confirmed-versus-provisional truth,
completed commitments, source project isolation, calendar dates, unresolved owners,
speaker-versus-owner presentation, status/search filters and mismatched response IDs.
Browser tests: **15 passed**, covering real seeded categories/counts, decision filters,
empty baseline, detail retry and cross-project response rejection as well as Step 1.1.

Build, lint, formatting and type checks pass. Vitest configuration uses `.mts` so
it loads as ESM without the future CommonJS/native-loader diagnostic. Unit tests
are isolated from Playwright by an explicit test-file include.

Acceptance: SSO remains Phase 2, launch remains 24 November 2026, synchronous export
and three retries remain confirmed, credentials remain John-owned without a guessed
date. Provisional decisions are excluded from the trusted baseline. Counts derive
from persisted statuses. No meeting analysis or AI-derived count is fabricated.
Database changes: none. Regression review: migrations, seed, scoped access, health
and all shell states remain verified. Next proposed step: 1.3, needs attention.

## STEP 1.3 COMPLETE — Needs attention and feature acceptance

Implemented: deterministic attention items/counts for explicit review-required
records, overdue commitments, missing due dates and active milestone dependencies;
read-only review inbox; milestone dependency details; links to record views; honest
conflict/evidence placeholders. Mobile header labels wrap without splitting words.
No date, review authority, conflict or canonical write is inferred.

Checks executed:

| Check | Command | Result |
| --- | --- | --- |
| Frontend domain | `npm test` | 19 passed: 6 workspace + 13 attention |
| Frontend static | `npm run lint`, `npm run typecheck`, `npm run format:check` | Passed |
| Production build | `NEXT_TELEMETRY_DISABLED=1 npm run build` | Passed |
| Feature-wide browser suite | `CAPTURE_WORKSPACE=1 UV_CACHE_DIR=/tmp/projectpulse-uv PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e` | 19 passed |
| Final mobile adjustment | Same browser command with `-- tests/e2e/attention.spec.ts tests/e2e/foundation.spec.ts` | 6 passed; screenshots refreshed |

Backend source is unchanged since Step 1.2, where all 56 tests and backend static
checks passed. Attention tests cover past/today/future dates, completed/cancelled
work, Kolkata midnight, explicit review status, active versus completed milestones,
ready versus pending dependencies and empty state. Browser tests verify the full
attention navigation flow, preservation of the baseline, actual overdue/review
fixtures, mobile drawer focus return and a 210-character project name.

Visual verification: inspected [desktop](../features/images/workspace-desktop.png)
and [mobile](../features/images/workspace-mobile.png) full-page captures. Spacing,
status labels, typography and responsive stacking are readable; the stakeholder
row was adjusted after visual review and recaptured. These are synthetic demo data.

Acceptance: seeded workspace has two follow-ups (pending security review and
John's undated credentials commitment), zero overdue commitments, zero explicit
decision reviews, and conflicts awaiting evidence. Review-required decisions stay
outside confirmed truth. Attention links reach commitments/milestones/review views.
Database changes: none. Regression review: all previous browser scenarios passed;
health/readiness and responsive rendering were rerun after the final header change.
Documentation updated: feature behavior/flows/screenshots, README, testing strategy
and this report. Next proposed step: Phase 2, Step 2.1, manual canonical-state CRUD.

## PHASE 1 COMPLETE

Implemented: responsive project shell; scoped, validated project reads; all six
canonical overview categories; stakeholder/activity presentation; searchable
record views; attention rules and read-only review inbox.

Files changed (relative to the Phase 0 checkpoint):

- Frontend `src/app`, `src/components/workspace`, `src/features/workspace`,
  `src/lib/workspace-proxy.ts`, package/lock/config files and browser/domain fixtures.
- Backend `app/api/projects.py`, `app/api/dependencies.py`, `app/domain/workspace.py`,
  `app/domain/errors.py`, `app/services/project_reads.py`, `app/main.py` and read tests.
- `.env.example`, CI checks, README, feature/testing documentation and two screenshots.

Database changes: no schema migration; the naming follow-up below pins existing
seed identities and updates fresh-install metadata without rewriting baseline data.
Tests: **23 unit/HTTP/domain passed** (4 backend + 19 frontend), **53 PostgreSQL
integration passed**, **19 E2E passed**. Production build, lint, formatting and
frontend/backend type checks passed. No pre-existing failures remain.

Manual verification: desktop/mobile screenshot review and a baseline/read-flow
walkthrough. Interaction assertions use actual browser automation. Remote CI was
unverified at the initial local checkpoint; the first published Phase 1 commit
subsequently [passed GitHub Actions](https://github.com/iamgauravjoshi/ProjectPulse/actions/runs/37114685434).
No public deployment was attempted.

Known limitations: fixed local demo identity; no production authentication;
canonical editing, transcript evidence, AI detection and review confirmation are
future phases. Demo timezone is fixed and attention refreshes on snapshot load.

Documentation: [workspace feature](../features/project-workspace.md), this report,
[testing strategy](strategy.md), README and captured views are current.
Ready for next phase: **Yes**. Stop here; Phase 2 is not implemented.

## Phase 1 follow-up — ProjectPulse naming and checkpoint workflow

Completed on 3 October 2026 after the user's product-name and Git-workflow update.

Implemented: ProjectPulse UI/title/help branding and P icon; API title; frontend
and backend package/lock metadata; new-install database/Compose/CI names; seed
email labels; refreshed screenshots and documentation. All 19 installed seed UUIDs
remain unchanged in `app/domain/demo_identity.py`; the read actor uses that shared
identity. Existing database credentials and records are preserved. Compose accepts
an explicit `POSTGRES_DATA_VOLUME` for upgrading an existing local installation.
No database migration or canonical update is required.

`AGENTS.md` records the ongoing workflow: implement, test, document, review and
push EACH step to `phase/<number>-<phase-name>`. Merge into `main` only after every
phase step and feature-wide E2E checks pass. Since the repository has no `main`,
its first publication uses the fully validated final Phase 1 checkpoint. No older
intermediate snapshot is published there. Future phases use pull requests into
that completed-phase base. Phase 2 remains unstarted.

Validation after the rename:

| Check | Result |
| --- | --- |
| Frozen backend install | `UV_CACHE_DIR=/tmp/projectpulse-uv uv sync --frozen` passed |
| Backend Ruff lint/format and mypy | Passed |
| Backend pytest using the explicitly configured empty `_test` database | 57 passed: 4 unit/HTTP + 53 PostgreSQL integration |
| Existing development database reseed inside a rolled-back transaction | Project/member/user/requirement counts unchanged; SSO remains Phase 2 |
| Alembic schema comparison | No new upgrade operations detected |
| Frontend lint/type/format and production build | Passed |
| Frontend domain tests | 19 passed |
| Full browser suite and refreshed captures | 19 passed; desktop/mobile inspected |

The compatibility test pins the installed project and Sarah IDs so a name change
cannot silently duplicate the baseline or strand existing membership. Test and
screenshot refreshes continue to use the existing database through its retained
local configuration; new installs use ProjectPulse defaults.

The application remains a browser-based web product. Local developers run the
stack; hosted users will open a URL. A native Windows executable is outside the
current scope. The [local guide](../development/local-setup.md) explains both use
and upgrading an existing local database volume. Ready for completed-phase merge:
**Yes**. GitHub records the completed-phase publication; local validation is complete.
The first published Phase 1 snapshot passed GitHub Actions; checkpoint updates
also run the same CI workflow before completed-phase publication.

CI follow-up: the rename checkpoint passed remotely. A later documentation-only
checkpoint exposed a race in the existing selector keyboard test (18 of 19 browser
cases passed). The test now waits for the selected option's focus after opening
the menu and for the last option's focus after End before pressing Enter. It uses
neither arbitrary sleeps nor retries. The corrected case passed **10 consecutive
runs**, then the full **19-case browser suite** passed again; frontend static
checks also passed. These corrections are pushed to the same Phase 1 branch before
publishing the completed phase.

Upgrade configuration also supports `POSTGRES_DATA_VOLUME_EXTERNAL=true` so an
existing volume can be reused without changing its Compose ownership. Both fresh
and external-volume Compose configurations validate. Existing baseline records
and credentials are preserved.
