# PostgreSQL and Windows compatibility checkpoint

5 October 2026 (Asia/Calcutta), based on `f9ff745`, the completed Phase 4 merge.
The local checkout initially pointed at completed Phase 3. Fetching origin showed
Phase 4 was already merged, so this checkpoint verifies its existing implementation
and resolves pending local database configuration changes. Phase 5 is not started.

## Changes and acceptance

- Retain the pending pinned pgvector 0.8.7/PostgreSQL 18 Compose and CI image.
  The running local container already uses that exact digest, PostgreSQL 18.6,
  pgvector 0.8.7 and `projectpulse_pgdata` at `/var/lib/postgresql`, with its cluster
  at `/var/lib/postgresql/18/docker`. No database major upgrade was performed.
- Add paired `POSTGRES_IMAGE` / `POSTGRES_DATA_TARGET` overrides and instructions
  for existing PostgreSQL 17 volumes to keep their original pinned image and mount.
  Both Compose layouts render correctly and retain the same named volume. The
  supported legacy layout is configuration-checked; a new PostgreSQL 17 server
  was not started during this checkpoint.
- Preserve the pre-existing Phase 0 table-formatting edit.
- Accept either supported pinned pgvector version in migration regression tests.
- Give binary pytest parameters compact IDs. Previously binary document parameters
  exceeded Windows' 32767-character `PYTEST_CURRENT_TEST` environment limit.
- Make Prettier accept the checkout's consistent line endings. Windows CRLF caused
  formatting failures across otherwise unchanged frontend files.
- Mark PDF and DOCX files as binary in Git. Windows autocrlf had changed the PDF
  fixture's internal offsets; restoring the original Git blob fixes strict parsing.
  No PDF content or parser validation was changed.

## Validation

Backend checks use the existing Python 3.12 virtual environment directly because
the restricted uv cache could not persist interpreter metadata. Normal approved
local runtime access was used for database/TestClient and Node checks.

- Full `pytest -q --tb=short`: **281 passed**, including real PostgreSQL integration,
  migration downgrade/reapply and schema comparison, using only the new empty
  `projectpulse_config_test` database. Credentials were loaded privately from the
  existing server configuration. Development data was never used for destructive tests.
- Ruff lint/format and strict mypy: passed; **58 source files** type checked.
- `python -m app.check_relevance`: **50 examples**, 35 resolved, 15 unresolved,
  zero false positives/negatives among resolved examples. No live AI call.
- Frontend lint/typecheck/format, **49 unit tests**, standard production Turbopack
  build and full dependency audit: passed; **0 vulnerabilities**.
- Applied existing additive `0006_relevance` to the development database;
  `alembic check` reported no drift. Before/after fingerprints verified all **31
  original canonical, identity, document and transcript rows** unchanged.
- `npm run test:e2e` with the installed Chrome executable: **61 passed**, including
  all ten Phase 4 relevance cases and the earlier document/meeting/manual-state
  regressions. The corrected PDF upload/read/deduplicate/delete journey passes.
  Final fingerprints again verify all 31 original rows unchanged after QA cleanup.
- Local acceptance is complete. GitHub's `foundation` and
  `windows-frontend-audit` jobs must both pass on the final pushed PR head before
  the authorized merge to main; retain the checkpoint branch afterwards.

Earlier failed checks were investigated: oversized Windows test IDs, the old
pgvector version assertion, CRLF formatting and corrupted PDF fixture bytes.
Only subsequent passing reruns count as acceptance. No `.env`, credentials,
generated Next.js declarations, build output or test artifacts belong in the commit.
AI interpretations remain independent of canonical project state. Live Gemini
quality is outside these deterministic checks; see the existing
[Phase 4 manual guide](phase-4-manual-testing.md).
