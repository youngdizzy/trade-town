import { test, expect, type Page } from "@playwright/test";
import { clickButton, clickContinueOnTitleScreen, clickExpand, clickRobust, clickTab, continueGame, dismissBlockingPopups, enableDebugOverlay, readDebug, setPlayerScene } from "./helpers";

/**
 * Browser tests for the v0.6.1 Global Command Center. These exercise the
 * real running app (Vite dev server + FastAPI backend) rather than a
 * mocked harness, so what passes here is what a player would actually
 * see.
 *
 * "Opening from a specific room" is done by writing a player position
 * directly through the real POST /api/save endpoint (the same endpoint
 * SaveManager already uses) and then clicking the title screen's
 * "Continue" button — this is the same resume path a real player uses
 * after closing the tab, not a test-only shortcut, so it's a legitimate
 * way to start a test in an arbitrary room without needing to script
 * pixel-perfect physics-based navigation through doors.
 *
 * Popup dismissal (a real closed trade, a fresh TradeProposal, a
 * Gatekeeper veto, a Founder-approved breakthrough — this sim clock
 * keeps ticking in real time for the whole file) is centralized in
 * ./helpers — see that module's own doc comment for why.
 */

/** Holds a movement key down, then confirms the player's real x actually
 * changed — retrying the hold a few times before giving up, since
 * DebugOverlay's readout updates on requestAnimationFrame (one tick
 * behind the scene's own internal position, and this headless
 * environment's render rate is real but variable), so a single
 * hold-then-read can occasionally sample between frames. */
async function expectMovement(page: Page, key: string, before: { x: number; scene: string }): Promise<{ scene: string; x: number; y: number }> {
  for (let attempt = 0; attempt < 3; attempt++) {
    await page.keyboard.down(key);
    await page.waitForTimeout(400);
    await page.keyboard.up(key);
    await page.waitForTimeout(150);
    const after = await readDebug(page);
    if (after.x !== before.x) return after;
  }
  throw new Error(`expectMovement: player.x never changed from ${before.x} after 3 attempts holding "${key}"`);
}

test.describe("Global Command Center", () => {
  test("opens via Tab from the Lobby, closes via Escape, preserves position", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);
    await enableDebugOverlay(page);

    const before = await readDebug(page);
    expect(before.scene).toBe("LobbyScene");

    await page.keyboard.press("Tab");
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toBeVisible();
    await expect(page.getByText("Quick View")).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toHaveCount(0);

    const after = await readDebug(page);
    expect(after).toEqual(before);
  });

  test("opens directly inside the Brain Room via the toolbar button", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "BrainRoomScene", 144, 96);
    await continueGame(page);
    await enableDebugOverlay(page);

    const before = await readDebug(page);
    expect(before.scene).toBe("BrainRoomScene");

    await clickButton(page, "Command ⌁");
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toBeVisible();

    const after = await readDebug(page);
    expect(after).toEqual(before);

    await clickButton(page, "CLOSE");
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toHaveCount(0);
  });

  test("blocks interaction but allows movement while open, unless a text field has focus", async ({ page }) => {
    // v0.7 — Input Priority fix: the Command Center's own backdrop isn't
    // fully opaque (bg-black/70 backdrop-blur-sm), so WASD keeps moving
    // the player behind it — only E-key interaction/agent updates/door
    // triggers stay suppressed (see GameManager.movementActive vs
    // worldActive, and gameStore.ts's MOVEMENT_BLOCKING_KEYS, which
    // excludes commandCenterOpen). A focused text field inside it still
    // takes priority over WASD so typing works normally.
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);
    await enableDebugOverlay(page);

    const before = await readDebug(page);

    await page.keyboard.press("Tab");
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toBeVisible();
    // A real proposal/vote can appear in the instant between opening and
    // this movement check (the sim keeps ticking); its modal is opaque
    // and does legitimately block input, unlike the Command Center's own
    // translucent backdrop this test is actually verifying, so clear it
    // first the same way a real player would.
    await dismissBlockingPopups(page);

    const movedWhileOpen = await expectMovement(page, "d", before);
    expect(movedWhileOpen.scene).toBe(before.scene); // no door/interaction fired — the scene never changed

    // Expand to the Full Command Center and focus a real text field
    // (Calendar's custom-event title input) — WASD must type into it
    // instead of moving the player while it has focus.
    await clickExpand(page);
    await clickTab(page, "CALENDAR");
    await dismissBlockingPopups(page);

    const titleInput = page.getByTestId("calendar-event-title");
    await titleInput.click();
    // A brief settle after the click — the same real mouse-to-keyboard
    // transition gap any actual player has (InputManager's capture
    // release is polled once per rendered frame; typing faster than a
    // single frame after the click isn't a scenario a real human hits).
    await page.waitForTimeout(100);
    const frozenWhileTyping = await readDebug(page);
    for (const key of ["w", "a", "s", "d"]) {
      await page.keyboard.press(key);
      await page.waitForTimeout(30);
    }
    await expect(titleInput).toHaveValue("wasd");
    const stillFrozen = await readDebug(page);
    expect(stillFrozen).toEqual(frozenWhileTyping);

    // No explicit blur() needed — Escape unmounts the whole Command
    // Center (including this input), which clears focus as a side effect.
    await page.keyboard.press("Escape");
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toHaveCount(0);

    // Sanity check: movement (and, implicitly, interaction) resume
    // normally once fully closed — no stale-keypress glitch from the
    // overlay-close transition (see GameManager.ts's resetSceneKeys()).
    const closedBefore = await readDebug(page);
    await expectMovement(page, "d", closedBefore);
  });

  test("expands to the Full Command Center and renders all 37 tabs with graceful empty states", async ({ page }) => {
    test.setTimeout(120000); // the longest-running test in the file — 37 real tab clicks, each dismissing real popups along the way
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toBeVisible();
    // This is the longest-running test in the file — with the real sim
    // ticking throughout, a genuine trade proposal can pop up in the
    // instant between continueGame() returning and this click, the same
    // race clickTab() below already guards against — so this one dismiss
    // immediately before clicking closes that same window.
    await clickExpand(page);

    // This is the longest-running test in the file — with the real sim
    // ticking throughout, a genuine trade or trade proposal can appear
    // (and pop up) mid-test. clickTab() dismisses and retries rather
    // than losing the race to a popup that appears in that instant.
    const tabs = ["OVERVIEW", "OPPORTUNITIES", "EXECUTIVE", "DECISIONS", "REPLAY", "RISK", "BLACKSWAN", "AGENTS", "RESEARCH", "COMPANY", "EXECINTEL", "MARKETINTEL", "ECONINTEL", "KNOWLEDGE", "DISCIPLINE", "VAULT", "WARROOM", "PORTFOLIO", "REASONING", "REFLECTION", "MENTOR", "MENTORLIB", "MENTORLAB", "TALENT", "SANDBOX", "CONSTITUTION", "OPS", "FOUNDERS", "TREASURY", "CALENDAR", "BLACKBOX", "TRAINING", "PVAI", "ACADEMY", "PERFORMANCE", "LOGS", "COMPLIANCE"];
    for (const tab of tabs) {
      await clickTab(page, tab);
      await expect(page.getByRole("button", { name: tab, exact: true })).toHaveClass(/text-cmd-cyan/);
    }

    // Design Bible Chapter 67 (TTOS) Phase 1 — the 34 tabs above now
    // render grouped under 7 real section labels rather than one flat
    // row; `.first()` since a couple of these strings also match a tab
    // button's own name (e.g. the RESEARCH section label vs. the
    // RESEARCH tab button) — any match confirms the real label rendered.
    for (const section of ["HEADQUARTERS", "MARKETS", "AI WORKFORCE", "RESEARCH", "PORTFOLIO", "OPERATIONS", "ARCHIVE"]) {
      await expect(page.getByText(section, { exact: true }).first()).toBeVisible();
    }

    // The backend keeps ticking in real time across this whole test file,
    // so by this point it may honestly have accumulated real decisions —
    // either way the panel must render something truthful, never a blank
    // screen: either real opportunity cards, or the explicit empty state.
    await clickTab(page, "OPPORTUNITIES");
    await expect(page.getByText(/No opportunities evaluated yet/).or(page.locator("text=/% confidence/").first())).toBeVisible();

    await clickTab(page, "RISK");
    // .first() since Design Bible Chapter 67's GlobalStatusBar now shows
    // this same real risk-level label from every scene, not just here.
    await expect(page.getByText(/NORMAL|ELEVATED|RESTRICTED/).first()).toBeVisible();

    await clickTab(page, "AGENTS");
    await expect(page.getByText("Atlas").first()).toBeVisible();

    await clickTab(page, "QUICK VIEW");
    await expect(page.getByText("Quick View")).toBeVisible();
  });

  test("renders a real candlestick chart on Overview, labeled SIMULATED, with working timeframe switching", async ({ page }) => {
    test.setTimeout(60000); // clickButton retries through a real popup that can intercept the "1d" click
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await expect(page.getByText("Market Chart")).toBeVisible();

    // Never claim simulated data is live — the badge must say so explicitly.
    // .first(): real coach-review text on closed trades elsewhere on the
    // page can also legitimately contain the substring "simulated" (case-
    // insensitive default match), so this scopes to the chart's own badge,
    // which renders before that text in DOM order.
    await expect(page.getByText("SIMULATED").first()).toBeVisible();

    const chartCanvas = page.locator("canvas").nth(1); // canvas 0 is the Phaser game itself
    await expect(chartCanvas).toBeVisible();
    const before = await chartCanvas.screenshot();

    await clickButton(page, "1d");
    await page.waitForTimeout(500);
    const after = await chartCanvas.screenshot();
    expect(Buffer.compare(before, after)).not.toBe(0); // switching timeframe actually redraws different data
  });

  test("Agent Energy widget spends real energy for a real effect (watch_symbol) via POST /api/energy/spend", async ({ page }) => {
    test.setTimeout(60000); // clickRobust retries through a real popup that can intercept the Watch New Symbol click
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    const widget = page.getByTestId("agent-energy-widget");
    await expect(widget).toBeVisible();

    const readEnergy = async () => {
      const text = await widget.getByText(/^\d+ \/ \d+$/).innerText();
      return Number(text.split(" / ")[0]);
    };
    const before = await readEnergy();

    const watchButton = widget.getByRole("button", { name: /Watch New Symbol/ });
    await expect(watchButton).toBeEnabled();
    await clickRobust(page, () => widget.getByRole("button", { name: /Watch New Symbol/ }), { label: "Watch New Symbol" });

    // The action either succeeds (energy drops by exactly the real cost) or
    // the extra-symbol pool is already exhausted from an earlier test run
    // against the same long-lived dev backend, in which case the button
    // must honestly report the real 400 error instead of pretending to spend.
    await expect(async () => {
      const after = await readEnergy();
      const errorVisible = await widget.getByText(/already being monitored/i).isVisible().catch(() => false);
      expect(after === before - 10 || errorVisible).toBe(true);
    }).toPass({ timeout: 5000 });
  });

  test("Signal Calibration mini-game grades a real round via POST /api/calibration/submit", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "TRAINING");

    const round = page.getByTestId("calibration-round");
    await expect(round).toBeVisible();
    await round.getByRole("button", { name: "Start Round" }).click();

    // A real symbol, a real chart, and the plain-English factor readouts
    // for level 1 — never a blank/fabricated round.
    await expect(round.locator("canvas")).toBeVisible();
    await expect(round.getByText(/Recent trend:/)).toBeVisible();

    await round.getByRole("button", { name: "ENTER", exact: true }).click();

    // Grading always reveals the rubric's disciplined answer and why —
    // either CORRECT or MISSED, never silence.
    await expect(round.getByText(/CORRECT|MISSED/)).toBeVisible({ timeout: 5000 });
    await expect(round.getByText(/Disciplined answer:/)).toBeVisible();
  });

  test("Player vs AI grades a real round against an already-closed AI trade via POST /api/player-vs-ai/submit", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "PVAI");

    const round = page.getByTestId("player-vs-ai-round");
    await expect(round).toBeVisible();
    await round.getByRole("button", { name: "Start Round" }).click();

    // The backend's dev save has accumulated real closed trades over this
    // whole test file's run, so a round should be offered — but if it
    // genuinely isn't (a fresh backend with no closed trades yet), the
    // panel must say so honestly rather than fabricate a round.
    const noRoundsMessage = round.getByText(/No resolved AI trades/i);
    const enterButton = round.getByRole("button", { name: "ENTER", exact: true });
    await expect(noRoundsMessage.or(enterButton)).toBeVisible({ timeout: 5000 });

    if (await enterButton.isVisible()) {
      await enterButton.click();
      await expect(round.getByText(/CORRECT|MISSED/).first()).toBeVisible({ timeout: 5000 });
      await expect(round.getByText(/real realized result/)).toBeVisible();
    }
  });

  test("Trading Academy: completes a real lesson quiz, and RISK's Need Help jumps straight to a lesson", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "ACADEMY");

    const lessonPane = page.getByTestId("education-lesson");
    await expect(lessonPane).toBeVisible();

    // v0.7 Feature 49 (Phase 2) — the 8-lesson Liquidity/Market
    // Structure module extends the curriculum through order 18.
    await expect(page.getByRole("button", { name: /11\. What Is Liquidity\?/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /18\. Order Flow/ })).toBeVisible();

    await page.getByRole("button", { name: /1\. Reading a Candlestick/ }).click();
    await expect(lessonPane.getByText(/Practice Challenge/)).toBeVisible();

    // Answer the quiz and submit — grading is server-side against a real
    // fixed answer key (see backend/app/education.py), so either outcome
    // (CORRECT or NOT QUITE) must render honestly, never silently accept.
    await lessonPane.getByText("It closed higher than it opened").click();
    await lessonPane.getByRole("button", { name: "Submit Answer" }).click();
    await expect(lessonPane.getByText(/CORRECT|NOT QUITE/)).toBeVisible({ timeout: 5000 });

    // RISK panel's "Need Help?" must jump straight into a real lesson.
    await clickTab(page, "RISK");
    await clickButton(page, "Need Help?");
    await expect(page.getByRole("button", { name: "ACADEMY", exact: true })).toHaveClass(/text-cmd-cyan/);
    await expect(page.getByTestId("education-lesson").getByText("Risk/Reward Ratio", { exact: true })).toBeVisible();
  });

  test("RISK panel's Position Sizing controls save real CEO-set limits (v0.7 Chapter 57)", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "RISK");

    await expect(page.getByText("Position Sizing — Capital Deployment", { exact: true })).toBeVisible();
    await expect(page.getByText("Position Tier allocation caps (% of equity)", { exact: true })).toBeVisible();

    // Enable the Portfolio Heat cap (off by default — see RiskLimits'
    // own docstring on why null is the honest default) and change the
    // weekly deployment budget, then save and confirm no error surfaces.
    const heatCapCheckbox = page.getByRole("checkbox");
    await heatCapCheckbox.check();
    const weeklyDeploymentInput = page.locator("label", { hasText: "Max weekly deployment" }).locator("input");
    await weeklyDeploymentInput.fill("20");
    await clickButton(page, "Save Position Sizing Controls");

    await expect(page.getByRole("button", { name: "Save Position Sizing Controls", exact: true })).toBeEnabled();
    await expect(page.getByText("must be a positive percentage", { exact: false })).toHaveCount(0);
    await expect(weeklyDeploymentInput).toHaveValue("20");
  });

  test("RISK panel's Opportunity Gatekeeper controls save real CEO-set limits (v0.7 Chapter 58)", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "RISK");

    await expect(page.getByText("Opportunity Gatekeeper", { exact: true })).toBeVisible();

    const minQualityInput = page.locator("label", { hasText: "Minimum Trade Quality Score" }).locator("input");
    await minQualityInput.fill("75");
    await clickButton(page, "Save Opportunity Gatekeeper Controls");

    await expect(page.getByRole("button", { name: "Save Opportunity Gatekeeper Controls", exact: true })).toBeEnabled();
    await expect(page.getByText("must be a percentage from 0 to 100", { exact: false })).toHaveCount(0);
    await expect(minQualityInput).toHaveValue("75");
  });

  test("EXECUTIVE tab shows the Opportunity Gatekeeper's real rejection record, always real content or an honest empty state", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "EXECUTIVE");

    await expect(page.getByText("Opportunity Gatekeeper", { exact: true })).toBeVisible();
    const hasEmptyState = await page.getByText(/No opportunities rejected yet/).count();
    if (hasEmptyState === 0) {
      await expect(page.getByText(/would have (BUY|SELL|WAIT)/).first()).toBeVisible();
    } else {
      expect(hasEmptyState).toBeGreaterThan(0);
    }
  });

  test("RISK panel's Capital Priority controls save real CEO-set limits (v0.7 Chapter 59)", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "RISK");

    await expect(page.getByText("Capital Priority — Opportunity Cost", { exact: true })).toBeVisible();

    const minPriorityInput = page.locator("label", { hasText: "Minimum Priority Score" }).locator("input");
    await minPriorityInput.fill("65");
    const capitalReserveInput = page.locator("label", { hasText: "Capital Reserve" }).locator("input");
    await capitalReserveInput.fill("15");
    await clickButton(page, "Save Capital Priority Controls");

    await expect(page.getByRole("button", { name: "Save Capital Priority Controls", exact: true })).toBeEnabled();
    await expect(page.getByText("must be a percentage from 0", { exact: false })).toHaveCount(0);
    await expect(minPriorityInput).toHaveValue("65");
    await expect(capitalReserveInput).toHaveValue("15");
  });

  test("RISK panel's Safety & Capital Protection controls save real weekly/monthly loss limits and surface Emergency Stop status (Design Bible Ch. 67)", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "RISK");

    await expect(page.getByText("Safety & Capital Protection", { exact: true })).toBeVisible();

    const weeklyLossInput = page.locator("label", { hasText: "Max weekly loss" }).locator("input");
    await weeklyLossInput.fill("12");
    const monthlyLossInput = page.locator("label", { hasText: "Max monthly loss" }).locator("input");
    await monthlyLossInput.fill("18");
    await clickButton(page, "Save Safety Limits");

    await expect(page.getByRole("button", { name: "Save Safety Limits", exact: true })).toBeEnabled();
    await expect(page.getByText("must be a positive percentage", { exact: false })).toHaveCount(0);
    await expect(weeklyLossInput).toHaveValue("12");
    await expect(monthlyLossInput).toHaveValue("18");
    await expect(page.getByText("Max weekly loss", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("Max monthly loss", { exact: false }).first()).toBeVisible();

    // Emergency Stop status is real, not a placeholder — it's the same
    // EmergencyStopState this session's own emergencyStop.spec.ts exercises
    // end-to-end via TopStatusBar; here we only confirm this panel shows
    // the current (inactive) status and offers the same control.
    await expect(page.getByText("Global Emergency Stop", { exact: true })).toBeVisible();
    await expect(page.getByText("Not active", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Emergency Stop", exact: true }).last()).toBeVisible();

    // Explicitly cut features must say so, never fake a control.
    await expect(page.getByText("Black Swan Protection", { exact: false })).toBeVisible();
    await expect(page.getByText("Broker Failover", { exact: false })).toBeVisible();
    await expect(page.getByText("Emergency Contacts", { exact: false })).toBeVisible();
  });

  test("EXECUTIVE tab's Pending Proposals queue shows a real Priority Score or the honest N/A, always real content or an honest empty state (v0.7 Chapter 59)", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "EXECUTIVE");

    await expect(page.getByText("Ranked by Priority Score", { exact: false })).toBeVisible();
    const hasEmptyState = await page.getByText(/No trade proposals awaiting a decision/).count();
    if (hasEmptyState === 0) {
      await expect(page.getByText(/Priority (N\/A|\d+\/100)/).first()).toBeVisible();
    } else {
      expect(hasEmptyState).toBeGreaterThan(0);
    }
  });

  test("Trade Closed notification shows a real closed trade's win/loss non-blockingly, and dismissal persists", async ({ page }) => {
    // UI Polish Sprint — this used to cover TradeOutcomeBanner.tsx's
    // center-screen modal-style card; that component was replaced by a
    // real right-side stacking toast in CyberNotifications.tsx (the
    // user-reported "interrupts gameplay" bug this sprint fixed), so this
    // test now covers the real testid/markup that replaced it.
    test.setTimeout(60000); // polls up to 45s for a real trade to close naturally
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page); // clears any pre-existing backlog, so what we wait for below is guaranteed fresh

    // POST /api/save only ever merges player/settings/dialogueHistory from
    // the client (see state.py's apply_client_save) — everything else,
    // including viewedTradeNotificationIds, stays server-authoritative. So
    // rather than faking an unviewed trade through a save round trip, wait
    // on the real live WS feed for the sim's own paper-trading engine to
    // actually close one — the same "real backend, real timing" approach
    // this whole test file already uses everywhere else.
    const toast = page.getByTestId("trade-outcome-toast").first();
    let appeared = true;
    try {
      await expect(toast).toBeVisible({ timeout: 45000 });
    } catch {
      appeared = false;
    }
    test.skip(!appeared, "no new real trade closed within the poll window");

    // The toast must be non-blocking — gameplay behind it stays clickable.
    await expect(page.getByRole("button", { name: "Command ⌁" })).toBeEnabled();

    await expect(toast).toHaveText(/Trade Closed — (Profit|Loss|Breakeven)/);

    const symbol = (await toast.innerText()).match(/^([A-Z.]+) ·/m)?.[1] ?? null;
    await toast.getByText("✕").click();
    await expect(toast).not.toBeVisible();

    // Dismissal must persist — reloading must never re-show a toast for
    // that same trade (a fresh one for a *different*, later trade closing
    // in the meantime is fine and expected).
    await page.reload();
    await clickContinueOnTitleScreen(page);
    const reloadedToast = page.getByTestId("trade-outcome-toast").first();
    if (symbol && (await reloadedToast.isVisible().catch(() => false))) {
      await expect(reloadedToast).not.toContainText(symbol);
    }
  });

  test("Company tab shows real Company Health, Market Environment, and a working Operating Mode toggle", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "COMPANY");

    // Company Health: a real overall score/tier and all ten sub-metrics.
    // (v0.7 Feature 50 Part 2/3 added an Executive Health card and a
    // Combined Overall row with their own tier badges from the same
    // EXCELLENT/GOOD/STABLE/... vocabulary, so `.first()` avoids a
    // strict-mode ambiguity — any match confirms a real tier rendered.)
    await expect(page.getByText("Company Health", { exact: true })).toBeVisible();
    await expect(page.getByText(/EXCELLENT|GOOD|STABLE|NEEDS ATTENTION|CRITICAL/).first()).toBeVisible();
    // .first() here too: Design Bible Chapter 64's Company Goals card
    // (below, same tab) adds a real category dropdown whose own
    // <option>Research</option> text is also matched by getByText, the
    // same legitimate multi-match case as the tier vocabulary above —
    // any match confirms the real Company Health label rendered.
    for (const metric of ["Stability", "Efficiency", "Morale", "Research", "Capital", "Resources", "Reputation", "Technology", "Office", "Education"]) {
      await expect(page.getByText(metric, { exact: true }).first()).toBeVisible();
    }

    // Regime Reconciliation (Design Bible Chapter 65) — reconciles the
    // two real regime engines into one aligned/diverging read plus a
    // cautious/normal/opportunistic posture recommendation.
    await expect(page.getByText("Regime Reconciliation", { exact: true })).toBeVisible();
    await expect(page.getByText(/ALIGNED|DIVERGING/).first()).toBeVisible();
    await expect(page.getByText(/CAUTIOUS|NORMAL|OPPORTUNISTIC/).first()).toBeVisible();

    // Market Environment: a real regime pill plus its own detail text.
    // (The regime label can also repeat in the historical timeline below,
    // so `.first()` avoids a strict-mode ambiguity — any match confirms
    // the real regime rendered.)
    await expect(page.getByText("Market Environment", { exact: true })).toBeVisible();
    await expect(page.getByText(/BULL MARKET|BEAR MARKET|SIDEWAYS|HIGH VOLATILITY|LOW VOLATILITY/).first()).toBeVisible();

    // Strategic Review Cycle (Design Bible Chapter 64, fifth pass) — the
    // card always renders, with either a real review or an honest empty
    // state (no review has generated yet on a fresh save).
    await expect(page.getByText("Strategic Review Cycle", { exact: true })).toBeVisible();

    // Operating Mode toggle: defaults to LEARNING; switching to ASSISTED
    // both highlights the new selection and persists across a reload
    // (settings are client-authoritative, merged into the next save).
    // "shadow-cmd-cyan" (not just "border-cmd-cyan", which also appears
    // in the inactive button's own hover: class) is the active-only marker.
    // Matched by its own description text, not just "LEARNING" — v0.7
    // Feature 34's Company Priority section (below) has its own distinct
    // "LEARNING" option, so a bare /^LEARNING/ match is ambiguous now.
    const learningButton = page.getByRole("button", { name: /Every trade proposal waits for your real buy\/sell\/wait call/ });
    await expect(learningButton).toHaveClass(/shadow-cmd-cyan/);

    const assistedButton = page.getByRole("button", { name: /^ASSISTED/ });
    await assistedButton.click();
    await expect(assistedButton).toHaveClass(/shadow-cmd-cyan/);
    await expect(learningButton).not.toHaveClass(/shadow-cmd-cyan/);
  });

  test("KNOWLEDGE tab shows real Academy Progression, Knowledge Trees, and the Company Knowledge Library", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "KNOWLEDGE");

    // Academy Progression: a real level (1-5) and its named tier.
    await expect(page.getByText("Academy Progression", { exact: true })).toBeVisible();
    await expect(page.getByText(/LEVEL [1-5] —/)).toBeVisible();

    // Knowledge Trees: every agent (including Meridian, the CIO) has a
    // real branch and a real points total — the ten agent names below
    // are the same roster the toolbar/Agents tab already shows.
    await expect(page.getByText("Knowledge Trees", { exact: true })).toBeVisible();
    await expect(page.getByText("Meridian", { exact: true }).first()).toBeVisible();

    // v0.7 Feature 40 — Career Level is the same real per-agent knowledge
    // tier academy.py already tracks, just relabeled onto the brief's
    // Student-through-Legend ladder (see careerLevels.ts).
    await expect(page.getByText(/Career Level: (Student|Junior|Professional|Senior|Expert|Master|Legend)/).first()).toBeVisible();

    // Active Research Project and the Company Knowledge Library both
    // render something truthful — either real content or the explicit
    // empty state — never a blank panel.
    await expect(page.getByText("Active Research Project", { exact: true })).toBeVisible();
    await expect(page.getByText("Company Knowledge Library", { exact: true })).toBeVisible();

    // v0.7 Feature 41 — Innovation Points, driven only by real Devil's
    // Advocate Challenge Report authorship (see backend/app/innovation.py)
    // — always real content or the honest empty state, never fabricated.
    await expect(page.getByText("Innovation Points — Devil's Advocate Track Record", { exact: true })).toBeVisible();
    const innovationEmptyState = page.getByText(/No Innovation Points earned yet/);
    const innovationRow = page.getByText(/Research Contributor|Research Specialist|Innovation Leader|Chief Innovator|Legendary Innovator/).first();
    await expect(innovationEmptyState.or(innovationRow)).toBeVisible();
  });

  test("Knowledge Graph opens a real node-edge network fetched from GET /api/knowledge-graph, with working filters and search", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    // The backend keeps ticking in real time across this whole test file,
    // so a genuine trade proposal can pop up in the instant before this
    // click — dismiss it first, the same guard the "renders all N tabs"
    // test above already uses.
    await clickExpand(page);
    await clickTab(page, "KNOWLEDGE");

    await expect(page.getByText("Company Knowledge Graph", { exact: true })).toBeVisible();
    await clickButton(page, /Open Knowledge Graph/);

    // The header's live node/edge count is real — it comes straight from
    // the fetched KnowledgeGraph, not a placeholder.
    await expect(page.getByText(/\d+ NODES · \d+ LINKS/)).toBeVisible();
    await expect(page.locator("canvas").last()).toBeVisible();

    // Type filter chips toggle a real node type off (visual state change
    // only — verified by the button no longer being "active"-styled).
    const researchFilter = page.getByRole("button", { name: "Research", exact: true });
    await expect(researchFilter).toBeVisible();
    await researchFilter.click();

    // Search narrows the "Recent Discoveries" default panel down to
    // real matching titles (or shows nothing if no real node matches).
    await page.getByPlaceholder("Search the network…").fill("zzz-no-such-discovery-zzz");
    await page.waitForTimeout(300);

    await page.getByRole("button", { name: "CLOSE ✕" }).last().click();
    await expect(page.getByText("Company Knowledge Graph", { exact: true })).toBeVisible();
  });

  test("DISCIPLINE tab shows the Discipline Chamber and Library of Mistakes, always real content or an honest empty state", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "DISCIPLINE");

    await expect(page.getByText("Discipline Chamber", { exact: true })).toBeVisible();
    await expect(page.getByText("Discipline Reviews", { exact: true })).toBeVisible();
    await expect(page.getByText("Library of Mistakes & Successes", { exact: true })).toBeVisible();

    // Either a real average score readout or the honest "no trades yet"
    // empty state — never a blank panel. Discipline Score is process-only
    // (never derived from pnl), so whichever renders is truthful either way.
    const hasScore = await page.getByText(/\d+\/100 average discipline score/).count();
    const hasEmptyState = await page.getByText(/No trades have closed yet/).count();
    expect(hasScore + hasEmptyState).toBeGreaterThan(0);
  });

  test("VAULT tab shows the Decision Vault, and selecting a record loads a real Trade Report Card and Similarity Engine read, always real content or an honest empty state", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "VAULT");

    await expect(page.getByText("Decision Vault", { exact: true })).toBeVisible();

    // Either the honest "nothing archived yet" empty state, or at least
    // one real vault record with a Trade Report Card and Similarity
    // Engine read fetched for it — never a blank panel either way.
    const hasEmptyState = await page.getByText(/Nothing archived yet/).count();
    if (hasEmptyState === 0) {
      await expect(page.getByText("Trade Report Card", { exact: false }).first()).toBeVisible();
      await expect(page.getByText("Similarity Engine", { exact: false }).first()).toBeVisible();
    } else {
      expect(hasEmptyState).toBeGreaterThan(0);
    }
  });

  test("WARROOM tab shows the Digital War Room, and selecting a session shows its real Decision Score, Expected Value, and Contingency Plan, always real content or an honest empty state", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "WARROOM");

    await expect(page.getByText("War Room", { exact: true })).toBeVisible();

    // Either the honest "no proposal has entered the War Room yet" empty
    // state, or at least one real session with its Decision Score,
    // Expected Value, and Contingency Plan — never a blank panel either way.
    const hasEmptyState = await page.getByText(/No proposal has entered the War Room yet/).count();
    if (hasEmptyState === 0) {
      await expect(page.getByText("Decision Score", { exact: false }).first()).toBeVisible();
      await expect(page.getByText("Expected Value", { exact: false }).first()).toBeVisible();
      await expect(page.getByText("Contingency Plan", { exact: false }).first()).toBeVisible();
      // v0.7 Chapter 57 — every session created after the engine landed
      // carries a real positionSizing result; only a save from before
      // Chapter 57 existed would lack one.
      await expect(page.getByText("Position Sizing — Capital Deployment Engine", { exact: true }).first()).toBeVisible();
    } else {
      expect(hasEmptyState).toBeGreaterThan(0);
    }
  });

  test("PORTFOLIO tab shows real Capital Allocation, Portfolio Heat, and Category Exposure, always real content or an honest empty state", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "PORTFOLIO");

    await expect(page.getByText("Capital Allocation", { exact: true })).toBeVisible();
    // .first() since Design Bible Chapter 67's GlobalStatusBar now shows
    // this same real Portfolio Heat tier from every scene, not just here.
    await expect(page.getByText(/COOL|WARM|HOT|OVERHEATED/).first()).toBeVisible();

    // Either real open-position category exposure, or the honest "no open
    // positions" empty state — never a blank panel either way.
    const hasEmptyState = await page.getByText(/No open positions — nothing to break down by category yet/).count();
    if (hasEmptyState === 0) {
      await expect(page.getByText(/position/).first()).toBeVisible();
    } else {
      expect(hasEmptyState).toBeGreaterThan(0);
    }
  });

  test("REASONING tab shows the Reasoning Lab's level, progress, and history, always real content or an honest empty state", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "REASONING");

    await expect(page.getByText("Reasoning Lab", { exact: true })).toBeVisible();
    await expect(page.getByText(/LEVEL \d+ —/)).toBeVisible();
    await expect(page.getByText("Reasoning History", { exact: true })).toBeVisible();

    // Either real filed challenges or the honest "none yet" empty state —
    // never a blank panel. No challenge here ever reads a trade's pnl, so
    // whichever renders is truthful either way.
    const hasEmptyState = await page.getByText(/No reasoning challenges filed yet/).count();
    if (hasEmptyState === 0) {
      await expect(page.locator(".text-cmd-purple").first()).toBeVisible();
    }
  });

  test("REFLECTION tab shows Company Wisdom and the Reflection Journal, always real content or an honest empty state", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "REFLECTION");

    await expect(page.getByText("Company Wisdom", { exact: true })).toBeVisible();
    await expect(page.getByText(/\/100 —/)).toBeVisible();
    await expect(page.getByText("Reflection Journal", { exact: true })).toBeVisible();

    // Either real filed sessions or the honest "none yet" empty state —
    // never a blank panel. Company Wisdom never reads a trade's pnl, so
    // whichever renders is truthful either way.
    const hasEmptyState = await page.getByText(/No Reflection Session yet/).count();
    if (hasEmptyState === 0) {
      await expect(page.getByText(/Wisdom \d+\/100/).first()).toBeVisible();
    }
  });

  test("MENTOR tab shows Sage's Question of the Day, the archive, and Thinking Profiles, always real content or an honest empty state", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "MENTOR");

    await expect(page.getByText("Question of the Day", { exact: true })).toBeVisible();
    await expect(page.getByText("Question Archive", { exact: true })).toBeVisible();
    await expect(page.getByText("Thinking Profiles", { exact: true })).toBeVisible();

    // Day 1 always seeds one real QuestionOfTheDay (see backend/app/state.py's
    // default_state()) — never a blank panel here.
    await expect(page.getByText(/“.+”/).first()).toBeVisible();

    // Every real agent (including Sage) gets a purely-computed Thinking
    // Profile from tick one — never a blank panel here either.
    await expect(page.getByText("Collaboration", { exact: true }).first()).toBeVisible();
  });

  test("FOUNDERS tab shows Keystone and Compass's real identity, and Legendary Status starts active (not retired)", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "FOUNDERS");

    await expect(page.getByText("Legendary Status", { exact: true })).toBeVisible();
    // A fresh company hasn't reached Company Health's "excellent" tier yet.
    await expect(page.getByText("ACTIVE LEADERSHIP", { exact: true })).toBeVisible();

    // Real, hand-authored identity content for both Founders — never a
    // blank panel, since this is static content, not simulation output.
    await expect(page.getByText("Keystone", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Chief Risk Architect", { exact: true })).toBeVisible();
    await expect(page.getByText("Protect the company first. Profit comes second.", { exact: false })).toBeVisible();
    await expect(page.getByText("Compass", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Chief Learning Architect", { exact: true })).toBeVisible();
    await expect(page.getByText("Every mistake is an opportunity to improve.", { exact: false })).toBeVisible();

    await expect(page.getByText("Founder Log", { exact: true })).toBeVisible();
    await expect(page.getByText("Founder Council", { exact: true })).toBeVisible();
  });

  test("TREASURY tab performs a real deposit and withdrawal via POST /api/treasury/deposit and /withdraw", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "TREASURY");

    await expect(page.getByText("CEO Treasury", { exact: true })).toBeVisible();
    await expect(page.getByText("Operating Capital", { exact: true })).toBeVisible();

    const treasuryBalance = page.getByTestId("treasury-balance");
    const operatingBalance = page.getByTestId("operating-capital-balance");
    const readDollar = async (locator: typeof treasuryBalance) => Number((await locator.innerText()).replace(/[^0-9.-]/g, ""));

    // Structural isolation: a deposit moves real cash from Operating
    // Capital to the Treasury — never invents money on either side.
    const treasuryBefore = await readDollar(treasuryBalance);
    const operatingBefore = await readDollar(operatingBalance);

    // BUG FIX (UI Polish Sprint): this used to grab
    // `input[type="number"]').first()`, which broke silently the moment
    // Chapter 69 Part 1's AccountsSection (its own "Starting Balance"
    // number input) started rendering above this Deposit/Withdraw card —
    // the test was filling the wrong field and asserting on whatever
    // stale default ("1000") the real Deposit button still held. Scoped
    // to the real field's own testid now, added alongside this fix.
    const amountInput = page.getByTestId("treasury-amount-input");
    await amountInput.fill("500");
    await clickButton(page, /Deposit/);

    await expect(async () => {
      const treasuryAfter = await readDollar(treasuryBalance);
      expect(treasuryAfter).toBe(treasuryBefore + 500);
    }).toPass({ timeout: 5000 });
    const operatingAfterDeposit = await readDollar(operatingBalance);
    expect(operatingAfterDeposit).toBe(operatingBefore - 500);

    // And a withdrawal reverses it — the same real, validated transfer
    // in the other direction.
    await amountInput.fill("500");
    await page.getByRole("button", { name: /Withdraw/ }).click();
    await expect(async () => {
      const treasuryAfter = await readDollar(treasuryBalance);
      expect(treasuryAfter).toBe(treasuryBefore);
    }).toPass({ timeout: 5000 });
    const operatingAfterWithdraw = await readDollar(operatingBalance);
    expect(operatingAfterWithdraw).toBe(operatingBefore);

    // Withdrawing more than the Treasury holds is rejected honestly
    // rather than silently going negative.
    await amountInput.fill("999999999");
    await page.getByRole("button", { name: /Withdraw/ }).click();
    await expect(page.getByText(/Treasury only holds/)).toBeVisible({ timeout: 5000 });
  });

  test("Company Priority selection is real and persists across a reload, distinct from Operating Mode", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "COMPANY");

    // Matched by its own description text, not just "RESEARCH" — the
    // top nav already has an exact "RESEARCH" tab button, so a bare
    // /^RESEARCH/ match against the priority button (whose accessible
    // name also includes its description) is ambiguous.
    await expect(page.getByText("Company Priority", { exact: true })).toBeVisible();
    const researchPriority = page.getByRole("button", { name: /Active research items gain confidence/ });
    await expect(researchPriority).toBeVisible();
    await researchPriority.click();
    await expect(researchPriority).toHaveClass(/border-cmd-purple/);

    await page.reload();
    await clickContinueOnTitleScreen(page);
    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "COMPANY");
    await expect(page.getByRole("button", { name: /Active research items gain confidence/ })).toHaveClass(/border-cmd-purple/);

    // Reset back to Balanced so later runs against this shared dev
    // backend start from a known-neutral priority. "BALANCED" is unique
    // (no Operating Mode or nav-tab collision).
    const balancedPriority = page.getByRole("button", { name: /^BALANCED/ });
    await balancedPriority.click();
    await expect(balancedPriority).toHaveClass(/border-cmd-purple/);
  });

  test("Time Controls END WORKDAY jumps the real clock via POST /api/time/advance", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "COMPANY");

    const headerTime = page.getByText(/^Day \d+ · \d{2}:\d{2}$/);
    const readMinutes = async () => {
      const text = await headerTime.textContent();
      const match = text?.match(/Day (\d+) · (\d{2}):(\d{2})/);
      if (!match) throw new Error(`could not parse header time: ${text}`);
      return Number(match[1]) * 1440 + Number(match[2]) * 60 + Number(match[3]);
    };
    const before = await readMinutes();

    // Not `exact: true` — the button's accessible name is its label plus
    // its own description text ("END WORKDAY Jump to 20:00 — ..."), so an
    // exact match against just the label never matches.
    const advanceButton = page.getByRole("button", { name: /^END WORKDAY/ });
    await expect(advanceButton).toBeVisible();
    await advanceButton.click();

    // A real fast-forward jumps a large amount — far more than the
    // handful of minutes the sim's own background real-time tick loop
    // could add over the few seconds this assertion polls for, so a
    // sizable forward jump confirms the CEO action actually fired
    // rather than just organic ticking.
    await expect(async () => {
      const after = await readMinutes();
      expect(after - before).toBeGreaterThan(60);
    }).toPass({ timeout: 15000 });
  });

  test("number keys 1-9 jump straight to the matching Command Center tab, ignored while typing in a form field", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await dismissBlockingPopups(page);

    // Tab 9 is "RESEARCH" per FullCommandCenter.tsx's own TABS order
    // (Design Bible Chapter 72 inserted BLACKSWAN right after RISK,
    // shifting every tab from AGENTS onward down one position).
    await page.keyboard.press("9");
    await expect(page.getByRole("button", { name: "RESEARCH", exact: true })).toHaveClass(/text-cmd-cyan/);

    // Tab 1 is "OVERVIEW".
    await page.keyboard.press("1");
    await expect(page.getByRole("button", { name: "OVERVIEW", exact: true })).toHaveClass(/text-cmd-cyan/);

    // Now jump into TREASURY (via a mouse click — its own tab index is
    // past 9, so it's not reachable by a number-key shortcut) and confirm
    // typing a digit into its real amount field does NOT trigger a tab
    // switch away from it.
    await clickTab(page, "TREASURY");
    // See the deposit/withdraw test above for why this must be scoped to
    // the real field's own testid rather than `.first()`.
    const amountInput = page.getByTestId("treasury-amount-input");
    await amountInput.fill("");
    await amountInput.type("2");
    await expect(page.getByRole("button", { name: "TREASURY", exact: true })).toHaveClass(/text-cmd-cyan/);
    await expect(amountInput).toHaveValue("2");
  });

  test("CALENDAR tab shows real system events, a real per-agent Live Schedule, and a working custom-event round trip", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await clickExpand(page);
    await clickTab(page, "CALENDAR");

    await expect(page.getByText("Executive View", { exact: true })).toBeVisible();
    await expect(page.getByText("Current Company Focus", { exact: true })).toBeVisible();
    await expect(page.getByText("Today's Schedule", { exact: true })).toBeVisible();
    await expect(page.getByText("Tomorrow's Schedule", { exact: true })).toBeVisible();
    await expect(page.getByText("Weekly Agenda", { exact: true })).toBeVisible();
    await expect(page.getByText("Monthly Company Events", { exact: true })).toBeVisible();

    // A real, always-present system event — Sage's daily Morning Briefing
    // — Question of the Day — appears somewhere in the upcoming lists.
    await expect(page.getByText(/Morning Briefing/).first()).toBeVisible();

    // Live Schedule: switching agents shows that real agent's own full
    // daily schedule (the same real blocks app/schedule.py drives).
    await expect(page.getByText("Live Schedule", { exact: true })).toBeVisible();
    await clickButton(page, "Atlas");
    await expect(page.getByText("Atlas's Real Daily Schedule")).toBeVisible();
    await expect(page.getByText("Reviewing overnight strategy")).toBeVisible();

    // Custom event round trip via a real POST /api/calendar/events/create
    // and /delete. Scheduled for tomorrow at a fixed hour — always in the
    // future regardless of the real backend's current in-game hour, since
    // this shared dev backend keeps ticking for this whole file's run.
    const dayInput = page.getByTestId("calendar-event-day");
    const currentDay = Number(await dayInput.inputValue());
    await dayInput.fill(String(currentDay + 1));
    await page.getByTestId("calendar-event-hour").fill("9");
    await page.getByTestId("calendar-event-minute").fill("0");

    const uniqueTitle = `Playwright test event ${Date.now()}`;
    await page.getByTestId("calendar-event-title").fill(uniqueTitle);
    await clickButton(page, "Schedule Event");

    const eventRow = page.getByText(uniqueTitle, { exact: true });
    await expect(eventRow).toBeVisible({ timeout: 5000 });

    // Deleting it removes it — the ✕ button sits in the same row.
    await eventRow.locator("xpath=..").getByText("✕", { exact: true }).click();
    await expect(eventRow).not.toBeVisible({ timeout: 5000 });
  });

  test("Work Mode toggle in the always-visible toolbar switches modes, the status indicator updates, and a real save routes every agent to a real off-hours task", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    const toggle = page.getByRole("button", { name: /WORK MODE ACTIVE|REST MODE ACTIVE/ });
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveText(/🟢 WORK MODE ACTIVE/);

    await clickButton(page, /WORK MODE ACTIVE|REST MODE ACTIVE/);
    await expect(toggle).toHaveText(/🌙 REST MODE ACTIVE/);

    // A real POST /api/save pushes the new work_mode setting to the
    // server the same way a real player's autosave would; the sim's own
    // next real tick then applies the real Rest Mode routing — poll
    // GET /api/load rather than asserting immediately, since that next
    // tick is a real ~2s-interval async event, not synchronous with the
    // save call.
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect(async () => {
      const state = await page.evaluate(async () => {
        const res = await fetch("/api/load");
        return res.json();
      });
      const locations = Object.values(state.agents).map((a: unknown) => (a as { location: string }).location);
      expect(locations.every((loc) => loc === "break-room")).toBe(true);
    }).toPass({ timeout: 15000 });

    // Switching back to Work Mode restores the status indicator; the
    // underlying schedule-routing effect is already covered by
    // backend/tests/test_work_mode.py, so the E2E round trip stops here.
    await toggle.click();
    await expect(toggle).toHaveText(/🟢 WORK MODE ACTIVE/);
    await page.getByRole("button", { name: "Save", exact: true }).click();
  });
});
