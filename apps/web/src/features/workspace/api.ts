import { projectListSchema, workspaceSchema } from "./contracts";

export async function loadProjects(signal: AbortSignal) {
  const response = await fetch("/api/workspace/projects", {
    signal,
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Projects could not be loaded.");
  return projectListSchema.parse(await response.json());
}

export async function loadWorkspace(projectId: string, signal: AbortSignal) {
  const response = await fetch(
    `/api/workspace/projects/${encodeURIComponent(projectId)}`,
    { signal, cache: "no-store" },
  );
  if (!response.ok) throw new Error("Project state could not be loaded.");
  const workspace = workspaceSchema.parse(await response.json());
  if (workspace.project.id !== projectId)
    throw new Error("Project response does not match the requested workspace.");
  return workspace;
}
