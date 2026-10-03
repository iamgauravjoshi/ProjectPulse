"use client";

import { Search } from "lucide-react";
import { useState } from "react";
import type { Workspace } from "../../features/workspace/contracts";
import {
  filterRows,
  formatDate,
  humanLabel,
  recordRows,
} from "../../features/workspace/presenters";
import { EmptyCategory, Panel, StatusBadge } from "./primitives";

const statuses = {
  decisions: [
    "CONFIRMED",
    "PROVISIONAL",
    "REVIEW_REQUIRED",
    "PROPOSAL",
    "DISCUSSION",
    "SUPERSEDED",
    "REJECTED",
  ],
  commitments: ["OPEN", "IN_PROGRESS", "DONE", "CANCELLED"],
  risks: ["OPEN", "MITIGATED", "CLOSED"],
};

export function RecordsView({
  workspace,
  view,
}: {
  workspace: Workspace;
  view: keyof typeof statuses;
}) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const rows = filterRows(recordRows(workspace, view), query, status);
  const label = view[0].toUpperCase() + view.slice(1);
  return (
    <Panel
      title={label}
      action={
        <span className="text-[13px] text-muted">{rows.length} records</span>
      }
    >
      <div className="flex flex-col gap-3 border-b border-line p-4 sm:flex-row">
        <label className="relative min-w-0 flex-1">
          <span className="sr-only">Search {view}</span>
          <Search
            size={16}
            aria-hidden="true"
            className="absolute left-3 top-3 text-muted"
          />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={`Search ${view}…`}
            className="w-full rounded-lg border border-line bg-white py-2.5 pl-9 pr-3 text-sm"
          />
        </label>
        <select
          aria-label="Status"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className="rounded-lg border border-line bg-white px-3 py-2.5 text-sm text-ink"
        >
          <option value="ALL">All statuses</option>
          {statuses[view].map((value) => (
            <option value={value} key={value}>
              {humanLabel(value)}
            </option>
          ))}
        </select>
      </div>
      {rows.length === 0 ? (
        <EmptyCategory
          text={
            query || status !== "ALL"
              ? "No records match your filters."
              : `No ${view} recorded yet.`
          }
        />
      ) : (
        <ul className="divide-y divide-line">
          {rows.map((row) => (
            <li
              key={row.id}
              className="flex flex-col justify-between gap-3 px-5 py-5 sm:flex-row"
            >
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-ink">{row.title}</h3>
                <p className="mt-1 text-sm leading-6 text-muted">
                  {row.description}
                </p>
                <p className="mt-2 text-[13px] text-muted">
                  {view === "risks"
                    ? `${humanLabel(row.owner)} severity`
                    : row.owner}
                  {view === "commitments" &&
                    ` · ${row.date ? `Due ${formatDate(row.date)}` : "Due date not set"}`}
                  <span className="mx-2 text-line">·</span>
                  {row.source === "SEED" ? "Demo baseline" : "Project baseline"}
                </p>
              </div>
              <span className="self-start">
                <StatusBadge status={row.status} />
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
