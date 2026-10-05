"""Validate labeled extraction fixtures; --live explicitly calls configured Gemini."""

import argparse
import json
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from app.config import REPOSITORY_ROOT
from app.domain.events import EventWindow, SourceSegment, validate_extraction
from app.domain.manual_state import StateError
from app.domain.relevance import ProjectContext
from app.services.event_provider import get_event_provider


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    rows: list[dict[str, Any]] = json.loads(
        (REPOSITORY_ROOT / "tests/fixtures/ai-evaluation/events.json").read_text(encoding="utf-8")
    )["items"]
    windows = [
        EventWindow(
            source=SourceSegment(
                id=uuid5(NAMESPACE_URL, f"projectpulse-event-example-{i}"),
                sequence=i,
                speaker="Sarah",
                text=row["text"],
            )
        )
        for i, row in enumerate(rows)
    ]
    expected = {
        "items": [
            {
                "id": str(w.source.id),
                "events": []
                if row["kind"] is None
                else [
                    {
                        "kind": row["kind"],
                        "statement": row["statement"],
                        "title": "Labeled contract example",
                        "description": "Manually supplied contract label.",
                        "confidence": 0.9,
                        "ownerMention": row["ownerMention"],
                        "dueDateText": row["dueDateText"],
                        "evidence": [{"utteranceId": str(w.source.id), "quote": w.source.text}],
                    }
                ],
            }
            for w, row in zip(windows, rows, strict=True)
        ]
    }
    validate_extraction(expected, windows)
    if not args.live:
        print(
            json.dumps(
                {
                    "mode": "labeled_contract_validation",
                    "examples": len(rows),
                    "note": "No model called. Valid labels are not extraction accuracy.",
                },
                indent=2,
            )
        )
        return 0
    provider = get_event_provider()
    try:
        result = provider.extract(
            windows, ProjectContext(project="Synthetic Client Portal project")
        )
    except StateError as exc:
        print(
            json.dumps(
                {
                    "mode": "live_gemini",
                    "model": provider.model,
                    "providerError": exc.code,
                    "evaluated": 0,
                },
                indent=2,
            )
        )
        return 2
    outputs = {item.id: item.events for item in result.batch.items}
    mismatches = []
    for index, (w, row) in enumerate(zip(windows, rows, strict=True)):
        events = outputs[w.source.id]
        matched = (
            not events
            if row["kind"] is None
            else len(events) == 1
            and all(
                events[0].model_dump(by_alias=True)[field] == row[field]
                for field in ["kind", "statement", "ownerMention", "dueDateText"]
            )
        )
        if not matched:
            mismatches.append(index + 1)
    print(
        json.dumps(
            {
                "mode": "live_gemini",
                "model": provider.model,
                "examples": len(rows),
                "mismatchedExamples": mismatches,
                "inputTokens": result.input_tokens,
                "outputTokens": result.output_tokens,
                "interpretations": result.batch.model_dump(mode="json", by_alias=True),
                "note": "Small synthetic smoke set. Review quotes, summaries and intent manually; "
                "this is not production accuracy.",
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
