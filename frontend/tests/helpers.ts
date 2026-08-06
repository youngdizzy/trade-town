import { expect, type Locator, type Page } from "@playwright/test";

/**
 * Shared Playwright helpers for the "exercise the real running app" test
 * suite (Vite dev server + FastAPI backend, no mocking). Every spec file
 * under tests/ used to carry its own copy-pasted version of these — see
 * docs/Architecture.md's "Test suite popup resilience" section for why
 * that drifted into real gaps (some files' `continueGame` never dismissed
 * anything; none of them knew about the Gatekeeper Rejection screen or
 * the Breakthrough Moment overlay).
 *
 * The core idea: this app's sim clock keeps ticking in real time for the
 * whole test run, against one shared dev backend. That's correct, honest
 * behavior, not a test-only quirk — it means a genuine TradeProposal,
 * closed trade, Gatekeeper veto, or Founder-approved breakthrough can pop
 * up over whatever a test is doing at any moment, the same way it would
 * for a real player. Tests should react to that popup exactly the way a
 * real player would (read it, dismiss it, keep going), never fail
 * because one showed up. A test should only fail here if a popup
 * genuinely can't be dismissed, blocks the app permanently, or the
 * dismiss action itself misbehaves (wrong content, doesn't close, etc.)
 * — see each tryDismiss* function below for the specific check that
 * turns "expected gameplay event" into a real, thrown failure.
 */

/** The raw title-screen "Continue" click sequence, with no popup
 * handling — used by continueGame() and by any test that specifically
 * needs to inspect a popup right as it appears. */
export async function clickContinueOnTitleScreen(page: Page): Promise<void> {
  const canvas = page.locator("canvas");
  await expect(canvas).toBeVisible();
  // Preload (asset loading + PreloadScene -> MainMenuScene handoff) can
  // take a moment after the canvas element itself first appears — click
  // too early and the pointerdown lands on nothing.
  await page.waitForTimeout(800);

  // "Continue" is the second title-screen button, drawn at
  // (width/2, height*0.5 + 44) in MainMenuScene.ts's own layout math.
  // Retry the click: under load, the very first click can land before
  // MainMenuScene's interactive text objects are registered.
  for (let attempt = 0; attempt < 5; attempt++) {
    const box = await canvas.boundingBox();
    if (!box) throw new Error("clickContinueOnTitleScreen: canvas has no bounding box");
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

/** Writes the player's scene/position directly through the real POST
 * /api/save endpoint (the same one SaveManager itself uses) so a test
 * can resume into an arbitrary room via the title screen's real
 * "Continue" path, without needing to script pixel-perfect physics-based
 * navigation through doors. */
export async function setPlayerScene(page: Page, scene: string, x: number, y: number): Promise<void> {
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  state.player = { ...state.player, scene, x, y, facing: "down" };
  await page.evaluate(async (s) => {
    await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(s),
    });
  }, state);
}

/** Reads DebugOverlay's live "FPS — Scene (x, y)" readout. */
export async function readDebug(page: Page): Promise<{ scene: string; x: number; y: number }> {
  const text = await page.locator("text=/FPS — /").textContent();
  const match = text?.match(/FPS — (\S+) \((-?\d+), (-?\d+)\)/);
  if (!match) throw new Error(`readDebug: could not parse debug overlay: ${text}`);
  return { scene: match[1]!, x: Number(match[2]), y: Number(match[3]) };
}

// --- Popup dismissal --------------------------------------------------

/** One real gameplay-event overlay this suite knows how to close as a
 * bystander (never as a meaningful gameplay decision — see each
 * function's own comment for the exact non-committal action taken).
 * Returns false if the popup wasn't showing at all (nothing to do).
 * Throws if it *was* showing but didn't close after clicking its own
 * dismiss control — that's the "cannot be dismissed" / "behaves
 * incorrectly" case that should still fail a test. */
type PopupDismisser = (page: Page) => Promise<boolean>;

/** v0.7 — the Eureka! Breakthrough System (BreakthroughMoment.tsx). Full-
 * screen, no data-testid, single exit button. Rare (needs a real
 * Founder-approved BlackBoxReview) but real, and blocks both movement
 * and interaction while open, so it must be handled first. */
const tryDismissBreakthroughMoment: PopupDismisser = async (page) => {
  const button = page.getByRole("button", { name: /Add to the Museum of Discoveries/ });
  if (!(await button.isVisible().catch(() => false))) return false;
  await button.click();
  const stillThere = await button
    .waitFor({ state: "hidden", timeout: 5000 })
    .then(() => false)
    .catch(() => true);
  if (stillThere) throw new Error("dismissBlockingPopups: Breakthrough Moment overlay did not close after clicking its own dismiss button");
  return true;
};

/** v0.7 Feature 20 — the Trade Gatekeeper's veto screen (ExecutiveVoting.tsx,
 * testid "gatekeeper-rejection"). Only ever reachable by a real BUY/SELL
 * decision another action in the same test (or an earlier test sharing
 * this dev backend's page) already submitted; this helper only ever
 * acknowledges it, never makes the underlying decision. */
const tryDismissGatekeeperRejection: PopupDismisser = async (page) => {
  const popup = page.getByTestId("gatekeeper-rejection");
  if (!(await popup.isVisible().catch(() => false))) return false;
  await popup.getByRole("button", { name: "ACKNOWLEDGE" }).click();
  const stillThere = await popup
    .waitFor({ state: "hidden", timeout: 5000 })
    .then(() => false)
    .catch(() => true);
  if (stillThere) throw new Error('dismissBlockingPopups: Gatekeeper Rejection screen did not close after clicking "ACKNOWLEDGE"');
  return true;
};

/** Feature 12 — Executive Voting (ExecutiveVoting.tsx, testid
 * "executive-voting"). Always dismissed via "Decide later — this
 * proposal stays pending", the one real exit that neither submits a CEO
 * decision nor can chain into the Gatekeeper Rejection screen — a test
 * that actually wants to exercise BUY/SELL/WAIT should interact with
 * this popup directly instead of going through this bystander helper. */
const tryDismissExecutiveVoting: PopupDismisser = async (page) => {
  const popup = page.getByTestId("executive-voting");
  if (!(await popup.isVisible().catch(() => false))) return false;
  await popup.getByText("Decide later").click();
  const stillThere = await popup
    .waitFor({ state: "hidden", timeout: 5000 })
    .then(() => false)
    .catch(() => true);
  if (stillThere) throw new Error('dismissBlockingPopups: Executive Voting popup did not close after clicking "Decide later"');
  return true;
};

/** A real closed PaperTrade's win/loss notification (UI Polish Sprint —
 * moved from the old center-screen TradeOutcomeBanner.tsx into
 * CyberNotifications.tsx's real right-side toast stack, testid
 * "trade-outcome-toast"). Non-blocking by design (a small corner card,
 * not a modal), but tests still dismiss it so it can't visually cover an
 * element a later step needs to click. Multiple can be visible
 * simultaneously now (the whole point of the redesign — real stacking,
 * not one-at-a-time queueing), so this closes the first one found each
 * pass and the outer dismiss loop naturally revisits for any more. */
const tryDismissTradeOutcomeBanner: PopupDismisser = async (page) => {
  const toasts = page.getByTestId("trade-outcome-toast");
  const countBefore = await toasts.count();
  if (countBefore === 0) return false;
  await toasts.first().getByText("✕").click();
  // Multiple can be visible at once now, so — unlike the old single-
  // instance banner — this waits for the *count* to drop rather than one
  // specific element to hide (a `.first()` locator re-resolves to
  // whatever remains after the dismissed one unmounts, which would
  // otherwise still be visible and falsely look "stuck").
  const stillThere = await expect(toasts)
    .toHaveCount(countBefore - 1, { timeout: 5000 })
    .then(() => false)
    .catch(() => true);
  if (stillThere) throw new Error("dismissBlockingPopups: Trade Closed notification did not close after clicking its dismiss button");
  return true;
};

// Checked in this order every pass — roughly highest z-index / most
// blocking first. Only one of these is ever expected to be visible at
// once, except for the deliberate chains this loop already re-checks
// for on the next pass: banner -> next queued banner, and (for a test
// that submits its own BUY/SELL rather than going through
// tryDismissExecutiveVoting) executive-voting -> gatekeeper-rejection.
const KNOWN_POPUP_DISMISSERS: readonly PopupDismisser[] = [
  tryDismissBreakthroughMoment,
  tryDismissGatekeeperRejection,
  tryDismissExecutiveVoting,
  tryDismissTradeOutcomeBanner,
];

// Generous on purpose: the longer this shared dev backend has been
// running, the more real decisions/trades/breakthroughs can be queued up
// behind one another (a real, honest consequence of one dev backend
// serving the whole test file), and each is dismissed one at a time,
// same as a player would. This is a *count of successful dismissals*,
// not a timeout — a popup that never closes throws immediately from its
// own tryDismiss* function above rather than silently exhausting this
// budget.
const MAX_POPUP_DISMISS_ROUNDS = 30;

/** Dismisses every known blocking/auto-appearing popup currently showing,
 * looping in case closing one reveals another queued behind it. Safe and
 * cheap to call when nothing is open (each check is a single
 * `isVisible()` probe). This is the one function every test's
 * `continueGame()` and every retry-safe click helper below should run
 * before interacting with anything, so an expected gameplay event never
 * fails a test — it only throws if a popup that *was* showing refused to
 * close, which is a real bug, not normal play. */
export async function dismissBlockingPopups(page: Page): Promise<void> {
  for (let round = 0; round < MAX_POPUP_DISMISS_ROUNDS; round++) {
    let dismissedSomething = false;
    for (const tryDismiss of KNOWN_POPUP_DISMISSERS) {
      if (await tryDismiss(page)) {
        dismissedSomething = true;
        break; // re-check from the top — closing one can reveal a higher-priority one
      }
    }
    if (!dismissedSomething) return;
  }
  throw new Error(`dismissBlockingPopups: still finding popups to dismiss after ${MAX_POPUP_DISMISS_ROUNDS} rounds — a popup may be stuck reopening itself`);
}

export async function continueGame(page: Page): Promise<void> {
  await clickContinueOnTitleScreen(page);
  await dismissBlockingPopups(page);
}

/** Wraps any single click in a dismiss-then-click retry loop, so a real
 * popup that appears in the gap between dismissing and clicking (the sim
 * keeps ticking throughout every test file) doesn't lose the race and
 * fail the test — it just gets dismissed again on the next attempt. Only
 * throws once the click itself has never actually landed after several
 * honest attempts, which is a real failure (element never appeared,
 * dismissal genuinely can't keep up, etc.), not an expected gameplay
 * event. */
export async function clickRobust(page: Page, locator: () => Locator, opts?: { attempts?: number; timeoutMs?: number; label?: string }): Promise<void> {
  const attempts = opts?.attempts ?? 8;
  const timeoutMs = opts?.timeoutMs ?? 5000;
  for (let attempt = 0; attempt < attempts; attempt++) {
    await dismissBlockingPopups(page);
    try {
      await locator().click({ timeout: timeoutMs });
      return;
    } catch {
      // a popup intercepted the click (or the element wasn't ready yet) — loop back and dismiss again
    }
  }
  throw new Error(`clickRobust: could not complete the click${opts?.label ? ` (${opts.label})` : ""} after ${attempts} attempts`);
}

/** Clicks a Command Center tab, retrying through any popup that
 * intercepts the click. */
export async function clickTab(page: Page, tab: string): Promise<void> {
  await clickRobust(page, () => page.getByRole("button", { name: tab, exact: true }), { label: `tab "${tab}"` });
}

/** Clicks a button by its accessible name (exact or pattern), retrying
 * through any popup that intercepts the click. */
export async function clickButton(page: Page, name: string | RegExp): Promise<void> {
  await clickRobust(page, () => page.getByRole("button", { name }), { label: `button "${String(name)}"` });
}

/** Expands the Global Command Center's Quick View into the Full Command
 * Center, retrying through any popup that intercepts the click. */
export async function clickExpand(page: Page): Promise<void> {
  await clickRobust(page, () => page.getByText("EXPAND — FULL COMMAND CENTER"), { label: "EXPAND — FULL COMMAND CENTER" });
}

export async function enableDebugOverlay(page: Page): Promise<void> {
  await clickButton(page, "Settings");
  const checkbox = page.getByRole("checkbox");
  if (!(await checkbox.isChecked())) {
    await dismissBlockingPopups(page);
    await checkbox.check();
  }
  await clickButton(page, "Close");
}
