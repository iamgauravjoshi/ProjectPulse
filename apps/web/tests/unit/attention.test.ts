import { describe, expect, it } from "vitest";
import {
  attentionCounts,
  attentionItems,
  projectDate,
} from "../../src/features/workspace/attention";
import type { Workspace } from "../../src/features/workspace/contracts";
import { emptyWorkspace, fixture } from "../fixtures/workspace";

function baseline() {
  const data = structuredClone(fixture);
  data.generatedAt = "2026-10-03T00:00:00Z";
  return data;
}

describe("deterministic attention presentation", () => {
  it("shows a missing due date separately from overdue work", () => {
    const data = baseline();
    expect(attentionCounts(data)).toEqual({
      review: 0,
      overdue: 0,
      timeline: 1,
      unscheduled: 1,
    });
    expect(attentionItems(data).map((item) => item.kind)).toEqual([
      "timeline",
      "unscheduled",
    ]);
  });

  it.each([
    ["2026-10-02", "OPEN", 1],
    ["2026-10-03", "OPEN", 0],
    ["2026-10-04", "OPEN", 0],
    ["2026-10-01", "DONE", 0],
    ["2026-10-01", "CANCELLED", 0],
    ["2026-10-01", "IN_PROGRESS", 1],
  ] as const)(
    "due %s, status %s produces %i overdue follow-ups",
    (date, status, expected) => {
      const data = baseline();
      data.commitments[0].dueDate = date;
      data.commitments[0].status = status;
      expect(attentionCounts(data).overdue).toBe(expected);
    },
  );

  it("requires the explicit review status instead of inferring authority", () => {
    const data = baseline();
    data.decisions[0].decisionStatus = "PROVISIONAL";
    expect(attentionCounts(data).review).toBe(0);
    data.decisions[0].decisionStatus = "REVIEW_REQUIRED";
    expect(attentionCounts(data).review).toBe(1);
  });

  it("does not flag dependencies of completed milestones", () => {
    const data = baseline();
    data.milestones[0].status = "COMPLETED";
    expect(attentionCounts(data).timeline).toBe(0);
  });

  it("does not flag a ready dependency", () => {
    const data = baseline();
    data.dependencies[0].status = "READY";
    expect(attentionCounts(data).timeline).toBe(0);
  });

  it("flags a passed active milestone as a separate follow-up", () => {
    const data = baseline();
    data.milestones[0].date = "2026-10-01";
    expect(attentionCounts(data).timeline).toBe(2);
  });

  it("uses the client timezone across the UTC date boundary", () => {
    const data = baseline();
    data.generatedAt = "2026-10-02T21:00:00Z";
    data.commitments[0].dueDate = "2026-10-02";
    expect(projectDate(data.generatedAt)).toBe("2026-10-03");
    expect(attentionCounts(data).overdue).toBe(1);
  });

  it("has no inferred follow-ups for an empty baseline", () => {
    expect(attentionItems(emptyWorkspace() as Workspace)).toEqual([]);
  });
});
