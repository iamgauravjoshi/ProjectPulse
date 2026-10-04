export type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";

// Presentation only: API status values and business classification are unchanged.
const tones: Record<string, StatusTone> = {
  ACTIVE: "success",
  CONFIRMED: "success",
  READY: "success",
  DONE: "success",
  COMPLETED: "success",
  MITIGATED: "success",
  RESOLVED: "success",
  CLOSED: "success",
  INDEXED: "success",
  LOW: "success",
  PENDING: "warning",
  PROVISIONAL: "warning",
  REVIEW_REQUIRED: "warning",
  MEDIUM: "warning",
  NO_DUE_DATE: "warning",
  NOT_INDEXED: "warning",
  HIGH: "danger",
  CRITICAL: "danger",
  BLOCKED: "danger",
  AT_RISK: "danger",
  OVERDUE: "danger",
  FAILED: "danger",
  REJECTED: "danger",
  OPEN: "info",
  IN_PROGRESS: "info",
  PLANNED: "info",
  PROPOSAL: "info",
  DISCUSSION: "info",
  DRAFT: "neutral",
  ARCHIVED: "neutral",
  SUPERSEDED: "neutral",
  CANCELLED: "neutral",
  UNAVAILABLE: "neutral",
};
export function statusTone(status: string): StatusTone {
  return tones[status.toUpperCase()] ?? "neutral";
}
