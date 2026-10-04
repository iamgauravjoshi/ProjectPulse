import { z } from "zod";
import { sameOrigin } from "./memory-proxy";

export async function proxyMeetings(
  request: Request,
  params: { projectId: string; meetingId?: string },
  action?: "participants" | "transcript",
) {
  if (
    !z.uuid().safeParse(params.projectId).success ||
    (params.meetingId && !z.uuid().safeParse(params.meetingId).success)
  )
    return Response.json(
      { error: { message: "Meeting not found." } },
      { status: 404 },
    );
  if (!sameOrigin(request))
    return Response.json(
      { error: { message: "Request origin is not allowed." } },
      { status: 403 },
    );
  const filename = new URL(request.url).searchParams.get("filename");
  if (action === "transcript" && (!filename || filename.length > 240))
    return Response.json(
      { error: { message: "Choose a valid filename." } },
      { status: 422 },
    );
  try {
    let body: Uint8Array | undefined;
    if (request.method === "POST") {
      const limit = action === "transcript" ? 2097152 : 65536;
      const reader = request.body?.getReader();
      const chunks: Uint8Array[] = [];
      let size = 0;
      if (reader)
        while (true) {
          const result = await reader.read();
          if (result.done) break;
          if (size + result.value.byteLength > limit) {
            await reader.cancel();
            return Response.json(
              {
                error: {
                  message:
                    action === "transcript"
                      ? "Transcripts must be no larger than 2 MiB."
                      : "Meeting fields are too large.",
                },
              },
              { status: 413 },
            );
          }
          size += result.value.byteLength;
          chunks.push(result.value);
        }
      body = new Uint8Array(size);
      let offset = 0;
      for (const chunk of chunks) {
        body.set(chunk, offset);
        offset += chunk.byteLength;
      }
    }
    const base = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
    const path = `meetings${params.meetingId ? `/${params.meetingId}` : ""}${action ? `/${action}` : ""}${action === "transcript" ? `?filename=${encodeURIComponent(filename!)}` : ""}`;
    const response = await fetch(
      `${base.replace(/\/$/, "")}/api/v1/projects/${params.projectId}/${path}`,
      {
        method: request.method,
        body: body as BodyInit | undefined,
        headers: body
          ? {
              "Content-Type":
                action === "transcript"
                  ? "application/octet-stream"
                  : "application/json",
            }
          : undefined,
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(20000),
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
          message:
            "Meetings are temporarily unavailable. Check the meeting before retrying.",
        },
      },
      { status: 503 },
    );
  }
}
