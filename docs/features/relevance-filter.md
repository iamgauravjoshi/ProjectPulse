# Project relevance filter

Phase 4 decides which conversation segments deserve project analysis. The result
is an interpretation of meeting evidence, never a confirmed requirement, decision,
owner or date. Original transcripts and canonical state are preserved.

## Step 4.1: classification boundary

A classification has `relevant`, finite numeric `confidence` (0–1), a short `reason`
and `relatedEntityTypes`: requirement, decision, commitment, risk, milestone,
dependency or open_question. Unknown types, extra fields, string/boolean scores,
duplicate IDs/types and partial provider output are rejected. An ignored result
has no related entity types. Confidence is an estimate, not measured accuracy.

Narrow deterministic rules recognize explicit project topics and standalone
personal small talk. Unknown text is retained for contextual/AI analysis. Mixed
social/project segments are not discarded just because they mention a weekend.
The initial rule benchmark deliberately records three keyword false positives
(hobby PostgreSQL, movie launch date, another client's deployment); contextual
rules in Step 4.2 must improve these before phase acceptance.

`RelevanceProvider.classify()` isolates provider details. `GeminiRelevance` uses
one bounded generateContent call for a batch, the existing server-only
`GEMINI_API_KEY`, and optional `GEMINI_RELEVANCE_MODEL` (default
`gemini-2.5-flash`). It uses a fixed Google destination, 25-second timeout,
20,000-character segment budget, at most 40 segments and a 512-KiB response bound.
JSON-schema output is independently validated against the exact requested IDs.
Blocked/truncated/malformed responses fail safely; there is no fake classification
when configuration or provider access is missing. There is no automatic retry.

The model name is configurable because availability can vary by account. Embeddings
continue to use gemini-embedding-001 independently. No new key or browser-visible
secret is required. Transcript and selected context are sent as untrusted data;
provider instructions prohibit following commands inside source content.

## Benchmark and limitations

[relevance-benchmark.json](../examples/relevance-benchmark.json) contains 50
human-authored synthetic utterances, balanced 25 relevant/25 irrelevant, with
expected labels and label reasons. Source order/previous utterance can matter.
The benchmark is a regression aid, not an independently validated production
accuracy claim. Rule coverage and false positives/negatives are reported separately
from unresolved items and provider-contract tests. Contract tests use synthetic
responses and do not establish live Gemini quality.

Context-aware persistence/API and meeting UI follow in individually tested
Step 4.2 and Step 4.3 checkpoints. Phase 5 event extraction is outside this feature.
