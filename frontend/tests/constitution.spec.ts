import { test, expect } from "@playwright/test";
import { clickButton, clickExpand, clickTab, continueGame } from "./helpers";

/**
 * v0.7 Feature 46 — the Company Constitution. Same real-app testing
 * approach as sandbox.spec.ts/talent.spec.ts — exercises the live Vite
 * + FastAPI stack, no mocking.
 */

test("the Constitution's 8 real Articles are present in the backend state", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(state.constitution).toBeTruthy();
  expect(state.constitution.articles.map((a: { id: string }) => a.id)).toEqual(["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]);
  expect(state.constitution.articles[0].text).toBe("Protect capital first.");
  expect(Array.isArray(state.constitution.citations)).toBe(true);
  expect(Array.isArray(state.constitution.amendments)).toBe(true);
});

test("the Constitution tab opens from the Command Center, shows the Articles and Live Enforcement, and a proposed amendment runs the real pipeline", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "CONSTITUTION");

  await expect(page.getByText("The Articles — permanent company law", { exact: true })).toBeVisible();
  await expect(page.getByText("Protect capital first.", { exact: true })).toBeVisible();
  await expect(page.getByText("Live Enforcement", { exact: true })).toBeVisible();
  await expect(page.getByText("Propose an Amendment", { exact: true })).toBeVisible();

  // A unique title per run — the backend rejects a second pending
  // amendment with a title that's already pending, and this dev
  // backend's state persists across repeated test runs.
  const amendmentTitle = `Test Amendment ${Date.now()}`;
  await page.getByPlaceholder("Article title").fill(amendmentTitle);
  await page.getByPlaceholder("Article text").fill("Employees must double-check every real number before citing it.");
  await page.getByRole("button", { name: "Propose", exact: true }).click();
  await expect(page.getByText(amendmentTitle, { exact: true })).toBeVisible();

  const amendmentCard = page.getByTestId("amendment-card").filter({ hasText: amendmentTitle });
  await amendmentCard.getByRole("button", { name: "Send to Founders, Coach & Employees" }).click();
  await expect(page.getByText(/Employee vote \(advisory\)/)).toBeVisible();
  await expect(amendmentCard.getByRole("button", { name: "Ratify" })).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
