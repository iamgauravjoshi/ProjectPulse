# Phase 3 checkpoint results

Started 4 October 2026 (Asia/Calcutta). Phase in progress; keep it off main until
all required checkpoints and phase-wide acceptance pass.

Branch: `phase/3-meeting-transcript-ingestion`. Base `e4836de` includes the shared
frontend design system and [passing main CI](https://github.com/iamgauravjoshi/ProjectPulse/actions/runs/37180534874).
Feature: [transcript ingestion](../features/transcript-ingestion.md).

## Step 3.1 — complete

Added Meeting, MeetingParticipant and Utterance models, additive reversible
`0005_meetings`, scoped list/create/detail/delete and participant registration.
Composite foreign keys reject speakers from another project/meeting; indexes
support scoped retrieval and cascade deletion. Unique speaker keys allow repeated
names without merging identities. Unknown timestamps/identity/confidence remain
nullable. Actor/provenance fields are server-owned; atomic audit failures roll back.

**180 backend tests passed**, including 15 new meeting scenarios: repeated names,
explicit membership, hidden/other project access, invalid/spoofed fields, timezone
validation, audit rollback, cascade, utterance bounds and partial-source rejection.
The full suite also verifies migration downgrade/reapply and metadata drift.
Ruff lint/format and strict mypy (48 source files) passed. Baseline records are
unchanged by meeting evidence. No frontend behavior changed at this checkpoint.

## Step 3.2 — complete

Added bounded deterministic TXT/JSON/VTT ingestion, original-source hash/bytes,
immutable utterance IDs, explicit/name-based participant attribution and raw-byte
upload. Meeting row locks serialize upload/participant changes. Duplicate input
preserves IDs and audit counts; different input is rejected without replacement.
Control characters, invalid UTF-8, duplicate JSON fields, nonfinite confidence,
conflicting identities and invalid times fail safely. VTT presentation markup is
parsed as text; no external calls or canonical mutations occur.

**224 backend tests passed**, including 44 new parser/upload scenarios. Acceptance
covers two/ten speakers, repeated names with distinct IDs, unknown speakers, missing
timestamps, source order, multiline VTT, all source formats, a 10,000-utterance
transcript, size/count/text/speaker budgets, explicit participant mapping, duplicate
immutability, project isolation, cascade, baseline preservation and audit rollback.
Ruff lint/format and strict mypy (50 source files) pass. Previous phase regressions,
migration rollback/reapply and metadata drift remain passing. No new dependency.

## Step 3.3 — complete

Replaced the Meetings placeholder with meeting creation, explicit participant/member
registration, bounded upload, deletion confirmation and a paged evidence viewer.
Stable utterance URLs open/focus/highlight the correct source row, including later
pages. Invalid citations are explicit. Shared design-system controls and Radix
focus behavior are retained; request failures preserve drafts/selections.

**43 frontend unit tests passed**, including six new contract/proxy cases. **All 10
meeting browser tests passed** with the real API/database: all three upload formats,
unchanged canonical baseline, repeated names/distinct IDs, explicit participant
mapping, reload/citations, long pagination, malformed upload/retry, confirmation,
error retry and mobile keyboard/focus. An additional long-label mobile test exposed
intrinsic flex width overflow; source labels now wrap and that test passes. Captures
with synthetic evidence were inspected on desktop/375px and saved in feature docs.
Lint, type checking, formatting and the production webpack build pass. Standard
build remains unchanged and will be verified by phase-wide GitHub CI. Local browser
acceptance uses the already-installed Chromium through the existing executable-path
configuration. The environment's shadcn registry fetch was blocked; existing local
components and public docs read through Firecrawl were used without installing a
competing library. No canonical data/credentials/volumes were reset.

## Step 3.4 — complete

Added typed, provider-independent `TranscriptAdapter[Source]`, immutable file input
and implemented `FileTranscriptAdapter`. FastAPI injects the file adapter into the
existing persistence service. Future Vexa/Teams integration boundaries are documented;
no unavailable provider is implemented as a fake success or exposed in the UI.
Optional live streaming is deferred in accordance with the original brief.

**229 backend tests passed**: five new cases check all file formats against the
contract, safe malformed-source failure and the actual HTTP injected-adapter boundary
through persisted evidence. Ruff lint/format and strict mypy (51 source files) pass.
All parser, scoped API, rollback, baseline and earlier phase regressions remain green.
The adapter adds no network call or dependency and preserves the tested UI contract.
Next: phase-wide browser/regression acceptance and final CI before merge.
