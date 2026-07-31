import { test, expect } from "@playwright/test";
import { clickButton, clickRobust, continueGame, dismissBlockingPopups, enableDebugOverlay, readDebug, setPlayerScene } from "./helpers";

/**
 * Browser tests for the v0.7 Company Campus Map — a real overlay reusing
 * the exact same gameStore data (agents, treasury, calendar, ...) every
 * other Command Center panel already reads, plus LobbyScene.ts's own real
 * building coordinates. See CampusMap.tsx's own module docstring for the
 * full scope note on what's real here versus the brief's fictional
 * 17-building blueprint.
 */

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
    // The roster has grown several times since this game shipped (most
    // recently with the CIO and Quant hires) — assert against the real
    // live agent count rather than a hardcoded number that goes stale
    // every time a new agent joins.
    const state = await page.evaluate(async () => {
      const res = await fetch("/api/load");
      return res.json();
    });
    const employeeCount = Object.keys(state.agents).length;
    await expect(page.getByText(String(employeeCount), { exact: true }).first()).toBeVisible();

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
    await dismissBlockingPopups(page);
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
    await dismissBlockingPopups(page);

    const tradingChip = page.getByRole("button", { name: "Trading", exact: true });
    await expect(tradingChip).toBeVisible();
    await clickRobust(page, () => page.getByRole("button", { name: "Trading", exact: true }), { label: "Trading filter chip" });

    // Trading Floor stays fully visible under the Trading filter; Brain
    // Room (a research building) dims to the real "filtered out" opacity.
    const tradingFloorNode = page.getByTitle(/Trading Floor —/);
    const brainRoomNode = page.getByTitle(/Brain Room —/);
    await expect(tradingFloorNode).toHaveClass(/opacity-100/);
    await expect(brainRoomNode).toHaveClass(/opacity-20/);

    await clickRobust(page, () => page.getByRole("button", { name: "All", exact: true }), { label: "All filter chip" });
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
    await dismissBlockingPopups(page);
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
    await clickButton(page, /CAMPUS/);
    await expect(page.getByText("COMPANY CAMPUS MAP", { exact: true })).toBeVisible();
    await page.keyboard.press("Escape");

    // The Pause Menu opens via the toolbar's own Pause button, not a
    // keyboard shortcut — see BottomToolbar.tsx/GameManager.togglePause().
    await clickButton(page, "Pause");
    await expect(page.getByText("Paused", { exact: true })).toBeVisible();
    await clickButton(page, "Campus Map");
    await expect(page.getByText("COMPANY CAMPUS MAP", { exact: true })).toBeVisible();
  });
});
