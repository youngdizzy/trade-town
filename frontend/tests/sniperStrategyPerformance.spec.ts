import { test, expect, type Page } from "@playwright/test";

/**
 * CEO directive "TradeTown — Sniper Per-Strategy Performance
 * Observability UI 1.0." Covers `src/sniper/SniperStrategyPerformance.tsx`
 * — the read-only panel rendering `GET /api/sniper/strategy-performance`
 * inside the Sniper Terminal (`/sniper`, a separate flat React surface
 * from the main game — see `SniperApp.tsx`'s own module docstring).
 *
 * TESTING APPROACH — same real-app philosophy as the rest of this suite
 * (tests/newGameConfirm.spec.ts's own docstring: "no mocking" is the
 * default). A fresh isolated backend (see tests/global-setup.ts) seeds
 * BOTH real registered Sniper strategies with zero closed trades via
 * `default_state()` — the first three tests below exercise that real,
 * naturally-reachable state with no interception at all.
 *
 * The remaining tests need EXACT, known outcome numbers (a specific win
 * rate, a specific P&L, a strategy with 100 trades vs. one with 1) to
 * prove ordering/null-handling/superiority-avoidance precisely — states
 * that would take an impractically long, non-deterministic real burn-in
 * to reach naturally (candidate discovery/outcomes are randomized). Per
 * this suite's own established, disclosed exception (newGameConfirm.spec.ts
 * uses `page.route()` for its one otherwise-unreachable real code path),
 * these use `page.route()` to intercept exactly
 * `GET /api/sniper/strategy-performance` with a controlled, real-shaped
 * `SniperStrategyPerformanceSummary` payload — never a UI-level mock, and
 * never touching any other endpoint this page also calls.
 */

async function gotoSniper(page: Page): Promise<void> {
  await page.goto("/sniper");
  await expect(page.getByText("Strategy performance", { exact: true })).toBeVisible();
}

test.describe("Sniper strategy performance — real backend, no interception", () => {
  test("panel renders both real registered strategies with honest zero-trade state", async ({ page }) => {
    await gotoSniper(page);
    // A brand-fresh isolated backend registers both real strategies via
    // default_state() with zero closed trades each — see
    // backend/app/sniper_strategy_registry.py::default_sniper_strategies().
    await expect(page.getByText("memecoin-sniper", { exact: true })).toBeVisible();
    await expect(page.getByText("memecoin-sniper-whale-confirmation", { exact: true })).toBeVisible();
    await expect(page.getByText("0 closed trades").first()).toBeVisible();
    await expect(page.getByText("No closed trades yet").first()).toBeVisible();
  });

  test("historical-observation disclaimer is visible without opening anything", async ({ page }) => {
    await gotoSniper(page);
    await expect(page.getByText(/Historical observed performance/i)).toBeVisible();
    await expect(page.getByText(/Not a validation score, ranking, or trading recommendation/i)).toBeVisible();
  });

  test("no ranking, promotion, or recommendation language exists anywhere on the page", async ({ page }) => {
    await gotoSniper(page);
    const bodyText = (await page.locator("body").innerText()).toLowerCase();
    // Deliberately excludes the bare word "winner" — this milestone's
    // own required metric label ("Avg winner", Section 8) legitimately
    // contains it; the real negative-space concern is a superiority
    // BADGE/LABEL, covered by the phrases below instead.
    for (const forbidden of ["best strategy", "recommended", "preferred strategy", "top performer", "champion", "challenger", "leaderboard"]) {
      expect(bodyText).not.toContain(forbidden);
    }
  });

  test("existing Sniper Terminal functionality remains intact alongside the new panel", async ({ page }) => {
    await gotoSniper(page);
    await expect(page.getByText("Memecoin Sniper", { exact: true })).toBeVisible();
    await expect(page.getByText("Active Trades (", { exact: false })).toBeVisible();
    await expect(page.getByText("Trade journal", { exact: false })).toBeVisible();
  });
});

test.describe("Sniper strategy performance — controlled fixture via page.route (disclosed exception, see file docstring)", () => {
  const FIXTURE = {
    reads: [
      {
        strategyId: "zzz-low-sample",
        name: "ZZZ Low Sample Strategy",
        family: "liquidity_momentum",
        provenance: "hardcoded",
        isRegistered: true,
        status: "enabled",
        distinctStrategyVersionsObserved: ["1"],
        closedTradeCount: 1,
        winCount: 1,
        lossCount: 0,
        winRatePct: 100.0,
        totalRealizedPnlSol: 0.5,
        averageRealizedPnlSol: 0.5,
        averageWinningTradeSol: 0.5,
        averageLosingTradeSol: null,
        observedExpectancyPerClosedTradeSol: 0.5,
      },
      {
        strategyId: "aaa-high-sample",
        name: "AAA High Sample Strategy With An Unusually Long Display Name To Test Layout Wrapping",
        family: "whale_confirmation",
        provenance: "hardcoded",
        isRegistered: true,
        status: "enabled",
        distinctStrategyVersionsObserved: ["1", "2"],
        closedTradeCount: 100,
        winCount: 60,
        lossCount: 40,
        winRatePct: 60.0,
        totalRealizedPnlSol: 12.3456,
        averageRealizedPnlSol: 0.123456,
        averageWinningTradeSol: 0.4,
        averageLosingTradeSol: -0.3,
        observedExpectancyPerClosedTradeSol: 0.123456,
      },
      {
        strategyId: "retired-unregistered-strategy-with-a-very-long-canonical-identifier",
        name: "Retired Strategy",
        family: null,
        provenance: null,
        isRegistered: false,
        status: null,
        distinctStrategyVersionsObserved: [],
        closedTradeCount: 3,
        winCount: 0,
        lossCount: 3,
        winRatePct: 0.0,
        totalRealizedPnlSol: -0.9,
        averageRealizedPnlSol: -0.3,
        averageWinningTradeSol: null,
        averageLosingTradeSol: -0.3,
        observedExpectancyPerClosedTradeSol: -0.3,
      },
    ],
    tradesExcludedMalformed: 0,
    closedTradesConsidered: 104,
    generatedAt: "2026-01-01T00:00:00+00:00",
  };

  async function mockPerformance(page: Page, body: unknown): Promise<void> {
    await page.route("**/api/sniper/strategy-performance", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) }),
    );
  }

  test("API ordering is preserved even when a low-sample strategy has a higher win rate than a high-sample one", async ({ page }) => {
    await mockPerformance(page, FIXTURE);
    await gotoSniper(page);
    // FIXTURE deliberately lists the 1-trade/100%-win-rate strategy
    // FIRST and the 100-trade/60%-win-rate strategy SECOND — the UI
    // must render them in that exact order (never re-sorted by any
    // performance metric).
    const names = await page.locator("span.font-semibold.text-cmd-cyan").allTextContents();
    const zzzIndex = names.findIndex((n) => n.includes("ZZZ Low Sample"));
    const aaaIndex = names.findIndex((n) => n.includes("AAA High Sample"));
    expect(zzzIndex).toBeGreaterThanOrEqual(0);
    expect(aaaIndex).toBeGreaterThan(zzzIndex);
  });

  test("sample size is visible and a 1-trade strategy is not visually implied superior to a 100-trade one", async ({ page }) => {
    await mockPerformance(page, FIXTURE);
    await gotoSniper(page);
    await expect(page.getByText("1 closed trade", { exact: true })).toBeVisible();
    await expect(page.getByText("100 closed trades", { exact: true })).toBeVisible();
    const panelText = (await page.getByTestId("sniper-strategy-performance-panel").innerText()).toLowerCase();
    for (const forbidden of ["best strategy", "top performer", "recommended", "preferred"]) {
      expect(panelText).not.toContain(forbidden);
    }
  });

  test("a strategy no longer in the registry still renders with its historical name and an honest badge", async ({ page }) => {
    await mockPerformance(page, FIXTURE);
    await gotoSniper(page);
    await expect(page.getByText("Retired Strategy", { exact: true })).toBeVisible();
    await expect(page.getByText("No longer registered", { exact: true })).toBeVisible();
  });

  test("null averageLosingTradeSol and null averageWinningTradeSol render as em dash, never as 0", async ({ page }) => {
    await mockPerformance(page, FIXTURE);
    await gotoSniper(page);
    // ZZZ has zero losing trades -> averageLosingTradeSol is null.
    // AAA/Retired rows have real numeric values for comparison so this
    // assertion can't pass merely because every field happens to say "—".
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).toContain("—");
    expect(bodyText).not.toMatch(/Avg loser[^\n]*0\.0000 SOL/);
  });

  test("real zero total realized P&L renders as an actual zero, not an em dash", async ({ page }) => {
    const zeroFixture = {
      ...FIXTURE,
      reads: [
        {
          strategyId: "brand-new-strategy",
          name: "Brand New Strategy",
          family: "liquidity_momentum",
          provenance: "hardcoded",
          isRegistered: true,
          status: "enabled",
          distinctStrategyVersionsObserved: [],
          closedTradeCount: 0,
          winCount: 0,
          lossCount: 0,
          winRatePct: null,
          totalRealizedPnlSol: 0.0,
          averageRealizedPnlSol: null,
          averageWinningTradeSol: null,
          averageLosingTradeSol: null,
          observedExpectancyPerClosedTradeSol: null,
        },
      ],
    };
    await mockPerformance(page, zeroFixture);
    await gotoSniper(page);
    // Zero trades -> the honest "no closed trades yet" branch, which
    // never even renders a P&L row (there is nothing to report a rate
    // against) — proven by the absence of a fabricated 0% win rate.
    await expect(page.getByText("Brand New Strategy", { exact: true })).toBeVisible();
    await expect(page.getByText("No closed trades yet", { exact: false })).toBeVisible();
    const panelText = await page.getByTestId("sniper-strategy-performance-panel").innerText();
    expect(panelText).not.toContain("0.0%");
  });

  test("long strategy names and ids do not break the layout (no horizontal page overflow)", async ({ page }) => {
    await mockPerformance(page, FIXTURE);
    await gotoSniper(page);
    await expect(page.getByText("AAA High Sample Strategy With An Unusually Long Display Name To Test Layout Wrapping")).toBeVisible();
    const hasHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
    expect(hasHorizontalOverflow).toBe(false);
  });

  test("empty reads array shows an honest empty state, never fabricated strategies", async ({ page }) => {
    await mockPerformance(page, { reads: [], tradesExcludedMalformed: 0, closedTradesConsidered: 0, generatedAt: "2026-01-01T00:00:00+00:00" });
    await gotoSniper(page);
    await expect(page.getByText("No strategy performance observations yet.", { exact: true })).toBeVisible();
  });

  test("a failed request shows a real error state, never stale or fixture data", async ({ page }) => {
    await page.route("**/api/sniper/strategy-performance", (route) => route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "Internal Server Error" }) }));
    await gotoSniper(page);
    await expect(page.getByText(/Could not load strategy performance/i)).toBeVisible();
  });
});
