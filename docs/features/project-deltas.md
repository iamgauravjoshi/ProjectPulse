# Phase 6: project delta comparison

Authorized 6 October 2026 (Asia/Calcutta) by the user's request to implement next.
Branch `phase/6-project-delta-comparison`, based on completed main `d44421b`.

## Steps and acceptance

1. **6.1 Contracts/provider:** bounded candidate-to-canonical comparison, validated
   target kinds, literal proposed wording, explicit SAME/CHANGE/NEW/UNCLEAR outcomes,
   Gemini transport, malformed-output and ambiguity tests. No persistence yet.
2. **6.2 Persistence/API:** additive migration, scoped comparison runs and deltas,
   server-owned baseline versions/previous values, cache, pending coverage, stale
   baseline/input handling, leases and audit rollback; no canonical writes.
3. **6.3 UI/acceptance:** meeting comparison panel, explicit batches/retry, previous
   values alongside proposed wording, citations, filters, honest coverage and usage.
   Full regression/build/static/E2E checks, documentation, push and completed PR merge.

Each tested and documented step is committed and pushed before starting the next.
Stop after the Phase 6 merge. Governance, decision-conflict detection and human
approval/application are later phases. The earlier Phase 4/5 live Gemini quality
gap remains open; successful injected-provider tests do not close it.

## Comparison boundary

Compare only current Phase 5 candidates. Current baseline includes active records
and confirmed decisions; provisional/rejected/superseded decisions are not truth.
Selected context is bounded to 100 records/20,000 characters; every versioned target
comes from that scoped selection. One request compares at most 20 candidates and
40,000 candidate characters. Missing/truncated context is explicitly recorded.
NEW is disallowed when selected context is incomplete. Questions, negations and
source/comparator confidence below 0.65 require UNCLEAR. Ambiguous matching must not
invent a target. A possible CHANGE is an interpretation, never an approved conflict.

The provider can return a target ID, explanation and proposed wording. It cannot
provide trusted previous values, versions, owner IDs, actor authority or approval.
The server validates candidate coverage, same-kind supplied targets, unique allowed
fields and verbatim evidence support. Relative/yearless dates remain wording.
The previous value is copied from the selected baseline by the server. No canonical
write service is available to the comparator.

`GEMINI_DELTA_MODEL` independently selects the comparison model (default
`gemini-3.5-flash-lite`); use the existing server-only `GEMINI_API_KEY`. Model and
transport follow [Google's model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)
and [generateContent API](https://ai.google.dev/api/generate-content). One call per
explicit action, 25-second timeout, 512 KiB response and 8192 output tokens. Missing
access, blocked output or invalid contracts leave work pending; no fake fallback.
Live semantic quality remains unverified until explicitly evaluated.
