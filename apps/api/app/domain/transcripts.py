import json
import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.domain.manual_state import StateError

MAX_TRANSCRIPT_BYTES = 2 * 1024 * 1024
MAX_UTTERANCES = 10_000
MAX_TRANSCRIPT_TEXT = 1_000_000
MAX_TIME_MS = 604_800_000


def invalid(message: str) -> StateError:
    return StateError("TRANSCRIPT_INVALID", message)


def safe_text(value: str) -> str:
    if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        raise ValueError("Control characters are not supported.")
    value.encode("utf-8")
    return value


def timestamp(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    match = re.fullmatch(r"(\d{1,3}):([0-5]\d):([0-5]\d)(?:\.(\d{1,3}))?", value.strip())
    if match is None:
        raise ValueError("Use HH:MM:SS or HH:MM:SS.mmm for elapsed time.")
    hours, minutes, seconds, fraction = match.groups()
    result = ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1000
    result += int((fraction or "0").ljust(3, "0"))
    if result > MAX_TIME_MS:
        raise ValueError("Elapsed time must be within seven days.")
    return result


class TranscriptRow(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    speaker: str | None = Field(default=None, min_length=1, max_length=120)
    speaker_id: str | None = Field(default=None, alias="speakerId", min_length=1, max_length=120)
    timestamp: str | None = Field(default=None, max_length=16)
    end_timestamp: str | None = Field(default=None, alias="endTimestamp", max_length=16)
    text: str = Field(min_length=1, max_length=6000)
    confidence: float | None = Field(default=None, ge=0, le=1, strict=True)

    @field_validator("speaker", "speaker_id", "text")
    @classmethod
    def readable(cls, value: str | None) -> str | None:
        return safe_text(value) if value is not None else None


@dataclass(frozen=True)
class ParsedUtterance:
    speaker: str
    speaker_key: str | None
    timestamp_ms: int | None
    end_ms: int | None
    text: str
    confidence: float | None


@dataclass(frozen=True)
class ParsedTranscript:
    filename: str
    format: str
    utterances: tuple[ParsedUtterance, ...]


def normalize(rows: list[Any]) -> tuple[ParsedUtterance, ...]:
    if not 1 <= len(rows) <= MAX_UTTERANCES:
        raise invalid("A transcript must contain 1–10,000 utterances.")
    result: list[ParsedUtterance] = []
    identities: dict[str, str] = {}
    total = 0
    for sequence, data in enumerate(rows):
        try:
            row = TranscriptRow.model_validate(data)
            start = timestamp(row.timestamp)
            end = timestamp(row.end_timestamp)
            if end is not None and (start is None or end < start):
                raise ValueError("End time must not precede a known start time.")
        except (ValidationError, ValueError, UnicodeError):
            raise invalid(
                f"Utterance {sequence + 1} is invalid. Check speaker, time, text and confidence."
            ) from None
        label = row.speaker or "Unknown speaker"
        key = (
            "id:" + row.speaker_id
            if row.speaker_id
            else "name:" + row.speaker
            if row.speaker
            else None
        )
        if key:
            if key in identities and identities[key] != label:
                raise invalid(f"Utterance {sequence + 1} uses a speaker ID with conflicting names.")
            identities[key] = label
        if len(identities) > 100:
            raise invalid("A transcript supports at most 100 distinct speakers.")
        total += len(row.text)
        if total > MAX_TRANSCRIPT_TEXT:
            raise invalid("Transcript text exceeds 1,000,000 characters. Split the meeting.")
        result.append(ParsedUtterance(label, key, start, end, row.text, row.confidence))
    return tuple(result)


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON fields.")
        result[key] = value
    return result


def json_rows(text: str) -> list[Any]:
    try:
        data = json.loads(text, object_pairs_hook=unique_object)
        if isinstance(data, dict) and set(data) == {"utterances"}:
            data = data["utterances"]
        if not isinstance(data, list):
            raise ValueError("Expected an utterance array.")
        return data
    except (ValueError, RecursionError):
        raise invalid(
            "Use a JSON utterance array or an object containing only utterances."
        ) from None


def text_rows(text: str) -> list[Any]:
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split("|", 2)
        if len(parts) != 3:
            raise invalid(
                f"Line {number}: use time | speaker | text; time or speaker may be blank."
            )
        time, speaker, content = (part.strip() for part in parts)
        rows.append({"timestamp": time or None, "speaker": speaker or None, "text": content})
        if len(rows) > MAX_UTTERANCES:
            raise invalid("A transcript supports at most 10,000 utterances.")
    return rows


class CueText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def vtt_rows(text: str) -> list[Any]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n[ \t]*\n", text.strip())
    if not blocks or not re.fullmatch(r"WEBVTT(?:[ \t].*)?", blocks[0].splitlines()[0]):
        raise invalid("VTT must start with a WEBVTT header.")
    rows = []
    for block in blocks[1:]:
        lines = block.splitlines()
        if re.match(r"^(NOTE(?:[ \t]|$)|STYLE$|REGION$)", lines[0]):
            continue
        if "-->" not in lines[0]:
            lines = lines[1:]
        if len(lines) < 2:
            raise invalid("Each VTT cue needs timing and readable text.")
        match = re.fullmatch(r"(\S+)\s+-->\s+(\S+)(?:[ \t]+.*)?", lines[0])
        if match is None:
            raise invalid("A VTT cue has invalid timing.")
        start, end = match.groups()
        # WebVTT also accepts MM:SS.mmm; normalize that to the shared elapsed-time format.
        if start.count(":") == 1:
            start = "00:" + start
        if end.count(":") == 1:
            end = "00:" + end
        payload = "\n".join(lines[1:])
        voices = re.findall(r"<v(?:[.][^ >]+)*[ \t]+([^>]+)>", payload)
        if len(voices) > 1:
            raise invalid("Use one voice per VTT cue.")
        parser = CueText()
        parser.feed(re.sub(r"<\d{1,3}:\d{2}(?::\d{2})?\.\d{3}>", "", payload))
        rows.append(
            {
                "timestamp": start,
                "endTimestamp": end,
                "speaker": unescape(voices[0]).strip() if voices else None,
                "text": "".join(parser.parts).strip(),
            }
        )
        if len(rows) > MAX_UTTERANCES:
            raise invalid("A transcript supports at most 10,000 utterances.")
    return rows


def parse_transcript(filename: str, raw: bytes) -> ParsedTranscript:
    name = PurePosixPath(filename.replace("\\", "/")).name.strip()
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if not name or len(name) > 240 or extension not in {"txt", "json", "vtt"}:
        raise invalid("Choose a TXT, JSON or VTT transcript with a filename up to 240 characters.")
    if not raw or len(raw) > MAX_TRANSCRIPT_BYTES:
        raise StateError(
            "TRANSCRIPT_SIZE",
            "Transcripts must be nonempty and no larger than 2 MiB.",
            413 if raw else 422,
        )
    try:
        safe_text(name)
        text = safe_text(raw.decode("utf-8-sig"))
        rows = {"txt": text_rows, "json": json_rows, "vtt": vtt_rows}[extension](text)
        return ParsedTranscript(name, extension, normalize(rows))
    except (UnicodeError, ValueError, RecursionError):
        raise invalid(
            "Transcript must be readable UTF-8 text without control characters."
        ) from None
