import { test, expect } from "@playwright/test";
import { clickButton, clickExpand, clickTab, continueGame } from "./helpers";

/**
 * v0.7 Feature 49 — Professional Day Trading Program's Daily Trading
 * Objectives. Same real-app testing approach as sandbox.spec.ts/
 * constitution.spec.ts — exercises the live Vite + FastAPI stack, no
 * mocking.
 */

test("the backend state carries real Daily Trading Objectives fields", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(state.riskLimits.dailyProfitTargetPct).toBeGreaterThan(0);
  expect(state.riskLimits.maxTradesPerDay).toBeGreaterThan(0);
  expect(state.riskLimits.maxDailyLossPct).toBeGreaterThan(0);
  expect(state.dailyObjectiveStatus).toBeTruthy();
  expect(typeof state.dailyObjectiveStatus.tradesToday).toBe("number");
  expect(typeof state.dailyObjectiveStatus.tradingHalted).toBe("boolean");
});

test("the RISK tab shows Daily Trading Objectives and a real CEO update round-trips through POST /api/risk-limits", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "RISK");

  await expect(page.getByText(/Daily Trading Objectives/)).toBeVisible();
  await expect(page.getByText("Trades today")).toBeVisible();

  const uniqueTarget = "7.5";
  const targetInput = page.getByLabel("Daily profit target (%)");
  await targetInput.fill(uniqueTarget);

  await Promise.all([page.waitForResponse((res) => res.url().includes("/api/risk-limits") && res.ok()), page.getByRole("button", { name: "Save Objectives" }).click()]);

  await expect(page.getByText("Daily profit target", { exact: true }).locator("xpath=following-sibling::span")).toContainText("7.5%");

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
