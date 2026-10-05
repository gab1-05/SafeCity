import { expect, test } from "@playwright/test";

// Smoke: public pages render, citizen logs in, authority sees the queue.
// Requires a seeded stack (backend :18081 + `seed_demo_data`).

const CITIZEN = { email: "citizen1@safecity.local", password: "Citizen@12345!" };
const ADMIN = { email: "admin@safecity.local", password: "Admin@12345!" };

async function login(page, creds: { email: string; password: string }) {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill(creds.email);
  await page.getByLabel(/password/i).fill(creds.password);
  await page.locator("form").getByRole("button", { name: /log in/i }).click();
  // Wait for the JWT to land before navigating anywhere.
  await page.waitForFunction(() => localStorage.getItem("safecity.access"), null, {
    timeout: 15_000,
  });
}

test("landing and public map render", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading").first()).toBeVisible();
  await page.goto("/map");
  await expect(page.locator(".leaflet-container")).toBeVisible({ timeout: 15_000 });
});

test("citizen login reaches dashboard and report wizard opens", async ({ page }) => {
  await login(page, CITIZEN);
  await expect(page).toHaveURL(/dashboard/, { timeout: 15_000 });
  await page.goto("/report");
  await expect(page.getByRole("heading", { name: /report/i })).toBeVisible({
    timeout: 15_000,
  });
});

test("admin login reaches the incident queue", async ({ page }) => {
  await login(page, ADMIN);
  await page.goto("/queue");
  await expect(page.getByRole("heading", { name: /queue/i })).toBeVisible({
    timeout: 15_000,
  });
});
