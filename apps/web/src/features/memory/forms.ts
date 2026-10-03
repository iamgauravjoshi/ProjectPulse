import { z } from "zod";
import type { Workspace } from "../workspace/contracts";

export const kinds = [
  "requirements",
  "decisions",
  "milestones",
  "risks",
  "commitments",
  "dependencies",
] as const;
export type RecordKind = (typeof kinds)[number];
export type StateRecord = Workspace[RecordKind][number];
export const fields: Record<RecordKind, Record<string, string[] | null>> = {
  requirements: {
    status: ["DRAFT", "ACTIVE", "COMPLETED", "ARCHIVED"],
    phase: null,
  },
  decisions: {
    decisionStatus: [
      "DISCUSSION",
      "PROPOSAL",
      "PROVISIONAL",
      "REVIEW_REQUIRED",
      "CONFIRMED",
      "SUPERSEDED",
      "REJECTED",
    ],
    impactArea: null,
  },
  milestones: {
    status: ["PLANNED", "AT_RISK", "COMPLETED", "CANCELLED"],
    date: null,
  },
  risks: {
    status: ["OPEN", "MITIGATED", "CLOSED"],
    severity: ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
  },
  commitments: {
    status: ["OPEN", "IN_PROGRESS", "DONE", "CANCELLED"],
    ownerId: null,
    dueDate: null,
    dependencyId: null,
  },
  dependencies: {
    status: ["PENDING", "READY", "BLOCKED"],
    ownerId: null,
    blockedMilestoneId: null,
  },
};
export const labels: Record<string, string> = {
  title: "Title",
  description: "Description",
  status: "Status",
  phase: "Phase",
  decisionStatus: "Decision status",
  impactArea: "Impact area",
  date: "Date",
  severity: "Severity",
  ownerId: "Owner",
  dueDate: "Due date",
  dependencyId: "Dependency",
  blockedMilestoneId: "Blocked milestone",
};
export function formValues(
  kind: RecordKind,
  record?: StateRecord,
): Record<string, string> {
  const source = record as unknown as Record<string, unknown> | undefined;
  return Object.fromEntries(
    ["title", "description", ...Object.keys(fields[kind])].map((key) => [
      key,
      String(
        source?.[key] ??
          (key === "phase"
            ? 1
            : key === "status" && kind === "requirements"
              ? "ACTIVE"
              : (fields[kind][key]?.[0] ?? "")),
      ),
    ]),
  );
}
export function parseValues(
  kind: RecordKind,
  values: Record<string, string>,
): Record<string, unknown> {
  const result: Record<string, unknown> = {
    title: z
      .string()
      .trim()
      .min(1, "Enter a title.")
      .max(240)
      .parse(values.title),
    description: z.string().trim().max(20000).parse(values.description),
  };
  for (const [key, choices] of Object.entries(fields[kind])) {
    const value = values[key]?.trim() ?? "";
    result[key] = choices
      ? z.enum(choices as [string, ...string[]]).parse(value)
      : key === "phase"
        ? z.coerce.number().int().positive().parse(value)
        : key.endsWith("Id")
          ? value
            ? z.uuid().parse(value)
            : null
          : key === "date" || key === "dueDate"
            ? value || key === "date"
              ? z.iso.date().parse(value)
              : null
            : z.string().max(120).parse(value);
  }
  return result;
}
