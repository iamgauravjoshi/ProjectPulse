"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Link2, RefreshCw, Sparkles } from "lucide-react";
import {
  type MeetingDetail,
  meetingHref,
  elapsedTime,
} from "../../features/meetings/contracts";
import {
  loadDeltas,
  compareDeltas,
  deltaOutcomes,
  outcomeLabels,
  type DeltaFilter,
} from "../../features/meetings/deltas";
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

const fieldLabels: Record<string, string> = {
  phase: "Phase",
  date: "Milestone date",
  dueDateText: "Due date",
  ownerMention: "Owner",
  title: "Title",
  description: "Description",
};

export function ProjectComparisons({
  meeting,
  revision,
}: {
  meeting: MeetingDetail;
  revision: number;
}) {
  const [page, setPage] = useState(1);
  const [outcome, setOutcome] = useState<DeltaFilter>("ALL");
  const load = useCallback(
    (signal: AbortSignal) => {
      void revision;
      return loadDeltas(meeting, signal, page, outcome);
    },
    [meeting, revision, page, outcome],
  );
  const resource = useResource(load);
  const [pending, setPending] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const citation = useSearchParams().get("utterance"),
    focused = useRef<string | null>(null);
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
  }, [resource.status, citation, meeting]);
  async function compare() {
    setPending(true);
    setError("");
    setMessage("");
    try {
      const result = await compareDeltas(meeting);
      if (!result.run?.lastError)
        setMessage(
          `${result.counts.processed} of ${result.counts.eligible} eligible candidates compared. ${result.counts.pending} remain.`,
        );
      setPage(1);
      resource.reload();
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Comparison failed. Refresh before retrying.",
      );
    } finally {
      setPending(false);
    }
  }
  let content, footer;
  if (resource.status === "loading")
    content = (
      <Skeleton className="h-32" aria-label="Loading project comparisons" />
    );
  else if (resource.status === "error")
    content = (
      <ErrorFeedback
        title="Project comparisons couldn’t load"
        retry={resource.reload}
        headingLevel={3}
      />
    );
  else {
    const data = resource.data,
      c = data.counts,
      run = data.run;
    const complete = !!run && c.pending === 0 && !data.stale;
    const action = data.stale
      ? "Compare current baseline"
      : complete
        ? "Comparison complete"
        : run?.lastError
          ? "Retry comparison"
          : run
            ? "Compare next candidate batch"
            : "Compare with project state";
    const pages = Math.max(1, Math.ceil(data.filteredCount / data.pageSize));
    content = (
      <>
        {data.prerequisite && (
          <Empty compact>
            <EmptyTitle>
              {data.prerequisite === "NO_TRANSCRIPT"
                ? "Awaiting meeting evidence"
                : data.prerequisite === "ANALYZE_RELEVANCE"
                  ? "Analyze current relevance first"
                  : "Extract current event candidates first"}
            </EmptyTitle>
            <EmptyDescription>
              Use Meeting Impact and Project Event Candidates above before
              comparing with project state.
            </EmptyDescription>
          </Empty>
        )}
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            ["Eligible candidates", c.eligible],
            ["Compared candidates", c.processed],
            ["Pending comparisons", c.pending],
            ["Possible changes", c.change],
            ["Consistent with baseline", c.same],
            ["Potential new items", c.new],
            ["Needs clarification", c.unclear],
          ].map(([label, value]) => (
            <div key={label}>
              <dt className="text-xs text-muted">{label}</dt>
              <dd className="mt-1 text-lg font-semibold tabular-nums">
                {value}
              </dd>
            </div>
          ))}
        </dl>
        {data.sourcePending > 0 && (
          <Alert aria-label="Partial source coverage">
            {data.sourcePending} source segments still need relevance analysis
            or extraction. Comparison completion covers eligible candidates
            only.
          </Alert>
        )}
        {data.stale && (
          <Alert aria-label="Stale comparisons">
            These comparisons use an earlier baseline, extraction or model.
            Analyze relevance and extract current events before comparing again.
          </Alert>
        )}
        {run && !run.contextComplete && (
          <Alert aria-label="Incomplete comparison context">
            Only selected project records were compared. Missing context cannot
            establish a new item.
          </Alert>
        )}
        {run?.lastError && (
          <Alert variant="destructive" aria-label="Comparison provider error">
            {run.lastError === "DELTA_PROVIDER_UNAVAILABLE"
              ? "Comparison AI is not configured. Pending candidates remain available for an explicit retry."
              : run.lastError === "DELTA_CONTEXT_CHANGED"
                ? "The baseline changed during comparison. That batch was discarded."
                : run.lastError === "DELTA_INPUT_CHANGED"
                  ? "The evidence changed during comparison. That batch was discarded."
                  : "Comparison could not complete. Saved results remain; refresh and retry pending candidates."}
          </Alert>
        )}
        {run?.processing && (
          <Alert aria-label="Comparison running">
            Comparison is running. Refresh shortly to check saved results.
          </Alert>
        )}
        {error && <Alert variant="destructive">{error}</Alert>}
        {message && <Alert variant="success">{message}</Alert>}
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={compare}
            disabled={
              pending || !!data.prerequisite || !!run?.processing || complete
            }
          >
            <Sparkles data-icon="inline-start" />
            {pending ? "Comparing…" : action}
          </Button>
          <Button
            variant="outline"
            onClick={resource.reload}
            disabled={pending}
          >
            <RefreshCw data-icon="inline-start" />
            Refresh comparisons
          </Button>
        </div>
        <Field>
          <FieldLabel htmlFor={`delta-outcome-${meeting.id}`}>
            Show comparison outcome
          </FieldLabel>
          <NativeSelect
            id={`delta-outcome-${meeting.id}`}
            value={outcome}
            onChange={(e) => {
              setOutcome(e.target.value as DeltaFilter);
              setPage(1);
            }}
          >
            <option value="ALL">All outcomes</option>
            {deltaOutcomes.map((o) => (
              <option key={o} value={o}>
                {outcomeLabels[o]}
              </option>
            ))}
          </NativeSelect>
        </Field>
        {data.items.length === 0 ? (
          <Empty compact>
            <EmptyTitle>
              {run && c.eligible === 0
                ? "No candidates to compare"
                : c.processed > 0
                  ? "No comparisons match this filter"
                  : "No saved comparisons"}
            </EmptyTitle>
            <EmptyDescription>
              Comparisons are interpretations for review. Confirmed project
              state stays unchanged.
            </EmptyDescription>
          </Empty>
        ) : (
          <ul
            className="flex flex-col gap-4"
            aria-label="Saved project comparisons"
          >
            {data.items.map((item) => (
              <li
                key={item.id}
                className="flex flex-col gap-3 rounded-lg border border-line p-4 break-words"
              >
                <div className="flex flex-wrap gap-2">
                  <Badge tone="neutral">Candidate</Badge>
                  <Badge
                    tone={
                      item.outcome === "CHANGE" || item.outcome === "UNCLEAR"
                        ? "warning"
                        : "neutral"
                    }
                  >
                    {outcomeLabels[item.outcome]}
                  </Badge>
                  <Badge tone="neutral">{humanLabel(item.statement)}</Badge>
                  <Badge tone="neutral">{humanLabel(item.kind)}</Badge>
                </div>
                <h3 className="text-sm font-semibold">{item.title}</h3>
                <p className="text-sm text-muted">{item.reason}</p>
                <p className="text-xs text-muted">
                  Comparator confidence {Math.round(item.confidence * 100)}%.
                  Interpretation requires human review.
                </p>
                {item.target ? (
                  <div className="flex flex-col gap-1 text-sm">
                    <p>Baseline record: {item.target.title}</p>
                    <p className="text-xs text-muted">
                      Compared version {item.target.version}
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-muted">
                    No canonical target established.
                  </p>
                )}
                {item.changes.length > 0 && (
                  <dl className="flex flex-col gap-3">
                    {item.changes.map((change) => (
                      <div
                        key={change.field}
                        className="grid gap-2 rounded-lg bg-surface-muted p-3 sm:grid-cols-3"
                      >
                        <dt className="text-sm font-medium">
                          {fieldLabels[change.field]}
                        </dt>
                        <dd className="min-w-0 break-words text-sm">
                          <span className="block text-xs text-muted">
                            Previous value
                          </span>
                          {change.previousValue === null
                            ? "Not stated"
                            : String(change.previousValue)}
                        </dd>
                        <dd className="min-w-0 break-words text-sm">
                          <span className="block text-xs text-muted">
                            Proposed wording
                          </span>
                          {change.proposedText}
                        </dd>
                      </div>
                    ))}
                  </dl>
                )}
                {item.evidence.map((e) => (
                  <div key={e.utteranceId} className="flex flex-col gap-2">
                    <blockquote className="border-l-2 border-accent/30 pl-3 text-sm">
                      {e.quote}
                    </blockquote>
                    <span className="text-xs text-muted">
                      {e.speaker} · {elapsedTime(e.timestampMs)}
                    </span>
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
                        View comparison source {e.sequence + 1}
                      </Link>
                    </Button>
                  </div>
                ))}
              </li>
            ))}
          </ul>
        )}
        {run && (
          <details className="text-xs text-muted">
            <summary className="cursor-pointer">Comparison usage</summary>
            <p className="mt-2 break-words">
              Model: {run.model} · Attempts: {run.apiCalls} · Reported usage:{" "}
              {run.usageReportedCalls} of {run.apiCalls} calls ·{" "}
              {run.usageReportedCalls > 0
                ? `${run.inputTokens} input and ${run.outputTokens} output tokens`
                : "Token usage unknown"}{" "}
              · Recorded latency: {run.latencyMs} ms
            </p>
          </details>
        )}
      </>
    );
    footer = (
      <>
        <p className="text-xs text-muted">
          Page {page} of {pages} · {data.filteredCount} comparisons
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={pending || page <= 1}
            onClick={() => setPage(page - 1)}
          >
            Previous comparisons
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={pending || page >= pages}
            onClick={() => setPage(page + 1)}
          >
            Next comparisons
          </Button>
        </div>
      </>
    );
  }
  return (
    <Card role="region" aria-label="Project comparisons">
      <CardHeader>
        <div>
          <CardTitle>Project Comparisons</CardTitle>
          <CardDescription>
            Compare meeting candidates with versioned project state. Proposed
            wording remains separate from confirmed values.
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">{content}</CardContent>
      {footer && (
        <CardFooter className="flex flex-wrap justify-between gap-3">
          {footer}
        </CardFooter>
      )}
    </Card>
  );
}
