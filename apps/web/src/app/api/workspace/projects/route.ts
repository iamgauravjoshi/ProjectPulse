import { proxyWorkspaceRead } from "../../../../lib/workspace-proxy";

export const dynamic = "force-dynamic";

export async function GET() {
  return proxyWorkspaceRead("");
}
