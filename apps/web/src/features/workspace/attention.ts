import type { Workspace } from "./contracts";
import { workspaceHref } from "./navigation";
import { formatDate, openCommitments } from "./presenters";

export type AttentionItem = {
  id: string;
  kind: "review" | "overdue" | "unscheduled" | "timeline";
  title: string;
  description: string;
  status: string;
  href: string;
};

export function projectDate(timestamp: string) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(timestamp));
  const value = (type: string) =>
    parts.find((part) => part.type === type)!.value;
  return `${value("year")}-${value("month")}-${value("day")}`;
}

export function attentionItems(workspace: Workspace): AttentionItem[] {
  const today = projectDate(workspace.generatedAt);
  const projectId = workspace.project.id;
  const items: AttentionItem[] = [];
  for (const decision of workspace.decisions) {
    if (decision.decisionStatus === "REVIEW_REQUIRED")
      items.push({
        id: decision.id,
        kind: "review",
        title: decision.title,
        description: "This decision is recorded as requiring review.",
        status: "REVIEW_REQUIRED",
        href: workspaceHref(projectId, "decisions"),
      });
  }
  for (const commitment of openCommitments(workspace)) {
    if (commitment.dueDate && commitment.dueDate < today)
      items.push({
        id: commitment.id,
        kind: "overdue",
        title: commitment.title,
        description: `Due ${formatDate(commitment.dueDate)}; delivery is still open.`,
        status: "OVERDUE",
        href: workspaceHref(projectId, "commitments"),
      });
    else if (!commitment.dueDate)
      items.push({
        id: commitment.id,
        kind: "unscheduled",
        title: commitment.title,
        description: "A delivery date has not been agreed.",
        status: "NO_DUE_DATE",
        href: workspaceHref(projectId, "commitments"),
      });
  }
  const activeMilestones = workspace.milestones.filter((m) =>
    ["PLANNED", "AT_RISK"].includes(m.status),
  );
  for (const dependency of workspace.dependencies) {
    const milestone = activeMilestones.find(
      (m) => m.id === dependency.blockedMilestoneId,
    );
    if (milestone && ["PENDING", "BLOCKED"].includes(dependency.status))
      items.push({
        id: dependency.id,
        kind: "timeline",
        title: dependency.title,
        description: `${dependency.status === "BLOCKED" ? "Blocked" : "Pending"} before ${milestone.title.toLowerCase()}.`,
        status: dependency.status,
        href: `${workspaceHref(projectId)}#milestones`,
      });
  }
  for (const milestone of activeMilestones) {
    if (milestone.date < today)
      items.push({
        id: milestone.id,
        kind: "timeline",
        title: milestone.title,
        description: `${formatDate(milestone.date)} has passed; the milestone remains open.`,
        status: "AT_RISK",
        href: `${workspaceHref(projectId)}#milestones`,
      });
  }
  const priority = { overdue: 0, review: 1, timeline: 2, unscheduled: 3 };
  return items.sort(
    (a, b) =>
      priority[a.kind] - priority[b.kind] || a.title.localeCompare(b.title),
  );
}

export function attentionCounts(workspace: Workspace) {
  const items = attentionItems(workspace);
  return {
    review: items.filter((i) => i.kind === "review").length,
    overdue: items.filter((i) => i.kind === "overdue").length,
    timeline: items.filter((i) => i.kind === "timeline").length,
    unscheduled: items.filter((i) => i.kind === "unscheduled").length,
  };
}

export function milestoneDependencies(
  workspace: Workspace,
  milestoneId: string,
) {
  return workspace.dependencies.filter(
    (d) =>
      d.blockedMilestoneId === milestoneId &&
      ["PENDING", "BLOCKED"].includes(d.status),
  );
}

export function reviewGroups(workspace: Workspace) {
  const items = attentionItems(workspace);
  return {
    reviews: items.filter((item) => item.kind === "review"),
    followups: items.filter((item) => item.kind !== "review"),
  };
}
