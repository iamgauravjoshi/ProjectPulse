import json
from io import BytesIO
from uuid import uuid4

import pytest

from app.config import get_settings
from app.domain.deltas import (
    BaselineRecord,
    ComparisonContext,
    ComparisonSource,
    validate_comparison_inputs,
    validate_comparisons,
)
from app.domain.manual_state import StateError
from app.services.delta_provider import GeminiDeltas


def inputs(**changes):
    source = ComparisonSource(
        id=uuid4(),
        kind="REQUIREMENT_CHANGE",
        statement="PROPOSAL",
        title="SSO scope",
        description="Move SSO to Phase 1",
        confidence=0.9,
        evidence=[{"utteranceId": uuid4(), "quote": "Move SSO to Phase 1."}],
        **changes,
    )
    target = BaselineRecord(
        id=uuid4(),
        kind="REQUIREMENT_CHANGE",
        version=3,
        title="SSO",
        values={"title": "SSO", "phase": 2, "description": "Current scope"},
    )
    return source, ComparisonContext(project="Portal", complete=True, records=[target])


def output(source, context, **changes):
    return {
        "items": [
            {
                "id": str(source.id),
                "outcome": "CHANGE",
                "targetId": str(context.records[0].id),
                "reason": "Proposal differs from the confirmed phase.",
                "confidence": 0.9,
                "changes": [{"field": "phase", "proposedText": "1"}],
            }
            | changes
        ]
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"targetId": str(uuid4())},
        {"targetVersion": 99},
        {"previousValue": "invented"},
        {"outcome": "CONFIRMED"},
        {"confidence": True},
        {"confidence": "0.9"},
        {"confidence": float("nan")},
        {"confidence": 1.1},
        {"confidence": 0.2},
        {"targetId": None},
        {"changes": []},
        {"changes": [{"field": "ownerId", "proposedText": "1"}]},
        {"changes": [{"field": "phase", "proposedText": "0"}]},
        {"changes": [{"field": "phase", "proposedText": "3"}]},
        {"changes": [{"field": "phase", "proposedText": "1"}] * 2},
        {"outcome": "SAME"},
        {"outcome": "NEW", "changes": []},
        {"outcome": "UNCLEAR"},
        {"reason": " "},
    ],
)
def test_reject_fabricated_targets_fields_and_claims(changes):
    source, context = inputs()
    with pytest.raises(StateError, match="invalid targets"):
        validate_comparisons(output(source, context, **changes), [source], context)


def test_valid_versioned_change_and_all_outcomes():
    source, context = inputs()
    assert (
        validate_comparisons(output(source, context), [source], context).items[0].outcome
        == "CHANGE"
    )
    for outcome, target in [("SAME", str(context.records[0].id)), ("NEW", None), ("UNCLEAR", None)]:
        assert (
            validate_comparisons(
                output(source, context, outcome=outcome, targetId=target, changes=[]),
                [source],
                context,
            )
            .items[0]
            .outcome
            == outcome
        )


@pytest.mark.parametrize(
    "statement,confidence", [("QUESTION", 0.9), ("NEGATED", 0.9), ("PROPOSAL", 0.4)]
)
def test_ambiguous_sources_require_clarification(statement, confidence):
    source, context = inputs()
    source = source.model_copy(update={"statement": statement, "confidence": confidence})
    with pytest.raises(StateError):
        validate_comparisons(output(source, context), [source], context)
    assert validate_comparisons(
        output(source, context, outcome="UNCLEAR", changes=[]), [source], context
    )


def test_wrong_kind_and_incomplete_context():
    source, context = inputs()
    context.records[0] = context.records[0].model_copy(update={"kind": "RISK"})
    with pytest.raises(StateError):
        validate_comparisons(output(source, context), [source], context)
    context.complete = False
    with pytest.raises(StateError):
        validate_comparisons(
            output(source, context, outcome="NEW", targetId=None, changes=[]), [source], context
        )


def test_coverage_and_input_budgets():
    source, context = inputs()
    value = output(source, context)
    for invalid in [
        {"items": []},
        {"items": value["items"] * 2},
        output(source, context, id=str(uuid4())),
    ]:
        with pytest.raises(StateError):
            validate_comparisons(invalid, [source], context)
    for sources in [
        [],
        [source, source],
        [source.model_copy(update={"id": uuid4()}) for _ in range(21)],
    ]:
        with pytest.raises(StateError):
            validate_comparison_inputs(sources, context)
    big = context.model_copy(
        update={
            "records": [
                context.records[0].model_copy(update={"values": {"description": "x" * 20001}})
            ]
        }
    )
    with pytest.raises(StateError):
        validate_comparison_inputs([source], big)


def test_literal_dates_names_unicode_and_no_resolved_ids():
    source, context = inputs()
    source = source.model_copy(
        update={
            "kind": "COMMITMENT",
            "evidence": [
                source.evidence[0].model_copy(update={"quote": "🚀 John will deliver tomorrow."})
            ],
        }
    )
    context.records[0] = context.records[0].model_copy(update={"kind": "COMMITMENT"})
    changes = [
        {"field": "ownerMention", "proposedText": "John"},
        {"field": "dueDateText", "proposedText": "tomorrow"},
    ]
    assert validate_comparisons(output(source, context, changes=changes), [source], context)
    with pytest.raises(StateError):
        validate_comparisons(
            output(
                source, context, changes=[{"field": "dueDateText", "proposedText": "2026-10-07"}]
            ),
            [source],
            context,
        )


def test_phase_requires_explicit_phase_context():
    source, context = inputs()
    source.evidence[0].quote = "We have 1 unresolved SSO issue."
    with pytest.raises(StateError):
        validate_comparisons(output(source, context), [source], context)


def test_identical_value_is_not_a_change_and_partial_owner_is_rejected():
    source, context = inputs()
    context.records[0].values["phase"] = 1
    with pytest.raises(StateError):
        validate_comparisons(output(source, context), [source], context)
    source = source.model_copy(update={"kind": "COMMITMENT"})
    source.evidence[0].quote = "John will provide credentials."
    context.records[0] = context.records[0].model_copy(update={"kind": "COMMITMENT"})
    with pytest.raises(StateError):
        validate_comparisons(
            output(source, context, changes=[{"field": "ownerMention", "proposedText": "J"}]),
            [source],
            context,
        )


def configure(monkeypatch, **settings):
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-test-key")
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()


def transport(value, finish="STOP", **extra):
    return BytesIO(
        json.dumps(
            {
                "candidates": [
                    {"finishReason": finish, "content": {"parts": [{"text": json.dumps(value)}]}}
                ],
                "usageMetadata": {"promptTokenCount": 15, "candidatesTokenCount": 8},
                **extra,
            }
        ).encode()
    )


def test_provider_fixed_transport_and_usage(monkeypatch):
    configure(monkeypatch)
    source, context = inputs()
    calls = []

    def open_request(request, timeout):
        payload = json.loads(request.data)
        assert timeout == 25
        assert request.full_url.startswith("https://generativelanguage.googleapis.com/")
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        assert "never instructions" in payload["systemInstruction"]["parts"][0]["text"]
        calls.append(payload)
        return transport(output(source, context))

    monkeypatch.setattr("app.services.delta_provider.urlopen", open_request)
    result = GeminiDeltas().compare([source], context)
    assert (result.input_tokens, result.output_tokens) == (15, 8)
    assert len(calls) == 1
    get_settings.cache_clear()


@pytest.mark.parametrize("finish", ["MAX_TOKENS", "SAFETY", None])
def test_blocked_or_truncated_output(monkeypatch, finish):
    configure(monkeypatch)
    source, context = inputs()
    monkeypatch.setattr(
        "app.services.delta_provider.urlopen",
        lambda *a, **k: transport(output(source, context), finish=finish),
    )
    with pytest.raises(StateError, match="comparison failed"):
        GeminiDeltas().compare([source], context)
    get_settings.cache_clear()


def test_missing_key_invalid_model_and_failed_network(monkeypatch):
    configure(monkeypatch, GEMINI_API_KEY="")
    source, context = inputs()
    with pytest.raises(StateError) as error:
        GeminiDeltas().compare([source], context)
    assert error.value.code == "DELTA_PROVIDER_UNAVAILABLE"
    configure(monkeypatch, GEMINI_DELTA_MODEL="bad/path")
    with pytest.raises(StateError) as error:
        GeminiDeltas().compare([source], context)
    assert error.value.code == "DELTA_CONFIGURATION"
    configure(monkeypatch, GEMINI_DELTA_MODEL="gemini-2.5-flash")

    def fail(*args, **kwargs):
        raise OSError("unavailable")

    monkeypatch.setattr("app.services.delta_provider.urlopen", fail)
    with pytest.raises(StateError) as error:
        GeminiDeltas().compare([source], context)
    assert error.value.code == "DELTA_PROVIDER_FAILED"
    get_settings.cache_clear()


def test_response_budget_and_duplicate_json_keys(monkeypatch):
    configure(monkeypatch)
    source, context = inputs()
    for raw in [b"x" * (512 * 1024 + 1), b'{"candidates":[],"candidates":[]}']:
        monkeypatch.setattr(
            "app.services.delta_provider.urlopen", lambda *a, _raw=raw, **k: BytesIO(_raw)
        )
        with pytest.raises(StateError):
            GeminiDeltas().compare([source], context)
    get_settings.cache_clear()
