import { proxyMemory } from "../../../../../../../lib/memory-proxy";
export const dynamic = "force-dynamic";
async function handle(
  request: Request,
  context: { params: Promise<{ projectId: string; kind: string }> },
) {
  return proxyMemory(request, await context.params);
}
export { handle as GET, handle as POST };
