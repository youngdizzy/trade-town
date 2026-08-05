# Volume 8 — Research Division

**Status:** Outline. Not yet written. See [the master Table of
Contents](../../README.md).

## What this volume will cover

- Knowledge Graph
- Innovation Lab
- Strategy Lab
- Research Projects
- Shadow Trading
- Backtesting
- Simulation Center
- Historical Database
- Pattern Library
- Institutional Memory
- Company Learning

## Where the real content lives today

- `backend/app/knowledge_graph.py` — the real Company Knowledge Graph, a
  node-edge network built fresh from six already-real sources (research,
  Academy projects, Executive Reviews, Coach Reports, Hall of Fame).
- `backend/app/strategy_lab.py` / `backend/app/sandbox.py` — Strategy Lab
  and Research Projects (the Research Sandbox pipeline: idea → backtest →
  paper-forward → certification).
- `backend/app/innovation.py` — Innovation Lab (Innovation Points, tied to
  Devil's Advocate challenges).
- `backend/app/black_box.py` — long-running, higher-risk Black Box
  Research Projects, the closest real analogue to a dedicated
  "high-conviction bets" research track.
- `backend/app/simulation.py` — Simulation Center.
- `backend/app/whatif.py` — the What-If Simulation Lab's 12 real
  bootstrap-resampled scenarios, the closest thing to Pattern Library
  content today.
- `backend/app/decision_vault.py` — Institutional Memory (the Decision
  Vault's real Similarity Engine — "has the desk seen this setup
  before?").
- **Shadow Trading** and a standalone **Historical Database** (as
  distinct from the mock `MarketDataProvider`'s own candle series) have
  no real implementation in this codebase today.
