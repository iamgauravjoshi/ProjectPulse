import { expect, test } from "@playwright/test";
import path from "node:path";
import { emptyWorkspace, fixture } from "../fixtures/workspace";

test("overview to follow-up to review inbox preserves the baseline", async ({
  page,
  request,
}) => {
  await page.goto("/");
  const panel = page
    .getByRole("heading", { name: "Needs attention", exact: true })
    .locator("../..");
  await expect(panel.getByLabel("2 items need attention")).toBeVisible();
  await expect(
    panel.getByText("Overdue commitments").locator(".."),
  ).toContainText("0");
  await expect(panel.getByText("Conflicts").locator("..")).toContainText(
    "Awaiting evidence",
  );
  if (process.env.CAPTURE_WORKSPACE === "1") {
    await page.screenshot({
      path: path.resolve(
        __dirname,
        "../../../../docs/features/images/workspace-desktop.png",
      ),
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({
      path: path.resolve(
        __dirname,
        "../../../../docs/features/images/workspace-mobile.png",
      ),
      fullPage: true,
    });
    await page.setViewportSize({ width: 1280, height: 800 });
  }
  await panel.getByRole("link", { name: /Production credentials/ }).click();
  await expect(page).toHaveURL(/view=commitments/);
  await expect(page.getByText("John · Due date not set")).toBeVisible();
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "Overview", exact: true })
    .click();
  await panel.getByRole("link", { name: /Security review/ }).click();
  await expect(page).toHaveURL(/#milestones$/);
  await expect(
    page.locator('#milestones [data-status="PENDING"]'),
  ).toBeVisible();
  await expect(
    page.locator("#milestones").getByText("Launch dependency"),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Open review inbox", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Decisions needing review" }),
  ).toBeVisible();
  await expect(
    page.getByText("No decisions are currently marked for review."),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Project follow-up" }),
  ).toBeVisible();
  const response = await request.get(
    `http://127.0.0.1:8010/api/v1/projects/${fixture.project.id}/workspace`,
  );
  expect((await response.json()).requirements[0].phase).toBe(2);
});

test("empty baseline has no fabricated attention or conflict result", async ({
  page,
}) => {
  await page.route("**/api/workspace/projects/*", (route) =>
    route.fulfill({ json: emptyWorkspace() }),
  );
  await page.goto("/");
  await expect(
    page.getByText("No baseline follow-ups right now."),
  ).toBeVisible();
  await expect(
    page.getByText("Awaiting evidence", { exact: true }),
  ).toBeVisible();
});

test("recorded overdue and review-required states remain separate from truth", async ({
  page,
}) => {
  const data = structuredClone(fixture);
  data.generatedAt = "2026-10-03T00:00:00Z";
  data.commitments[0].dueDate = "2026-10-01";
  data.decisions[0].decisionStatus = "REVIEW_REQUIRED";
  await page.route("**/api/workspace/projects/*", (route) =>
    route.fulfill({ json: data }),
  );
  await page.goto("/");
  const panel = page
    .getByRole("heading", { name: "Needs attention" })
    .locator("../..");
  await expect(panel.getByText("Overdue", { exact: true })).toBeVisible();
  await expect(
    panel.getByText("Review required", { exact: true }),
  ).toBeVisible();
  const state = page.locator("#project-state");
  await expect(
    state.getByText(data.decisions[0].title, { exact: true }),
  ).toHaveCount(0);
});

test("mobile overview and a long project name do not overflow", async ({
  page,
}) => {
  const data = structuredClone(fixture);
  data.project.name = "Portal".repeat(35);
  await page.route("**/api/workspace/projects", (route) =>
    route.fulfill({ json: [data.project] }),
  );
  await page.route("**/api/workspace/projects/*", (route) =>
    route.fulfill({ json: data }),
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Needs attention" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(
    page.getByRole("dialog", { name: "Workspace navigation" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Open navigation" }),
  ).toBeFocused();
});
