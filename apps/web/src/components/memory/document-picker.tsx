"use client";
import { FileText, UploadCloud, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { cn } from "../../lib/utils";
import { Button } from "../ui/button";
import { Field, FieldDescription, FieldLabel } from "../ui/field";
import { validateDocumentFile } from "../../features/memory/documents";

export function DocumentPicker({
  file,
  disabled,
  onChange,
  onError,
}: {
  file: File | null;
  disabled: boolean;
  onChange: (file: File | null) => void;
  onError: (message: string) => void;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  useEffect(() => {
    if (!file && input.current) input.current.value = "";
  }, [file]);
  function choose(files: FileList | null) {
    if (disabled) return;
    // Cancelling the chooser preserves the previous selection.
    if (!files?.length) return;
    const error =
      files.length > 1
        ? "Choose one document at a time."
        : validateDocumentFile(files[0]);
    if (error) {
      onChange(null);
      onError(error);
      if (input.current) input.current.value = "";
      return;
    }
    onError("");
    onChange(files[0]);
  }
  return (
    <Field data-disabled={disabled || undefined}>
      <FieldLabel htmlFor={id}>Choose document</FieldLabel>
      <input
        ref={input}
        id={id}
        type="file"
        accept=".pdf,.docx,.txt,.md,.markdown"
        disabled={disabled}
        tabIndex={-1}
        className="sr-only"
        aria-describedby={`${id}-help`}
        onChange={(e) => choose(e.target.files)}
      />
      <div
        data-slot="document-picker"
        data-dragging={dragging || undefined}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node | null))
            setDragging(false);
        }}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          choose(e.dataTransfer.files);
        }}
        className={cn(
          "flex min-w-0 flex-col items-center gap-4 rounded-xl border border-dashed border-line bg-canvas px-5 py-6 text-center transition-colors sm:flex-row sm:text-left",
          dragging && !disabled && "border-accent bg-accent-soft",
        )}
      >
        <div
          aria-hidden="true"
          className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent-deep"
        >
          {file ? <FileText size={24} /> : <UploadCloud size={24} />}
        </div>
        <div className="min-w-0 flex-1">
          <p className="break-all text-sm font-semibold text-ink">
            {file ? file.name : "Drop a document here"}
          </p>
          <p className="mt-1 text-xs leading-5 text-muted">
            {file
              ? `${file.size < 1024 ? `${file.size} bytes` : `${(file.size / 1024).toFixed(1)} KB`} · Ready to upload`
              : "Browse your files to add traceable project evidence."}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button
            variant="outline"
            disabled={disabled}
            onClick={() => input.current?.click()}
          >
            {file ? "Change file" : "Browse files"}
          </Button>
          {file && (
            <Button
              variant="ghost"
              size="icon"
              disabled={disabled}
              aria-label="Remove selected file"
              onClick={() => {
                onChange(null);
                onError("");
              }}
            >
              <X data-icon="inline-start" />
            </Button>
          )}
        </div>
      </div>
      <FieldDescription id={`${id}-help`}>
        PDF, DOCX, UTF-8 TXT or Markdown · Up to 5 MiB · Scanned PDFs need OCR.
      </FieldDescription>
    </Field>
  );
}
