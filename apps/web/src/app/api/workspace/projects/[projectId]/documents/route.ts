import { proxyEvidence } from "../../../../../../lib/evidence-proxy";
export const dynamic = "force-dynamic";
async function handle(
  request: Request,
  context: { params: Promise<{ projectId: string }> },
) {
  const { projectId } = await context.params;
  const filename = new URL(request.url).searchParams.get("filename");
  if (request.method === "POST" && (!filename || filename.length > 240))
    return Response.json(
      { error: { message: "Choose a valid filename." } },
      { status: 422 },
    );
  return proxyEvidence(
    request,
    projectId,
    `documents${request.method === "POST" ? `?filename=${encodeURIComponent(filename!)}` : ""}`,
  );
}
export { handle as GET, handle as POST };
