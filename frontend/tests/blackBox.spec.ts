import { test, expect } from "@playwright/test";
import { clickButton, clickExpand, clickTab, continueGame } from "./helpers";

/**
 * v0.7 — the Advanced Quantitative Research Division (Black Box Research
 * Panel / CEO Research Dashboard). Same real-app testing approach as
 * commandCenter.spec.ts — exercises the live Vite + FastAPI stack.
 */

test("Quant agent is a real part of the backend roster", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(state.agents.quant).toBeTruthy();
  expect(state.blackBox).toBeTruthy();
});

test("the Black Box Research panel opens from the Command Center and shows real project state", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "BLACKBOX");

  // Either an active project's dashboard, or the honest empty state —
  // never a blank/crashed panel.
  const hasActiveProject = await page.getByText("Current Project —").isVisible().catch(() => false);
  const hasEmptyState = await page.getByText("No Black Box Research Project is currently active").isVisible().catch(() => false);
  expect(hasActiveProject || hasEmptyState).toBe(true);

  await page.getByText("Founder Council Reviews").waitFor({ state: "visible", timeout: 5000 });
  await page.getByText("Museum of Discoveries").waitFor({ state: "visible", timeout: 5000 });
  await page.getByText("Research Archives").waitFor({ state: "visible", timeout: 5000 });

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
