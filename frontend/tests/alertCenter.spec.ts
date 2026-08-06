import { test, expect } from "@playwright/test";
import { clickRobust, continueGame, dismissBlockingPopups, setPlayerScene } from "./helpers";

/**
 * Design Bible Chapter 67 (TTOS) Part 3 — Smart Notification priority
 * tiers + the Executive Alert Center. Exercises the real running app: a
 * real critical event (Emergency Stop activation, via the same real
 * POST /api/emergency-stop/activate endpoint emergencyStop.spec.ts
 * exercises) produces a sticky, non-auto-dismissing toast, and every
 * toast this session produces (critical or not) is recorded into the
 * real Alert Center overlay, opened here via the Command Palette's own
 * "Open Alert Center" command — not a second Ctrl+K-shaped surface.
 */
test.describe("Smart Notification tiers + Executive Alert Center", () => {
  test("Emergency Stop produces a sticky critical toast, and the Alert Center records real history", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);
    await dismissBlockingPopups(page);

    // Activate the real Emergency Stop.
    await clickRobust(page, () => page.getByRole("button", { name: "EMERGENCY STOP" }), { label: "Emergency Stop button (open dialog)" });
    await clickRobust(page, () => page.getByRole("button", { name: "ACTIVATE EMERGENCY STOP" }), { label: "ACTIVATE EMERGENCY STOP" });

    // A sticky, critical-tier toast appears — distinct styling from the
    // normal-tier toasts (border-cmd-red + animate-pulse vs. cmd-cyan).
    const toast = page.getByText("EMERGENCY STOP ACTIVATED", { exact: true });
    await expect(toast).toBeVisible();

    // Still visible well past the 6s auto-dismiss window every other
    // toast kind uses — this is the "sticky" behavior CyberNotifications
    // reserves for tier "critical".
    await page.waitForTimeout(7000);
    await expect(toast).toBeVisible();

    // Open the real Alert Center via the Command Palette, not a second
    // overlay-triggering surface.
    await page.keyboard.press("Control+k");
    await page.getByPlaceholder("Search or type a command…").fill("alert");
    await page.getByText("Open Alert Center", { exact: true }).click();

    const center = page.getByText("EXECUTIVE ALERT CENTER", { exact: true });
    await expect(center).toBeVisible();

    // The real activation is recorded as a Critical-tier entry, not
    // fabricated copy.
    await expect(page.getByText("EMERGENCY STOP ACTIVATED", { exact: true }).last()).toBeVisible();
    await expect(page.getByText(/^Critical \(\d+\)$/)).toBeVisible();

    // Tier filter chips narrow the real recorded history. The dev
    // backend this suite shares can carry more than one real Emergency
    // Stop activation across a session (this test and emergencyStop.spec
    // both trigger real ones) — `.first()` targets any one real,
    // correctly-recorded entry rather than assuming there's exactly one.
    await page.getByText(/^Critical \(\d+\)$/).click();
    await expect(page.getByText("All new trading is halted until the CEO resumes.").first()).toBeVisible();

    await page.getByRole("button", { name: "CLOSE" }).click();
    await expect(center).toHaveCount(0);

    // Resume trading so this test leaves the shared dev backend in a
    // clean state for whichever spec runs next.
    await clickRobust(page, () => page.getByRole("button", { name: /EMERGENCY.*RESUME TRADING/ }), { label: "Resume button (open dialog)" });
    await clickRobust(page, () => page.getByRole("button", { name: "RESUME TRADING", exact: true }), { label: "RESUME TRADING" });
  });
});
