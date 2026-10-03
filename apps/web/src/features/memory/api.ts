import { workspaceSchema } from "../workspace/contracts";
import type { RecordKind } from "./forms";
export class MemoryError extends Error {
  constructor(
    public code: string,
    message: string,
  ) {
    super(message);
  }
}
export async function mutateState(
  projectId: string,
  kind: RecordKind,
  method: "POST" | "PUT" | "DELETE",
  values?: Record<string, unknown>,
  id?: string,
  version?: number,
) {
  const url = `/api/workspace/projects/${projectId}/state/${kind}${id ? `/${id}` : ""}${method === "DELETE" ? `?expectedVersion=${version}` : ""}`;
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body:
        method === "DELETE"
          ? undefined
          : JSON.stringify(
              method === "PUT" ? { expectedVersion: version, values } : values,
            ),
    });
  } catch {
    throw new MemoryError(
      "NETWORK_ERROR",
      "Connection lost. Check the project state before retrying.",
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new MemoryError(
      body?.error?.code ?? "SAVE_FAILED",
      body?.error?.message ??
        "Couldn’t save. Check the project state before retrying.",
    );
  }
  if (method !== "DELETE") {
    const record = workspaceSchema.shape[kind].element.parse(
      await response.json(),
    );
    if (record.projectId !== projectId || (id && record.id !== id))
      throw new MemoryError(
        "INVALID_RESPONSE",
        "Unexpected record returned. Reload the project state.",
      );
  }
}
