"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import { Link2, Upload } from "lucide-react";
import {
  loadMeeting,
  meetingDetailSchema,
  meetingHref,
  elapsedTime,
  PAGE_SIZE,
  validateTranscriptFile,
  type MeetingDetail,
} from "../../features/meetings/contracts";
import { memoryRequest } from "../../features/memory/documents";
import type { Workspace } from "../../features/workspace/contracts";
import { useResource } from "../../features/workspace/use-resource";
import { Button } from "../ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "../ui/card";
import { FieldGroup, Field, FieldLabel, FieldDescription } from "../ui/field";
import { Input } from "../ui/input";
import {
  Alert,
  Empty,
  EmptyTitle,
  EmptyDescription,
  Skeleton,
  Separator,
} from "../ui/feedback";
import { ErrorFeedback } from "../workspace/feedback";
import { cn } from "../../lib/utils";

export function MeetingDetailView({
  projectId,
  meetingId,
  members,
  changed,
}: {
  projectId: string;
  meetingId: string;
  members: Workspace["members"];
  changed: () => void;
}) {
  const load = useCallback(
    (signal: AbortSignal) => loadMeeting(projectId, meetingId, signal),
    [projectId, meetingId],
  );
  const resource = useResource(load);
  return resource.status === "loading" ? (
    <Skeleton className="h-40" aria-label="Loading transcript" />
  ) : resource.status === "error" ? (
    <ErrorFeedback
      title="Meeting couldn’t load"
      retry={resource.reload}
      headingLevel={2}
    />
  ) : (
    <TranscriptViewer
      meeting={resource.data}
      members={members}
      changed={changed}
    />
  );
}
function TranscriptViewer({
  meeting,
  members,
  changed,
}: {
  meeting: MeetingDetail;
  members: Workspace["members"];
  changed: () => void;
}) {
  const params = useSearchParams();
  const target = params.get("utterance");
  const targetIndex = meeting.utterances.findIndex((u) => u.id === target);
  const targetPage = targetIndex < 0 ? 0 : Math.floor(targetIndex / PAGE_SIZE);
  const [manualPage, setManualPage] = useState<{
    target: string | null;
    page: number;
  } | null>(null);
  const page = manualPage?.target === target ? manualPage.page : targetPage;
  const pages = Math.max(1, Math.ceil(meeting.utterances.length / PAGE_SIZE));
  const [file, setFile] = useState<File | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    const invalid = validateTranscriptFile(file);
    if (invalid) {
      setError(invalid);
      return;
    }
    setPending(true);
    setError("");
    try {
      const result = meetingDetailSchema.parse(
        await memoryRequest(
          `/api/workspace/projects/${meeting.projectId}/meetings/${meeting.id}/transcript?filename=${encodeURIComponent(file.name)}`,
          { method: "POST", body: file },
        ),
      );
      if (result.id !== meeting.id || result.projectId !== meeting.projectId)
        throw new Error("Invalid meeting response.");
      changed();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed. Retry.");
      setPending(false);
    }
  }
  return (
    <Card>
      <CardHeader>
        <div className="min-w-0">
          <CardTitle className="min-w-0 max-w-full [overflow-wrap:anywhere]">
            {meeting.title}
          </CardTitle>
          <CardDescription>
            Transcript evidence · {meeting.utterances.length} utterances ·{" "}
            {meeting.participants.length} participants
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div>
          <h3 className="mb-2 text-sm font-semibold">Participants</h3>
          {meeting.participants.length ? (
            <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
              {meeting.participants.map((p) => (
                <li
                  key={p.id}
                  className="min-w-0 max-w-full [overflow-wrap:anywhere]"
                >
                  {p.displayName}
                  <span className="text-xs text-muted">
                    {" "}
                    ·{" "}
                    {p.speakerKey.startsWith("id:")
                      ? p.speakerKey.slice(3)
                      : "Name-only speaker"}{" "}
                    ·{" "}
                    {p.userId
                      ? `Linked to ${members.find((m) => m.id === p.userId)?.name ?? "project member"}`
                      : "Unlinked"}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">
              Speakers appear after upload. You can also register participants
              before uploading.
            </p>
          )}
        </div>
        <Separator />
        {!meeting.hasTranscript ? (
          <form onSubmit={upload}>
            <FieldGroup>
              <Field data-invalid={!!error}>
                <FieldLabel htmlFor={`transcript-file-${meeting.id}`}>
                  Transcript file
                </FieldLabel>
                <Input
                  ref={input}
                  id={`transcript-file-${meeting.id}`}
                  type="file"
                  accept=".txt,.json,.vtt"
                  disabled={pending}
                  aria-invalid={!!error}
                  onChange={(e) => {
                    const chosen = e.target.files?.[0];
                    if (chosen) {
                      setFile(chosen);
                      setError(validateTranscriptFile(chosen) ?? "");
                    }
                  }}
                />
                <FieldDescription>
                  UTF-8 TXT, JSON or VTT, up to 2 MiB. Select a file, then
                  upload explicitly.
                </FieldDescription>
              </Field>
              <details className="text-sm">
                <summary className="cursor-pointer text-accent-deep">
                  Transcript format examples
                </summary>
                <p className="my-2 text-xs text-muted">
                  TXT uses time | speaker | text. Leave time or speaker blank
                  when unknown. Use JSON speakerId to distinguish repeated
                  names.
                </p>
                <pre className="overflow-x-auto rounded-lg bg-surface-muted p-3 text-xs">
                  {
                    "00:01:10 | Sarah | We need SSO.\n | John | Timestamp unknown.\n | | Speaker unknown."
                  }
                </pre>
                <pre className="mt-2 overflow-x-auto rounded-lg bg-surface-muted p-3 text-xs">
                  {
                    '[{"speaker":"Sarah","speakerId":"sarah-1","timestamp":"00:01:10","text":"Need SSO."}]'
                  }
                </pre>
              </details>
              {file && (
                <p className="break-all text-xs text-muted">
                  Selected: {file.name}
                </p>
              )}
              {error && (
                <Alert variant="destructive" aria-label="Transcript error">
                  {error}
                </Alert>
              )}
              <div className="flex flex-wrap gap-3">
                <Button
                  type="submit"
                  disabled={pending || !file || !!validateTranscriptFile(file)}
                >
                  <Upload data-icon="inline-start" />
                  {pending ? "Uploading…" : "Upload transcript"}
                </Button>
                {file && (
                  <Button
                    variant="outline"
                    disabled={pending}
                    onClick={() => {
                      setFile(null);
                      setError("");
                      if (input.current) input.current.value = "";
                    }}
                  >
                    Clear selection
                  </Button>
                )}
              </div>
            </FieldGroup>
          </form>
        ) : (
          <>
            <p className="break-words text-xs text-muted">
              Source: {meeting.transcriptFilename}. Times are elapsed from the
              source; unknown values are preserved. Select an utterance link to
              highlight it and copy its URL.
            </p>
            {target && targetIndex < 0 && (
              <Alert variant="destructive" aria-label="Citation error">
                That utterance is not part of this meeting. Choose a valid
                source link below.
              </Alert>
            )}
            <ol start={page * PAGE_SIZE + 1} className="flex flex-col gap-3">
              {meeting.utterances
                .slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
                .map((u) => (
                  <li
                    key={u.id}
                    id={`utterance-${u.id}`}
                    tabIndex={-1}
                    aria-current={u.id === target ? "location" : undefined}
                    ref={(element) => {
                      if (element && u.id === target) {
                        element.scrollIntoView({ block: "center" });
                        element.focus({ preventScroll: true });
                      }
                    }}
                    className={cn(
                      "rounded-lg border border-line p-4",
                      u.id === target && "border-accent bg-accent-soft",
                    )}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="min-w-0 max-w-full text-sm font-semibold [overflow-wrap:anywhere]">
                        {u.sequence + 1}. {u.speaker}
                      </h3>
                      <Button asChild variant="link" size="sm">
                        <Link
                          href={meetingHref(
                            meeting.projectId,
                            meeting.id,
                            u.id,
                          )}
                          scroll={false}
                        >
                          <Link2 data-icon="inline-start" />
                          Link to utterance {u.sequence + 1}
                        </Link>
                      </Button>
                    </div>
                    <p className="text-xs text-muted">
                      {elapsedTime(u.timestampMs)}
                      {u.endMs !== null ? ` – ${elapsedTime(u.endMs)}` : ""}
                      {u.confidence !== null
                        ? ` · Source confidence ${Math.round(u.confidence * 100)}%`
                        : ""}
                    </p>
                    <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6">
                      {u.text}
                    </p>
                  </li>
                ))}
            </ol>
          </>
        )}
        {!meeting.hasTranscript && (
          <Empty compact>
            <EmptyTitle>Awaiting transcript</EmptyTitle>
            <EmptyDescription>
              Upload a file to preserve speaker-attributed meeting evidence
              here.
            </EmptyDescription>
          </Empty>
        )}
      </CardContent>
      {meeting.hasTranscript && (
        <CardFooter>
          <Button
            variant="outline"
            disabled={page === 0}
            onClick={() => setManualPage({ target, page: page - 1 })}
          >
            Previous utterances
          </Button>
          <p
            className="text-sm text-muted"
            role="status"
            aria-label="Transcript page"
          >
            Page {page + 1} of {pages}
          </p>
          <Button
            variant="outline"
            disabled={page >= pages - 1}
            onClick={() => setManualPage({ target, page: page + 1 })}
          >
            Next utterances
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
