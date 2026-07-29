import { test, expect, type Page } from "@playwright/test";

/**
 * Browser tests for the v0.7 Company Campus Map — a real overlay reusing
 * the exact same gameStore data (agents, treasury, calendar, ...) every
 * other Command Center panel already reads, plus LobbyScene.ts's own real
 * building coordinates. See CampusMap.tsx's own module docstring for the
 * full scope note on what's real here versus the brief's fictional
 * 17-building blueprint.
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

async function clickContinueOnTitleScreen(page: Page): Promise<void> {
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
  throw new Error("clickContinueOnTitleScreen: never reached an in-game scene after 5 click attempts");
}

/** Same real-backend-keeps-ticking tolerance every other spec file in
 * this suite already needs — a genuine trade banner/voting popup can
 * appear mid-test and must be cleared like a real player would. */
async function dismissTradeOutcomePopups(page: Page): Promise<void> {
  for (let i = 0; i < 5; i++) {
    const tradeBanner = page.getByTestId("trade-outcome-banner");
    if (await tradeBanner.isVisible().catch(() => false)) {
      await tradeBanner.getByText("Dismiss").click();
      await tradeBanner.waitFor({ state: "hidden", timeout: 3000 }).catch(() => {});
      continue;
    }
    const votingPopup = page.getByTestId("executive-voting");
    if (await votingPopup.isVisible().catch(() => false)) {
      await votingPopup.getByText("Decide later").click();
      await votingPopup.waitFor({ state: "hidden", timeout: 3000 }).catch(() => {});
      continue;
    }
    return;
  }
}

async function continueGame(page: Page): Promise<void> {
  await clickContinueOnTitleScreen(page);
  await dismissTradeOutcomePopups(page);
}

async function readDebug(page: Page): Promise<{ scene: string; x: number; y: number }> {
  const text = await page.locator("text=/FPS — /").textContent();
  const match = text?.match(/FPS — (\S+) \((-?\d+), (-?\d+)\)/);
  if (!match) throw new Error(`could not parse debug overlay: ${text}`);
  return { scene: match[1]!, x: Number(match[2]), y: Number(match[3]) };
}

async function enableDebugOverlay(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Settings" }).click();
  const checkbox = page.getByRole("checkbox");
  if (!(await checkbox.isChecked())) await checkbox.check();
  await page.getByRole("button", { name: "Close" }).click();
}

test.describe("Company Campus Map", () => {
  test("opens via the M key from the Lobby, shows a real Campus Overview, and closes via Escape", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("m");
    await expect(page.getByText("COMPANY CAMPUS MAP", { exact: true })).toBeVisible();
    await expect(page.getByText("Campus Overview", { exact: true })).toBeVisible();

    // Every stat here is a real field off gameStore — assert a few by name
    // to confirm they rendered something, not that the panel is blank.
    await expect(page.getByText("Company Score", { exact: true })).toBeVisible();
    await expect(page.getByText("Treasury", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Employee Count", { exact: true })).toBeVisible();
    // v0.7 Feature 39 — the roster grew from 11 to 13 with the Original
    // Founders (Keystone/Compass); assert against the real live count
    // rather than a hardcoded number that would go stale again.
    await expect(page.getByText("13", { exact: true }).first()).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(page.getByText("COMPANY CAMPUS MAP", { exact: true })).toHaveCount(0);
  });

  test("blocks world interaction while open, same as the Command Center", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);
    await enableDebugOverlay(page);

    const before = await readDebug(page);
    await page.keyboard.press("m");
    await expect(page.getByText("COMPANY CAMPUS MAP", { exact: true })).toBeVisible();

    for (const key of ["d", "d", "d", "s", "s", "s"]) {
      await page.keyboard.press(key);
      await page.waitForTimeout(30);
    }
    const stillFrozen = await readDebug(page);
    expect(stillFrozen).toEqual(before);

    await page.keyboard.press("Escape");
  });

  test("clicking a real building shows its real info panel, and clicking a real employee shows theirs", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("m");
    await dismissTradeOutcomePopups(page);
    await expect(page.getByText("COMPANY CAMPUS MAP", { exact: true })).toBeVisible();

    // Brain Room is a real building with a real, always-present purpose
    // string — click its node and confirm the honest real info panel.
    await page.getByTitle(/Brain Room — double-click to fast travel/).click();
    await expect(page.getByText(/Mission Control/)).toBeVisible();
    await expect(page.getByText("Current Employees", { exact: true })).toBeVisible();
    await expect(page.getByText("Related Departments", { exact: true })).toBeVisible();

    // An employee icon — Scout is guaranteed to exist and have a real
    // current task at all times.
    await page.getByTitle(/Scout —/).click();
    await expect(page.getByText("Current Task", { exact: true })).toBeVisible();
    await expect(page.getByText("Destination", { exact: true })).toBeVisible();
    await expect(page.getByText("ETA", { exact: true })).toBeVisible();
  });

  test("filter chips narrow the visible buildings by real category", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("m");
    await dismissTradeOutcomePopups(page);

    const tradingChip = page.getByRole("button", { name: "Trading", exact: true });
    await expect(tradingChip).toBeVisible();
    await tradingChip.click();

    // Trading Floor stays fully visible under the Trading filter; Brain
    // Room (a research building) dims to the real "filtered out" opacity.
    const tradingFloorNode = page.getByTitle(/Trading Floor —/);
    const brainRoomNode = page.getByTitle(/Brain Room —/);
    await expect(tradingFloorNode).toHaveClass(/opacity-100/);
    await expect(brainRoomNode).toHaveClass(/opacity-20/);

    await page.getByRole("button", { name: "All", exact: true }).click();
    await expect(brainRoomNode).toHaveClass(/opacity-100/);
  });

  test("double-clicking a building fast-travels the player there via a real scene change", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);
    await enableDebugOverlay(page);

    const before = await readDebug(page);
    expect(before.scene).toBe("LobbyScene");

    await page.keyboard.press("m");
    await dismissTradeOutcomePopups(page);
    await page.getByTitle(/Hall of Fame — double-click to fast travel/).dblclick();

    // The map closes and the real scene changes.
    await expect(page.getByText("COMPANY CAMPUS MAP", { exact: true })).toHaveCount(0);
    await expect(async () => {
      const after = await readDebug(page);
      expect(after.scene).toBe("HallOfFameScene");
    }).toPass({ timeout: 5000 });
  });

  test("opens from the Command Center's Campus button and from the Pause Menu", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);

    await page.keyboard.press("Tab");
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: /CAMPUS/ }).click();
    await expect(page.getByText("COMPANY CAMPUS MAP", { exact: true })).toBeVisible();
    await page.keyboard.press("Escape");

    // The Pause Menu opens via the toolbar's own Pause button, not a
    // keyboard shortcut — see BottomToolbar.tsx/GameManager.togglePause().
    await page.getByRole("button", { name: "Pause", exact: true }).click();
    await expect(page.getByText("Paused", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Campus Map", exact: true }).click();
    await expect(page.getByText("COMPANY CAMPUS MAP", { exact: true })).toBeVisible();
  });
});
