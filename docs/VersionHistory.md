# Version History

A version-by-version summary of TradeTown's scope. For the itemized
per-change list (including bug fixes), see [`CHANGELOG.md`](../CHANGELOG.md)
at the repo root; this file is the higher-level "what was each version
about and why" narrative, plus what's intentionally deferred.

## v0.1 — Foundation

One employee (Scout), a small HQ (Lobby + Scout Office + CEO Office +
Brain Room), a live backend simulation driving Scout's daily
schedule/mood/energy/memory, save/load, and Docker Compose deployment with
an nginx reverse proxy. Established the core client/server architecture
(server-authoritative agent state over WebSocket, client-authoritative
player/settings/dialogue) that every later version builds on without
rewriting.

## v0.2 — Multi-agent office

Three more agents (Atlas, Echo, Nova), each with a distinct personality
and daily routine; two new rooms (Meeting Room, Break Room) plus an
upgraded Brain Room ("Mission Control"); a reusable server-authoritative
`Task` system; the NEXUS orchestrator (task assignment, meetings, breaks,
whiteboards, discovery news); a newspaper stand; and an extended save
schema. Generalized the v0.1 single-agent architecture (`ScoutState` →
`Record<AgentId, AgentState>`, `ScoutNPC` → `AgentNPC`) to support an
arbitrary agent roster without a rewrite — a design choice that paid off
directly in v0.3, where adding a fifth agent (Scribe) required zero
Phaser scene changes.

## v0.3 — Intelligence & research

A fifth agent (Scribe, the company historian); a `MarketDataProvider`
interface with a mock adapter (no real market API, no trades — see
`docs/Architecture.md`); a rotating research queue across an 8-symbol
watchlist with per-agent confidence; meetings that now produce real
discussion transcripts and minutes; a searchable `CompanyMemory` log with
a dedicated viewer; and an upgraded Brain Room HUD / newspaper /
whiteboards surfacing all of it. Extended (not replaced) v0.2's `Task`
system with categories, and v0.2's meeting/break `AgentOverride`
mechanism gained a `discussion` field rather than a parallel state
machine.

**Explicitly not in v0.3** (per the brief's STOP CONDITION): paper
trading, brokerage connections, live trading of any kind, or a real
market data API call. "Future trade" flags are a logged note for a human
to consider, never a queued or simulated order.

## v0.4 — Design & Architecture Foundation

Documentation only — **zero code changes**. Twelve planning documents
(`DESIGN_BIBLE.md`, `ROADMAP.md`, `AI_AGENT_BIBLE.md`, `UI_UX_BIBLE.md`,
`COMPANY_LORE.md`, `NEXUS_ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`,
`CODING_STANDARDS.md`, `TASK_BACKLOG.md`, `KNOWN_LIMITATIONS.md`,
`FUTURE_ARCHITECTURE.md`, and a final `ARCHITECTURE_REVIEW.md` scoring the
codebase across nine dimensions) capturing the v0.3 codebase's design
intent, coding conventions, and a scored backlog of 268 candidate future
tasks. Explicitly forbade starting v0.5 or touching any trading feature —
v0.3 continued to run exactly as it did before this version.

## v0.5 — Intelligence Evolution

A sixth agent (Coach, Performance & Improvement) who reviews completed
research and closed paper trades and files weekly/monthly reports
(`coach.py`, `CoachDashboard.tsx`); a Simulation Lab (`simulation.py`) —
a new room where strategies queue, run, and complete with placeholder
backtest metrics (see `simulation.py`'s module docstring — no real
historical data source exists yet); a Paper Trading engine
(`portfolio.py`, `paper_trading.py`) with a fully simulated $100,000
starting account, opening/closing positions from high-confidence research
completions; a Hall of Fame room celebrating the company's best research,
strategies, simulations, streaks, and monthly performance
(`hall_of_fame.py`); a Learning System (`knowledge.py`) that derives a
`lesson` or `mistake` Company Memory record from every closed paper
trade; a seven-metric Company Score (`company_score.py`) — Research
Quality, Decision Quality, Risk Management, Paper Trading Performance,
Team Coordination, Knowledge Growth, Simulation Success — shown in an
expanded Brain Room HUD; and daily/weekly/monthly/all-time performance
snapshots (`analytics.py`). Company Memory gained six new searchable
categories (`lesson`, `mistake`, `strategy`, `coach_review`, `simulation`,
`paper_trade`). The Lobby widened from five doors to eight to fit the
three new rooms (Simulation Lab, Hall of Fame, Performance Center).

**Explicitly not in v0.5** (per the brief's STOP CONDITION): live
brokerage support, a connection to Charles Schwab or any other broker, or
execution of a single real trade. Every `PaperOrder`, `PaperPosition`,
and `PaperTrade` is simulated bookkeeping only — see `portfolio.py`'s
module docstring for the enforcement boundary.

## What's next for v0.6 (not started, not scoped)

These are candidate directions surfaced by v0.5's design, not commitments
— nothing below has been designed, and per every version's stop
condition, work stops at the end of its own brief:

- **A real `MarketDataProvider` adapter.** The interface and mock
  implementation are already in place (`market_data.py`); the natural
  next step is one real vendor (Polygon, Finnhub, Alpha Vantage, Yahoo
  Finance, or Schwab) behind an API key, still with a mock fallback when
  no key is configured. This would also let `simulation.py` replace its
  placeholder backtest metrics with real historical-data-driven ones.
- **Model-generated meeting discussion and coach commentary.** Both
  `discussion.py` and `coach.py`'s recommendation text are templated
  flavor text tied to real state; the architecture was deliberately built
  so a future version could swap the template call for a real model call
  without touching the surrounding state machines.
- **A `CompanyMemory` REST search endpoint.** `memory.search()` /
  `knowledge.search_knowledge()` already implement the filter contract;
  neither is wired to a route yet, since the frontend currently filters
  the WS-synced list client-side.
- **Monte Carlo simulation and parameter optimization.** `simulation.py`
  is deliberately structured so these can be added as new functions that
  still produce a `SimulationResult` — no other part of the pipeline
  (queueing, progress, archiving) needs to change. See
  `docs/FUTURE_ARCHITECTURE.md`.
- **Real broker paper-trading APIs** (e.g. a sandbox/paper endpoint from
  a real brokerage), once there's a real market data connection — still
  simulated money, but against real historical fills instead of
  placeholder math. Explicitly not live trading.
