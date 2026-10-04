"use client";
import { Plus, Pencil, Trash2, Database } from "lucide-react";
import { useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { Workspace } from "../../features/workspace/contracts";
import {
  kinds,
  type RecordKind,
  type StateRecord,
} from "../../features/memory/forms";
import { RecordDialog } from "./record-dialog";
import { StatusBadge } from "../workspace/primitives";
import { Button } from "../ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "../ui/card";
import { Field, FieldGroup, FieldLabel } from "../ui/field";
import { NativeSelect } from "../ui/input";
import { Empty, EmptyDescription } from "../ui/feedback";

export function StateEditor({
  workspace,
  onChanged,
}: {
  workspace: Workspace;
  onChanged: (message: string) => void;
}) {
  const router = useRouter();
  const params = useSearchParams();
  const kind = (kinds.find((k) => k === params.get("kind")) ??
    "requirements") as RecordKind;
  const [target, setTarget] = useState<{
    record?: StateRecord;
    remove: boolean;
  } | null>(null);
  const opener = useRef<HTMLElement | null>(null);
  function open(record?: StateRecord, remove = false) {
    opener.current = document.activeElement as HTMLElement;
    setTarget({ record, remove });
  }
  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>
            <Database size={18} aria-hidden="true" className="text-muted" />
            Project state
          </CardTitle>
          <CardDescription>
            Human-established baseline. Every saved change is audited.
          </CardDescription>
        </div>
        <Button onClick={() => open()}>
          <Plus data-icon="inline-start" />
          New record
        </Button>
      </CardHeader>
      <CardContent>
        <FieldGroup className="mb-5">
          <Field className="sm:max-w-xs">
            <FieldLabel htmlFor="record-type">Record type</FieldLabel>
            <NativeSelect
              id="record-type"
              value={kind}
              onChange={(e) => {
                const next = new URLSearchParams(params.toString());
                next.set("kind", e.target.value);
                router.replace(`/?${next}`);
              }}
            >
              {kinds.map((k) => (
                <option key={k} value={k}>
                  {k[0].toUpperCase() + k.slice(1)}
                </option>
              ))}
            </NativeSelect>
          </Field>
        </FieldGroup>
        <div className="divide-y divide-line">
          {workspace[kind].map((record) => (
            <article
              key={record.id}
              id={record.id}
              className="flex flex-col justify-between gap-4 py-5 sm:flex-row sm:items-start"
            >
              <div className="min-w-0">
                <h3 className="font-semibold leading-6">{record.title}</h3>
                <p className="mt-1 max-w-2xl whitespace-pre-wrap text-sm leading-6 text-muted">
                  {record.description}
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <StatusBadge
                    status={
                      "decisionStatus" in record
                        ? record.decisionStatus
                        : record.status
                    }
                  />
                  {"severity" in record && (
                    <StatusBadge status={record.severity} variant="outline" />
                  )}
                  <span className="text-xs text-muted">
                    Version {record.version}
                  </span>
                </div>
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => open(record)}
                >
                  <Pencil data-icon="inline-start" />
                  Edit<span className="sr-only"> {record.title}</span>
                </Button>
                <Button
                  variant="destructive-outline"
                  size="sm"
                  onClick={() => open(record, true)}
                >
                  <Trash2 data-icon="inline-start" />
                  Delete<span className="sr-only"> {record.title}</span>
                </Button>
              </div>
            </article>
          ))}
        </div>
        {workspace[kind].length === 0 && (
          <Empty compact>
            <EmptyDescription>
              No {kind} yet. Create a record to establish the baseline.
            </EmptyDescription>
          </Empty>
        )}
      </CardContent>
      {target && (
        <RecordDialog
          key={`${kind}-${target.record?.id ?? "new"}-${target.remove}`}
          workspace={workspace}
          kind={kind}
          target={target}
          close={() => setTarget(null)}
          onChanged={onChanged}
          opener={opener}
        />
      )}
    </Card>
  );
}
