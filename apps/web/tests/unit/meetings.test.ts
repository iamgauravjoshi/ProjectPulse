import { afterEach, describe, expect, it, vi } from "vitest";
import {
  elapsedTime,
  meetingDetailSchema,
  meetingHref,
  loadMeeting,
  loadMeetings,
  validateTranscriptFile,
} from "../../src/features/meetings/contracts";
import { proxyMeetings } from "../../src/lib/meetings-proxy";
import { fixture } from "../fixtures/workspace";
const projectId = fixture.project.id;
const meetingId = "00c377c0-e93e-490a-a9b7-0fd5d0d7c417";
const speakerId = "9d00b9a2-cc0f-40bf-880b-3fe8d70d1465";
const utteranceId = "6b5a3f05-37a7-493e-82e0-302ec3fbf281";
const detail = {
  id: meetingId,
  projectId,
  title: "Meeting",
  startedAt: null,
  createdAt: "2026-10-04T01:00:00Z",
  createdBy: fixture.members[0].id,
  hasTranscript: true,
  transcriptFilename: "x.txt",
  transcriptFormat: "txt",
  participants: [
    {
      id: speakerId,
      meetingId,
      displayName: "Sarah",
      speakerKey: "name:Sarah",
      userId: null,
    },
  ],
  utterances: [
    {
      id: utteranceId,
      meetingId,
      sequence: 0,
      speaker: "Sarah",
      speakerId,
      timestampMs: null,
      endMs: null,
      text: "Evidence",
      confidence: null,
    },
  ],
};
afterEach(() => vi.unstubAllGlobals());
describe("meeting evidence contracts", () => {
  it("preserves unknown time and millisecond precision", () => {
    expect(elapsedTime(null)).toBe("Time unknown");
    expect(elapsedTime(70125)).toBe("00:01:10.125");
    expect(elapsedTime(604800000)).toBe("168:00:00");
  });
  it("links directly to a stable project meeting utterance", () =>
    expect(meetingHref(projectId, meetingId, utteranceId)).toContain(
      `&utterance=${utteranceId}#utterance-${utteranceId}`,
    ));
  it("rejects cross-meeting, duplicate, out-of-order and unknown speaker evidence", () => {
    expect(meetingDetailSchema.safeParse(detail).success).toBe(true);
    for (const change of [
      { meetingId: projectId },
      { sequence: 1 },
      { speakerId: projectId },
      { endMs: 10 },
      { confidence: NaN },
      { text: "x".repeat(6001) },
    ])
      expect(
        meetingDetailSchema.safeParse({
          ...detail,
          utterances: [{ ...detail.utterances[0], ...change }],
        }).success,
      ).toBe(false);
    expect(
      meetingDetailSchema.safeParse({
        ...detail,
        utterances: [
          detail.utterances[0],
          { ...detail.utterances[0], sequence: 1 },
        ],
      }).success,
    ).toBe(false);
  });
  it("enforces supported nonempty files and byte limits before upload", () => {
    for (const file of [
      { name: "x.txt", size: 0 },
      { name: "x.txt", size: 2097153 },
      { name: "x.exe", size: 1 },
    ])
      expect(validateTranscriptFile(file)).toBeTruthy();
    expect(
      validateTranscriptFile({ name: "x.JSON", size: 2097152 }),
    ).toBeNull();
  });
  it("rejects other project responses instead of rendering evidence", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json({ ...detail, projectId: meetingId })),
    );
    await expect(
      loadMeeting(projectId, meetingId, new AbortController().signal),
    ).rejects.toThrow();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json([{ ...detail, projectId: meetingId }])),
    );
    await expect(
      loadMeetings(projectId, new AbortController().signal),
    ).rejects.toThrow();
  });
});
it("meeting proxy rejects bad IDs, cross-origin writes and oversized streams before contacting API", async () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  const request = (headers?: HeadersInit, body?: Uint8Array) =>
    new Request("http://127.0.0.1:3010/api?filename=x.txt", {
      method: "POST",
      headers,
      body: body as BodyInit | undefined,
    });
  expect((await proxyMeetings(request(), { projectId: "bad" })).status).toBe(
    404,
  );
  expect(
    (
      await proxyMeetings(
        request({ host: "127.0.0.1:3010", origin: "https://outside.test" }),
        { projectId },
      )
    ).status,
  ).toBe(403);
  expect(
    (
      await proxyMeetings(
        request(undefined, new Uint8Array(2097153)),
        { projectId, meetingId },
        "transcript",
      )
    ).status,
  ).toBe(413);
  expect(fetch).not.toHaveBeenCalled();
});
