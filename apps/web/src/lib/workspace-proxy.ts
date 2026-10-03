export async function proxyWorkspaceRead(path: string): Promise<Response> {
  const base = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
  try {
    const response = await fetch(
      `${base.replace(/\/$/, "")}/api/v1/projects${path}`,
      {
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(8_000),
      },
    );
    return Response.json(await response.json(), {
      status: response.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return Response.json(
      {
        error: {
          code: "WORKSPACE_UNAVAILABLE",
          message: "Workspace is temporarily unavailable.",
        },
      },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }
}
