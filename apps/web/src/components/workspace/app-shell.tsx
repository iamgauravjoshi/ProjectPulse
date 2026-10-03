"use client";

import * as Dialog from "@radix-ui/react-dialog";
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
    <div className="flex h-full flex-col">
      <div className="flex h-[72px] shrink-0 items-center gap-2.5 px-5">
        <span
          aria-hidden="true"
          className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-base font-semibold text-white"
        >
          P
        </span>
        <span className="text-base font-semibold tracking-tight text-ink">
          ProjectPulse
        </span>
      </div>
      <div className="mb-4 px-5">
        <span className="rounded-md bg-surface-muted px-2 py-1 text-[13px] font-medium text-muted">
          Demo workspace
        </span>
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
      <nav aria-label="Main navigation" className="space-y-1 px-3">
        {navigation.map(({ id, label, icon: Icon }) => {
          const style = `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${selected && view === id ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface-muted hover:text-ink"}`;
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
              className={`${style} opacity-60`}
            >
              <Icon size={18} aria-hidden="true" />
              {label}
            </span>
          );
        })}
      </nav>
      <div className="mt-auto px-3 pb-4 pt-8">
        <HelpDialog />
        <div className="mt-4 border-t border-line px-3 pt-4">
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
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <a
        href="#workspace-content"
        className="sr-only z-[80] rounded bg-white p-3 text-accent focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        Skip to workspace
      </a>
      <aside className="fixed inset-y-0 left-0 hidden w-60 border-r border-line bg-white lg:block">
        <Sidebar {...props} />
      </aside>
      <div className="min-h-screen lg:ml-60">
        <header className="flex h-[72px] items-center justify-between gap-4 border-b border-line bg-white px-4 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <Dialog.Trigger asChild>
              <button
                type="button"
                className="icon-button shrink-0 lg:hidden"
                aria-label="Open navigation"
              >
                <Menu size={20} />
              </button>
            </Dialog.Trigger>
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
              className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent"
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
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-ink/30" />
        <Dialog.Content className="fixed inset-y-0 left-0 z-50 w-[min(320px,calc(100%-32px))] border-r border-line bg-white">
          <Dialog.Title className="sr-only">Workspace navigation</Dialog.Title>
          <Dialog.Description className="sr-only">
            Choose a project and workspace view.
          </Dialog.Description>
          <Sidebar {...props} onNavigate={() => setOpen(false)} />
          <Dialog.Close asChild>
            <button
              type="button"
              className="icon-button absolute right-3 top-5"
              aria-label="Close navigation"
            >
              <X size={18} />
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
