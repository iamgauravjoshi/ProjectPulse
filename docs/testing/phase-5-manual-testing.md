# Phase 5 manual acceptance

Use the browser application with the existing database and seed identities. Apply
`uv run alembic upgrade head` from `apps/api`; preserve the root `.env` and volumes.
Start the normal API (`app.main:app`) and frontend using the local setup guide.
The Playwright entry point in `tests/e2e_app.py` is exclusively a synthetic test
provider; it must not be used to demonstrate live AI quality.

## Evidence and extraction

1. Record the current canonical categories. Create a disposable meeting. Before
   upload, the candidate panel explains the transcript prerequisite. Upload a
   transcript; before current relevance analysis, extraction is disabled.
2. Include SSO scope proposals, a decision assertion, a commitment made by Sarah
   naming John and “tomorrow”, a negated commitment, a launch date proposal, a
   dependency, an ownership question and personal conversation. Labeled examples
   are in `tests/fixtures/ai-evaluation/events.json`.
3. Analyze relevance, then explicitly extract. Each click handles one bounded batch.
   Ignored/uncertain segments are excluded. Incomplete relevance is identified, so
   completion applies only to currently eligible sources.
4. Inspect each kind, statement, summary and exact quote. Proposals and negations
   must retain their meaning. Every score remains CANDIDATE. Below 65% shows Needs
   review. Semantic interpretation can still be wrong at high confidence.
5. Said by shows source identity independently of the literal Owner mention.
   Absent ownership is Unknown; absent dates are Not stated. “Tomorrow” remains
   wording, never an inferred calendar date or assigned project member.
6. Open citations, including one on a later transcript page. Check speaker, time,
   quote, highlighted source and keyboard focus. Reload; source selection and saved
   candidate IDs persist. Filter kinds, empty filters and over-100 pagination.
7. Process a relevant segment with no event; check Segments without events and
   completion without fabricated candidates. Repeated extraction preserves IDs.

## Failure, context and interaction

- With `GEMINI_API_KEY` absent, the normal API shows Event AI is not configured and
  eligible work stays pending. Restore existing configuration privately and
  explicitly retry; there is no automatic retry or substitute extraction.
- Invalid, blocked/truncated output or network errors preserve saved results and
  leave the failed batch pending. Usage shows reported tokens and attempts; missing
  usage is unknown. Do not infer cost or accuracy.
- Change a disposable manual baseline record. Candidates show a stale warning;
  current relevance is required before new extraction. A context change during a
  request discards that batch. Remove the disposable baseline record afterward.
- At 375px, use Tab/Enter for extraction, filters and source links. Long titles,
  Unicode quotes and speaker names wrap without horizontal page overflow.
- Verify the recorded canonical state is unchanged. Delete only the disposable
  meeting; its interpretations/evidence links cascade.

## Live smoke evaluation

From `apps/api`, `uv run python -m app.check_events` validates 16 manually supplied
contract labels without calling a model. It does not measure extraction quality.
For an explicit live check, configure the server-only Gemini key/model and run:

```sh
uv run python -m app.check_events --live
```

This makes one request with synthetic sources, writes no project records and prints
model, actual usage, field mismatches and returned candidates. Exit 0 means field
labels matched this small set, 1 means mismatches, and 2 means provider failure.
Review summaries, quotes and intent manually. Production quality requires a broader,
independently labeled real-world evaluation.

Phase 6 comparison, conflict detection and approval/application are outside this
phase. There is no confirmation action in this panel.
