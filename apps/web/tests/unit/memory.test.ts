import { sameOrigin } from "../../src/lib/memory-proxy";
import { describe, expect, it } from "vitest";
import {
  fields,
  formValues,
  kinds,
  parseValues,
} from "../../src/features/memory/forms";
import { fixture } from "../fixtures/workspace";
describe("manual state forms", () => {
  for (const kind of kinds)
    it(`projects only editable ${kind} fields`, () => {
      const record = fixture[kind][0];
      const form = formValues(kind, record);
      expect(Object.keys(form)).toEqual([
        "title",
        "description",
        ...Object.keys(fields[kind]),
      ]);
      expect(parseValues(kind, form)).not.toHaveProperty("sourceKind");
      expect(parseValues(kind, form)).not.toHaveProperty("confirmedAt");
    });
  it("does not silently confirm a decision", () =>
    expect(formValues("decisions").decisionStatus).toBe("DISCUSSION"));
  it("validates empty titles, positive whole phases and calendar dates", () => {
    const form = { ...formValues("requirements"), title: "example" };
    for (const phase of ["", "0", "-1", "1.2"])
      expect(() => parseValues("requirements", { ...form, phase })).toThrow();
    expect(() =>
      parseValues("requirements", { ...form, title: "  " }),
    ).toThrow();
    expect(() =>
      parseValues("milestones", {
        ...formValues("milestones"),
        title: "launch",
        date: "2026-02-30",
      }),
    ).toThrow();
  });
  it("keeps optional owners and dates unresolved", () => {
    const data = parseValues("commitments", {
      ...formValues("commitments"),
      title: "Follow up",
    });
    expect(data.ownerId).toBeNull();
    expect(data.dueDate).toBeNull();
    expect(data.dependencyId).toBeNull();
  });
});

it("validates browser origins against incoming Host even when Next rewrites request.url", () => {
  const request = (origin: string) =>
    new Request("http://localhost:3010/api", {
      headers: { host: "127.0.0.1:3010", origin },
    });
  expect(sameOrigin(request("http://127.0.0.1:3010"))).toBe(true);
  for (const origin of ["http://evil.test", "https://127.0.0.1:3010", "null"])
    expect(sameOrigin(request(origin))).toBe(false);
});
