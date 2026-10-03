import { z } from "zod";
import { proxyEvidence } from "../../../../../../../../lib/evidence-proxy";
export const dynamic = "force-dynamic";
export async function POST(
  request: Request,
  context: { params: Promise<{ projectId: string; documentId: string }> },
) {
  const { projectId, documentId } = await context.params;
  if (!z.uuid().safeParse(documentId).success)
    return Response.json(
      { error: { message: "Document not found." } },
      { status: 404 },
    );
  return proxyEvidence(request, projectId, `documents/${documentId}/index`);
}
