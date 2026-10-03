import { expect, test } from "@playwright/test";

test("workspace renders without browser errors on desktop and mobile", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await page.goto("/");
  await expect(page).toHaveTitle("ProjectPulse — Project workspace");
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Client Portal Modernization",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "Main navigation" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(
    page.getByRole("dialog", { name: "Workspace navigation" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Commitments", exact: true }).click();
  await expect(page).toHaveURL(/view=commitments/);
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});

test("live API reports migrated PostgreSQL readiness", async ({ request }) => {
  for (const endpoint of ["live", "ready"]) {
    const response = await request.get(
      `http://127.0.0.1:8010/health/${endpoint}`,
    );
    expect(response.status()).toBe(200);
    expect(await response.json()).toEqual({ status: "ok" });
  }
});
