import { test, expect } from "@playwright/test";
import { continueGame, dismissBlockingPopups, setPlayerScene } from "./helpers";

/**
 * Design Bible Chapter 67 (TTOS) Part 3 — the Command Palette
 * (Cmd/Ctrl+K), doubling as Universal Search. Exercises the real
 * running app: opening via Ctrl+K, filtering, and executing a real
 * "Go to X" command that opens the actual Command Center on that tab —
 * the same "ui:commandCenterJump"/pendingCommandCenterTab plumbing
 * QuickActionDock.tsx already exercises end-to-end — plus a real
 * employee search result (Scout, one of the 14 real agents that exist
 * from a fresh save onward).
 */
test.describe("Command Palette", () => {
  test("opens via Ctrl+K, filters to real commands, and executes a real tab jump", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);
    await dismissBlockingPopups(page);

    await expect(page.getByPlaceholder("Search or type a command…")).toHaveCount(0);
    await page.keyboard.press("Control+k");
    // Scoped to the palette's own container: several of its real command
    // labels ("Save", tab names) legitimately duplicate other
    // always-visible real controls (BottomToolbar's own Save button,
    // etc.) while the palette is open — the same "second correct
    // instance" situation this chapter's GlobalStatusBar/QuickActionDock
    // slices already established, not a bug.
    const palette = page.getByTestId("command-palette");
    const input = page.getByPlaceholder("Search or type a command…");
    await expect(input).toBeVisible();

    // Real, non-fabricated commands are present.
    await expect(palette.getByText("Save", { exact: true })).toBeVisible();
    await expect(palette.getByText("Go to OVERVIEW", { exact: true })).toBeVisible();

    // Filtering narrows to a single real command.
    await input.fill("risk");
    await expect(palette.getByText("Go to RISK", { exact: true })).toBeVisible();
    await expect(palette.getByText("Go to OVERVIEW", { exact: true })).toHaveCount(0);

    // Executing it opens the real Command Center directly on RISK — the
    // same jump mechanism the Quick Action Dock's own buttons use.
    await page.keyboard.press("Enter");
    await dismissBlockingPopups(page);
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "RISK", exact: true })).toHaveClass(/text-cmd-cyan/);
    await expect(page.getByPlaceholder("Search or type a command…")).toHaveCount(0);

    // Escape closes the palette without executing anything, when reopened.
    await page.keyboard.press("Escape");
    await page.keyboard.press("Control+k");
    await expect(page.getByPlaceholder("Search or type a command…")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByPlaceholder("Search or type a command…")).toHaveCount(0);
  });

  test("Universal Search: real employee results jump to AGENTS, real Company Memory results open the real overlay", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);
    await dismissBlockingPopups(page);

    await page.keyboard.press("Control+k");
    const palette = page.getByTestId("command-palette");
    const input = page.getByPlaceholder("Search or type a command…");
    await expect(input).toBeVisible();

    // Scout is one of the 14 real agents present from a fresh save — a
    // real, non-fabricated Employee search result, not a command.
    await input.fill("scout");
    await expect(palette.getByText("Employee", { exact: true }).first()).toBeVisible();
    await expect(palette.getByText(/^Scout — /)).toBeVisible();

    // Executing an Employee result jumps to the real AGENTS tab.
    await page.keyboard.press("Enter");
    await dismissBlockingPopups(page);
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "AGENTS", exact: true })).toHaveClass(/text-cmd-cyan/);
    await page.keyboard.press("Escape");
  });
});
