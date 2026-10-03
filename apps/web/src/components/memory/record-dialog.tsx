"use client";
import * as Dialog from "@radix-ui/react-dialog";
import { useState } from "react";
import type { Workspace } from "../../features/workspace/contracts";
import {
  fields,
  formValues,
  labels,
  parseValues,
  type RecordKind,
  type StateRecord,
} from "../../features/memory/forms";
import { MemoryError, mutateState } from "../../features/memory/api";
export function RecordDialog({
  workspace,
  kind,
  target,
  close,
  onChanged,
  opener,
}: {
  workspace: Workspace;
  kind: RecordKind;
  target: { record?: StateRecord; remove: boolean };
  close: () => void;
  onChanged: (message: string) => void;
  opener: React.RefObject<HTMLElement | null>;
}) {
  const [values, setValues] = useState(() => formValues(kind, target.record));
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<MemoryError | null>(null);
  const title = target.remove
    ? "Delete record"
    : target.record
      ? "Edit record"
      : "Create record";
  async function save(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    let payload: Record<string, unknown> | undefined;
    try {
      payload = target.remove ? undefined : parseValues(kind, values);
    } catch {
      setError(
        new MemoryError(
          "INVALID_FIELDS",
          "Check the title, dates and phase. A phase must be a positive whole number.",
        ),
      );
      return;
    }
    setPending(true);
    try {
      await mutateState(
        workspace.project.id,
        kind,
        target.remove ? "DELETE" : target.record ? "PUT" : "POST",
        payload,
        target.record?.id,
        target.record?.version,
      );
      onChanged(
        `Record ${target.remove ? "deleted" : target.record ? "updated" : "created"}.`,
      );
    } catch (e) {
      setError(
        e instanceof MemoryError
          ? e
          : new MemoryError(
              "SAVE_FAILED",
              "Couldn’t save. Reload the project state before retrying.",
            ),
      );
      setPending(false);
    }
  }
  function field(key: string, choices: string[] | null) {
    const relations =
      key === "ownerId"
        ? workspace.members.map((x) => ({ id: x.id, title: x.name }))
        : key === "dependencyId"
          ? workspace.dependencies
          : key === "blockedMilestoneId"
            ? workspace.milestones
            : null;
    const common = {
      id: `field-${key}`,
      value: values[key],
      disabled: pending,
      onChange: (
        e: React.ChangeEvent<
          HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
        >,
      ) => setValues({ ...values, [key]: e.target.value }),
      className:
        "mt-1 block w-full rounded-lg border border-line bg-white px-3 py-2 text-sm",
    };
    return (
      <label
        key={key}
        htmlFor={common.id}
        className="block text-sm font-medium"
      >
        {labels[key]}
        {choices ? (
          <select {...common}>
            {choices.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        ) : relations ? (
          <select {...common}>
            <option value="">Unassigned</option>
            {relations.map((r) => (
              <option key={r.id} value={r.id}>
                {r.title}
              </option>
            ))}
          </select>
        ) : key === "description" ? (
          <textarea {...common} rows={3} maxLength={20000} />
        ) : (
          <input
            {...common}
            type={
              key === "date" || key === "dueDate"
                ? "date"
                : key === "phase"
                  ? "number"
                  : "text"
            }
            required={key === "title" || key === "date" || key === "phase"}
            min={key === "phase" ? 1 : undefined}
            step={key === "phase" ? 1 : undefined}
            maxLength={key === "title" ? 240 : undefined}
          />
        )}
      </label>
    );
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
        <Dialog.Content
          onCloseAutoFocus={(e) => {
            e.preventDefault();
            opener.current?.focus();
          }}
          className="fixed left-1/2 top-1/2 z-50 max-h-[85dvh] w-[calc(100%-32px)] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl bg-white p-6 shadow-xl"
        >
          <Dialog.Title className="text-xl font-semibold">{title}</Dialog.Title>
          <Dialog.Description className="mt-2 text-sm text-muted">
            {target.remove
              ? `Delete “${target.record?.title}”? The audit history is retained. Linked records must be unlinked first.`
              : "Only your explicit save changes canonical state. Confirmed decisions establish the human baseline."}
          </Dialog.Description>
          <form onSubmit={save} className="mt-5 space-y-4">
            {!target.remove && [
              field("title", null),
              field("description", null),
              ...Object.entries(fields[kind]).map(([k, v]) => field(k, v)),
            ]}
            {error && (
              <p role="alert" className="text-sm text-red-700">
                {error.message}
              </p>
            )}
            {error?.code === "STALE_VERSION" && (
              <button
                type="button"
                className="button-secondary"
                onClick={() =>
                  onChanged(
                    "Latest state loaded. Reopen the record to review your changes.",
                  )
                }
              >
                Reload latest state
              </button>
            )}
            <div className="flex gap-3">
              <button className="button-primary" disabled={pending}>
                {pending
                  ? "Saving…"
                  : target.remove
                    ? "Confirm delete"
                    : "Save record"}
              </button>
              <button
                type="button"
                className="button-secondary"
                disabled={pending}
                onClick={close}
              >
                Cancel
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
