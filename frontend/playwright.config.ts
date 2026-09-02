import { defineConfig, devices } from "@playwright/test";

/**
 * Points at the pre-installed Chromium in this environment rather than
 * downloading a browser (PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 is set
 * globally here) — see the environment's own README for why.
 *
 * Tests assume both the backend (`uvicorn app.main:app`, port 8000) and
 * the Vite dev server (port 5173, which proxies /api and /ws to 8000)
 * are already running — this suite doesn't manage either process itself,
 * since a from-scratch backend boot needs a real SQLite file and sim
 * loop that are simpler to reason about started once, out-of-band.
 *
 * CEO directive "Paper Burn-in Test-Isolation Hardening" — because this
 * suite has no `webServer` of its own, it will happily mutate whatever
 * save the backend on :8000 happens to be pointed at. `globalSetup`
 * below (tests/global-setup.ts) refuses to run the suite at all — fail
 * closed, before any test executes — when that backend reports it's
 * pointed at the shared default dev save rather than an isolated
 * DATABASE_URL. Start the backend for a real test run like:
 *   DATABASE_URL="sqlite:////tmp/tradetown-test-$(date +%s).db" uvicorn app.main:app --port 8000
 */
export default defineConfig({
  testDir: "./tests",
  globalSetup: "./tests/global-setup.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    viewport: { width: 1400, height: 900 },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], launchOptions: { executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" } },
    },
  ],
});
