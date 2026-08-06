import { test, expect } from "@playwright/test";
import { clickRobust, continueGame, dismissBlockingPopups, setPlayerScene } from "./helpers";

/**
 * Design Bible Chapter 67 (TTOS) Part 3 — the Quick Action Dock.
 * Exercises the real running app: cycling Automation Mode writes through
 * SettingsManager the same way the COMPANY tab's own toggle does, and
 * each quick-jump button opens the real Command Center directly on that
 * tab via the same pendingCommandCenterTab plumbing
 * pendingInspectDecision already established for the Trade Outcome
 * Banner's "View Trade" button.
 */
test.describe("Quick Action Dock", () => {
  test("cycles Automation Mode and jumps straight to a real Command Center tab", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);
    await dismissBlockingPopups(page);

    // The dock's own accessible name is deliberately distinct from its
    // visible mode text (see QuickActionDock.tsx's own doc comment) so
    // it never collides with CompanyPanel's own real Operating Mode
    // buttons, which are always-mounted-adjacent real content, not a
    // test-only concern.
    const automationButton = () => page.getByRole("button", { name: /Cycle Automation Mode/ });
    await expect(automationButton()).toBeVisible();
    await expect(automationButton()).toHaveText("LEARNING");

    // Cycling writes through the same real settings field COMPANY tab's
    // own Operating Mode toggle uses — confirm it actually advances.
    await clickRobust(page, automationButton, { label: "Automation Mode (cycle to Assisted)" });
    await expect(automationButton()).toHaveText("ASSISTED");

    // Quick-jump: clicking "→ Risk" opens the real Command Center
    // directly on the RISK tab, never the default OVERVIEW.
    await clickRobust(page, () => page.getByRole("button", { name: "→ Risk", exact: true }), { label: "Jump to Risk" });
    await dismissBlockingPopups(page);
    await expect(page.getByText("COMMAND CENTER", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "RISK", exact: true })).toHaveClass(/text-cmd-cyan/);
    await page.keyboard.press("Escape");

    // A second jump, to a different tab, still lands correctly — proves
    // this isn't a one-shot fluke of the first click.
    await clickRobust(page, () => page.getByRole("button", { name: "→ Company Health", exact: true }), { label: "Jump to Company Health" });
    await dismissBlockingPopups(page);
    await expect(page.getByRole("button", { name: "COMPANY", exact: true })).toHaveClass(/text-cmd-cyan/);
  });
});
