import {
  ArrowUpRight,
  CalendarDays,
  CheckCheck,
  CheckCircle2,
  CircleAlert,
  Clock3,
  HelpCircle,
  MessageSquare,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import type { Workspace } from "../../features/workspace/contracts";
import { workspaceHref } from "../../features/workspace/navigation";
import {
  formatDate,
  formatTimestamp,
  humanLabel,
  overviewRecords,
  ownerName,
  workspaceMetrics,
} from "../../features/workspace/presenters";
import { EmptyCategory, Panel, StatusBadge } from "./primitives";
import { Badge } from "../ui/badge";
import { Separator } from "../ui/feedback";
import { milestoneDependencies } from "../../features/workspace/attention";

export function Overview({
  workspace,
  attention,
}: {
  workspace: Workspace;
  attention?: React.ReactNode;
}) {
  const { requirements, decisions, commitments, questions } =
    overviewRecords(workspace);
  return (
    <>
      <section
        aria-label="Project statistics"
        className="mb-7 grid grid-cols-2 overflow-hidden rounded-xl border border-line bg-surface sm:grid-cols-4"
      >
        {workspaceMetrics(workspace).map((metric) => (
          <div
            key={metric.label}
            className="border-line p-5 sm:border-r sm:last:border-0"
          >
            <p className="text-[13px] text-muted">{metric.label}</p>
            <p className="mt-2 text-2xl font-semibold tracking-tight text-ink">
              {metric.value}
            </p>
          </div>
        ))}
      </section>
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="min-w-0 flex flex-col gap-6">
          <Panel
            title="Current project state"
            icon={ShieldCheck}
            id="project-state"
            action={
              <Badge tone="success" variant="outline">
                Trusted baseline
              </Badge>
            }
          >
            <div className="px-5 pb-1 pt-4">
              <h3 className="text-[13px] font-medium text-muted">
                Requirements
              </h3>
            </div>
            {requirements.length === 0 ? (
              <EmptyCategory text="No active requirements yet." />
            ) : (
              requirements.map((record) => (
                <div
                  key={record.id}
                  className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 border-b border-line px-5 py-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]"
                >
                  <span className="text-sm font-medium text-ink">
                    {record.title}
                  </span>
                  <span className="col-span-2 text-sm text-muted sm:col-span-1 sm:col-start-2 sm:row-start-1">
                    Phase {record.phase}
                  </span>
                  <span className="col-start-2 row-start-1 sm:col-start-3">
                    <StatusBadge status={record.status} />
                  </span>
                </div>
              ))
            )}
            <div className="px-5 pb-1 pt-4">
              <h3 className="text-[13px] font-medium text-muted">
                Confirmed decisions
              </h3>
            </div>
            {decisions.length === 0 ? (
              <EmptyCategory text="No confirmed decisions yet. Proposals stay separate from the baseline." />
            ) : (
              decisions.map((record) => (
                <div
                  key={record.id}
                  className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-2 border-b border-line px-5 py-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto]"
                >
                  <span className="text-sm font-medium text-ink">
                    {record.title}
                  </span>
                  <span className="col-span-2 text-sm leading-6 text-muted sm:col-span-1 sm:col-start-2 sm:row-start-1">
                    {record.description}
                  </span>
                  <span className="col-start-2 row-start-1 sm:col-start-3">
                    <StatusBadge status={record.decisionStatus} />
                  </span>
                </div>
              ))
            )}
            <div className="flex items-center justify-between gap-3 px-5 py-3.5">
              <span className="text-[13px] text-muted">
                Confirmed values inform future conversations.
              </span>
              <Link
                className="flex shrink-0 items-center gap-1 text-[13px] font-medium text-accent"
                href={workspaceHref(workspace.project.id, "decisions")}
              >
                View decisions
                <ArrowUpRight size={14} aria-hidden="true" />
              </Link>
            </div>
          </Panel>
          <Panel
            title="Open commitments"
            icon={CheckCheck}
            action={
              <Link
                className="text-[13px] font-medium text-accent"
                href={workspaceHref(workspace.project.id, "commitments")}
              >
                View all
              </Link>
            }
          >
            {commitments.length === 0 ? (
              <EmptyCategory text="No open commitments." />
            ) : (
              commitments.map((record) => (
                <div
                  key={record.id}
                  className="flex flex-wrap items-start justify-between gap-3 px-5 py-4"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium">{record.title}</p>
                    <p className="mt-1.5 text-[13px] text-muted">
                      {ownerName(workspace, record.ownerId)}
                      <span className="mx-2 text-line">·</span>
                      {record.dueDate
                        ? `Due ${formatDate(record.dueDate)}`
                        : "Due date not set"}
                    </p>
                  </div>
                  <StatusBadge status={record.status} />
                </div>
              ))
            )}
          </Panel>
          <div className="grid gap-6 md:grid-cols-2">
            <Panel title="Risks" icon={CircleAlert}>
              {workspace.risks.length === 0 ? (
                <EmptyCategory text="No risks recorded." />
              ) : (
                workspace.risks.map((risk) => (
                  <div key={risk.id} className="flex flex-col gap-2 px-5 py-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={risk.severity} />
                      <StatusBadge status={risk.status} variant="outline" />
                    </div>
                    <h3 className="text-sm font-medium">{risk.title}</h3>
                    <p className="text-[13px] leading-6 text-muted">
                      {risk.description}
                    </p>
                  </div>
                ))
              )}
            </Panel>
            <Panel title="Open questions" icon={HelpCircle}>
              {questions.length === 0 ? (
                <EmptyCategory text="No open questions." />
              ) : (
                questions.map((question) => (
                  <div key={question.id} className="px-5 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="text-sm font-medium leading-6">
                        {question.title}
                      </h3>
                      <StatusBadge status={question.status} variant="outline" />
                    </div>
                    <p className="mt-2 text-[13px] text-muted">
                      Owner: {ownerName(workspace, question.ownerId)}
                    </p>
                  </div>
                ))
              )}
            </Panel>
          </div>
        </div>
        <div className="min-w-0 flex flex-col gap-6">
          {attention}
          <Panel title="Milestones" icon={CalendarDays} id="milestones">
            {workspace.milestones.length === 0 ? (
              <EmptyCategory text="No milestones recorded." />
            ) : (
              workspace.milestones.map((milestone) => (
                <div key={milestone.id} className="px-5 py-4">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-sm font-medium">{milestone.title}</h3>
                    <StatusBadge status={milestone.status} />
                  </div>
                  <p className="mt-3 text-xl font-semibold tracking-tight">
                    {formatDate(milestone.date)}
                  </p>
                  <p className="mt-1 text-[13px] text-muted">
                    {milestone.sourceKind === "SEED"
                      ? "Demo baseline"
                      : "Project baseline"}
                  </p>
                  {milestoneDependencies(workspace, milestone.id).map(
                    (dependency) => (
                      <div key={dependency.id} className="mt-4">
                        <Separator className="mb-3" />
                        <p className="text-[13px] font-medium text-ink">
                          {dependency.title}
                        </p>
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <StatusBadge status={dependency.status} />
                          <span className="text-[13px] text-muted">
                            Launch dependency
                          </span>
                        </div>
                      </div>
                    ),
                  )}
                </div>
              ))
            )}
          </Panel>
          <Panel title="Recent meeting impact" icon={MessageSquare}>
            <div className="px-5 py-6">
              <div className="mb-4 flex size-9 items-center justify-center rounded-lg bg-surface-muted text-muted">
                <MessageSquare size={18} aria-hidden="true" />
              </div>
              <h3 className="text-sm font-medium">
                Every conversation needs context.
              </h3>
              <p className="mt-2 text-[13px] leading-6 text-muted">
                Meeting evidence and the changes it suggests will appear here.
              </p>
              <Link
                href={workspaceHref(workspace.project.id, "meetings")}
                className="mt-4 inline-flex items-center gap-1 text-[13px] font-medium text-accent"
              >
                Meeting workspace
                <ArrowUpRight size={14} aria-hidden="true" />
              </Link>
            </div>
          </Panel>
          <Panel title="Project activity" icon={Clock3}>
            {workspace.activity.length === 0 ? (
              <EmptyCategory text="No project activity yet." />
            ) : (
              <ol className="flex flex-col gap-5 px-5 py-5">
                {workspace.activity.map((event) => (
                  <li key={event.id} className="flex items-start gap-3">
                    <CheckCircle2
                      size={17}
                      aria-hidden="true"
                      className="mt-0.5 shrink-0 text-accent"
                    />
                    <div>
                      <p className="text-sm font-medium leading-5">
                        {humanLabel(event.action)}
                      </p>
                      <p className="mt-1 text-[13px] leading-5 text-muted">
                        {formatTimestamp(event.createdAt)}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </Panel>
        </div>
      </div>
    </>
  );
}
