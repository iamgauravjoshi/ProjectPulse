import { z } from "zod";
import { kinds } from "./forms";
import { memoryRequest } from "./documents";
const base = z.object({
  id: z.uuid(),
  projectId: z.uuid(),
  title: z.string(),
  excerpt: z.string().max(600),
});
export const searchSchema = z
  .object({
    projectId: z.uuid(),
    query: z.string().min(1).max(400),
    semanticStatus: z.enum(["ready", "unavailable", "not_indexed", "failed"]),
    matches: z
      .array(
        z.discriminatedUnion("kind", [
          base.extend({
            kind: z.literal("record"),
            canonical: z.literal(true),
            entityType: z.enum(kinds),
            facts: z.record(
              z.string(),
              z.union([z.string(), z.number(), z.null()]),
            ),
          }),
          base.extend({
            kind: z.literal("document"),
            canonical: z.literal(false),
            documentId: z.uuid(),
            page: z.number().int().positive().nullable(),
            section: z.string().nullable(),
            segmentIndex: z.number().int().nonnegative(),
            start: z.number().int().nonnegative(),
            end: z.number().int().positive(),
          }),
        ]),
      )
      .max(8),
  })
  .superRefine((data, ctx) => {
    if (data.matches.some((x) => x.projectId !== data.projectId))
      ctx.addIssue({ code: "custom", message: "Outside project context" });
  });
export type SearchResult = z.infer<typeof searchSchema>;
export async function searchContext(
  projectId: string,
  query: string,
  signal: AbortSignal,
) {
  const parsed = searchSchema.safeParse(
    await memoryRequest(
      `/api/workspace/projects/${projectId}/context/search?query=${encodeURIComponent(query)}`,
      { signal, cache: "no-store" },
    ),
  );
  if (!parsed.success)
    throw new Error("Unexpected project context. Try again.");
  const data = parsed.data;
  if (data.projectId !== projectId || data.query !== query.trim())
    throw new Error("Unexpected project context. Try again.");
  return data;
}
