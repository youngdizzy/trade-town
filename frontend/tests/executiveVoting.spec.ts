import { test, expect, type Page } from "@playwright/test";

/**
 * Browser tests for v0.6.3 Feature 12 — Executive Voting (CEO Approval).
 * Like commandCenter.spec.ts, these exercise the real running app rather
 * than a mocked harness.
 *
 * The popup is deliberately gated to never render during MainMenuScene,
 * and to never auto-open for a proposal that already existed before a
 * given page's own first load (see ExecutiveVoting.tsx's currentScene
 * guard and NexusManager's `hydrated` flag — the WebSocket connects at
 * app boot, independent of the title screen, so without these guards a
 * pre-existing proposal would pop the modal up over the title screen
 * itself and swallow the "Continue" click). So every test here goes
 * through the real title-screen flow first, and opens the popup
 * explicitly through the EXECUTIVE panel's pending-proposal list rather
 * than waiting on an auto-popup that correctly won't fire for backlog.
 *
 * A real research item only crosses the trade-confidence threshold
 * (and so only generates a real TradeProposal) after many sim ticks —
 * on a freshly booted backend that can take longer than any reasonable
 * test timeout, even though it always happens eventually in real
 * gameplay. boostResearchToThreshold() speeds that up via the real
 * research_boost energy action (see its own doc comment below) instead
 * of waiting on organic completion.
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

/**
 * Pushes a real in-progress research item over the trade-confidence
 * threshold via the real research_boost action (POST /api/energy/spend
 * — the same mechanic the "Agent Energy widget" test in
 * commandCenter.spec.ts already exercises), so the next real tick
 * completes it and generates a real TradeProposal. A cold-started
 * backend can otherwise take many minutes of real sim ticks before any
 * research item organically crosses the threshold on its own — too
 * long for a test to wait on — but research_boost is real gameplay
 * (it's literally "spend energy to speed up research"), not a
 * test-only shortcut.
 */
async function boostResearchToThreshold(page: Page): Promise<void> {
  const research = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    const state = await res.json();
    return state.research as Array<{ id: string; status: string; symbol: string | null; confidence: number }>;
  });
  const target = research.find((r) => r.status === "in_progress" && r.symbol);
  if (!target) throw new Error("boostResearchToThreshold: no in-progress research item with a symbol found");

  let confidence = target.confidence;
  for (let i = 0; i < 6 && confidence < 90; i++) {
    const res = await page.evaluate(async (researchId) => {
      const r = await fetch("/api/energy/spend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "research_boost", researchId }),
      });
      return r.ok;
    }, target.id);
    if (!res) break; // out of energy — the item may already be close enough
    confidence += 25;
  }
}

test("Executive Voting popup shows real analyst votes and a BUY submits a real CEO decision", async ({ page }) => {
  await page.goto("/");
  await continueGame(page);
  await boostResearchToThreshold(page);

  // The popup only ever auto-opens for a proposal that appears WHILE this
  // page is already live (see ExecutiveVoting.tsx's hydrated guard) —
  // a proposal that already existed at this page's own first load (very
  // likely true here, since other tests in this file/suite have been
  // ticking the shared backend for a while) correctly does NOT auto-pop
  // over whatever the player was already doing. So open it the same way
  // a real player reviewing their queue would: through the EXECUTIVE
  // panel's pending-proposal list, not by waiting on an auto-popup.
  await page.keyboard.press("Tab");
  await page.getByText("EXPAND — FULL COMMAND CENTER").click();
  await page.getByRole("button", { name: "EXECUTIVE", exact: true }).click();

  const pendingRow = page.locator("button").filter({ hasText: /% confidence/ }).first();
  await expect(pendingRow).toBeVisible({ timeout: 20000 });
  await pendingRow.click();

  const popup = page.getByTestId("executive-voting");
  await expect(popup).toBeVisible();
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
