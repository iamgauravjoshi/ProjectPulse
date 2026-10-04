"use client";
import { useRef, useState } from "react";
import { z } from "zod";
import { memoryRequest } from "../../features/memory/documents";
import {
  meetingSchema,
  participantSchema,
  type MeetingSummary,
} from "../../features/meetings/contracts";
import type { Workspace } from "../../features/workspace/contracts";
import { Button } from "../ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "../ui/dialog";
import { FieldGroup, Field, FieldLabel, FieldDescription } from "../ui/field";
import { Input, NativeSelect } from "../ui/input";
import { Alert } from "../ui/feedback";

export function MeetingDialog({
  workspace,
  mode,
  meeting,
  close,
  changed,
  opener,
  fallback,
}: {
  workspace: Workspace;
  mode: "create" | "participant" | "delete";
  meeting?: MeetingSummary;
  close: () => void;
  changed: (message: string, id?: string) => void;
  opener: React.RefObject<HTMLElement | null>;
  fallback: React.RefObject<HTMLHeadingElement | null>;
}) {
  const [title, setTitle] = useState("");
  const [time, setTime] = useState("");
  const [name, setName] = useState("");
  const [externalId, setExternalId] = useState("");
  const [member, setMember] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError("");
    try {
      const root = `/api/workspace/projects/${workspace.project.id}/meetings`;
      if (mode === "create") {
        const values = {
          title: title.trim(),
          startedAt: time ? new Date(time).toISOString() : null,
        };
        const result = meetingSchema.parse(
          await memoryRequest(root, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(values),
          }),
        );
        if (result.projectId !== workspace.project.id)
          throw new Error("Invalid meeting response.");
        changed("Meeting created.", result.id);
      } else if (mode === "participant" && meeting) {
        const displayName = name.trim();
        const speakerKey = externalId.trim()
          ? `id:${externalId.trim()}`
          : `name:${displayName}`;
        const result = participantSchema.parse(
          await memoryRequest(`${root}/${meeting.id}/participants`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              displayName,
              speakerKey,
              userId: member || null,
            }),
          }),
        );
        if (
          result.meetingId !== meeting.id ||
          !z.uuid().safeParse(result.id).success
        )
          throw new Error("Invalid participant response.");
        changed("Participant registered.");
      } else if (meeting) {
        await memoryRequest(`${root}/${meeting.id}`, { method: "DELETE" });
        changed("Meeting deleted. Audit history is retained.", "");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed. Retry.");
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
        onCloseAutoFocus={(e) => {
          e.preventDefault();
          (opener.current?.isConnected
            ? opener.current
            : fallback.current
          )?.focus();
        }}
        onEscapeKeyDown={(e) => {
          if (pending) e.preventDefault();
        }}
        onPointerDownOutside={(e) => {
          if (pending) e.preventDefault();
        }}
      >
        <DialogHeader>
          <DialogTitle ref={heading} tabIndex={-1}>
            {mode === "create"
              ? "New meeting"
              : mode === "participant"
                ? "Add participant"
                : "Delete meeting"}
          </DialogTitle>
          <DialogDescription>
            {mode === "delete"
              ? "Remove this meeting, participants and transcript? Canonical state and audit history are retained."
              : "Meeting evidence stays separate from confirmed project state."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit}>
          <FieldGroup className="mt-5">
            {mode === "create" && (
              <>
                <Field>
                  <FieldLabel htmlFor="meeting-title">Meeting title</FieldLabel>
                  <Input
                    id="meeting-title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                    maxLength={240}
                    disabled={pending}
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="meeting-time">
                    Start time (optional)
                  </FieldLabel>
                  <Input
                    id="meeting-time"
                    type="datetime-local"
                    value={time}
                    onChange={(e) => setTime(e.target.value)}
                    disabled={pending}
                  />
                  <FieldDescription>
                    Uses your local timezone. Leave blank if the meeting time is
                    unknown.
                  </FieldDescription>
                </Field>
              </>
            )}
            {mode === "participant" && (
              <>
                <Field>
                  <FieldLabel htmlFor="participant-name">
                    Participant name
                  </FieldLabel>
                  <Input
                    id="participant-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    maxLength={120}
                    disabled={pending}
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="participant-source">
                    Transcript speaker ID (optional)
                  </FieldLabel>
                  <Input
                    id="participant-source"
                    value={externalId}
                    onChange={(e) => setExternalId(e.target.value)}
                    maxLength={120}
                    disabled={pending}
                  />
                  <FieldDescription>
                    Use the JSON speakerId to distinguish people with the same
                    name. For name-only files, leave blank and match the
                    transcript label exactly.
                  </FieldDescription>
                </Field>
                <Field>
                  <FieldLabel htmlFor="participant-member">
                    Project member (optional)
                  </FieldLabel>
                  <NativeSelect
                    id="participant-member"
                    value={member}
                    onChange={(e) => setMember(e.target.value)}
                    disabled={pending}
                  >
                    <option value="">Unlinked participant</option>
                    {workspace.members.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                  </NativeSelect>
                  <FieldDescription>
                    Names alone never assign project membership.
                  </FieldDescription>
                </Field>
              </>
            )}
            {error && (
              <Alert variant="destructive" aria-label="Meeting error">
                {error}
              </Alert>
            )}
          </FieldGroup>
          <DialogFooter>
            <Button
              type="submit"
              variant={mode === "delete" ? "destructive" : "default"}
              disabled={
                pending ||
                (mode === "create" && !title.trim()) ||
                (mode === "participant" && !name.trim())
              }
            >
              {pending
                ? "Saving…"
                : mode === "create"
                  ? "Create meeting"
                  : mode === "participant"
                    ? "Save participant"
                    : "Confirm delete"}
            </Button>
            <Button variant="outline" disabled={pending} onClick={close}>
              Cancel
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
