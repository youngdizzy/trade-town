import { test, expect } from "@playwright/test";

/**
 * Browser tests for v0.6.3 Feature 12 — Executive Voting (CEO Approval).
 * Like commandCenter.spec.ts, these exercise the real running app rather
 * than a mocked harness. They assume the backend already has at least one
 * pending TradeProposal by the time the page loads (true for any fresh
 * dev-loop run once research has crossed the trade-confidence threshold),
 * since the popup only ever renders real, server-generated proposals —
 * there is no test-only seam to fabricate one client-side.
 */

test("Executive Voting popup shows real analyst votes and a BUY submits a real CEO decision", async ({ page }) => {
  await page.goto("/");

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
