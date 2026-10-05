import { randomUUID } from "node:crypto";
import {
  expect,
  test,
  type APIRequestContext,
  type Locator,
} from "@playwright/test";
import { fixture } from "../fixtures/workspace";
const projectId = fixture.project.id;
const root = `/api/workspace/projects/${projectId}/meetings`;
async function create(request: APIRequestContext, texts: string[]) {
  const result = await request.post(root, {
    data: { title: `Relevance test ${randomUUID()}` },
  });
  expect(result.status()).toBe(201);
  const meeting = await result.json();
  if (texts.length) {
    const upload = await request.post(
      `${root}/${meeting.id}/transcript?filename=relevance.json`,
      {
        headers: { "Content-Type": "application/octet-stream" },
        data: Buffer.from(
          JSON.stringify(texts.map((text) => ({ speaker: "Sarah", text }))),
        ),
      },
    );
    expect(upload.status()).toBe(201);
  }
  return meeting;
}
async function metric(impact: Locator, label: string, value: number) {
  await expect(
    impact
      .locator("dl > div")
      .filter({ has: impact.page().getByText(label, { exact: true }) })
      .locator("dd"),
  ).toHaveText(String(value));
}
const normal = [
  "I went hiking this weekend.",
  "Good morning.",
  "Move the launch to November 10.",
  "SSO stays in Phase 2.",
];

test("real relevance rules persist metrics citations cache and unchanged baseline", async ({
  page,
  request,
}) => {
  const meeting = await create(request, normal);
  const before = await (
    await request.get(`/api/workspace/projects/${projectId}`)
  ).json();
  try {
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}`,
    );
    const impact = page.getByRole("region", {
      name: "Meeting impact",
      exact: true,
    });
    await expect(
      impact.getByText("Relevance has not been analyzed", { exact: true }),
    ).toBeVisible();
    await impact
      .getByRole("button", { name: "Analyze relevance", exact: true })
      .click();
    await metric(impact, "Conversation segments analyzed", 4);
    await metric(impact, "Project-relevant segments", 2);
    await metric(impact, "Ignored segments", 2);
    await metric(impact, "Pending segments", 0);
    await expect(
      impact.getByRole("status", { name: "Ignored conversation share" }),
    ).toContainText("50%");
    await expect(
      impact.getByRole("button", { name: "Analysis complete", exact: true }),
    ).toBeDisabled();
    const saved = await (
      await request.get(`${root}/${meeting.id}/relevance`)
    ).json();
    expect(saved.analysis.apiCalls).toBe(0);
    await impact
      .getByLabel("Show relevance", { exact: true })
      .selectOption("IGNORED");
    await expect(impact.getByRole("listitem")).toHaveCount(2);
    await expect(impact.getByRole("list")).not.toContainText("Move the launch");
    await impact
      .getByRole("link", { name: "View source utterance 1", exact: true })
      .click();
    const detail = await (await request.get(`${root}/${meeting.id}`)).json();
    await expect(
      page.locator(`#utterance-${detail.utterances[0].id}`),
    ).toHaveAttribute("aria-current", "location");
    await page.reload();
    await metric(impact, "Conversation segments analyzed", 4);
    await expect(
      page.locator(`#utterance-${detail.utterances[0].id}`),
    ).toBeInViewport();
    await expect(
      page.locator(`#utterance-${detail.utterances[0].id}`),
    ).toBeFocused();
    expect(
      (await (await request.get(`${root}/${meeting.id}/relevance`)).json())
        .analysis.id,
    ).toBe(saved.analysis.id);
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
    if (process.env.CAPTURE_RELEVANCE === "1") {
      await page.screenshot({
        path: "../../docs/features/images/relevance-desktop.png",
        fullPage: true,
      });
      await page.setViewportSize({ width: 375, height: 812 });
      await page.screenshot({
        path: "../../docs/features/images/relevance-mobile.png",
        fullPage: true,
      });
    }
  } finally {
    await request.delete(`${root}/${meeting.id}`);
  }
});

test("missing AI configuration leaves ambiguous segments pending with honest denominator", async ({
  page,
  request,
}) => {
  const meeting = await create(request, [
    ...normal,
    "The login button fails QA.",
  ]);
  try {
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}`,
    );
    const impact = page.getByRole("region", {
      name: "Meeting impact",
      exact: true,
    });
    await impact
      .getByRole("button", { name: "Analyze relevance", exact: true })
      .click();
    await metric(impact, "Conversation segments analyzed", 4);
    await metric(impact, "Pending segments", 1);
    await metric(impact, "Ignored segments", 2);
    await expect(
      impact.getByRole("alert", { name: "Relevance provider error" }),
    ).toContainText("remaining segments have not been classified");
    await expect(
      impact.getByRole("status", { name: "Ignored conversation share" }),
    ).toContainText("does not represent the whole meeting");
    await expect(
      impact.getByRole("button", {
        name: "Retry remaining segments",
        exact: true,
      }),
    ).toBeEnabled();
  } finally {
    await request.delete(`${root}/${meeting.id}`);
  }
});

test("changed manual baseline marks saved relevance stale and explicit analysis refreshes", async ({
  page,
  request,
}) => {
  const meeting = await create(request, normal);
  let record: { id: string; version: number } | undefined;
  try {
    expect(
      (await request.post(`${root}/${meeting.id}/relevance`)).ok(),
    ).toBeTruthy();
    const result = await request.post(
      `/api/workspace/projects/${projectId}/state/requirements`,
      {
        data: {
          title: `QA context ${randomUUID()}`,
          status: "ACTIVE",
          phase: 1,
        },
      },
    );
    expect(result.status()).toBe(201);
    record = await result.json();
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}`,
    );
    const impact = page.getByRole("region", {
      name: "Meeting impact",
      exact: true,
    });
    await expect(
      impact.getByRole("status", { name: "Stale relevance" }),
    ).toBeVisible();
    await impact
      .getByRole("button", { name: "Analyze current baseline", exact: true })
      .click();
    await expect(
      impact.getByRole("status", { name: "Stale relevance" }),
    ).toHaveCount(0);
    await expect(
      impact.getByRole("button", { name: "Analysis complete", exact: true }),
    ).toBeDisabled();
  } finally {
    await request.delete(`${root}/${meeting.id}`);
    if (record)
      await request.delete(
        `/api/workspace/projects/${projectId}/state/requirements/${record.id}?expectedVersion=${record.version}`,
      );
  }
});

test("long relevance pagination and filters preserve ordered source citations", async ({
  page,
  request,
}) => {
  const meeting = await create(
    request,
    Array.from({ length: 205 }, (_, i) =>
      i % 2 ? "Good morning." : "SSO stays in Phase 2.",
    ),
  );
  try {
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}`,
    );
    const impact = page.getByRole("region", {
      name: "Meeting impact",
      exact: true,
    });
    await impact
      .getByRole("button", { name: "Analyze relevance", exact: true })
      .click();
    await metric(impact, "Conversation segments analyzed", 205);
    await impact
      .getByRole("button", { name: "Next relevance", exact: true })
      .click();
    await expect(
      impact.getByRole("status", { name: "Relevance page" }),
    ).toHaveText("Page 2 of 3");
    await expect(
      impact.getByRole("link", {
        name: "View source utterance 101",
        exact: true,
      }),
    ).toBeVisible();
    await impact
      .getByRole("button", { name: "Next relevance", exact: true })
      .click();
    await expect(impact.getByRole("listitem")).toHaveCount(5);
    await impact
      .getByRole("link", { name: "View source utterance 205", exact: true })
      .click();
    await expect(
      page.getByRole("status", { name: "Transcript page" }),
    ).toHaveText("Page 3 of 3");
    await impact
      .getByLabel("Show relevance", { exact: true })
      .selectOption("IGNORED");
    await expect(
      impact.getByRole("status", { name: "Relevance page" }),
    ).toHaveText("Page 1 of 2");
    await impact
      .getByRole("button", { name: "Next relevance", exact: true })
      .click();
    await expect(impact.getByRole("listitem")).toHaveCount(2);
  } finally {
    await request.delete(`${root}/${meeting.id}`);
  }
});

test("impact read failure retries independently while source remains readable", async ({
  page,
  request,
}) => {
  const meeting = await create(request, normal);
  const url = `**/meetings/${meeting.id}/relevance*`;
  await page.route(url, (route) =>
    route.fulfill({
      status: 503,
      json: { error: { message: "Synthetic read outage" } },
    }),
  );
  try {
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}`,
    );
    const impact = page.getByRole("region", {
      name: "Meeting impact",
      exact: true,
    });
    await expect(
      impact.getByRole("heading", {
        name: "Meeting impact couldn’t load",
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page.getByText("SSO stays in Phase 2.", { exact: true }),
    ).toBeVisible();
    await page.unroute(url);
    await impact
      .getByRole("button", { name: "Try again", exact: true })
      .click();
    await expect(
      impact.getByRole("button", { name: "Analyze relevance", exact: true }),
    ).toBeVisible();
  } finally {
    await request.delete(`${root}/${meeting.id}`);
  }
});

test("failed analysis preserves counts and filter and permits deliberate retry", async ({
  page,
  request,
}) => {
  const meeting = await create(request, normal);
  const url = `**/meetings/${meeting.id}/relevance*`;
  try {
    await page.route(url, (route) =>
      route.request().method() === "POST"
        ? route.fulfill({
            status: 503,
            json: { error: { message: "Synthetic analysis outage" } },
          })
        : route.continue(),
    );
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}`,
    );
    const impact = page.getByRole("region", {
      name: "Meeting impact",
      exact: true,
    });
    await impact
      .getByRole("button", { name: "Analyze relevance", exact: true })
      .click();
    await expect(
      impact.getByRole("alert", { name: "Relevance error" }),
    ).toContainText("Synthetic analysis outage");
    await metric(impact, "Pending segments", 4);
    await page.unroute(url);
    await impact
      .getByRole("button", { name: "Analyze relevance", exact: true })
      .click();
    await metric(impact, "Pending segments", 0);
  } finally {
    await request.delete(`${root}/${meeting.id}`);
  }
});

test("mobile keyboard analysis and long source text fit the viewport", async ({
  page,
  request,
}) => {
  const meeting = await create(request, [
    "SSO " + "long source ".repeat(100),
    "Good morning.",
  ]);
  try {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}`,
    );
    const impact = page.getByRole("region", {
      name: "Meeting impact",
      exact: true,
    });
    const button = impact.getByRole("button", {
      name: "Analyze relevance",
      exact: true,
    });
    await button.focus();
    await page.keyboard.press("Enter");
    await metric(impact, "Conversation segments analyzed", 2);
    await impact
      .getByLabel("Show relevance", { exact: true })
      .selectOption("UNCERTAIN");
    await expect(
      impact.getByText("No analyzed segments match this filter.", {
        exact: true,
      }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
  } finally {
    await request.delete(`${root}/${meeting.id}`);
  }
});

test("meeting without transcript explains impact prerequisite", async ({
  page,
  request,
}) => {
  const meeting = await create(request, []);
  try {
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}`,
    );
    const impact = page.getByRole("region", {
      name: "Meeting impact",
      exact: true,
    });
    await expect(
      impact.getByText("Awaiting meeting evidence", { exact: true }),
    ).toBeVisible();
    await expect(
      impact.getByRole("button", { name: "Analyze relevance", exact: true }),
    ).toHaveCount(0);
  } finally {
    await request.delete(`${root}/${meeting.id}`);
  }
});

test("fractional ignored percentage agrees across Python API and browser contract", async ({
  page,
  request,
}) => {
  const meeting = await create(request, [
    "Good morning.",
    ...Array.from({ length: 7 }, () => "SSO stays in Phase 2."),
  ]);
  try {
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}`,
    );
    const impact = page.getByRole("region", {
      name: "Meeting impact",
      exact: true,
    });
    await impact
      .getByRole("button", { name: "Analyze relevance", exact: true })
      .click();
    await expect(
      impact.getByRole("status", { name: "Ignored conversation share" }),
    ).toContainText("13%");
    await metric(impact, "Conversation segments analyzed", 8);
  } finally {
    await request.delete(`${root}/${meeting.id}`);
  }
});

test("synthetic low-confidence AI contract displays Needs review without false ignored count", async ({
  page,
  request,
}) => {
  const meeting = await create(request, ["The login button fails QA."]);
  const detail = await (await request.get(`${root}/${meeting.id}`)).json();
  const source = detail.utterances[0];
  let analyzed = false;
  await page.route(`**/meetings/${meeting.id}/relevance*`, async (route) => {
    if (route.request().method() === "POST") analyzed = true;
    if (!analyzed) return route.continue();
    const filter =
      new URL(route.request().url()).searchParams.get("outcome") ?? "ALL";
    const shown = filter === "ALL" || filter === "UNCERTAIN";
    await route.fulfill({
      json: {
        projectId,
        meetingId: meeting.id,
        stale: false,
        analysis: {
          id: randomUUID(),
          model: "synthetic-ui-contract",
          classifierVersion: "v1",
          createdAt: "2026-10-05T01:00:00Z",
          contextComplete: true,
          lastError: null,
          apiCalls: 1,
          inputTokens: 30,
          outputTokens: 10,
          usageReportedCalls: 1,
          latencyMs: 1,
          processing: false,
        },
        counts: {
          total: 1,
          analyzed: 1,
          relevant: 0,
          ignored: 0,
          uncertain: 1,
          pending: 0,
        },
        ignoredPercent: 0,
        page: 1,
        pageSize: 100,
        filteredCount: shown ? 1 : 0,
        items: shown
          ? [
              {
                utteranceId: source.id,
                sequence: 0,
                speaker: source.speaker,
                text: source.text,
                outcome: "UNCERTAIN",
                relevant: false,
                confidence: 0.5,
                reason: "Insufficient context.",
                relatedEntityTypes: [],
                method: "GEMINI",
              },
            ]
          : [],
      },
    });
  });
  try {
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}`,
    );
    const impact = page.getByRole("region", {
      name: "Meeting impact",
      exact: true,
    });
    await impact
      .getByRole("button", { name: "Analyze relevance", exact: true })
      .click();
    await metric(impact, "Needs review", 1);
    await metric(impact, "Ignored segments", 0);
    await metric(impact, "Project-relevant segments", 0);
    await impact
      .getByLabel("Show relevance", { exact: true })
      .selectOption("UNCERTAIN");
    await expect(impact.getByRole("listitem")).toHaveCount(1);
    await expect(
      impact.getByText("Insufficient context.", { exact: true }),
    ).toBeVisible();
  } finally {
    await request.delete(`${root}/${meeting.id}`);
  }
});
