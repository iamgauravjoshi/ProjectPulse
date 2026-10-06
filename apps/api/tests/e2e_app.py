"""Playwright-only app entry point. Never imported by the production application.

Inject deterministic extraction transport for real API/database/browser checks.
This does not test Gemini semantic accuracy or introduce a production fallback.
"""

from app.domain.deltas import validate_comparisons
from app.domain.events import validate_extraction
from app.domain.manual_state import StateError
from app.main import app
from app.services.delta_provider import DeltaProviderResult, get_delta_provider
from app.services.event_provider import EventProviderResult, get_event_provider


class BrowserEvents:
    model = "synthetic-playwright-events"
    available = True

    def extract(self, windows, context):
        items = []
        for window in windows:
            text = window.source.text
            if "provider-failure" in text:
                raise StateError("EVENT_PROVIDER_FAILED", "Synthetic provider failure.", 503)
            kind = "REQUIREMENT_CHANGE"
            for token, candidate_kind in [
                ("decision", "DECISION"),
                ("commitment", "COMMITMENT"),
                ("risk", "RISK"),
                ("milestone", "MILESTONE_CHANGE"),
                ("dependency", "DEPENDENCY"),
                ("question", "OPEN_QUESTION"),
            ]:
                if token in text:
                    kind = candidate_kind
            statement = (
                "NEGATED" if "negated" in text else "QUESTION" if "question" in text else "PROPOSAL"
            )
            events = (
                []
                if "no-event" in text
                else [
                    {
                        "kind": kind,
                        "statement": statement,
                        "title": "Synthetic " + kind.lower().replace("_", " "),
                        "description": "Synthetic interpretation for browser acceptance.",
                        "confidence": 0.5 if "low-confidence" in text else 0.9,
                        "ownerMention": "John" if "John" in text else None,
                        "dueDateText": "tomorrow" if "tomorrow" in text else None,
                        "evidence": [{"utteranceId": str(window.source.id), "quote": text[:500]}],
                    }
                ]
            )
            items.append({"id": str(window.source.id), "events": events})
        return EventProviderResult(validate_extraction({"items": items}, windows), 120, 60)


app.dependency_overrides[get_event_provider] = lambda: BrowserEvents()


class BrowserDeltas:
    model = "synthetic-playwright-comparison"
    available = True

    def compare(self, sources, context):
        items = []
        for source in sources:
            text = " ".join(e.quote for e in source.evidence)
            if "delta-failure" in text:
                raise StateError("DELTA_PROVIDER_FAILED", "Synthetic comparison failure.", 503)
            target = next((r for r in context.records if r.kind == source.kind), None)
            outcome, changes = "SAME" if target else "NEW", []
            if source.statement in {"QUESTION", "NEGATED"} or source.confidence < 0.65:
                outcome = "UNCLEAR"
            elif "new-item" in text:
                target, outcome = None, "NEW"
            elif target and "Phase 1" in text and source.kind == "REQUIREMENT_CHANGE":
                outcome, changes = "CHANGE", [{"field": "phase", "proposedText": "1"}]
            elif target and "November 10" in text and source.kind == "MILESTONE_CHANGE":
                outcome, changes = "CHANGE", [{"field": "date", "proposedText": "November 10"}]
            elif target and "tomorrow" in text and source.kind == "COMMITMENT":
                outcome, changes = "CHANGE", [{"field": "dueDateText", "proposedText": "tomorrow"}]
            if not context.complete and outcome == "NEW":
                outcome = "UNCLEAR"
            items.append(
                {
                    "id": str(source.id),
                    "outcome": outcome,
                    "targetId": str(target.id) if target else None,
                    "reason": "Synthetic baseline comparison for browser acceptance; "
                    "human review required.",
                    "confidence": 0.9,
                    "changes": changes,
                }
            )
        return DeltaProviderResult(validate_comparisons({"items": items}, sources, context), 90, 45)


app.dependency_overrides[get_delta_provider] = lambda: BrowserDeltas()
