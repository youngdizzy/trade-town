import { test, expect } from "@playwright/test";
import { clickButton, clickExpand, clickTab, continueGame } from "./helpers";

/**
 * v0.7 Feature 45 — the Research Sandbox. Same real-app testing approach
 * as talent.spec.ts/execIntel.spec.ts — exercises the live Vite +
 * FastAPI stack, no mocking.
 */

test("strategies carry real stage/stageHistory/allocatedCapital in the backend state", async ({ page }) => {
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

  await page.getByRole("button", { name: "Run Backtest" }).click();
  await expect(page.getByText(/queued|running/).first()).toBeVisible({ timeout: 10_000 });

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
