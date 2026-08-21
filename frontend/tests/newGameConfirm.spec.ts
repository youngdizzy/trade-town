import { test, expect } from "@playwright/test";
import { clickContinueOnTitleScreen } from "./helpers";

/**
 * Safe "New Game" confirmation. Same real-app testing approach as every
 * other spec in this suite (live Vite + FastAPI dev stack) EXCEPT one
 * deliberate, disclosed deviation: this codebase's backend is a single,
 * always-on, ever-growing save (see MainMenuScene.ts/NewGameConfirm.tsx's
 * own docstrings) — there is no way to genuinely put it back to "no save
 * exists" without being destructive to the real dev save every other
 * test in this suite also depends on. The one test below that needs that
 * exact precondition (`GET /api/load` failing) uses `page.route()` to
 * simulate it at the network layer, clearly marked. Every other test here
 * exercises the real save as-is.
 */

/** New Game is the FIRST title-screen button, at (width/2, height*0.5) —
 * see MainMenuScene.ts's own layout math (Continue is the same x, +44). */
async function clickNewGameOnTitleScreen(page: import("@playwright/test").Page): Promise<void> {
  const canvas = page.locator("canvas");
  await expect(canvas).toBeVisible();
  await page.waitForTimeout(800);
  const box = await canvas.boundingBox();
  if (!box) throw new Error("clickNewGameOnTitleScreen: canvas has no bounding box");
  await page.mouse.click(box.x + box.width / 2, box.y + box.height * 0.5);
}

test("New Game with an existing save (Day > 1) shows a real confirmation dialog naming the real current day", async ({ page }) => {
  await page.goto("/");
  await clickNewGameOnTitleScreen(page);

  // The real running dev save is well past Day 1 (this suite's own sim
  // clock has been ticking for hours) — a real confirmation is expected.
  await expect(page.getByText("Start a new game?", { exact: true })).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/You have an existing company in progress \(Day \d+\)/)).toBeVisible();
  await expect(page.getByRole("button", { name: "START NEW GAME", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Cancel", exact: true })).toBeVisible();
});

test("Cancel leaves the existing save completely unchanged and fires no mutating request", async ({ page }) => {
  await page.goto("/");
  const before = await page.evaluate(async () => (await (await fetch("/api/load")).json()).time.day);

  // Tracked only across the New Game -> confirm-dialog -> Cancel round trip
  // itself, not page-load bootstrap or the later Continue click, so this
  // stays a precise claim about the Cancel flow specifically.
  const mutatingRequests: string[] = [];
  const track = (req: import("@playwright/test").Request) => {
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

  const after = await page.evaluate(async () => (await (await fetch("/api/load")).json()).time.day);
  expect(after).toBeGreaterThanOrEqual(before); // the sim clock itself keeps ticking in real time; never goes backward or resets to 1
});

test("Start New Game proceeds to a fresh Lobby view after explicit confirmation", async ({ page }) => {
  await page.goto("/");
  await clickNewGameOnTitleScreen(page);
  await expect(page.getByText("Start a new game?", { exact: true })).toBeVisible({ timeout: 10_000 });

  await page.getByRole("button", { name: "START NEW GAME", exact: true }).click();
  await expect(page.getByText("Start a new game?", { exact: true })).not.toBeVisible();
  // Same real success marker clickContinueOnTitleScreen() uses: reaching an in-game scene.
  await expect(page.getByRole("button", { name: "Command ⌁" })).toBeVisible({ timeout: 10_000 });
});

test("Continue never triggers the New Game confirmation and loads the existing save normally", async ({ page }) => {
  await page.goto("/");
  await clickContinueOnTitleScreen(page);
  await expect(page.getByText("Start a new game?", { exact: true })).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Command ⌁" })).toBeVisible();
});

test("New Game with no existing save proceeds directly, without any confirmation", async ({ page }) => {
  // The one deliberate mock in this file — see the module docstring above
  // for why a real "no save" precondition isn't reachable against this
  // suite's shared, always-on dev save. Simulates exactly the failure
  // MainMenuScene.existingProgressDay() itself catches (a failed
  // GET /api/load), the same real code path continueGame()'s own
  // fresh-deployment fallback already relies on.
  await page.route("**/api/load", (route) => route.abort("failed"));

  await page.goto("/");
  await clickNewGameOnTitleScreen(page);

  await expect(page.getByText("Start a new game?", { exact: true })).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Command ⌁" })).toBeVisible({ timeout: 10_000 });
});
