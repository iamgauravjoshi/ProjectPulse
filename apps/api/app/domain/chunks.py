from typing import Any

CHUNK_SIZE = 1000
OVERLAP = 120
MAX_CHUNKS = 256


def chunk_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for segment_index, segment in enumerate(segments):
        text = str(segment["text"])
        for start in range(0, len(text), CHUNK_SIZE - OVERLAP):
            end = min(start + CHUNK_SIZE, len(text))
            raw = text[start:end]
            if raw.strip():
                chunks.append(
                    {
                        "chunk_index": len(chunks),
                        "page": segment["page"],
                        "section": segment["section"],
                        "raw_text": raw,
                        "metadata_json": {
                            "segmentIndex": segment_index,
                            "start": start,
                            "end": end,
                            "chunker": "characters-1000-overlap-120-v1",
                        },
                    }
                )
            if len(chunks) > MAX_CHUNKS:
                raise ValueError("Document exceeds chunk budget")
            if end == len(text):
                break
    return chunks
