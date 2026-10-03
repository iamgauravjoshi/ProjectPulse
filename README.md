# ProjectPulse

Project intelligence and decision reconciliation. Meetings are evidence; the
project state is the truth.

Phases 0 and 1 are complete. Phase 2 implementation is on
`phase/2-project-memory`; live Gemini acceptance is pending before merge.
It adds audited manual editing, a document library, Gemini indexing and bounded
context search in a purple theme. See the
[project memory feature](docs/features/project-memory.md) and
[Phase 2 results](docs/testing/phase-2-results.md).

The workspace reads the seeded PostgreSQL project
through FastAPI and displays its trusted baseline, stakeholders, delivery
follow-ups and activity. Decisions, commitments and risks have searchable views;
the review inbox separates recorded review requirements from delivery follow-ups.
See the [workspace feature](docs/features/project-workspace.md),
[Phase 1 checkpoint](docs/testing/phase-1-results.md), and
[architecture](docs/architecture/proposed-architecture.md).

## Requirements

Node.js 22+ with npm, Python 3.12 with uv, and Docker Compose for PostgreSQL/pgvector.
Local development only; no
production authentication is implemented.

## Install and run

To get the latest completed phase on your laptop:

```sh
git clone --branch main https://github.com/iamgauravjoshi/ProjectPulse.git
cd ProjectPulse
```

Follow the [local setup guide](docs/development/local-setup.md) for the complete
first-time sequence. The commands below assume the database is already set up.

ProjectPulse runs in a web browser. In development, open localhost; a later hosted
deployment will provide a web URL. A Windows `.exe` is outside the current scope.
The [working agreement](AGENTS.md) requires a push after every tested/documented
step and a merge into `main` only after the entire phase is complete.

Frontend, from `apps/web`:

```sh
npm ci
npm run dev
```

Backend, from `apps/api`:

```sh
uv sync --frozen
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Set up and seed the database below before viewing the project. The frontend
uses a same-origin proxy to FastAPI at `http://127.0.0.1:8000`; set the server-side
`API_BASE_URL` in the frontend process if your backend uses a different address.
The root `.env` configures the backend/Compose; Next.js does not load it automatically.

Open the frontend at `http://127.0.0.1:3000`. API liveness is
`http://127.0.0.1:8000/health/live` and does not need a database or model key.

## Database setup

From the repository root, for first-time local setup:

```sh
cp .env.example .env
docker compose --project-name projectpulse up -d --wait
```

Preserve an existing `.env` instead of overwriting it. The sample password is for
localhost development only. The image is pinned to pgvector 0.8.1/PostgreSQL 17
with a digest. From `apps/api`, apply migrations:

```sh
uv run alembic upgrade head
uv run python -m app.seed
```

`GET /health/ready` requires the expected migration head and pgvector, and returns
503 for unavailable or unmigrated databases. Initial migrations require a fresh
database; the extension migration refuses to take ownership of existing pgvector.

The explicit seed creates one Client Portal Modernization demo project with Phase 2
SSO, 24 November 2026 launch, PostgreSQL, synchronous export, three payment retries,
pending credentials and security review. It is safe to repeat and preserves edits.
It does not invent transcript evidence or AI results.

Create a separate test database once, from the repository root:

```sh
docker compose --project-name projectpulse exec db createdb -U projectpulse projectpulse_test
```

Then, from `apps/api`:

```sh
TEST_DATABASE_URL=postgresql+psycopg://projectpulse:projectpulse_local@127.0.0.1:54329/projectpulse_test uv run pytest
```

Integration tests require an explicit database URL ending in `_test`, reject
databases containing canonical records, and run
migration rollback/reapply only there. Never point them at the development
database. Stopping with `docker compose --project-name projectpulse stop` preserves
local data; do not delete volumes as routine cleanup.

## Checks

From `apps/web`:

```sh
npm run build
npm run lint
npm run typecheck
npm run format:check
npm test
```

From `apps/api`:

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -m 'not integration'
```

For the workspace browser suite, start/migrate/seed the local database first.
From `apps/web`:

```sh
npm run build
npx playwright install chromium
npm run test:e2e
```

Playwright starts production Next.js on port 3010 and FastAPI on port 8010 and
stops them afterwards. It checks project selection, canonical-state views,
attention/review navigation, failure/retry, keyboard behavior, desktop/mobile
rendering and real PostgreSQL readiness. If using an existing Chromium installation, set
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to its absolute path instead of downloading
a browser. The CI workflow is configured for the same static, database and browser
checks. Pushed checkpoints also run in
[GitHub Actions](https://github.com/iamgauravjoshi/ProjectPulse/actions).

To refresh the documented desktop/mobile previews, run the browser suite with
`CAPTURE_WORKSPACE=1`. Screenshots contain only the synthetic seeded demo.

Do not commit `.env`, keys, generated build output or test artifacts. Keep backend
configuration and credentials in server-side environment variables. Authentication,
manual state editing, transcript ingestion and AI review actions remain future work.
