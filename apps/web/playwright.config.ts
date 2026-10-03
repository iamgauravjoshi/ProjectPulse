import { defineConfig } from "@playwright/test";
import path from "node:path";

const browserPath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3010",
    viewport: { width: 1280, height: 800 },
    launchOptions: browserPath ? { executablePath: browserPath } : {},
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "npm run start -- --port 3010",
      env: {
        API_BASE_URL: "http://127.0.0.1:8010",
        NEXT_TELEMETRY_DISABLED: "1",
      },
      url: "http://127.0.0.1:3010",
      reuseExistingServer: false,
    },
    {
      command:
        "uv run --frozen --offline uvicorn app.main:app --host 127.0.0.1 --port 8010",
      cwd: path.resolve(__dirname, "../api"),
      env: { GEMINI_API_KEY: "" },
      url: "http://127.0.0.1:8010/health/live",
      reuseExistingServer: false,
    },
  ],
});
