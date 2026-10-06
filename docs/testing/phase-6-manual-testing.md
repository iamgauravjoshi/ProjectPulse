# Phase 6 manual acceptance

Preserve existing `.env`, seed identities and database volumes. Upgrade additively
with `uv run alembic upgrade head` from `apps/api`; expect `0008_deltas (head)`.
Start normal `app.main:app` and the frontend using the local setup guide. A server-only
`GEMINI_API_KEY` and accessible `GEMINI_DELTA_MODEL` are required for live comparison.
The browser test entry point supplies synthetic responses and does not verify Gemini.

## Page and sequence

1. Open ProjectPulse, select Client Portal Modernization and record Project state
   values/versions. Existing manually edited values take precedence over seed examples.
2. Meetings → New meeting → Open. Use a disposable QA meeting and upload
   [delta-transcript.json](../examples/delta-transcript.json). No documents are required.
3. In Meeting Impact, explicitly analyze current relevance. Complete remaining batches
   or record partial coverage. Ignored/uncertain segments are not extracted.
4. In Project Event Candidates, explicitly extract remaining event batches. Inspect
   intent/quotes first: a wrong event interpretation cannot be fixed by comparison.
5. In Project Comparisons (below candidates and above the transcript), click Compare
   with project state, then Compare next candidate batch until eligible work finishes.
6. Against an unchanged seed, SSO Phase 1 wording should be a possible phase difference
   from Phase 2; unchanged Phase 2 should match. November 10 is proposed wording against
   the current launch date, not an inferred calendar date or approved milestone.
   MySQL wording should differ from the confirmed PostgreSQL decision. Inspect reasons
   and matching targets; source proposals are never confirmed facts or authority.
7. Questions/negations and low-confidence candidates must require clarification.
   Unknown owners remain unknown; Sarah saying John will deliver does not assign Sarah
   as owner. Relative dates remain wording. Source false positives/semantic mismatches
   are recorded as quality failures, not relabeled to pass the demonstration.
8. Verify baseline record ID/kind/version and each Previous value. Compare those with
   Project state. Proposed wording must occur literally in the displayed exact quotes.
   A same-kind but unrelated target is a model quality failure even if its ID is valid.
9. Open citation links; confirm speaker, time, full original text, highlighting and
   focus. Reload; saved IDs/results and source selection remain. Filter each outcome,
   including an empty outcome. Over-100 results paginate and later citations open the
   corresponding transcript page. Repeat a completed POST only via developer tools
   if needed: IDs/attempts remain stable, with no duplicate paid call.
10. Recheck all Project state categories. They must be unchanged. No approve/apply
    action exists in this phase. Delete only your disposable QA meeting afterward.

## Recovery and coverage

- Without a transcript, current relevance or current extraction, the appropriate
  prerequisite appears and comparison is disabled. After explicit analysis/extraction,
  the panel updates without a full page reload.
- Zero extracted candidates complete without a comparison provider call or fabricated
  change. Partial source coverage remains visible even after all eligible candidates
  have been compared. Unclear results count as processed, never as approved changes.
- Missing key/model access, timeout, blocked/truncated/invalid output preserves saved
  results and pending candidates. Use explicit retry after provider recovery. No fake
  fallback or automatic retry exists. Reported token usage is distinguished from unknown
  usage; confidence/token counts do not establish accuracy or price.
- Add a disposable manual requirement, then refresh comparisons. Historical results
  show stale and comparison requires current relevance/extraction. A baseline/evidence
  change during a request discards the entire batch. Remove only the QA requirement.
- At 375px, use Tab/Enter for controls and source links; long/Unicode wording wraps.
- Record date, commit, models, meeting/candidate/source IDs, observed counts, target
  versions, mismatches and provider errors. A small successful walkthrough verifies
  integration, not general semantic accuracy; broader independently labeled evaluation
  remains necessary. Earlier Phase 4/5 live quality gaps remain open until tested.

Governance, decision conflict detection, human approval/application and integrations
are outside Phase 6. Stop after the completed Phase 6 merge.
