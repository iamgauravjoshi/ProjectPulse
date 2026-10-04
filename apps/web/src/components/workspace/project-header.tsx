import { ArrowUpRight, CircleCheck } from "lucide-react";
import Link from "next/link";
import type {
  ProjectSummary,
  Workspace,
} from "../../features/workspace/contracts";
import {
  navigation,
  type WorkspaceView,
  workspaceHref,
} from "../../features/workspace/navigation";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { humanLabel } from "../../features/workspace/presenters";

export function ProjectHeader({
  project,
  view,
  members = [],
}: {
  project: ProjectSummary;
  view: WorkspaceView;
  members?: Workspace["members"];
}) {
  return (
    <div className="mb-7">
      <div className="flex flex-col justify-between gap-5 xl:flex-row xl:items-start">
        <div className="min-w-0">
          <p className="mb-2 flex items-center gap-1.5 text-sm font-medium text-muted">
            <CircleCheck size={15} aria-hidden="true" />
            {navigation.find((item) => item.id === view)?.label}
          </p>
          <h1 className="page-title">{project.name}</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
            {project.description}
          </p>
        </div>
        <Button asChild variant="outline" className="self-start">
          <Link href={workspaceHref(project.id, "review")}>
            Open review inbox
            <ArrowUpRight data-icon="inline-end" aria-hidden="true" />
          </Link>
        </Button>
      </div>
      {members.length > 0 && (
        <div className="mt-5 flex flex-wrap items-center gap-x-3 gap-y-2">
          <div className="flex shrink-0 [&>*+*]:-ml-1.5">
            {members.map((member) => (
              <span
                key={member.id}
                title={`${member.name} · ${humanLabel(member.role)}`}
                className="flex size-7 items-center justify-center rounded-full border-2 border-canvas bg-accent-soft text-[13px] font-medium text-ink"
              >
                {member.name[0]}
              </span>
            ))}
          </div>
          <span className="whitespace-nowrap text-[13px] text-muted">
            {members.length} stakeholders
          </span>
          <span className="hidden text-line sm:inline" aria-hidden="true">
            ·
          </span>
          <Badge tone="success" variant="outline">
            Human-established baseline
          </Badge>
        </div>
      )}
    </div>
  );
}
