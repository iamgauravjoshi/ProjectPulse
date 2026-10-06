"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Link2, RefreshCw, Sparkles } from "lucide-react";
import {
  elapsedTime,
  meetingHref,
  type MeetingDetail,
} from "../../features/meetings/contracts";
import {
  eventKinds,
  extractEvents,
  loadEvents,
  type EventFilter,
} from "../../features/meetings/events";
import { useResource } from "../../features/workspace/use-resource";
import { humanLabel } from "../../features/workspace/presenters";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "../ui/card";
import {
  Alert,
  Empty,
  EmptyTitle,
  EmptyDescription,
  Skeleton,
} from "../ui/feedback";
import { Field, FieldLabel } from "../ui/field";
import { NativeSelect } from "../ui/input";
import { ErrorFeedback } from "../workspace/feedback";

export function EventCandidates({
  meeting,
  revision,
  onExtracted,
}: {
  meeting: MeetingDetail;
  revision: number;
  onExtracted?: () => void;
}) {
  const [page, setPage] = useState(1);
  const [kind, setKind] = useState<EventFilter>("ALL");
  const load = useCallback(
    (signal: AbortSignal) => {
      void revision;
      return loadEvents(meeting, signal, page, kind);
    },
    [meeting, page, kind, revision],
  );
  const resource = useResource(load);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const citation = useSearchParams().get("utterance");
  const focused = useRef<string | null>(null);
  useEffect(() => {
    if (
      resource.status !== "ready" ||
      !citation ||
      citation === focused.current
    )
      return;
    const source = document.getElementById(`utterance-${citation}`);
    if (source && meeting.utterances.some((u) => u.id === citation)) {
      focused.current = citation;
      source.scrollIntoView({ block: "center" });
      source.focus({ preventScroll: true });
    }
  }, [citation, resource.status, meeting]);
  async function extract() {
    setPending(true);
    setError("");
    setMessage("");
    try {
      const result = await extractEvents(meeting);
      if (!result.extraction?.lastError)
        setMessage(
          `${result.counts.processed} of ${result.counts.eligible} eligible segments processed. ${result.counts.pending} remain.`,
        );
      setPage(1);
      resource.reload();
      onExtracted?.();
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Extraction failed. Refresh before retrying.",
      );
    } finally {
      setPending(false);
    }
  }
  let content;
  let footer;
  if (resource.status === "loading")
    content = (
      <Skeleton className="h-32" aria-label="Loading event candidates" />
    );
  else if (resource.status === "error")
    content = (
      <ErrorFeedback
        title="Event candidates couldn’t load"
        retry={resource.reload}
        headingLevel={3}
      />
    );
  else {
    const data = resource.data,
      c = data.counts,
      run = data.extraction;
    const complete = !!run && c.pending === 0 && !data.stale;
    const action = data.stale
      ? "Extract for current baseline"
      : complete
        ? "Extraction complete"
        : run?.lastError
          ? "Retry event extraction"
          : run
            ? "Extract next event batch"
            : "Extract event candidates";
    const pages = Math.max(1, Math.ceil(data.filteredCount / data.pageSize));
    content = (
      <>
        {data.prerequisite && (
          <Empty compact>
            <EmptyTitle>
              {data.prerequisite === "NO_TRANSCRIPT"
                ? "Awaiting meeting evidence"
                : "Analyze relevance first"}
            </EmptyTitle>
            <EmptyDescription>
              {data.prerequisite === "NO_TRANSCRIPT"
                ? "Upload a transcript to extract project event candidates."
                : "Use Meeting Impact to analyze the current baseline, then extract its project-relevant segments."}
            </EmptyDescription>
          </Empty>
        )}
        <dl
          className="grid grid-cols-2 gap-4 sm:grid-cols-3"
          aria-label="Event metrics"
        >
          {[
            ["Eligible segments", c.eligible],
            ["Processed segments", c.processed],
            ["Pending event segments", c.pending],
            ["Event candidates", c.candidates],
            ["Segments without events", c.noEvent],
            ["Low-confidence candidates", c.lowConfidence],
          ].map(([label, value]) => (
            <div
              key={label}
              className="min-w-0 rounded-lg bg-surface-muted p-3"
            >
              <dt className="text-xs text-muted">{label}</dt>
              <dd className="mt-1 text-2xl font-semibold">{value}</dd>
            </div>
          ))}
        </dl>
        <p className="text-xs text-muted">
          Coverage: {data.relevance.relevant} relevant, {data.relevance.ignored}{" "}
          ignored, {data.relevance.uncertain} uncertain and{" "}
          {data.relevance.pending} unclassified source segments. Only relevant
          segments are eligible. One source may yield several candidates.
        </p>
        {data.stale && (
          <Alert aria-label="Stale event candidates">
            These candidates use an earlier baseline or model. Analyze current
            relevance before extracting new candidates. Coverage above describes
            the saved run.
          </Alert>
        )}
        {data.relevance.pending > 0 && (
          <Alert aria-label="Partial relevance coverage">
            Relevance is incomplete. More eligible segments may become available
            after another relevance batch.
          </Alert>
        )}
        {run && !run.contextComplete && (
          <Alert>
            A selection of project context was used. Missing context can affect
            interpretation.
          </Alert>
        )}
        {run?.lastError && (
          <Alert variant="destructive" aria-label="Event provider error">
            {run.lastError === "EVENT_PROVIDER_UNAVAILABLE"
              ? "Event AI is not configured. Eligible segments remain pending; check provider configuration before retrying."
              : run.lastError === "EVENT_CONTEXT_CHANGED"
                ? "The baseline changed during extraction. That batch was discarded. Analyze current relevance first."
                : "Event extraction could not be completed. Saved candidates remain available; check provider access, then retry unfinished segments."}
          </Alert>
        )}
        {error && (
          <Alert variant="destructive" aria-label="Event extraction error">
            {error}
          </Alert>
        )}
        {message && (
          <Alert variant="success" aria-label="Event extraction feedback">
            {message}
          </Alert>
        )}
        {run?.processing && (
          <Alert>
            Extraction is running. Refresh shortly to check saved candidates.
          </Alert>
        )}
        <div className="flex flex-wrap gap-3">
          <Button
            disabled={
              pending || complete || !!data.prerequisite || run?.processing
            }
            onClick={extract}
          >
            <Sparkles data-icon="inline-start" />
            {pending ? "Extracting…" : action}
          </Button>
          <Button
            variant="outline"
            disabled={pending}
            onClick={() => {
              setError("");
              resource.reload();
            }}
          >
            <RefreshCw data-icon="inline-start" />
            Refresh candidates
          </Button>
        </div>
        {run && (
          <>
            <Field>
              <FieldLabel htmlFor={`event-kind-${meeting.id}`}>
                Show event kind
              </FieldLabel>
              <NativeSelect
                id={`event-kind-${meeting.id}`}
                value={kind}
                disabled={pending}
                onChange={(e) => {
                  setKind(e.target.value as EventFilter);
                  setPage(1);
                  setMessage("");
                  resource.reload();
                }}
              >
                <option value="ALL">All candidate kinds</option>
                {eventKinds.map((k) => (
                  <option key={k} value={k}>
                    {humanLabel(k)}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            {data.items.length ? (
              <ol
                className="flex flex-col gap-3"
                aria-label="Saved event candidates"
              >
                {data.items.map((item) => (
                  <li
                    key={item.id}
                    className="min-w-0 rounded-lg border border-line p-4"
                  >
                    <div className="flex flex-wrap gap-2">
                      <Badge tone="warning">Candidate</Badge>
                      <Badge tone="neutral" variant="outline">
                        {humanLabel(item.kind)}
                      </Badge>
                      <Badge tone="info" variant="outline">
                        {humanLabel(item.statement)}
                      </Badge>
                      {item.needsReview && (
                        <Badge tone="warning">Needs review</Badge>
                      )}
                    </div>
                    <h3 className="mt-3 text-sm font-semibold [overflow-wrap:anywhere]">
                      {item.title}
                    </h3>
                    <p className="mt-2 text-sm leading-6 [overflow-wrap:anywhere]">
                      {item.description}
                    </p>
                    <dl className="mt-3 grid gap-2 text-xs text-muted sm:grid-cols-2">
                      <div>
                        <dt>Said by</dt>
                        <dd className="[overflow-wrap:anywhere]">
                          {item.speaker}
                          {item.saidByUserId
                            ? " · linked project member"
                            : " · unlinked speaker"}
                        </dd>
                      </div>
                      <div>
                        <dt>Owner mention</dt>
                        <dd className="[overflow-wrap:anywhere]">
                          {item.ownerMention ?? "Unknown"}
                        </dd>
                      </div>
                      <div>
                        <dt>Due date wording</dt>
                        <dd className="[overflow-wrap:anywhere]">
                          {item.dueDateText ?? "Not stated"}
                        </dd>
                      </div>
                      <div>
                        <dt>Extractor confidence</dt>
                        <dd>{Math.round(item.confidence * 100)}%</dd>
                      </div>
                    </dl>
                    {item.evidence.map((e) => (
                      <div key={e.utteranceId} className="mt-3">
                        <blockquote className="whitespace-pre-wrap border-l-2 border-line pl-3 text-sm leading-6 [overflow-wrap:anywhere]">
                          {e.quote}
                        </blockquote>
                        <p className="mt-1 text-xs text-muted [overflow-wrap:anywhere]">
                          {e.speaker} · {elapsedTime(e.timestampMs)}
                        </p>
                        <Button asChild variant="link" size="sm">
                          <Link
                            href={meetingHref(
                              meeting.projectId,
                              meeting.id,
                              e.utteranceId,
                            )}
                            scroll={false}
                          >
                            <Link2 data-icon="inline-start" />
                            View event source {e.sequence + 1}
                          </Link>
                        </Button>
                      </div>
                    ))}
                  </li>
                ))}
              </ol>
            ) : (
              <Empty compact>
                <EmptyTitle>
                  {complete && kind === "ALL"
                    ? "No event candidates found"
                    : "No candidates to show"}
                </EmptyTitle>
                <EmptyDescription>
                  {complete && kind === "ALL"
                    ? "All currently eligible segments were processed. Confirmed project state is unchanged."
                    : "No saved candidates match this filter yet. Coverage above shows remaining work."}
                </EmptyDescription>
              </Empty>
            )}
            <details className="text-xs text-muted">
              <summary className="cursor-pointer">Extraction usage</summary>
              <p className="mt-2 [overflow-wrap:anywhere]">
                {run.model} · {run.apiCalls} AI request attempts ·{" "}
                {run.latencyMs} ms recorded latency · {run.inputTokens} input /{" "}
                {run.outputTokens} output tokens reported across{" "}
                {run.usageReportedCalls} of {run.apiCalls} attempts. Unreported
                usage is unknown.
              </p>
            </details>
          </>
        )}
      </>
    );
    if (run)
      footer = (
        <CardFooter>
          <Button
            variant="outline"
            disabled={pending || page === 1}
            onClick={() => {
              setPage((x) => x - 1);
              resource.reload();
            }}
          >
            Previous candidates
          </Button>
          <p
            className="text-sm text-muted"
            role="status"
            aria-label="Candidate page"
          >
            Page {page} of {pages}
          </p>
          <Button
            variant="outline"
            disabled={pending || page >= pages}
            onClick={() => {
              setPage((x) => x + 1);
              resource.reload();
            }}
          >
            Next candidates
          </Button>
        </CardFooter>
      );
  }
  return (
    <Card aria-label="Project event candidates">
      <CardHeader>
        <div>
          <CardTitle>Project Event Candidates</CardTitle>
          <CardDescription>
            AI interpretations with source evidence. Proposals, statements,
            questions and negations remain unconfirmed; extraction preserves
            confirmed project state.
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">{content}</CardContent>
      {footer}
    </Card>
  );
}
