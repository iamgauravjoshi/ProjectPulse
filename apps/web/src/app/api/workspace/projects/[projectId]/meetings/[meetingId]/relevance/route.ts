import { proxyMeetings } from "../../../../../../../../lib/meetings-proxy";
export const dynamic = "force-dynamic";
async function handle(
  request: Request,
  context: { params: Promise<{ projectId: string; meetingId: string }> },
) {
  return proxyMeetings(request, await context.params, "relevance");
}
export { handle as GET, handle as POST };
