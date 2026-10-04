import { expect, test } from "@playwright/test";
import { fixture } from "../fixtures/workspace";

// Fixture-backed UI cases complement the real upload/CRUD regression suite.
test.beforeEach(async ({ page }) => {
  await page.route("**/api/workspace/projects", (route) =>
    route.fulfill({ json: [fixture.project] }),
  );
  await page.route("**/api/workspace/projects/*", (route) =>
    route.fulfill({ json: fixture }),
  );
  await page.route("**/api/workspace/projects/*/documents", (route) =>
    route.fulfill({ json: [] }),
  );
});

test("risk, pending and confirmed chips use distinct semantic colors in every record surface", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator('[data-status="HIGH"]').first()).toHaveCSS(
    "color",
    "rgb(185, 28, 28)",
  );
  await expect(page.locator('[data-status="PENDING"]').first()).toHaveCSS(
    "color",
    "rgb(154, 52, 18)",
  );
  await expect(
    page.locator('[data-status="NO_DUE_DATE"]').first(),
  ).toHaveAttribute("data-tone", "warning");
  for (const status of ["ACTIVE", "CONFIRMED"])
    await expect(page.locator(`[data-status="${status}"]`).first()).toHaveCSS(
      "color",
      "rgb(2, 107, 63)",
    );
  await page.goto("/?view=state&kind=risks");
  await expect(page.locator('[data-status="HIGH"]')).toHaveAttribute(
    "data-variant",
    "outline",
  );
  await expect(page.locator('[data-status="HIGH"]')).toHaveCSS(
    "color",
    "rgb(185, 28, 28)",
  );
  await page.goto("/?view=risks");
  await expect(page.locator('[data-status="HIGH"]')).toBeVisible();
  await expect(page.locator('[data-status="OPEN"]')).toHaveAttribute(
    "data-tone",
    "info",
  );
});

test("keyboard file browsing shows the selection and can clear it before upload", async ({
  page,
}) => {
  await page.goto("/?view=documents");
  const upload = page.getByRole("button", {
    name: "Upload document",
    exact: true,
  });
  await expect(upload).toBeDisabled();
  const browse = page.getByRole("button", {
    name: "Browse files",
    exact: true,
  });
  await browse.focus();
  const chooserPromise = page.waitForEvent("filechooser");
  await page.keyboard.press("Enter");
  await (
    await chooserPromise
  ).setFiles({
    name: "Project scope.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("# Scope\nProject evidence"),
  });
  await expect(
    page.getByText("Project scope.md", { exact: true }),
  ).toBeVisible();
  await expect(upload).toBeEnabled();
  await page.getByRole("button", { name: "Remove selected file" }).click();
  await expect(
    page.getByRole("button", { name: "Browse files", exact: true }),
  ).toBeVisible();
  await expect(upload).toBeDisabled();
});

test("invalid selection is explained and never starts an upload", async ({
  page,
}) => {
  await page.goto("/?view=documents");
  await page.getByLabel("Choose document").setInputFiles({
    name: "program.exe",
    mimeType: "application/octet-stream",
    buffer: Buffer.from("unsupported"),
  });
  await expect(
    page.getByRole("alert", { name: "Library error" }),
  ).toContainText("PDF, DOCX, TXT or Markdown");
  await expect(
    page.getByRole("button", { name: "Upload document", exact: true }),
  ).toBeDisabled();
  await page.getByLabel("Choose document").setInputFiles({
    name: "empty.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(""),
  });
  await expect(
    page.getByRole("alert", { name: "Library error" }),
  ).toContainText("nonempty file");
});

test("dragging a document selects it without uploading automatically", async ({
  page,
}) => {
  let uploads = 0;
  page.on("request", (request) => {
    if (request.method() === "POST") uploads++;
  });
  await page.goto("/?view=documents");
  const dataTransfer = await page.evaluateHandle(() => {
    const transfer = new DataTransfer();
    transfer.items.add(
      new File(["Synthetic evidence"], "Dropped scope.txt", {
        type: "text/plain",
      }),
    );
    return transfer;
  });
  await page
    .locator('[data-slot="document-picker"]')
    .dispatchEvent("drop", { dataTransfer });
  await expect(
    page.getByText("Dropped scope.txt", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Upload document", exact: true }),
  ).toBeEnabled();
  expect(uploads).toBe(0);
});
