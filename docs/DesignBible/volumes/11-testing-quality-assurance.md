# Volume 11 — Testing & Quality Assurance

**Status:** Outline. Not yet written. See [the master Table of
Contents](../../README.md).

## What this volume will cover

- Unit Tests
- Integration Tests
- Paper Trading Tests
- Simulation Tests
- Stress Tests
- Edge Cases
- Failure Recovery
- Performance Benchmarks
- Regression Testing
- Release Checklist

## Where the real content lives today

- `backend/tests/` — the real backend unit/integration suite (900+
  tests as of the War Room / Portfolio Intelligence slice), one file per
  module under test, following the established `_fixture()` helper +
  one-`TestClass`-per-function convention documented in
  `docs/CODING_STANDARDS.md`.
- `frontend/tests/` — the real Playwright end-to-end suite, exercising
  the live Vite dev server + FastAPI backend rather than a mocked
  harness (see `frontend/tests/helpers.ts`'s own doc comment for the
  shared popup-dismissal convention every spec file relies on).
- Multi-thousand-tick standalone smoke tests (e.g. the 11,500-tick
  Reflection Chamber verification, the 4,000-tick Reasoning Lab
  verification) are this codebase's real Stress Test / Simulation Test
  practice — ad hoc scripts run once per feature slice, not a repeatable
  harness. This volume should decide whether that should become a real,
  repeatable Stress Test suite.
- **A formal Release Checklist and dedicated Performance Benchmark suite
  do not exist yet** — each feature slice's own CHANGELOG.md entry
  documents its own verification, but there is no cross-feature release
  gate today.
