import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";
import { fixture } from "../fixtures/workspace";
const root = `/api/workspace/projects/${fixture.project.id}`;
test("project memory journey: human baseline, document evidence, search, citations and cleanup", async ({
  page,
  request,
}) => {
  const keyword = `scope${randomUUID().replaceAll("-", "").slice(0, 10)}`;
  const title = `Human ${keyword}`;
  const filename = `Evidence ${keyword}.md`;
  let recordId: string | undefined;
  let documentId: string | undefined;
  try {
    await page.goto("/?view=state&kind=requirements");
    await page.getByRole("button", { name: "New record" }).click();
    await page.getByLabel("Title", { exact: true }).fill(title);
    await page
      .getByLabel("Description", { exact: true })
      .fill(`${keyword}: SSO remains in phase 2. A new checkpoint is phase 3.`);
    await page.getByLabel("Phase", { exact: true }).fill("3");
    await page.getByRole("button", { name: "Save record" }).click();
    await expect(
      page.getByRole("status", { name: "Save feedback" }),
    ).toContainText("created");
    recordId = (
      await (await request.get(`${root}/state/requirements`)).json()
    ).find((r: { title: string }) => r.title === title).id;
    await page.getByRole("link", { name: "Documents", exact: true }).click();
    await page.getByLabel("Choose document").setInputFiles({
      name: filename,
      mimeType: "text/markdown",
      buffer: Buffer.from(
        `# Release\n${keyword}: stakeholder evidence proposes phase 4, awaiting human review.`,
      ),
    });
    await page.getByRole("button", { name: "Upload document" }).click();
    await expect(
      page.getByRole("status", { name: "Library feedback" }),
    ).toContainText("uploaded");
    documentId = (await (await request.get(`${root}/documents`)).json()).find(
      (d: { filename: string }) => d.filename === filename,
    ).id;
    await page
      .getByRole("button", { name: `Index ${filename}`, exact: true })
      .click();
    await expect(
      page.getByRole("alert", { name: "Library error" }),
    ).toContainText("Configure GEMINI_API_KEY");
    await page
      .getByRole("link", { name: "Context search", exact: true })
      .click();
    await page.getByLabel("Context query").fill(keyword);
    await page
      .getByRole("button", { name: "Search context", exact: true })
      .click();
    await expect(
      page.getByRole("status", { name: "Search feedback" }),
    ).toContainText("2 results");
    await expect(
      page.getByText("Current baseline", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Document evidence", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText("Phase: 3")).toBeVisible();
    if (process.env.CAPTURE_MEMORY === "1") {
      await page.screenshot({
        path: "../../docs/features/images/memory-search-desktop.png",
        fullPage: true,
      });
      await page.setViewportSize({ width: 390, height: 844 });
      await page.screenshot({
        path: "../../docs/features/images/memory-search-mobile.png",
        fullPage: true,
      });
      await page.setViewportSize({ width: 1280, height: 800 });
    }
    await page.getByRole("link", { name: "Read source" }).click();
    await expect(page.getByRole("dialog")).toContainText("Release");
    await expect(page.getByRole("dialog")).toContainText(
      "awaiting human review",
    );
    await page.getByRole("button", { name: "Close", exact: true }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await page
      .getByRole("link", { name: "Context search", exact: true })
      .click();
    await page.getByLabel("Context query").fill(keyword);
    await page
      .getByRole("button", { name: "Search context", exact: true })
      .click();
    await page.getByRole("link", { name: "View baseline" }).click();
    await page
      .getByRole("button", { name: `Edit ${title}`, exact: true })
      .click();
    await expect(page.getByLabel("Phase", { exact: true })).toHaveValue("3");
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
  } finally {
    if (!recordId) {
      const rows = await (
        await request.get(`${root}/state/requirements`)
      ).json();
      recordId = rows.find((r: { title: string }) => r.title === title)?.id;
    }
    if (recordId) {
      const res = await request.get(`${root}/state/requirements/${recordId}`);
      if (res.ok()) {
        const r = await res.json();
        await request.delete(
          `${root}/state/requirements/${recordId}?expectedVersion=${r.version}`,
        );
      }
    }
    if (!documentId) {
      const docs = await (await request.get(`${root}/documents`)).json();
      documentId = docs.find(
        (d: { filename: string }) => d.filename === filename,
      )?.id;
    }
    if (documentId) await request.delete(`${root}/documents/${documentId}`);
  }
  await page.goto("/?view=context");
  await page.getByLabel("Context query").fill(keyword);
  await page
    .getByRole("button", { name: "Search context", exact: true })
    .click();
  await expect(
    page.getByText("No relevant project context found. Try another query."),
  ).toBeVisible();
});
test("search failure preserves query and retries explicitly on mobile", async ({
  page,
}) => {
  let calls = 0;
  await page.route("**/context/search?*", (route) => {
    calls++;
    return calls === 1
      ? route.fulfill({
          status: 503,
          json: { error: { message: "Temporarily unavailable" } },
        })
      : route.fulfill({
          json: {
            projectId: fixture.project.id,
            query: "SSO",
            semanticStatus: "unavailable",
            matches: [],
          },
        });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?view=context");
  await page.getByLabel("Context query").fill("SSO");
  await page
    .getByRole("button", { name: "Search context", exact: true })
    .click();
  await expect(page.getByRole("alert", { name: "Search error" })).toContainText(
    "unavailable",
  );
  await expect(page.getByLabel("Context query")).toHaveValue("SSO");
  await page
    .getByRole("button", { name: "Search context", exact: true })
    .click();
  await expect(
    page.getByRole("status", { name: "Search feedback" }),
  ).toContainText("0 results");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});
test("cross-project context payload is rejected", async ({ page }) => {
  await page.route("**/context/search?*", (route) =>
    route.fulfill({
      json: {
        projectId: "4f76ce55-33b2-4a44-954c-03291c56b24b",
        query: "SSO",
        semanticStatus: "ready",
        matches: [],
      },
    }),
  );
  await page.goto("/?view=context");
  await page.getByLabel("Context query").fill("SSO");
  await page
    .getByRole("button", { name: "Search context", exact: true })
    .click();
  await expect(page.getByRole("alert", { name: "Search error" })).toContainText(
    "Unexpected project context",
  );
  await expect(
    page.getByRole("status", { name: "Search feedback" }),
  ).toHaveCount(0);
});
