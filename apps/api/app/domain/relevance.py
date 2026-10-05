"""Validated relevance interpretations; never canonical state or extracted events."""

import re
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.manual_state import StateError

CLASSIFIER_VERSION = "relevance-v1"
MAX_AI_SEGMENTS = 40
MAX_AI_TEXT = 20_000
CONFIDENCE_THRESHOLD = 0.65


class EntityType(StrEnum):
    REQUIREMENT = "requirement"
    DECISION = "decision"
    COMMITMENT = "commitment"
    RISK = "risk"
    MILESTONE = "milestone"
    DEPENDENCY = "dependency"
    OPEN_QUESTION = "open_question"


class RelevanceClassification(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)
    relevant: bool = Field(strict=True)
    confidence: float = Field(ge=0, le=1, strict=True)
    reason: str = Field(min_length=1, max_length=500)
    related_entity_types: list[EntityType] = Field(alias="relatedEntityTypes", max_length=7)

    @model_validator(mode="after")
    def consistent_types(self) -> "RelevanceClassification":
        if len(set(self.related_entity_types)) != len(self.related_entity_types):
            raise ValueError("Duplicate entity types")
        if not self.relevant and self.related_entity_types:
            raise ValueError("Ignored conversation has no related entity types")
        return self


class SegmentClassification(RelevanceClassification):
    id: UUID


class ClassificationBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[SegmentClassification] = Field(min_length=1, max_length=MAX_AI_SEGMENTS)


class Segment(BaseModel):
    id: UUID
    text: str = Field(min_length=1, max_length=6000)
    previous_text: str = Field(default="", max_length=800)


class ContextFact(BaseModel):
    type: EntityType
    id: UUID
    title: str
    description: str = ""
    owner: str | None = None
    due_date: str | None = Field(default=None, alias="dueDate")


class ProjectContext(BaseModel):
    project: str = ""
    facts: list[ContextFact] = Field(default_factory=list)
    complete: bool = True


def validate_batch(value: object, segments: list[Segment]) -> ClassificationBatch:
    try:
        batch = ClassificationBatch.model_validate(value)
        ids = [item.id for item in batch.items]
        if len(ids) != len(set(ids)) or set(ids) != {item.id for item in segments}:
            raise ValueError("Provider must classify exactly the supplied segment IDs")
        return batch
    except ValueError:
        raise StateError(
            "RELEVANCE_INVALID", "Relevance provider returned invalid classifications.", 503
        ) from None


# Narrow project signals and whole-segment social patterns precede model calls.
# Unknown text is retained for context/AI; absence of keywords is not irrelevance.
PROJECT_SIGNALS = (
    (
        r"\b(?:sso|single[ -]sign[ -]on|csv export|requirement|scope change)\b",
        EntityType.REQUIREMENT,
    ),
    (
        r"\b(?:launch date|move (?:the |our )?launch|deployment|milestone|deadline)\b",
        EntityType.MILESTONE,
    ),
    (r"\b(?:production credentials|payment retr(?:y|ies)|postgresql)\b", EntityType.DECISION),
    (r"\b(?:security review|blocked by|blocking dependency)\b", EntityType.DEPENDENCY),
)
SOCIAL = re.compile(
    r"^(?:i (?:went hiking|watched (?:a |the )?movie|had pizza|played football|went to the beach)"
    r"(?: this weekend| yesterday| last night)?|how was your weekend|"
    r"good morning(?: everyone)?|thanks(?: everyone)?|hello(?: everyone)?)\s*[.!?]*$",
    re.I,
)


def rule_classification(text: str) -> RelevanceClassification | None:
    normalized = " ".join(text.split())
    types = list(
        dict.fromkeys(
            kind for pattern, kind in PROJECT_SIGNALS if re.search(pattern, normalized, re.I)
        )
    )
    if types:
        return RelevanceClassification(
            relevant=True,
            confidence=0.9,
            reason=(
                "Explicit project delivery or scope topic; "
                "retained as evidence, not an approved change."
            ),
            relatedEntityTypes=types,
        )
    if SOCIAL.fullmatch(normalized):
        return RelevanceClassification(
            relevant=False,
            confidence=0.95,
            reason="Standalone greeting or personal small talk with no project content.",
            relatedEntityTypes=[],
        )
    return None
