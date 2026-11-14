import { defineConfig } from "@playwright/test";

/**
 * End-to-end tests: the real React app (Vite) against the real Booski Core API and a real, disposable
 * PostgreSQL database (see e2e/server.py). No API responses are mocked.
 *
 * Ports differ from the everyday dev servers (5173 / 8000) so a running dev setup is never touched.
 * Uses the installed Google Chrome (`channel: "chrome"`), so no browser download is needed.
 */
const API_PORT = process.env.BOOSKI_E2E_API_PORT ?? "8765";
const WEB_PORT = process.env.BOOSKI_E2E_WEB_PORT ?? "5174";

export default defineConfig({
  testDir: "e2e",
  fullyParallel: false,
  workers: 1, // the journeys share one database and build on each other
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : [["list"]],
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    channel: process.env.BOOSKI_E2E_BROWSER_CHANNEL ?? "chrome",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "uv run --project backend python e2e/server.py",
      url: `http://127.0.0.1:${API_PORT}/api/v1/health/ready`,
      env: { BOOSKI_E2E_API_PORT: API_PORT },
      timeout: 180_000,
      reuseExistingServer: false,
      stdout: process.env.CI ? "pipe" : "ignore",
    },
    {
      command: `npx vite --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      env: { BOOSKI_API_URL: `http://127.0.0.1:${API_PORT}` },
      timeout: 120_000,
      reuseExistingServer: false,
    },
  ],
});
