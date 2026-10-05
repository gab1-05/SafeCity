import { defineConfig, devices } from "@playwright/test";

// Smoke suite against a seeded stack (see e2e.yml / `make test-e2e`):
// backend on :18081 (migrate + seed first), frontend preview on :5174.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5174",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: process.env.E2E_NO_SERVER
    ? undefined
    : {
        command: "npm run preview -- --port 5174",
        url: "http://localhost:5174",
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
