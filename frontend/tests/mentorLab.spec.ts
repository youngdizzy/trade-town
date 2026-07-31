import { test, expect } from "@playwright/test";
import { clickButton, clickExpand, clickTab, continueGame } from "./helpers";

/**
 * Command Center UI Revision — the Mentor Lab tab. Mentor-centric
 * browsing/authoring, distinct from MENTORLIB's employee-centric Academy
 * Dashboard: pick a mentor track, see its curriculum, and (real,
 * in-product) add brand-new CEO-authored mentors/lessons. Same real-app
 * testing approach as mentorLibrary.spec.ts — exercises the live Vite +
 * FastAPI stack, no mocking.
 */

test("Mentor Lab: CEO can add a real custom mentor, author a lesson for it, and make it the active track", async ({ page }) => {
  test.setTimeout(60000); // several sequential form fills + network round trips against the real backend
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await continueGame(page);

  await clickButton(page, "Command ⌁");
  await clickExpand(page);
  await clickTab(page, "MENTORLAB");

  await expect(page.getByText("Mentor Roadmap")).toBeVisible();
  await expect(page.getByText("Company Concepts Learned")).toBeVisible();
  await expect(page.getByText("Mentor Comparison")).toBeVisible();

  const uniqueName = `Playwright Test Mentor ${Date.now()}`;
  await clickButton(page, "+ Add New Mentor");
  await page.getByLabel("Mentor name").fill(uniqueName);
  await page.getByLabel(/Focus areas/).fill("Order Flow, Tape Reading");
  await Promise.all([page.waitForResponse((res) => res.url().includes("/api/foundational-mentors/add-mentor") && res.ok()), page.getByRole("button", { name: "Add Mentor" }).click()]);

  await expect(page.getByText(`${uniqueName} Track`).first()).toBeVisible();
  await expect(page.getByText("This track's content will be entirely CEO-authored")).toHaveCount(0);

  await clickButton(page, "+ Add Lesson (Build Curriculum)");
  await page.getByLabel("Lesson title").fill("Reading the Tape");
  await page.getByLabel("Simple explanation").fill("Watch order flow, not just price.");
  await page.getByLabel("Deeper explanation").fill("Large resting orders and absorption reveal where real supply and demand sit.");
  await page.getByLabel("Quiz question").fill("What does absorption at a price level suggest?");
  const optionInputs = page.locator('input[placeholder^="Option "]');
  await optionInputs.nth(0).fill("A large player is soaking up opposing supply");
  await optionInputs.nth(1).fill("The market is closed");
  await optionInputs.nth(2).fill("Volume is zero");
  await optionInputs.nth(3).fill("The ticker is delisted");
  await Promise.all([page.waitForResponse((res) => res.url().includes("/api/foundational-mentors/add-lesson") && res.ok()), page.getByRole("button", { name: "Add Lesson", exact: true }).click()]);

  await expect(page.getByText("Reading the Tape")).toBeVisible();

  await Promise.all([page.waitForResponse((res) => res.url().includes("/api/foundational-mentors/set-active") && res.ok()), clickButton(page, "Make Active Track")]);
  await expect(page.getByRole("button", { name: "Make Active Track" })).toHaveCount(0);

  // This suite shares one always-on dev backend across every spec file —
  // restore TJR as the active track afterward so this test doesn't
  // permanently redirect company-wide focus away from what
  // mentorLibrary.spec.ts (and the rest of the app) expect to find active.
  await page.getByRole("button", { name: "TJR Track" }).click();
  await Promise.all([page.waitForResponse((res) => res.url().includes("/api/foundational-mentors/set-active") && res.ok()), clickButton(page, "Make Active Track")]);
  await expect(page.getByRole("button", { name: "Make Active Track" })).toHaveCount(0);

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
