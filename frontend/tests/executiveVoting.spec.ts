import { test, expect, type Page } from "@playwright/test";

/**
 * Browser tests for v0.6.3 Feature 12 — Executive Voting (CEO Approval).
 * Like commandCenter.spec.ts, these exercise the real running app rather
 * than a mocked harness. They assume the backend already has at least one
 * pending TradeProposal by the time the page loads (true for any fresh
 * dev-loop run once research has crossed the trade-confidence threshold),
 * since the popup only ever renders real, server-generated proposals —
 * there is no test-only seam to fabricate one client-side.
 *
 * The popup is deliberately gated to never render during MainMenuScene
 * (see ExecutiveVoting.tsx's currentScene guard — the WebSocket connects
 * at app boot, independent of the title screen, so without this guard a
 * pre-existing proposal would pop the modal up over the title screen
 * itself and swallow the "Continue" click). So every test here goes
 * through the real title-screen flow first, the same way a player would.
 */
async function continueGame(page: Page): Promise<void> {
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
  throw new Error("continueGame: never reached an in-game scene after 5 click attempts");
}

test("Executive Voting popup shows real analyst votes and a BUY submits a real CEO decision", async ({ page }) => {
  await page.goto("/");
  await continueGame(page);

  const popup = page.getByTestId("executive-voting");
  await expect(popup).toBeVisible({ timeout: 15000 });
  await expect(popup.getByText("EXECUTIVE VOTING")).toBeVisible();

  // Expanding an analyst vote reveals its real reasoning + evidence.
  const firstVoteCard = popup.locator("button").filter({ hasText: "Technical Analyst" }).first();
  await firstVoteCard.click();
  await expect(popup.getByText(/Trend:/)).toBeVisible();

  // Review Analysis reveals the Trade Quality Score + Pre-Trade Checklist.
  await popup.getByText("REVIEW ANALYSIS").click();
  await expect(popup.getByText("Trade Quality Score")).toBeVisible();
  await expect(popup.getByText("Pre-Trade Checklist")).toBeVisible();

  const symbol = await popup.locator("span.font-cmdmono").first().innerText();

  await popup.getByRole("button", { name: "BUY", exact: true }).click();
  await expect(popup.getByText("EXECUTIVE VOTING")).not.toContainText(symbol, { timeout: 10000 });
});

test("Executive panel in the Command Center lists pending proposals and CEO track record", async ({ page }) => {
  await page.goto("/");
  await continueGame(page);

  // Clear whatever popups auto-opened (a trade outcome popup sits above
  // Executive Voting, so it must be dismissed first if both are queued).
  for (let i = 0; i < 5; i++) {
    const tradePopup = page.getByTestId("trade-outcome-popup");
    if (await tradePopup.isVisible().catch(() => false)) {
      await tradePopup.getByText("Continue").click();
      await page.waitForTimeout(300);
      continue;
    }
    const votingPopup = page.getByTestId("executive-voting");
    if (await votingPopup.isVisible().catch(() => false)) {
      await votingPopup.getByText("Decide later").click();
      await page.waitForTimeout(300);
      continue;
    }
    break;
  }

  await page.keyboard.press("Tab");
  await page.getByText("EXPAND — FULL COMMAND CENTER").click();
  await page.getByRole("button", { name: "EXECUTIVE" }).click();

  await expect(page.getByText("CEO Track Record")).toBeVisible();
  await expect(page.getByText(/Pending Proposals/)).toBeVisible();
});
