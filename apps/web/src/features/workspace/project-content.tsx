"use client";

import { MessageSquare } from "lucide-react";
import { useCallback, useState } from "react";
import {
  ErrorFeedback,
  Feedback,
  WorkspaceSkeleton,
} from "../../components/workspace/feedback";
import { Overview } from "../../components/workspace/overview";
import { ProjectHeader } from "../../components/workspace/project-header";
import { RecordsView } from "../../components/workspace/records-view";
import { AttentionPanel } from "../../components/workspace/attention-panel";
import { ReviewInbox } from "../../components/workspace/review-inbox";
import { ContextSearch } from "../../components/memory/context-search";
import { DocumentLibrary } from "../../components/memory/document-library";
import { StateEditor } from "../../components/memory/state-editor";
import { loadWorkspace } from "./api";
import type { ProjectSummary } from "./contracts";
import type { WorkspaceView } from "./navigation";
import { useResource } from "./use-resource";

export function ProjectContent({
  project,
  view,
}: {
  project: ProjectSummary;
  view: WorkspaceView;
}) {
  const load = useCallback(
    (signal: AbortSignal) => loadWorkspace(project.id, signal),
    [project.id],
  );
  const resource = useResource(load);
  const [message, setMessage] = useState("");
  let content: React.ReactNode;
  if (resource.status === "loading") content = <WorkspaceSkeleton />;
  else if (resource.status === "error")
    content = (
      <ErrorFeedback
        title="Project state couldn’t load"
        retry={resource.reload}
        headingLevel={2}
      />
    );
  else if (view === "context")
    content = <ContextSearch workspace={resource.data} />;
  else if (view === "documents")
    content = <DocumentLibrary projectId={project.id} />;
  else if (view === "state")
    content = (
      <StateEditor
        workspace={resource.data}
        onChanged={(message) => {
          setMessage(message);
          resource.reload();
        }}
      />
    );
  else if (view === "overview")
    content = (
      <Overview
        workspace={resource.data}
        attention={<AttentionPanel workspace={resource.data} />}
      />
    );
  else if (view === "decisions" || view === "commitments" || view === "risks")
    content = <RecordsView key={view} workspace={resource.data} view={view} />;
  else if (view === "meetings")
    content = (
      <Feedback
        title="Meeting evidence starts here"
        description="Speaker-attributed conversations and the changes they suggest will live in this workspace."
        icon={MessageSquare}
        headingLevel={2}
      />
    );
  else content = <ReviewInbox workspace={resource.data} />;
  return (
    <div className="mx-auto max-w-[1440px] p-5 lg:p-8">
      <ProjectHeader
        project={resource.status === "ready" ? resource.data.project : project}
        view={view}
        members={resource.status === "ready" ? resource.data.members : []}
      />
      {message && view === "state" && (
        <p
          role="status"
          aria-label="Save feedback"
          className="mb-4 rounded-lg bg-accent-soft p-3 text-sm text-accent"
        >
          {message}
        </p>
      )}
      {content}
    </div>
  );
}
