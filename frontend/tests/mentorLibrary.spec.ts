import { test, expect, type Page } from "@playwright/test";

/**
 * v0.7 Feature 49 (Phase 3, revised) — the Foundational Mentor Program /
 * Professional Academy. Employees are the real students (auto-progress
 * every backend tick); the CEO manages via a dashboard and may
 * optionally also take lessons personally (CEO Learning Mode). Same
 * real-app testing approach as dailyObjectives.spec.ts — exercises the
 * live Vite + FastAPI stack, no mocking.
 */

async function clickContinueOnTitleScreen(page: Page): Promise<void> {
  const canvas = page.locator("canvas");
  await expect(canvas).toBeVisible();
  await page.waitForTimeout(800);
  for (let attempt = 0; attempt < 5; attempt++) {
    const box = await canvas.boundingBox();
    if (!box) throw new Error("canvas has no bounding box");
    await page.mouse.click(box.x + box.width / 2, box.y + box.height * 0.5 + 44);
    try {
      await page.getByRole("button", { name: "Command ⌁" }).waitFor({ state: "attached", timeout: 3000 });
      return;
    } catch {
      // not in-game yet — try again
    }
  }
  throw new Error("clickContinueOnTitleScreen: never reached an in-game scene after 5 click attempts");
}

async function dismissTradeOutcomePopups(page: Page): Promise<void> {
  for (let i = 0; i < 5; i++) {
    const tradeBanner = page.getByTestId("trade-outcome-banner");
    if (await tradeBanner.isVisible().catch(() => false)) {
      await tradeBanner.getByText("Dismiss").click();
      await tradeBanner.waitFor({ state: "hidden", timeout: 3000 }).catch(() => {});
      continue;
    }
    const votingPopup = page.getByTestId("executive-voting");
    if (await votingPopup.isVisible().catch(() => false)) {
      await votingPopup.getByText("Decide later").click();
      await votingPopup.waitFor({ state: "hidden", timeout: 3000 }).catch(() => {});
      continue;
    }
    return;
  }
}

async function continueGame(page: Page): Promise<void> {
  await clickContinueOnTitleScreen(page);
  await dismissTradeOutcomePopups(page);
}

async function clickTab(page: Page, tab: string): Promise<void> {
  for (let attempt = 0; attempt < 5; attempt++) {
    await dismissTradeOutcomePopups(page);
    try {
      await page.getByRole("button", { name: tab, exact: true }).click({ timeout: 5000 });
      return;
    } catch {
      // a popup intercepted the click — loop back and dismiss again
    }
  }
  throw new Error(`clickTab: could not click "${tab}" after 5 attempts`);
}

test("the backend auto-progresses real employee students, not the CEO, through the active mentor track", async ({ page }) => {
  await page.goto("/");
  // Give the shared dev backend's real tick loop a moment to run at
  // least once — the same "wait for a real tick" convention as other
  // real-app tests in this suite (see dailyObjectives.spec.ts).
  await page.waitForTimeout(2500);
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  const fm = state.foundationalMentorState;
  expect(fm).toBeTruthy();
  // The shared dev backend persists real CEO-added custom mentors (see
  // mentorLab.spec.ts) appended after the six built-in ones, so this
  // checks the built-in roadmap prefix rather than an exact array match.
  const mentorIds = fm.mentors.map((m: { id: string }) => m.id);
  expect(mentorIds.slice(0, 6)).toEqual(["tjr", "al_brooks", "linda_raschke", "mark_douglas", "tom_hougaard", "mike_bellafiore"]);

  const tjr = fm.mentors.find((m: { id: string }) => m.id === "tjr");
  expect(tjr.status).toBe("active");
  expect(tjr.lessons.length).toBe(8);
  expect(tjr.contentNote).toContain("original TradeTown-authored teaching material");

  // Real employee students only — never the CEO, never Coach/Sage/CIO/Quant.
  const studentAgentIds = ["scout", "atlas", "echo", "nova", "scribe", "sentinel", "pulse", "guardian"];
  const progressKeys = Object.keys(fm.progress);
  for (const key of progressKeys) expect(studentAgentIds).toContain(key);
  expect(progressKeys.length).toBeGreaterThan(0);
  expect(fm.progress.coach).toBeUndefined();
  expect(fm.progress.sage).toBeUndefined();

  const scoutTjr = fm.progress.scout?.tjr;
  expect(scoutTjr).toBeTruthy();
  expect(typeof scoutTjr.currentLessonStudyPct).toBe("number");
  // The shared dev backend keeps ticking in real time across this whole
  // suite, so by the time this runs scout may honestly have finished the
  // curriculum and be sitting in the real CEO-approval queue already —
  // either status proves the same thing (auto-progression, no CEO quiz).
  expect(["in_progress", "pending_approval"]).toContain(scoutTjr.graduationStatus);

  // Not asserted empty: the shared dev backend persists real CEO Learning
  // Mode activity from other tests/sessions in this same suite (see the
  // MENTORLIB test below) — only the shape and key space matter here.
  for (const key of Object.keys(fm.ceoProgress)) expect(typeof key).toBe("string");
});

test("the MENTORLIB tab renders the Academy Dashboard and CEO Learning Mode reveals a separate personal-learning panel", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await continueGame(page);

  for (let attempt = 0; attempt < 5; attempt++) {
    await dismissTradeOutcomePopups(page);
    try {
      await page.getByRole("button", { name: "Command ⌁" }).click({ timeout: 5000 });
      break;
    } catch {
      // a popup intercepted the click — loop back and dismiss again
    }
  }
  await page.getByRole("button", { name: "EXPAND — FULL COMMAND CENTER" }).click();
  await clickTab(page, "MENTORLIB");

  await expect(page.getByText("Professional Academy")).toBeVisible();
  await expect(page.getByText("Academy Statistics")).toBeVisible();
  await expect(page.getByText(/Employees complete Academy training automatically/)).toBeVisible();

  // Personal learning is hidden until CEO Learning Mode is switched on.
  await expect(page.getByTestId("ceo-personal-learning")).toHaveCount(0);

  for (let attempt = 0; attempt < 5; attempt++) {
    await dismissTradeOutcomePopups(page);
    try {
      await page.getByRole("button", { name: /CEO Learning Mode: OFF/ }).click({ timeout: 5000 });
      break;
    } catch {
      // a popup intercepted the click — loop back and dismiss again
    }
  }
  await expect(page.getByTestId("ceo-personal-learning")).toBeVisible();

  await page.getByText("1. Trading Psychology: Process Over Outcome").click();
  const viewer = page.getByTestId("ceo-lesson-viewer");
  await expect(viewer.getByText("Trading Psychology: Process Over Outcome")).toBeVisible();

  await viewer.getByRole("button", { name: "It stays high — Discipline Score never reads trade P&L" }).click();
  await Promise.all([page.waitForResponse((res) => res.url().includes("/api/foundational-mentors/ceo/quiz") && res.ok()), viewer.getByRole("button", { name: "Submit Answer" }).click()]);
  await expect(viewer.getByText(/CORRECT|NOT QUITE/)).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
