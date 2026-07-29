import { test, expect, type Page } from "@playwright/test";

/**
 * v0.7 Feature 43 — the Executive Intelligence Dashboard. Same real-app
 * testing approach as replay.spec.ts/blackBox.spec.ts — exercises the
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

test("companyDna is present in the real backend state", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(state.companyDna).toBeTruthy();
  expect(Array.isArray(state.companyDna.traits)).toBe(true);
  expect(state.companyDna.traits.length).toBe(5);
  expect(state.companyHealth.teamChemistry).not.toBeUndefined();
});

test("the Executive Intelligence Dashboard opens from the Command Center and shows Company DNA, Executive Priorities, and Department Health", async ({ page }) => {
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
  await clickTab(page, "EXECINTEL");

  await expect(page.getByText("Company DNA", { exact: true })).toBeVisible();
  await expect(page.getByText("Risk Appetite", { exact: true })).toBeVisible();
  await expect(page.getByText("Patience", { exact: true })).toBeVisible();
  await expect(page.getByText("Contrarian Tendency", { exact: true })).toBeVisible();
  await expect(page.getByText("Research Rigor", { exact: true })).toBeVisible();
  await expect(page.getByText("Collaboration Style", { exact: true })).toBeVisible();

  await expect(page.getByText(/Executive Priorities/)).toBeVisible();

  await expect(page.getByText("Department Health", { exact: true })).toBeVisible();
  await expect(page.getByText("Academy", { exact: true })).toBeVisible();
  await expect(page.getByText("Research", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Trading", { exact: true })).toBeVisible();
  await expect(page.getByText("Innovation", { exact: true })).toBeVisible();
  await expect(page.getByText("Founders", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/Brain Room.*is not shown here/)).toBeVisible();

  // Company Health's COMPANY tab should now show Team Chemistry too.
  await clickTab(page, "COMPANY");
  await expect(page.getByText("Team Chemistry", { exact: true })).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
