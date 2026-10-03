from collections.abc import Sequence
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.dependencies import get_database_session
from app.db.models import AuditEvent, Project, ProjectMember
from app.domain.manual_state import StateError
from app.main import app
from app.services.demo_seed import DEMO_PROJECT_ID, seed_demo
from app.services.embeddings import MODEL, get_embedding_provider
from app.services.project_access import LOCAL_DEMO_ACTOR_ID

ROOT = f"/api/v1/projects/{DEMO_PROJECT_ID}"


class Provider:
    model = MODEL
    available = False

    def __init__(self):
        self.calls = 0
        self.fail = False
        self.before_query = None

    def embed(self, texts: Sequence[str], *, query: bool = False) -> list[list[float]]:
        self.calls += 1
        if self.fail:
            raise StateError("EMBEDDING_PROVIDER_FAILED", "failure", 503)
        if query and self.before_query:
            self.before_query()
        return [
            [1.0] + [0.0] * 767 if query or "credentials" in text else [0.0, 1.0] + [0.0] * 766
            for text in texts
        ]


@pytest.fixture
def client(db_session):
    seed_demo(db_session)
    provider = Provider()
    app.dependency_overrides[get_database_session] = lambda: db_session
    app.dependency_overrides[get_embedding_provider] = lambda: provider
    try:
        with TestClient(app) as client:
            yield client, provider
    finally:
        app.dependency_overrides.pop(get_database_session, None)
        app.dependency_overrides.pop(get_embedding_provider, None)


def search(client, query, **params):
    return client.get(f"{ROOT}/context/search", params={"query": query, **params})


@pytest.mark.integration
def test_search_returns_actual_confirmed_baseline_not_proposals_or_whole_history(
    db_session, client
):
    api, provider = client
    for status in [
        "DISCUSSION",
        "PROPOSAL",
        "PROVISIONAL",
        "REVIEW_REQUIRED",
        "CONFIRMED",
        "SUPERSEDED",
        "REJECTED",
    ]:
        response = api.post(
            f"{ROOT}/state/decisions",
            json={"title": f"Unique choice {status}", "decisionStatus": status},
        )
        assert response.status_code == 201
    before = db_session.scalar(select(func.count()).select_from(AuditEvent))
    data = search(api, "Unique choice").json()
    assert data["projectId"] == str(DEMO_PROJECT_ID) and data["semanticStatus"] == "unavailable"
    assert (
        len(data["matches"]) == 1 and data["matches"][0]["facts"]["decisionStatus"] == "CONFIRMED"
    )
    assert data["matches"][0]["canonical"] and provider.calls == 0
    assert db_session.scalar(select(func.count()).select_from(AuditEvent)) == before


@pytest.mark.integration
def test_text_evidence_search_works_before_index_and_preserves_scope_location(client):
    api, _ = client
    doc = api.post(
        f"{ROOT}/documents",
        params={"filename": "scope.md"},
        content=b"# Scope\nLaunch credentials require security approval.",
    ).json()
    data = search(api, "credentials approval").json()
    evidence = [x for x in data["matches"] if x["kind"] == "document"]
    assert (
        len(evidence) == 1
        and evidence[0]["documentId"] == doc["id"]
        and not evidence[0]["canonical"]
    )
    assert (
        evidence[0]["section"] == "Scope"
        and evidence[0]["page"] is None
        and evidence[0]["start"] == 0
        and evidence[0]["end"] > 0
    )
    assert "security approval" in evidence[0]["excerpt"]
    api.delete(f"{ROOT}/documents/{doc['id']}")
    assert not [
        x for x in search(api, "credentials approval").json()["matches"] if x["kind"] == "document"
    ]


@pytest.mark.integration
def test_semantic_cosine_neighbors_are_real_project_scoped_vectors(client, db_session):
    api, provider = client
    provider.available = True
    relevant = api.post(
        f"{ROOT}/documents",
        params={"filename": "scope.txt"},
        content=b"Obtain credentials from security.",
    ).json()
    irrelevant = api.post(
        f"{ROOT}/documents",
        params={"filename": "catering.txt"},
        content=b"Lunch menus and catering.",
    ).json()
    for doc in [relevant, irrelevant]:
        assert api.post(f"{ROOT}/documents/{doc['id']}/index").status_code == 200
    hidden = Project(name="Hidden")
    db_session.add(hidden)
    db_session.flush()
    db_session.add(
        ProjectMember(project_id=hidden.id, user_id=LOCAL_DEMO_ACTOR_ID, role="PRODUCT_OWNER")
    )
    db_session.flush()
    outside = api.post(
        f"/api/v1/projects/{hidden.id}/documents",
        params={"filename": "outside.txt"},
        content=b"credentials outside",
    ).json()
    assert (
        api.post(f"/api/v1/projects/{hidden.id}/documents/{outside['id']}/index").status_code == 200
    )
    data = search(api, "permissions").json()
    assert data["semanticStatus"] == "ready" and len(data["matches"]) == 1
    assert data["matches"][0]["documentId"] == relevant["id"]
    assert all(x["projectId"] == str(DEMO_PROJECT_ID) for x in data["matches"])


@pytest.mark.integration
def test_provider_failure_returns_honest_lexical_fallback(client):
    api, provider = client
    provider.available = True
    doc = api.post(
        f"{ROOT}/documents", params={"filename": "scope.txt"}, content=b"credentials source"
    ).json()
    api.post(f"{ROOT}/documents/{doc['id']}/index")
    provider.fail = True
    data = search(api, "credentials").json()
    assert data["semanticStatus"] == "failed" and any(
        x.get("documentId") == doc["id"] for x in data["matches"]
    )


@pytest.mark.integration
def test_no_indexed_vectors_does_not_charge_query_provider(client):
    api, provider = client
    provider.available = True
    data = search(api, "PostgreSQL").json()
    assert data["semanticStatus"] == "not_indexed" and provider.calls == 0
    assert any(x["kind"] == "record" and "PostgreSQL" in x["excerpt"] for x in data["matches"])


@pytest.mark.integration
@pytest.mark.parametrize(
    "params",
    [
        {"query": ""},
        {"query": "   "},
        {"query": "x" * 401},
        {"query": "hello", "limit": 0},
        {"query": "hello", "limit": 9},
    ],
)
def test_query_bounds(client, params):
    api, _ = client
    assert api.get(f"{ROOT}/context/search", params=params).status_code == 422


@pytest.mark.integration
def test_small_context_and_per_document_diversity(client):
    api, _ = client
    for index in range(12):
        api.post(
            f"{ROOT}/state/requirements",
            json={"title": f"Bounded scope {index}", "description": "scope " * 1000},
        )
    api.post(f"{ROOT}/documents", params={"filename": "scope.txt"}, content=b"scope " * 1000)
    data = search(api, "scope").json()
    assert len(data["matches"]) == 8
    assert all(len(x["excerpt"]) <= 600 for x in data["matches"])
    assert len([x for x in data["matches"] if x["kind"] == "document"]) <= 2
    assert len(search(api, "scope", limit=2).json()["matches"]) == 2


@pytest.mark.integration
def test_empty_query_results_and_literal_metacharacters_do_not_expand_scope(client):
    api, _ = client
    for query in ["unfindableuniquephrase", "%_\\"]:
        assert search(api, query).json()["matches"] == []


@pytest.mark.integration
def test_missing_and_hidden_projects_fail_before_provider_call(client, db_session):
    api, provider = client
    hidden = Project(name="Hidden")
    db_session.add(hidden)
    db_session.flush()
    replies = [
        api.get(f"/api/v1/projects/{id}/context/search", params={"query": "secret"})
        for id in [hidden.id, uuid4()]
    ]
    assert (
        all(x.status_code == 404 for x in replies)
        and replies[0].json() == replies[1].json()
        and provider.calls == 0
    )


@pytest.mark.integration
def test_baseline_is_read_after_external_query_embedding_not_stale(client, db_session):
    api, provider = client
    provider.available = True
    doc = api.post(
        f"{ROOT}/documents", params={"filename": "x.txt"}, content=b"credentials evidence"
    ).json()
    api.post(f"{ROOT}/documents/{doc['id']}/index")
    record = api.post(
        f"{ROOT}/state/decisions",
        json={"title": "Current unique choice", "decisionStatus": "CONFIRMED"},
    ).json()

    def change():
        assert (
            api.put(
                f"{ROOT}/state/decisions/{record['id']}",
                json={
                    "expectedVersion": 1,
                    "values": {
                        "title": "Current unique choice",
                        "decisionStatus": "REVIEW_REQUIRED",
                    },
                },
            ).status_code
            == 200
        )

    provider.before_query = change
    data = search(api, "Current unique choice").json()
    assert not any(x["id"] == record["id"] for x in data["matches"])
