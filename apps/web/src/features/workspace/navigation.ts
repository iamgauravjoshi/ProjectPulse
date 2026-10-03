import {
  CalendarDays,
  Database,
  FileText,
  CheckCheck,
  CircleAlert,
  LayoutDashboard,
  ListChecks,
  MessageSquare,
  Inbox,
} from "lucide-react";

export const navigation = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "state", label: "Project state", icon: Database },
  { id: "documents", label: "Documents", icon: FileText },
  { id: "meetings", label: "Meetings", icon: CalendarDays },
  { id: "decisions", label: "Decisions", icon: ListChecks },
  { id: "commitments", label: "Commitments", icon: CheckCheck },
  { id: "risks", label: "Risks", icon: CircleAlert },
  { id: "review", label: "Review inbox", icon: Inbox },
] as const;

export type WorkspaceView = (typeof navigation)[number]["id"];
export function workspaceHref(
  projectId: string,
  view: WorkspaceView = "overview",
) {
  return `/?project=${encodeURIComponent(projectId)}&view=${view}`;
}
export function resolveView(value: string | null): WorkspaceView | null {
  if (value === null) return "overview";
  return navigation.find((item) => item.id === value)?.id ?? null;
}
export const emptyViewIcon = MessageSquare;
