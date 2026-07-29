import { test, expect, type Page } from "@playwright/test";

/**
 * v0.7 Feature 46 — the Company Constitution. Same real-app testing
 * approach as sandbox.spec.ts/talent.spec.ts — exercises the live Vite
 * + FastAPI stack, no mocking.
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

test("the Constitution's 8 real Articles are present in the backend state", async ({ page }) => {
  await page.goto("/");
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  expect(state.constitution).toBeTruthy();
  expect(state.constitution.articles.map((a: { id: string }) => a.id)).toEqual(["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]);
  expect(state.constitution.articles[0].text).toBe("Protect capital first.");
  expect(Array.isArray(state.constitution.citations)).toBe(true);
  expect(Array.isArray(state.constitution.amendments)).toBe(true);
});

test("the Constitution tab opens from the Command Center, shows the Articles and Live Enforcement, and a proposed amendment runs the real pipeline", async ({ page }) => {
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
  await clickTab(page, "CONSTITUTION");

  await expect(page.getByText("The Articles — permanent company law", { exact: true })).toBeVisible();
  await expect(page.getByText("Protect capital first.", { exact: true })).toBeVisible();
  await expect(page.getByText("Live Enforcement", { exact: true })).toBeVisible();
  await expect(page.getByText("Propose an Amendment", { exact: true })).toBeVisible();

  // A unique title per run — the backend rejects a second pending
  // amendment with a title that's already pending, and this dev
  // backend's state persists across repeated test runs.
  const amendmentTitle = `Test Amendment ${Date.now()}`;
  await page.getByPlaceholder("Article title").fill(amendmentTitle);
  await page.getByPlaceholder("Article text").fill("Employees must double-check every real number before citing it.");
  await page.getByRole("button", { name: "Propose", exact: true }).click();
  await expect(page.getByText(amendmentTitle, { exact: true })).toBeVisible();

  const amendmentCard = page.getByTestId("amendment-card").filter({ hasText: amendmentTitle });
  await amendmentCard.getByRole("button", { name: "Send to Founders, Coach & Employees" }).click();
  await expect(page.getByText(/Employee vote \(advisory\)/)).toBeVisible();
  await expect(amendmentCard.getByRole("button", { name: "Ratify" })).toBeVisible();

  const relevantErrors = consoleErrors.filter((e) => !e.includes("favicon"));
  expect(relevantErrors).toEqual([]);
});
