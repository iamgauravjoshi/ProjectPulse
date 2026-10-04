"use client";
import {
  BookOpen,
  FileText,
  ScanText,
  Trash2,
  Upload,
  LoaderCircle,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogHeader,
  DialogFooter,
} from "../ui/dialog";
import { Button } from "../ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "../ui/card";
import { FieldGroup } from "../ui/field";
import { Alert, Empty, EmptyDescription, Skeleton } from "../ui/feedback";
import { Badge } from "../ui/badge";
import { StatusBadge } from "../workspace/primitives";
import { DocumentPicker } from "./document-picker";
import { useRouter, useSearchParams } from "next/navigation";
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
  const params = useSearchParams();
  const router = useRouter();
  const load = useCallback(
    (signal: AbortSignal) => loadDocuments(projectId, signal),
    [projectId],
  );
  const resource = useResource(load);
  const [file, setFile] = useState<File | null>(null);
  const opener = useRef<HTMLElement | null>(null);
  const libraryHeading = useRef<HTMLHeadingElement>(null);
  const [busy, setBusy] = useState<"upload" | "index" | null>(null);
  const pending = busy !== null;
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [manualTarget, setTarget] = useState<{
    doc: DocumentSummary;
    remove: boolean;
  } | null>(null);
  const linked =
    resource.status === "ready"
      ? resource.data.find((x) => x.id === params.get("document"))
      : undefined;
  const target =
    manualTarget ?? (linked ? { doc: linked, remove: false } : null);
  function close() {
    setTarget(null);
    if (params.has("document")) {
      const next = new URLSearchParams(params.toString());
      next.delete("document");
      next.delete("segment");
      router.replace(`/?${next}`);
    }
  }
  async function index(doc: DocumentSummary) {
    setBusy("index");
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
      setBusy(null);
      resource.reload();
    }
  }
  async function upload(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;
    setError("");
    setMessage("");
    if (file.size === 0 || file.size > 5242880) {
      setError("Choose a nonempty file no larger than 5 MiB.");
      return;
    }
    setBusy("upload");
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
      setFile(null);
      resource.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setBusy(null);
    }
  }
  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle ref={libraryHeading} tabIndex={-1}>
            <FileText size={18} aria-hidden="true" className="text-muted" />
            Document library
          </CardTitle>
          <CardDescription>
            Project evidence with traceable text. Uploads never change confirmed
            state.
          </CardDescription>
        </div>
        <Badge tone="info" variant="outline">
          Evidence library
        </Badge>
      </CardHeader>
      <CardContent>
        <form onSubmit={upload} className="mb-6">
          <FieldGroup>
            <DocumentPicker
              file={file}
              disabled={pending}
              onChange={setFile}
              onError={setError}
            />
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-muted">
                Files stay separate from confirmed project state.
              </p>
              <Button type="submit" disabled={pending || !file}>
                {busy === "upload" ? (
                  <LoaderCircle
                    data-icon="inline-start"
                    className="motion-safe:animate-spin"
                  />
                ) : (
                  <Upload data-icon="inline-start" />
                )}
                {busy === "upload" ? "Uploading…" : "Upload document"}
              </Button>
            </div>
          </FieldGroup>
        </form>
        {message && (
          <Alert
            variant="success"
            aria-label="Library feedback"
            className="mb-4"
          >
            {message}
          </Alert>
        )}
        {error && (
          <Alert
            variant="destructive"
            aria-label="Library error"
            className="mb-4"
          >
            {error}
          </Alert>
        )}
        {resource.status === "loading" ? (
          <div
            role="status"
            aria-label="Loading documents"
            className="flex flex-col gap-3"
          >
            <span className="sr-only">Loading documents…</span>
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        ) : resource.status === "error" ? (
          <ErrorFeedback
            title="Documents couldn’t load"
            retry={resource.reload}
            headingLevel={3}
          />
        ) : resource.data.length === 0 ? (
          <Empty compact>
            <EmptyDescription>
              No documents yet. Upload project evidence to start.
            </EmptyDescription>
          </Empty>
        ) : (
          <div className="divide-y divide-line">
            {resource.data.map((doc) => (
              <article
                key={doc.id}
                className="flex flex-col justify-between gap-4 py-5 xl:flex-row xl:items-start"
              >
                <div className="min-w-0">
                  <h3 className="break-all font-medium">{doc.filename}</h3>
                  <p className="mt-1 text-xs text-muted">
                    {doc.format.toUpperCase()} · {doc.byteSize} bytes ·{" "}
                    {doc.segmentCount} text sections · Evidence
                  </p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <span className="text-xs text-muted">Index:</span>
                    <StatusBadge status={doc.indexStatus} />
                    <Badge tone="info" variant="outline">
                      Document evidence
                    </Badge>
                    {doc.indexedChunks > 0 && (
                      <span className="text-xs text-muted">
                        {doc.indexedChunks} indexed chunks
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={pending || doc.indexStatus === "INDEXED"}
                    onClick={() => index(doc)}
                  >
                    <ScanText data-icon="inline-start" />
                    Index<span className="sr-only"> {doc.filename}</span>
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      opener.current = document.activeElement as HTMLElement;
                      setTarget({ doc, remove: false });
                    }}
                  >
                    <BookOpen data-icon="inline-start" />
                    Read<span className="sr-only"> {doc.filename}</span>
                  </Button>
                  <Button
                    variant="destructive-outline"
                    size="sm"
                    disabled={pending}
                    onClick={() => {
                      opener.current = document.activeElement as HTMLElement;
                      setTarget({ doc, remove: true });
                    }}
                  >
                    <Trash2 data-icon="inline-start" />
                    Delete<span className="sr-only"> {doc.filename}</span>
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </CardContent>
      {target && (
        <DocumentDialog
          key={`${target.doc.id}-${target.remove}`}
          opener={opener}
          fallback={libraryHeading}
          projectId={projectId}
          target={target}
          close={close}
          segment={Number(params.get("segment") ?? 0)}
          changed={() => {
            close();
            setMessage("Document deleted. Audit history is retained.");
            resource.reload();
          }}
        />
      )}
    </Card>
  );
}
function DocumentDialog({
  projectId,
  target,
  close,
  changed,
  segment: selectedSegment,
  opener,
  fallback,
}: {
  projectId: string;
  target: { doc: DocumentSummary; remove: boolean };
  close: () => void;
  changed: () => void;
  segment: number;
  opener: React.RefObject<HTMLElement | null>;
  fallback: React.RefObject<HTMLHeadingElement | null>;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
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
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !pending) close();
      }}
    >
      <DialogContent
        onOpenAutoFocus={(e) => {
          e.preventDefault();
          heading.current?.focus();
        }}
        size="wide"
        onCloseAutoFocus={(e) => {
          e.preventDefault();
          (opener.current?.isConnected
            ? opener.current
            : fallback.current
          )?.focus();
        }}
      >
        <DialogHeader>
          <DialogTitle tabIndex={-1} ref={heading} className="break-all">
            {target.remove ? "Delete document" : target.doc.filename}
          </DialogTitle>
          <DialogDescription>
            {target.remove
              ? "Remove this evidence and its indexed chunks? Canonical state and audit history are retained."
              : "Source text is evidence, not confirmed project truth."}
          </DialogDescription>
        </DialogHeader>
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
              <div
                key={index}
                ref={(element) => {
                  if (index === selectedSegment)
                    element?.scrollIntoView({ block: "center" });
                }}
                className="my-5"
              >
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
          <Alert
            variant="destructive"
            aria-label="Library error"
            className="my-4"
          >
            {error}
          </Alert>
        )}
        <DialogFooter>
          {target.remove && (
            <Button variant="destructive" disabled={pending} onClick={remove}>
              {pending ? "Deleting…" : "Confirm delete"}
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            disabled={pending}
            onClick={close}
          >
            {target.remove ? "Cancel" : "Close"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
