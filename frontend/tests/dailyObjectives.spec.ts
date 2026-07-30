import { test, expect, type Page } from "@playwright/test";

/**
 * v0.7 Feature 49 — Professional Day Trading Program's Daily Trading
 * Objectives. Same real-app testing approach as sandbox.spec.ts/
 * constitution.spec.ts — exercises the live Vite + FastAPI stack, no
 * mocking.
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

test("the backend state carries real Daily Trading Objectives fields", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(state.riskLimits.dailyProfitTargetPct).toBeGreaterThan(0);
  expect(state.riskLimits.maxTradesPerDay).toBeGreaterThan(0);
  expect(state.riskLimits.maxDailyLossPct).toBeGreaterThan(0);
  expect(state.dailyObjectiveStatus).toBeTruthy();
  expect(typeof state.dailyObjectiveStatus.tradesToday).toBe("number");
  expect(typeof state.dailyObjectiveStatus.tradingHalted).toBe("boolean");
});

test("the RISK tab shows Daily Trading Objectives and a real CEO update round-trips through POST /api/risk-limits", async ({ page }) => {
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
  await clickTab(page, "RISK");

  await expect(page.getByText(/Daily Trading Objectives/)).toBeVisible();
  await expect(page.getByText("Trades today")).toBeVisible();

  const uniqueTarget = "7.5";
  const targetInput = page.getByLabel("Daily profit target (%)");
  await targetInput.fill(uniqueTarget);

  await Promise.all([page.waitForResponse((res) => res.url().includes("/api/risk-limits") && res.ok()), page.getByRole("button", { name: "Save Objectives" }).click()]);

  await expect(page.getByText("Daily profit target", { exact: true }).locator("xpath=following-sibling::span")).toContainText("7.5%");

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
