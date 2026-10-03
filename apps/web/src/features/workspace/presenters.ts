import type { Workspace } from "./contracts";

export function humanLabel(value: string) {
  const labels: Record<string, string> = {
    QA: "QA",
    TECH_LEAD: "Technical lead",
    DEMO_SEEDED: "Project baseline established",
  };
  return (
    labels[value] ??
    value
      .toLowerCase()
      .replaceAll("_", " ")
      .replace(/^./, (c) => c.toUpperCase())
  );
}

export function formatDate(value: string | null) {
  if (!value) return "Not set";
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T12:00:00Z`));
}

export function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));
}

export function ownerName(workspace: Workspace, id: string | null) {
  return (
    workspace.members.find((member) => member.id === id)?.name ?? "Unassigned"
  );
}

export function workspaceMetrics(workspace: Workspace) {
  return [
    {
      label: "Active requirements",
      value: workspace.requirements.filter((r) => r.status === "ACTIVE").length,
    },
    {
      label: "Confirmed decisions",
      value: workspace.decisions.filter((d) => d.decisionStatus === "CONFIRMED")
        .length,
    },
    { label: "Open commitments", value: openCommitments(workspace).length },
    {
      label: "Open risks",
      value: workspace.risks.filter((r) => r.status === "OPEN").length,
    },
  ];
}

export function openCommitments(workspace: Workspace) {
  return workspace.commitments.filter((record) =>
    ["OPEN", "IN_PROGRESS"].includes(record.status),
  );
}

export function overviewRecords(workspace: Workspace) {
  return {
    requirements: workspace.requirements.filter((r) => r.status === "ACTIVE"),
    decisions: workspace.decisions.filter(
      (d) => d.decisionStatus === "CONFIRMED",
    ),
    commitments: openCommitments(workspace),
    questions: workspace.questions.filter((q) => q.status === "OPEN"),
  };
}

export type RecordRow = {
  id: string;
  title: string;
  description: string;
  status: string;
  owner: string;
  date: string | null;
  source: string;
};
export function recordRows(
  workspace: Workspace,
  view: "decisions" | "commitments" | "risks",
): RecordRow[] {
  if (view === "decisions")
    return workspace.decisions.map((d) => ({
      id: d.id,
      title: d.title,
      description: d.description,
      status: d.decisionStatus,
      owner: ownerName(workspace, d.madeBy),
      date: null,
      source: d.sourceKind,
    }));
  if (view === "commitments")
    return workspace.commitments.map((c) => ({
      id: c.id,
      title: c.title,
      description: c.description,
      status: c.status,
      owner: ownerName(workspace, c.ownerId),
      date: c.dueDate,
      source: c.sourceKind,
    }));
  return workspace.risks.map((r) => ({
    id: r.id,
    title: r.title,
    description: r.description,
    status: r.status,
    owner: r.severity,
    date: null,
    source: r.sourceKind,
  }));
}

export function filterRows(rows: RecordRow[], query: string, status: string) {
  const term = query.trim().toLowerCase();
  return rows.filter(
    (row) =>
      (status === "ALL" || row.status === status) &&
      `${row.title} ${row.description} ${row.owner}`
        .toLowerCase()
        .includes(term),
  );
}
