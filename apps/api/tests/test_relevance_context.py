import json
from pathlib import Path
from uuid import uuid4

from app.domain.relevance import ContextFact, EntityType, ProjectContext
from app.services.relevance_context import contextual_rule


def raj_context(**changes):
    return ProjectContext(
        project="Client Portal",
        members=["Raj"],
        facts=[
            ContextFact(
                type=EntityType.COMMITMENT,
                id=uuid4(),
                title="Critical Friday deployment",
                owner="Raj",
                dueDate="2026-10-09",
            )
        ],
        **changes,
    )


def test_availability_requires_explicit_owned_context():
    assert contextual_rule("Raj is off Friday.", raj_context()).relevant
    without = ProjectContext(project="Client Portal", members=["Raj"], facts=[])
    assert not contextual_rule("Raj is off Friday.", without).relevant
    assert contextual_rule("Raj is off Friday.", ProjectContext()) is None
    assert (
        contextual_rule(
            "Raj is off Friday.", ProjectContext(project="Client Portal", complete=False)
        )
        is None
    )
    ambiguous = raj_context()
    ambiguous.members = ["Raj Kapoor", "Raj Patel"]
    assert contextual_rule("Raj is off Friday.", ambiguous) is None
    unknown_date = raj_context()
    unknown_date.facts[0].due_date = None
    assert contextual_rule("Raj is off Friday.", unknown_date) is None
    assert contextual_rule("Raj is off Thursday.", raj_context()) is None


def test_non_selected_project_is_ignored_but_cross_impact_retained():
    context = raj_context()
    assert not contextual_rule("I installed PostgreSQL for my hobby app.", context).relevant
    assert not contextual_rule("What was the movie launch date?", context).relevant
    assert not contextual_rule(
        "The deployment in another client's project failed.", context
    ).relevant
    assert contextual_rule(
        "Our project depends on the deployment in another client's project.", context
    ).relevant


def test_context_benchmark_tracks_unresolved_separately_from_errors():
    data = json.loads(
        (Path(__file__).resolve().parents[3] / "docs/examples/relevance-benchmark.json").read_text()
    )
    results = [(r, contextual_rule(r["text"], raj_context())) for r in data["items"]]
    assert not [
        r["id"] for r, c in results if c is not None and c.relevant != r["expectedRelevant"]
    ]
    assert sum(c is not None for _, c in results) == 35
    assert sum(c is None for _, c in results) == 15


def test_other_project_phrase_does_not_hide_mixed_project_content():
    context = raj_context()
    assert contextual_rule(
        "I installed PostgreSQL for my hobby app, but the deployment is blocked.", context
    ).relevant
    assert contextual_rule(
        "We must update SSO because another client's project exposed a vulnerability.", context
    ).relevant
