import { z } from "zod";
import { sameOrigin } from "./memory-proxy";
export async function proxyEvidence(
  request: Request,
  projectId: string,
  path: string,
) {
  if (!z.uuid().safeParse(projectId).success)
    return Response.json(
      { error: { message: "Project not found." } },
      { status: 404 },
    );
  if (!sameOrigin(request))
    return Response.json(
      { error: { message: "Request origin is not allowed." } },
      { status: 403 },
    );
  try {
    let body: Uint8Array | undefined;
    if (request.method === "POST") {
      const reader = request.body?.getReader();
      const chunks: Uint8Array[] = [];
      let size = 0;
      if (reader) {
        while (true) {
          const result = await reader.read();
          if (result.done) break;
          size += result.value.byteLength;
          if (size > 5242880) {
            await reader.cancel();
            return Response.json(
              { error: { message: "Files must be no larger than 5 MiB." } },
              { status: 413 },
            );
          }
          chunks.push(result.value);
        }
      }
      body = new Uint8Array(size);
      let offset = 0;
      for (const chunk of chunks) {
        body.set(chunk, offset);
        offset += chunk.byteLength;
      }
    }
    const base = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(
      `${base.replace(/\/$/, "")}/api/v1/projects/${projectId}/${path}`,
      {
        method: request.method,
        body: body as BodyInit | undefined,
        headers: body
          ? { "Content-Type": "application/octet-stream" }
          : undefined,
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(path.endsWith("/index") ? 40000 : 20000),
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
      { error: { message: "Project memory is temporarily unavailable." } },
      { status: 503 },
    );
  }
}
