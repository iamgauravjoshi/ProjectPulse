"""Selected current canonical context, with conservative context-dependent rules."""

import json
import re
from collections.abc import Sequence
from datetime import date
from hashlib import sha256
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.relevance import (
    ContextFact,
    EntityType,
    ProjectContext,
    RelevanceClassification,
    rule_classification,
)
from app.domain.workspace import CanonicalView
from app.services.project_reads import read_workspace


def project_context(session: Session, project_id: UUID) -> tuple[ProjectContext, str]:
    workspace = read_workspace(session, project_id)
    if workspace is None:
        raise ValueError("Project access must be checked first")
    baseline = workspace.model_dump(mode="json", by_alias=True)
    baseline.pop("activity")
    baseline.pop("generatedAt")
    for value in baseline.values():
        if isinstance(value, list):
            value.sort(key=lambda row: row["id"])
    fingerprint = sha256(json.dumps(baseline, sort_keys=True).encode()).hexdigest()
    members = {member.id: member.name for member in workspace.members}
    specs: list[tuple[Sequence[CanonicalView], EntityType, set[str]]] = [
        (workspace.commitments, EntityType.COMMITMENT, {"OPEN", "IN_PROGRESS"}),
        (workspace.milestones, EntityType.MILESTONE, {"PLANNED", "AT_RISK"}),
        (workspace.requirements, EntityType.REQUIREMENT, {"ACTIVE"}),
        (workspace.decisions, EntityType.DECISION, {"CONFIRMED"}),
        (workspace.risks, EntityType.RISK, {"OPEN"}),
        (workspace.dependencies, EntityType.DEPENDENCY, {"PENDING", "READY", "BLOCKED"}),
        (workspace.questions, EntityType.OPEN_QUESTION, {"OPEN"}),
    ]
    facts: list[ContextFact] = []
    characters = 0
    complete = len(workspace.members) <= 100
    for records, kind, statuses in specs:
        for record in records:
            values = record.model_dump(mode="json", by_alias=True)
            if values.get("status", values.get("decisionStatus")) not in statuses:
                continue
            details = {
                key: values[key]
                for key in ["status", "decisionStatus", "phase", "date", "severity", "dueDate"]
                if key in values
            }
            description = record.description[:350] + "\nCurrent fields: " + json.dumps(details)
            owner_id = getattr(record, "owner_id", None)
            fact = ContextFact(
                type=kind,
                id=record.id,
                title=record.title[:240],
                description=description,
                owner=members.get(owner_id) if isinstance(owner_id, UUID) else None,
                dueDate=values.get("dueDate"),
            )
            size = len(fact.model_dump_json(by_alias=True))
            if len(facts) >= 60 or characters + size > 12_000:
                complete = False
                continue
            facts.append(fact)
            characters += size
    return ProjectContext(
        project=workspace.project.name[:240],
        facts=facts,
        complete=complete,
        members=[m.name for m in workspace.members][:100],
    ), fingerprint


AVAILABILITY = re.compile(
    r"^([\w'-]+(?: [\w'-]+){0,3}) (?:is|will be) (?:off|unavailable|on leave) "
    r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[.!?]*$",
    re.I,
)
NON_PROJECT = re.compile(
    r"^(?:I (?:installed|used|tried) [^.!?;]+ for my hobby (?:app|project)|"
    r"What was the movie launch date|The deployment in another client's project failed)[.!?]*$",
    re.I,
)
CROSS_IMPACT = re.compile(
    r"\b(?:our project|our deployment|we depend|blocking us|affects our)\b", re.I
)


def contextual_rule(text: str, context: ProjectContext) -> RelevanceClassification | None:
    normalized = " ".join(text.split())
    if NON_PROJECT.fullmatch(normalized) and not CROSS_IMPACT.search(normalized):
        return RelevanceClassification(
            relevant=False,
            confidence=0.9,
            reason="Explicit hobby, film or other-client topic without a "
            "stated impact on this project.",
            relatedEntityTypes=[],
        )
    match = AVAILABILITY.fullmatch(normalized)
    if match and context.project:
        name, weekday = match.groups()
        possible_members = [
            m
            for m in context.members
            if m.casefold() == name.casefold() or m.split()[0].casefold() == name.casefold()
        ]
        if len(set(possible_members)) > 1:
            return None
        names = {name.casefold()} | {m.casefold() for m in possible_members}
        owned = [f for f in context.facts if f.owner and f.owner.casefold() in names]
        for fact in owned:
            if (
                fact.type == EntityType.COMMITMENT
                and fact.due_date
                and re.search(
                    r"\b(?:deployment|release|launch)\b", fact.title + " " + fact.description, re.I
                )
            ):
                if (
                    date.fromisoformat(fact.due_date).strftime("%A").casefold()
                    == weekday.casefold()
                ):
                    return RelevanceClassification(
                        relevant=True,
                        confidence=0.88,
                        reason=(
                            "Availability may affect the explicitly owned obligation: "
                            f"{fact.title[:180]}. "
                            "No project change is approved."
                        ),
                        relatedEntityTypes=[EntityType.COMMITMENT, EntityType.RISK],
                    )
        if not owned and context.complete:
            return RelevanceClassification(
                relevant=False,
                confidence=0.8,
                reason="No active owned obligation links this availability "
                "statement to the complete selected project context.",
                relatedEntityTypes=[],
            )
        return None
    return rule_classification(text)
