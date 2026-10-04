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
import { Badge } from "../ui/badge";
import { Field, FieldGroup, FieldLabel } from "../ui/field";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
  NativeSelect,
} from "../ui/input";

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
      action={<Badge variant="outline">{rows.length} records</Badge>}
    >
      <FieldGroup className="border-b border-line p-5">
        <Field orientation="horizontal">
          <div className="min-w-0 flex-1">
            <FieldLabel htmlFor={`search-${view}`} className="sr-only">
              Search {view}
            </FieldLabel>
            <InputGroup>
              <InputGroupAddon>
                <Search aria-hidden="true" />
              </InputGroupAddon>
              <InputGroupInput
                id={`search-${view}`}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={`Search ${view}…`}
              />
            </InputGroup>
          </div>
          <div className="sm:w-48">
            <FieldLabel htmlFor={`filter-${view}`} className="sr-only">
              Status
            </FieldLabel>
            <NativeSelect
              id={`filter-${view}`}
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="ALL">All statuses</option>
              {statuses[view].map((value) => (
                <option value={value} key={value}>
                  {humanLabel(value)}
                </option>
              ))}
            </NativeSelect>
          </div>
        </Field>
      </FieldGroup>
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
              <div className="flex shrink-0 flex-wrap items-center gap-2 self-start">
                {view === "risks" && (
                  <StatusBadge status={row.owner} variant="outline" />
                )}
                <StatusBadge status={row.status} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
