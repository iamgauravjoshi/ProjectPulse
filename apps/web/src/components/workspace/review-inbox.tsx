import { GitCompareArrows, Inbox, ListChecks } from "lucide-react";
import Link from "next/link";
import type { Workspace } from "../../features/workspace/contracts";
import { reviewGroups } from "../../features/workspace/attention";
import { EmptyCategory, Panel, StatusBadge } from "./primitives";

export function ReviewInbox({ workspace }: { workspace: Workspace }) {
  const { reviews, followups } = reviewGroups(workspace);
  return (
    <div className="grid items-start gap-6 xl:grid-cols-2">
      <Panel title="Decisions needing review" icon={Inbox}>
        {reviews.length === 0 ? (
          <EmptyCategory text="No decisions are currently marked for review." />
        ) : (
          <ul className="divide-y divide-line">
            {reviews.map((item) => (
              <li key={item.id} className="px-5 py-4">
                <Link
                  href={item.href}
                  className="text-sm font-medium text-accent"
                >
                  {item.title}
                </Link>
                <div className="mt-2">
                  <StatusBadge status={item.status} />
                </div>
                <p className="mt-2 text-sm leading-6 text-muted">
                  {item.description}
                </p>
              </li>
            ))}
          </ul>
        )}
        <div className="border-t border-line px-5 py-4 text-[13px] leading-6 text-muted">
          Proposed changes stay separate from confirmed project state.
        </div>
      </Panel>
      <Panel title="Conflicts" icon={GitCompareArrows}>
        <EmptyCategory text="Conflicting interpretations will appear here when meeting evidence is available." />
      </Panel>
      <Panel title="Project follow-up" icon={ListChecks}>
        {followups.length === 0 ? (
          <EmptyCategory text="No open baseline follow-ups." />
        ) : (
          <ul className="divide-y divide-line">
            {followups.map((item) => (
              <li key={item.id} className="px-5 py-4">
                <Link
                  href={item.href}
                  className="flex flex-wrap items-center justify-between gap-2 text-sm font-medium text-accent"
                >
                  {item.title}
                  <StatusBadge status={item.status} />
                </Link>
                <p className="mt-2 text-sm leading-6 text-muted">
                  {item.description}
                </p>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
