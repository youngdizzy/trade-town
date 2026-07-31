import { test, expect } from "@playwright/test";
import { clickButton, clickExpand, clickTab, continueGame } from "./helpers";

/**
 * v0.7 Feature 44 — the Talent Discovery System. Same real-app testing
 * approach as replay.spec.ts/execIntel.spec.ts — exercises the live Vite
 * + FastAPI stack, no mocking.
 */

test("talent is present in the real backend state", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(state.talent).toBeTruthy();
  expect(Array.isArray(state.talent.reports)).toBe(true);
  expect(Array.isArray(state.talent.viewedReportIds)).toBe(true);
});

test("the Talent Discovery tab opens from the Command Center and shows Discovery Events, Growth History, Best Collaborators, and Performance Analysis", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "TALENT");

  await expect(page.getByText("Discovery Events — Talent Reports", { exact: true })).toBeVisible();
  await expect(page.getByText("Growth History", { exact: true })).toBeVisible();
  await expect(page.getByText("Best Collaborators", { exact: true })).toBeVisible();
  await expect(page.getByText(/The roster is fixed/)).toBeVisible();
  await expect(page.getByText("Performance Analysis — Thinking Profiles", { exact: true })).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
