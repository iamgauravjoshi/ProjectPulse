import { z } from "zod";
import { memoryRequest } from "../memory/documents";
import type { MeetingDetail } from "./contracts";
import { eventKinds } from "./events";

export const deltaOutcomes = ["SAME", "CHANGE", "NEW", "UNCLEAR"] as const;
export type DeltaFilter = "ALL" | (typeof deltaOutcomes)[number];
export const outcomeLabels = {
  SAME: "Consistent with baseline",
  CHANGE: "Possible change",
  NEW: "Potential new item",
  UNCLEAR: "Needs clarification",
};
const count = z.number().int().min(0).max(40000);
const text = (max: number) =>
  z
    .string()
    .min(1)
    .max(max * 2)
    .refine((s) => s.trim().length > 0 && Array.from(s).length <= max);
const value = z.union([z.string().max(20000), z.number().int(), z.null()]);
const fields: Record<(typeof eventKinds)[number], string[]> = {
  REQUIREMENT_CHANGE: ["title", "description", "phase"],
  MILESTONE_CHANGE: ["title", "description", "date"],
  COMMITMENT: ["title", "description", "ownerMention", "dueDateText"],
  DEPENDENCY: ["title", "description", "ownerMention"],
  OPEN_QUESTION: ["title", "description", "ownerMention"],
  DECISION: ["title", "description"],
  RISK: ["title", "description"],
};
const delta = z.object({
  id: z.uuid(),
  candidateId: z.uuid(),
  projectId: z.uuid(),
  meetingId: z.uuid(),
  runId: z.uuid(),
  extractionId: z.uuid(),
  primaryUtteranceId: z.uuid(),
  kind: z.enum(eventKinds),
  statement: z.enum(["PROPOSAL", "STATEMENT", "QUESTION", "NEGATED"]),
  title: text(240),
  outcome: z.enum(deltaOutcomes),
  status: z.literal("CANDIDATE"),
  reason: text(1600),
  confidence: z.number().min(0).max(1),
  target: z
    .object({
      id: z.uuid(),
      kind: z.enum(eventKinds),
      version: z.number().int().positive(),
      title: text(240),
      values: z.record(z.string(), value),
    })
    .nullable(),
  changes: z
    .array(
      z.object({
        field: text(40),
        previousValue: value,
        proposedText: text(500),
      }),
    )
    .max(6),
  evidence: z
    .array(
      z.object({
        utteranceId: z.uuid(),
        sequence: z.number().int().min(0).max(9999),
        speaker: text(120),
        timestampMs: z.number().int().min(0).max(604800000).nullable(),
        quote: text(500),
      }),
    )
    .min(1)
    .max(2),
});
export const deltasSchema = z
  .object({
    projectId: z.uuid(),
    meetingId: z.uuid(),
    currentExtractionId: z.uuid().nullable(),
    prerequisite: z
      .enum(["NO_TRANSCRIPT", "ANALYZE_RELEVANCE", "EXTRACT_EVENTS"])
      .nullable(),
    stale: z.boolean(),
    sourcePending: count.max(20000),
    counts: z.object({
      eligible: count,
      processed: count,
      pending: count,
      same: count,
      change: count,
      new: count,
      unclear: count,
    }),
    run: z
      .object({
        id: z.uuid(),
        extractionId: z.uuid(),
        model: text(80),
        comparatorVersion: text(40),
        createdAt: z.iso.datetime({ offset: true }),
        contextComplete: z.boolean(),
        lastError: z.string().nullable(),
        apiCalls: z.number().int().nonnegative(),
        inputTokens: z.number().int().nonnegative(),
        outputTokens: z.number().int().nonnegative(),
        usageReportedCalls: z.number().int().nonnegative(),
        latencyMs: z.number().int().nonnegative(),
        processing: z.boolean(),
      })
      .nullable(),
    page: z.number().int().min(1).max(400),
    pageSize: z.literal(100),
    filteredCount: count,
    items: z.array(delta).max(100),
  })
  .superRefine((r, ctx) => {
    const c = r.counts;
    if (
      c.eligible !== c.processed + c.pending ||
      c.processed !== c.same + c.change + c.new + c.unclear ||
      r.filteredCount > c.processed ||
      r.items.length !==
        Math.min(100, Math.max(0, r.filteredCount - (r.page - 1) * 100)) ||
      new Set(r.items.map((x) => x.id)).size !== r.items.length ||
      new Set(r.items.map((x) => x.candidateId)).size !== r.items.length ||
      (!r.run && (c.processed > 0 || r.stale)) ||
      (r.run &&
        (r.run.usageReportedCalls > r.run.apiCalls ||
          (!r.stale && r.run.extractionId !== r.currentExtractionId))) ||
      (r.prerequisite === null) !== (r.currentExtractionId !== null) ||
      r.items.some(
        (x) =>
          x.projectId !== r.projectId ||
          x.meetingId !== r.meetingId ||
          x.runId !== r.run?.id ||
          x.extractionId !== r.run?.extractionId ||
          (x.target && x.target.kind !== x.kind) ||
          ((x.outcome === "SAME" || x.outcome === "CHANGE") && !x.target) ||
          (x.outcome === "NEW" && (x.target || !r.run?.contextComplete)) ||
          (x.outcome === "CHANGE"
            ? x.changes.length === 0
            : x.changes.length !== 0) ||
          ((x.confidence < 0.65 ||
            x.statement === "QUESTION" ||
            x.statement === "NEGATED") &&
            x.outcome !== "UNCLEAR") ||
          new Set(x.changes.map((p) => p.field)).size !== x.changes.length ||
          x.changes.some(
            (p) =>
              !fields[x.kind].includes(p.field) ||
              p.previousValue !== (x.target?.values[p.field] ?? null) ||
              String(p.previousValue) === p.proposedText ||
              !x.evidence.some((e) => e.quote.includes(p.proposedText)) ||
              (["date", "dueDateText", "ownerMention"].includes(p.field) &&
                !x.evidence.some((e) =>
                  new RegExp(
                    `(?<![\\p{L}\\p{N}_])${p.proposedText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?![\\p{L}\\p{N}_])`,
                    "u",
                  ).test(e.quote),
                )) ||
              (p.field === "phase" &&
                (!/^[1-9]\d{0,3}$/.test(p.proposedText) ||
                  Number(p.proposedText) > 1000 ||
                  !x.evidence.some((e) =>
                    new RegExp(`\\bphase\\s+${p.proposedText}\\b`, "i").test(
                      e.quote,
                    ),
                  ))),
          ) ||
          !x.evidence.some((e) => e.utteranceId === x.primaryUtteranceId) ||
          new Set(x.evidence.map((e) => e.utteranceId)).size !==
            x.evidence.length,
      )
    )
      ctx.addIssue({
        code: "custom",
        message: "Invalid comparison coverage or provenance",
      });
  });
export function verifyDeltas(
  data: unknown,
  meeting: MeetingDetail,
  page = 1,
  outcome: DeltaFilter = "ALL",
) {
  const r = deltasSchema.parse(data);
  const sources = new Map(meeting.utterances.map((u) => [u.id, u]));
  if (
    r.projectId !== meeting.projectId ||
    r.meetingId !== meeting.id ||
    r.page !== page ||
    (r.prerequisite === "NO_TRANSCRIPT") !== !meeting.hasTranscript ||
    (outcome === "ALL" && r.filteredCount !== r.counts.processed) ||
    r.items.some((x) => {
      const primary = sources.get(x.primaryUtteranceId);
      return (
        !primary ||
        (outcome !== "ALL" && x.outcome !== outcome) ||
        x.evidence.some((e) => {
          const s = sources.get(e.utteranceId);
          return (
            !s ||
            s.sequence !== e.sequence ||
            s.speaker !== e.speaker ||
            s.timestampMs !== e.timestampMs ||
            !s.text.includes(e.quote) ||
            (s.id !== primary.id && s.sequence !== primary.sequence - 1)
          );
        })
      );
    })
  )
    throw new Error("Comparisons do not match this meeting's evidence.");
  return r;
}
export async function loadDeltas(
  meeting: MeetingDetail,
  signal: AbortSignal,
  page = 1,
  outcome: DeltaFilter = "ALL",
) {
  return verifyDeltas(
    await memoryRequest(
      `/api/workspace/projects/${meeting.projectId}/meetings/${meeting.id}/deltas?page=${page}&outcome=${outcome}`,
      { signal, cache: "no-store" },
    ),
    meeting,
    page,
    outcome,
  );
}
export async function compareDeltas(meeting: MeetingDetail) {
  return verifyDeltas(
    await memoryRequest(
      `/api/workspace/projects/${meeting.projectId}/meetings/${meeting.id}/deltas`,
      { method: "POST" },
    ),
    meeting,
  );
}
