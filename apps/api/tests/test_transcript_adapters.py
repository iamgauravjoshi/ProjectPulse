import pytest
from test_meetings import ROOT
from test_meetings import client as meeting_client

from app.domain.manual_state import StateError
from app.services.transcript_adapters import (
    FileTranscriptAdapter,
    FileTranscriptSource,
    TranscriptAdapter,
    get_file_transcript_adapter,
)

client = meeting_client


@pytest.mark.parametrize(
    "filename, raw",
    [
        ("x.txt", b" | Sarah | Evidence"),
        ("x.json", b'[{"speaker":"Sarah","text":"Evidence"}]'),
        ("x.vtt", b"WEBVTT\n\n00:01.000 --> 00:02.000\n<v Sarah>Evidence</v>"),
    ],
)
def test_file_adapter_contract_is_provider_independent_and_preserves_unknowns(filename, raw):
    adapter: TranscriptAdapter[FileTranscriptSource] = FileTranscriptAdapter()
    source = FileTranscriptSource(filename, raw)
    result = adapter.parse(source)
    assert result.utterances[0].text == "Evidence"
    assert result.utterances[0].speaker_key == "name:Sarah"
    assert result.utterances[0].confidence is None
    assert source.raw_bytes == raw


def test_file_adapter_errors_remain_safe():
    with pytest.raises(StateError) as error:
        get_file_transcript_adapter().parse(FileTranscriptSource("private.txt", b"private content"))
    assert "private content" not in error.value.message


@pytest.mark.integration
def test_upload_calls_injected_adapter_with_source_then_persists_evidence(client):
    from app.main import app

    sources = []

    class RecordingAdapter:
        def parse(self, source):
            sources.append(source)
            return FileTranscriptAdapter().parse(source)

    app.dependency_overrides[get_file_transcript_adapter] = lambda: RecordingAdapter()
    try:
        meeting = client.post(ROOT, json={"title": "Adapter boundary"}).json()
        raw = b" | Sarah | Evidence via adapter"
        response = client.post(
            f"{ROOT}/{meeting['id']}/transcript", params={"filename": "x.txt"}, content=raw
        )
        assert response.status_code == 201, response.text
        assert len(sources) == 1 and sources[0] == FileTranscriptSource("x.txt", raw)
        assert response.json()["utterances"][0]["text"] == "Evidence via adapter"
    finally:
        app.dependency_overrides.pop(get_file_transcript_adapter, None)
