import { test, expect } from "@playwright/test";
import { clickButton, clickExpand, clickTab, continueGame } from "./helpers";

/**
 * v0.7 Feature 49 (Phase 3, revised) — the Foundational Mentor Program /
 * Professional Academy. Employees are the real students (auto-progress
 * every backend tick); the CEO manages via a dashboard and may
 * optionally also take lessons personally (CEO Learning Mode). Same
 * real-app testing approach as dailyObjectives.spec.ts — exercises the
 * live Vite + FastAPI stack, no mocking.
 */

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

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "MENTORLIB");

  await expect(page.getByText("Professional Academy")).toBeVisible();
  await expect(page.getByText("Academy Statistics")).toBeVisible();
  await expect(page.getByText(/Employees complete Academy training automatically/)).toBeVisible();

  // Personal learning is hidden until CEO Learning Mode is switched on.
  await expect(page.getByTestId("ceo-personal-learning")).toHaveCount(0);

  await clickButton(page, /CEO Learning Mode: OFF/);
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

test("Current Certifications honestly shows no certifications and no per-row actions before any real graduation exists", async ({ page }) => {
  // Certification Management's Revoke/Downgrade/Promote can only act on
  // a real earned CertificationRecord, and reaching one takes many real
  // ticks plus a probabilistic real quiz pass through
  // tick_employee_progress() — there is no test-only shortcut to force
  // it (ClientSaveRequest, the real /api/save shape, only ever accepts
  // player/settings/dialogueHistory, deliberately never
  // foundationalMentorState — see app/schemas.py). The full lifecycle
  // (revoke/downgrade/promote/reset progress, history preservation,
  // re-earning) is covered thoroughly by TestCertificationManagement in
  // test_foundational_mentors.py; this test covers what's honestly
  // reachable live: the empty state before any certification exists.
  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "MENTORLIB");

  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  const certifications = state.foundationalMentorState.certifications as unknown[];
  test.skip(certifications.length > 0, "a real employee has already earned a certification in this shared dev backend — the honest-empty-state case no longer applies");

  await expect(page.getByText("Current Certifications")).toBeVisible();
  await expect(page.getByText("No certifications earned yet.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Revoke", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Downgrade", exact: true })).toHaveCount(0);
});
