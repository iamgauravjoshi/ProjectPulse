"use client";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogHeader,
  DialogFooter,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Field, FieldGroup, FieldLabel } from "../ui/field";
import { Input, NativeSelect, Textarea } from "../ui/input";
import { Alert } from "../ui/feedback";
import { humanLabel } from "../../features/workspace/presenters";
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
      "aria-invalid": error?.code === "INVALID_FIELDS" || undefined,
    };
    return (
      <Field
        key={key}
        data-disabled={pending || undefined}
        data-invalid={error?.code === "INVALID_FIELDS" || undefined}
      >
        <FieldLabel htmlFor={common.id}>{labels[key]}</FieldLabel>
        {choices ? (
          <NativeSelect {...common}>
            {choices.map((c) => (
              <option key={c} value={c}>
                {humanLabel(c)}
              </option>
            ))}
          </NativeSelect>
        ) : relations ? (
          <NativeSelect {...common}>
            <option value="">Unassigned</option>
            {relations.map((r) => (
              <option key={r.id} value={r.id}>
                {r.title}
              </option>
            ))}
          </NativeSelect>
        ) : key === "description" ? (
          <Textarea {...common} rows={3} maxLength={20000} />
        ) : (
          <Input
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
      </Field>
    );
  }
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !pending) close();
      }}
    >
      <DialogContent
        onCloseAutoFocus={(e) => {
          e.preventDefault();
          opener.current?.focus();
        }}
      >
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            {target.remove
              ? `Delete “${target.record?.title}”? The audit history is retained. Linked records must be unlinked first.`
              : "Only your explicit save changes canonical state. Confirmed decisions establish the human baseline."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={save} className="mt-5">
          <FieldGroup>
            {!target.remove && [
              field("title", null),
              field("description", null),
              ...Object.entries(fields[kind]).map(([k, v]) => field(k, v)),
            ]}
            {error && <Alert variant="destructive">{error.message}</Alert>}
            {error?.code === "STALE_VERSION" && (
              <Button
                type="button"
                variant="outline"
                onClick={() =>
                  onChanged(
                    "Latest state loaded. Reopen the record to review your changes.",
                  )
                }
              >
                Reload latest state
              </Button>
            )}
            <DialogFooter>
              <Button
                type="submit"
                variant={target.remove ? "destructive" : "default"}
                disabled={pending}
              >
                {pending
                  ? "Saving…"
                  : target.remove
                    ? "Confirm delete"
                    : "Save record"}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={pending}
                onClick={close}
              >
                Cancel
              </Button>
            </DialogFooter>
          </FieldGroup>
        </form>
      </DialogContent>
    </Dialog>
  );
}
