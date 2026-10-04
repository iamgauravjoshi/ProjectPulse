import { z } from "zod";
import { memoryRequest } from "../memory/documents";
import { workspaceHref } from "../workspace/navigation";

export const meetingSchema = z
  .object({
    id: z.uuid(),
    projectId: z.uuid(),
    title: z.string().min(1).max(240),
    startedAt: z.iso.datetime({ offset: true }).nullable(),
    createdAt: z.iso.datetime({ offset: true }),
    createdBy: z.uuid(),
    hasTranscript: z.boolean(),
    transcriptFilename: z.string().max(240).nullable(),
    transcriptFormat: z.enum(["txt", "json", "vtt"]).nullable(),
  })
  .refine(
    (m) =>
      m.hasTranscript ===
      (m.transcriptFilename !== null && m.transcriptFormat !== null),
    "Invalid source metadata",
  );
export const participantSchema = z.object({
  id: z.uuid(),
  meetingId: z.uuid(),
  displayName: z.string().min(1).max(120),
  speakerKey: z.string().min(1).max(160),
  userId: z.uuid().nullable(),
});
export const utteranceSchema = z
  .object({
    id: z.uuid(),
    meetingId: z.uuid(),
    sequence: z.number().int().min(0).max(9999),
    speaker: z.string().min(1).max(120),
    speakerId: z.uuid().nullable(),
    timestampMs: z.number().int().min(0).max(604800000).nullable(),
    endMs: z.number().int().min(0).max(604800000).nullable(),
    text: z.string().min(1).max(6000),
    confidence: z.number().min(0).max(1).nullable(),
  })
  .refine(
    (u) =>
      u.endMs === null || (u.timestampMs !== null && u.endMs >= u.timestampMs),
  );
export const meetingDetailSchema = meetingSchema
  .safeExtend({
    participants: z.array(participantSchema).max(100),
    utterances: z.array(utteranceSchema).max(10000),
  })
  .superRefine((m, ctx) => {
    const ids = new Set(m.participants.map((p) => p.id));
    if (
      ids.size !== m.participants.length ||
      new Set(m.participants.map((p) => p.speakerKey)).size !==
        m.participants.length ||
      m.participants.some((p) => p.meetingId !== m.id) ||
      new Set(m.utterances.map((u) => u.id)).size !== m.utterances.length ||
      m.utterances.some(
        (u, i) =>
          u.meetingId !== m.id ||
          u.sequence !== i ||
          (u.speakerId !== null && !ids.has(u.speakerId)),
      ) ||
      m.utterances.reduce((sum, u) => sum + u.text.length, 0) > 1000000 ||
      m.hasTranscript !== m.utterances.length > 0
    )
      ctx.addIssue({ code: "custom", message: "Invalid meeting evidence" });
  });
export type MeetingSummary = z.infer<typeof meetingSchema>;
export type MeetingDetail = z.infer<typeof meetingDetailSchema>;
export const PAGE_SIZE = 100;
export function elapsedTime(ms: number | null) {
  if (ms === null) return "Time unknown";
  const seconds = Math.floor(ms / 1000);
  const base = [
    Math.floor(seconds / 3600),
    Math.floor(seconds / 60) % 60,
    seconds % 60,
  ]
    .map((value) => value.toString().padStart(2, "0"))
    .join(":");
  return ms % 1000
    ? `${base}.${(ms % 1000).toString().padStart(3, "0")}`
    : base;
}
export function meetingHref(
  projectId: string,
  meetingId: string,
  utteranceId?: string,
) {
  return `${workspaceHref(projectId, "meetings")}&meeting=${encodeURIComponent(meetingId)}${utteranceId ? `&utterance=${encodeURIComponent(utteranceId)}#utterance-${encodeURIComponent(utteranceId)}` : ""}`;
}
export function validateTranscriptFile(file: Pick<File, "name" | "size">) {
  if (!file.size || file.size > 2097152)
    return "Choose a nonempty transcript no larger than 2 MiB.";
  if (file.name.length > 240 || !/\.(txt|json|vtt)$/i.test(file.name))
    return "Choose a TXT, JSON or VTT transcript.";
  return null;
}
export async function loadMeetings(projectId: string, signal: AbortSignal) {
  const meetings = z
    .array(meetingSchema)
    .max(200)
    .parse(
      await memoryRequest(`/api/workspace/projects/${projectId}/meetings`, {
        signal,
        cache: "no-store",
      }),
    );
  if (meetings.some((m) => m.projectId !== projectId))
    throw new Error("Outside project meeting");
  return meetings;
}
export async function loadMeeting(
  projectId: string,
  meetingId: string,
  signal: AbortSignal,
) {
  const m = meetingDetailSchema.parse(
    await memoryRequest(
      `/api/workspace/projects/${projectId}/meetings/${meetingId}`,
      { signal, cache: "no-store" },
    ),
  );
  if (m.projectId !== projectId || m.id !== meetingId)
    throw new Error("Outside project meeting");
  return m;
}
