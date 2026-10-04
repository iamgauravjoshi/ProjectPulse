"use client";

import { Button } from "../ui/button";
import {
  Dialog,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "../ui/dialog";
import { ChevronRight, Menu, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import type { ProjectSummary } from "../../features/workspace/contracts";
import {
  navigation,
  type WorkspaceView,
  workspaceHref,
} from "../../features/workspace/navigation";
import { HelpDialog } from "./help-dialog";
import { cn } from "../../lib/utils";
import { Badge } from "../ui/badge";
import { Separator } from "../ui/feedback";
import { ProjectSelector } from "./project-selector";

type ShellProps = {
  projects: ProjectSummary[];
  selected?: ProjectSummary;
  view: WorkspaceView | null;
  loading?: boolean;
  onSelect: (id: string) => void;
  children: React.ReactNode;
};

function Sidebar({
  projects,
  selected,
  view,
  loading = false,
  onSelect,
  onNavigate,
}: Omit<ShellProps, "children"> & { onNavigate?: () => void }) {
  return (
    <div className="flex min-h-full flex-col">
      <div className="flex h-[72px] shrink-0 items-center gap-2.5 px-5">
        <span
          aria-hidden="true"
          className="flex size-8 items-center justify-center rounded-lg bg-accent text-base font-semibold text-white"
        >
          P
        </span>
        <span className="text-base font-semibold tracking-tight text-ink">
          ProjectPulse
        </span>
      </div>
      <div className="mb-4 px-5">
        <Badge variant="outline">Demo workspace</Badge>
      </div>
      <ProjectSelector
        projects={projects}
        selected={selected}
        loading={loading}
        onSelect={(id) => {
          onSelect(id);
          onNavigate?.();
        }}
      />
      <nav aria-label="Main navigation" className="flex flex-col gap-1 px-3">
        {navigation.map(({ id, label, icon: Icon }) => {
          const style = cn(
            "flex min-h-11 items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
            selected && view === id
              ? "bg-accent-soft text-accent-deep"
              : "text-muted hover:bg-surface-muted hover:text-ink",
          );
          return selected ? (
            <Link
              key={id}
              href={workspaceHref(selected.id, id)}
              className={style}
              aria-current={view === id ? "page" : undefined}
              onClick={onNavigate}
            >
              <Icon size={18} aria-hidden="true" />
              {label}
            </Link>
          ) : (
            <span
              key={id}
              aria-disabled="true"
              className={cn(style, "opacity-60")}
            >
              <Icon size={18} aria-hidden="true" />
              {label}
            </span>
          );
        })}
      </nav>
      <div className="mt-auto px-3 pb-4 pt-8">
        <HelpDialog />
        <div className="mt-4 px-3">
          <Separator className="mb-4" />
          <p className="text-[13px] leading-5 text-muted">
            Meetings are evidence.
            <br />
            Project state is the truth.
          </p>
        </div>
      </div>
    </div>
  );
}

export function AppShell(props: ShellProps) {
  const [open, setOpen] = useState(false);
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <a
        href="#workspace-content"
        className="sr-only z-[80] rounded bg-surface p-3 text-accent focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        Skip to workspace
      </a>
      <aside className="fixed inset-y-0 left-0 hidden w-60 overflow-y-auto border-r border-line bg-surface lg:block">
        <Sidebar {...props} />
      </aside>
      <div className="min-h-screen lg:ml-60">
        <header className="flex h-[72px] items-center justify-between gap-4 border-b border-line bg-surface px-4 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <DialogTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="shrink-0 lg:hidden"
                aria-label="Open navigation"
              >
                <Menu data-icon="inline-start" />
              </Button>
            </DialogTrigger>
            <div className="flex min-w-0 items-center gap-2 text-sm">
              <span className="shrink-0 text-muted">Projects</span>
              <ChevronRight
                size={14}
                className="shrink-0 text-muted"
                aria-hidden="true"
              />
              <span className="truncate font-medium text-ink">
                {props.selected?.name ?? "Workspace"}
              </span>
            </div>
          </div>
          <div
            className="flex shrink-0 items-center gap-2.5"
            aria-label="Sarah, local demo member"
          >
            <span className="hidden text-[13px] text-muted sm:inline">
              Demo member
            </span>
            <span
              title="Sarah · Product owner"
              className="flex size-8 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent"
            >
              S
            </span>
          </div>
        </header>
        <main
          id="workspace-content"
          tabIndex={-1}
          className="min-w-0 outline-none"
        >
          {props.children}
        </main>
      </div>
      <DialogContent size="sheet">
        <DialogTitle className="sr-only">Workspace navigation</DialogTitle>
        <DialogDescription className="sr-only">
          Choose a project and workspace view.
        </DialogDescription>
        <Sidebar {...props} onNavigate={() => setOpen(false)} />
        <DialogClose asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="absolute right-3 top-3.5"
            aria-label="Close navigation"
          >
            <X data-icon="inline-start" />
          </Button>
        </DialogClose>
      </DialogContent>
    </Dialog>
  );
}
