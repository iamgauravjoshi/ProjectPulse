"""Run the labeled relevance benchmark; --live explicitly calls server-configured Gemini."""

import argparse
import json
from uuid import NAMESPACE_URL, uuid5

from app.config import REPOSITORY_ROOT
from app.domain.manual_state import StateError
from app.domain.relevance import (
    CONFIDENCE_THRESHOLD,
    ContextFact,
    EntityType,
    ProjectContext,
    Segment,
)
from app.services.relevance_context import contextual_rule
from app.services.relevance_provider import get_relevance_provider


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    data = json.loads((REPOSITORY_ROOT / "docs/examples/relevance-benchmark.json").read_text())
    context = ProjectContext(
        project="Client Portal Modernization",
        members=["Raj"],
        facts=[
            ContextFact(
                type=EntityType.COMMITMENT,
                id=uuid5(NAMESPACE_URL, "projectpulse-benchmark-deployment"),
                title="Critical Friday deployment",
                owner="Raj",
                dueDate="2026-10-09",
            )
        ],
    )
    rows = data["items"]
    predictions = {}
    pending = []
    for row in rows:
        id = uuid5(NAMESPACE_URL, row["id"])
        result = contextual_rule(row["text"], context)
        if result is not None:
            predictions[id] = result
        else:
            pending.append(Segment(id=id, text=row["text"], previous_text=row["previousText"]))
    rule_count = len(predictions)
    error = None
    if args.live and pending:
        try:
            output = get_relevance_provider().classify(pending, context)
            predictions.update({item.id: item for item in output.batch.items})
        except StateError as exc:
            error = exc.code
    false_positives: list[str] = []
    false_negatives: list[str] = []
    uncertain = []
    unresolved = []
    for row in rows:
        result = predictions.get(uuid5(NAMESPACE_URL, row["id"]))
        if result is None:
            unresolved.append(row["id"])
        elif result.confidence < CONFIDENCE_THRESHOLD:
            uncertain.append(row["id"])
        elif result.relevant != row["expectedRelevant"]:
            (false_positives if result.relevant else false_negatives).append(row["id"])
    print(
        json.dumps(
            {
                "mode": "live_gemini" if args.live else "contextual_rules_only",
                "examples": len(rows),
                "ruleClassified": rule_count,
                "falsePositives": false_positives,
                "falseNegatives": false_negatives,
                "uncertain": uncertain,
                "unresolved": unresolved,
                "providerError": error,
                "note": "Synthetic manually labeled smoke set; this is not production accuracy.",
            },
            indent=2,
        )
    )
    return 2 if error else 1 if false_positives or false_negatives else 0


if __name__ == "__main__":
    raise SystemExit(main())
