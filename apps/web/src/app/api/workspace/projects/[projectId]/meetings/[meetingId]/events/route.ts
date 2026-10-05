import { proxyMeetings } from "../../../../../../../../lib/meetings-proxy";
type Context = { params: Promise<{ projectId: string; meetingId: string }> };
export async function GET(request: Request, context: Context) {
  return proxyMeetings(request, await context.params, "events");
}
export async function POST(request: Request, context: Context) {
  return proxyMeetings(request, await context.params, "events");
}
