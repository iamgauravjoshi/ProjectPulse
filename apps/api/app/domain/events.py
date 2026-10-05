"""Evidence-backed interpretations; no confirmed state, ownership or inferred dates."""

import re
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.manual_state import StateError
from app.domain.relevance import ProjectContext

EXTRACTOR_VERSION = "events-v1"
MAX_WINDOWS = 20
MAX_WINDOW_TEXT = 20_000
MAX_EVENTS = 4


class EventKind(StrEnum):
    REQUIREMENT_CHANGE = "REQUIREMENT_CHANGE"
    DECISION = "DECISION"
    COMMITMENT = "COMMITMENT"
    RISK = "RISK"
    MILESTONE_CHANGE = "MILESTONE_CHANGE"
    DEPENDENCY = "DEPENDENCY"
    OPEN_QUESTION = "OPEN_QUESTION"


class StatementKind(StrEnum):
    PROPOSAL = "PROPOSAL"
    STATEMENT = "STATEMENT"
    QUESTION = "QUESTION"
    NEGATED = "NEGATED"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class SourceSegment(StrictModel):
    id: UUID
    sequence: int = Field(ge=0, le=9999, strict=True)
    speaker: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=6000)


class EventWindow(StrictModel):
    source: SourceSegment
    previous: SourceSegment | None = None


class EventEvidence(StrictModel):
    utterance_id: UUID = Field(alias="utteranceId")
    quote: str = Field(min_length=1, max_length=500)


class ExtractedEvent(StrictModel):
    kind: EventKind
    statement: StatementKind
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=1600)
    confidence: float = Field(ge=0, le=1, strict=True)
    owner_mention: str | None = Field(alias="ownerMention", max_length=120)
    due_date_text: str | None = Field(alias="dueDateText", max_length=120)
    evidence: list[EventEvidence] = Field(min_length=1, max_length=2)


class SegmentEvents(StrictModel):
    id: UUID
    events: list[ExtractedEvent] = Field(max_length=MAX_EVENTS)


class ExtractionBatch(StrictModel):
    items: list[SegmentEvents] = Field(min_length=1, max_length=MAX_WINDOWS)


def validate_inputs(windows: list[EventWindow], context: ProjectContext) -> None:
    if (
        not 1 <= len(windows) <= MAX_WINDOWS
        or len({w.source.id for w in windows}) != len(windows)
        or sum(len(w.source.text) + (len(w.previous.text) if w.previous else 0) for w in windows)
        > MAX_WINDOW_TEXT
        or len(context.model_dump_json(by_alias=True)) > 20_000
        or any(
            w.previous is not None
            and (w.previous.id == w.source.id or w.previous.sequence != w.source.sequence - 1)
            for w in windows
        )
    ):
        raise StateError("EVENT_INPUT", "Event extraction exceeds its bounded source budget.")


def validate_extraction(value: object, windows: list[EventWindow]) -> ExtractionBatch:
    try:
        batch = ExtractionBatch.model_validate(value)
        inputs = {w.source.id: w for w in windows}
        ids = [item.id for item in batch.items]
        if len(ids) != len(set(ids)) or set(ids) != set(inputs):
            raise ValueError("Exactly one result per source segment")
        for item in batch.items:
            window = inputs[item.id]
            sources = {window.source.id: window.source.text}
            if window.previous:
                sources[window.previous.id] = window.previous.text
            signatures: set[str] = set()
            for event in item.events:
                evidence_ids = [e.utterance_id for e in event.evidence]
                if (
                    len(evidence_ids) != len(set(evidence_ids))
                    or item.id not in evidence_ids
                    or any(e.utterance_id not in sources for e in event.evidence)
                    or any(e.quote not in sources[e.utterance_id] for e in event.evidence)
                ):
                    raise ValueError("Evidence must quote the primary source and optional neighbor")
                quotes = "\n".join(e.quote for e in event.evidence)
                for mention in (event.owner_mention, event.due_date_text):
                    if mention is not None and (
                        not mention
                        or not re.search(r"(?<!\w)" + re.escape(mention) + r"(?!\w)", quotes)
                    ):
                        raise ValueError(
                            "Owner/date wording must occur literally in cited evidence"
                        )
                signature = event.model_dump_json(by_alias=True)
                if signature in signatures:
                    raise ValueError("Duplicate event")
                signatures.add(signature)
        return batch
    except ValueError:
        raise StateError(
            "EVENT_OUTPUT_INVALID",
            "Event provider returned invalid or uncited interpretations.",
            503,
        ) from None
