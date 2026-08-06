import { test, expect } from "@playwright/test";
import { continueGame, dismissBlockingPopups, setPlayerScene } from "./helpers";

/**
 * Design Bible Chapter 67 (TTOS) Part 3 — the always-visible broker-
 * status/risk-status/capital-status/company-health strip, real from
 * every scene, distinct from TopStatusBar's own connection dot. See
 * GlobalStatusBar.tsx's own doc comment for exactly which real field
 * backs each item and why Broker Status is honestly static.
 */
test.describe("Global Status Bar", () => {
  test("shows real Risk/Company Health/Portfolio/Market/Automation/Deployed status from every scene", async ({ page }) => {
    await page.goto("/");
    await setPlayerScene(page, "LobbyScene", 160, 220);
    await continueGame(page);
    await dismissBlockingPopups(page);

    await expect(page.getByText("RISK", { exact: true })).toBeVisible();
    await expect(page.getByText("COMPANY HEALTH", { exact: true })).toBeVisible();
    await expect(page.getByText("PORTFOLIO", { exact: true })).toBeVisible();
    await expect(page.getByText("MARKET", { exact: true })).toBeVisible();
    await expect(page.getByText("AUTOMATION", { exact: true })).toBeVisible();
    await expect(page.getByText("DEPLOYED", { exact: true })).toBeVisible();
    await expect(page.getByText("BROKER", { exact: true })).toBeVisible();
    await expect(page.getByText("SIMULATED", { exact: true })).toBeVisible();

    // Real values, not placeholders — RISK starts NORMAL/ELEVATED/
    // RESTRICTED (never blank) and AUTOMATION always shows the current
    // Operating Mode (learning by default on a fresh save).
    await expect(page.getByText(/NORMAL|ELEVATED|RESTRICTED/).first()).toBeVisible();
    // .first() since Design Bible Chapter 67's Quick Action Dock also
    // shows this same real Operating Mode value from every scene.
    await expect(page.getByText("LEARNING", { exact: true }).first()).toBeVisible();

    // Still visible from inside the Command Center — a global strip,
    // never scoped to one scene or overlay.
    await page.keyboard.press("Tab");
    await dismissBlockingPopups(page);
    await expect(page.getByText("COMPANY HEALTH", { exact: true })).toBeVisible();
    await page.keyboard.press("Escape");
  });
});
