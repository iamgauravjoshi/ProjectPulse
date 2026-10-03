import { expect, test } from "@playwright/test";
import { emptyWorkspace, fixture } from "../fixtures/workspace";

const projects = [
  {
    id: "b0b0fead-d9da-54f3-9fd2-aac6e7ab1a0d",
    name: "Client Portal Modernization",
    description: "Trusted demo baseline.",
  },
  {
    id: "4f76ce55-33b2-4a44-954c-03291c56b24b",
    name: "Discovery workstream",
    description: "A second workspace.",
  },
];

test("project selector supports keyboard switching and browser history", async ({
  page,
}) => {
  await page.route("**/api/workspace/projects", (route) =>
    route.fulfill({ json: projects }),
  );
  await page.route("**/api/workspace/projects/*", (route) =>
    route.fulfill({
      json: route.request().url().endsWith(projects[0].id)
        ? fixture
        : emptyWorkspace(projects[1]),
    }),
  );
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    projects[0].name,
  );
  const selector = page.getByRole("combobox", { name: "Project", exact: true });
  await selector.focus();
  await selector.press("ArrowDown");
  await page.keyboard.press("End");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(new RegExp(projects[1].id));
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    projects[1].name,
  );
  await page.goBack();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    projects[0].name,
  );
});

test("navigation is bookmarkable and the help dialog returns focus", async ({
  page,
}) => {
  await page.goto("/");
  const decisions = page.getByRole("link", { name: "Decisions", exact: true });
  await decisions.click();
  await expect(page).toHaveURL(/view=decisions/);
  await expect(decisions).toHaveAttribute("aria-current", "page");
  const help = page.getByRole("button", { name: "How ContextBoard works" });
  await help.click();
  await expect(page.getByRole("dialog")).toHaveAccessibleName(
    "From conversation to confirmed state",
  );
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(help).toBeFocused();
});

test("slow project loading shows an accessible skeleton", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/workspace/projects", async (route) => {
    await gate;
    await route.fulfill({ json: projects });
  });
  await page.goto("/");
  await expect(
    page.getByRole("status", { name: "Loading workspace" }),
  ).toBeVisible();
  release();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    projects[0].name,
  );
});

test("failed project request retries successfully", async ({ page }) => {
  let attempts = 0;
  await page.route("**/api/workspace/projects", (route) => {
    attempts += 1;
    return attempts === 1
      ? route.fulfill({ status: 503, json: { error: {} } })
      : route.fulfill({ json: projects });
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Projects couldn’t load" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    projects[0].name,
  );
});

test("empty project list has a truthful empty state", async ({ page }) => {
  await page.route("**/api/workspace/projects", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "No projects yet" }),
  ).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: "Project", exact: true }),
  ).toBeDisabled();
});

test("malformed project response is handled", async ({ page }) => {
  await page.route("**/api/workspace/projects", (route) =>
    route.fulfill({ json: [{ id: "wrong", name: null }] }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Projects couldn’t load" }),
  ).toBeVisible();
});

test("unavailable project does not fall through to another workspace", async ({
  page,
}) => {
  await page.goto("/?project=4f76ce55-33b2-4a44-954c-03291c56b24b");
  await expect(
    page.getByRole("heading", { name: "Project unavailable" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Choose available project" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    projects[0].name,
  );
});

test("unknown workspace view offers recovery", async ({ page }) => {
  await page.goto("/?view=missing");
  await expect(
    page.getByRole("heading", { name: "Page not found" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Back to overview" }).click();
  await expect(page).toHaveURL(/view=overview/);
});
