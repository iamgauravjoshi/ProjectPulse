import type { LucideIcon } from "lucide-react";
import { humanLabel } from "../../features/workspace/presenters";

export function StatusBadge({ status }: { status: string }) {
  const positive = [
    "CONFIRMED",
    "ACTIVE",
    "READY",
    "DONE",
    "COMPLETED",
  ].includes(status);
  const warning = [
    "HIGH",
    "CRITICAL",
    "PENDING",
    "BLOCKED",
    "AT_RISK",
    "REVIEW_REQUIRED",
    "PROVISIONAL",
    "OVERDUE",
  ].includes(status);
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-md px-2 py-0.5 text-[13px] font-medium ${positive ? "badge-success" : warning ? "badge-warning" : "badge-neutral"}`}
    >
      {humanLabel(status)}
    </span>
  );
}

export function Panel({
  title,
  icon: Icon,
  action,
  children,
  id,
}: {
  title: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  children: React.ReactNode;
  id?: string;
}) {
  return (
    <section id={id} className="min-w-0 rounded-xl border border-line bg-white">
      <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-4">
        <h2 className="flex items-center gap-2 text-base font-semibold text-ink">
          {Icon && <Icon size={18} aria-hidden="true" className="text-muted" />}
          {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function EmptyCategory({ text }: { text: string }) {
  return <p className="px-5 py-6 text-sm leading-6 text-muted">{text}</p>;
}
