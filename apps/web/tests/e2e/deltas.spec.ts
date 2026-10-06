import { randomUUID } from "node:crypto";
import {
  test,
  expect,
  type APIRequestContext,
  type Page,
  type Locator,
} from "@playwright/test";
import { fixture } from "../fixtures/workspace";
const projectId = fixture.project.id,
  root = `/api/workspace/projects/${projectId}/meetings`;
const href = (id: string) =>
  `/?project=${projectId}&view=meetings&meeting=${id}`;
const region = (page: Page) =>
  page.getByRole("region", { name: "Project comparisons", exact: true });
async function metric(panel: Locator, label: string, value: number) {
  await expect(
    panel
      .locator("dl > div")
      .filter({ has: panel.page().getByText(label, { exact: true }) })
      .locator("dd"),
  ).toHaveText(String(value));
}
async function create(
  request: APIRequestContext,
  texts: string[],
  analyze = true,
  extract = true,
) {
  const response = await request.post(root, {
    data: { title: `Delta acceptance ${randomUUID()}` },
  });
  expect(response.status()).toBe(201);
  const meeting = await response.json();
  if (texts.length) {
    expect(
      (
        await request.post(
          `${root}/${meeting.id}/transcript?filename=deltas.json`,
          {
            headers: { "Content-Type": "application/octet-stream" },
            data: Buffer.from(
              JSON.stringify(
                texts.map((text, i) => ({
                  speaker: "Sarah",
                  timestamp: `00:${String(Math.floor(i / 60)).padStart(2, "0")}:${String(i % 60).padStart(2, "0")}`,
                  text,
                })),
              ),
            ),
          },
        )
      ).status(),
    ).toBe(201);
    if (analyze)
      expect(
        (await request.post(`${root}/${meeting.id}/relevance`)).ok(),
      ).toBeTruthy();
    if (extract)
      for (let i = 0; i < Math.ceil(texts.length / 20); i++)
        expect(
          (await request.post(`${root}/${meeting.id}/events`)).ok(),
        ).toBeTruthy();
  }
  return meeting;
}
test("all outcomes preserve versioned baseline, literal dates, citations and canonical state", async ({
  page,
  request,
}) => {
  const m = await create(request, [
    "SSO Phase 1 proposal.",
    "SSO same-baseline.",
    "SSO risk new-item.",
    "SSO question ownership.",
    "SSO commitment John tomorrow.",
    "SSO milestone November 10.",
    "SSO milestone negated.",
    "SSO risk low-confidence.",
    "Good morning.",
  ]);
  const before = await (
    await request.get(`/api/workspace/projects/${projectId}`)
  ).json();
  try {
    await page.goto(href(m.id));
    const panel = region(page);
    await panel
      .getByRole("button", { name: "Compare with project state", exact: true })
      .click();
    await metric(panel, "Compared candidates", 8);
    await metric(panel, "Possible changes", 3);
    await metric(panel, "Consistent with baseline", 1);
    await metric(panel, "Potential new items", 1);
    await metric(panel, "Needs clarification", 3);
    await expect(
      panel.getByRole("button", { name: "Comparison complete", exact: true }),
    ).toBeDisabled();
    await expect(
      panel
        .locator("dd")
        .filter({ hasText: "Proposed wording" })
        .filter({ hasText: "tomorrow" }),
    ).toBeVisible();
    await expect(
      panel
        .locator("dd")
        .filter({ hasText: "Proposed wording" })
        .filter({ hasText: "November 10" }),
    ).toBeVisible();
    const saved = await (await request.get(`${root}/${m.id}/deltas`)).json();
    expect(saved.items[0].target.values.phase).toBe(2);
    expect(saved.items[0].target.version).toBeGreaterThan(0);
    expect(saved.items[0].changes[0].previousValue).toBe(2);
    expect(
      saved.items.every((x: { status: string }) => x.status === "CANDIDATE"),
    ).toBeTruthy();
    await panel
      .getByLabel("Show comparison outcome", { exact: true })
      .selectOption("CHANGE");
    await expect(panel.getByRole("listitem")).toHaveCount(3);
    await panel
      .getByRole("link", { name: "View comparison source 5", exact: true })
      .click();
    const detail = await (await request.get(`${root}/${m.id}`)).json();
    await expect(
      page.locator(`#utterance-${detail.utterances[4].id}`),
    ).toBeFocused();
    await page.reload();
    await expect(
      page.locator(`#utterance-${detail.utterances[4].id}`),
    ).toBeFocused();
    const again = await (await request.post(`${root}/${m.id}/deltas`)).json();
    expect(again.items.map((x: { id: string }) => x.id)).toEqual(
      saved.items.map((x: { id: string }) => x.id),
    );
    expect(again.run.apiCalls).toBe(1);
    const after = await (
      await request.get(`/api/workspace/projects/${projectId}`)
    ).json();
    for (const key of [
      "requirements",
      "decisions",
      "commitments",
      "risks",
      "milestones",
      "dependencies",
      "questions",
      "members",
    ])
      expect(after[key]).toEqual(before[key]);
    if (process.env.CAPTURE_DELTAS === "1") {
      await panel.getByLabel("Show comparison outcome").selectOption("CHANGE");
      await expect(panel.getByRole("listitem")).toHaveCount(3);
      await panel.screenshot({ path: "test-results/deltas-desktop.png" });
      await page.setViewportSize({ width: 375, height: 812 });
      await panel.screenshot({ path: "test-results/deltas-mobile.png" });
    }
  } finally {
    await request.delete(`${root}/${m.id}`);
  }
});
test("analysis and extraction unlock comparison without reloading", async ({
  page,
  request,
}) => {
  const m = await create(request, ["SSO Phase 1 proposal."], false, false);
  try {
    await page.goto(href(m.id));
    const panel = region(page);
    await expect(
      panel.getByRole("button", {
        name: "Compare with project state",
        exact: true,
      }),
    ).toBeDisabled();
    await page
      .getByRole("region", { name: "Meeting impact", exact: true })
      .getByRole("button", { name: "Analyze relevance", exact: true })
      .click();
    await expect(
      panel.getByText("Extract current event candidates first", {
        exact: true,
      }),
    ).toBeVisible();
    await page
      .getByRole("region", { name: "Project event candidates", exact: true })
      .getByRole("button", { name: "Extract event candidates", exact: true })
      .click();
    await expect(
      panel.getByRole("button", {
        name: "Compare with project state",
        exact: true,
      }),
    ).toBeEnabled();
    await panel
      .getByRole("button", { name: "Compare with project state", exact: true })
      .click();
    await metric(panel, "Compared candidates", 1);
  } finally {
    await request.delete(`${root}/${m.id}`);
  }
});
test("provider failure leaves pending work and explicit retries", async ({
  page,
  request,
}) => {
  const m = await create(request, ["SSO delta-failure."]);
  try {
    await page.goto(href(m.id));
    const panel = region(page);
    await panel
      .getByRole("button", { name: "Compare with project state", exact: true })
      .click();
    await expect(
      panel.getByRole("alert", { name: "Comparison provider error" }),
    ).toBeVisible();
    await metric(panel, "Pending comparisons", 1);
    await expect(panel.getByRole("listitem")).toHaveCount(0);
    await panel
      .getByRole("button", { name: "Retry comparison", exact: true })
      .click();
    await expect
      .poll(
        async () =>
          (await (await request.get(`${root}/${m.id}/deltas`)).json()).run
            .apiCalls,
      )
      .toBe(2);
  } finally {
    await request.delete(`${root}/${m.id}`);
  }
});
test("zero-event extraction completes without fabricated comparisons", async ({
  page,
  request,
}) => {
  const m = await create(request, ["SSO no-event."]);
  try {
    await page.goto(href(m.id));
    const panel = region(page);
    await panel
      .getByRole("button", { name: "Compare with project state", exact: true })
      .click();
    await expect(
      panel.getByText("No candidates to compare", { exact: true }),
    ).toBeVisible();
    await expect(
      panel.getByRole("button", { name: "Comparison complete", exact: true }),
    ).toBeDisabled();
    const data = await (await request.get(`${root}/${m.id}/deltas`)).json();
    expect(data.run.apiCalls).toBe(0);
  } finally {
    await request.delete(`${root}/${m.id}`);
  }
});
test("batches, later pages and empty filters retain source navigation", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const m = await create(
    request,
    Array.from({ length: 105 }, (_, i) => `SSO Phase 1 proposal ${i}.`),
  );
  try {
    const first = await (await request.post(`${root}/${m.id}/deltas`)).json();
    expect(first.counts.pending).toBe(85);
    for (let i = 0; i < 5; i++)
      expect((await request.post(`${root}/${m.id}/deltas`)).ok()).toBeTruthy();
    await page.goto(href(m.id));
    const panel = region(page);
    await expect(panel.getByRole("listitem")).toHaveCount(100);
    await panel
      .getByRole("button", { name: "Next comparisons", exact: true })
      .click();
    await expect(panel.getByRole("listitem")).toHaveCount(5);
    await panel
      .getByRole("link", { name: "View comparison source 105", exact: true })
      .click();
    await expect(
      page.getByRole("status", { name: "Transcript page" }),
    ).toHaveText("Page 2 of 2");
    await panel.getByLabel("Show comparison outcome").selectOption("NEW");
    await expect(
      panel.getByText("No comparisons match this filter", { exact: true }),
    ).toBeVisible();
  } finally {
    await request.delete(`${root}/${m.id}`);
  }
});
test("baseline changes retain historical comparisons and require current extraction", async ({
  page,
  request,
}) => {
  const m = await create(request, ["SSO Phase 1 proposal."]);
  let record: { id: string; version: number } | undefined;
  try {
    await request.post(`${root}/${m.id}/deltas`);
    const response = await request.post(
      `/api/workspace/projects/${projectId}/state/requirements`,
      {
        data: {
          title: `Delta context ${randomUUID()}`,
          status: "ACTIVE",
          phase: 1,
        },
      },
    );
    expect(response.status()).toBe(201);
    record = await response.json();
    await page.goto(href(m.id));
    const panel = region(page);
    await expect(
      panel.getByRole("status", { name: "Stale comparisons" }),
    ).toBeVisible();
    await expect(panel.getByRole("listitem")).toHaveCount(1);
    await expect(
      panel.getByRole("button", {
        name: "Compare current baseline",
        exact: true,
      }),
    ).toBeDisabled();
    expect((await request.post(`${root}/${m.id}/deltas`)).status()).toBe(409);
  } finally {
    await request.delete(`${root}/${m.id}`);
    if (record)
      await request.delete(
        `/api/workspace/projects/${projectId}/state/requirements/${record.id}?expectedVersion=${record.version}`,
      );
  }
});
test("read and write outages preserve transcript and support recovery", async ({
  page,
  request,
}) => {
  const m = await create(request, ["SSO Phase 1 proposal."]),
    url = `**/meetings/${m.id}/deltas*`;
  try {
    await page.route(url, (r) =>
      r.fulfill({
        status: 503,
        json: { error: { message: "Synthetic comparison outage" } },
      }),
    );
    await page.goto(href(m.id));
    const panel = region(page);
    await expect(
      panel.getByRole("heading", {
        name: "Project comparisons couldn’t load",
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page
        .locator('[id^="utterance-"]')
        .getByText("SSO Phase 1 proposal.", { exact: true }),
    ).toBeVisible();
    await page.unroute(url);
    await panel.getByRole("button", { name: "Try again", exact: true }).click();
    await page.route(url, (r) =>
      r.request().method() === "POST"
        ? r.fulfill({
            status: 503,
            json: { error: { message: "Synthetic write outage" } },
          })
        : r.continue(),
    );
    await panel
      .getByRole("button", { name: "Compare with project state", exact: true })
      .click();
    await expect(panel.getByRole("alert")).toBeVisible();
    await page.unroute(url);
    await panel
      .getByRole("button", { name: "Compare with project state", exact: true })
      .click();
    await metric(panel, "Compared candidates", 1);
  } finally {
    await request.delete(`${root}/${m.id}`);
  }
});
for (const width of [320, 375])
  test(`mobile keyboard operation wraps and keeps comparisons accessible at ${width}px`, async ({
    page,
    request,
  }) => {
    const m = await create(request, ["SSO Phase 1 proposal."]);
    try {
      await page.setViewportSize({ width, height: 812 });
      await page.goto(href(m.id));
      const panel = region(page),
        button = panel.getByRole("button", {
          name: "Compare with project state",
          exact: true,
        });
      await button.focus();
      await page.keyboard.press("Enter");
      await metric(panel, "Compared candidates", 1);
      await panel.getByLabel("Show comparison outcome").focus();
      await page.keyboard.press("ArrowDown");
      await page.keyboard.press("Enter");
      await expect
        .poll(() =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= window.innerWidth,
          ),
        )
        .toBe(true);
    } finally {
      await request.delete(`${root}/${m.id}`);
    }
  });
