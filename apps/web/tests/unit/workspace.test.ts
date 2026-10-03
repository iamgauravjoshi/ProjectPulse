import { afterEach, describe, expect, it, vi } from "vitest";
import { loadWorkspace } from "../../src/features/workspace/api";
import { workspaceSchema } from "../../src/features/workspace/contracts";
import {
  filterRows,
  formatDate,
  ownerName,
  overviewRecords,
  recordRows,
  workspaceMetrics,
} from "../../src/features/workspace/presenters";
import { fixture } from "../fixtures/workspace";

afterEach(() => vi.unstubAllGlobals());

describe("trusted workspace presentation", () => {
  it("does not count proposals or completed commitments as current truth", () => {
    const data = structuredClone(fixture);
    data.decisions[0].decisionStatus = "PROVISIONAL";
    data.requirements[0].status = "DRAFT";
    data.commitments[0].status = "DONE";
    expect(workspaceMetrics(data).map((m) => m.value)).toEqual([0, 2, 0, 1]);
    expect(
      overviewRecords(data).decisions.every(
        (d) => d.decisionStatus === "CONFIRMED",
      ),
    ).toBe(true);
  });

  it("rejects a nested record from a different project", () => {
    const data = structuredClone(fixture);
    data.requirements[0].projectId = "4f76ce55-33b2-4a44-954c-03291c56b24b";
    expect(workspaceSchema.safeParse(data).success).toBe(false);
  });

  it("keeps calendar dates and unresolved dates explicit", () => {
    expect(formatDate("2026-11-24")).toBe("24 Nov 2026");
    expect(formatDate(null)).toBe("Not set");
  });

  it("uses commitment owner rather than speaker", () => {
    const data = structuredClone(fixture);
    data.commitments[0].saidBy = data.members.find(
      (m) => m.name === "Sarah",
    )!.id;
    expect(recordRows(data, "commitments")[0].owner).toBe("John");
    expect(ownerName(data, null)).toBe("Unassigned");
  });

  it("combines search and actual decision status filters", () => {
    const data = structuredClone(fixture);
    data.decisions.find((d) => d.title === "CSV export")!.decisionStatus =
      "PROVISIONAL";
    const rows = recordRows(data, "decisions");
    expect(filterRows(rows, " CSV ", "PROVISIONAL")).toHaveLength(1);
    expect(filterRows(rows, "CSV", "CONFIRMED")).toHaveLength(0);
  });

  it("rejects a coherent response for the wrong requested project", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(fixture)));
    await expect(
      loadWorkspace(
        "4f76ce55-33b2-4a44-954c-03291c56b24b",
        new AbortController().signal,
      ),
    ).rejects.toThrow("does not match");
  });
});
