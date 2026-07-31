import { test, expect } from "@playwright/test";
import { clickButton, clickExpand, clickTab, continueGame } from "./helpers";

/**
 * v0.7 Feature 42 — the Decision Replay Center. Same real-app testing
 * approach as commandCenter.spec.ts/blackBox.spec.ts — exercises the live
 * Vite + FastAPI stack, no mocking.
 */

test("the Decision Replay Center opens from the Command Center and shows the structured filter grid", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "REPLAY");

  await expect(page.getByText("Smart Search — Structured Filters", { exact: true })).toBeVisible();
  await expect(page.getByText(/Decision Archive/)).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});

test("filtering by result and resetting filters both work against real decision data", async ({ page }) => {
  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "REPLAY");

  // Filter selects render in DOM order: Employee, Department, Result.
  const resultSelect = page.locator("select").nth(2);
  await resultSelect.selectOption("loss");
  await expect(page.getByText("Reset Filters", { exact: true })).toBeVisible();

  await page.getByText("Reset Filters", { exact: true }).click();
  await expect(page.getByText("Reset Filters", { exact: true })).not.toBeVisible();
});

test("opening a decision's replay shows the Full Decision Timeline with an honest per-stage status", async ({ page }) => {
  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "REPLAY");

  const firstRow = page.locator("tbody tr").first();
  const hasRow = await firstRow.isVisible().catch(() => false);
  test.skip(!hasRow, "no decisions recorded yet in this run — nothing to open a replay for");

  await firstRow.click();
  await expect(page.getByText(/Full Decision Timeline/)).toBeVisible();
  await expect(page.getByText("Quant Review", { exact: true })).toBeVisible();
  await expect(page.getByText("N/A", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Decision Recording", { exact: true })).toBeVisible();
  await expect(page.getByText(/Stop Loss, Profit Target, and Expected Value are not shown/)).toBeVisible();

  await page.getByRole("button", { name: "CLOSE ✕" }).last().click();
});
