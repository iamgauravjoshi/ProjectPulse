import json
import math
from collections.abc import Sequence
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.dependencies import get_database_session
from app.config import get_settings
from app.db.models import Document, DocumentChunk, Project
from app.domain.chunks import chunk_segments
from app.domain.manual_state import StateError
from app.main import app
from app.repositories.audit import AuditRepository
from app.services.demo_seed import DEMO_PROJECT_ID, seed_demo
from app.services.embeddings import (
    MODEL,
    GeminiEmbeddings,
    get_embedding_provider,
    normalized_vector,
)

ROOT = f"/api/v1/projects/{DEMO_PROJECT_ID}/documents"


def test_chunk_boundaries_provenance_overlap_and_budget():
    text = "x" * 2500
    chunks = chunk_segments([{"page": 3, "section": "Scope", "text": text}])
    assert [x["metadata_json"]["start"] for x in chunks] == [0, 880, 1760]
    assert chunks[0]["raw_text"][-120:] == chunks[1]["raw_text"][:120]
    assert all(
        x["page"] == 3 and x["section"] == "Scope" and len(x["raw_text"]) <= 1000 for x in chunks
    )
    assert chunks[-1]["metadata_json"]["end"] == 2500
    with pytest.raises(ValueError):
        chunk_segments([{"page": None, "section": None, "text": "x" * 300000}])


@pytest.mark.parametrize(
    "value",
    [[0.0] * 768, [1.0] * 767, [float("nan")] * 768, [float("inf")] * 768, [True] * 768, "bad"],
)
def test_invalid_vectors_are_never_stored(value):
    with pytest.raises(StateError):
        normalized_vector(value)


def test_gemini_contract_batches_document_and_query_tasks_and_normalizes(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-contract-key")
    get_settings.cache_clear()
    requests = []

    def send(request, timeout):
        payload = json.loads(request.data)
        requests.append(payload)
        assert request.full_url.endswith(f"/models/{MODEL}:batchEmbedContents")
        assert request.get_header("X-goog-api-key") == "synthetic-contract-key" and timeout <= 8
        return BytesIO(
            json.dumps(
                {"embeddings": [{"values": [2.0] * 768} for _ in payload["requests"]]}
            ).encode()
        )

    monkeypatch.setattr("app.services.embeddings.urlopen", send)
    try:
        provider = GeminiEmbeddings()
        vectors = provider.embed(["text"] * 17)
        assert len(requests) == 2 and len(vectors) == 17
        assert math.isclose(sum(x * x for x in vectors[0]), 1)
        assert requests[0]["requests"][0]["embedContentConfig"] == {
            "taskType": "RETRIEVAL_DOCUMENT",
            "outputDimensionality": 768,
        }
        provider.embed(["query"], query=True)
        assert requests[-1]["requests"][0]["embedContentConfig"]["taskType"] == "RETRIEVAL_QUERY"
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize(
    "response",
    [
        b"bad",
        b"{}",
        json.dumps({"embeddings": []}).encode(),
        json.dumps({"embeddings": [{"values": [0] * 768}]}).encode(),
    ],
)
def test_provider_failures_sanitized(monkeypatch, response):
    monkeypatch.setenv("GEMINI_API_KEY", "never-echo-this-key")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.embeddings.urlopen", lambda *args, **kwargs: BytesIO(response)
    )
    try:
        with pytest.raises(StateError) as error:
            GeminiEmbeddings().embed(["text"])
        assert "never-echo-this-key" not in str(error.value)
    finally:
        get_settings.cache_clear()


class FakeProvider:
    model = MODEL
    available = True

    def __init__(self):
        self.calls = 0
        self.fail = False
        self.invalid = False

    def embed(self, texts: Sequence[str], *, query: bool = False) -> list[list[float]]:
        self.calls += 1
        if self.fail:
            raise StateError("EMBEDDING_PROVIDER_FAILED", "Provider unavailable", 503)
        return [[1.0] + [0.0] * (767 if not self.invalid else 2) for _ in texts]


@pytest.fixture
def indexed_client(db_session):
    seed_demo(db_session)
    provider = FakeProvider()
    app.dependency_overrides[get_database_session] = lambda: db_session
    app.dependency_overrides[get_embedding_provider] = lambda: provider
    try:
        with TestClient(app) as client:
            yield client, provider
    finally:
        app.dependency_overrides.pop(get_database_session, None)
        app.dependency_overrides.pop(get_embedding_provider, None)


@pytest.mark.integration
def test_vectors_provenance_idempotence_and_delete_cascade(db_session, indexed_client):
    client, provider = indexed_client
    doc = client.post(
        ROOT, params={"filename": "scope.md"}, content=b"# Scope\n" + b"x" * 2500
    ).json()
    response = client.post(f"{ROOT}/{doc['id']}/index")
    assert response.status_code == 200, response.text
    assert response.json()["indexStatus"] == "INDEXED" and response.json()["indexedChunks"] == 3
    chunks = db_session.scalars(select(DocumentChunk)).all()
    assert len(chunks) == 3
    assert all(
        x.project_id == DEMO_PROJECT_ID
        and str(x.document_id) == doc["id"]
        and x.section == "Scope"
        and len(x.embedding) == 768
        and x.embedding_model == MODEL
        for x in chunks
    )
    assert client.post(f"{ROOT}/{doc['id']}/index").status_code == 200 and provider.calls == 1
    duplicate = client.post(
        ROOT, params={"filename": "renamed.md"}, content=b"# Scope\n" + b"x" * 2500
    ).json()
    assert duplicate["id"] == doc["id"]
    assert client.delete(f"{ROOT}/{doc['id']}").status_code == 204
    assert db_session.scalar(select(func.count()).select_from(DocumentChunk)) == 0


@pytest.mark.integration
@pytest.mark.parametrize("invalid", [False, True])
def test_failed_index_keeps_traceable_chunks_without_fake_vectors_then_recovers(
    db_session, indexed_client, invalid
):
    client, provider = indexed_client
    provider.fail = not invalid
    provider.invalid = invalid
    doc = client.post(ROOT, params={"filename": "scope.txt"}, content=b"source evidence").json()
    assert client.post(f"{ROOT}/{doc['id']}/index").status_code == 503
    assert client.get(f"{ROOT}/{doc['id']}").json()["indexStatus"] == "FAILED"
    assert all(
        x.embedding is None and x.embedding_model is None
        for x in db_session.scalars(select(DocumentChunk))
    )
    provider.fail = False
    provider.invalid = False
    assert client.post(f"{ROOT}/{doc['id']}/index").json()["indexStatus"] == "INDEXED"


@pytest.mark.integration
def test_missing_key_is_honest_and_does_not_call_google(db_session, indexed_client, monkeypatch):
    client, _ = indexed_client
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    app.dependency_overrides[get_embedding_provider] = lambda: GeminiEmbeddings()
    monkeypatch.setattr(
        "app.services.embeddings.urlopen",
        lambda *a, **kw: pytest.fail("Must not call provider without a key"),
    )
    try:
        doc = client.post(ROOT, params={"filename": "scope.txt"}, content=b"source").json()
        response = client.post(f"{ROOT}/{doc['id']}/index")
        assert (
            response.status_code == 503
            and response.json()["error"]["code"] == "EMBEDDINGS_UNAVAILABLE"
        )
        assert client.get(f"{ROOT}/{doc['id']}").json()["indexStatus"] == "UNAVAILABLE"
        assert db_session.scalar(select(DocumentChunk)).embedding is None
    finally:
        get_settings.cache_clear()


@pytest.mark.integration
def test_outside_project_index_cannot_call_provider(db_session, indexed_client):
    client, provider = indexed_client
    other = Project(name="Outside")
    db_session.add(other)
    db_session.flush()
    response = client.post(f"/api/v1/projects/{other.id}/documents/{uuid4()}/index")
    assert response.status_code == 404 and provider.calls == 0


@pytest.mark.integration
def test_index_audit_failure_rolls_back_all_vectors(db_session, indexed_client, monkeypatch):
    client, _ = indexed_client
    doc = client.post(ROOT, params={"filename": "scope.txt"}, content=b"evidence").json()

    def fail(*args, **kwargs):
        raise RuntimeError("audit failed")

    monkeypatch.setattr(AuditRepository, "append", fail)
    with pytest.raises(RuntimeError):
        client.post(f"{ROOT}/{doc['id']}/index")
    assert db_session.scalar(select(DocumentChunk)).embedding is None
    assert db_session.get(Document, doc["id"]).index_status == "PENDING"


@pytest.mark.integration
def test_deleted_document_is_not_resurrected_after_provider_returns(db_session, indexed_client):
    from uuid import UUID

    from app.services.documents import delete_document

    client, provider = indexed_client
    doc = client.post(ROOT, params={"filename": "scope.txt"}, content=b"evidence").json()

    def delete_during_call(texts, **kwargs):
        delete_document(db_session, DEMO_PROJECT_ID, UUID(doc["id"]))
        return [[1.0] + [0.0] * 767 for _ in texts]

    provider.embed = delete_during_call
    assert client.post(f"{ROOT}/{doc['id']}/index").status_code == 404
    assert db_session.scalar(select(func.count()).select_from(Document)) == 0
    assert db_session.scalar(select(func.count()).select_from(DocumentChunk)) == 0
