import { test, expect } from "@playwright/test";
import { clickButton, clickExpand, clickRobust, clickTab, continueGame } from "./helpers";

/**
 * v0.7 Feature 45/52 — the Research Sandbox / Strategy Validation
 * Laboratory. Same real-app testing approach as talent.spec.ts/
 * execIntel.spec.ts — exercises the live Vite + FastAPI stack, no
 * mocking.
 */

test("strategies carry real stage/stageHistory/allocatedCapital in the backend state, plus every real Feature 52 Part 1/2 artifact list", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(Array.isArray(state.strategies)).toBe(true);
  expect(state.strategies.length).toBeGreaterThan(0);
  for (const strategy of state.strategies) {
    expect(strategy.stage).toBeTruthy();
    expect(Array.isArray(strategy.stageHistory)).toBe(true);
    expect(typeof strategy.allocatedCapital).toBe("number");
  }
  expect(Array.isArray(state.strategyReports)).toBe(true);
  expect(Array.isArray(state.strategyReviews)).toBe(true);
  // v0.7 Feature 52 (Part 1/2) — every new real artifact list this
  // feature added, all in the "company" save module.
  for (const field of [
    "strategyMonteCarloResults",
    "strategyRegimeTests",
    "strategyLiquidityValidations",
    "strategyExecutiveReviews",
    "strategyFounderApprovals",
    "strategyHealthAssessments",
    "strategyHallOfFame",
    "strategyFailedArchive",
  ]) {
    expect(Array.isArray(state[field]), `${field} should be a real array`).toBe(true);
  }
});

test("the Research Sandbox tab opens from the Command Center, shows the pipeline, and queues a real scenario backtest", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "SANDBOX");

  await expect(page.getByText(/no strategy skips a stage/)).toBeVisible();
  await expect(page.getByText("Testing Environments — queue a real backtest run", { exact: true })).toBeVisible();
  await expect(page.getByText("Performance Metrics — real per-run history", { exact: true })).toBeVisible();
  await expect(page.getByText("Approval Process — advance the pipeline", { exact: true })).toBeVisible();

  await clickRobust(page, () => page.getByRole("button", { name: "Run Backtest" }), { label: "Run Backtest" });
  await expect(page.getByText(/queued|running/).first()).toBeVisible({ timeout: 10_000 });

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});

test("Feature 52 (Part 1/2) — every Strategy Validation Laboratory sub-tab opens and renders its own real content", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "SANDBOX");

  // LIBRARY — every strategy this company has ever created, click
  // through to open one strategy's own real Certification dossier.
  await clickRobust(page, () => page.getByRole("button", { name: "LIBRARY", exact: true }), { label: "sub-tab LIBRARY" });
  await expect(page.getByText(/Strategy Library — every strategy this company has ever created/)).toBeVisible();
  await clickRobust(page, () => page.getByRole("button", { name: "Open", exact: true }).first(), { label: "Open (Library row)" });

  // CERTIFICATION — the real validation dossier (Monte Carlo/Regime
  // Test/Liquidity/Executive Review/Founder Approval/Confidence Score),
  // computed fresh on request.
  await expect(page.getByRole("button", { name: "CERTIFICATION", exact: true })).toHaveClass(/text-cmd-cyan/, { timeout: 10_000 });
  await expect(page.getByText(/No real validation evidence on file yet|Confidence Score|Monte Carlo Testing/).first()).toBeVisible({ timeout: 10_000 });

  // HEALTH — the honest "Live Performance Monitor" reframe.
  await clickRobust(page, () => page.getByRole("button", { name: "HEALTH", exact: true }), { label: "sub-tab HEALTH" });
  await expect(page.getByText(/Strategy Health — real simulation performance, not live P&L/)).toBeVisible();

  // EVOLUTION — the honest "Strategy Evolution" reframe (real stage
  // history, never fabricated versioning).
  await clickRobust(page, () => page.getByRole("button", { name: "EVOLUTION", exact: true }), { label: "sub-tab EVOLUTION" });
  await expect(page.getByText(/Real Journey — every stage this strategy has actually earned/)).toBeVisible();

  // HALL OF FAME / FAILED ARCHIVE — the two permanent retirement outcomes.
  await clickRobust(page, () => page.getByRole("button", { name: "HALL OF FAME", exact: true }), { label: "sub-tab HALL OF FAME" });
  await expect(page.getByText(/Strategy Hall of Fame — permanent, only ever earned through real evidence/)).toBeVisible();
  await clickRobust(page, () => page.getByRole("button", { name: "FAILED ARCHIVE", exact: true }), { label: "sub-tab FAILED ARCHIVE" });
  await expect(page.getByText(/Failed Strategy Archive — every real lesson, permanently kept/)).toBeVisible();

  // DASHBOARD — the real, computed-on-request Executive Dashboard.
  await clickRobust(page, () => page.getByRole("button", { name: "DASHBOARD", exact: true }), { label: "sub-tab DASHBOARD" });
  await expect(page.getByText(/Portfolio Overview — real stage counts/)).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/Named Slots — each citing the real metric that earned it/)).toBeVisible();

  // Back to PIPELINE — the real Retirement action form opens and cancels
  // cleanly without actually retiring anything (a real, deliberate,
  // irreversible CEO action this test must not perform as a side effect).
  await clickRobust(page, () => page.getByRole("button", { name: "PIPELINE", exact: true }), { label: "sub-tab PIPELINE" });
  await expect(page.getByText(/Retirement — a real, deliberate CEO call, never automatic/)).toBeVisible();
  await clickRobust(page, () => page.getByRole("button", { name: "Retire This Strategy" }), { label: "Retire This Strategy" });
  await expect(page.getByPlaceholder(/Recent win rate has fallen/)).toBeVisible();
  await clickRobust(page, () => page.getByRole("button", { name: "Cancel" }), { label: "Cancel retire form" });
  await expect(page.getByRole("button", { name: "Retire This Strategy" })).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
