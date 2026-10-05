import json
from io import BytesIO
from uuid import uuid4

import pytest

from app.config import REPOSITORY_ROOT, get_settings
from app.domain.events import EventWindow, SourceSegment, validate_extraction, validate_inputs
from app.domain.manual_state import StateError
from app.domain.relevance import ProjectContext
from app.services.event_provider import GeminiEvents


def window(text="John will provide credentials tomorrow.", **changes):
    return EventWindow(
        source=SourceSegment(id=uuid4(), sequence=1, speaker="Sarah", text=text), **changes
    )


def event(w, **changes):
    return {
        "kind": "COMMITMENT",
        "statement": "STATEMENT",
        "title": "Credentials",
        "description": "An interpreted promise, not a confirmed owner assignment.",
        "confidence": 0.9,
        "ownerMention": "John",
        "dueDateText": "tomorrow",
        "evidence": [{"utteranceId": str(w.source.id), "quote": w.source.text}],
    } | changes


def batch(w, **changes):
    return {"items": [{"id": str(w.source.id), "events": [event(w, **changes)]}]}


@pytest.mark.parametrize(
    "changes",
    [
        {"confidence": True},
        {"confidence": "0.9"},
        {"confidence": float("nan")},
        {"confidence": 1.1},
        {"kind": "UNKNOWN"},
        {"statement": "CONFIRMED"},
        {"title": " "},
        {"description": "x" * 1601},
        {"ownerId": str(uuid4())},
        {"ownerMention": "Sarah"},
        {"dueDateText": "2026-10-06"},
        {"dueDateText": ""},
        {"evidence": []},
        {"evidence": [{"utteranceId": str(uuid4()), "quote": "John"}]},
    ],
)
def test_reject_invalid_or_invented_fields(changes):
    w = window()
    with pytest.raises(StateError, match="invalid or uncited"):
        validate_extraction(batch(w, **changes), [w])


def test_exact_source_coverage_and_duplicate_events():
    a, b = window(), window()
    for value in [
        {"items": []},
        batch(a),
        {"items": batch(a)["items"] * 2},
        {"items": [{"id": str(uuid4()), "events": []}]},
        {"items": [{"id": str(a.source.id), "events": [event(a), event(a)]}]},
    ]:
        with pytest.raises(StateError):
            validate_extraction(value, [a, b] if value == batch(a) else [a])
    assert (
        validate_extraction({"items": [{"id": str(a.source.id), "events": []}]}, [a])
        .items[0]
        .events
        == []
    )


def test_neighbor_citation_requires_primary_and_exact_quote():
    previous = SourceSegment(
        id=uuid4(), sequence=0, speaker="John", text="I will provide credentials tomorrow."
    )
    w = window("Yes, John will provide credentials tomorrow.", previous=previous)
    quotes = [
        {"utteranceId": str(w.source.id), "quote": w.source.text},
        {"utteranceId": str(previous.id), "quote": previous.text},
    ]
    assert len(validate_extraction(batch(w, evidence=quotes), [w]).items[0].events[0].evidence) == 2
    for evidence in [
        quotes[1:],
        quotes + [quotes[0]],
        [quotes[0] | {"quote": "Not in source"}],
        [quotes[0], quotes[0]],
    ]:
        with pytest.raises(StateError):
            validate_extraction(batch(w, evidence=evidence), [w])


def test_unicode_quotes_and_literal_word_boundaries():
    w = window("🚀 Sarah Chen will review SSO tomorrow.")
    assert validate_extraction(batch(w, ownerMention="Sarah Chen"), [w])
    for mention in ["I", "Sarah C", "Chen will review SSO tomorrow. invented"]:
        with pytest.raises(StateError):
            validate_extraction(batch(w, ownerMention=mention), [w])


def test_input_window_and_context_budgets():
    a = window()
    for windows, context in [
        ([], ProjectContext()),
        ([a, a], ProjectContext()),
        ([window() for _ in range(21)], ProjectContext()),
        ([window("x" * 6000) for _ in range(4)], ProjectContext()),
        ([a], ProjectContext(project="x" * 20001)),
        (
            [
                window(
                    previous=SourceSegment(
                        id=uuid4(), sequence=5, speaker="Other", text="Wrong neighbor"
                    )
                )
            ],
            ProjectContext(),
        ),
    ]:
        with pytest.raises(StateError, match="budget"):
            validate_inputs(windows, context)


def test_labeled_contract_examples_all_event_kinds():
    rows = json.loads(
        (REPOSITORY_ROOT / "tests/fixtures/ai-evaluation/events.json").read_text(encoding="utf-8")
    )["items"]
    kinds = set()
    for row in rows:
        w = window(row["text"])
        values = (
            []
            if row["kind"] is None
            else [
                event(
                    w, **{k: row[k] for k in ["kind", "statement", "ownerMention", "dueDateText"]}
                )
            ]
        )
        validate_extraction({"items": [{"id": str(w.source.id), "events": values}]}, [w])
        kinds.add(row["kind"])
    assert len(rows) == 16 and len(kinds - {None}) == 7


def test_gemini_schema_request_exact_ids_usage_and_key_scope(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-event-key")
    monkeypatch.setenv("GEMINI_EVENT_MODEL", "gemini-3.5-flash-lite")
    get_settings.cache_clear()
    w = window()

    def send(request, timeout):
        assert request.full_url.endswith("/gemini-3.5-flash-lite:generateContent")
        assert request.get_header("X-goog-api-key") == "synthetic-event-key" and timeout == 25
        payload = json.loads(request.data)
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        assert "untrusted" in payload["systemInstruction"]["parts"][0]["text"]
        user = json.loads(payload["contents"][0]["parts"][0]["text"])
        assert user["windows"][0]["source"]["id"] == str(w.source.id)
        assert "synthetic-event-key" not in json.dumps(payload)
        return BytesIO(
            json.dumps(
                {
                    "candidates": [
                        {
                            "finishReason": "STOP",
                            "content": {"parts": [{"text": json.dumps(batch(w))}]},
                        }
                    ],
                    "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 20},
                }
            ).encode()
        )

    monkeypatch.setattr("app.services.event_provider.urlopen", send)
    try:
        output = GeminiEvents().extract([w], ProjectContext(project="Client Portal"))
        assert output.input_tokens == 50 and output.output_tokens == 20
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize(
    "raw",
    [
        b"bad-json",
        b"x" * (512 * 1024 + 1),
        b'{"candidates":[]}',
        b'{"candidates":[{"finishReason":"MAX_TOKENS"}]}',
        b'{"candidates":[],"candidates":[]}',
    ],
)
def test_malformed_truncated_blocked_output_safe_error(monkeypatch, raw):
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.event_provider.urlopen", lambda *_args, **_kwargs: BytesIO(raw)
    )
    try:
        with pytest.raises(StateError, match="failed"):
            GeminiEvents().extract([window()], ProjectContext())
    finally:
        get_settings.cache_clear()


def test_missing_configuration_invalid_model_and_network_failure(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    with pytest.raises(StateError, match="Configure"):
        GeminiEvents().extract([window()], ProjectContext())
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic")
    monkeypatch.setenv("GEMINI_EVENT_MODEL", "https://other.example")
    get_settings.cache_clear()
    with pytest.raises(StateError, match="valid Gemini"):
        GeminiEvents().extract([window()], ProjectContext())
    monkeypatch.setenv("GEMINI_EVENT_MODEL", "gemini-3.5-flash-lite")
    get_settings.cache_clear()

    def failed(*_args, **_kwargs):
        raise TimeoutError("Secret internal detail")

    monkeypatch.setattr("app.services.event_provider.urlopen", failed)
    with pytest.raises(StateError, match="Check model access") as error:
        GeminiEvents().extract([window()], ProjectContext())
    assert "Secret internal detail" not in str(error.value)
    get_settings.cache_clear()
