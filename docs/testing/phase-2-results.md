# Phase 2 checkpoint results

Started 3 October 2026 (Asia/Calcutta). Phase 2 in progress; do not merge to `main`
until every step and phase-wide acceptance are complete.

Feature: [canonical project memory](../features/project-memory.md).
Branch: `phase/2-project-memory`. Base: latest verified Phase 1 `main`, commit
`70789d3`, whose [GitHub CI passed](https://github.com/iamgauravjoshi/ProjectPulse/actions/runs/37127914246).
The Phase 1 dependency audit fix and its Windows compatibility checks are retained.

## Purple theme checkpoint

Implemented: shared purple accent/soft surface tokens, neutral purple canvas/text/
borders, stakeholder avatars using the shared token and a purple P favicon. Existing
warning badges remain amber for distinct meaning. No data/API behavior changed.

Acceptance: normal text contrast is at least 4.5:1 for white on accent, accent on
soft surface, muted text on canvas and primary text on white. Browser and build
checks passed: lint/type/format, production build, 25 frontend unit tests and all
19 browser tests. Desktop/mobile captures were refreshed and visually inspected.
Text contrast ratios are 7.10:1 (white on accent), 6.19:1 (accent on soft),
4.98:1 (muted on canvas) and 13.99:1 (primary on white). No regressions found.
Gemini is the user-selected embedding provider for the later indexing step.

## STEP 2.1a COMPLETE — Scoped manual-state API

Implemented: create/list/get/edit/delete for all six canonical record types;
strict editable-field schemas; server-owned provenance, actor and confirmation
metadata; same-project references; row locks and expected-version checks;
atomic audit/state mutations; sanitized missing/hidden/reference/stale errors.
No schema or seed modification. The browser editor follows in Step 2.1b.

Testing: **103 backend tests passed** (4 unit/HTTP, 99 real PostgreSQL integration),
including 46 new API scenarios. Each record type completes create → read → edit →
delete; all three mutations attribute audit events to the human actor. Invalid
fields and spoofed metadata cannot write; hidden/missing projects and outside record
IDs are protected. Cross-project/unknown owner and dependency references fail.
Stale edits/deletes retain newer values; in-use deletes require explicit unlinking.
Injected audit failures roll back create/edit/delete. A proposal is not inferred
confirmed; an explicit human confirmation creates a timestamp, and returning it to
review removes that timestamp. Ruff lint/format and mypy pass.

Regression review: all Phase 0/1 backend tests remain passing. Foundation browser
smoke passed both cases against the updated API before this checkpoint is pushed. Next step:
2.1b, browser editor and full manual-state E2E acceptance.
