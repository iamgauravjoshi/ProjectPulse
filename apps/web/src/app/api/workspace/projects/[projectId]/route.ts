import { z } from "zod";
import { proxyWorkspaceRead } from "../../../../../lib/workspace-proxy";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ projectId: string }> },
) {
  const { projectId } = await context.params;
  if (!z.uuid().safeParse(projectId).success) {
    return Response.json(
      { error: { code: "PROJECT_NOT_FOUND", message: "Project not found." } },
      { status: 404 },
    );
  }
  return proxyWorkspaceRead(`/${projectId}/workspace`);
}
