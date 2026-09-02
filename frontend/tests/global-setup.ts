import type { FullConfig } from "@playwright/test";

const BACKEND_HEALTH_URL = "http://localhost:8000/api/health";

interface HealthCheck {
  isDefaultDevSave?: boolean;
}

/**
 * CEO directive "Paper Burn-in Test-Isolation Hardening" — the real
 * root cause this guards against: this suite has no `webServer` config
 * of its own (see playwright.config.ts's own doc comment) — it always
 * assumes whatever backend happens to be running on port 8000, with
 * zero enforcement that it's an isolated save. A real Emergency Stop
 * test (tests/alertCenter.spec.ts) activated Emergency Stop on the
 * SHARED REAL DEV SAVE, then crashed mid-test before it could resume —
 * leaving a real paper-trading burn-in silently blocked for days (see
 * CHANGELOG.md's own entry for the full incident writeup). Cleanup
 * hooks (afterEach) cannot fix this class of failure — a crash skips
 * them too. The only reliable fix is refusing to run ANY test at all
 * — fail closed, before a single mutation happens — whenever the
 * backend reports it is pointed at the shared default dev save
 * (`GET /api/health`'s `isDefaultDevSave`, backend/app/config.py's
 * `DEFAULT_DATABASE_URL`).
 *
 * `shouldAbort()` is the pure decision logic, exported so
 * tests/testIsolationGuard.spec.ts can exercise it directly without a
 * live backend. `globalSetup()` below is the thin Playwright wrapper —
 * throwing here aborts the ENTIRE run before any test file executes
 * (see https://playwright.dev/docs/test-global-setup-teardown).
 */
export function shouldAbort(health: HealthCheck | null): string | null {
  if (health === null) {
    // Backend unreachable is a separate, pre-existing failure mode —
    // the suite's own tests already fail with their normal connection
    // error in that case; this guard only owns the "wrong target"
    // failure mode, never masks a different one.
    return null;
  }
  if (health.isDefaultDevSave === true) {
    return [
      "Refusing to run the Playwright suite: the backend on :8000 is pointed at the shared default dev save",
      "(no DATABASE_URL override). This suite mutates real trading/company state — running it against the",
      "same save a paper-trading burn-in depends on can silently block trading for days. See CHANGELOG.md's",
      '"Paper Burn-in Test-Isolation Hardening" entry for the real incident this check exists to prevent.',
      "",
      "Start the backend against an isolated save instead, e.g.:",
      '  DATABASE_URL="sqlite:////tmp/tradetown-test-$(date +%s).db" uvicorn app.main:app --port 8000',
    ].join("\n");
  }
  return null;
}

async function fetchHealth(): Promise<HealthCheck | null> {
  try {
    const res = await fetch(BACKEND_HEALTH_URL);
    if (!res.ok) return null;
    return (await res.json()) as HealthCheck;
  } catch {
    return null;
  }
}

export default async function globalSetup(_config: FullConfig): Promise<void> {
  const health = await fetchHealth();
  const reason = shouldAbort(health);
  if (reason !== null) {
    throw new Error(reason);
  }
}
