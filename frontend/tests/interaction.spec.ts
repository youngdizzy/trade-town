import { test, expect, type Page } from "@playwright/test";

/**
 * v0.7 — Input Priority fix, Part 2: "Press E to Talk" and the underlying
 * interaction system (proximity detection, the E key, real dialogue) —
 * all of which already worked, just with no on-screen discoverability
 * prompt (see RoomScene.ts's `setInteractionPrompt()`/`nearestAgent()`).
 *
 * Agent locations are real, live, schedule-driven state on this shared
 * dev backend (backend/app/schedule.py) — which room actually has anyone
 * in it changes over time and isn't something a test can dictate. Rather
 * than assume a specific room is populated, this queries the real
 * GET /api/load agent locations first and walks into whichever populated
 * room is currently real, so the test stays honest instead of pinning to
 * a room that might be empty by the time it runs.
 */

// AgentLocation -> the RoomScene subclass that renders it (see each
// scene's own `agentLocation` field) and its real room dimensions (see
// each scene's own `widthTiles`/`heightTiles`, all in 16px tiles) — used
// only to walk toward the room's rough center; the exact seat/spawn
// formula differs per room and per how many agents are present, so the
// test sweeps a small area around center rather than requiring an exact
// coordinate match.
const TILE_SIZE = 16;
const POPULATED_ROOMS: Record<string, { scene: string; widthPx: number; heightPx: number }> = {
  "brain-room": { scene: "BrainRoomScene", widthPx: 18 * TILE_SIZE, heightPx: 12 * TILE_SIZE },
  "break-room": { scene: "BreakRoomScene", widthPx: 12 * TILE_SIZE, heightPx: 9 * TILE_SIZE },
  "meeting-room": { scene: "MeetingRoomScene", widthPx: 15 * TILE_SIZE, heightPx: 11 * TILE_SIZE },
  "scout-office": { scene: "ScoutOfficeScene", widthPx: 14 * TILE_SIZE, heightPx: 10 * TILE_SIZE },
  "trading-floor": { scene: "TradingFloorScene", widthPx: 22 * TILE_SIZE, heightPx: 15 * TILE_SIZE },
  "executive-boardroom": { scene: "ExecutiveBoardroomScene", widthPx: 34 * TILE_SIZE, heightPx: 22 * TILE_SIZE },
  "simulation-lab": { scene: "SimulationLabScene", widthPx: 17 * TILE_SIZE, heightPx: 11 * TILE_SIZE },
  "performance-center": { scene: "PerformanceCenterScene", widthPx: 15 * TILE_SIZE, heightPx: 13 * TILE_SIZE },
  "hall-of-fame": { scene: "HallOfFameScene", widthPx: 17 * TILE_SIZE, heightPx: 11 * TILE_SIZE },
};

async function findPopulatedRoom(page: Page): Promise<{ scene: string; x: number; y: number }> {
  const state = await page.evaluate(async () => {
    const res = await fetch("/api/load");
    return res.json();
  });
  for (const agent of Object.values(state.agents) as { location: string }[]) {
    const room = POPULATED_ROOMS[agent.location];
    if (room) return { scene: room.scene, x: room.widthPx / 2, y: room.heightPx / 2 };
  }
  throw new Error("findPopulatedRoom: no agent is currently in any RoomScene-backed location — nothing to walk toward");
}

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

const PROMPT_PATTERN = /Talk to/;

/** Walks the player in a small ring around their current position,
 * checking for the "Press E to Talk" prompt after each step, since the
 * exact per-room seat/spawn formula (different for every room, and
 * dependent on how many agents are currently present) isn't worth
 * duplicating here just to land on one exact pixel. */
async function sweepForPrompt(page: Page): Promise<void> {
  const moves: string[][] = [
    ["s", "s"],
    ["d", "d"],
    ["s", "s"],
    ["a", "a", "a", "a"],
    ["w", "w", "w", "w"],
    ["d", "d", "d", "d"],
  ];
  for (const step of moves) {
    if (await page.getByText(PROMPT_PATTERN).isVisible().catch(() => false)) return;
    for (const key of step) {
      await page.keyboard.press(key);
      await page.waitForTimeout(40);
    }
  }
  await expect(page.getByText(PROMPT_PATTERN)).toBeVisible({ timeout: 2000 });
}

test.describe("Press E to Talk", () => {
  test("shows a real agent's name near them, and E opens real dialogue", async ({ page }) => {
    await page.goto("/");
    const room = await findPopulatedRoom(page);
    await setPlayerScene(page, room.scene, room.x, room.y);
    await clickContinueOnTitleScreen(page);

    await sweepForPrompt(page);
    const promptText = await page.getByText(PROMPT_PATTERN).textContent();
    expect(promptText).toMatch(/Talk to \S+/); // a real agent name, not a placeholder

    await page.keyboard.press("e");
    // DialogueBox renders the real agent's name as the speaker, and a real line.
    const dialogueSpeaker = page.locator("div.text-gold").first();
    await expect(dialogueSpeaker).toBeVisible({ timeout: 3000 });
    const speakerText = await dialogueSpeaker.textContent();
    expect(speakerText?.trim().length).toBeGreaterThan(0);

    // Close it out — Space/Enter/E all advance/close (DialogueBox.tsx).
    for (let i = 0; i < 6; i++) {
      if (!(await page.getByText(PROMPT_PATTERN).isVisible().catch(() => false)) && (await dialogueSpeaker.isVisible().catch(() => false)) === false) break;
      await page.keyboard.press("Space");
      await page.waitForTimeout(150);
    }
  });

  test("clears once the Command Center opens, and interaction stays suppressed until it closes", async ({ page }) => {
    await page.goto("/");
    const room = await findPopulatedRoom(page);
    await setPlayerScene(page, room.scene, room.x, room.y);
    await clickContinueOnTitleScreen(page);

    await sweepForPrompt(page);
    await expect(page.getByText(PROMPT_PATTERN)).toBeVisible();

    // v0.7 — Input Priority fix: opening the Command Center suppresses
    // interaction (worldActive), and the prompt must clear with it — a
    // stale prompt would otherwise show an agent E can no longer reach.
    await page.keyboard.press("Tab");
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toBeVisible();
    await expect(page.getByText(PROMPT_PATTERN)).toHaveCount(0);

    await page.keyboard.press("Escape");
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toHaveCount(0);

    // Interaction resumes normally once fully closed. Re-sweep rather than
    // asserting the prompt reappears instantly at the exact same spot —
    // agent locations are real, live, schedule-driven state (this is the
    // same reasoning findPopulatedRoom() above is built on), and enough
    // real time passed opening/closing the Command Center that the agent
    // may genuinely have moved on to their next scheduled activity.
    await sweepForPrompt(page);
    await expect(page.getByText(PROMPT_PATTERN)).toBeVisible();
  });
});
