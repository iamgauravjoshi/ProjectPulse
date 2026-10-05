# Phase 4 checkpoint results

Started 5 October 2026 (Asia/Calcutta).
Branch: `phase/4-project-relevance-filter`, based on completed Phase 3 main
`26895c13ae4e1c0806068a83ce15cc8d8c710076`.

## Step 4.1 — complete

Implemented strict relevance contracts, deterministic social/project rules and a
provider-independent batched Gemini generateContent adapter. Uses the existing
server-only key and configurable generation model. Missing configuration, malformed
output, invalid IDs/scores/types, budget violations and blocked/truncated responses
fail safely. No API/UI/persistence or canonical mutation is introduced in this step.

Added 50 manually labeled examples and 30 new backend cases. Initial rule coverage:
34/50 classified, 16 unresolved, three false positives (hobby database, film launch,
other-client deployment), zero false negatives among decided examples. These are
explicit Step 4.2 improvement targets; unresolved examples are not counted as ignored.
No live AI accuracy is inferred from synthetic contract tests.

Validation: `pytest -m 'not integration'` **104 passed**, Ruff lint/format and strict
mypy (53 source files) passed. Backend suites from earlier phases remain green.
The sandbox cannot run FastAPI TestClient threads normally; the same tests pass
with approved local runtime access. Initial sandbox run was interrupted without
claiming success. PostgreSQL was started preserving the configured development
volume; Step 4.2 will add migration/database checks.

Live Gemini is unavailable in this cloud task: no configured API key and Google
is outside its outbound policy. Your laptop key is independent of this runtime.
Provider code is exercised through validated synthetic responses; the phase's
live laptop verification instructions will be documented with final acceptance.

Next checkpoint: Step 4.2 selected project context, durable scoped interpretations
and analysis API. Main remains unchanged until all phase steps and CI pass.
