import { test, expect } from "@playwright/test";
import { clickButton, clickExpand, clickTab, continueGame } from "./helpers";

/**
 * Design Bible Chapter 74/74.5 — the EvolutionPanel bundles CLSIS Self-
 * Improvement Proposals + the Institutional Evolution Engine (Part 1/2)
 * and the CEO Vision Board (Chapter 74.5) into one Command Center tab,
 * previously frontend-less (a Chapters 67-75 audit finding). Same real
 * app testing approach as constitution.spec.ts — exercises the live
 * Vite + FastAPI stack, no mocking.
 */

test("the EVOLUTION tab opens from the Command Center and shows real CLSIS/Evolution/Vision Board data with no console errors", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "EVOLUTION");

  await expect(page.getByText("No self-improvement proposals filed yet", { exact: false })).toBeVisible();
  await expect(page.getByText("Executive Learning Summary", { exact: false })).toBeVisible();
  await expect(page.getByText("Company Evolution Score", { exact: false })).toBeVisible();
  await expect(page.getByText("Institutional Evolution Reports", { exact: false })).toBeVisible();
  await expect(page.getByText("CEO Vision Board", { exact: false })).toBeVisible();

  // The Executive Learning Summary fetch resolves for the default agent.
  await expect(page.getByText("Knowledge Tier", { exact: false })).toBeVisible();
  // The Company Evolution Score fetch resolves with a real overall/100 pill.
  await expect(page.getByText(/\/ 100/)).toBeVisible();

  expect(consoleErrors, `Console errors on the EVOLUTION tab: ${consoleErrors.join("\n")}`).toEqual([]);
});

test("the CEO can set a Vision Board mission and it persists through the real backend", async ({ page }) => {
  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "EVOLUTION");

  // A unique-per-run mission — this test hits the real, persisted dev
  // backend (same one across test runs), so a fixed string would go
  // stale (already-saved from a prior run) and leave "Save Mission"
  // disabled with nothing to click.
  const mission = `Become the most disciplined paper-trading company in the sim (run ${Date.now()}).`;
  const missionBox = page.getByPlaceholder("What is this company trying to become?");
  await missionBox.fill(mission);
  await page.getByRole("button", { name: "Save Mission" }).click();

  await expect(page.getByRole("button", { name: "Save Mission" })).toBeDisabled({ timeout: 5000 });

  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(state.visionBoard.mission).toBe(mission);
});
