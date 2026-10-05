import { randomUUID } from "node:crypto";
import {
  test,
  expect,
  type APIRequestContext,
  type Locator,
} from "@playwright/test";
import { fixture } from "../fixtures/workspace";
const projectId = fixture.project.id,
  root = `/api/workspace/projects/${projectId}/meetings`;
async function create(
  request: APIRequestContext,
  texts: string[],
  analyze = true,
) {
  const response = await request.post(root, {
    data: { title: `Events acceptance ${randomUUID()}` },
  });
  expect(response.status()).toBe(201);
  const m = await response.json();
  if (texts.length) {
    expect(
      (
        await request.post(`${root}/${m.id}/transcript?filename=events.json`, {
          headers: { "Content-Type": "application/octet-stream" },
          data: Buffer.from(
            JSON.stringify(texts.map((text) => ({ speaker: "Sarah", text }))),
          ),
        })
      ).status(),
    ).toBe(201);
    if (analyze)
      expect(
        (await request.post(`${root}/${m.id}/relevance`)).ok(),
      ).toBeTruthy();
  }
  return m;
}
async function metric(panel: Locator, label: string, value: number) {
  await expect(
    panel
      .locator("dl > div")
      .filter({ has: panel.page().getByText(label, { exact: true }) })
      .locator("dd"),
  ).toHaveText(String(value));
}
const region = (page: import("@playwright/test").Page) =>
  page.getByRole("region", { name: "Project event candidates", exact: true });
const href = (id: string) =>
  `/?project=${projectId}&view=meetings&meeting=${id}`;
const normal = [
  "SSO proposal requirement.",
  "SSO decision proposal.",
  "SSO commitment John tomorrow.",
  "SSO risk low-confidence.",
  "SSO milestone negated.",
  "SSO dependency proposal.",
  "SSO question ownership.",
  "SSO no-event.",
  "Good morning.",
];
test("seven kinds persist with exact citations, proposal and negation, unknown owner and unchanged canonical state", async ({
  page,
  request,
}) => {
  const m = await create(request, normal),
    before = await (
      await request.get(`/api/workspace/projects/${projectId}`)
    ).json();
  try {
    await page.goto(href(m.id));
    const panel = region(page);
    await panel
      .getByRole("button", { name: "Extract event candidates", exact: true })
      .click();
    await metric(panel, "Processed segments", 8);
    await metric(panel, "Event candidates", 7);
    await metric(panel, "Segments without events", 1);
    await metric(panel, "Low-confidence candidates", 1);
    await expect(
      panel.getByRole("button", { name: "Extraction complete", exact: true }),
    ).toBeDisabled();
    const saved = await (await request.get(`${root}/${m.id}/events`)).json();
    expect(new Set(saved.items.map((x: { kind: string }) => x.kind)).size).toBe(
      7,
    );
    expect(
      saved.items.every((x: { status: string }) => x.status === "CANDIDATE"),
    ).toBeTruthy();
    await expect(panel.getByText("Negated", { exact: true })).toBeVisible();
    await expect(
      panel.getByText("Needs review", { exact: true }),
    ).toBeVisible();
    const commitment = panel.getByRole("listitem").filter({
      has: page.getByRole("heading", {
        name: "Synthetic commitment",
        exact: true,
      }),
    });
    await expect(commitment.getByText("John", { exact: true })).toBeVisible();
    await expect(
      commitment.getByText("tomorrow", { exact: true }),
    ).toBeVisible();
    await expect(
      commitment.getByText("Sarah · unlinked speaker", { exact: true }),
    ).toBeVisible();
    await panel
      .getByLabel("Show event kind", { exact: true })
      .selectOption("OPEN_QUESTION");
    await expect(panel.getByRole("listitem")).toHaveCount(1);
    await expect(panel.getByText("Unknown", { exact: true })).toBeVisible();
    await panel
      .getByRole("link", { name: "View event source 7", exact: true })
      .click();
    const detail = await (await request.get(`${root}/${m.id}`)).json();
    await expect(
      page.locator(`#utterance-${detail.utterances[6].id}`),
    ).toBeFocused();
    await page.reload();
    await expect(
      page.locator(`#utterance-${detail.utterances[6].id}`),
    ).toBeFocused();
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
    const fresh = await (await request.post(`${root}/${m.id}/events`)).json();
    expect(fresh.items.map((x: { id: string }) => x.id)).toEqual(
      saved.items.map((x: { id: string }) => x.id),
    );
    expect(fresh.extraction.apiCalls).toBe(1);
    if (process.env.CAPTURE_EVENTS === "1") {
      await panel
        .getByLabel("Show event kind", { exact: true })
        .selectOption("COMMITMENT");
      await expect(panel.getByRole("listitem")).toHaveCount(1);
      await panel.screenshot({ path: "test-results/events-desktop.png" });
      await page.setViewportSize({ width: 375, height: 812 });
      await panel.screenshot({ path: "test-results/events-mobile.png" });
    }
  } finally {
    await request.delete(`${root}/${m.id}`);
  }
});
test("relevance prerequisite updates immediately after explicit analysis", async ({
  page,
  request,
}) => {
  const m = await create(request, ["SSO proposal."], false);
  try {
    await page.goto(href(m.id));
    const panel = region(page);
    await expect(
      panel.getByText("Analyze relevance first", { exact: true }),
    ).toBeVisible();
    await expect(
      panel.getByRole("button", {
        name: "Extract event candidates",
        exact: true,
      }),
    ).toBeDisabled();
    await page
      .getByRole("region", { name: "Meeting impact", exact: true })
      .getByRole("button", { name: "Analyze relevance", exact: true })
      .click();
    await metric(panel, "Eligible segments", 1);
    await panel
      .getByRole("button", { name: "Extract event candidates", exact: true })
      .click();
    await metric(panel, "Event candidates", 1);
  } finally {
    await request.delete(`${root}/${m.id}`);
  }
});
test("provider failure stays pending and a deliberate retry never fabricates results", async ({
  page,
  request,
}) => {
  const m = await create(request, ["SSO provider-failure."]);
  try {
    await page.goto(href(m.id));
    const panel = region(page);
    await panel
      .getByRole("button", { name: "Extract event candidates", exact: true })
      .click();
    await expect(
      panel.getByRole("alert", { name: "Event provider error" }),
    ).toBeVisible();
    await metric(panel, "Processed segments", 0);
    await metric(panel, "Pending event segments", 1);
    await panel
      .getByRole("button", { name: "Retry event extraction", exact: true })
      .click();
    await expect(
      panel.getByRole("alert", { name: "Event provider error" }),
    ).toBeVisible();
    await metric(panel, "Event candidates", 0);
    expect(
      (await (await request.get(`${root}/${m.id}/events`)).json()).extraction
        .apiCalls,
    ).toBe(2);
  } finally {
    await request.delete(`${root}/${m.id}`);
  }
});
test("zero events completes eligible coverage without suggesting confirmed change", async ({
  page,
  request,
}) => {
  const m = await create(request, ["SSO no-event.", "Good morning."]);
  try {
    await page.goto(href(m.id));
    const panel = region(page);
    await panel
      .getByRole("button", { name: "Extract event candidates", exact: true })
      .click();
    await metric(panel, "Processed segments", 1);
    await metric(panel, "Segments without events", 1);
    await expect(
      panel.getByText("No event candidates found", { exact: true }),
    ).toBeVisible();
    await expect(
      panel.getByRole("button", { name: "Extraction complete", exact: true }),
    ).toBeDisabled();
  } finally {
    await request.delete(`${root}/${m.id}`);
  }
});
test("bounded batches and pagination retain ordered citations on later transcript pages", async ({
  page,
  request,
}) => {
  test.setTimeout(90000);
  const m = await create(
    request,
    Array.from({ length: 105 }, (_, i) => `SSO ${i} proposal.`),
  );
  try {
    for (let i = 0; i < 6; i++)
      expect((await request.post(`${root}/${m.id}/events`)).ok()).toBeTruthy();
    await page.goto(href(m.id));
    const panel = region(page);
    await metric(panel, "Processed segments", 105);
    await expect(panel.getByRole("listitem")).toHaveCount(100);
    await panel
      .getByRole("button", { name: "Next candidates", exact: true })
      .click();
    await expect(panel.getByRole("listitem")).toHaveCount(5);
    await expect(
      panel.getByRole("status", { name: "Candidate page" }),
    ).toHaveText("Page 2 of 2");
    await panel
      .getByRole("link", { name: "View event source 105", exact: true })
      .click();
    await expect(
      page.getByRole("status", { name: "Transcript page" }),
    ).toHaveText("Page 2 of 2");
    await panel
      .getByLabel("Show event kind", { exact: true })
      .selectOption("RISK");
    await expect(
      panel.getByRole("status", { name: "Candidate page" }),
    ).toHaveText("Page 1 of 1");
    await expect(panel.getByRole("listitem")).toHaveCount(0);
  } finally {
    await request.delete(`${root}/${m.id}`);
  }
});
test("baseline changes mark candidates stale and require current relevance", async ({
  page,
  request,
}) => {
  const m = await create(request, ["SSO proposal."]);
  let record: { id: string; version: number } | undefined;
  try {
    await request.post(`${root}/${m.id}/events`);
    const saved = await (await request.get(`${root}/${m.id}/events`)).json();
    const r = await request.post(
      `/api/workspace/projects/${projectId}/state/requirements`,
      {
        data: {
          title: `Event context ${randomUUID()}`,
          status: "ACTIVE",
          phase: 1,
        },
      },
    );
    expect(r.status()).toBe(201);
    record = await r.json();
    await page.goto(href(m.id));
    const panel = region(page);
    await expect(
      panel.getByRole("status", { name: "Stale event candidates" }),
    ).toBeVisible();
    await expect(
      panel.getByRole("button", {
        name: "Extract for current baseline",
        exact: true,
      }),
    ).toBeDisabled();
    await page
      .getByRole("region", { name: "Meeting impact", exact: true })
      .getByRole("button", { name: "Analyze current baseline", exact: true })
      .click();
    await expect(
      panel.getByRole("button", {
        name: "Extract for current baseline",
        exact: true,
      }),
    ).toBeEnabled();
    await panel
      .getByRole("button", {
        name: "Extract for current baseline",
        exact: true,
      })
      .click();
    await expect(
      panel.getByRole("status", { name: "Stale event candidates" }),
    ).toHaveCount(0);
    const fresh = await (await request.get(`${root}/${m.id}/events`)).json();
    expect(fresh.extraction.id).not.toBe(saved.extraction.id);
  } finally {
    await request.delete(`${root}/${m.id}`);
    if (record)
      await request.delete(
        `/api/workspace/projects/${projectId}/state/requirements/${record.id}?expectedVersion=${record.version}`,
      );
  }
});
test("read and write outages preserve evidence and enable explicit recovery", async ({
  page,
  request,
}) => {
  const m = await create(request, ["SSO proposal."]),
    url = `**/meetings/${m.id}/events*`;
  try {
    await page.route(url, (r) =>
      r.fulfill({
        status: 503,
        json: { error: { message: "Synthetic event outage" } },
      }),
    );
    await page.goto(href(m.id));
    const panel = region(page);
    await expect(
      panel.getByRole("heading", {
        name: "Event candidates couldn’t load",
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page
        .locator('[id^="utterance-"]')
        .getByText("SSO proposal.", { exact: true }),
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
      .getByRole("button", { name: "Extract event candidates", exact: true })
      .click();
    await expect(
      panel.getByRole("alert", { name: "Event extraction error" }),
    ).toContainText("Synthetic write outage");
    await metric(panel, "Pending event segments", 1);
    await page.unroute(url);
    await panel
      .getByRole("button", { name: "Extract event candidates", exact: true })
      .click();
    await metric(panel, "Event candidates", 1);
  } finally {
    await request.delete(`${root}/${m.id}`);
  }
});
test("mobile keyboard extraction and emoji evidence fit the viewport", async ({
  page,
  request,
}) => {
  const m = await create(request, ["SSO " + "🚀".repeat(550)]);
  try {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(href(m.id));
    const panel = region(page),
      button = panel.getByRole("button", {
        name: "Extract event candidates",
        exact: true,
      });
    await button.focus();
    await page.keyboard.press("Enter");
    await metric(panel, "Event candidates", 1);
    await expect(panel.locator("blockquote")).toContainText("🚀".repeat(496));
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    await panel
      .getByRole("link", { name: "View event source 1", exact: true })
      .focus();
    await page.keyboard.press("Enter");
    const detail = await (await request.get(`${root}/${m.id}`)).json();
    await expect(
      page.locator(`#utterance-${detail.utterances[0].id}`),
    ).toBeFocused();
  } finally {
    await request.delete(`${root}/${m.id}`);
  }
});
test("empty evidence explains the upload prerequisite", async ({
  page,
  request,
}) => {
  const m = await create(request, []);
  try {
    await page.goto(href(m.id));
    const panel = region(page);
    await expect(
      panel.getByText("Awaiting meeting evidence", { exact: true }),
    ).toBeVisible();
    await expect(
      panel.getByRole("button", {
        name: "Extract event candidates",
        exact: true,
      }),
    ).toBeDisabled();
  } finally {
    await request.delete(`${root}/${m.id}`);
  }
});
