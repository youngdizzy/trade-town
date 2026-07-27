import { test, expect, type Page } from "@playwright/test";

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
 */

async function setPlayerScene(page: Page, scene: string, x: number, y: number): Promise<void> {
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

async function continueGame(page: Page): Promise<void> {
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

async function enableDebugOverlay(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Settings" }).click();
  const checkbox = page.getByRole("checkbox");
  if (!(await checkbox.isChecked())) await checkbox.check();
  await page.getByRole("button", { name: "Close" }).click();
}

/** Reads DebugOverlay's live "FPS — Scene (x, y)" readout. */
async function readDebug(page: Page): Promise<{ scene: string; x: number; y: number }> {
  const text = await page.locator("text=/FPS — /").textContent();
  const match = text?.match(/FPS — (\S+) \((-?\d+), (-?\d+)\)/);
  if (!match) throw new Error(`could not parse debug overlay: ${text}`);
  return { scene: match[1]!, x: Number(match[2]), y: Number(match[3]) };
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

    await page.getByRole("button", { name: "Command ⌁" }).click();
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toBeVisible();

    const after = await readDebug(page);
    expect(after).toEqual(before);

    await page.getByRole("button", { name: "CLOSE" }).click();
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toHaveCount(0);
  });

  test("blocks world interaction while open: movement keys don't move the player", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);
    await enableDebugOverlay(page);

    await page.keyboard.press("Tab");
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toBeVisible();
    const frozen = await readDebug(page);

    // Hold movement keys with the overlay open — the world must stay inert.
    for (const key of ["d", "d", "d", "s", "s", "s"]) {
      await page.keyboard.press(key);
      await page.waitForTimeout(30);
    }
    const stillFrozen = await readDebug(page);
    expect(stillFrozen).toEqual(frozen);

    await page.keyboard.press("Escape");

    // Sanity check: the same keys DO move the player once the overlay is closed.
    for (const key of ["d", "d", "d", "d", "d", "d"]) {
      await page.keyboard.press(key);
      await page.waitForTimeout(30);
    }
    const moved = await readDebug(page);
    expect(moved.x).not.toBe(frozen.x);
  });

  test("expands to the Full Command Center and renders all 9 tabs with graceful empty states", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: /EXPAND/ }).click();

    const tabs = ["OVERVIEW", "OPPORTUNITIES", "DECISIONS", "RISK", "AGENTS", "RESEARCH", "TRAINING", "PERFORMANCE", "LOGS"];
    for (const tab of tabs) {
      await page.getByRole("button", { name: tab, exact: true }).click();
      await expect(page.getByRole("button", { name: tab, exact: true })).toHaveClass(/text-cmd-cyan/);
    }

    // The backend keeps ticking in real time across this whole test file,
    // so by this point it may honestly have accumulated real decisions —
    // either way the panel must render something truthful, never a blank
    // screen: either real opportunity cards, or the explicit empty state.
    await page.getByRole("button", { name: "OPPORTUNITIES", exact: true }).click();
    await expect(page.getByText(/No opportunities evaluated yet/).or(page.locator("text=/% confidence/").first())).toBeVisible();

    await page.getByRole("button", { name: "RISK", exact: true }).click();
    await expect(page.getByText(/NORMAL|ELEVATED|RESTRICTED/)).toBeVisible();

    await page.getByRole("button", { name: "AGENTS", exact: true }).click();
    await expect(page.getByText("Atlas").first()).toBeVisible();

    await page.getByRole("button", { name: "QUICK VIEW", exact: true }).click();
    await expect(page.getByText("Quick View")).toBeVisible();
  });

  test("renders a real candlestick chart on Overview, labeled SIMULATED, with working timeframe switching", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await page.getByRole("button", { name: /EXPAND/ }).click();
    await expect(page.getByText("Market Chart")).toBeVisible();

    // Never claim simulated data is live — the badge must say so explicitly.
    await expect(page.getByText("SIMULATED")).toBeVisible();

    const chartCanvas = page.locator("canvas").nth(1); // canvas 0 is the Phaser game itself
    await expect(chartCanvas).toBeVisible();
    const before = await chartCanvas.screenshot();

    await page.getByRole("button", { name: "1d", exact: true }).click();
    await page.waitForTimeout(500);
    const after = await chartCanvas.screenshot();
    expect(Buffer.compare(before, after)).not.toBe(0); // switching timeframe actually redraws different data
  });

  test("Agent Energy widget spends real energy for a real effect (watch_symbol) via POST /api/energy/spend", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await page.getByRole("button", { name: /EXPAND/ }).click();
    const widget = page.getByTestId("agent-energy-widget");
    await expect(widget).toBeVisible();

    const readEnergy = async () => {
      const text = await widget.getByText(/^\d+ \/ \d+$/).innerText();
      return Number(text.split(" / ")[0]);
    };
    const before = await readEnergy();

    const watchButton = widget.getByRole("button", { name: /Watch New Symbol/ });
    await expect(watchButton).toBeEnabled();
    await watchButton.click();

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
    await page.getByRole("button", { name: /EXPAND/ }).click();
    await page.getByRole("button", { name: "TRAINING", exact: true }).click();

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
});
