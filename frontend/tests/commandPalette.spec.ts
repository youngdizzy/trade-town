import { test, expect } from "@playwright/test";
import { continueGame, dismissBlockingPopups, setPlayerScene } from "./helpers";

/**
 * Design Bible Chapter 67 (TTOS) Part 3 — the Command Palette
 * (Cmd/Ctrl+K). Exercises the real running app: opening via Ctrl+K,
 * filtering, and executing a real "Go to X" command that opens the
 * actual Command Center on that tab — the same
 * "ui:commandCenterJump"/pendingCommandCenterTab plumbing
 * QuickActionDock.tsx already exercises end-to-end.
 */
test.describe("Command Palette", () => {
  test("opens via Ctrl+K, filters to real commands, and executes a real tab jump", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);
    await dismissBlockingPopups(page);

    await expect(page.getByPlaceholder("Type a command…")).toHaveCount(0);
    await page.keyboard.press("Control+k");
    // Scoped to the palette's own container: several of its real command
    // labels ("Save", tab names) legitimately duplicate other
    // always-visible real controls (BottomToolbar's own Save button,
    // etc.) while the palette is open — the same "second correct
    // instance" situation this chapter's GlobalStatusBar/QuickActionDock
    // slices already established, not a bug.
    const palette = page.getByTestId("command-palette");
    const input = page.getByPlaceholder("Type a command…");
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
    await expect(page.getByPlaceholder("Type a command…")).toHaveCount(0);

    // Escape closes the palette without executing anything, when reopened.
    await page.keyboard.press("Escape");
    await page.keyboard.press("Control+k");
    await expect(page.getByPlaceholder("Type a command…")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByPlaceholder("Type a command…")).toHaveCount(0);
  });
});
