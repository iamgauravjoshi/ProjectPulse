import json

import pytest
from sqlalchemy import func, select
from test_meetings import ROOT
from test_meetings import client as meeting_client

from app.db.models import AuditEvent, MeetingParticipant, Utterance
from app.domain.manual_state import StateError
from app.domain.transcripts import MAX_TRANSCRIPT_BYTES, parse_transcript
from app.repositories.audit import AuditRepository
from app.services.demo_seed import DEMO_PROJECT_ID

client = meeting_client


@pytest.mark.parametrize("speakers", [2, 10])
def test_multiple_speakers_stable_order_and_missing_values(speakers):
    rows = [
        {
            "speaker": f"Person {i}",
            "speakerId": str(i),
            "timestamp": "00:01:10.125",
            "text": "Evidence",
            "confidence": 0.7,
        }
        for i in range(speakers)
    ]
    rows += [
        {"speaker": "Person 0", "speakerId": "different-person", "text": "Same name"},
        {"text": "Unknown speaker"},
    ]
    parsed = parse_transcript("meeting.json", json.dumps({"utterances": rows}).encode())
    assert len(parsed.utterances) == speakers + 2
    assert parsed.utterances[0].timestamp_ms == 70125
    assert parsed.utterances[0].confidence == 0.7
    assert parsed.utterances[0].speaker_key != parsed.utterances[-2].speaker_key
    assert (
        parsed.utterances[-1].speaker == "Unknown speaker"
        and parsed.utterances[-1].speaker_key is None
    )
    assert parsed.utterances[-2].timestamp_ms is None


def test_plain_text_blank_time_speaker_and_embedded_pipe():
    parsed = parse_transcript(
        r"C:\uploads\meeting.TXT", b"00:01:10 | Sarah | Need SSO\n | John | a | b\n | | Unknown\n"
    )
    assert parsed.filename == "meeting.TXT"
    assert [x.timestamp_ms for x in parsed.utterances] == [70000, None, None]
    assert parsed.utterances[1].text == "a | b"
    assert parsed.utterances[2].speaker_key is None


def test_vtt_voice_timestamp_entities_and_multiline():
    raw = (
        b"WEBVTT\n\nNOTE skipped\nprivate notes\n\ncue1\n"
        b"00:01.125 --> 00:02.500 align:start\n<v Sarah><b>SSO</b> &amp; API\n"
        b"next line</v>\n\n00:03.000 --> 00:04.000\nUnknown voice\n"
    )
    parsed = parse_transcript("meeting.vtt", raw)
    assert len(parsed.utterances) == 2
    first = parsed.utterances[0]
    assert (first.timestamp_ms, first.end_ms, first.speaker, first.text) == (
        1125,
        2500,
        "Sarah",
        "SSO & API\nnext line",
    )
    assert parsed.utterances[1].speaker_key is None


@pytest.mark.parametrize(
    "name,raw",
    [
        ("x.exe", b"data"),
        ("x.txt", b""),
        ("x.txt", b" \n"),
        ("x.txt", b"unstructured"),
        ("x.txt", b"00:99:10 | Sarah | bad"),
        ("x.txt", b"169:00:00 | Sarah | bad"),
        ("x.txt", b" | | "),
        ("x.txt", b"\xff"),
        ("x.txt", b" | Sarah | \x00"),
        ("x.txt", b"x" * (MAX_TRANSCRIPT_BYTES + 1)),
        ("x.json", b"{}"),
        ("x.json", b"["),
        ("x.json", b'[{"text":"x","text":"y"}]'),
        ("x.json", b'[{"text":"x","confidence":NaN}]'),
        ("x.json", b'[{"text":"x","confidence":true}]'),
        ("x.json", b'[{"text":"x","timestamp":10}]'),
        ("x.json", b'[{"text":"x","confidence":1.1}]'),
        ("x.json", b'[{"text":"x","speakerId":42}]'),
        ("x.json", b'[{"text":"x","sequence":0}]'),
        ("x.json", b'[{"text":"x","speaker":""}]'),
        ("x.json", b'[{"text":"x","endTimestamp":"00:01:00"}]'),
        ("x.json", b'[{"text":"x","timestamp":"00:02:00","endTimestamp":"00:01:00"}]'),
        (
            "x.json",
            b'[{"text":"x","speakerId":"a","speaker":"A"},{"text":"x","speakerId":"a","speaker":"B"}]',
        ),
        ("x.json", b'[{"text":"\\ud800"}]'),
        ("x.vtt", b"not vtt"),
        ("x.vtt", b"WEBVTT\n\n00:01 --> nope\nx"),
        ("x.vtt", b"WEBVTT\n\n00:01.000 --> 00:00.000\nx"),
        ("x.vtt", b"WEBVTT\n\n00:01.000 --> 00:02.000\n<v A>x</v><v B>y</v>"),
    ],
)
def test_malformed_transcripts_rejected(name, raw):
    with pytest.raises(StateError):
        parse_transcript(name, raw)


@pytest.mark.parametrize(
    "rows",
    [
        [{"text": "x"}] * 10001,
        [{"text": "x" * 6001}],
        [{"text": "x" * 6000}] * 167,
        [{"text": "x", "speaker": str(i)} for i in range(101)],
    ],
)
def test_parse_budgets(rows):
    with pytest.raises(StateError):
        parse_transcript("x.json", json.dumps(rows).encode())


def test_long_transcript_keeps_all_source_order():
    rows = [{"text": f"utterance {i}", "speaker": f"speaker {i % 10}"} for i in range(10000)]
    parsed = parse_transcript("long.json", json.dumps(rows).encode())
    assert len(parsed.utterances) == 10000 and parsed.utterances[-1].text == "utterance 9999"


@pytest.mark.integration
@pytest.mark.parametrize(
    "filename,raw",
    [
        ("x.txt", b"00:01:10 | Sarah | Need SSO\n | | Unknown"),
        (
            "x.json",
            b'[{"speaker":"Sarah","speakerId":"sarah-1","text":"SSO","confidence":0.9},{"speaker":"Sarah","speakerId":"sarah-2","text":"API"}]',
        ),
        ("x.vtt", b"WEBVTT\n\n00:01.000 --> 00:02.000\n<v Sarah>SSO</v>"),
    ],
)
def test_upload_duplicate_immutable_source_and_baseline(db_session, client, filename, raw):
    before = client.get(f"/api/v1/projects/{DEMO_PROJECT_ID}/workspace").json()
    meeting = client.post(ROOT, json={"title": "Upload"}).json()
    path = f"{ROOT}/{meeting['id']}/transcript"
    r = client.post(path, params={"filename": filename}, content=raw)
    assert r.status_code == 201, r.text
    detail = r.json()
    assert detail["hasTranscript"] and not detail["duplicate"]
    assert "transcript_bytes" not in detail and detail["utterances"][0]["sequence"] == 0
    again = client.post(path, params={"filename": filename}, content=raw).json()
    assert again["duplicate"] and again["utterances"] == detail["utterances"]
    assert (
        client.post(
            path, params={"filename": "different.txt"}, content=b" | Sarah | different"
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"{ROOT}/{meeting['id']}/participants", json={"displayName": "Later", "speakerKey": "x"}
        ).status_code
        == 409
    )
    after = client.get(f"/api/v1/projects/{DEMO_PROJECT_ID}/workspace").json()
    for key in ["requirements", "decisions", "milestones", "risks", "commitments", "dependencies"]:
        assert before[key] == after[key]
    events = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_id == meeting["id"], AuditEvent.action == "TRANSCRIPT_UPLOADED"
        )
    ).all()
    assert len(events) == 1 and "text" not in events[0].payload
    assert client.delete(f"{ROOT}/{meeting['id']}").status_code == 204
    assert db_session.scalar(select(func.count()).select_from(Utterance)) == 0


@pytest.mark.integration
def test_explicit_member_mapping_and_unknown_speaker(db_session, client):
    meeting = client.post(ROOT, json={"title": "Mapping"}).json()
    path = f"{ROOT}/{meeting['id']}"
    speaker = client.post(
        path + "/participants", json={"displayName": "Member", "speakerKey": "id:member-1"}
    ).json()
    r = client.post(
        path + "/transcript",
        params={"filename": "x.json"},
        content=(
            b'[{"speakerId":"member-1","speaker":"Source name","text":"Evidence"},'
            b'{"text":"Unknown"}]'
        ),
    )
    assert r.status_code == 201
    assert len(r.json()["participants"]) == 1
    assert r.json()["utterances"][0]["speakerId"] == speaker["id"]
    assert r.json()["utterances"][0]["speaker"] == "Source name"
    assert r.json()["utterances"][1]["speakerId"] is None


@pytest.mark.integration
def test_failed_parse_and_audit_do_not_leave_partial_evidence(db_session, client, monkeypatch):
    meeting = client.post(ROOT, json={"title": "Atomic"}).json()
    path = f"{ROOT}/{meeting['id']}"
    for name, raw in [("x.txt", b"malformed"), ("x.txt", b"x" * (MAX_TRANSCRIPT_BYTES + 1))]:
        assert client.post(
            path + "/transcript", params={"filename": name}, content=raw
        ).status_code in [422, 413]
    assert not client.get(path).json()["hasTranscript"]

    def fail(*args, **kwargs):
        raise RuntimeError("audit failure")

    monkeypatch.setattr(AuditRepository, "append", fail)
    with pytest.raises(RuntimeError):
        client.post(
            path + "/transcript", params={"filename": "x.txt"}, content=b" | Sarah | evidence"
        )
    assert not client.get(path).json()["hasTranscript"]
    assert db_session.scalar(select(func.count()).select_from(Utterance)) == 0
    assert db_session.scalar(select(func.count()).select_from(MeetingParticipant)) == 0


@pytest.mark.integration
def test_upload_missing_and_other_meeting_rejected_before_parse(db_session, client):
    from uuid import uuid4

    from app.db.models import Project, ProjectMember
    from app.services.project_access import LOCAL_DEMO_ACTOR_ID

    meeting = client.post(ROOT, json={"title": "Scoped source"}).json()
    other = Project(name="Other")
    db_session.add(other)
    db_session.flush()
    for project, target in [(other.id, meeting["id"]), (DEMO_PROJECT_ID, uuid4())]:
        result = client.post(
            f"/api/v1/projects/{project}/meetings/{target}/transcript",
            params={"filename": "x.txt"},
            content=b"malformed",
        )
        assert result.status_code == 404
    db_session.add(ProjectMember(project_id=other.id, user_id=LOCAL_DEMO_ACTOR_ID, role="QA"))
    db_session.flush()
    assert (
        client.post(
            f"/api/v1/projects/{other.id}/meetings/{meeting['id']}/transcript",
            params={"filename": "x.txt"},
            content=b" | Sarah | evidence",
        ).status_code
        == 404
    )


@pytest.mark.integration
def test_combined_speaker_budget_and_control_characters(client):
    meeting = client.post(ROOT, json={"title": "Speaker budget"}).json()
    path = f"{ROOT}/{meeting['id']}"
    assert client.post(ROOT, json={"title": "bad\u0000"}).status_code == 422
    assert (
        client.post(
            path + "/participants", json={"displayName": "bad\u0000", "speakerKey": "x"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            path + "/participants", json={"displayName": "Attendee", "speakerKey": "id:registered"}
        ).status_code
        == 201
    )
    raw = json.dumps(
        [{"speakerId": str(i), "speaker": "Sarah", "text": "Evidence"} for i in range(100)]
    ).encode()
    assert (
        client.post(path + "/transcript", params={"filename": "x.json"}, content=raw).status_code
        == 422
    )
    detail = client.get(path).json()
    assert len(detail["participants"]) == 1 and not detail["hasTranscript"]
