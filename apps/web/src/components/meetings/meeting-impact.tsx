"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Filter, Link2, RefreshCw } from "lucide-react";
import {
  meetingHref,
  type MeetingDetail,
} from "../../features/meetings/contracts";
import {
  analyzeRelevance,
  loadRelevance,
  type RelevanceOutcome,
} from "../../features/meetings/relevance";
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
  EmptyDescription,
  EmptyTitle,
  Skeleton,
} from "../ui/feedback";
import { Field, FieldLabel } from "../ui/field";
import { NativeSelect } from "../ui/input";
import { ErrorFeedback } from "../workspace/feedback";

export function MeetingImpact({
  meeting,
  onAnalyzed,
}: {
  meeting: MeetingDetail;
  onAnalyzed?: () => void;
}) {
  return (
    <Card aria-label="Meeting impact">
      <CardHeader>
        <div>
          <CardTitle>Meeting Impact</CardTitle>
          <CardDescription>
            Relevance interpretations. Original evidence and confirmed project
            state are preserved.
          </CardDescription>
        </div>
      </CardHeader>
      {meeting.hasTranscript ? (
        <ImpactContent
          key={meeting.id}
          meeting={meeting}
          onAnalyzed={onAnalyzed}
        />
      ) : (
        <CardContent>
          <Empty compact>
            <EmptyTitle>Awaiting meeting evidence</EmptyTitle>
            <EmptyDescription>
              Upload a transcript to analyze project relevance.
            </EmptyDescription>
          </Empty>
        </CardContent>
      )}
    </Card>
  );
}
function ImpactContent({
  meeting,
  onAnalyzed,
}: {
  meeting: MeetingDetail;
  onAnalyzed?: () => void;
}) {
  const [page, setPage] = useState(1);
  const [outcome, setOutcome] = useState<RelevanceOutcome>("ALL");
  const load = useCallback(
    (signal: AbortSignal) => loadRelevance(meeting, signal, page, outcome),
    [meeting, page, outcome],
  );
  const resource = useResource(load);
  const citation = useSearchParams().get("utterance");
  const focusedCitation = useRef<string | null>(null);
  useEffect(() => {
    if (
      resource.status !== "ready" ||
      !citation ||
      citation === focusedCitation.current
    )
      return;
    const source = document.getElementById(`utterance-${citation}`);
    if (source && meeting.utterances.some((u) => u.id === citation)) {
      focusedCitation.current = citation;
      source.scrollIntoView({ block: "center" });
      source.focus({ preventScroll: true });
    }
  }, [citation, resource.status, meeting]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function analyze() {
    setPending(true);
    setError("");
    setMessage("");
    try {
      const result = await analyzeRelevance(meeting);
      onAnalyzed?.();
      if (!result.analysis?.lastError)
        setMessage(
          `${result.counts.analyzed} of ${result.counts.total} segments analyzed. ${result.counts.pending} remain.`,
        );
      setPage(1);
      resource.reload();
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Analysis failed. Refresh before retrying.",
      );
    } finally {
      setPending(false);
    }
  }
  if (resource.status === "loading")
    return (
      <CardContent>
        <Skeleton className="h-32" aria-label="Loading relevance" />
      </CardContent>
    );
  if (resource.status === "error")
    return (
      <CardContent>
        <ErrorFeedback
          title="Meeting impact couldn’t load"
          retry={resource.reload}
          headingLevel={3}
        />
      </CardContent>
    );
  const data = resource.data,
    c = data.counts;
  const pages = Math.max(1, Math.ceil(data.filteredCount / data.pageSize));
  const complete = data.analysis !== null && c.pending === 0 && !data.stale;
  const processing = data.analysis?.processing ?? false;
  const action = data.stale
    ? "Analyze current baseline"
    : complete
      ? "Analysis complete"
      : data.analysis?.lastError
        ? "Retry remaining segments"
        : data.analysis
          ? "Analyze next batch"
          : "Analyze relevance";
  const providerError = data.analysis?.lastError;
  return (
    <>
      <CardContent className="flex flex-col gap-4">
        <dl
          className="grid grid-cols-2 gap-4 sm:grid-cols-3"
          aria-label="Relevance metrics"
        >
          {[
            ["Conversation segments analyzed", c.analyzed],
            ["Project-relevant segments", c.relevant],
            ["Ignored segments", c.ignored],
            ["Needs review", c.uncertain],
            ["Pending segments", c.pending],
            ["Total segments", c.total],
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
        {data.ignoredPercent !== null && (
          <p
            className="text-sm"
            role="status"
            aria-label="Ignored conversation share"
          >
            <strong>{data.ignoredPercent}%</strong> of analyzed conversation
            segments ignored as non-project discussion.
            {c.pending > 0 && " This does not represent the whole meeting yet."}
          </p>
        )}
        <p className="text-xs text-muted">
          Counts cover source segments, not meeting duration. Low-confidence
          classifications stay in Needs review.
        </p>
        {data.stale && (
          <Alert aria-label="Stale relevance">
            The baseline has changed. These saved interpretations use earlier
            context; analyze the current baseline before relying on them.
          </Alert>
        )}
        {data.analysis && !data.analysis.contextComplete && (
          <Alert aria-label="Selected context notice">
            A selection of current project context was used. Missing context can
            leave segments uncertain.
          </Alert>
        )}
        {providerError && (
          <Alert variant="destructive" aria-label="Relevance provider error">
            {providerError === "RELEVANCE_UNAVAILABLE"
              ? "AI classification is not configured. Saved rule results are available; remaining segments have not been classified."
              : providerError === "RELEVANCE_CONTEXT_CHANGED"
                ? "The baseline changed during analysis. That AI batch was discarded; analyze the current baseline."
                : "AI analysis could not be completed. Saved results remain available. Check provider access or configuration, then retry remaining segments."}
          </Alert>
        )}
        {error && (
          <Alert variant="destructive" aria-label="Relevance error">
            {error}
          </Alert>
        )}
        {message && (
          <Alert variant="success" aria-label="Relevance feedback">
            {message}
          </Alert>
        )}
        {processing && (
          <Alert>
            Analysis is in progress. Refresh shortly to check saved results.
          </Alert>
        )}
        <div className="flex flex-wrap gap-3">
          <Button
            disabled={pending || complete || processing}
            onClick={analyze}
          >
            <Filter data-icon="inline-start" />
            {pending ? "Analyzing…" : action}
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
            Refresh impact
          </Button>
        </div>
        {!data.analysis && (
          <Empty compact>
            <EmptyTitle>Relevance has not been analyzed</EmptyTitle>
            <EmptyDescription>
              Analyze explicitly to separate project discussion from personal
              conversation.
            </EmptyDescription>
          </Empty>
        )}
        {data.analysis && (
          <>
            <Field>
              <FieldLabel htmlFor={`relevance-outcome-${meeting.id}`}>
                Show relevance
              </FieldLabel>
              <NativeSelect
                id={`relevance-outcome-${meeting.id}`}
                value={outcome}
                disabled={pending}
                onChange={(e) => {
                  setOutcome(e.target.value as RelevanceOutcome);
                  setPage(1);
                  resource.reload();
                  setMessage("");
                }}
              >
                <option value="ALL">All analyzed segments</option>
                <option value="RELEVANT">Project relevant</option>
                <option value="IGNORED">Ignored</option>
                <option value="UNCERTAIN">Needs review</option>
              </NativeSelect>
            </Field>
            {data.items.length ? (
              <ol
                className="flex flex-col gap-3"
                aria-label="Relevance interpretations"
              >
                {data.items.map((item) => (
                  <li
                    key={item.utteranceId}
                    className="min-w-0 rounded-lg border border-line p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="min-w-0 text-sm font-semibold [overflow-wrap:anywhere]">
                        {item.sequence + 1}. {item.speaker}
                      </h3>
                      <Badge
                        tone={
                          item.outcome === "RELEVANT"
                            ? "info"
                            : item.outcome === "UNCERTAIN"
                              ? "warning"
                              : "neutral"
                        }
                      >
                        {item.outcome === "UNCERTAIN"
                          ? "Needs review"
                          : humanLabel(item.outcome)}
                      </Badge>
                    </div>
                    <p className="mt-2 break-words text-sm leading-6">
                      {item.text}
                    </p>
                    <p className="mt-2 break-words text-sm text-muted">
                      {item.reason}
                    </p>
                    <p className="mt-2 text-xs text-muted">
                      Classifier confidence {Math.round(item.confidence * 100)}%
                      · {item.method === "GEMINI" ? "AI" : "Rule"}
                      {item.relatedEntityTypes.length > 0
                        ? ` · ${item.relatedEntityTypes.map(humanLabel).join(", ")}`
                        : ""}
                    </p>
                    <Button asChild variant="link" size="sm">
                      <Link
                        href={meetingHref(
                          meeting.projectId,
                          meeting.id,
                          item.utteranceId,
                        )}
                        scroll={false}
                      >
                        <Link2 data-icon="inline-start" />
                        View source utterance {item.sequence + 1}
                      </Link>
                    </Button>
                  </li>
                ))}
              </ol>
            ) : (
              <Empty compact>
                <EmptyDescription>
                  No analyzed segments match this filter.
                </EmptyDescription>
              </Empty>
            )}
            <details className="text-xs text-muted">
              <summary className="cursor-pointer">Analysis usage</summary>
              <p className="mt-2 break-words">
                {data.analysis.apiCalls} AI request attempts ·{" "}
                {data.analysis.latencyMs} ms recorded provider latency ·{" "}
                {data.analysis.inputTokens} input / {data.analysis.outputTokens}{" "}
                output tokens reported across {data.analysis.usageReportedCalls}{" "}
                of {data.analysis.apiCalls} attempts. Unreported usage is
                unknown.
              </p>
            </details>
          </>
        )}
      </CardContent>
      {data.analysis && (
        <CardFooter>
          <Button
            variant="outline"
            disabled={pending || page === 1}
            onClick={() => {
              setPage((x) => x - 1);
              resource.reload();
            }}
          >
            Previous relevance
          </Button>
          <p
            className="text-sm text-muted"
            role="status"
            aria-label="Relevance page"
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
            Next relevance
          </Button>
        </CardFooter>
      )}
    </>
  );
}
