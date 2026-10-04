"use client";
import { Folder } from "lucide-react";
import type { ProjectSummary } from "../../features/workspace/contracts";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";

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
      <Select
        value={selected?.id ?? ""}
        onValueChange={onSelect}
        disabled={loading || projects.length === 0}
      >
        <SelectTrigger aria-label="Project" title={selected?.name}>
          <Folder
            size={16}
            className="shrink-0 text-muted"
            aria-hidden="true"
          />
          <span className="min-w-0 flex-1 truncate">
            <SelectValue
              placeholder={loading ? "Loading projects…" : "Choose a project"}
            />
          </span>
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            {projects.map((project) => (
              <SelectItem value={project.id} key={project.id}>
                {project.name}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
    </div>
  );
}
