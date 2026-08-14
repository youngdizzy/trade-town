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

test("CEO directive Features 26-30, Feature 27 — the TALENT tab shows a real Agent Performance Review", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(Array.isArray(state.agentPerformanceReviews)).toBe(true);
  for (const review of state.agentPerformanceReviews) {
    expect(["evaluated", "not_enough_evidence"]).toContain(review.status);
    expect(Array.isArray(review.dimensions)).toBe(true);
    expect(review.dimensions.length).toBe(8);
    for (const dim of review.dimensions) {
      // Every dimension must disclose a real sample size, and a value
      // that's either a real number or an honest null — never a fake
      // placeholder like -1 or a string.
      expect(typeof dim.sampleSize).toBe("number");
      expect(dim.value === null || typeof dim.value === "number").toBe(true);
    }
  }

  await continueGame(page);
  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "TALENT");

  await expect(page.getByText(/Agent Performance Review —/)).toBeVisible();
});

test("CEO directive Features 26-30, Feature 28 — the TALENT tab shows a real Agent Skill Profile", async ({ page }) => {
  await page.goto("/");
  // /api/load deliberately returns archive modules (agentSkillProfiles
  // included) empty — see routers/save.py's own docstring — so real
  // evidence is checked via the dedicated per-agent endpoint instead.
  const profile = await page.evaluate(async () => {
    const res = await fetch("/api/skill-profiles/scout/latest");
    return res.json();
  });
  if (profile) {
    expect(Array.isArray(profile.assessments)).toBe(true);
    expect(profile.assessments.length).toBe(11);
    for (const a of profile.assessments) {
      // Every domain must disclose a real sample size and evidence
      // string, and a value that's either a real number or an honest
      // null (NOT_ENOUGH_EVIDENCE or NOT_TRACKABLE_YET) — never a fake
      // placeholder.
      expect(typeof a.sampleSize).toBe("number");
      expect(a.value === null || typeof a.value === "number").toBe(true);
      expect(typeof a.evidence).toBe("string");
      expect(a.evidence.length).toBeGreaterThan(0);
      expect(["improving", "stagnant", "regressed", "not_enough_history"]).toContain(a.trend);
    }
  }

  await continueGame(page);
  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "TALENT");

  await expect(page.getByText(/Skill Progression —/)).toBeVisible();
});
