import { afterEach, describe, expect, it, vi } from "vitest";
import {
  relevanceSchema,
  verifyRelevance,
  loadRelevance,
  analyzeRelevance,
} from "../../src/features/meetings/relevance";
import { proxyMeetings } from "../../src/lib/meetings-proxy";
import { fixture } from "../fixtures/workspace";
const projectId = fixture.project.id;
const meetingId = "00c377c0-e93e-490a-a9b7-0fd5d0d7c417";
const utteranceId = "6b5a3f05-37a7-493e-82e0-302ec3fbf281";
const source = {
  id: utteranceId,
  meetingId,
  sequence: 0,
  speaker: "Sarah",
  speakerId: null,
  timestampMs: null,
  endMs: null,
  text: "Need SSO.",
  confidence: null,
};
const meeting = {
  id: meetingId,
  projectId,
  title: "Evidence",
  startedAt: null,
  createdAt: "2026-10-05T01:00:00Z",
  createdBy: fixture.members[0].id,
  hasTranscript: true,
  transcriptFilename: "meeting.json",
  transcriptFormat: "json" as const,
  participants: [],
  utterances: [source],
};
const snapshot = {
  projectId,
  meetingId,
  stale: false,
  analysis: {
    id: meetingId,
    model: "gemini-2.5-flash",
    classifierVersion: "v1",
    createdAt: "2026-10-05T01:00:00Z",
    contextComplete: true,
    lastError: null,
    apiCalls: 0,
    inputTokens: 0,
    outputTokens: 0,
    usageReportedCalls: 0,
    latencyMs: 0,
    processing: false,
  },
  counts: {
    total: 1,
    analyzed: 1,
    relevant: 1,
    ignored: 0,
    uncertain: 0,
    pending: 0,
  },
  ignoredPercent: 0,
  page: 1,
  pageSize: 100,
  filteredCount: 1,
  items: [
    {
      utteranceId,
      sequence: 0,
      speaker: "Sarah",
      text: "Need SSO.",
      outcome: "RELEVANT",
      relevant: true,
      confidence: 0.9,
      reason: "Project scope.",
      relatedEntityTypes: ["requirement"],
      method: "CONTEXT_RULE",
    },
  ],
};
afterEach(() => vi.unstubAllGlobals());
describe("relevance evidence and coverage", () => {
  it("validates exact counts and citation attribution", () =>
    expect(verifyRelevance(snapshot, meeting).counts.relevant).toBe(1));
  it("rejects fabricated coverage and source content", () => {
    for (const change of [
      { counts: { ...snapshot.counts, pending: 1 } },
      { ignoredPercent: 63 },
      { filteredCount: 0 },
      { analysis: null },
      { items: [{ ...snapshot.items[0], confidence: 0.5 }] },
      { items: [{ ...snapshot.items[0], reason: "" }] },
    ])
      expect(
        relevanceSchema.safeParse({ ...snapshot, ...change }).success,
      ).toBe(false);
    for (const change of [
      { projectId: meetingId },
      { meetingId: projectId },
      { items: [{ ...snapshot.items[0], utteranceId: projectId }] },
      { items: [{ ...snapshot.items[0], text: "Fabricated" }] },
    ])
      expect(() =>
        verifyRelevance({ ...snapshot, ...change }, meeting),
      ).toThrow();
  });
  it("retains low-confidence interpretation without counting it as ignored", () => {
    const uncertain = {
      ...snapshot,
      counts: { ...snapshot.counts, relevant: 0, uncertain: 1 },
      items: [{ ...snapshot.items[0], confidence: 0.5, outcome: "UNCERTAIN" }],
    };
    expect(relevanceSchema.parse(uncertain).counts.ignored).toBe(0);
    expect(
      relevanceSchema.safeParse({
        ...uncertain,
        items: [{ ...uncertain.items[0], outcome: "IGNORED" }],
      }).success,
    ).toBe(false);
  });
  it("loads filtered pages and analyzes only on explicit POST", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>(async () =>
      Response.json(snapshot),
    );
    vi.stubGlobal("fetch", fetch);
    await loadRelevance(meeting, new AbortController().signal, 1, "ALL");
    expect(fetch.mock.calls[0][0]).toContain("?page=1&outcome=ALL");
    await analyzeRelevance(meeting);
    expect(fetch.mock.calls[1][1]).toMatchObject({ method: "POST" });
  });
});
it("relevance proxy constrains context, filters and origin before API access", async () => {
  const fetch = vi.fn<typeof globalThis.fetch>(async () =>
    Response.json(snapshot),
  );
  vi.stubGlobal("fetch", fetch);
  const url =
    "http://127.0.0.1:3010/api?outcome=IGNORED&page=2&model=untrusted";
  const params = { projectId, meetingId };
  expect(
    (await proxyMeetings(new Request(url), params, "relevance")).status,
  ).toBe(200);
  expect(fetch.mock.calls[0][0]).toContain("/relevance?page=2&outcome=IGNORED");
  expect(fetch.mock.calls[0][0]).not.toContain("untrusted");
  expect(
    (
      await proxyMeetings(
        new Request(url.replace("page=2", "page=101")),
        params,
        "relevance",
      )
    ).status,
  ).toBe(422);
  expect(
    (
      await proxyMeetings(
        new Request(url, {
          method: "POST",
          headers: { host: "127.0.0.1:3010", origin: "https://outside.test" },
        }),
        params,
        "relevance",
      )
    ).status,
  ).toBe(403);
  expect(
    (
      await proxyMeetings(
        new Request(url, { method: "POST", body: '{"context":"spoof"}' }),
        params,
        "relevance",
      )
    ).status,
  ).toBe(413);
  expect(fetch).toHaveBeenCalledTimes(1);
});
