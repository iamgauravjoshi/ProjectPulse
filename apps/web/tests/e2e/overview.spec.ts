import { expect, test } from "@playwright/test";
import { emptyWorkspace, fixture } from "../fixtures/workspace";

test("seeded overview shows all six canonical categories and truthful counts", async ({
  page,
}) => {
  await page.goto("/");
  for (const title of [
    "Current project state",
    "Requirements",
    "Confirmed decisions",
    "Open commitments",
    "Risks",
    "Milestones",
    "Open questions",
    "Project activity",
  ]) {
    await expect(
      page.getByRole("heading", { name: title, exact: true }),
    ).toBeVisible();
  }
  const metrics = page.getByRole("region", { name: "Project statistics" });
  await expect(
    metrics.getByText("Confirmed decisions").locator(".."),
  ).toContainText("3");
  await expect(
    metrics.getByText("Open commitments").locator(".."),
  ).toContainText("1");
  await expect(page.getByText("Phase 2", { exact: true })).toBeVisible();
  await expect(page.getByText("24 Nov 2026", { exact: true })).toBeVisible();
  await expect(page.getByText("CSV export remains synchronous.")).toBeVisible();
  await expect(
    page.getByText("Retry failed payments three times."),
  ).toBeVisible();
  await expect(page.getByText("Due date not set")).toBeVisible();
  const activity = await (
    await page.request.get(`/api/workspace/projects/${fixture.project.id}`)
  ).json();
  expect(activity.activity.length).toBeGreaterThan(0);
  await expect(
    page
      .getByRole("heading", { name: "Project activity", exact: true })
      .locator("../.."),
  ).toContainText(/Project baseline established|Manual state|Document/);
});

test("decisions support search, status filter and empty results", async ({
  page,
}) => {
  await page.goto("/?view=decisions");
  await expect(
    page.getByRole("heading", { name: "Database", exact: true }),
  ).toBeVisible();
  await page.getByRole("textbox", { name: "Search decisions" }).fill("CSV");
  await expect(
    page.getByRole("heading", { name: "CSV export", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Database", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("combobox", { name: "Status", exact: true })
    .selectOption("PROVISIONAL");
  await expect(page.getByText("No records match your filters.")).toBeVisible();
});

test("empty baseline keeps every category usable", async ({ page }) => {
  await page.route("**/api/workspace/projects/*", (route) =>
    route.fulfill({ json: emptyWorkspace() }),
  );
  await page.goto("/");
  for (const text of [
    "No active requirements yet.",
    "No open commitments.",
    "No risks recorded.",
    "No milestones recorded.",
    "No open questions.",
    "No project activity yet.",
  ])
    await expect(page.getByText(text, { exact: true })).toBeVisible();
});

test("project detail error retries without losing the selected project", async ({
  page,
}) => {
  let attempts = 0;
  await page.route("**/api/workspace/projects/*", (route) => {
    attempts += 1;
    return attempts === 1
      ? route.fulfill({ status: 503, json: { error: {} } })
      : route.fulfill({ json: fixture });
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Project state couldn’t load" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    fixture.project.name,
  );
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText("Phase 2", { exact: true })).toBeVisible();
});

test("cross-project detail payload is rejected", async ({ page }) => {
  const data = structuredClone(fixture);
  data.requirements[0].projectId = "4f76ce55-33b2-4a44-954c-03291c56b24b";
  await page.route("**/api/workspace/projects/*", (route) =>
    route.fulfill({ json: data }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Project state couldn’t load" }),
  ).toBeVisible();
  await expect(page.getByText("Single sign-on", { exact: true })).toHaveCount(
    0,
  );
});
