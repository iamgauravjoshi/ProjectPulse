import { afterEach, describe, expect, it, vi } from "vitest";
import {
  eventsSchema,
  verifyEvents,
  loadEvents,
  extractEvents,
} from "../../src/features/meetings/events";
import { proxyMeetings } from "../../src/lib/meetings-proxy";
import { fixture } from "../fixtures/workspace";
const projectId = fixture.project.id,
  meetingId = "00c377c0-e93e-490a-a9b7-0fd5d0d7c417",
  sourceId = "6b5a3f05-37a7-493e-82e0-302ec3fbf281";
const source = {
  id: sourceId,
  meetingId,
  sequence: 0,
  speaker: "Sarah",
  speakerId: null,
  timestampMs: null,
  endMs: null,
  text: "John will review SSO tomorrow.",
  confidence: null,
};
const meeting = {
  id: meetingId,
  projectId,
  title: "Evidence",
  startedAt: null,
  createdAt: "2026-10-06T01:00:00Z",
  createdBy: fixture.members[0].id,
  hasTranscript: true,
  transcriptFilename: "events.json",
  transcriptFormat: "json" as const,
  participants: [],
  utterances: [source],
};
const event = {
  id: sourceId,
  projectId,
  meetingId,
  extractionId: meetingId,
  primaryUtteranceId: sourceId,
  sequence: 0,
  speaker: "Sarah",
  saidByUserId: null,
  kind: "COMMITMENT",
  statement: "STATEMENT",
  status: "CANDIDATE",
  title: "Review SSO",
  description: "Interpreted commitment.",
  confidence: 0.9,
  ownerMention: "John",
  dueDateText: "tomorrow",
  needsReview: false,
  evidence: [
    {
      utteranceId: sourceId,
      sequence: 0,
      speaker: "Sarah",
      speakerId: null,
      timestampMs: null,
      quote: source.text,
    },
  ],
};
const snapshot = {
  projectId,
  meetingId,
  prerequisite: null,
  currentRelevanceId: meetingId,
  stale: false,
  relevance: { total: 1, relevant: 1, ignored: 0, uncertain: 0, pending: 0 },
  counts: {
    eligible: 1,
    processed: 1,
    pending: 0,
    candidates: 1,
    noEvent: 0,
    lowConfidence: 0,
  },
  extraction: {
    id: meetingId,
    relevanceAnalysisId: meetingId,
    model: "synthetic-test",
    extractorVersion: "events-v1",
    createdAt: "2026-10-06T01:00:00Z",
    contextComplete: true,
    lastError: null,
    apiCalls: 1,
    inputTokens: 30,
    outputTokens: 10,
    usageReportedCalls: 1,
    latencyMs: 1,
    processing: false,
  },
  page: 1,
  pageSize: 100,
  filteredCount: 1,
  items: [event],
};
afterEach(() => vi.unstubAllGlobals());
describe("candidate coverage and evidence", () => {
  it("keeps speaker separate from a literal owner and date", () => {
    const r = verifyEvents(snapshot, meeting);
    expect(r.items[0].speaker).toBe("Sarah");
    expect(r.items[0].ownerMention).toBe("John");
    expect(r.items[0].dueDateText).toBe("tomorrow");
  });
  it.each(["PROPOSAL", "NEGATED", "QUESTION", "STATEMENT"])(
    "keeps %s unconfirmed",
    (statement) =>
      expect(
        verifyEvents({ ...snapshot, items: [{ ...event, statement }] }, meeting)
          .items[0].status,
      ).toBe("CANDIDATE"),
  );
  it("rejects confirmation, fabricated counts, false review flags and usage", () => {
    for (const change of [
      { items: [{ ...event, status: "CONFIRMED" }] },
      { items: [{ ...event, needsReview: true }] },
      { counts: { ...snapshot.counts, pending: 1 } },
      { counts: { ...snapshot.counts, noEvent: 1 } },
      { extraction: { ...snapshot.extraction, usageReportedCalls: 2 } },
      { items: [event, event] },
    ])
      expect(eventsSchema.safeParse({ ...snapshot, ...change }).success).toBe(
        false,
      );
  });
  it("rejects foreign scope, speaker identity, altered quotes and wrong requested filter", () => {
    for (const change of [
      { projectId: meetingId },
      { items: [{ ...event, speaker: "John" }] },
      { items: [{ ...event, ownerMention: "Sarah" }] },
      { items: [{ ...event, ownerMention: "Jo" }] },
      { items: [{ ...event, dueDateText: "2026-10-07" }] },
      { items: [{ ...event, saidByUserId: fixture.members[0].id }] },
      {
        items: [
          {
            ...event,
            evidence: [{ ...event.evidence[0], quote: "invented quote" }],
          },
        ],
      },
      {
        items: [
          { ...event, evidence: [{ ...event.evidence[0], timestampMs: 1 }] },
        ],
      },
    ])
      expect(() => verifyEvents({ ...snapshot, ...change }, meeting)).toThrow();
    expect(() => verifyEvents(snapshot, meeting, 1, "RISK")).toThrow();
    expect(() => verifyEvents(snapshot, meeting, 2)).toThrow();
  });
  it("validates emoji quote bounds using Unicode code points", () => {
    const quote = "🚀".repeat(500),
      m = { ...meeting, utterances: [{ ...source, text: quote }] };
    const r = {
      ...snapshot,
      items: [
        {
          ...event,
          ownerMention: null,
          dueDateText: null,
          evidence: [{ ...event.evidence[0], quote }],
        },
      ],
    };
    expect(verifyEvents(r, m).items[0].evidence[0].quote).toBe(quote);
    expect(
      eventsSchema.safeParse({
        ...r,
        items: [
          {
            ...r.items[0],
            evidence: [{ ...r.items[0].evidence[0], quote: quote + "🚀" }],
          },
        ],
      }).success,
    ).toBe(false);
  });
  it("accepts zero-event completion and stale historical context", () => {
    const r = verifyEvents(
      {
        ...snapshot,
        counts: { ...snapshot.counts, candidates: 0, noEvent: 1 },
        filteredCount: 0,
        items: [],
      },
      meeting,
    );
    expect(r.counts.pending).toBe(0);
    expect(
      verifyEvents(
        {
          ...snapshot,
          stale: true,
          prerequisite: "ANALYZE_RELEVANCE",
          currentRelevanceId: null,
        },
        meeting,
      ).stale,
    ).toBe(true);
  });
  it("allows the immediate neighbor but rejects another source window", () => {
    const next = {
      ...source,
      id: meetingId,
      sequence: 1,
      text: "Yes, John will do it.",
    };
    const m = { ...meeting, utterances: [source, next] };
    const r = {
      ...snapshot,
      relevance: { ...snapshot.relevance, total: 2, ignored: 1 },
      items: [
        {
          ...event,
          primaryUtteranceId: meetingId,
          sequence: 1,
          evidence: [
            event.evidence[0],
            {
              ...event.evidence[0],
              utteranceId: meetingId,
              sequence: 1,
              quote: next.text,
            },
          ],
        },
      ],
    };
    expect(verifyEvents(r, m).items[0].evidence).toHaveLength(2);
    expect(() =>
      verifyEvents(
        { ...r, items: [{ ...r.items[0], sequence: 2 }] },
        {
          ...m,
          utterances: [
            source,
            { ...source, id: projectId, sequence: 1 },
            { ...next, sequence: 2 },
          ],
        },
      ),
    ).toThrow();
  });
});
describe("bounded same-origin event API", () => {
  it("loads validated results and sends an empty explicit POST", async () => {
    const fetch = vi
      .fn()
      .mockImplementation(async () => new Response(JSON.stringify(snapshot)));
    vi.stubGlobal("fetch", fetch);
    await loadEvents(meeting, new AbortController().signal);
    await extractEvents(meeting);
    expect(fetch.mock.calls[1][1]).toEqual({ method: "POST" });
  });
  it("proxies bounded filters and rejects client context or foreign origin", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(snapshot)));
    vi.stubGlobal("fetch", fetch);
    const params = { projectId, meetingId },
      url = `http://localhost/api/events`;
    expect(
      (
        await proxyMeetings(
          new Request(url + "?page=400&kind=RISK"),
          params,
          "events",
        )
      ).status,
    ).toBe(200);
    expect(fetch.mock.calls[0][0]).toContain("/events?page=400&kind=RISK");
    for (const query of ["?page=401", "?kind=CONFIRMED", "?page=1.5"])
      expect(
        (await proxyMeetings(new Request(url + query), params, "events"))
          .status,
      ).toBe(422);
    expect(
      (
        await proxyMeetings(
          new Request(url, { method: "POST", body: "{}" }),
          params,
          "events",
        )
      ).status,
    ).toBe(413);
    expect(
      (
        await proxyMeetings(
          new Request(url, {
            method: "POST",
            headers: { Origin: "https://foreign.invalid" },
          }),
          params,
          "events",
        )
      ).status,
    ).toBe(403);
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
