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

test("CEO directive Features 26-30, Feature 26 — the OPS tab shows Institutional Memory with real promoted lessons", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(Array.isArray(state.institutionalMemory)).toBe(true);
  for (const entry of state.institutionalMemory) {
    expect(typeof entry.observation).toBe("string");
    expect(entry.observation.length).toBeGreaterThan(0);
    expect(["active", "superseded", "contradicted", "stale"]).toContain(entry.status);
    expect(entry.confidence).toBeGreaterThanOrEqual(0);
    expect(entry.relevancePct).toBeGreaterThanOrEqual(0);
  }

  await continueGame(page);
  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "OPS");

  await expect(page.getByText("Institutional Memory — promoted lessons", { exact: true })).toBeVisible();
  // The live sim keeps ticking between the /api/load fetch above and this
  // check, so assert against the DOM at check-time rather than the
  // earlier snapshot: either real promoted entries are showing, or the
  // honest empty state is — never neither.
  const hasEntries = await page.getByTestId("institutional-memory-entry").first().isVisible().catch(() => false);
  const hasEmptyState = await page
    .getByText("No institutional memory filed yet", { exact: false })
    .isVisible()
    .catch(() => false);
  expect(hasEntries || hasEmptyState).toBe(true);
});
