"""Opt-in synthetic live probe. Never prints credentials, vectors or document content."""

import os

from app.domain.manual_state import StateError
from app.services.embeddings import DIMENSIONS, MODEL, GeminiEmbeddings


def main() -> int:
    provider = GeminiEmbeddings()
    source = "process environment" if "GEMINI_API_KEY" in os.environ else "root .env"
    print(f"Model: {MODEL}; expected dimensions: {DIMENSIONS}")
    print(f"Key configured: {'yes' if provider.available else 'no'}; settings source: {source}")
    if not provider.available:
        print(
            "Set GEMINI_API_KEY in the root .env or backend environment, then restart the backend."
        )
        return 1
    try:
        for query, task in [(False, "RETRIEVAL_DOCUMENT"), (True, "RETRIEVAL_QUERY")]:
            vectors = provider.embed(
                ["ProjectPulse synthetic embedding connectivity check."], query=query
            )
            print(f"{task}: OK; received {len(vectors[0])} normalized dimensions")
    except StateError as error:
        print(f"FAILED [{error.code}]: {error.message}")
        return 1
    print(
        "Gemini connectivity and vector format passed. Verify document indexing and citations next."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
