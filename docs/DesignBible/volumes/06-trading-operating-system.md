# Volume 6 — Trading Operating System

**Status:** Outline. Not yet written. See [the master Table of
Contents](../../README.md).

## What this volume will cover

- Probability Philosophy
- Evidence Framework
- Confidence Framework
- Expected Value
- Trade Quality
- Position Sizing
- Capital Allocation
- Risk Budget
- Risk Management
- Trade Selection
- Trade Rejection
- Day Trading
- Swing Trading
- Hybrid Trading
- Automation Modes
- Portfolio Management
- Execution Standards
- Institutional Trading Standards

## Where the real content lives today

This is the most heavily-implemented volume in the codebase already —
the job here is consolidation, not invention:

- `backend/app/confidence.py` — the Evidence/Confidence Framework
  (`DecisionConfidence`'s six weighted factors).
- `backend/app/war_room.py` — Expected Value (`ExpectedValueAnalysis`,
  a real probability-weighted read over 12 simulated scenarios).
- `backend/app/risk_engine.py` — Position Sizing, Risk Budget, Risk
  Management (`recommended_quantity()`, exposure/concentration checks).
- `backend/app/gatekeeper.py` — Trade Selection and Trade Rejection (the
  Trade Gatekeeper's seven real checks).
- `backend/app/portfolio_intelligence.py` — Capital Allocation and
  Portfolio Management (Portfolio Heat, correlation, capital efficiency).
- `backend/app/schemas.py`'s `SettingsState.operatingMode` — Automation
  Modes (Learning / Assisted / Executive).
- **Day Trading / Swing Trading / Hybrid Trading** as distinct, separately
  configured modes are not yet real in this codebase (only the Trading
  Floor's real order-book paper trading exists); this volume should
  document that gap honestly rather than imply three real modes exist.
