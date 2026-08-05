# Volume 10 — Broker & Live Trading

**Status:** Outline. Not yet written. See [the master Table of
Contents](../../README.md).

## What this volume will cover

- Paper Trading
- Live Trading
- Charles Schwab
- Future Broker Integrations
- Authentication
- API Security
- Broker Health
- Emergency Stop
- Kill Switch
- Capital Protection
- Account Permissions
- Trading Permissions

## Where the real content lives today

- `backend/app/broker.py` — the real, current, and **only** broker:
  `PaperBroker`, an order-book paper-trading engine (market / limit /
  stop / take-profit / stop-loss). This is the honest, current state of
  this entire volume.
- `backend/app/market_data.py`'s `MarketDataProvider` interface — the
  real abstraction layer a future live adapter (Polygon, Finnhub, Alpha
  Vantage, Yahoo Finance, **Charles Schwab**, ...) would implement without
  touching anything that consumes it. This is real, working, deliberate
  future-proofing — not yet a live connection.
- **Live Trading, Charles Schwab, real broker Authentication/API
  Security, Broker Health, Emergency Stop, Kill Switch, and real Account/
  Trading Permissions do not exist anywhere in this codebase today.** No
  real money, real order, or real brokerage credential is ever touched.
  This is this volume's single most important honesty boundary — when
  written, it must state this as plainly as this stub does, not soften it
  into "coming soon" language that implies more progress than exists.
