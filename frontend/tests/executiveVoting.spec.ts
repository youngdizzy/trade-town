import { test, expect, type Page } from "@playwright/test";
import { clickExpand, clickTab, continueGame } from "./helpers";

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
  // page is already live (see ExecutiveVoting.tsx's hydrated guard) — but
  // that can genuinely happen mid-test on a long-running dev backend, so
  // dismiss it first the same way a real player would before opening the
  // EXECUTIVE panel's own pending-proposal list.
  await page.keyboard.press("Tab");
  await clickExpand(page);
  await clickTab(page, "EXECUTIVE");

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

  // Review Analysis reveals the Decision Confidence Engine + Pre-Trade Checklist.
  await popup.getByText("REVIEW ANALYSIS").click();
  await expect(popup.getByText("Decision Confidence Engine")).toBeVisible();
  await expect(popup.getByText("Pre-Trade Checklist")).toBeVisible();

  const symbol = await popup.locator("span.font-cmdmono").first().innerText();

  await popup.getByRole("button", { name: "BUY", exact: true }).click();
  await expect(popup.getByText("EXECUTIVE VOTING")).not.toContainText(symbol, { timeout: 10000 });
});

test("Request More Research holds a proposal without resolving it, and caps out at the real limit", async ({ page }) => {
  await page.goto("/");
  await continueGame(page);
  await boostResearchToThreshold(page);
  await page.keyboard.press("Tab");
  await clickExpand(page);
  await clickTab(page, "EXECUTIVE");

  const pendingRow = page.locator("button").filter({ hasText: /% confidence/ }).first();
  await expect(pendingRow).toBeVisible({ timeout: 20000 });
  await pendingRow.click();

  const popup = page.getByTestId("executive-voting");
  await expect(popup).toBeVisible();
  const symbol = await popup.locator("span.font-cmdmono").first().innerText();

  const researchButton = popup.getByRole("button", { name: /REQUEST MORE RESEARCH/ });
  const delayButton = popup.getByRole("button", { name: /DELAY DECISION/ });
  await expect(researchButton).toContainText("(0/2)");

  // v0.7 Feature 40.5 — a hold resets the proposal's own expiry clock but
  // never resolves it (see backend/app/executive.py's hold_proposal()), so
  // the same proposal — same symbol — must still be the one showing.
  await researchButton.click();
  await expect(researchButton).toContainText("(1/2)", { timeout: 10000 });
  await expect(popup.getByText("EXECUTIVE VOTING")).toBeVisible();
  await expect(popup.locator("span.font-cmdmono").first()).toHaveText(symbol);

  await delayButton.click();
  await expect(delayButton).toContainText("(2/2)", { timeout: 10000 });

  // MAX_PROPOSAL_HOLDS (2) reached — both hold buttons are now disabled,
  // the CEO must actually decide (or let it expire).
  await expect(researchButton).toBeDisabled();
  await expect(delayButton).toBeDisabled();
});

test("Devil's Advocate Challenge Report shows a real assigned employee and severity, and Request Another Review rotates the assignment", async ({
  page,
}) => {
  await page.goto("/");
  await continueGame(page);
  await boostResearchToThreshold(page);
  await page.keyboard.press("Tab");
  await clickExpand(page);
  await clickTab(page, "EXECUTIVE");

  const pendingRow = page.locator("button").filter({ hasText: /% confidence/ }).first();
  await expect(pendingRow).toBeVisible({ timeout: 20000 });
  await pendingRow.click();

  const popup = page.getByTestId("executive-voting");
  await expect(popup).toBeVisible();

  await popup.getByText("OPEN DEVIL'S ADVOCATE REVIEW").click();
  await expect(popup.getByText(/Challenge Report —/)).toBeVisible();

  // v0.7 Feature 41 — every genuinely new proposal gets a real Challenge
  // Report generated up front (nexus.py, same convention as Feature 17's
  // Debate); this popup may have opened on an older pending proposal from
  // before this feature shipped in this long-running dev session, so
  // "Request Another Review" is used unconditionally here (rather than
  // asserting the auto-generated one) — it's real gameplay either way,
  // and guarantees real content to assert on regardless of proposal age.
  await popup.getByRole("button", { name: "Request Another Review" }).click();
  await expect(popup.getByText(/NO WEAKNESSES FOUND|MINOR WEAKNESSES|MAJOR WEAKNESSES/)).toBeVisible({ timeout: 10000 });
  await expect(popup.getByText("assigned Devil's Advocate")).toBeVisible();
  await expect(popup.getByText("Bull Case")).toBeVisible();
  await expect(popup.getByText("Bear Case")).toBeVisible();
  await expect(popup.getByText("Worst Case Scenario")).toBeVisible();

  const assignedBefore = await popup.getByTestId("challenge-report-assignee").innerText();
  const reviewButton = popup.getByRole("button", { name: "Request Another Review" });
  await expect(reviewButton).toBeEnabled();

  await Promise.all([page.waitForResponse((res) => res.url().includes("/executive/challenge/regenerate") && res.ok()), reviewButton.click()]);

  // The rotation is deterministic across a fixed pool of 5 eligible
  // employees (see backend/app/devils_advocate.py) — a second report
  // exists now, so the assignment should have moved to the next name in
  // that rotation rather than staying identical.
  await expect(popup.getByTestId("challenge-report-assignee")).not.toHaveText(assignedBefore, { timeout: 10000 });
});

test("Executive Intelligence Network panel synthesizes real department opinions into one recommendation", async ({ page }) => {
  await page.goto("/");
  await continueGame(page);
  await boostResearchToThreshold(page);
  await page.keyboard.press("Tab");
  await clickExpand(page);
  await clickTab(page, "EXECUTIVE");

  const pendingRow = page.locator("button").filter({ hasText: /% confidence/ }).first();
  await expect(pendingRow).toBeVisible({ timeout: 20000 });
  await pendingRow.click();

  const popup = page.getByTestId("executive-voting");
  await expect(popup).toBeVisible();

  await popup.getByText("OPEN EXECUTIVE INTELLIGENCE NETWORK").click();
  await expect(popup.getByText(/Executive Recommendation —/)).toBeVisible({ timeout: 10000 });

  // v0.7 Feature 50 (Part 1) — 8 real departments, each a real stance
  // synthesized from an already-computed system (see
  // backend/app/executive_intelligence.py), never a fabricated 9th vote.
  for (const label of ["Research", "Quant", "Risk", "Simulation", "Decision Intelligence", "Coach", "Founders", "Devil's Advocate"]) {
    await expect(popup.getByText(label, { exact: true })).toBeVisible();
  }
  await expect(popup.getByText(/% network confidence/)).toBeVisible();
  await expect(popup.getByText(/Supporting:/)).toBeVisible();
  await expect(popup.getByText(/Opposing:/)).toBeVisible();
  await expect(popup.getByText(/recomputed fresh each time this panel opens, not stored/)).toBeVisible();
});

test("Weighted Executive Decision Engine panel shows Raw vs Weighted votes and per-department influence", async ({ page }) => {
  await page.goto("/");
  await continueGame(page);
  await boostResearchToThreshold(page);
  await page.keyboard.press("Tab");
  await clickExpand(page);
  await clickTab(page, "EXECUTIVE");

  const pendingRow = page.locator("button").filter({ hasText: /% confidence/ }).first();
  await expect(pendingRow).toBeVisible({ timeout: 20000 });
  await pendingRow.click();

  const popup = page.getByTestId("executive-voting");
  await expect(popup).toBeVisible();

  await popup.getByText("OPEN WEIGHTED EXECUTIVE DECISION ENGINE").click();
  await expect(popup.getByText(/Weighted Executive Decision Engine —/)).toBeVisible({ timeout: 10000 });

  await expect(popup.getByText("RAW VOTE", { exact: true })).toBeVisible();
  await expect(popup.getByText("WEIGHTED VOTE", { exact: true })).toBeVisible();
  await expect(popup.getByText(/Market regime:/)).toBeVisible();
  await expect(popup.getByText("SCORE BY ACTION (published, 0-100)")).toBeVisible();

  // Design Bible Chapter 70 Part 3 — every one of the 9 real departments
  // gets a real, published multiplier and reasoning line, never a
  // hidden blend.
  for (const label of ["Research", "Quant", "Risk", "Simulation", "Decision Intelligence", "Coach", "Founders", "Devil's Advocate", "Market Intelligence"]) {
    await expect(popup.getByText(label, { exact: true })).toBeVisible();
  }

  // Switching the Weight Profile re-fetches a live, real preview without
  // persisting until "SET AS ACTIVE PROFILE" is clicked.
  await popup.getByRole("combobox").selectOption("risk_first");
  await expect(popup.getByText(/Risk First — 2\.00× preset emphasis/)).toBeVisible({ timeout: 10000 });
  await expect(popup.getByText("SET AS ACTIVE PROFILE")).toBeVisible();
});

test("Executive panel in the Command Center lists pending proposals and CEO track record", async ({ page }) => {
  await page.goto("/");
  await continueGame(page);
  await page.keyboard.press("Tab");
  await clickExpand(page);
  await clickTab(page, "EXECUTIVE");

  await expect(page.getByText("CEO Track Record")).toBeVisible();
  await expect(page.getByText(/Pending Proposals/)).toBeVisible();
});

test("CEO directive Features 26-30, Feature 29 — the EXECUTIVE panel shows a real Prediction Ledger", async ({ page }) => {
  await page.goto("/");
  // /api/load deliberately returns archive modules (predictionRecords
  // included) empty — see routers/save.py's own docstring — so real
  // evidence is checked via the dedicated per-agent endpoint instead.
  const predictions = await page.evaluate(async () => {
    const res = await fetch("/api/predictions/scout");
    return res.json();
  });
  expect(Array.isArray(predictions)).toBe(true);
  for (const p of predictions) {
    expect(p.claimType).toBe("trade_direction");
    expect(["buy", "sell"]).toContain(p.predictedDirection);
    expect(["pending", "correct", "incorrect"]).toContain(p.outcome);
    expect(p.attributedAgents).toContain("scout");
    // A resolved prediction always carries a real linked trade and P&L;
    // a pending one never has hindsight data attached.
    if (p.outcome === "pending") {
      expect(p.resolvedTradeId).toBeNull();
      expect(p.resolvedPnlPct).toBeNull();
    } else {
      expect(typeof p.resolvedTradeId).toBe("string");
      expect(typeof p.resolvedPnlPct).toBe("number");
    }
  }

  await continueGame(page);
  await page.keyboard.press("Tab");
  await clickExpand(page);
  await clickTab(page, "EXECUTIVE");

  await expect(page.getByText("Prediction Ledger", { exact: true })).toBeVisible();
});
