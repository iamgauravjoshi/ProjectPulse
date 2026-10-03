"use client";
import { useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { Workspace } from "../../features/workspace/contracts";
import {
  kinds,
  type RecordKind,
  type StateRecord,
} from "../../features/memory/forms";
import { RecordDialog } from "./record-dialog";

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
    <section className="rounded-xl border border-line bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Project state</h2>
          <p className="mt-1 text-sm text-muted">
            Human-established baseline. Every saved change is audited.
          </p>
        </div>
        <button className="button-primary" onClick={() => open()}>
          New record
        </button>
      </div>
      <label className="my-5 block text-sm font-medium">
        Record type
        <select
          className="ml-3 rounded border border-line p-2"
          aria-label="Record type"
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
        </select>
      </label>
      <div className="divide-y divide-line">
        {workspace[kind].map((record) => (
          <article
            key={record.id}
            id={record.id}
            className="flex flex-wrap items-center justify-between gap-4 py-4"
          >
            <div>
              <h3 className="font-medium">{record.title}</h3>
              <p className="mt-1 max-w-2xl whitespace-pre-wrap text-sm text-muted">
                {record.description}
              </p>
              <p className="mt-2 text-xs text-muted">
                {"decisionStatus" in record
                  ? record.decisionStatus
                  : record.status}{" "}
                · Version {record.version}
              </p>
            </div>
            <div className="flex gap-2">
              <button className="button-secondary" onClick={() => open(record)}>
                Edit<span className="sr-only"> {record.title}</span>
              </button>
              <button
                className="button-secondary"
                onClick={() => open(record, true)}
              >
                Delete<span className="sr-only"> {record.title}</span>
              </button>
            </div>
          </article>
        ))}
      </div>
      {workspace[kind].length === 0 && (
        <p className="py-8 text-sm text-muted">
          No {kind} yet. Create a record to establish the baseline.
        </p>
      )}
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
    </section>
  );
}
