import { test, expect, type Page } from "@playwright/test";

/**
 * v0.7 Feature 45 — the Research Sandbox. Same real-app testing approach
 * as talent.spec.ts/execIntel.spec.ts — exercises the live Vite +
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

test("strategies carry real stage/stageHistory/allocatedCapital in the backend state", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(Array.isArray(state.strategies)).toBe(true);
  expect(state.strategies.length).toBeGreaterThan(0);
  for (const strategy of state.strategies) {
    expect(strategy.stage).toBeTruthy();
    expect(Array.isArray(strategy.stageHistory)).toBe(true);
    expect(typeof strategy.allocatedCapital).toBe("number");
  }
  expect(Array.isArray(state.strategyReports)).toBe(true);
  expect(Array.isArray(state.strategyReviews)).toBe(true);
});

test("the Research Sandbox tab opens from the Command Center, shows the pipeline, and queues a real scenario backtest", async ({ page }) => {
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
  await clickTab(page, "SANDBOX");

  await expect(page.getByText(/no strategy skips a stage/)).toBeVisible();
  await expect(page.getByText("Testing Environments — queue a real backtest run", { exact: true })).toBeVisible();
  await expect(page.getByText("Performance Metrics — real per-run history", { exact: true })).toBeVisible();
  await expect(page.getByText("Approval Process — advance the pipeline", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Run Backtest" }).click();
  await expect(page.getByText(/queued|running/).first()).toBeVisible({ timeout: 10_000 });

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
