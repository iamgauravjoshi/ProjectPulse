import data from "./workspace.json";
import {
  workspaceSchema,
  type ProjectSummary,
} from "../../src/features/workspace/contracts";

export const fixture = workspaceSchema.parse(data);
export function emptyWorkspace(project: ProjectSummary = fixture.project) {
  return {
    ...structuredClone(fixture),
    project,
    requirements: [],
    decisions: [],
    commitments: [],
    risks: [],
    milestones: [],
    dependencies: [],
    questions: [],
    activity: [],
    members: fixture.members.filter((m) => m.name === "Sarah"),
  };
}
