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

Clone the latest completed version from main into your chosen folder:

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

### Frontend dependency audit

For `GHSA-vfj7-8cjw-p6xm`, do not run `npm audit fix --force` or downgrade
`eslint-config-next`. As of 3 October 2026, every published `braces` version
(including 3.0.3) is affected, so pinning 3.0.3 does not fix this advisory.

The frontend replaces only the Next.js ESLint plugin's `fast-glob` dependency
with the local `tools/next-eslint-glob` adapter backed by pinned `tinyglobby`.
It preserves the plugin's synchronous directory lookup, including literal roots,
absolute globs and Windows separators, without installing `micromatch` or `braces`.
Next.js, ESLint and their lint rules retain their existing versions/configuration.
The adapter deliberately supports only the API used by the current plugin;
recheck compatibility when upgrading `eslint-config-next`, and remove this
workaround once an upstream release eliminates the vulnerable dependency chain.

After pulling the fix, run these commands from `apps/web` (also valid in Windows
Command Prompt):

```sh
npm ci
npm audit
npm run lint
```

Keep the committed lockfile and `tools/next-eslint-glob` directory together.
`npm ci` installs the tested dependency tree. The full audit includes development
dependencies; `npm audit --omit=dev` alone would leave the lint dependency issue
unresolved.

## Upgrading an existing local installation

Read the PostgreSQL compatibility section below before starting Compose after an
update. Application migrations and PostgreSQL major-version upgrades are separate.

Keep your existing `.env` and its database credentials/name. Renaming the product
does not require renaming a PostgreSQL role or database. Seed UUIDs are stable, so
existing bookmarks, memberships and edited baseline records remain valid.

Before changing the Compose project name to `projectpulse`, find the existing
database's volume name in Docker Desktop (container details → mounts). Set
`POSTGRES_DATA_VOLUME` in your existing `.env` to that exact volume name and set
`POSTGRES_DATA_VOLUME_EXTERNAL=true` to reuse it without changing its ownership. Stop the
old database container, then start the new Compose project using the commands above.
This reuses the existing data instead of initializing another database. Do not
delete the original volume or overwrite your `.env` with the new sample.

Once a phase has merged, update your local source with `git fetch origin` followed
by `git switch main` and `git pull --ff-only origin main`. Preserve any uncommitted
local work before switching branches.

### PostgreSQL image and volume compatibility

New installations default to pgvector 0.8.7/PostgreSQL 18, pinned by digest, with
the named volume mounted at `/var/lib/postgresql`. PostgreSQL 18 stores its cluster
at `/var/lib/postgresql/18/docker`. See the
[official image documentation](https://github.com/docker-library/docs/blob/master/postgres/README.md#pgdata).
An existing PostgreSQL 18 installation using this layout needs no volume change.

For an existing PostgreSQL 17 installation, preserve its original volume and add
both settings to your existing root `.env` before starting Compose:

```dotenv
POSTGRES_IMAGE=pgvector/pgvector:0.8.1-pg17@sha256:3e8b3adfd27b5707128f60956f62a793c3c9326ea8cfaf0eab7adccb5d700b21
POSTGRES_DATA_TARGET=/var/lib/postgresql/data
```

Keep your existing `POSTGRES_DATA_VOLUME`, credentials and database name. These
settings retain the previously tested PostgreSQL 17 image and its original mount;
they do not perform a database upgrade. Set image and mount together. Inspect the
existing container's image and mount in Docker Desktop if unsure which layout it uses.

Never point PostgreSQL 18 directly at a PostgreSQL 17 cluster or delete a volume
to resolve a version mismatch. A deliberate major upgrade requires a verified
backup and PostgreSQL's supported dump/restore or `pg_upgrade` procedure into a
separate target cluster. This source update does not perform that migration.
Alembic upgrades application tables within the current PostgreSQL version.

## How people use the application

ProjectPulse is a web application. Developers run the frontend/backend locally;
after a hosted deployment, users open the application URL in a browser and select
a project. The workspace supports baseline inspection, manual editing, document
memory/search and speaker-attributed meeting transcript upload. Later phases add
AI interpretation and evidence-backed human review.
Users will not need Node, Python or Docker to access a hosted version. A Windows
executable is outside the current product plan.

The current workspace is a local prototype with a fixed demo identity. Phase 4 adds
AI relevance interpretation; event extraction and review actions remain future work.
See the [Phase 1 report](../testing/phase-1-results.md) and
[test commands](../../README.md#checks).


## Updating to completed Phase 2

Phase 2 is available on `main`; `phase/2-project-memory` is retained for history.
Update an existing clean checkout:

```sh
git fetch origin
git switch main
git pull --ff-only origin main
```

Then run `uv sync --frozen` and `uv run alembic upgrade head` from `apps/api`,
`npm ci` from `apps/web`, and restart both servers using the commands above.
Keep the existing root `.env`, credentials and database volume. The additive
migrations preserve canonical records. Do not downgrade a populated database;
downgrade tests use only a disposable database ending in `_test`.

Open the browser at `http://127.0.0.1:3000`. Use **Project state** for audited manual
CRUD, **Documents** to upload/read/delete evidence, and **Context search** for a
bounded mix of current baseline facts and document excerpts with source links.
Upload does not change baseline truth. New decisions default to Discussion.

### Server-side Gemini setup

For detailed laptop instructions and recovery from invalid-vector errors, see the
[Gemini setup guide](gemini-setup.md). A laptop backend does not require Codex cloud
secrets or a Codex network allowlist.

Add `GEMINI_API_KEY=<your key>` to your existing root `.env` locally (never commit
it or paste it into chat). The FastAPI server reads it; restart the backend after
changing it. Do not create a `NEXT_PUBLIC_` variable for this key. The provider uses
`gemini-embedding-001`, 768 dimensions and a fixed Google REST endpoint. In a
restricted cloud runtime, configure outbound HTTP access to
`generativelanguage.googleapis.com` through that runtime's supported configuration
workflow; changing a local policy file cannot grant access.

In Documents, upload a small readable document and click **Index**. Expect
`indexed` with a positive chunk count. Search for a paraphrase of a distinctive
sentence in Context search; expect **Text and semantic search** and a citation
back to the original page/section. Verify the source text and confirm no baseline
fact changed. These checks verify Gemini configuration on your installation.
Without a key, upload/read/manual editing and text search still work; the app
explicitly reports semantic search/indexing as unavailable. Automated browser tests
force an empty key, while provider contract tests use synthetic responses.

If this cloud environment's Turbopack build fails with a socket EPERM, use the
supported production builder `npm run build -- --webpack` from `apps/web`. The
standard build remains unchanged for normal local and GitHub runners.


## Updating to completed Phase 3

Stop the frontend and backend with Ctrl+C in their terminals. From your ProjectPulse
checkout, update main and keep your existing `.env` and database volume:

```sh
git switch main
git pull --ff-only origin main
cd apps/api
uv sync --frozen
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal at the checkout root:

```sh
cd apps/web
npm ci
npm run dev
```

Open `http://localhost:3000`, select your project and **Meetings**. Choose **New
meeting**, enter a title, then open it and upload a UTF-8 TXT, JSON or VTT file.
The [sample transcript](../examples/meeting-transcript.json) contains distinct
speaker IDs, a repeated name and unknown time/speaker examples. The upload form
also shows format examples. **Add participant** before upload optionally links a
speaker to a project member. After upload, use **Link to utterance** to bookmark
specific evidence; reload preserves the source and attribution.

The additive `0005_meetings` migration preserves canonical state and existing
documents. No new secret, domain allowlist, Gemini call, meeting-bot setup or database
reset is required for file ingestion. This remains a browser application. Read the
[transcript guide](../features/transcript-ingestion.md) for source formats/limits.

## Updating to completed Phase 4

Stop the frontend/backend, keep the existing root `.env` and database volume, then
update `main` after the phase PR is merged. In Windows Command Prompt:

```bat
cd /d D:\okruti_projects\Hackathon_Projects\ProjectPulse
git switch main
git pull --ff-only origin main
docker compose --project-name projectpulse up -d --wait
cd apps\api
uv sync --frozen
uv run alembic upgrade head
uv run alembic current
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The migration head should be `0006_relevance`. In a second terminal:

```bat
cd /d D:\okruti_projects\Hackathon_Projects\ProjectPulse\apps\web
npm ci
npm run dev
```

Refresh `http://127.0.0.1:3000`, choose your project, open **Meetings** and a meeting
with a transcript, then click **Analyze relevance** in **Meeting Impact**. Rule
classifications are saved first. Ambiguous segments use the existing server-side
`GEMINI_API_KEY`; optional `GEMINI_RELEVANCE_MODEL` defaults to `gemini-2.5-flash`.
No new secret is required and a laptop does not need a Codex cloud allowlist.
This additive migration preserves existing canonical state, documents and meetings.

Follow the [complete Phase 4 manual scenarios](../testing/phase-4-manual-testing.md)
to check known counts, source links, persistence, context changes and live Gemini.
