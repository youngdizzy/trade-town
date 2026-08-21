import { test, expect, type Page, type Request } from "@playwright/test";
import { clickContinueOnTitleScreen } from "./helpers";

/**
 * Safe "New Game" confirmation + multi-run isolation. Same real-app
 * testing approach as every other spec in this suite (live Vite +
 * FastAPI dev stack, no mocking) with two deliberate, disclosed
 * exceptions:
 *
 * 1. "Start New Game" now performs a REAL backend action
 *    (POST /api/runs) that switches the shared dev backend's ACTIVE run
 *    — unlike every other test in this whole suite that only ever adds
 *    permanent data (a filed experiment, a registered strategy version),
 *    this one would leave the shared environment's active run pointed
 *    somewhere other than where every other test/manual session expects
 *    it. So this file captures the active run before any test that
 *    creates one, and restores it via a real POST /api/runs/{id}/activate
 *    call afterward — every test leaves the shared backend's ACTIVE run
 *    exactly where it found it, even though (like every other real
 *    artifact this whole suite creates) the new run itself is never
 *    deleted and stays permanently in the run registry — there is no
 *    delete/archive capability, by design.
 * 2. One test needs the genuine "no run is currently active" precondition
 *    (a failed GET /api/runs/active), which isn't otherwise reachable
 *    against this suite's shared, always-on dev backend — it uses
 *    `page.route()` to simulate exactly that one real failure, the same
 *    real code path MainMenuScene.activeRunDayWorthProtecting()'s own
 *    `catch` already handles.
 *
 * IMPORTANT — repeated test runs (and this feature's own live-verification
 * work) accumulate real, permanent runs in the shared dev database over
 * time (no delete capability, by design). helpers.ts's own
 * clickContinueOnTitleScreen() was updated alongside this feature to
 * handle BOTH real Continue outcomes (direct entry, or a run picker
 * requiring "Original Run" to be chosen) — every other spec file in this
 * whole suite also calls it, so fixing it centrally there (rather than
 * duplicating a fix locally here) is what keeps the entire existing
 * suite working now that "exactly one run" can no longer be assumed
 * against this shared environment. The single-run code path itself is
 * still covered by backend/tests/test_runs.py's own isolated unit tests.
 */

/** New Game is the FIRST title-screen button, at (width/2, height*0.5) —
 * see MainMenuScene.ts's own layout math (Continue is the same x, +44). */
async function clickNewGameOnTitleScreen(page: Page): Promise<void> {
  const canvas = page.locator("canvas");
  await expect(canvas).toBeVisible();
  await page.waitForTimeout(800);
  const box = await canvas.boundingBox();
  if (!box) throw new Error("clickNewGameOnTitleScreen: canvas has no bounding box");
  await page.mouse.click(box.x + box.width / 2, box.y + box.height * 0.5);
}

async function currentActiveRunId(page: Page): Promise<string | null> {
  return page.evaluate(async () => {
    const res = await fetch("/api/runs/active");
    const data = (await res.json()) as { runId: string } | null;
    return data ? data.runId : null;
  });
}

async function currentDay(page: Page): Promise<number> {
  return page.evaluate(async () => (await (await fetch("/api/load")).json()).time.day);
}

/** Restores the shared dev backend's active run to whatever it was
 * before a test that created/activated a different one — a real
 * POST /api/runs/{id}/activate call, the same endpoint the app itself
 * uses, not a shortcut around it. */
async function restoreActiveRun(page: Page, runId: string | null): Promise<void> {
  if (runId === null) return;
  await page.evaluate(async (id) => {
    await fetch(`/api/runs/${encodeURIComponent(id)}/activate`, { method: "POST" });
  }, runId);
}

test("New Game with an existing run (Day > 1) shows a real confirmation dialog naming the real current day", async ({ page }) => {
  await page.goto("/");
  await clickNewGameOnTitleScreen(page);

  // The real running dev backend's active run is well past Day 1 (this
  // suite's own sim clock has been ticking for hours) — a real
  // confirmation is expected.
  await expect(page.getByText("Start a new game?", { exact: true })).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/You currently have a run at Day \d+/)).toBeVisible();
  await expect(page.getByRole("button", { name: "START NEW GAME", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Cancel", exact: true })).toBeVisible();

  // Resolve the dialog before the test ends (Cancel) — leaving it
  // unresolved would leave MainMenuScene's own pending confirmation
  // promise dangling into whatever happens next on this page.
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByText("Start a new game?", { exact: true })).not.toBeVisible();
});

test("Cancel leaves the active run completely unchanged and fires no mutating request", async ({ page }) => {
  await page.goto("/");
  const before = await currentDay(page);

  // Tracked only across the New Game -> confirm-dialog -> Cancel round trip
  // itself, not page-load bootstrap or the later Continue click, so this
  // stays a precise claim about the Cancel flow specifically.
  const mutatingRequests: string[] = [];
  const track = (req: Request) => {
    if (req.method() !== "GET" && req.url().includes("/api/")) mutatingRequests.push(`${req.method()} ${req.url()}`);
  };
  page.on("request", track);

  await clickNewGameOnTitleScreen(page);
  await expect(page.getByText("Start a new game?", { exact: true })).toBeVisible({ timeout: 10_000 });

  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByText("Start a new game?", { exact: true })).not.toBeVisible();
  page.off("request", track);

  expect(mutatingRequests).toEqual([]); // Cancel — and the confirmation flow itself — never sent a single non-GET request

  // Still on the title screen — Continue should work exactly as normal,
  // proving Cancel didn't leave MainMenuScene in a broken/half-transitioned state.
  await clickContinueOnTitleScreen(page);

  const after = await currentDay(page);
  expect(after).toBeGreaterThanOrEqual(before); // the sim clock itself keeps ticking in real time; never goes backward or resets to 1
});

test("Start New Game creates a real, separate Day 1 run — and the original run remains fully recoverable afterward", async ({ page }) => {
  await page.goto("/");
  const originalRunId = await currentActiveRunId(page);
  const originalDay = await currentDay(page);

  await clickNewGameOnTitleScreen(page);
  await expect(page.getByText("Start a new game?", { exact: true })).toBeVisible({ timeout: 10_000 });

  await page.getByRole("button", { name: "START NEW GAME", exact: true }).click();
  await expect(page.getByText("Start a new game?", { exact: true })).not.toBeVisible();
  // Same real success marker every Continue path in this file uses: reaching an in-game scene.
  await expect(page.getByRole("button", { name: "Command ⌁" })).toBeVisible({ timeout: 10_000 });

  // A genuinely new, separate run — not the original one reset in place.
  expect(await currentDay(page)).toBe(1);
  const newRunId = await currentActiveRunId(page);
  expect(newRunId).not.toBe(originalRunId);

  // Restore the shared dev backend to the run it was on before this test,
  // and confirm the original run's real day survived completely untouched.
  await restoreActiveRun(page, originalRunId);
  expect(await currentDay(page)).toBeGreaterThanOrEqual(originalDay);
});

test("New Game with no currently-active run proceeds directly, without any confirmation", async ({ page }) => {
  await page.goto("/");
  const originalRunId = await currentActiveRunId(page);

  // The one deliberate mock in this file — see the module docstring above
  // for why a real "no active run" precondition isn't otherwise reachable
  // against this suite's shared dev backend. Simulates exactly the
  // failure MainMenuScene.activeRunDayWorthProtecting() itself catches.
  await page.route("**/api/runs/active", (route) => route.abort("failed"));

  await clickNewGameOnTitleScreen(page);

  await expect(page.getByText("Start a new game?", { exact: true })).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Command ⌁" })).toBeVisible({ timeout: 10_000 });

  await page.unroute("**/api/runs/active");
  await restoreActiveRun(page, originalRunId);
});

test("Continue with more than one run shows a real run picker naming every real run; choosing the original one restores it", async ({ page }) => {
  // This suite's shared dev database always has more than one run
  // registered by this point (this feature's own live-verification work
  // alone guarantees it, quite apart from the two tests above) — a real
  // precondition, not staged.
  await page.goto("/");
  const originalRunId = await currentActiveRunId(page);

  // Click Continue directly (not clickContinueOnTitleScreen(), which would
  // already resolve the picker on its own — this test needs to inspect
  // the picker itself before choosing).
  const canvas = page.locator("canvas");
  await expect(canvas).toBeVisible();
  await page.waitForTimeout(800);
  const box = await canvas.boundingBox();
  if (!box) throw new Error("canvas has no bounding box");
  await page.mouse.click(box.x + box.width / 2, box.y + box.height * 0.5 + 44);

  await expect(page.getByText("Continue which run?", { exact: true })).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("Original Run", { exact: true })).toBeVisible();

  // Picking "Original Run" both exercises real run selection AND is its
  // own restoration — no separate cleanup call needed for this test.
  await page.getByText("Original Run", { exact: true }).click();

  await expect(page.getByText("Continue which run?", { exact: true })).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Command ⌁" })).toBeVisible({ timeout: 10_000 });
  expect(await currentActiveRunId(page)).toBe(originalRunId);
});

test("Canceling the run picker activates nothing and leaves the player on the title screen", async ({ page }) => {
  await page.goto("/");
  const originalRunId = await currentActiveRunId(page);

  const mutatingRequests: string[] = [];
  const track = (req: Request) => {
    if (req.method() !== "GET" && req.url().includes("/api/")) mutatingRequests.push(`${req.method()} ${req.url()}`);
  };
  page.on("request", track);

  const canvas = page.locator("canvas");
  await expect(canvas).toBeVisible();
  await page.waitForTimeout(800);
  const box = await canvas.boundingBox();
  if (!box) throw new Error("canvas has no bounding box");
  await page.mouse.click(box.x + box.width / 2, box.y + box.height * 0.5 + 44);

  await expect(page.getByText("Continue which run?", { exact: true })).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByText("Continue which run?", { exact: true })).not.toBeVisible();
  page.off("request", track);

  // Never transitioned into any run (the one real, DOM-visible signal a
  // canvas-drawn title screen can offer), and no run-activation call was
  // ever sent.
  await expect(page.getByRole("button", { name: "Command ⌁" })).not.toBeVisible();
  expect(mutatingRequests.some((r) => r.includes("/activate"))).toBe(false);
  expect(await currentActiveRunId(page)).toBe(originalRunId);
});
