# Phase 4: end-to-end manual testing

Use your laptop checkout after the Phase 4 PR has merged. This guide checks the
relevance filter built on Phases 0–3. For their original workflows, keep using the
earlier phase reports and your existing manual QA kit.

## Prepare the application

1. Stop the old frontend/backend and follow
   [Updating to Phase 4](../development/local-setup.md#updating-to-completed-phase-4).
   Keep your existing `.env`, Gemini key and database volume.
2. Check `uv run alembic current` from `apps/api`: expect `0006_relevance (head)`.
   Open `http://127.0.0.1:8000/health/live` and `/health/ready`: both should return
   `{"status":"ok"}`. `/health` is not the documented route.
3. Open `http://127.0.0.1:3000`, select **Client Portal Modernization**, and inspect
   **Project state**. Note the existing SSO phase and launch date; saved edits on
   your installation may differ from the seed. Take a screenshot for comparison.
4. Use **Meetings → New meeting**. Title it `Phase 4 manual — rules`. Open it and
   upload [relevance-transcript.json](../examples/relevance-transcript.json) from
   the repository's `docs/examples` folder. Four speaker-attributed utterances
   should appear. No indexing or document upload is needed for this workflow.

## Step 4.1 and 4.3: rules, counts and source evidence

Before analysis, expect 0 analyzed and 4 pending. Click **Analyze relevance**.

| Metric | Expected value |
| --- | --- |
| Conversation segments analyzed | 4 |
| Project-relevant segments | 2 |
| Ignored segments | 2 |
| Needs review | 0 |
| Pending segments | 0 |
| Total segments | 4 |
| Ignored conversation share | 50% of analyzed segments |

The hiking/greeting statements should be ignored. Launch/SSO should be relevant,
with a reason and rule confidence. **Analysis usage** should show 0 AI attempts.
**Analysis complete** should be disabled. This scenario works without a key.

Select **Show relevance → Ignored**: only the two ignored interpretations should
remain. The raw transcript below must still contain all four utterances. Click
**View source utterance 1**: the original hiking statement should be focused and
highlighted. Copy the browser URL, reload it and verify the same source/speaker/time
remains visible. Saved classifications and metrics should survive reload.

Check Project state again. The SSO phase, launch date and all other baseline
values must match your earlier screenshot. The transcript's proposed November 10
launch is evidence; relevance never approves that date.

## Step 4.1 and 4.2: Gemini, context and honest coverage

Create a second meeting, `Phase 4 manual — Gemini`, and upload
[relevance-ai-transcript.json](../examples/relevance-ai-transcript.json). It adds
one login/QA statement that requires AI rather than a keyword rule. Analyze it.

With working Gemini access, expect 5 analyzed and 0 pending. The last statement
should normally be project-relevant in this project's authentication context;
inspect its reason and confidence. A score below 0.65 belongs in **Needs review**,
which counts as analyzed and is excluded from relevant/ignored totals. The output
is probabilistic: record an incorrect confident result as a quality failure rather
than changing the expected label to make the test pass. **Analysis usage** should
show 1 AI attempt, recorded latency and reported token counts when supplied.

If provider configuration/access fails, expect 4 analyzed, 2 relevant, 2 ignored,
1 pending, and an explicit provider error. The 50% share describes the four analyzed
segments and says the whole meeting is not covered yet. Fix provider access, restart
the backend if configuration changed, then click **Retry remaining segments**.
Never delete/re-upload evidence just to recover from an AI failure.

From a third terminal at `apps/api`, run:

```sh
uv run python -m app.check_relevance
uv run python -m app.check_relevance --live
```

The first command should report 50 examples, 35 rule-classified, 15 unresolved and
empty false-positive/false-negative lists. It makes no AI call. The second sends
only those unresolved examples using selected synthetic context, including Raj's
explicitly owned Friday deployment. Inspect all output: `providerError` should be
null and confident mismatches should be absent; record uncertain/unresolved IDs
separately. This smoke set is not a production accuracy guarantee. Neither command
changes your database or prints the key. See [Gemini setup](../development/gemini-setup.md)
if there is a provider error; the embedding probe alone does not verify generation.

## Step 4.2 and 4.3: cache and stale context

1. Open the analyzed rule-only meeting. Refresh the page and click **Refresh impact**.
   The same metrics should return with 0 AI attempts; no analysis is started by reads.
2. In **Project state**, create a temporary ACTIVE requirement named
   `Phase 4 manual context check`. Return to the meeting and refresh impact.
   Expect a stale-baseline notice and **Analyze current baseline**.
3. Click that action. Expect the notice to clear and the four deterministic counts
   to remain the same. This stores a new interpretation using current context.
4. Delete only your temporary requirement, using its normal manual-state action.
   A later impact refresh should show stale context again because the baseline changed.
   Analyze again if you want to leave the meeting current.

Ownership-dependent availability is covered by backend tests and the benchmark.
“Raj is off Friday” is relevant only when selected context links Raj to an explicit
Friday deployment obligation. No owner or date is inferred from a transcript. The
fixed seed may not contain Raj; do not relabel a real member solely to fit this test.

## Failure, longer-meeting and usability checks

| Scenario | Where and expected behavior |
| --- | --- |
| No transcript | Create another QA meeting; Meeting Impact explains the upload prerequisite and offers no analysis action. |
| Read failure/recovery | Open a meeting, stop the backend, refresh the page. Resume the backend and use **Try again**; saved evidence/results return. Independent impact-loading failure is also covered by browser tests. |
| Provider failure/recovery | Optional: temporarily remove the local key, restart backend, analyze a new AI sample. Four rules persist and one stays pending. Restore the existing key privately, restart and retry. Do not modify a shared environment for this test. |
| Long transcript | On a QA meeting, upload >100 separate rows; saved relevance pages contain at most 100 results. Filters reset to page 1 and citations open the matching original transcript page. |
| More than one AI batch | With >40 ambiguous segments, each explicit action processes at most one bounded AI batch; pending decreases across actions. No full-meeting percentage is claimed while coverage remains pending. This optional check consumes Gemini quota. |
| Mobile and keyboard | At 375px width, counts/controls/long text should wrap without horizontal page overflow. Use Tab, Enter and the relevance select; source links remain usable. |
| Low confidence | When an AI result is below 0.65, it appears under Needs review and never increases ignored/relevant counts. Synthetic automated tests cover this because live model scores cannot be forced reliably. |

Record date, commit, provider model, scenario, observed counts and any mismatched
utterance IDs. Delete only meetings/records you created for QA. Preserve original
meetings, documents, canonical records, `.env` and Docker volumes. Phase 5 event
extraction and human review are outside Phase 4 testing.
