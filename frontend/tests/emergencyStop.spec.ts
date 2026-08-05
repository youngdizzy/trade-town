import { test, expect } from "@playwright/test";
import { clickRobust, continueGame, dismissBlockingPopups, setPlayerScene } from "./helpers";

/**
 * Design Bible Chapter 67 (TTOS) Part 3 — the real Global Emergency
 * Stop. Exercises the actual running app against the real backend
 * (POST /api/emergency-stop/activate and /resume), not a mock — see
 * ./helpers.ts's own doc comment for why real gameplay popups can
 * appear mid-test and how dismissing them is handled.
 */
test.describe("Global Emergency Stop", () => {
  test("button visible from anywhere, requires confirmation, activates and resumes for real", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);
    await dismissBlockingPopups(page);

    const stopButton = () => page.getByRole("button", { name: "EMERGENCY STOP" });
    await expect(stopButton()).toBeVisible();

    // Clicking opens a confirmation — it does not activate immediately.
    await clickRobust(page, stopButton, { label: "Emergency Stop button (open dialog)" });
    await expect(page.getByText("Activate Emergency Stop?")).toBeVisible();

    // Cancelling leaves trading unaffected.
    await clickRobust(page, () => page.getByRole("button", { name: "Cancel" }), { label: "Cancel" });
    await expect(page.getByText("Activate Emergency Stop?")).toHaveCount(0);
    await expect(stopButton()).toBeVisible();

    // Confirming really activates it via the real endpoint.
    await clickRobust(page, stopButton, { label: "Emergency Stop button (activate)" });
    await clickRobust(page, () => page.getByRole("button", { name: "ACTIVATE EMERGENCY STOP" }), { label: "ACTIVATE EMERGENCY STOP" });

    const resumeButton = () => page.getByRole("button", { name: /EMERGENCY.*RESUME TRADING/ });
    await expect(resumeButton()).toBeVisible();

    // Still visible from inside the Command Center — never lives in a tab.
    await page.keyboard.press("Tab");
    await dismissBlockingPopups(page);
    await expect(resumeButton()).toBeVisible();
    await page.keyboard.press("Escape");

    // Resuming also requires confirmation, and lifts the halt for real.
    await clickRobust(page, resumeButton, { label: "Resume button (open dialog)" });
    await expect(page.getByText("Resume trading?")).toBeVisible();
    await clickRobust(page, () => page.getByRole("button", { name: "RESUME TRADING", exact: true }), { label: "RESUME TRADING" });
    await expect(stopButton()).toBeVisible();
  });
});
