import { expect, it } from "vitest";
import { searchSchema } from "../../src/features/memory/search";
import { fixture } from "../fixtures/workspace";
const record = {
  kind: "record",
  id: fixture.requirements[0].id,
  projectId: fixture.project.id,
  title: "Scope",
  excerpt: "Human-established SSO scope",
  canonical: true,
  entityType: "requirements",
  facts: { phase: 2 },
};
const result = {
  projectId: fixture.project.id,
  query: "SSO",
  semanticStatus: "unavailable",
  matches: [record],
};
it("validates bounded context and honest semantic status", () => {
  expect(searchSchema.parse(result).matches).toHaveLength(1);
  for (const changes of [
    { matches: Array(9).fill(record) },
    { semanticStatus: "pretend" },
    { matches: [{ ...record, excerpt: "x".repeat(601) }] },
    { matches: [{ ...record, canonical: false }] },
  ])
    expect(() => searchSchema.parse({ ...result, ...changes })).toThrow();
});
it("rejects cross-project results and document evidence labelled canonical", () => {
  expect(() =>
    searchSchema.parse({
      ...result,
      matches: [
        { ...record, projectId: "4f76ce55-33b2-4a44-954c-03291c56b24b" },
      ],
    }),
  ).toThrow();
  const doc = {
    kind: "document",
    id: record.id,
    projectId: fixture.project.id,
    documentId: record.id,
    title: "scope.md",
    excerpt: "Source evidence",
    canonical: false,
    page: null,
    section: "Scope",
    segmentIndex: 0,
    start: 0,
    end: 15,
  };
  expect(
    searchSchema.parse({ ...result, matches: [doc] }).matches[0].canonical,
  ).toBe(false);
  expect(() =>
    searchSchema.parse({ ...result, matches: [{ ...doc, canonical: true }] }),
  ).toThrow();
});
