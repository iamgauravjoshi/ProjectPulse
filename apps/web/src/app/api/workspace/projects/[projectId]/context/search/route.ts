import { proxyEvidence } from "../../../../../../../lib/evidence-proxy";
export const dynamic = "force-dynamic";
export async function GET(
  request: Request,
  context: { params: Promise<{ projectId: string }> },
) {
  const { projectId } = await context.params;
  const params = new URL(request.url).searchParams;
  const query = params.get("query")?.trim();
  const limit = params.get("limit") ?? "8";
  if (!query || query.length > 400 || !/^[1-8]$/.test(limit))
    return Response.json(
      { error: { message: "Enter a query of 1–400 characters." } },
      { status: 422 },
    );
  return proxyEvidence(
    request,
    projectId,
    `context/search?query=${encodeURIComponent(query)}&limit=${limit}`,
  );
}
