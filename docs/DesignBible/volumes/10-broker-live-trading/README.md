# Volume 10 — Broker & Live Trading

**Status:** Chapters 68–69 written — pure target architecture, no
implementation. Chapter 69 is organized in three parts (Part 1:
Multi-Account & Fund Management; Part 2: Prop Firm Rule Engine, with
its own addendum; Part 3: Institutional Rule Engine) rather than as
separate chapter numbers — earlier drafts briefly existed as standalone
"Chapters 70/71" before being folded back into Chapter 69 per explicit
correction. See [the master Table of Contents](../../README.md) and
[Appendix G's Live Trading
Gate](../../appendices/appendix-g-permanent-development-policy.md) for
the standing policy on exactly when this volume moves from
architecture to a real connection.

Every real order this codebase has ever placed has gone to exactly one
destination: `backend/app/broker.py`'s `PaperBroker`, a fully simulated
in-process order book. No brokerage SDK, API key, or real execution
endpoint exists anywhere in this codebase. This volume exists to
describe, honestly, both that permanent boundary and the architecture a
real connector (Charles Schwab first) would need to implement without
requiring TradeTown's own trading logic to change — mirroring the same
"chapter documents the real system honestly, target design stays
clearly labeled" discipline [Volume 9](../09-departments/README.md)
already established.

## Chapters

| Feature | Title | Status |
|---|---|---|
| 68 | [Institutional Broker Management System (IBMS)](chapter-68-institutional-broker-management-system.md) | Pure architecture — no implementation. `app/broker.py`'s `PaperBroker` (a real, fully simulated order-book engine) and `app/market_data.py`'s `MarketDataProvider` adapter-interface pattern (proven out for market data, never for execution) are the only real precedents. Broker connections, authentication, encrypted credentials, account synchronization, buying power beyond a cash-reserve floor, position reconciliation, broker health monitoring, a multi-account model, and Charles Schwab v1.0 itself are all genuinely unbuilt. Gated by the Live Trading Gate — see Appendix G. |
| 69 | [Multi-Account & Fund Management System (MAFMS)](chapter-69-multi-account-fund-management-system.md) | Pure architecture — no implementation, in three parts. **Part 1 (MAFMS):** `PaperPortfolio` and `TreasuryState` are two real, genuinely isolated capital pools — the one real precedent this chapter's architecture generalizes from; a generalized N-account model, account types, per-account permissions/risk profiles, account switching, cross-account aggregation, Fund Mode, and Client Mode are all genuinely unbuilt. **Part 2 (Prop Firm Rule Engine, + addendum):** the strongest real-coverage ratio in this volume — 5 of 15 supported rules are already real, enforced `RiskLimits` fields, and `DailyObjectiveStatus` already provides a live daily compliance readout; trailing drawdown, consistency rules, leverage, scaling milestones, challenge windows, and a weekday-aware time system are all confirmed genuinely unbuilt. **Part 3 (Institutional Rule Engine):** grep-confirmed no `Rule`/`RuleProfile`/`RuleEngine` class exists anywhere; today's real risk checks are deliberately hardcoded, transparent Python functions, not a data-driven rule interpreter — a real architectural trade-off Part 3 must honor, not silently fix. Depends on Chapter 68 becoming real first. |

## Where the real content lives today

- `backend/app/broker.py` — the real, current, and **only** broker:
  `PaperBroker`, an order-book paper-trading engine (market / limit /
  stop / take-profit / stop-loss).
- `backend/app/market_data.py`'s `MarketDataProvider` interface — the
  real abstraction layer a future live adapter (Charles Schwab, ...)
  would implement without touching anything that consumes it. Proven
  out for market data only; no equivalent interface exists for
  execution today.
- `frontend/src/ui/components/GlobalStatusBar.tsx`'s `BROKER` pill —
  the one real, honest CEO-facing acknowledgment that trading is
  simulated (`"SIMULATED"`, always).
- **Live Trading, Charles Schwab, real broker authentication/API
  security, broker health, a multi-account model, and real Account/
  Trading Permissions do not exist anywhere in this codebase today.**
  No real money, real order, or real brokerage credential is ever
  touched. This is this volume's single most important honesty
  boundary.
