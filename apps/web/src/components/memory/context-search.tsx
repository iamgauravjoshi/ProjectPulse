"use client";
import Link from "next/link";
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
    <section className="rounded-xl border border-line bg-white p-5">
      <h2 className="text-lg font-semibold">Search project context</h2>
      <p className="mt-2 text-sm text-muted">
        Find current baseline facts and traceable document evidence. Evidence
        does not establish project truth.
      </p>
      <form onSubmit={search} className="my-6 flex flex-wrap items-end gap-3">
        <label className="block grow text-sm font-medium">
          Context query
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            required
            maxLength={400}
            disabled={pending}
            className="mt-2 block w-full rounded-lg border border-line px-3 py-2"
            placeholder="What is the current SSO scope?"
          />
        </label>
        <button className="button-primary" disabled={pending}>
          {pending ? "Searching…" : "Search context"}
        </button>
      </form>
      {error && (
        <p
          role="alert"
          aria-label="Search error"
          className="my-4 text-sm text-danger"
        >
          {error}
        </p>
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
            <p className="py-6 text-sm text-muted">
              No relevant project context found. Try another query.
            </p>
          )}
          <div className="space-y-4">
            {result.matches.map((match) => (
              <article
                key={`${match.kind}-${match.id}`}
                className="rounded-lg border border-line p-4"
              >
                <p className="text-xs font-medium text-accent">
                  {match.kind === "record"
                    ? "Current baseline"
                    : "Document evidence"}
                </p>
                <h3 className="mt-2 break-words font-medium">{match.title}</h3>
                {match.kind === "record" ? (
                  <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                    {Object.entries(match.facts).map(([key, value]) => (
                      <div key={key}>
                        <dt className="inline">{labels[key] ?? key}: </dt>
                        <dd className="inline">{fact(key, value)}</dd>
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
                <Link
                  className="mt-3 inline-block text-sm font-medium text-accent"
                  href={
                    match.kind === "record"
                      ? `${workspaceHref(workspace.project.id, "state")}&kind=${match.entityType}#${match.id}`
                      : `${workspaceHref(workspace.project.id, "documents")}&document=${match.documentId}&segment=${match.segmentIndex}`
                  }
                >
                  {match.kind === "record" ? "View baseline" : "Read source"}
                </Link>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
