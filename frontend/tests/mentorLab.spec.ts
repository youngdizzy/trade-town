import { test, expect, type Page } from "@playwright/test";

/**
 * Command Center UI Revision — the Mentor Lab tab. Mentor-centric
 * browsing/authoring, distinct from MENTORLIB's employee-centric Academy
 * Dashboard: pick a mentor track, see its curriculum, and (real,
 * in-product) add brand-new CEO-authored mentors/lessons. Same real-app
 * testing approach as mentorLibrary.spec.ts — exercises the live Vite +
 * FastAPI stack, no mocking.
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

async function clickButton(page: Page, name: string | RegExp): Promise<void> {
  for (let attempt = 0; attempt < 5; attempt++) {
    await dismissTradeOutcomePopups(page);
    try {
      await page.getByRole("button", { name }).click({ timeout: 5000 });
      return;
    } catch {
      // a popup intercepted the click — loop back and dismiss again
    }
  }
  throw new Error(`clickButton: could not click "${String(name)}" after 5 attempts`);
}

test("Mentor Lab: CEO can add a real custom mentor, author a lesson for it, and make it the active track", async ({ page }) => {
  test.setTimeout(60000); // several sequential form fills + network round trips against the real backend
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
