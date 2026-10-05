import { z } from "zod";
import { memoryRequest } from "../memory/documents";
import type { MeetingDetail } from "./contracts";

export const relevanceOutcomes = [
  "ALL",
  "RELEVANT",
  "IGNORED",
  "UNCERTAIN",
] as const;
export type RelevanceOutcome = (typeof relevanceOutcomes)[number];
const entityTypes = [
  "requirement",
  "decision",
  "commitment",
  "risk",
  "milestone",
  "dependency",
  "open_question",
] as const;
const count = z.number().int().min(0).max(10000);
export const relevanceSchema = z
  .object({
    projectId: z.uuid(),
    meetingId: z.uuid(),
    stale: z.boolean(),
    analysis: z
      .object({
        id: z.uuid(),
        model: z.string().min(1).max(80),
        classifierVersion: z.string(),
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
    counts: z.object({
      total: count,
      analyzed: count,
      relevant: count,
      ignored: count,
      uncertain: count,
      pending: count,
    }),
    ignoredPercent: z.number().int().min(0).max(100).nullable(),
    page: z.number().int().min(1).max(100),
    pageSize: z.literal(100),
    filteredCount: count,
    items: z
      .array(
        z.object({
          utteranceId: z.uuid(),
          sequence: z.number().int().min(0).max(9999),
          speaker: z.string().min(1).max(120),
          text: z.string().min(1).max(400),
          outcome: z.enum(["RELEVANT", "IGNORED", "UNCERTAIN"]),
          relevant: z.boolean(),
          confidence: z.number().min(0).max(1),
          reason: z.string().min(1).max(500),
          relatedEntityTypes: z.array(z.enum(entityTypes)).max(7),
          method: z.enum(["RULE", "CONTEXT_RULE", "GEMINI"]),
        }),
      )
      .max(100),
  })
  .superRefine((r, ctx) => {
    const c = r.counts;
    if (
      c.analyzed !== c.relevant + c.ignored + c.uncertain ||
      c.total !== c.analyzed + c.pending ||
      r.filteredCount > c.analyzed ||
      r.items.length !==
        Math.min(100, Math.max(0, r.filteredCount - (r.page - 1) * 100)) ||
      new Set(r.items.map((x) => x.utteranceId)).size !== r.items.length ||
      (r.analysis === null &&
        (c.analyzed !== 0 || r.items.length !== 0 || r.stale)) ||
      (r.analysis && r.analysis.usageReportedCalls > r.analysis.apiCalls) ||
      r.ignoredPercent !==
        (c.analyzed ? Math.round((c.ignored * 100) / c.analyzed) : null) ||
      r.items.some(
        (x, i) =>
          x.sequence >= c.total ||
          (i > 0 && x.sequence <= r.items[i - 1].sequence) ||
          (x.confidence < 0.65
            ? x.outcome !== "UNCERTAIN"
            : x.outcome !== (x.relevant ? "RELEVANT" : "IGNORED")) ||
          new Set(x.relatedEntityTypes).size !== x.relatedEntityTypes.length ||
          (!x.relevant && x.relatedEntityTypes.length > 0),
      )
    )
      ctx.addIssue({
        code: "custom",
        message: "Invalid relevance coverage or source attribution",
      });
  });
export type RelevanceSnapshot = z.infer<typeof relevanceSchema>;
export function verifyRelevance(data: unknown, meeting: MeetingDetail) {
  const result = relevanceSchema.parse(data);
  const sources = new Map(meeting.utterances.map((u) => [u.id, u]));
  if (
    result.projectId !== meeting.projectId ||
    result.meetingId !== meeting.id ||
    result.counts.total !== meeting.utterances.length ||
    result.items.some((x) => {
      const source = sources.get(x.utteranceId);
      return (
        !source ||
        source.sequence !== x.sequence ||
        source.speaker !== x.speaker ||
        source.text.slice(0, 400) !== x.text
      );
    })
  )
    throw new Error("Relevance does not match this meeting's evidence.");
  return result;
}
export async function loadRelevance(
  meeting: MeetingDetail,
  signal: AbortSignal,
  page = 1,
  outcome: RelevanceOutcome = "ALL",
) {
  return verifyRelevance(
    await memoryRequest(
      `/api/workspace/projects/${meeting.projectId}/meetings/${meeting.id}/relevance?page=${page}&outcome=${outcome}`,
      { signal, cache: "no-store" },
    ),
    meeting,
  );
}
export async function analyzeRelevance(meeting: MeetingDetail) {
  return verifyRelevance(
    await memoryRequest(
      `/api/workspace/projects/${meeting.projectId}/meetings/${meeting.id}/relevance`,
      { method: "POST" },
    ),
    meeting,
  );
}
