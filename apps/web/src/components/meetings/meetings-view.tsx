"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { BookOpen, Plus, Trash2, Users } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import {
  loadMeetings,
  meetingHref,
  type MeetingSummary,
} from "../../features/meetings/contracts";
import type { Workspace } from "../../features/workspace/contracts";
import { useResource } from "../../features/workspace/use-resource";
import { workspaceHref } from "../../features/workspace/navigation";
import { Button } from "../ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "../ui/card";
import {
  Alert,
  Empty,
  EmptyTitle,
  EmptyDescription,
  Skeleton,
} from "../ui/feedback";
import { ErrorFeedback } from "../workspace/feedback";
import { MeetingDialog } from "./meeting-dialog";
import { MeetingDetailView } from "./transcript-viewer";

export function MeetingsView({ workspace }: { workspace: Workspace }) {
  const projectId = workspace.project.id;
  const params = useSearchParams();
  const router = useRouter();
  const selected = params.get("meeting");
  const load = useCallback(
    (signal: AbortSignal) => loadMeetings(projectId, signal),
    [projectId],
  );
  const resource = useResource(load);
  const [dialog, setDialog] = useState<{
    mode: "create" | "participant" | "delete";
    meeting?: MeetingSummary;
  } | null>(null);
  const [message, setMessage] = useState("");
  const [revision, setRevision] = useState(0);
  const opener = useRef<HTMLElement | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  function open(
    mode: "create" | "participant" | "delete",
    meeting?: MeetingSummary,
  ) {
    opener.current = document.activeElement as HTMLElement;
    setDialog({ mode, meeting });
  }
  function changed(message: string, id?: string) {
    setDialog(null);
    setMessage(message);
    setRevision((x) => x + 1);
    resource.reload();
    if (id !== undefined)
      router.replace(
        id ? meetingHref(projectId, id) : workspaceHref(projectId, "meetings"),
        { scroll: false },
      );
  }
  return (
    <div className="flex flex-col gap-5">
      <Card>
        <CardHeader>
          <div>
            <CardTitle ref={heading} tabIndex={-1}>
              Meetings
            </CardTitle>
            <CardDescription>
              Speaker-attributed evidence. Uploads do not change confirmed
              project state.
            </CardDescription>
          </div>
          <Button onClick={() => open("create")}>
            <Plus data-icon="inline-start" />
            New meeting
          </Button>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {message && (
            <Alert variant="success" aria-label="Meeting feedback">
              {message}
            </Alert>
          )}
          {resource.status === "loading" ? (
            <Skeleton className="h-24" aria-label="Loading meetings" />
          ) : resource.status === "error" ? (
            <ErrorFeedback
              title="Meetings couldn’t load"
              retry={resource.reload}
              headingLevel={3}
            />
          ) : resource.data.length === 0 ? (
            <Empty compact>
              <EmptyTitle>No meeting evidence yet</EmptyTitle>
              <EmptyDescription>
                Create a meeting, then upload a speaker-attributed TXT, JSON or
                VTT transcript.
              </EmptyDescription>
            </Empty>
          ) : (
            <div className="flex flex-col gap-3">
              {resource.data.map((meeting) => (
                <article
                  key={meeting.id}
                  className="flex flex-col gap-3 rounded-lg border border-line p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <h3 className="break-words text-sm font-semibold">
                      {meeting.title}
                    </h3>
                    <p className="mt-1 break-words text-xs text-muted">
                      {meeting.startedAt
                        ? new Date(meeting.startedAt).toLocaleString()
                        : "Meeting time unknown"}{" "}
                      ·{" "}
                      {meeting.hasTranscript
                        ? "Transcript uploaded"
                        : "Awaiting transcript"}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button asChild variant="outline" size="sm">
                      <Link
                        href={meetingHref(projectId, meeting.id)}
                        scroll={false}
                      >
                        <BookOpen data-icon="inline-start" />
                        Open<span className="sr-only"> {meeting.title}</span>
                      </Link>
                    </Button>
                    {!meeting.hasTranscript && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => open("participant", meeting)}
                      >
                        <Users data-icon="inline-start" />
                        Add participant
                        <span className="sr-only"> {meeting.title}</span>
                      </Button>
                    )}
                    <Button
                      variant="destructive-outline"
                      size="sm"
                      onClick={() => open("delete", meeting)}
                    >
                      <Trash2 data-icon="inline-start" />
                      Delete<span className="sr-only"> {meeting.title}</span>
                    </Button>
                  </div>
                </article>
              ))}
            </div>
          )}
          {resource.status === "ready" && resource.data.length === 200 && (
            <p className="text-xs text-muted">
              Showing the latest 200 meetings. Saved transcript links also open
              older meetings.
            </p>
          )}
        </CardContent>
      </Card>
      {selected && (
        <MeetingDetailView
          key={`${selected}-${revision}`}
          projectId={projectId}
          meetingId={selected}
          members={workspace.members}
          changed={() =>
            changed(
              "Transcript uploaded. Confirmed project state is unchanged.",
            )
          }
        />
      )}
      {dialog && (
        <MeetingDialog
          workspace={workspace}
          mode={dialog.mode}
          meeting={dialog.meeting}
          close={() => setDialog(null)}
          changed={changed}
          opener={opener}
          fallback={heading}
        />
      )}
    </div>
  );
}
