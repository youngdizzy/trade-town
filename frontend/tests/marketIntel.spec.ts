import { test, expect } from "@playwright/test";
import { clickButton, clickExpand, clickTab, continueGame } from "./helpers";

/**
 * v0.7 Feature 51 — Market Intelligence Department. Same real-app
 * testing approach as execIntel.spec.ts/blackBox.spec.ts — exercises the
 * live Vite + FastAPI stack, no mocking.
 */

test("marketIntelligence is present in the real backend state", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(state.marketIntelligence).toBeTruthy();
  expect(typeof state.marketIntelligence.regime).toBe("string");
  expect(typeof state.marketIntelligence.regimeLabel).toBe("string");
  expect(state.marketIntelligence.quality).toBeTruthy();
  expect(Array.isArray(state.marketIntelligence.liquidity)).toBe(true);
  expect(Array.isArray(state.marketIntelligence.structure)).toBe(true);
  expect(Array.isArray(state.marketIntelligenceReports)).toBe(true);
  expect(Array.isArray(state.marketIntelligenceLearning)).toBe(true);
});

test("the Market Intelligence tab opens from the Command Center and shows the real live read", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (e) => consoleErrors.push(String(e)));

  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "MARKETINTEL");

  // TerminalLabel renders this uppercase via CSS text-transform only —
  // the underlying DOM text (what getByText actually matches) stays
  // title-case ("Market Regime — ..."), so this match must be case-
  // insensitive.
  await expect(page.getByText(/^Market Regime —/i)).toBeVisible();
  await expect(page.getByText("Session", { exact: true })).toBeVisible();
  await expect(page.getByText("Volatility", { exact: true })).toBeVisible();
  await expect(page.getByText("Momentum", { exact: true })).toBeVisible();
  await expect(page.getByText("Institutional Activity", { exact: true })).toBeVisible();
  await expect(page.getByText("News Risk", { exact: true })).toBeVisible();
  await expect(page.getByText(/Liquidity & Structure — By Symbol/)).toBeVisible();

  // The Executive Market Brief and Learning Loop are once-daily real
  // history — either real cards or the honest empty state must render,
  // never a blank/broken panel, regardless of how far into the current
  // in-game day this dev backend happens to be.
  await expect(page.getByText(/Executive Market Brief/)).toBeVisible();
  await expect(
    page.getByText(/No Executive Market Brief has been generated yet/).or(page.getByText(/One real snapshot per in-game evening/)),
  ).toBeVisible();
  await expect(page.getByText("Learning Loop", { exact: true })).toBeVisible();
  // .first(): the shared dev backend may have accumulated several real
  // graded days by now, each with its own "predicted ..." entry — any
  // one of them (or the honest empty state) proves the panel rendered
  // real content, so this only needs at least one match, not a unique one.
  await expect(
    page.getByText(/No prior brief has been graded against a real outcome yet/).or(page.getByText(/predicted/)).first(),
  ).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon") && !e.includes("Failed to process file"));
  expect(relevantErrors).toEqual([]);
});
