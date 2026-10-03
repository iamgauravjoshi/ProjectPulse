"use client";

import * as Select from "@radix-ui/react-select";
import { Check, ChevronsUpDown, Folder } from "lucide-react";
import type { ProjectSummary } from "../../features/workspace/contracts";

export function ProjectSelector({
  projects,
  selected,
  loading,
  onSelect,
}: {
  projects: ProjectSummary[];
  selected?: ProjectSummary;
  loading: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="px-4 pb-6">
      <p className="mb-2 px-1 text-[13px] font-medium text-muted">Project</p>
      <Select.Root
        value={selected?.id ?? ""}
        onValueChange={onSelect}
        disabled={loading || projects.length === 0}
      >
        <Select.Trigger
          aria-label="Project"
          title={selected?.name}
          className="flex w-full items-center gap-2 rounded-lg border border-line bg-white px-3 py-2.5 text-left text-sm text-ink hover:bg-surface-muted disabled:opacity-60"
        >
          <Folder
            size={16}
            className="shrink-0 text-muted"
            aria-hidden="true"
          />
          <span className="min-w-0 flex-1 truncate">
            <Select.Value
              placeholder={loading ? "Loading projects…" : "Choose a project"}
            />
          </span>
          <Select.Icon>
            <ChevronsUpDown size={14} className="text-muted" />
          </Select.Icon>
        </Select.Trigger>
        <Select.Portal>
          <Select.Content
            position="popper"
            sideOffset={5}
            className="z-[70] max-h-72 min-w-[var(--radix-select-trigger-width)] max-w-[calc(100vw-32px)] overflow-hidden rounded-lg border border-line bg-white p-1 shadow-lg"
          >
            <Select.Viewport>
              {projects.map((project) => (
                <Select.Item
                  value={project.id}
                  key={project.id}
                  className="relative cursor-pointer rounded-md py-2 pl-3 pr-8 text-sm text-ink outline-none data-[highlighted]:bg-accent-soft"
                >
                  <Select.ItemText>{project.name}</Select.ItemText>
                  <Select.ItemIndicator className="absolute right-2 top-2.5">
                    <Check size={15} className="text-accent" />
                  </Select.ItemIndicator>
                </Select.Item>
              ))}
            </Select.Viewport>
          </Select.Content>
        </Select.Portal>
      </Select.Root>
    </div>
  );
}
