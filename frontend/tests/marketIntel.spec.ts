import { test, expect, type Page } from "@playwright/test";

/**
 * v0.7 Feature 51 — Market Intelligence Department. Same real-app
 * testing approach as execIntel.spec.ts/blackBox.spec.ts — exercises the
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

test("marketIntelligence is present in the real backend state", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(state.marketIntelligence).toBeTruthy();
  expect(typeof state.marketIntelligence.regime).toBe("string");
  expect(typeof state.marketIntelligence.regimeLabel).toBe("string");
  expect(state.marketIntelligence.quality).toBeTruthy();
  expect(Array.isArray(state.marketIntelligence.liquidity)).toBe(true);
  expect(Array.isArray(state.marketIntelligence.structure)).toBe(true);
  expect(Array.isArray(state.marketIntelligenceReports)).toBe(true);
  expect(Array.isArray(state.marketIntelligenceLearning)).toBe(true);
});

test("the Market Intelligence tab opens from the Command Center and shows the real live read", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (e) => consoleErrors.push(String(e)));

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
  await clickTab(page, "MARKETINTEL");

  await expect(page.getByText(/^MARKET REGIME —/)).toBeVisible();
  await expect(page.getByText("Session", { exact: true })).toBeVisible();
  await expect(page.getByText("Volatility", { exact: true })).toBeVisible();
  await expect(page.getByText("Momentum", { exact: true })).toBeVisible();
  await expect(page.getByText("Institutional Activity", { exact: true })).toBeVisible();
  await expect(page.getByText("News Risk", { exact: true })).toBeVisible();
  await expect(page.getByText(/Liquidity & Structure — By Symbol/)).toBeVisible();

  // The Executive Market Brief and Learning Loop are once-daily real
  // history — either real cards or the honest empty state must render,
  // never a blank/broken panel, regardless of how far into the current
  // in-game day this dev backend happens to be.
  await expect(page.getByText(/Executive Market Brief/)).toBeVisible();
  await expect(
    page.getByText(/No Executive Market Brief has been generated yet/).or(page.getByText(/One real snapshot per in-game evening/)),
  ).toBeVisible();
  await expect(page.getByText("Learning Loop", { exact: true })).toBeVisible();
  await expect(
    page.getByText(/No prior brief has been graded against a real outcome yet/).or(page.getByText(/predicted/)),
  ).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon") && !e.includes("Failed to process file"));
  expect(relevantErrors).toEqual([]);
});
