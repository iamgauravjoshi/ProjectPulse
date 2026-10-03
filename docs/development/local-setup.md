# Run ProjectPulse on your laptop

The source built in this chat lives in a cloud workspace at
`/workspace/ProjectPulse`. Cloning the GitHub repository creates an independent
local copy on your laptop. Your local database starts with the same explicit demo
seed; cloud database contents and ignored configuration are not copied by Git.

## Prerequisites

Install Git, Node.js 22 or newer with npm, Python 3.12, uv, and Docker Desktop
(or Docker Engine with Compose). Start Docker before running the setup commands.
The shell examples use Bash; on Windows use Git Bash or WSL with Docker integration.

## First-time setup

Clone the completed phase branch into your chosen folder:

```sh
git clone --branch main https://github.com/iamgauravjoshi/ProjectPulse.git
cd ProjectPulse
cp .env.example .env
docker compose --project-name projectpulse up -d --wait
```

Preserve an existing `.env` instead of replacing it. The supplied database
credentials are only for local development. PostgreSQL runs on port 54329.

Install the backend, migrate the local database, and create the demo baseline:

```sh
cd apps/api
uv sync --frozen
uv run alembic upgrade head
uv run python -m app.seed
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Keep this terminal running. Open a second terminal at the cloned `ProjectPulse`
folder and start the frontend:

```sh
cd apps/web
npm ci
npm run dev
```

Open [ProjectPulse](http://localhost:3000). Select Client Portal Modernization.
The overview should show one active requirement, three confirmed decisions,
one open commitment, one open risk and two follow-ups.

The API is at [localhost:8000](http://localhost:8000/docs);
[readiness](http://localhost:8000/health/ready) should return `{"status":"ok"}`.
No AI provider key is required for Phases 0 and 1.

## Later starts and stops

Start the database from the repository root with
`docker compose --project-name projectpulse up -d --wait`, then run the backend
and frontend commands in separate terminals. Install and migrate again only when
dependencies or migrations change. Repeating the seed preserves existing edits.

Use Ctrl+C in each application terminal to stop the frontend/backend. From the
repository root, `docker compose --project-name projectpulse stop` stops the
database while keeping its data. Do not remove its volume as routine cleanup.

## Troubleshooting

- If Docker is unavailable, start Docker Desktop and retry Compose.
- If the overview cannot load, check API readiness, migrations and seeding first.
- Next.js forwards requests to `http://127.0.0.1:8000` by default. For a different
  backend address, set server-side `API_BASE_URL` in the frontend process or
  `apps/web/.env.local`; the repository-root `.env` is not loaded by Next.js.
- If port 3000 is occupied, stop the other server or use the URL printed by Next.js.
- If Python is not installed, use `uv python install 3.12`, then retry `uv sync`.

## Upgrading an existing local installation

Keep your existing `.env` and its database credentials/name. Renaming the product
does not require renaming a PostgreSQL role or database. Seed UUIDs are stable, so
existing bookmarks, memberships and edited baseline records remain valid.

Before changing the Compose project name to `projectpulse`, find the existing
database's volume name in Docker Desktop (container details → mounts). Set
`POSTGRES_DATA_VOLUME` in your existing `.env` to that exact volume name. Stop the
old database container, then start the new Compose project using the commands above.
This reuses the existing data instead of initializing another database. Do not
delete the original volume or overwrite your `.env` with the new sample.

Once a phase has merged, update your local source with `git fetch origin` followed
by `git switch main` and `git pull --ff-only origin main`. Preserve any uncommitted
local work before switching branches.

## How people use the application

ProjectPulse is a web application. Developers run the frontend/backend locally;
after a hosted deployment, users open the application URL in a browser and select
a project. The current version supports inspecting its baseline and follow-ups.
Later phases add editing, transcript import and evidence-backed human review.
Users will not need Node, Python or Docker to access a hosted version. A Windows
executable is outside the current product plan.

The current workspace is a local prototype with a fixed demo identity. State
editing, transcript ingestion and AI review actions are not implemented yet.
See the [Phase 1 report](../testing/phase-1-results.md) and
[test commands](../../README.md#checks).
