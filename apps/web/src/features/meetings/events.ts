import { z } from "zod";
import { memoryRequest } from "../memory/documents";
import type { MeetingDetail } from "./contracts";

export const eventKinds = [
  "REQUIREMENT_CHANGE",
  "DECISION",
  "COMMITMENT",
  "RISK",
  "MILESTONE_CHANGE",
  "DEPENDENCY",
  "OPEN_QUESTION",
] as const;
export type EventFilter = "ALL" | (typeof eventKinds)[number];
const count = z.number().int().nonnegative().max(10000);
const eventCount = z.number().int().nonnegative().max(40000);
const text = (max: number) =>
  z
    .string()
    .min(1)
    .max(max * 2)
    .refine((s) => s.trim().length > 0 && Array.from(s).length <= max);
const evidence = z.object({
  utteranceId: z.uuid(),
  sequence: count.max(9999),
  speaker: text(120),
  speakerId: z.uuid().nullable(),
  timestampMs: z.number().int().min(0).max(604800000).nullable(),
  quote: text(500),
});
const candidate = z.object({
  id: z.uuid(),
  projectId: z.uuid(),
  meetingId: z.uuid(),
  extractionId: z.uuid(),
  primaryUtteranceId: z.uuid(),
  sequence: count.max(9999),
  speaker: text(120),
  saidByUserId: z.uuid().nullable(),
  kind: z.enum(eventKinds),
  statement: z.enum(["PROPOSAL", "STATEMENT", "QUESTION", "NEGATED"]),
  status: z.literal("CANDIDATE"),
  title: text(240),
  description: text(1600),
  confidence: z.number().min(0).max(1),
  ownerMention: text(120).nullable(),
  dueDateText: text(120).nullable(),
  needsReview: z.boolean(),
  evidence: z.array(evidence).min(1).max(2),
});
export const eventsSchema = z
  .object({
    projectId: z.uuid(),
    meetingId: z.uuid(),
    prerequisite: z.enum(["NO_TRANSCRIPT", "ANALYZE_RELEVANCE"]).nullable(),
    currentRelevanceId: z.uuid().nullable(),
    stale: z.boolean(),
    relevance: z.object({
      total: count,
      relevant: count,
      ignored: count,
      uncertain: count,
      pending: count,
    }),
    counts: z.object({
      eligible: count,
      processed: count,
      pending: count,
      candidates: eventCount,
      noEvent: count,
      lowConfidence: eventCount,
    }),
    extraction: z
      .object({
        id: z.uuid(),
        relevanceAnalysisId: z.uuid(),
        model: text(80),
        extractorVersion: text(40),
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
    filteredCount: eventCount,
    items: z.array(candidate).max(100),
  })
  .superRefine((r, ctx) => {
    const c = r.counts,
      v = r.relevance;
    if (
      v.total !== v.relevant + v.ignored + v.uncertain + v.pending ||
      c.eligible !== v.relevant ||
      c.eligible !== c.processed + c.pending ||
      c.noEvent > c.processed ||
      c.candidates < c.processed - c.noEvent ||
      c.candidates > 4 * (c.processed - c.noEvent) ||
      c.lowConfidence > c.candidates ||
      r.filteredCount > c.candidates ||
      r.items.length !==
        Math.min(100, Math.max(0, r.filteredCount - (r.page - 1) * 100)) ||
      new Set(r.items.map((x) => x.id)).size !== r.items.length ||
      (r.extraction === null &&
        (c.processed !== 0 || c.candidates !== 0 || r.stale)) ||
      (r.extraction &&
        (r.extraction.usageReportedCalls > r.extraction.apiCalls ||
          (!r.stale &&
            r.extraction.relevanceAnalysisId !== r.currentRelevanceId))) ||
      (r.prerequisite === null) !== (r.currentRelevanceId !== null) ||
      r.items.some(
        (x, i) =>
          x.projectId !== r.projectId ||
          x.meetingId !== r.meetingId ||
          x.extractionId !== r.extraction?.id ||
          x.sequence >= v.total ||
          (i > 0 && x.sequence < r.items[i - 1].sequence) ||
          x.needsReview !== x.confidence < 0.65 ||
          !x.evidence.some((e) => e.utteranceId === x.primaryUtteranceId) ||
          new Set(x.evidence.map((e) => e.utteranceId)).size !==
            x.evidence.length,
      )
    )
      ctx.addIssue({
        code: "custom",
        message: "Invalid event coverage or provenance",
      });
  });
export type EventSnapshot = z.infer<typeof eventsSchema>;
export function verifyEvents(
  data: unknown,
  meeting: MeetingDetail,
  page = 1,
  kind: EventFilter = "ALL",
) {
  const r = eventsSchema.parse(data);
  const sources = new Map(meeting.utterances.map((u) => [u.id, u]));
  if (
    r.projectId !== meeting.projectId ||
    r.meetingId !== meeting.id ||
    r.relevance.total !== meeting.utterances.length ||
    r.page !== page ||
    (kind === "ALL" && r.filteredCount !== r.counts.candidates) ||
    (r.prerequisite === "NO_TRANSCRIPT") !== !meeting.hasTranscript ||
    r.items.some((x) => {
      const primary = sources.get(x.primaryUtteranceId);
      const participant = meeting.participants.find(
        (p) => p.id === primary?.speakerId,
      );
      const quotes = x.evidence.map((e) => e.quote).join("\n");
      const uncitedMention = [x.ownerMention, x.dueDateText].some(
        (mention) =>
          mention !== null &&
          !new RegExp(
            `(?<![\\p{L}\\p{N}_])${mention.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?![\\p{L}\\p{N}_])`,
            "u",
          ).test(quotes),
      );
      return (
        !primary ||
        primary.sequence !== x.sequence ||
        primary.speaker !== x.speaker ||
        x.saidByUserId !== (participant?.userId ?? null) ||
        (kind !== "ALL" && x.kind !== kind) ||
        uncitedMention ||
        x.evidence.some((e) => {
          const source = sources.get(e.utteranceId);
          return (
            !source ||
            source.sequence !== e.sequence ||
            source.speaker !== e.speaker ||
            source.speakerId !== e.speakerId ||
            source.timestampMs !== e.timestampMs ||
            !source.text.includes(e.quote) ||
            (source.id !== primary.id &&
              source.sequence !== primary.sequence - 1)
          );
        })
      );
    })
  )
    throw new Error("Event candidates do not match this meeting's evidence.");
  return r;
}
export async function loadEvents(
  meeting: MeetingDetail,
  signal: AbortSignal,
  page = 1,
  kind: EventFilter = "ALL",
) {
  return verifyEvents(
    await memoryRequest(
      `/api/workspace/projects/${meeting.projectId}/meetings/${meeting.id}/events?page=${page}&kind=${kind}`,
      { signal, cache: "no-store" },
    ),
    meeting,
    page,
    kind,
  );
}
export async function extractEvents(meeting: MeetingDetail) {
  return verifyEvents(
    await memoryRequest(
      `/api/workspace/projects/${meeting.projectId}/meetings/${meeting.id}/events`,
      { method: "POST" },
    ),
    meeting,
  );
}
