"use client";
import Link from "next/link";
import { Search, LoaderCircle } from "lucide-react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "../ui/card";
import { FieldGroup, Field, FieldLabel } from "../ui/field";
import { InputGroup, InputGroupAddon, InputGroupInput } from "../ui/input";
import { Alert, Empty, EmptyDescription } from "../ui/feedback";
import { StatusBadge } from "../workspace/primitives";
import { useEffect, useRef, useState } from "react";
import type { Workspace } from "../../features/workspace/contracts";
import { humanLabel, ownerName } from "../../features/workspace/presenters";
import { workspaceHref } from "../../features/workspace/navigation";
import { searchContext, type SearchResult } from "../../features/memory/search";
import { labels } from "../../features/memory/forms";
export function ContextSearch({ workspace }: { workspace: Workspace }) {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function search(event: React.FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    controller.current?.abort();
    controller.current = new AbortController();
    setPending(true);
    setError("");
    setResult(null);
    try {
      setResult(
        await searchContext(
          workspace.project.id,
          query.trim(),
          controller.current.signal,
        ),
      );
    } catch (e) {
      if (!controller.current.signal.aborted)
        setError(e instanceof Error ? e.message : "Context search failed.");
    } finally {
      setPending(false);
    }
  }
  function fact(key: string, value: string | number | null) {
    if (value === null) return "Unassigned";
    if (key === "ownerId") return ownerName(workspace, String(value));
    if (key === "dependencyId")
      return (
        workspace.dependencies.find((x) => x.id === value)?.title ??
        "Linked dependency"
      );
    if (key === "blockedMilestoneId")
      return (
        workspace.milestones.find((x) => x.id === value)?.title ??
        "Linked milestone"
      );
    return key.toLowerCase().includes("status") || key === "severity"
      ? humanLabel(String(value))
      : String(value);
  }
  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>
            <Search size={18} aria-hidden="true" className="text-muted" />
            Search project context
          </CardTitle>
          <CardDescription>
            Find current baseline facts and traceable document evidence.
            Evidence does not establish project truth.
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={search} className="mb-6">
          <FieldGroup>
            <Field
              orientation="horizontal"
              data-disabled={pending || undefined}
            >
              <div className="flex min-w-0 flex-1 flex-col gap-2">
                <FieldLabel htmlFor="context-query">Context query</FieldLabel>
                <InputGroup>
                  <InputGroupAddon>
                    <Search aria-hidden="true" />
                  </InputGroupAddon>
                  <InputGroupInput
                    id="context-query"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    required
                    maxLength={400}
                    disabled={pending}
                    placeholder="What is the current SSO scope?"
                  />
                </InputGroup>
              </div>
              <Button type="submit" disabled={pending}>
                {pending ? (
                  <LoaderCircle
                    data-icon="inline-start"
                    className="motion-safe:animate-spin"
                  />
                ) : (
                  <Search data-icon="inline-start" />
                )}
                {pending ? "Searching…" : "Search context"}
              </Button>
            </Field>
          </FieldGroup>
        </form>
        {error && (
          <Alert
            variant="destructive"
            aria-label="Search error"
            className="mb-4"
          >
            {error}
          </Alert>
        )}
        {result && (
          <>
            <p
              role="status"
              aria-label="Search feedback"
              className="mb-5 text-sm text-muted"
            >
              {result.matches.length} results ·{" "}
              {result.semanticStatus === "ready"
                ? "Text and semantic search"
                : result.semanticStatus === "failed"
                  ? "Semantic search failed; showing text matches."
                  : result.semanticStatus === "not_indexed"
                    ? "Showing text matches. Index documents to enable semantic search."
                    : "Showing text matches. Semantic search is not configured yet."}
            </p>
            {result.matches.length === 0 && (
              <Empty compact>
                <EmptyDescription>
                  No relevant project context found. Try another query.
                </EmptyDescription>
              </Empty>
            )}
            <div className="flex flex-col gap-4">
              {result.matches.map((match) => (
                <article
                  key={`${match.kind}-${match.id}`}
                  className="rounded-lg border border-line p-4"
                >
                  <Badge
                    tone={match.kind === "record" ? "success" : "info"}
                    variant="outline"
                  >
                    {match.kind === "record"
                      ? "Current baseline"
                      : "Document evidence"}
                  </Badge>
                  <h3 className="mt-2 break-words font-medium">
                    {match.title}
                  </h3>
                  {match.kind === "record" ? (
                    <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                      {Object.entries(match.facts).map(([key, value]) => (
                        <div key={key}>
                          <dt className="inline">{labels[key] ?? key}: </dt>
                          <dd className="inline">
                            {value !== null &&
                            (key.toLowerCase().includes("status") ||
                              key === "severity") ? (
                              <StatusBadge
                                status={String(value)}
                                variant="outline"
                              />
                            ) : (
                              fact(key, value)
                            )}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  ) : (
                    <p className="mt-2 text-xs text-muted">
                      {match.page
                        ? `Page ${match.page}`
                        : (match.section ?? "Document")}{" "}
                      · Source characters {match.start + 1}–{match.end}
                    </p>
                  )}
                  <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-6">
                    {match.excerpt}
                  </p>
                  <Button asChild variant="link" className="mt-3">
                    <Link
                      href={
                        match.kind === "record"
                          ? `${workspaceHref(workspace.project.id, "state")}&kind=${match.entityType}#${match.id}`
                          : `${workspaceHref(workspace.project.id, "documents")}&document=${match.documentId}&segment=${match.segmentIndex}`
                      }
                    >
                      {match.kind === "record"
                        ? "View baseline"
                        : "Read source"}
                    </Link>
                  </Button>
                </article>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
