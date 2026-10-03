"""Gemini REST embeddings: fixed destination, bounded batches, no secret logging."""

import json
import math
import time
from collections.abc import Sequence
from typing import Any, Protocol
from urllib.request import Request, urlopen

from app.config import get_settings
from app.domain.manual_state import StateError

MODEL = "gemini-embedding-001"
DIMENSIONS = 768
BATCH_SIZE = 16


class EmbeddingProvider(Protocol):
    model: str
    available: bool

    def embed(self, texts: Sequence[str], *, query: bool = False) -> list[list[float]]: ...


def normalized_vector(values: Any) -> list[float]:
    if (
        not isinstance(values, list)
        or len(values) != DIMENSIONS
        or any(
            isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x)
            for x in values
        )
    ):
        raise StateError("EMBEDDING_INVALID", "Embedding provider returned invalid vectors.", 503)
    norm = math.sqrt(sum(float(x) * float(x) for x in values))
    if not math.isfinite(norm) or norm == 0:
        raise StateError("EMBEDDING_INVALID", "Embedding provider returned invalid vectors.", 503)
    return [float(x) / norm for x in values]


class GeminiEmbeddings:
    model = MODEL

    def __init__(self) -> None:
        secret = get_settings().gemini_api_key
        self._key = secret.get_secret_value().strip() if secret else ""
        self.available = bool(self._key)

    def embed(self, texts: Sequence[str], *, query: bool = False) -> list[list[float]]:
        if not self.available:
            raise StateError(
                "EMBEDDINGS_UNAVAILABLE",
                "Gemini embeddings are unavailable. Configure GEMINI_API_KEY on the server.",
                503,
            )
        if not texts or len(texts) > 256 or any(not x.strip() or len(x) > 1000 for x in texts):
            raise StateError("EMBEDDING_INPUT", "Embedding input exceeds the bounded text budget.")
        vectors: list[list[float]] = []
        deadline = time.monotonic() + 30
        for start in range(0, len(texts), BATCH_SIZE):
            if time.monotonic() >= deadline:
                raise StateError(
                    "EMBEDDING_PROVIDER_FAILED", "Gemini indexing timed out. Retry explicitly.", 503
                )
            batch = texts[start : start + BATCH_SIZE]
            payload = {
                "requests": [
                    {
                        "model": f"models/{MODEL}",
                        "content": {"parts": [{"text": text}]},
                        "embedContentConfig": {
                            "taskType": "RETRIEVAL_QUERY" if query else "RETRIEVAL_DOCUMENT",
                            "outputDimensionality": DIMENSIONS,
                        },
                    }
                    for text in batch
                ]
            }
            request = Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:batchEmbedContents",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "x-goog-api-key": self._key},
                method="POST",
            )
            try:
                with urlopen(
                    request, timeout=max(0.1, min(8, deadline - time.monotonic()))
                ) as response:
                    raw = response.read(4 * 1024 * 1024 + 1)
                if len(raw) > 4 * 1024 * 1024:
                    raise ValueError("Response budget")
                data = json.loads(raw)
                embeddings = data["embeddings"]
                if not isinstance(embeddings, list) or len(embeddings) != len(batch):
                    raise ValueError("Response count")
                vectors.extend(normalized_vector(x["values"]) for x in embeddings)
            except StateError:
                raise
            except Exception:
                raise StateError(
                    "EMBEDDING_PROVIDER_FAILED",
                    "Gemini request failed. Check server configuration or quota and retry.",
                    503,
                ) from None
        return vectors


def get_embedding_provider() -> EmbeddingProvider:
    return GeminiEmbeddings()
