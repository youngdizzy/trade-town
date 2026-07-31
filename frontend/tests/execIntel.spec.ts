import { test, expect } from "@playwright/test";
import { clickButton, clickExpand, clickTab, continueGame } from "./helpers";

/**
 * v0.7 Feature 43 — the Executive Intelligence Dashboard. Same real-app
 * testing approach as replay.spec.ts/blackBox.spec.ts — exercises the
 * live Vite + FastAPI stack, no mocking.
 */

test("companyDna is present in the real backend state", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(state.companyDna).toBeTruthy();
  expect(Array.isArray(state.companyDna.traits)).toBe(true);
  expect(state.companyDna.traits.length).toBe(5);
  // v0.7 Feature 48 — Company Identity: a real, non-empty label always
  // present, "Not Yet Established" until enough history exists.
  expect(typeof state.companyDna.identity).toBe("string");
  expect(state.companyDna.identity.length).toBeGreaterThan(0);
  expect(state.companyHealth.teamChemistry).not.toBeUndefined();
});

test("the Executive Intelligence Dashboard opens from the Command Center and shows Company DNA, Executive Priorities, and Department Health", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "EXECINTEL");

  await expect(page.getByText("Company DNA", { exact: true })).toBeVisible();
  await expect(page.getByTestId("company-dna-identity")).toBeVisible();
  await expect(page.getByText("Risk Appetite", { exact: true })).toBeVisible();
  await expect(page.getByText("Patience", { exact: true })).toBeVisible();
  await expect(page.getByText("Contrarian Tendency", { exact: true })).toBeVisible();
  await expect(page.getByText("Research Rigor", { exact: true })).toBeVisible();
  await expect(page.getByText("Collaboration Style", { exact: true })).toBeVisible();

  await expect(page.getByText(/Executive Priorities/)).toBeVisible();

  await expect(page.getByText("Department Health", { exact: true })).toBeVisible();
  await expect(page.getByText("Academy", { exact: true })).toBeVisible();
  await expect(page.getByText("Research", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Trading", { exact: true })).toBeVisible();
  await expect(page.getByText("Innovation", { exact: true })).toBeVisible();
  await expect(page.getByText("Founders", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/Brain Room.*is not shown here/)).toBeVisible();

  // Company Health's COMPANY tab should now show Team Chemistry too.
  await clickTab(page, "COMPANY");
  await expect(page.getByText("Team Chemistry", { exact: true })).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
