import { test, expect } from "@playwright/test";
import { shouldAbort } from "./global-setup";

/**
 * CEO directive "Paper Burn-in Test-Isolation Hardening" — real
 * regression coverage of global-setup.ts's own pure decision logic
 * (Phase 9's "the protection fails closed" requirement). These assert
 * against the function directly, no live backend involved — the live,
 * end-to-end proof (globalSetup actually aborting a real run against
 * the real dev save, and actually proceeding against an isolated one)
 * is the separate, manual verification recorded in this milestone's own
 * forensic report, since a Playwright test file can't easily assert
 * about the outcome of "the whole suite refused to start."
 */
test.describe("global-setup guard — shouldAbort()", () => {
  test("aborts when the backend reports the shared default dev save", () => {
    const reason = shouldAbort({ isDefaultDevSave: true });
    expect(reason).not.toBeNull();
    expect(reason).toContain("shared default dev save");
    expect(reason).toContain("DATABASE_URL");
  });

  test("allows the suite to proceed against an isolated save", () => {
    expect(shouldAbort({ isDefaultDevSave: false })).toBeNull();
  });

  test("does not abort on an unreachable backend — a separate, pre-existing failure mode", () => {
    expect(shouldAbort(null)).toBeNull();
  });

  test("treats a missing isDefaultDevSave field as safe rather than aborting on an ambiguous signal", () => {
    // A backend running an older build without this field should never
    // silently block every test run forever — absence is not proof of
    // danger, only presence of `true` is.
    expect(shouldAbort({})).toBeNull();
  });
});
