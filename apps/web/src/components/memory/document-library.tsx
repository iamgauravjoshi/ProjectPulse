"use client";
import * as Dialog from "@radix-ui/react-dialog";
import { useCallback, useRef, useState } from "react";
import {
  detailSchema,
  documentSchema,
  loadDocuments,
  memoryRequest,
  type DocumentSummary,
} from "../../features/memory/documents";
import { useResource } from "../../features/workspace/use-resource";
import { ErrorFeedback } from "../workspace/feedback";
export function DocumentLibrary({ projectId }: { projectId: string }) {
  const load = useCallback(
    (signal: AbortSignal) => loadDocuments(projectId, signal),
    [projectId],
  );
  const resource = useResource(load);
  const input = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [target, setTarget] = useState<{
    doc: DocumentSummary;
    remove: boolean;
  } | null>(null);
  async function index(doc: DocumentSummary) {
    setPending(true);
    setError("");
    setMessage("");
    try {
      const result = documentSchema.parse(
        await memoryRequest(
          `/api/workspace/projects/${projectId}/documents/${doc.id}/index`,
          { method: "POST" },
        ),
      );
      if (result.projectId !== projectId || result.id !== doc.id)
        throw new Error("Unexpected project evidence.");
      setMessage(
        `Document indexed: ${result.indexedChunks} chunks. Canonical state is unchanged.`,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Indexing failed.");
    } finally {
      setPending(false);
      resource.reload();
    }
  }
  async function upload(event: React.FormEvent) {
    event.preventDefault();
    const file = input.current?.files?.[0];
    if (!file) return;
    setError("");
    setMessage("");
    if (file.size === 0 || file.size > 5242880) {
      setError("Choose a nonempty file no larger than 5 MiB.");
      return;
    }
    setPending(true);
    try {
      const doc = documentSchema.parse(
        await memoryRequest(
          `/api/workspace/projects/${projectId}/documents?filename=${encodeURIComponent(file.name)}`,
          { method: "POST", body: file },
        ),
      );
      if (doc.projectId !== projectId)
        throw new Error("Unexpected project evidence.");
      setMessage(
        doc.duplicate
          ? "This file is already in the library. No duplicate was created."
          : "Document uploaded. Canonical state is unchanged.",
      );
      if (input.current) input.current.value = "";
      resource.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="rounded-xl border border-line bg-white p-5">
      <h2 className="text-lg font-semibold">Document library</h2>
      <p className="mt-2 text-sm text-muted">
        Project evidence with traceable text. Uploads never change confirmed
        state.
      </p>
      <form onSubmit={upload} className="my-6 flex flex-wrap items-end gap-3">
        <label className="block min-w-0 text-sm">
          Choose document
          <input
            ref={input}
            type="file"
            accept=".pdf,.docx,.txt,.md,.markdown"
            required
            disabled={pending}
            className="mt-2 block w-full max-w-xs text-sm"
          />
        </label>
        <button className="button-primary" disabled={pending}>
          {pending ? "Uploading…" : "Upload document"}
        </button>
      </form>
      <p className="mb-5 text-xs text-muted">
        PDF, DOCX, UTF-8 TXT or Markdown · Up to 5 MiB · Scanned PDFs need OCR.
      </p>
      {message && (
        <p
          role="status"
          aria-label="Library feedback"
          className="mb-4 text-sm text-accent"
        >
          {message}
        </p>
      )}
      {error && (
        <p
          role="alert"
          aria-label="Library error"
          className="mb-4 text-sm text-red-700"
        >
          {error}
        </p>
      )}
      {resource.status === "loading" ? (
        <p role="status" aria-label="Loading documents">
          Loading documents…
        </p>
      ) : resource.status === "error" ? (
        <ErrorFeedback
          title="Documents couldn’t load"
          retry={resource.reload}
          headingLevel={3}
        />
      ) : resource.data.length === 0 ? (
        <p className="py-8 text-sm text-muted">
          No documents yet. Upload project evidence to start.
        </p>
      ) : (
        <div className="divide-y divide-line">
          {resource.data.map((doc) => (
            <article
              key={doc.id}
              className="flex flex-wrap items-center justify-between gap-3 py-4"
            >
              <div>
                <h3 className="break-all font-medium">{doc.filename}</h3>
                <p className="mt-1 text-xs text-muted">
                  {doc.format.toUpperCase()} · {doc.byteSize} bytes ·{" "}
                  {doc.segmentCount} text sections · Evidence
                </p>
                <p className="mt-1 text-xs text-muted">
                  Index: {doc.indexStatus.toLowerCase()}{" "}
                  {doc.indexedChunks > 0
                    ? `· ${doc.indexedChunks} Gemini chunks`
                    : ""}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  className="button-secondary"
                  disabled={pending || doc.indexStatus === "INDEXED"}
                  onClick={() => index(doc)}
                >
                  Index<span className="sr-only"> {doc.filename}</span>
                </button>
                <button
                  className="button-secondary"
                  onClick={() => setTarget({ doc, remove: false })}
                >
                  Read<span className="sr-only"> {doc.filename}</span>
                </button>
                <button
                  className="button-secondary"
                  onClick={() => setTarget({ doc, remove: true })}
                >
                  Delete<span className="sr-only"> {doc.filename}</span>
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
      {target && (
        <DocumentDialog
          key={target.doc.id}
          projectId={projectId}
          target={target}
          close={() => setTarget(null)}
          changed={() => {
            setTarget(null);
            setMessage("Document deleted. Audit history is retained.");
            resource.reload();
          }}
        />
      )}
    </section>
  );
}
function DocumentDialog({
  projectId,
  target,
  close,
  changed,
}: {
  projectId: string;
  target: { doc: DocumentSummary; remove: boolean };
  close: () => void;
  changed: () => void;
}) {
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const load = useCallback(
    async (signal: AbortSignal) => {
      const detail = detailSchema.parse(
        await memoryRequest(
          `/api/workspace/projects/${projectId}/documents/${target.doc.id}`,
          { signal },
        ),
      );
      if (detail.projectId !== projectId || detail.id !== target.doc.id)
        throw new Error("Invalid evidence");
      return detail;
    },
    [projectId, target.doc.id],
  );
  const resource = useResource(load);
  async function remove() {
    setPending(true);
    try {
      await memoryRequest(
        `/api/workspace/projects/${projectId}/documents/${target.doc.id}`,
        { method: "DELETE" },
      );
      changed();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed.");
      setPending(false);
    }
  }
  return (
    <Dialog.Root
      open
      onOpenChange={(open) => {
        if (!open && !pending) close();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-ink/30" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[85dvh] w-[calc(100%-32px)] max-w-2xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
          <Dialog.Title className="break-all text-lg font-semibold">
            {target.remove ? "Delete document" : target.doc.filename}
          </Dialog.Title>
          <Dialog.Description className="mt-2 text-sm text-muted">
            {target.remove
              ? "Remove this evidence and its indexed chunks? Canonical state and audit history are retained."
              : "Source text is evidence, not confirmed project truth."}
          </Dialog.Description>
          {!target.remove &&
            (resource.status === "loading" ? (
              <p className="my-5">Loading text…</p>
            ) : resource.status === "error" ? (
              <ErrorFeedback
                title="Text couldn’t load"
                retry={resource.reload}
                headingLevel={3}
              />
            ) : (
              resource.data.segments.map((segment, index) => (
                <div key={index} className="my-5">
                  <p className="text-xs font-medium text-accent">
                    {segment.page
                      ? `Page ${segment.page}`
                      : (segment.section ?? "Document")}
                  </p>
                  <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6">
                    {segment.text}
                  </p>
                </div>
              ))
            ))}
          {error && (
            <p
              role="alert"
              aria-label="Library error"
              className="my-4 text-sm text-red-700"
            >
              {error}
            </p>
          )}
          <div className="mt-5 flex gap-3">
            {target.remove && (
              <button
                className="button-primary"
                disabled={pending}
                onClick={remove}
              >
                {pending ? "Deleting…" : "Confirm delete"}
              </button>
            )}
            <button
              className="button-secondary"
              disabled={pending}
              onClick={close}
            >
              {target.remove ? "Cancel" : "Close"}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
