import { z } from "zod";
export const documentSchema = z.object({
  id: z.uuid(),
  projectId: z.uuid(),
  filename: z.string(),
  format: z.string(),
  byteSize: z.number().int().positive(),
  createdAt: z.iso.datetime({ offset: true }),
  uploadedBy: z.uuid(),
  duplicate: z.boolean(),
  segmentCount: z.number().int().nonnegative(),
});
export const detailSchema = documentSchema.extend({
  segments: z.array(
    z.object({
      page: z.number().int().positive().nullable(),
      section: z.string().nullable(),
      text: z.string(),
    }),
  ),
});
export type DocumentSummary = z.infer<typeof documentSchema>;
export async function memoryRequest(url: string, options?: RequestInit) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      body?.error?.message ??
        "Request failed. Check the library before retrying.",
    );
  }
  return response.status === 204 ? null : response.json();
}
export async function loadDocuments(projectId: string, signal: AbortSignal) {
  const docs = z.array(documentSchema).parse(
    await memoryRequest(`/api/workspace/projects/${projectId}/documents`, {
      signal,
      cache: "no-store",
    }),
  );
  if (docs.some((x) => x.projectId !== projectId))
    throw new Error("Outside project evidence");
  return docs;
}
