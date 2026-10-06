import { afterEach, describe, expect, it, vi } from "vitest";
import {
  deltasSchema,
  verifyDeltas,
  loadDeltas,
  compareDeltas,
} from "../../src/features/meetings/deltas";
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
  text: "Move SSO to Phase 1.",
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
  transcriptFilename: "delta.json",
  transcriptFormat: "json" as const,
  participants: [],
  utterances: [source],
};
const item = {
  id: sourceId,
  candidateId: sourceId,
  projectId,
  meetingId,
  runId: meetingId,
  extractionId: meetingId,
  primaryUtteranceId: sourceId,
  kind: "REQUIREMENT_CHANGE",
  statement: "PROPOSAL",
  status: "CANDIDATE",
  title: "SSO scope",
  reason: "Scope proposal differs from baseline.",
  confidence: 0.9,
  outcome: "CHANGE",
  target: {
    id: sourceId,
    kind: "REQUIREMENT_CHANGE",
    version: 3,
    title: "SSO",
    values: { phase: 2 },
  },
  changes: [{ field: "phase", previousValue: 2, proposedText: "1" }],
  evidence: [
    {
      utteranceId: sourceId,
      sequence: 0,
      speaker: "Sarah",
      timestampMs: null,
      quote: source.text,
    },
  ],
};
const snapshot = {
  projectId,
  meetingId,
  prerequisite: null,
  currentExtractionId: meetingId,
  stale: false,
  sourcePending: 0,
  counts: {
    eligible: 1,
    processed: 1,
    pending: 0,
    same: 0,
    change: 1,
    new: 0,
    unclear: 0,
  },
  run: {
    id: meetingId,
    extractionId: meetingId,
    model: "synthetic",
    comparatorVersion: "deltas-v1",
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
  items: [item],
};
afterEach(() => vi.unstubAllGlobals());
describe("versioned comparison boundary", () => {
  it("preserves previous values, proposed wording and proposal status", () => {
    const r = verifyDeltas(snapshot, meeting);
    expect(r.items[0].target?.version).toBe(3);
    expect(r.items[0].changes[0]).toEqual({
      field: "phase",
      previousValue: 2,
      proposedText: "1",
    });
    expect(r.items[0].status).toBe("CANDIDATE");
  });
  it.each(["SAME", "NEW", "UNCLEAR"] as const)(
    "accepts %s without invented changes",
    (outcome) => {
      const counts = {
        ...snapshot.counts,
        change: 0,
        [outcome.toLowerCase()]: 1,
      };
      expect(
        verifyDeltas(
          {
            ...snapshot,
            counts,
            items: [
              {
                ...item,
                outcome,
                changes: [],
                target: outcome === "SAME" ? item.target : null,
              },
            ],
          },
          meeting,
        ).items[0].outcome,
      ).toBe(outcome);
    },
  );
  it("rejects altered versions, previous values, targets, confirmation and counts", () => {
    for (const change of [
      { items: [{ ...item, status: "CONFIRMED" }] },
      { items: [{ ...item, target: { ...item.target, version: 0 } }] },
      { items: [{ ...item, target: { ...item.target, kind: "RISK" } }] },
      {
        items: [
          { ...item, changes: [{ ...item.changes[0], previousValue: 99 }] },
        ],
      },
      { counts: { ...snapshot.counts, pending: 1 } },
      { run: { ...snapshot.run, usageReportedCalls: 2 } },
      { items: [item, item] },
    ])
      expect(deltasSchema.safeParse({ ...snapshot, ...change }).success).toBe(
        false,
      );
  });
  it("rejects foreign scope, evidence, source identity and requested filter", () => {
    for (const changes of [
      { projectId: meetingId },
      { runId: sourceId },
      { evidence: [{ ...item.evidence[0], quote: "invented" }] },
      { evidence: [{ ...item.evidence[0], speaker: "John" }] },
      { primaryUtteranceId: meetingId },
    ])
      expect(() =>
        verifyDeltas(
          { ...snapshot, items: [{ ...item, ...changes }] },
          meeting,
        ),
      ).toThrow();
    expect(() => verifyDeltas(snapshot, meeting, 1, "SAME")).toThrow();
  });
  it("requires clarification for questions, negations and low confidence", () => {
    for (const changes of [
      { statement: "QUESTION" },
      { statement: "NEGATED" },
      { confidence: 0.3 },
    ])
      expect(
        deltasSchema.safeParse({
          ...snapshot,
          items: [{ ...item, ...changes }],
        }).success,
      ).toBe(false);
  });
  it("rejects invented wording, duplicate fields and mismatched phase context", () => {
    for (const changes of [
      [{ field: "ownerId", previousValue: null, proposedText: "1" }],
      [{ field: "phase", previousValue: 2, proposedText: "3" }],
      [...item.changes, ...item.changes],
    ])
      expect(
        deltasSchema.safeParse({ ...snapshot, items: [{ ...item, changes }] })
          .success,
      ).toBe(false);
    expect(
      deltasSchema.safeParse({
        ...snapshot,
        items: [
          {
            ...item,
            evidence: [{ ...item.evidence[0], quote: "SSO has 1 issue." }],
          },
        ],
      }).success,
    ).toBe(false);
  });
  it("incomplete context cannot claim a new item", () => {
    expect(
      deltasSchema.safeParse({
        ...snapshot,
        run: { ...snapshot.run, contextComplete: false },
        counts: { ...snapshot.counts, change: 0, new: 1 },
        items: [{ ...item, outcome: "NEW", target: null, changes: [] }],
      }).success,
    ).toBe(false);
  });
  it("labels stale historical results and partial coverage honestly", () => {
    expect(
      verifyDeltas(
        {
          ...snapshot,
          stale: true,
          currentExtractionId: null,
          prerequisite: "EXTRACT_EVENTS",
          sourcePending: 2,
        },
        meeting,
      ).stale,
    ).toBe(true);
  });
  it("loads read-only results and compares through an empty-body explicit POST", async () => {
    const fetch = vi
      .fn()
      .mockImplementation(async () => Response.json(snapshot));
    vi.stubGlobal("fetch", fetch);
    await loadDeltas(meeting, new AbortController().signal);
    await compareDeltas(meeting);
    expect(fetch.mock.calls[1][1].method).toBe("POST");
    expect(fetch.mock.calls[1][1].body).toBeUndefined();
  });
  it("proxy validates scope, filter, origin and body before transport", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    const url = `http://localhost/api/workspace/projects/${projectId}/meetings/${meetingId}/deltas`;
    for (const [request, params, status] of [
      [new Request(url + "?outcome=CONFIRMED"), { projectId, meetingId }, 422],
      [new Request(url + "?page=401"), { projectId, meetingId }, 422],
      [new Request(url), { projectId: "bad", meetingId }, 404],
      [
        new Request(url, { method: "POST", body: "{}" }),
        { projectId, meetingId },
        413,
      ],
      [
        new Request(url, {
          method: "POST",
          headers: { origin: "http://foreign.test" },
        }),
        { projectId, meetingId },
        403,
      ],
    ] as const) {
      expect((await proxyMeetings(request, params, "deltas")).status).toBe(
        status,
      );
    }
    expect(fetch).not.toHaveBeenCalled();
  });
});
