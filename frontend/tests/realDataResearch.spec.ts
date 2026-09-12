import { test, expect, type Page } from "@playwright/test";
import { clickButton, clickExpand, clickRobust, clickTab, continueGame } from "./helpers";

/**
 * CEO directive "TradeTown — Real-Data Research Command Center UI 1.0."
 * The "REAL-DATA RESEARCH" card inside the existing RESEARCH FACTORY
 * sub-tab (backend/app/real_data_research_bridge.py, milestone
 * 08c4b26). This dev environment's own accumulator database is
 * genuinely empty (no accumulation cycle has ever run here), so the
 * READY path is otherwise unreachable — same real limitation
 * sniperStrategyPerformance.spec.ts already documented for its own
 * page. Tests against the REAL, unmocked backend cover the honest
 * BLOCKED state this environment actually produces; a second group
 * uses `page.route()` to intercept ONLY the two new real-data
 * endpoints with a controlled, real-shaped fixture, to exercise the
 * READY/insufficient/result-display paths this sandbox cannot reach
 * for real. Never touches any other endpoint this page also calls.
 */

async function gotoResearchFactory(page: Page): Promise<void> {
  await page.goto("/");
  await continueGame(page);
  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "SANDBOX");
  await clickRobust(page, () => page.getByRole("button", { name: "RESEARCH FACTORY", exact: true }), { label: "sub-tab RESEARCH FACTORY" });
  await expect(page.getByText("REAL-DATA RESEARCH — RESEARCH ONLY, NEVER TRADING")).toBeVisible();
}

const PROVENANCE_FIXTURE = {
  provider: "kraken" as const,
  dataStatus: "real" as const,
  symbol: "BTC-USD",
  timeframe: "1h",
  developmentCandleCount: 1296,
  holdoutCandleCount: 324,
  datasetStartTimestamp: "2026-01-01T00:00:00+00:00",
  datasetEndTimestamp: "2026-02-24T00:00:00+00:00",
  datasetContentHash: "abcdef0123456789abcdef0123456789abcdef0123456789abcdef01234567",
  strategyFingerprint: "1febc98c00000000000000000000000000000000000000000000000000f61ca3",
  holdoutBoundaryFrozenAt: "2026-01-05T00:00:00+00:00",
};

const FIXTURE_RUN = {
  id: "factory-run-real-data-fixture",
  strategyFamily: "50 EMA Breakout Pullback (Long)",
  seedDefinitionId: "50-ema-breakout-pullback-long",
  seedDefinitionVersion: 1,
  lineageId: "factory-run-real-data-fixture",
  config: { maxGenerations: 1, maxTotalBacktests: 2, maxMutationsPerParent: 3, maxIterationsPerFamily: 10, maxChildrenPerParent: 1, maxRuntimeSeconds: 60 },
  candidates: [],
  generationsCompleted: 1,
  candidatesGenerated: 1,
  candidatesCompiled: 1,
  candidatesBacktested: 1,
  candidatesValidated: 1,
  candidatesRejected: 0,
  survivorCandidateIds: ["candidate-fixture-1"],
  bestSurvivorCandidateId: "candidate-fixture-1",
  topRejectionReasons: [],
  topLessons: [],
  stopReason: "Test fixture — completed after 1 generation.",
  currentChampionDefinitionId: null,
  currentChampionDefinitionVersion: null,
  createdAt: new Date().toISOString(),
  runtimeSeconds: 1.2,
  paretoFrontier: [],
};

test.describe("Real-Data Research — real backend, no interception", () => {
  test("Test A/B/F/I: idle state renders and shows the honest BLOCKED/REAL_DATA_UNAVAILABLE state this empty dev accumulator actually produces", async ({ page }) => {
    await gotoResearchFactory(page);

    // Test A — idle state renders: the symbol selector and the
    // research-vs-trading disclaimer are visible before any network
    // round trip resolves.
    await expect(page.getByText("Research only · Uses accumulated Kraken data · Does not place orders or open positions")).toBeVisible();
    // Scoped: the page has several other <select> elements (agent
    // pickers), so identify this one by its unique ETH-USD option.
    const symbolSelect = page.locator("select").filter({ has: page.getByRole("option", { name: "ETH-USD" }) });
    await expect(symbolSelect).toHaveValue("BTC-USD");

    // Test B/F — this dev environment's real accumulator has zero
    // accumulated candles, so the real, unmocked backend must report
    // BLOCKED / REAL_DATA_UNAVAILABLE — never a fabricated READY state.
    await expect(page.getByText("BLOCKED", { exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("REAL_DATA_UNAVAILABLE")).toBeVisible();
    await expect(page.getByText(/No Factory run was executed\. No mock data was substituted\./)).toBeVisible();

    // Test D — the Run action is disabled while not ready, so a click
    // (or an accidental double-click) can never submit a doomed request.
    await expect(page.getByRole("button", { name: "Run Real-Data Research" })).toBeDisabled();
  });

  test("Test J: the existing (mock-path) Research Factory UI remains fully functional alongside the new card", async ({ page }) => {
    await gotoResearchFactory(page);
    await expect(page.getByText("Research Factory — hypothesis to funnel decision, never a black-box score")).toBeVisible();
    await expect(page.getByPlaceholder("Strategy name")).toBeVisible();
    await expect(page.getByRole("button", { name: "Run Research Funnel (single pass)" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Run Autonomous Factory Cycle" })).toBeVisible();
  });
});

test.describe("Real-Data Research — real-shaped fixture via page.route() (READY path is otherwise unreachable in this empty-accumulator dev environment)", () => {
  test("Test C/E/H: a READY symbol shows real provenance, frozen/reserved holdout with no include control, and a Run click reaches the real-data endpoint", async ({ page }) => {
    let runRequestBody: unknown = null;

    await page.route("**/api/sandbox/research-factory/run-real-data/preflight", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "ready", symbol: "BTC-USD", reason: null, detail: "Real accumulated data available.", provenance: PROVENANCE_FIXTURE }),
      })
    );
    await page.route("**/api/sandbox/research-factory/run-real-data", async (route) => {
      runRequestBody = route.request().postDataJSON();
      // A deliberate delay so the intermediate loading/disabled state
      // (Test D) is actually observable rather than resolving instantly.
      await new Promise((r) => setTimeout(r, 400));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "completed", symbol: "BTC-USD", reason: null, detail: "Real-data Factory run completed.", run: FIXTURE_RUN, provenance: PROVENANCE_FIXTURE }),
      });
    });

    await gotoResearchFactory(page);

    // Test C setup / Test E — READY status plus real provenance fields,
    // never labeled "LIVE".
    await expect(page.getByText("READY", { exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("DATA PROVENANCE — REAL MARKET DATA")).toBeVisible();
    await expect(page.getByText("1,296")).toBeVisible();
    await expect(page.getByText("LIVE", { exact: true })).not.toBeVisible();

    // Test H — holdout shown as a fixed, reserved fact; no control to
    // include it in research exists anywhere on the card.
    await expect(page.getByText("FROZEN / RESERVED")).toBeVisible();
    await expect(page.getByText(/Development optimization above does not include holdout data/)).toBeVisible();
    await expect(page.getByRole("button", { name: /include holdout/i })).toHaveCount(0);

    // Test C — the explicit CEO action reaches the canonical endpoint
    // with the real compiled definition and chosen symbol, and the
    // resulting FactoryRunRecord renders through the SAME existing
    // Factory Status card the mock path already uses (never a second,
    // duplicated result display).
    const runButton = page.getByRole("button", { name: "Run Real-Data Research" });
    await expect(runButton).toBeEnabled();
    await runButton.click();

    // Test D — while the request is in flight, the button relabels and
    // disables, preventing a duplicate submission from an impatient
    // second click; a plain research-vs-trading loading state is shown,
    // never a fake progress percentage.
    await expect(page.getByRole("button", { name: "Running real-data research…" })).toBeDisabled();
    await expect(page.getByText("No trading action is being taken.")).toBeVisible();

    await expect(page.getByText(`Factory Status — Run ${FIXTURE_RUN.id}`)).toBeVisible({ timeout: 15_000 });
    expect(runRequestBody).not.toBeNull();
    expect((runRequestBody as { symbol: string }).symbol).toBe("BTC-USD");
    expect((runRequestBody as { definition: { id: string } }).definition.id).toBe("50-ema-breakout-pullback-long");
  });

  test("Test G: INSUFFICIENT_REAL_CANDLES displays the insufficient-evidence state, not a generic error", async ({ page }) => {
    await page.route("**/api/sandbox/research-factory/run-real-data/preflight", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "preflight_failed",
          symbol: "BTC-USD",
          reason: "INSUFFICIENT_REAL_CANDLES",
          detail: "BTC-USD has 0 real development candle(s) — below the real floor.",
          provenance: null,
        }),
      })
    );

    await gotoResearchFactory(page);
    await expect(page.getByText("INSUFFICIENT EVIDENCE", { exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("INSUFFICIENT_REAL_CANDLES")).toBeVisible();
    await expect(page.getByText(/does not currently contain enough usable real data/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Run Real-Data Research" })).toBeDisabled();
  });
});
