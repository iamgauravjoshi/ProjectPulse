"use client";

import { Button } from "../../components/ui/button";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AppShell } from "../../components/workspace/app-shell";
import {
  ErrorFeedback,
  Feedback,
  WorkspaceSkeleton,
} from "../../components/workspace/feedback";
import { loadProjects } from "./api";
import { resolveView, workspaceHref } from "./navigation";
import { ProjectContent } from "./project-content";
import { useResource } from "./use-resource";

export function WorkspaceScreen() {
  const projects = useResource(loadProjects);
  const params = useSearchParams();
  const router = useRouter();
  const list = projects.status === "ready" ? projects.data : [];
  const requested = params.get("project");
  const selected = requested ? list.find((p) => p.id === requested) : list[0];
  const view = resolveView(params.get("view"));
  let content: React.ReactNode;
  if (projects.status === "loading") content = <WorkspaceSkeleton />;
  else if (projects.status === "error")
    content = (
      <ErrorFeedback title="Projects couldn’t load" retry={projects.reload} />
    );
  else if (list.length === 0)
    content = (
      <Feedback
        title="No projects yet"
        description="A project gives your conversations a trusted baseline."
        action={
          <Button type="button" variant="outline" onClick={projects.reload}>
            Refresh projects
          </Button>
        }
      />
    );
  else if (!selected)
    content = (
      <Feedback
        title="Project unavailable"
        description="Choose a project to continue. You may not have access to this workspace."
        action={
          <Button
            type="button"
            onClick={() => router.push(workspaceHref(list[0].id))}
          >
            Choose available project
          </Button>
        }
      />
    );
  else if (!view)
    content = (
      <Feedback
        title="Page not found"
        description="This workspace view isn’t available."
        action={
          <Button asChild>
            <Link href={workspaceHref(selected.id)}>Back to overview</Link>
          </Button>
        }
      />
    );
  else
    content = (
      <ProjectContent key={selected.id} project={selected} view={view} />
    );
  return (
    <AppShell
      projects={list}
      selected={selected}
      view={view}
      loading={projects.status === "loading"}
      onSelect={(id) => router.push(workspaceHref(id, view ?? "overview"))}
    >
      {content}
    </AppShell>
  );
}
