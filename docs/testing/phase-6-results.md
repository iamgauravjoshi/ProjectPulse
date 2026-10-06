# Phase 6 verification

Authorized 6 October 2026 (Asia/Calcutta); branch `phase/6-project-delta-comparison`.
Plan: [project delta comparison](../features/project-deltas.md).

## Step 6.1: contracts and provider — complete

Added bounded, strict comparison inputs/output and a separate Gemini comparison
adapter. Outcomes distinguish matching state, possible change, new item and
clarification. Trusted targets/versioned baseline are server supplied. Literal
proposed wording is evidence checked; unknown IDs/kinds, invented fields/values,
question/negation certainty, low-confidence certainty, incomplete-context NEW and
duplicate/missing candidate results fail validation. No persistence or UI yet.

Checks: 33 new contract/transport tests pass; all 167 non-integration backend tests
pass (199 integration cases excluded at this step). Ruff lint/format pass; strict
mypy passes for 66 source files. Reviewed budgets, fixed Google endpoint, safe key
header, no external retry, no canonical mutation dependencies, and no synthetic
production fallback. Original database/schema were not changed in this step.

Normal-process regression execution was needed because sandboxed TestClient tests
stalled; the same suite completed in 1.20 seconds with normal permissions. Live
Gemini requests were not made; transport tests use injected synthetic responses.
Phase 4/5 live quality remains unverified. Next step: scoped persistence/API.

Published Step 6.1 as `9acf40c` through the authenticated GitHub connector because
local Git push credentials are unavailable. Published tree matches the tested tree.

## Step 6.2: scoped persistence and API — complete

Migration `0008_deltas` adds comparison runs and deltas with scoped composite foreign
keys and CANDIDATE-only status. API derives current extraction and versioned canonical
context server-side. Previous values are server-owned; dates/names remain proposed
wording. Saved unchanged/unclear results, empty extraction completion, bounded batches,
stable IDs, cache, stale baselines, active/expired/superseded leases, input changes,
source deletion, project isolation and transactional audit are covered.

Full disposable-PostgreSQL regression: **383 passed in 35.01 seconds**, including
17 new integration cases and the 33 Step 6.1 tests. Final hardening adds identical-value
and partial-owner rejection; the final focused contract/integration suite has **51
passing cases**. Ruff lint/format pass (102 files); strict mypy passes (70 source files).
Full migration downgrade/reapply and schema/model comparison passed. Auto-generated
migration ordering was reviewed and corrected so the candidate unique constraint
precedes its referencing foreign key and is removed after dependent tables.

Two expected test-fixture warnings occur when deliberately injected save failures
roll back the outer test transaction; they do not represent test failures or partial
production writes. Regression review confirms no canonical mutation service is called.
Tests use a separately named `_phase6_test` database; development schema/records,
existing seed identities, `.env` and volumes remain untouched. No live AI calls.
Next step: meeting UI and complete phase acceptance.

Step 6.2 published as `9947949`; both GitHub CI jobs passed on PR #8 (run
`37431556960`). Published tree matches the tested local tree.

## Step 6.3: UI and phase acceptance — complete

Added Project Comparisons beneath meeting event candidates, same-origin proxy and
strict client contracts. Explicit analysis/extraction refreshes prerequisites without
a reload. The panel shows bounded coverage, unchanged/change/new/unclear outcomes,
baseline record/version, previous values, literal proposed wording, source citations,
usage, filters/pages, stale context and explicit retry. All results remain candidates;
questions/negations/low confidence require clarification. No approve/apply action.

Final verification, 6 October 2026 (Asia/Calcutta):

- Full backend regression on disposable PostgreSQL: **385 passed in 47.44 seconds**,
  including 35 comparison contract/transport cases and 17 comparison integration cases.
- Ruff lint/format: passed (102 files); strict mypy: passed (70 source files).
- Full migration downgrade/reapply and model/schema comparison: passed.
- Frontend unit regression: **73 passed**, including 12 new comparison cases.
- Frontend lint/typecheck/format and final production build: passed.
- Dependency audit: **zero vulnerabilities**.
- Full production-browser regression after CI layout correction: **79 passed in 2.5 minutes**, including nine
  comparison scenarios. Browser comparisons/extraction use test-only synthetic providers
  with real FastAPI/PostgreSQL; they do not prove live Gemini semantic accuracy.
- Final desktop/mobile wording screenshot scenario: **passed** after rebuild; screenshots
  visually reviewed at desktop and 375px in `docs/features/images/deltas-{desktop,mobile}.png`.
- Additive development migration to `0008_deltas`: passed; `alembic check` reports no
  pending schema differences. Fresh pre-upgrade fingerprints confirm **all 489 existing
  rows across 22 tables unchanged**, including current meetings, evidence, interpretations
  and audit history. Existing `.env`, seed identities and volumes are preserved.

The old Phase 5 snapshot predates today's meeting evidence and therefore differs for
meetings/participants/utterances; canonical and seed table fingerprints still match it.
The fresh immutable Phase 6 snapshot was taken before the development migration and
is the preservation evidence for this upgrade. Tests ran in separate `_phase6_test`
and `_phase6_browser_test` databases, preserving current development data.

One unit mock initially reused a consumed Response; corrected to return a new response.
One browser assertion initially selected a text-only node inside a labeled definition
list; corrected to inspect the proposed-wording value. Both corrected tests and full
suites pass. Visual review replaced the camel-case technical label with Due date.
Final hardening rejects zero-padded phase wording that could falsely imply a difference
and aligns the API with the client. Two deliberate save-failure cases emit the existing
outer test-transaction warning; no test fails or partial production write is introduced.

Regression review covers canonical preservation, scoped targets and candidate links,
literal dates/names, proposals/negations, invalid provider output, current extraction,
partial batches, stable cache/IDs, leases, input/baseline changes, audit rollback,
cascading evidence removal, pagination, source focus/reload, recovery and mobile input.
Manual live acceptance uses the new sample transcript and documented meeting-page
sequence. No live Gemini call was made; Phase 4/5/6 live semantic quality remains unverified.

Final-head CI run `37434250160` passed backend and Windows checks but exposed mobile
horizontal overflow in four meeting-page browser cases. Comparison pagination kept
two buttons on one row. Reproduced locally at 320px and confirmed the overflowing
Next comparisons button, then allowed the pagination group to wrap. The mobile
keyboard acceptance scenario now covers both 320px and 375px. Production rebuild,
lint and formatting pass; refreshed desktop/mobile screenshots were visually reviewed.
The corrected full browser regression passes all 79 scenarios, including the four
CI failures and both comparison mobile widths. Rechecked development fingerprints:
all 489 pre-upgrade rows remain unchanged.

## Delivery and boundary

All three implementation steps are complete and delivered through
[PR #8](https://github.com/iamgauravjoshi/ProjectPulse/pull/8). The final checkpoint's
published Git tree must equal the tested local tree. Merge requires both `foundation`
and `windows-frontend-audit` to pass on the final PR head. Keep
`phase/6-project-delta-comparison` for history and stop after the completed-phase merge.
Phase 7 is not authorized.
