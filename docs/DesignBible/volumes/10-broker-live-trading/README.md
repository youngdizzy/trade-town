# Volume 10 — Broker & Live Trading

**Status:** Chapter 68 remains pure target architecture — explicitly
deferred until Chapter 75 per [Appendix G's Live Trading
Gate](../../appendices/appendix-g-permanent-development-policy.md).
**Chapter 69 is now implemented, on the paper-trading side, in all
three of its parts** (Part 1: Multi-Account & Fund Management; Part 2:
Prop Firm Rule Engine, with its own addendum; Part 3: Institutional
Rule Engine) — organized under one chapter number rather than as
separate ones, per the same explicit correction as before (earlier
drafts briefly existed as standalone "Chapters 70/71"). See [the master
Table of Contents](../../README.md) and each part's own Implementation
Notes for exactly what was built and the honest boundaries of what
remains unbuilt or gated behind Chapter 68.

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
| 69 | [Multi-Account & Fund Management System (MAFMS)](chapter-69-multi-account-fund-management-system.md) | **Implemented, in all three parts, on the paper-trading side.** **Part 1 (MAFMS):** a real `Account` model (`app/schemas.py`/`app/accounts.py`) generalizes the old two-pool precedent — create/close accounts, capital allocation reusing `treasury.py`'s real transfer machinery, account switching. Live trading execution against non-primary accounts remains explicitly unwired (named honestly, not silently assumed). **Part 2 (Prop Firm Rule Engine, + addendum):** `app/prop_firm.py` adds a real Weekday-Aware Time System, Trailing Drawdown Engine (peak-equity high-water mark), Consistency Rule Engine, Scaling Milestones, Challenge Windows, and a transparent, published Compliance Score. Leverage is stated as explicitly not applicable (100% cash account) rather than fabricated — these are real status computations, not yet wired as pre-trade blocks. **Part 3 (Institutional Rule Engine):** `app/rule_engine.py` (new) is a real, centralized evaluator for a closed, named `RuleType` set (not a free-text DSL, a deliberate scope decision) attached per-account via `Account.custom_rules`, with corrective-action suggestions and real Company Memory recording — not yet wired into the pre-trade pipeline as a blocking veto. Chapter 68 (the real broker connection) remains deferred until Chapter 75 per Appendix G. |

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
