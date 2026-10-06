"""Validated comparisons against versioned truth; proposed wording is never an update."""

import re
from enum import StrEnum
from uuid import UUID

from pydantic import Field, StrictInt

from app.domain.events import EventEvidence, EventKind, StatementKind, StrictModel
from app.domain.manual_state import StateError

COMPARATOR_VERSION = "deltas-v1"
MAX_CANDIDATES = 20
MAX_INPUT_CHARACTERS = 40_000
MAX_CONTEXT_CHARACTERS = 20_000


class DeltaOutcome(StrEnum):
    SAME = "SAME"
    CHANGE = "CHANGE"
    NEW = "NEW"
    UNCLEAR = "UNCLEAR"


class BaselineRecord(StrictModel):
    id: UUID
    kind: EventKind
    version: int = Field(ge=1, strict=True)
    title: str = Field(min_length=1, max_length=240)
    values: dict[str, str | StrictInt | None]


class ComparisonContext(StrictModel):
    project: str = Field(max_length=240)
    complete: bool
    records: list[BaselineRecord] = Field(max_length=100)


class ComparisonSource(StrictModel):
    id: UUID
    kind: EventKind
    statement: StatementKind
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=1600)
    confidence: float = Field(ge=0, le=1, strict=True)
    evidence: list[EventEvidence] = Field(min_length=1, max_length=2)


class ProposedField(StrictModel):
    field: str = Field(min_length=1, max_length=40)
    proposed_text: str = Field(alias="proposedText", min_length=1, max_length=500)


class Comparison(StrictModel):
    id: UUID
    outcome: DeltaOutcome
    target_id: UUID | None = Field(alias="targetId")
    reason: str = Field(min_length=1, max_length=1600)
    confidence: float = Field(ge=0, le=1, strict=True)
    changes: list[ProposedField] = Field(max_length=6)


class ComparisonBatch(StrictModel):
    items: list[Comparison] = Field(min_length=1, max_length=MAX_CANDIDATES)


FIELDS: dict[EventKind, set[str]] = {
    EventKind.REQUIREMENT_CHANGE: {"title", "description", "phase"},
    EventKind.MILESTONE_CHANGE: {"title", "description", "date"},
    EventKind.COMMITMENT: {"title", "description", "ownerMention", "dueDateText"},
    EventKind.DEPENDENCY: {"title", "description", "ownerMention"},
    EventKind.OPEN_QUESTION: {"title", "description", "ownerMention"},
    EventKind.DECISION: {"title", "description"},
    EventKind.RISK: {"title", "description"},
}


def validate_comparison_inputs(sources: list[ComparisonSource], context: ComparisonContext) -> None:
    if (
        not 1 <= len(sources) <= MAX_CANDIDATES
        or len({s.id for s in sources}) != len(sources)
        or len({r.id for r in context.records}) != len(context.records)
        or sum(len(s.model_dump_json(by_alias=True)) for s in sources) > MAX_INPUT_CHARACTERS
        or len(context.model_dump_json()) > MAX_CONTEXT_CHARACTERS
    ):
        raise StateError("DELTA_INPUT", "Comparison exceeds the selected evidence budget.")


def validate_comparisons(
    value: object, sources: list[ComparisonSource], context: ComparisonContext
) -> ComparisonBatch:
    try:
        batch = ComparisonBatch.model_validate(value)
        inputs = {s.id: s for s in sources}
        records = {r.id: r for r in context.records}
        ids = [c.id for c in batch.items]
        if len(ids) != len(set(ids)) or set(ids) != set(inputs):
            raise ValueError("Exactly one comparison per candidate")
        for result in batch.items:
            source = inputs[result.id]
            target = records.get(result.target_id) if result.target_id else None
            if result.target_id and (target is None or target.kind != source.kind):
                raise ValueError("Target must be a supplied canonical record of the same kind")
            if result.outcome in {DeltaOutcome.SAME, DeltaOutcome.CHANGE} and target is None:
                raise ValueError("Existing comparisons require a target")
            if result.outcome == DeltaOutcome.NEW and (target is not None or not context.complete):
                raise ValueError("New items require complete selected context and no target")
            if result.outcome != DeltaOutcome.CHANGE and result.changes:
                raise ValueError("Only possible changes carry changed fields")
            if result.outcome == DeltaOutcome.CHANGE and not result.changes:
                raise ValueError("Changes require evidence-supported wording")
            if (
                source.statement in {StatementKind.QUESTION, StatementKind.NEGATED}
                or source.confidence < 0.65
                or result.confidence < 0.65
            ) and result.outcome != DeltaOutcome.UNCLEAR:
                raise ValueError("Questions, negations and low confidence require clarification")
            names = [c.field for c in result.changes]
            if len(names) != len(set(names)) or not set(names).issubset(FIELDS[source.kind]):
                raise ValueError("Unsupported or duplicate changed field")
            quotes = [e.quote for e in source.evidence]
            for change in result.changes:
                if not any(change.proposed_text in quote for quote in quotes):
                    raise ValueError("Proposed wording must occur verbatim in cited evidence")
                if change.field == "phase" and not any(
                    re.search(r"\bphase\s+" + re.escape(change.proposed_text) + r"\b", q, re.I)
                    for q in quotes
                ):
                    raise ValueError("Phase values require explicit phase wording")
                if change.field == "phase" and (
                    not change.proposed_text.isascii()
                    or not change.proposed_text.isdecimal()
                    or not 1 <= int(change.proposed_text) <= 1000
                ):
                    raise ValueError("Invalid phase")
        return batch
    except ValueError:
        raise StateError(
            "DELTA_OUTPUT_INVALID",
            "Comparison returned invalid targets or unsupported wording.",
            503,
        ) from None
