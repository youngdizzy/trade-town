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
 */
export default defineConfig({
  testDir: "./tests",
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
