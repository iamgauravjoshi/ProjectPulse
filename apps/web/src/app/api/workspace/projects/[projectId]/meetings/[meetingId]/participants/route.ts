import { proxyMeetings } from "../../../../../../../../lib/meetings-proxy";
export const dynamic = "force-dynamic";
async function handle(
  request: Request,
  context: { params: Promise<{ projectId: string; meetingId: string }> },
) {
  return proxyMeetings(request, await context.params, "participants");
}
export { handle as POST };
