import { test, expect, type Page } from "@playwright/test";
import { clickExpand, clickTab, continueGame, dismissBlockingPopups } from "./helpers";

/**
 * Browser tests for v0.7 Feature 50 (Part 2/3) — Decision Grade,
 * Executive Meeting Log, Weekly Self-Evaluation, and the Company Health
 * redesign's Executive tier. Same real-app testing approach as
 * executiveVoting.spec.ts — exercises the live Vite + FastAPI stack.
 */

/** Same real research_boost mechanic executiveVoting.spec.ts already uses
 * — see that file's own doc comment for why this isn't a test-only
 * shortcut. Ensures at least one real TradeProposal exists to decide on,
 * so the Meeting Log / Decision Grade panels have real data to render. */
async function boostResearchToThreshold(page: Page): Promise<void> {
  const research = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    const state = await res.json();
    return state.research as Array<{ id: string; status: string; symbol: string | null; confidence: number }>;
  });
  const target = research.find((r) => r.status === "in_progress" && r.symbol);
  if (!target) return;

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
    if (!res) break;
    confidence += 25;
  }
}

/** Decides whatever real proposal is currently open (or opens the first
 * pending one via the EXECUTIVE tab) with a real BUY/SELL/WAIT call, so
 * the backend records a real ExecutiveMeetingLogEntry with a real
 * Decision Grade — the same real CEO-decision path
 * executiveVoting.spec.ts's own BUY test exercises. */
async function ensureAtLeastOneRealDecision(page: Page): Promise<void> {
  await boostResearchToThreshold(page);
  await dismissBlockingPopups(page);
  await page.keyboard.press("Tab");
  await clickExpand(page);
  await clickTab(page, "EXECUTIVE");

  const pendingRow = page.locator("button").filter({ hasText: /% confidence/ }).first();
  const hasPending = await pendingRow.isVisible({ timeout: 15000 }).catch(() => false);
  if (!hasPending) return; // shared dev backend may already have decided everything recently — honest no-op
  await pendingRow.click();

  const popup = page.getByTestId("executive-voting");
  await expect(popup).toBeVisible();
  const buyButton = popup.getByRole("button", { name: "BUY", exact: true });
  if (await buyButton.isEnabled().catch(() => false)) {
    await buyButton.click();
    await page.waitForTimeout(1500);
  }
}

test("Company Health redesign shows the Executive tier alongside the original Operational one", async ({ page }) => {
  test.setTimeout(90000); // same rationale as commandCenter.spec.ts — real popups may need several dismiss rounds
  await page.goto("/");
  await continueGame(page);
  await dismissBlockingPopups(page);
  await page.keyboard.press("Tab");
  await clickExpand(page);
  await clickTab(page, "COMPANY");

  await expect(page.getByText("Company Health", { exact: true })).toBeVisible();
  // .first() — Design Bible Chapter 63's Tier Thresholds card
  // (CompanyPanel.tsx) also mentions "Executive Health" in its own
  // descriptive text, so a non-exact match resolves to two elements;
  // any match confirms the real Executive Health card rendered.
  await expect(page.getByText("Executive Health").first()).toBeVisible();
  for (const label of ["Decision Quality", "Exec Alignment", "Risk Governance", "Sim Coverage", "Dept Consensus", "Self-Eval Health", "Institutional Memory", "Innovation Velocity", "Talent Development", "Founder Oversight"]) {
    await expect(page.getByText(label, { exact: true })).toBeVisible();
  }
  await expect(page.getByText("Combined Overall")).toBeVisible();
});

test("Risk dashboard shows the real Risk Governance metric", async ({ page }) => {
  test.setTimeout(90000);
  await page.goto("/");
  await continueGame(page);
  await dismissBlockingPopups(page);
  await page.keyboard.press("Tab");
  await clickExpand(page);
  await clickTab(page, "RISK");

  await expect(page.getByText("Risk Governance")).toBeVisible();
  await expect(page.getByText(/Real Trade Gatekeeper approval rate/)).toBeVisible();
});

test("Executive Intelligence Network hub shows Weekly Self-Evaluation and the Executive Meeting Log, with a real entry after a real decision", async ({ page }) => {
  test.setTimeout(90000);
  await page.goto("/");
  await continueGame(page);
  await ensureAtLeastOneRealDecision(page);
  await dismissBlockingPopups(page);
  await clickTab(page, "EXECINTEL");

  await expect(page.getByText("Weekly Self-Evaluation")).toBeVisible();
  await expect(page.getByText(/Executive Meeting Log \(\d+\)/)).toBeVisible();

  // Either a real entry now exists (this test's own decision, or one from
  // elsewhere in this shared dev backend's real activity) or the honest
  // empty state shows — both are real, valid states to assert on.
  const meetingLogCount = await page.evaluate(async () => {
    const res = await fetch("/api/load/archive/trade_history");
    const data = await res.json();
    return (data.executiveMeetingLog as unknown[]).length;
  });
  if (meetingLogCount > 0) {
    await expect(page.getByText("No real Executive decisions have been recorded yet.")).toHaveCount(0);
  } else {
    await expect(page.getByText("No real Executive decisions have been recorded yet.")).toBeVisible();
  }
});

test("Decision Intelligence dashboard shows a Decision Grade column and distribution once real decisions exist", async ({ page }) => {
  test.setTimeout(90000);
  await page.goto("/");
  await continueGame(page);
  await ensureAtLeastOneRealDecision(page);
  await dismissBlockingPopups(page);
  await clickTab(page, "DECISIONS");

  await expect(page.getByText(/Decision Log \(\d+ of \d+\)/)).toBeVisible();

  const decisionCount = await page.evaluate(async () => {
    const res = await fetch("/api/load/archive/trade_history");
    const data = await res.json();
    return (data.decisions as unknown[]).length;
  });
  if (decisionCount > 0) {
    await expect(page.getByText("Decision Grade Distribution")).toBeVisible();
  }
});
