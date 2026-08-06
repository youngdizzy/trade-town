import { test, expect } from "@playwright/test";
import { clickButton, clickExpand, clickTab, continueGame } from "./helpers";

/**
 * Design Bible Chapter 71 — Economic Intelligence Center. Same real-app
 * testing approach as marketIntel.spec.ts/execIntel.spec.ts — exercises
 * the live Vite + FastAPI stack, no mocking.
 */

test("economicIntelligence is present in the real backend state", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(state.economicIntelligence).toBeTruthy();
  expect(typeof state.economicIntelligence.regime).toBe("string");
  expect(typeof state.economicIntelligence.regimeLabel).toBe("string");
  expect(state.economicIntelligence.health).toBeTruthy();
  expect(Array.isArray(state.economicIntelligence.health.factors)).toBe(true);
  expect(state.economicIntelligence.health.factors.length).toBe(5);
  expect(state.economicIntelligence.confidence).toBeTruthy();
  expect(Array.isArray(state.economicIntelligenceReports)).toBe(true);
});

test("the Economic Intelligence tab opens from the Command Center and shows the real live read", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (e) => consoleErrors.push(String(e)));

  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "ECONINTEL");

  await expect(page.getByText(/^Economic Health —/i)).toBeVisible();
  await expect(page.getByText(/Five Real Factors/)).toBeVisible();
  await expect(page.getByText("Regime Favorability", { exact: true })).toBeVisible();
  await expect(page.getByText("Market Quality", { exact: true })).toBeVisible();
  await expect(page.getByText("Correlation Clustering", { exact: true })).toBeVisible();
  await expect(page.getByText("Concentration", { exact: true })).toBeVisible();
  await expect(page.getByText(/Economic Confidence Engine/)).toBeVisible();
  await expect(page.getByText("Supporting", { exact: true })).toBeVisible();
  await expect(page.getByText("Contradicting", { exact: true })).toBeVisible();
  // "News Risk" appears twice — as a Five Factors card name and as the
  // standalone News Risk card's own header — either match proves the
  // panel rendered, same ambiguity-handling convention marketIntel.spec.ts
  // already uses for "Coach" matching both a department label and an agent.
  await expect(page.getByText("News Risk", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/Correlation Clustering — held symbols only/)).toBeVisible();

  await expect(page.getByText(/Daily Economic Intelligence Brief/)).toBeVisible();
  await expect(
    page.getByText(/No brief has been generated yet/).or(page.getByText(/One real snapshot per in-game evening/)).first(),
  ).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon") && !e.includes("Failed to process file"));
  expect(relevantErrors).toEqual([]);
});
