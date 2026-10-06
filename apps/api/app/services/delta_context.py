"""Versioned, bounded canonical snapshots for comparison only."""

import json
from hashlib import sha256
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.deltas import MAX_CONTEXT_CHARACTERS, BaselineRecord, ComparisonContext
from app.domain.events import EventKind
from app.services.project_reads import read_workspace


def comparison_context(session: Session, project_id: UUID) -> tuple[ComparisonContext, str]:
    workspace = read_workspace(session, project_id)
    if workspace is None:
        raise ValueError("Project access must be resolved first")
    baseline = workspace.model_dump(mode="json", by_alias=True)
    baseline.pop("activity")
    baseline.pop("generatedAt")
    for value in baseline.values():
        if isinstance(value, list):
            value.sort(key=lambda row: row["id"])
    fingerprint = sha256(json.dumps(baseline, sort_keys=True).encode()).hexdigest()
    members = {str(member.id): member.name for member in workspace.members}
    context = ComparisonContext(project=workspace.project.name[:240], complete=True, records=[])
    specs = [
        ("requirements", EventKind.REQUIREMENT_CHANGE, {"ACTIVE"}),
        ("decisions", EventKind.DECISION, {"CONFIRMED"}),
        ("milestones", EventKind.MILESTONE_CHANGE, {"PLANNED", "AT_RISK"}),
        ("commitments", EventKind.COMMITMENT, {"OPEN", "IN_PROGRESS"}),
        ("dependencies", EventKind.DEPENDENCY, {"PENDING", "READY", "BLOCKED"}),
        ("risks", EventKind.RISK, {"OPEN"}),
        ("questions", EventKind.OPEN_QUESTION, {"OPEN"}),
    ]
    for category, kind, statuses in specs:
        for row in baseline[category]:
            if row.get("status", row.get("decisionStatus")) not in statuses:
                continue
            values = {
                k: row[k]
                for k in [
                    "title",
                    "description",
                    "phase",
                    "date",
                    "status",
                    "severity",
                    "decisionStatus",
                ]
                if k in row
            }
            if "ownerId" in row:
                values["ownerMention"] = members.get(row["ownerId"])
            if "dueDate" in row:
                values["dueDateText"] = row["dueDate"]
            record = BaselineRecord(
                id=row["id"], kind=kind, version=row["version"], title=row["title"], values=values
            )
            selected = context.model_copy(update={"records": [*context.records, record]})
            if (
                len(selected.records) > 100
                or len(selected.model_dump_json()) > MAX_CONTEXT_CHARACTERS
            ):
                context.complete = False
                continue
            context.records.append(record)
    return context, fingerprint
