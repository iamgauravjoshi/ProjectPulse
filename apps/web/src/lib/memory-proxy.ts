import { z } from "zod";
import { kinds } from "../features/memory/forms";
export function sameOrigin(request: Request) {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  try {
    const url = new URL(origin);
    return (
      url.host === request.headers.get("host") &&
      url.protocol === new URL(request.url).protocol
    );
  } catch {
    return false;
  }
}
export async function proxyMemory(
  request: Request,
  params: { projectId: string; kind: string; recordId?: string },
) {
  if (
    !z.uuid().safeParse(params.projectId).success ||
    !kinds.includes(params.kind as (typeof kinds)[number]) ||
    (params.recordId && !z.uuid().safeParse(params.recordId).success)
  )
    return Response.json(
      { error: { code: "NOT_FOUND", message: "Record not found." } },
      { status: 404 },
    );
  if (!sameOrigin(request))
    return Response.json(
      {
        error: {
          code: "INVALID_ORIGIN",
          message: "Request origin is not allowed.",
        },
      },
      { status: 403 },
    );
  let body: string | undefined;
  if (request.method === "POST" || request.method === "PUT") {
    body = await request.text();
    if (new TextEncoder().encode(body).length > 65536)
      return Response.json(
        { error: { message: "Record is too large." } },
        { status: 413 },
      );
  }
  const query = new URL(request.url).searchParams;
  let suffix = "";
  if (request.method === "DELETE") {
    const version = query.get("expectedVersion");
    if (!version || !/^[1-9]\d*$/.test(version))
      return Response.json(
        { error: { message: "A valid version is required." } },
        { status: 422 },
      );
    suffix = `?expectedVersion=${version}`;
  }
  try {
    const base = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(
      `${base.replace(/\/$/, "")}/api/v1/projects/${params.projectId}/state/${params.kind}${params.recordId ? `/${params.recordId}` : ""}${suffix}`,
      {
        method: request.method,
        body,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(8000),
      },
    );
    return response.status === 204
      ? new Response(null, { status: 204 })
      : Response.json(await response.json(), {
          status: response.status,
          headers: { "Cache-Control": "no-store" },
        });
  } catch {
    return Response.json(
      {
        error: {
          code: "UNAVAILABLE",
          message: "Project state is temporarily unavailable.",
        },
      },
      { status: 503 },
    );
  }
}
