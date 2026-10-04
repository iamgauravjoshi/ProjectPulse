"""Provider boundary: normalize evidence; never persist or interpret project state.

Future VexaTranscriptAdapter / TeamsTranscriptAdapter implementations can use their
own source type and return the same validated ParsedTranscript. They are not
implemented or selectable by the upload endpoint. Network/auth/retry behavior belongs
to those integrations, not to the file adapter or canonical state services.
"""

from dataclasses import dataclass
from typing import Protocol, TypeVar

from app.domain.transcripts import ParsedTranscript, parse_transcript

Source = TypeVar("Source", contravariant=True)


class TranscriptAdapter(Protocol[Source]):
    def parse(self, source: Source) -> ParsedTranscript:
        """Return bounded, validated, ordered evidence or a sanitized StateError."""
        ...


@dataclass(frozen=True)
class FileTranscriptSource:
    filename: str
    raw_bytes: bytes


class FileTranscriptAdapter:
    """Deterministic UTF-8 file parsing, with no database, network or AI calls."""

    def parse(self, source: FileTranscriptSource) -> ParsedTranscript:
        return parse_transcript(source.filename, source.raw_bytes)


def get_file_transcript_adapter() -> TranscriptAdapter[FileTranscriptSource]:
    # Server-selected dependency: a browser cannot select a conferencing provider.
    return FileTranscriptAdapter()
