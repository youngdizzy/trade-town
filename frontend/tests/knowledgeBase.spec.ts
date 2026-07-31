import { test, expect } from "@playwright/test";
import { clickButton, clickExpand, clickTab, continueGame } from "./helpers";

/**
 * v0.7 Feature 47 — the Company Operating System. Same real-app testing
 * approach as sandbox.spec.ts/constitution.spec.ts — exercises the live
 * Vite + FastAPI stack, no mocking.
 */

test("every ChallengeReport carries a real citedArticleIds array", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(Array.isArray(state.challengeReports)).toBe(true);
  for (const report of state.challengeReports) {
    expect(Array.isArray(report.citedArticleIds)).toBe(true);
    // every cited id must be a real Article on the Constitution
    const realArticleIds = state.constitution.articles.map((a: { id: string }) => a.id);
    for (const articleId of report.citedArticleIds) {
      expect(realArticleIds).toContain(articleId);
    }
  }
});

test("the OPS tab opens from the Command Center and shows the Knowledge Base timeline", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "OPS");

  await expect(page.getByText("Knowledge Base — everything the company has learned", { exact: true })).toBeVisible();
  await expect(page.getByText("Library of Mistakes", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Timeline", { exact: true })).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
