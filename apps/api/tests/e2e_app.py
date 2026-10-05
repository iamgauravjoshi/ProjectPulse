"""Playwright-only app entry point. Never imported by the production application.

Inject deterministic extraction transport for real API/database/browser checks.
This does not test Gemini semantic accuracy or introduce a production fallback.
"""

from app.domain.events import validate_extraction
from app.domain.manual_state import StateError
from app.main import app
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
