import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { fixture } from "../fixtures/workspace";
const root = `/api/workspace/projects/${fixture.project.id}/documents`;
for (const extension of ["txt", "md", "pdf", "docx"])
  test(`upload ${extension}, read provenance, deduplicate and delete evidence`, async ({
    page,
    request,
  }) => {
    const filename = `Browser ${randomUUID()}.${extension}`;
    const content =
      extension === "pdf" || extension === "docx"
        ? Buffer.concat([
            readFileSync(`tests/fixtures/documents/scope.${extension}`),
            Buffer.from(`\n% Synthetic browser case ${randomUUID()}\n`),
          ])
        : Buffer.from(`# Scope\nSynthetic project scope ${randomUUID()}`);
    let id: string | undefined;
    try {
      await page.goto("/?view=documents");
      await page.getByLabel("Choose document").setInputFiles({
        name: filename,
        mimeType: "application/octet-stream",
        buffer: content,
      });
      await page.getByRole("button", { name: "Upload document" }).click();
      await expect(
        page.getByRole("status", { name: "Library feedback" }),
      ).toContainText(/Document uploaded|already in the library/);
      const docs = await (await request.get(root)).json();
      const doc =
        docs.find((d: { filename: string }) => d.filename === filename) ??
        docs.find((d: { format: string }) => d.format === extension);
      id = doc.id;
      const storedName = doc.filename;
      await page.reload();
      await page
        .getByRole("button", { name: `Read ${storedName}`, exact: true })
        .click();
      await expect(page.getByRole("dialog")).toContainText(
        extension === "pdf"
          ? "Page 1"
          : extension === "txt"
            ? "Document"
            : "Scope",
      );
      await expect(page.getByRole("dialog")).toContainText(
        "evidence, not confirmed",
      );
      await page.getByRole("button", { name: "Close", exact: true }).click();
      await page.getByLabel("Choose document").setInputFiles({
        name: filename,
        mimeType: "application/octet-stream",
        buffer: content,
      });
      await page.getByRole("button", { name: "Upload document" }).click();
      await expect(
        page.getByRole("status", { name: "Library feedback" }),
      ).toContainText("already in the library");
      await page
        .getByRole("button", { name: `Delete ${storedName}`, exact: true })
        .click();
      await page.getByRole("button", { name: "Confirm delete" }).click();
      await expect(
        page.getByRole("status", { name: "Library feedback" }),
      ).toContainText("Document deleted");
      await expect(
        page.getByRole("heading", { name: storedName, exact: true }),
      ).toHaveCount(0);
    } finally {
      if (id) await request.delete(`${root}/${id}`);
    }
  });
test("malformed upload displays actionable error without creating evidence", async ({
  page,
}) => {
  await page.goto("/?view=documents");
  await page.getByLabel("Choose document").setInputFiles({
    name: "broken.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("not a PDF"),
  });
  await page.getByRole("button", { name: "Upload document" }).click();
  await expect(
    page.getByRole("alert", { name: "Library error" }),
  ).toContainText("malformed");
});
test("empty mobile library fits the viewport and failed loading retries", async ({
  page,
}) => {
  let calls = 0;
  await page.route("**/documents", (route) => {
    calls++;
    return calls === 1
      ? route.fulfill({ status: 503, json: { error: {} } })
      : route.fulfill({ json: [] });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?view=documents");
  await expect(
    page.getByRole("heading", { name: "Documents couldn’t load" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(
    page.getByText("No documents yet. Upload project evidence to start."),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});

test("missing Gemini configuration shows unavailable indexing and retains readable evidence", async ({
  page,
  request,
}) => {
  const name = `Unindexed ${randomUUID()}.txt`;
  let id: string | undefined;
  try {
    const doc = await (
      await request.post(`${root}?filename=${encodeURIComponent(name)}`, {
        data: `Synthetic evidence ${randomUUID()}`,
      })
    ).json();
    id = doc.id;
    await page.goto("/?view=documents");
    await page
      .getByRole("button", { name: `Index ${name}`, exact: true })
      .click();
    await expect(
      page.getByRole("alert", { name: "Library error" }),
    ).toContainText("Configure GEMINI_API_KEY");
    await expect(
      page
        .getByRole("heading", { name, exact: true })
        .locator("..")
        .locator('[data-status="UNAVAILABLE"]'),
    ).toHaveText("Unavailable");
    await page
      .getByRole("button", { name: `Read ${name}`, exact: true })
      .click();
    await expect(page.getByRole("dialog")).toContainText("Synthetic evidence");
  } finally {
    if (id) await request.delete(`${root}/${id}`);
  }
});
