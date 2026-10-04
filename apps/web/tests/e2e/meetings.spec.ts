import { randomUUID } from "node:crypto";
import { expect, test, type APIRequestContext } from "@playwright/test";
import { fixture } from "../fixtures/workspace";
const projectId = fixture.project.id;
const root = `/api/workspace/projects/${projectId}/meetings`;
async function create(request: APIRequestContext) {
  const response = await request.post(root, {
    data: { title: `Transcript test ${randomUUID()}` },
  });
  expect(response.status()).toBe(201);
  return response.json();
}
const formats = [
  {
    name: "meeting.txt",
    text: "00:01:10 | Sarah | Need SSO.\n | John | Time unknown.\n | | Speaker unknown.",
  },
  {
    name: "meeting.json",
    text: JSON.stringify([
      {
        speaker: "Sarah",
        speakerId: "sarah-1",
        timestamp: "00:01:10.125",
        text: "Need SSO.",
        confidence: 0.9,
      },
      { speaker: "Sarah", speakerId: "sarah-2", text: "Distinct Sarah." },
      { text: "Speaker unknown." },
    ]),
  },
  {
    name: "meeting.vtt",
    text: "WEBVTT\n\n00:01:10.000 --> 00:01:11.000\n<v Sarah>Need SSO.</v>\n\n00:01:12.000 --> 00:01:13.000\n<v John>Approval pending.</v>",
  },
];
for (const file of formats)
  test(`${file.name} upload persists attribution source link and unchanged baseline`, async ({
    page,
    request,
  }) => {
    const meeting = await create(request);
    const before = await (
      await request.get(`/api/workspace/projects/${projectId}`)
    ).json();
    try {
      await page.goto(
        `/?project=${projectId}&view=meetings&meeting=${meeting.id}`,
      );
      await page.getByLabel("Transcript file", { exact: true }).setInputFiles({
        name: file.name,
        mimeType: "application/octet-stream",
        buffer: Buffer.from(file.text),
      });
      await page
        .getByRole("button", { name: "Upload transcript", exact: true })
        .click();
      await expect(
        page.getByRole("status", { name: "Meeting feedback" }),
      ).toContainText("Transcript uploaded");
      await expect(page.getByText("Need SSO.", { exact: true })).toBeVisible();
      const detail = await (await request.get(`${root}/${meeting.id}`)).json();
      expect(detail.utterances.length).toBeGreaterThanOrEqual(2);
      if (file.name.endsWith("json")) {
        expect(detail.participants).toHaveLength(2);
        await expect(
          page.locator(`[id="utterance-${detail.utterances[0].id}"]`),
        ).toContainText("Speaker ID: sarah-1");
        await expect(
          page.locator(`[id="utterance-${detail.utterances[1].id}"]`),
        ).toContainText("Speaker ID: sarah-2");
        expect(detail.utterances[0].speakerId).not.toBe(
          detail.utterances[1].speakerId,
        );
        await expect(
          page.getByText("Source confidence 90%", { exact: false }),
        ).toBeVisible();
      }
      await page
        .getByRole("link", { name: "Link to utterance 2", exact: true })
        .click();
      await expect(
        page.locator(`[id="utterance-${detail.utterances[1].id}"]`),
      ).toHaveAttribute("aria-current", "location");
      await page.reload();
      await expect(
        page.locator(`[id="utterance-${detail.utterances[1].id}"]`),
      ).toBeVisible();
      await expect(
        page.locator(`[id="utterance-${detail.utterances[1].id}"]`),
      ).toHaveAttribute("aria-current", "location");
      const after = await (
        await request.get(`/api/workspace/projects/${projectId}`)
      ).json();
      for (const key of [
        "requirements",
        "decisions",
        "milestones",
        "risks",
        "commitments",
        "dependencies",
      ])
        expect(after[key]).toEqual(before[key]);
    } finally {
      await request.delete(`${root}/${meeting.id}`);
    }
  });
test("create meeting register repeated-name participants and confirm audited deletion", async ({
  page,
  request,
}) => {
  const title = `Planning ${randomUUID()}`;
  let id: string | undefined;
  try {
    await page.goto(`/?project=${projectId}&view=meetings`);
    await page
      .getByRole("button", { name: "New meeting", exact: true })
      .click();
    await page.getByLabel("Meeting title", { exact: true }).fill(title);
    await page
      .getByRole("button", { name: "Create meeting", exact: true })
      .click();
    await expect(
      page.getByRole("status", { name: "Meeting feedback" }),
    ).toHaveText("Meeting created.");
    const list = await (await request.get(root)).json();
    id = list.find((m: { title: string }) => m.title === title)?.id;
    expect(id).toBeTruthy();
    for (const source of ["sarah-1", "sarah-2"]) {
      await page
        .getByRole("button", { name: `Add participant ${title}`, exact: true })
        .click();
      await page.getByLabel("Participant name", { exact: true }).fill("Sarah");
      await page
        .getByLabel("Transcript speaker ID (optional)", { exact: true })
        .fill(source);
      if (source === "sarah-1")
        await page
          .getByLabel("Project member (optional)", { exact: true })
          .selectOption(fixture.members[0].id);
      await page
        .getByRole("button", { name: "Save participant", exact: true })
        .click();
      await expect(
        page.getByRole("status", { name: "Meeting feedback" }),
      ).toHaveText("Participant registered.");
    }
    await expect(page.getByText("Linked to", { exact: false })).toBeVisible();
    const detail = await (await request.get(`${root}/${id}`)).json();
    expect(detail.participants).toHaveLength(2);
    await page
      .getByRole("button", { name: `Delete ${title}`, exact: true })
      .click();
    await expect(page.getByRole("dialog")).toContainText(
      "audit history are retained",
    );
    await page
      .getByRole("button", { name: "Confirm delete", exact: true })
      .click();
    await expect(
      page.getByRole("status", { name: "Meeting feedback" }),
    ).toContainText("Meeting deleted");
    expect((await request.get(`${root}/${id}`)).status()).toBe(404);
  } finally {
    if (id) await request.delete(`${root}/${id}`);
  }
});
test("malformed upload preserves selected file and retries without partial evidence", async ({
  page,
  request,
}) => {
  const meeting = await create(request);
  try {
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}`,
    );
    await page.getByLabel("Transcript file", { exact: true }).setInputFiles({
      name: "bad.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("malformed"),
    });
    await page
      .getByRole("button", { name: "Upload transcript", exact: true })
      .click();
    await expect(
      page.getByRole("alert", { name: "Transcript error" }),
    ).toContainText("Line 1");
    await expect(
      page.getByText("Selected: bad.txt", { exact: true }),
    ).toBeVisible();
    expect(
      (await (await request.get(`${root}/${meeting.id}`)).json()).utterances,
    ).toHaveLength(0);
    await page.getByLabel("Transcript file", { exact: true }).setInputFiles({
      name: "good.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(" | Sarah | Retry evidence"),
    });
    await page
      .getByRole("button", { name: "Upload transcript", exact: true })
      .click();
    await expect(
      page.getByText("Retry evidence", { exact: true }),
    ).toBeVisible();
  } finally {
    await request.delete(`${root}/${meeting.id}`);
  }
});
test("long transcript deep link opens correct page and invalid citation is explicit", async ({
  page,
  request,
}) => {
  const meeting = await create(request);
  try {
    const rows = Array.from({ length: 205 }, (_, i) => ({
      speaker: `Speaker ${i % 10}`,
      text: `Utterance content ${i}`,
    }));
    const response = await request.post(
      `${root}/${meeting.id}/transcript?filename=long.json`,
      {
        data: Buffer.from(JSON.stringify(rows)),
        headers: { "Content-Type": "application/octet-stream" },
      },
    );
    expect(response.status()).toBe(201);
    const detail = await response.json();
    const id = detail.utterances[204].id;
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}&utterance=${id}#utterance-${id}`,
    );
    await expect(
      page.getByRole("status", { name: "Transcript page" }),
    ).toHaveText("Page 3 of 3");
    await expect(page.locator(`[id="utterance-${id}"]`)).toBeFocused();
    await page
      .getByRole("button", { name: "Previous utterances", exact: true })
      .click();
    await expect(
      page.getByRole("status", { name: "Transcript page" }),
    ).toHaveText("Page 2 of 3");
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}&utterance=${randomUUID()}`,
    );
    await expect(
      page.getByRole("alert", { name: "Citation error" }),
    ).toContainText("not part of this meeting");
  } finally {
    await request.delete(`${root}/${meeting.id}`);
  }
});
test("mobile dialog dismissal restores focus and failed create preserves draft", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(`/?project=${projectId}&view=meetings`);
  const trigger = page.getByRole("button", {
    name: "New meeting",
    exact: true,
  });
  await trigger.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await page.route(`**/projects/${projectId}/meetings`, (route) =>
    route.request().method() === "POST"
      ? route.fulfill({
          status: 503,
          json: { error: { message: "Please retry." } },
        })
      : route.continue(),
  );
  await trigger.click();
  await page
    .getByLabel("Meeting title", { exact: true })
    .fill("Preserved draft");
  await page
    .getByRole("button", { name: "Create meeting", exact: true })
    .click();
  await expect(
    page.getByRole("alert", { name: "Meeting error" }),
  ).toContainText("Please retry");
  await expect(page.getByLabel("Meeting title", { exact: true })).toHaveValue(
    "Preserved draft",
  );
});
test("meeting fetch error supports retry", async ({ page }) => {
  let fail = true;
  await page.route(`**/projects/${projectId}/meetings`, (route) =>
    fail
      ? route.fulfill({
          status: 503,
          json: { error: { message: "Unavailable" } },
        })
      : route.fulfill({ json: [] }),
  );
  await page.goto(`/?project=${projectId}&view=meetings`);
  await expect(
    page.getByRole("heading", { name: "Meetings couldn’t load", exact: true }),
  ).toBeVisible();
  fail = false;
  await page.getByRole("button", { name: "Try again", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "No meeting evidence yet", exact: true }),
  ).toBeVisible();
});

test("transcript stays within mobile viewport and captures evidence layout", async ({
  page,
  request,
}) => {
  const response = await request.post(root, {
    data: { title: "Release planning" },
  });
  const meeting = await response.json();
  try {
    const rows = [
      {
        speaker: "Sarah",
        speakerId: "sarah",
        timestamp: "00:01:10",
        text: "We need SSO in Phase 1. This is meeting evidence awaiting review.",
      },
      {
        speaker: "John",
        speakerId: "john",
        timestamp: "00:01:20",
        text: "I will send the credentials Friday.",
        confidence: 0.92,
      },
      {
        speaker: "Priya",
        speakerId: "priya",
        text: "The meeting source did not include a timestamp for this utterance.",
      },
      { text: "Speaker attribution is unknown; no identity was inferred." },
    ];
    const upload = await request.post(
      `${root}/${meeting.id}/transcript?filename=release-planning.json`,
      {
        data: Buffer.from(JSON.stringify(rows)),
        headers: { "Content-Type": "application/octet-stream" },
      },
    );
    expect(upload.status()).toBe(201);
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}`,
    );
    await expect(
      page.getByText("I will send the credentials Friday.", { exact: true }),
    ).toBeVisible();
    await page.screenshot({
      path: "test-results/transcript-desktop.png",
      fullPage: true,
    });
    await page.setViewportSize({ width: 375, height: 812 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    await page.screenshot({
      path: "test-results/transcript-mobile.png",
      fullPage: true,
    });
  } finally {
    await request.delete(`${root}/${meeting.id}`);
  }
});

test("long meeting and speaker labels wrap on mobile", async ({
  page,
  request,
}) => {
  const response = await request.post(root, {
    data: { title: "Meeting".repeat(34) },
  });
  const meeting = await response.json();
  try {
    const upload = await request.post(
      `${root}/${meeting.id}/transcript?filename=long-label.json`,
      {
        data: Buffer.from(
          JSON.stringify([
            {
              speaker: "Speaker".repeat(17),
              speakerId: "same-name",
              text: "Long evidence text " + "x".repeat(300),
            },
          ]),
        ),
        headers: { "Content-Type": "application/octet-stream" },
      },
    );
    expect(upload.status()).toBe(201);
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(
      `/?project=${projectId}&view=meetings&meeting=${meeting.id}`,
    );
    await expect(page.getByText(/Long evidence text/)).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
  } finally {
    await request.delete(`${root}/${meeting.id}`);
  }
});
