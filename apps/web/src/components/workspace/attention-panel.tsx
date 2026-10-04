import { ArrowUpRight, CircleAlert } from "lucide-react";
import Link from "next/link";
import type { Workspace } from "../../features/workspace/contracts";
import {
  attentionCounts,
  attentionItems,
} from "../../features/workspace/attention";
import { EmptyCategory, Panel, StatusBadge } from "./primitives";

export function AttentionPanel({ workspace }: { workspace: Workspace }) {
  const items = attentionItems(workspace);
  const counts = attentionCounts(workspace);
  return (
    <Panel
      title="Needs attention"
      icon={CircleAlert}
      action={
        <span
          aria-label={`${items.length} items need attention`}
          className="badge-warning rounded-md px-2 py-0.5 text-[13px] font-medium"
        >
          {items.length}
        </span>
      }
    >
      {items.length === 0 ? (
        <EmptyCategory text="No baseline follow-ups right now." />
      ) : (
        <ul className="divide-y divide-line">
          {items.map((item) => (
            <li key={item.id}>
              <Link
                href={item.href}
                className="block px-5 py-4 hover:bg-surface-muted"
              >
                <div className="mb-2">
                  <StatusBadge status={item.status} />
                </div>
                <div className="flex items-start justify-between gap-3">
                  <h3 className="text-sm font-semibold leading-5">
                    {item.title}
                  </h3>
                  <ArrowUpRight
                    size={15}
                    className="mt-0.5 shrink-0 text-muted"
                    aria-hidden="true"
                  />
                </div>
                <p className="mt-1 text-[13px] leading-5 text-muted">
                  {item.description}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <dl className="space-y-2 border-t border-line px-5 py-4 text-[13px]">
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Decision reviews</dt>
          <dd>{counts.review}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Overdue commitments</dt>
          <dd>{counts.overdue}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Timeline follow-ups</dt>
          <dd>{counts.timeline}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Conflicts</dt>
          <dd className="text-muted">Awaiting evidence</dd>
        </div>
      </dl>
    </Panel>
  );
}
