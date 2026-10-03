import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";
import { kinds } from "../../src/features/memory/forms";
import { fixture } from "../fixtures/workspace";
const projectId = fixture.project.id;
for (const kind of kinds)
  test(`manual ${kind} persists create/edit/delete without touching the baseline`, async ({
    page,
    request,
  }) => {
    const title = `Browser ${kind} ${randomUUID()}`;
    let id: string | undefined;
    try {
      await page.goto(`/?project=${projectId}&view=state&kind=${kind}`);
      await page.getByRole("button", { name: "New record" }).click();
      await page.getByLabel("Title", { exact: true }).fill(title);
      await page
        .getByLabel("Description", { exact: true })
        .fill("Explicit human baseline");
      if (kind === "milestones")
        await page.getByLabel("Date", { exact: true }).fill("2026-12-10");
      if (kind === "decisions")
        await page.getByLabel("Decision status").selectOption("PROPOSAL");
      await page.getByRole("button", { name: "Save record" }).click();
      await expect(
        page.getByRole("status", { name: "Save feedback" }),
      ).toHaveText("Record created.");
      const response = await request.get(
        `/api/workspace/projects/${projectId}/state/${kind}`,
      );
      const records = await response.json();
      id = records.find((r: { title: string }) => r.title === title)?.id;
      expect(id).toBeTruthy();
      await page.reload();
      await expect(
        page.getByRole("heading", { name: title, exact: true }),
      ).toBeVisible();
      await page
        .getByRole("button", { name: `Edit ${title}`, exact: true })
        .click();
      await page.getByLabel("Title", { exact: true }).fill(`${title} revised`);
      await page.getByRole("button", { name: "Save record" }).click();
      await expect(
        page.getByRole("status", { name: "Save feedback" }),
      ).toHaveText("Record updated.");
      await page.reload();
      await expect(
        page.getByRole("heading", { name: `${title} revised`, exact: true }),
      ).toBeVisible();
      await page
        .getByRole("button", { name: `Delete ${title} revised`, exact: true })
        .click();
      await expect(page.getByRole("dialog")).toContainText(
        "audit history is retained",
      );
      await page.getByRole("button", { name: "Confirm delete" }).click();
      await expect(
        page.getByRole("status", { name: "Save feedback" }),
      ).toHaveText("Record deleted.");
      await expect(
        page.getByRole("heading", { name: `${title} revised`, exact: true }),
      ).toHaveCount(0);
    } finally {
      if (id) {
        const res = await request.get(
          `/api/workspace/projects/${projectId}/state/${kind}/${id}`,
        );
        if (res.ok()) {
          const record = await res.json();
          await request.delete(
            `/api/workspace/projects/${projectId}/state/${kind}/${id}?expectedVersion=${record.version}`,
          );
        }
      }
    }
    const baseline = await (
      await request.get(`/api/workspace/projects/${projectId}`)
    ).json();
    expect(
      baseline.requirements.find(
        (r: { title: string }) => r.title === "Single sign-on",
      ).phase,
    ).toBe(2);
    expect(
      baseline.decisions.filter(
        (r: { decisionStatus: string }) => r.decisionStatus === "CONFIRMED",
      ),
    ).toHaveLength(3);
  });
test("failed saves preserve drafts and stale edits require reloading", async ({
  page,
}) => {
  await page.route("**/state/requirements", (route) =>
    route.fulfill({
      status: 409,
      json: {
        error: {
          code: "STALE_VERSION",
          message: "Record changed. Reload before editing.",
        },
      },
    }),
  );
  await page.goto("/?view=state");
  await page.getByRole("button", { name: "New record" }).click();
  await page.getByLabel("Title", { exact: true }).fill("Preserved draft");
  await page.getByRole("button", { name: "Save record" }).click();
  await expect(page.getByRole("alert")).toContainText("Record changed");
  await expect(page.getByLabel("Title", { exact: true })).toHaveValue(
    "Preserved draft",
  );
  await page.getByRole("button", { name: "Reload latest state" }).click();
  await expect(
    page.getByRole("status", { name: "Save feedback" }),
  ).toContainText("Latest state loaded");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
test("mobile editor and keyboard dismissal return focus", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?view=state&kind=commitments");
  const trigger = page.getByRole("button", { name: "New record" });
  await trigger.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
});
