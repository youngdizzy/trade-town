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

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon") && !e.includes("Failed to process file"));
  expect(relevantErrors).toEqual([]);
});

test("Feature 52 (Part 1/2) — every Strategy Validation Laboratory sub-tab opens and renders its own real content", async ({ page }) => {
  test.setTimeout(140000); // 10 real sub-tabs, each dismissing real popups along the way, plus the 50 EMA RESEARCH and STRATEGY COMPILER tabs' own real on-demand backtest + full research-experiment computation
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
  // computed fresh on request, plus the v0.7 Feature 53 15-point
  // Company Certification checklist.
  await expect(page.getByRole("button", { name: "CERTIFICATION", exact: true })).toHaveClass(/text-cmd-cyan/, { timeout: 10_000 });
  await expect(page.getByText(/No real validation evidence on file yet|Confidence Score|Monte Carlo Testing/).first()).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/Company Certification — 15 real requirements/)).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/^(CERTIFIED|NOT CERTIFIED)$/).first()).toBeVisible();

  // HEALTH — the honest "Live Performance Monitor" reframe.
  await clickRobust(page, () => page.getByRole("button", { name: "HEALTH", exact: true }), { label: "sub-tab HEALTH" });
  await expect(page.getByText(/Strategy Health — real simulation performance, not live P&L/)).toBeVisible();

  // EVOLUTION — the honest "Strategy Evolution" reframe (real stage
  // history, never fabricated versioning). Scoped to the Sandbox
  // sub-tab nav bar (identified by its own "PIPELINE" label) since the
  // Command Center's own top-level "AI WORKFORCE" section has an
  // unrelated "EVOLUTION" tab with the identical accessible name.
  const sandboxSubTabNav = page.locator("nav").filter({ hasText: "PIPELINE" });
  await clickRobust(page, () => sandboxSubTabNav.getByRole("button", { name: "EVOLUTION", exact: true }), { label: "sub-tab EVOLUTION" });
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

  // 50 EMA RESEARCH — CEO directive "Market-Analysis Knowledge + Session
  // Intelligence Expansion," Phase 15. A real, on-demand bar-by-bar
  // backtest, kept explicitly separate from the source material's own
  // claimed win rate.
  await clickRobust(page, () => page.getByRole("button", { name: "50 EMA RESEARCH", exact: true }), { label: "sub-tab 50 EMA RESEARCH" });
  await expect(page.getByText("50 EMA Breakout + Pullback — Research Hypothesis")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Source Claim vs. TradeTown Evidence")).toBeVisible();
  await expect(page.getByText(/SOURCE CLAIM, not TradeTown-validated evidence/)).toBeVisible();

  // STRATEGY COMPILER — CEO directive "Professional Quant Trading Firm —
  // Quant Intelligence + Market Analysis Completion Phase," Phase F. A
  // real, deterministic English-language strategy compiler (never an LLM
  // guess) plus a generic backtest engine that runs the compiled
  // definition against real (mock) candle history.
  await clickRobust(page, () => sandboxSubTabNav.getByRole("button", { name: "STRATEGY COMPILER", exact: true }), { label: "sub-tab STRATEGY COMPILER" });
  await expect(page.getByText("English Strategy → Structured, Reproducible Definition")).toBeVisible();
  await clickRobust(page, () => page.getByRole("button", { name: "Compile Strategy", exact: true }), { label: "Compile Strategy" });
  await expect(page.getByText(/Compiled Definition/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("compiled", { exact: true })).toBeVisible();
  await clickRobust(page, () => page.getByRole("button", { name: "Backtest This Definition" }), { label: "Backtest This Definition" });
  await expect(page.getByText(/Overall — \d+ symbols/)).toBeVisible({ timeout: 20_000 });
  // CEO directive "Professional Quant Firm Phase" follow-up — real regime breakdowns and the
  // Feature 38 Sharpe/Sortino/Calmar/Max DD row, both now shared by every bucket display.
  await expect(page.getByText("Regime Trend Breakdown")).toBeVisible();
  await expect(page.getByText("Regime Volatility Breakdown")).toBeVisible();
  await expect(page.getByText("Sharpe", { exact: true }).first()).toBeVisible();

  // "Next Research + Validation Pass" — one bundled real experiment
  // record (walk-forward stability, one-parameter-at-a-time stop/target
  // sensitivity, transaction-cost/slippage sensitivity, and a
  // structural look-ahead audit) for this same compiled definition.
  await clickRobust(page, () => page.getByRole("button", { name: "Run Full Research Experiment", exact: true }), { label: "Run Full Research Experiment" });
  await expect(page.getByText(/Research Experiment —/)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Walk-Forward Stability", { exact: true })).toBeVisible();
  await expect(page.getByText("Parameter Sensitivity", { exact: true })).toBeVisible();
  await expect(page.getByText("Cost / Slippage Sensitivity", { exact: true })).toBeVisible();
  await expect(page.getByText("Look-Ahead Audit", { exact: true })).toBeVisible();

  // Back to PIPELINE — the real Retirement action form opens and cancels
  // cleanly without actually retiring anything (a real, deliberate,
  // irreversible CEO action this test must not perform as a side effect).
  await clickRobust(page, () => page.getByRole("button", { name: "PIPELINE", exact: true }), { label: "sub-tab PIPELINE" });
  await expect(page.getByText(/Retirement — a real, deliberate CEO call, never automatic/)).toBeVisible();
  await clickRobust(page, () => page.getByRole("button", { name: "Retire This Strategy" }), { label: "Retire This Strategy" });
  await expect(page.getByPlaceholder(/Recent win rate has fallen/)).toBeVisible();
  await clickRobust(page, () => page.getByRole("button", { name: "Cancel" }), { label: "Cancel retire form" });
  await expect(page.getByRole("button", { name: "Retire This Strategy" })).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon") && !e.includes("Failed to process file"));
  expect(relevantErrors).toEqual([]);
});

test("CEO directive 'Professional Quant Firm Phase' — the QUANT RESEARCH LAB sub-tab files a real experiment, registers a real version, and runs a real 2-strategy tournament", async ({ page }) => {
  test.setTimeout(180000); // compile + file experiment (one full research-experiment run) + register version + a second compile + tournament (two full research-experiment runs)
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "SANDBOX");
  await clickRobust(page, () => page.getByRole("button", { name: "QUANT RESEARCH LAB", exact: true }), { label: "sub-tab QUANT RESEARCH LAB" });
  await expect(page.getByText("Compile a Definition", { exact: true })).toBeVisible();

  // A unique name per run: POST /register-strategy-version and
  // POST /quant-research-lab/experiments are real, persisted state
  // mutations against this dev server's own real save file, so re-running
  // this test against an already-registered "50 EMA Pullback" would find
  // pre-existing version history from a prior run rather than a fresh one.
  const uniqueName = `50 EMA Pullback ${Date.now()}`;
  await page.getByPlaceholder("Strategy name").fill(uniqueName);

  // Compile the first definition, then exercise Feature 36 (file a
  // hypothesis-driven experiment) and Feature 37 (register a real
  // persisted version) against it.
  await clickRobust(page, () => page.getByRole("button", { name: "Compile", exact: true }), { label: "Compile" });
  await expect(page.getByText("Feature 36 — File to the Quant Research Lab")).toBeVisible({ timeout: 15_000 });

  const hypothesis = `The 50 EMA breakout works better during the London session (${Date.now()}).`;
  await page.getByPlaceholder(/50 EMA breakout \+ pullback setup performs better/).fill(hypothesis);
  await page.getByPlaceholder(/Momentum continuation after a confirmed trend-following breakout/).fill("Trend-following continuation after a confirmed breakout should outperform during higher-liquidity sessions.");
  await page.getByPlaceholder(/Flat or negative expectancy across a real out-of-sample walk-forward window/).fill("Flat or negative expectancy across a real out-of-sample walk-forward window would disprove this.");
  await clickRobust(page, () => page.getByRole("button", { name: "File Experiment", exact: true }), { label: "File Experiment" });
  const filedLine = page.getByText(/^Filed as experiment-/);
  await expect(filedLine).toBeVisible({ timeout: 30_000 });
  // Scoped to the filed-result row, not a bare page-wide search — this dev
  // save file is long-lived and never deletes prior experiments, so a
  // page-wide outcome-pill search can match many unrelated rows already on
  // screen (e.g. the duplicate-warning block's own matched-experiment pills).
  const filedRow = filedLine.locator("xpath=..");
  await expect(filedRow.getByText(/^(promising|inconclusive|rejected)$/)).toBeVisible();

  await expect(page.getByText("Never registered")).toBeVisible();
  await clickRobust(page, () => page.getByRole("button", { name: "Register This Text as a New Version", exact: true }), { label: "Register This Text as a New Version" });
  await expect(page.getByText("v1", { exact: true })).toBeVisible({ timeout: 15_000 });

  // Feature 40 — add this definition to the tournament roster, compile a
  // second, different definition, add it too, then run the real
  // tournament and check its comparison table / superlatives / rounds
  // all render.
  await clickRobust(page, () => page.getByRole("button", { name: "Add To Roster", exact: true }), { label: "Add To Roster" });
  await expect(page.getByText("Tournament Roster (1)")).toBeVisible();

  await page.getByPlaceholder("Strategy name").fill(`20 EMA Pullback ${Date.now()}`);
  await page.getByPlaceholder(/Describe the strategy in plain English/).fill("Buy when price closes above the 20 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 3R.");
  await clickRobust(page, () => page.getByRole("button", { name: "Compile", exact: true }), { label: "Compile (second definition)" });
  await expect(page.getByText("Feature 36 — File to the Quant Research Lab")).toBeVisible({ timeout: 15_000 });
  await clickRobust(page, () => page.getByRole("button", { name: "Add To Roster", exact: true }), { label: "Add To Roster (second)" });
  await expect(page.getByText("Tournament Roster (2)")).toBeVisible();

  await clickRobust(page, () => page.getByRole("button", { name: "Run Tournament", exact: true }), { label: "Run Tournament" });
  await expect(page.getByText(/Tournament Comparison/)).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("Named Superlatives — one real dimension per slot, never blended")).toBeVisible();
  await expect(page.getByText("Elimination Rounds")).toBeVisible();
  await expect(page.getByText(/Round 7 — Portfolio interaction/)).toBeVisible();
  await expect(page.getByText("architecturally blocked").first()).toBeVisible();
  await expect(page.getByText(/never an autonomous production promotion/)).toBeVisible();
  // Round 7 follow-up — a real per-symbol pairwise return correlation, computed from each
  // candidate's own walk-forward windows (never a full portfolio-level backtest).
  await expect(page.getByText(/Real Pairwise Return Correlation/)).toBeVisible();

  // The permanent search view — the experiment filed above must be
  // findable, since nothing in the Quant Research Lab is ever deleted.
  await clickRobust(page, () => page.getByRole("button", { name: "Load All", exact: true }), { label: "Load All (search)" });
  // .last(): the textarea above still literally contains this same text too — the search-results
  // card renders after it in the DOM.
  await expect(page.getByText(hypothesis).last()).toBeVisible({ timeout: 15_000 });
  // Phase 10 — a real per-strategy-family test count renders alongside the filed experiment.
  await expect(page.getByText("Family test #").first()).toBeVisible();
  // Phase 5 — a real buy-and-hold baseline (context only) renders alongside the filed experiment.
  await expect(page.getByText(/Buy-and-hold context:/).first()).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon") && !e.includes("Failed to process file"));
  expect(relevantErrors).toEqual([]);
});
