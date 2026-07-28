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

## v0.6 — Paper Trading Operations

Three more agents (Sentinel — Risk Management, Pulse — Market Scanner,
Guardian — Portfolio Protection), TradeTown's ninth Lobby door: the
Trading Floor, home to all three. The v0.5 paper-trading engine's
opening logic moved behind a full Decision Voting pipeline
(`voting.py` + `decision.py`): every high-confidence completed research
item is now voted on by the four researcher agents plus Sentinel and
Guardian, with a permanent, explainable `TradeDecision` record (research/
technical/fundamental/risk summaries, supporting/opposing agents, final
reasoning) stored for every candidate — approved or not. Approved trades
route through a new order-book `PaperBroker` (`broker.py`, market/limit/
stop/take-profit/stop-loss orders, one tick of fill latency) instead of
opening a position directly. A configurable `RiskEngine`
(`risk_engine.py`) backs Sentinel's hard trade-approval gate and
Guardian's softer exposure/concentration watch; a `ScannerManager`
(`scanner.py`) backs Pulse's continuous gap/breakout/volume-spike/
volatility scan across the watchlist. A `TradeJournal` (`journal.py`)
stamps every closed trade with a coach review and lessons learned,
closing a v0.5 gap where those two schema fields existed but nothing
populated them. The v0.5 closing logic (mark-to-market, hold-duration-
based random-roll close) is unchanged — only how a position gets opened
moved. Brain Room HUD and the newspaper both gained sections surfacing
all of this (Open Positions, Pending Orders, Risk Management, Votes,
Scanner Alerts, Company Rating).

**Explicitly not in v0.6** (per the brief's STOP CONDITION): live
brokerage support, a connection to Charles Schwab or any other broker, or
execution of a single real trade — the same boundary every version
before it has held. Every `PaperOrder`, `PaperPosition`, and `PaperTrade`
is simulated bookkeeping only.

## v0.7 — Intelligence & Decision Systems

Six systems layered onto v0.6.3's Executive Voting rather than replacing
it, aimed at making both the AI desk and the player better decision-
makers over time rather than maximizing a single trade's P&L. A
**Decision Confidence Engine** (`confidence.py`) formalizes the old
client-side "Trade Quality Score" into a real, persisted six-factor
score carried onto every `TradeDecision`. A **What-If Simulation Lab**
(`whatif.py`) stress-tests a pending proposal against 12 named market
scenarios, each a bootstrap resample of the symbol's own real recent
returns — computed fresh per request, never persisted. An **AI Debate
Room** (`debate.py`) turns the six analyst votes into a full investment-
committee review (opening statement + real cross-examination per
analyst) before the CEO decides. The **Decision Journal & Mistake
Tracker** extends Coach's existing weekly/monthly reporting with two new
recurring-mistake patterns and a strengths readout, rather than building
a parallel journal. A **Premium Trade Outcome Banner** replaces the old
blocking trade-result popup with a non-blocking, queued, top-center
banner. Last, the **Trade Gatekeeper** (`gatekeeper.py`) sits between the
CEO's real buy/sell call and the order actually being placed — seven
real checks (confidence, risk-vote alignment, desk agreement, the AI
Debate's own recommendation, portfolio exposure, correlated positions,
active critical risk warnings) can now veto even the player's own
choice, ending v0.6.3's "the CEO's choice is unconditionally final"
model. A rejected trade never executes, so there's no real P&L to grade
it against — its hypothetical outcome instead resolves later purely from
the symbol's own real subsequent price move, the same "wait for real
time, check real data" convention every other outcome-grading path in
this codebase already uses.

Several factors named across these six features' briefs (multi-timeframe
confirmation, support/resistance quality, liquidity, reward-to-risk
ratio, stop-loss placement, strategy match, historical similar-setup
performance) have no real data source in this codebase and are
deliberately not computed anywhere — see each module's own docstring for
the same honesty boundary applied consistently across all six.

### v0.7 continued — AI Company Management & Simulation Systems

Three more systems, shifting the frame from grading individual trades to
managing the company itself. **Company Operating Modes** add a
`Learning | Assisted | Executive` toggle (`settings.operatingMode`) that
changes how much NEXUS auto-resolves on the player's behalf — Learning
Mode leaves every trade proposal to a real CEO click (unchanged v0.6.3
behavior); Assisted Mode auto-resolves only proposals a new
`is_significant_proposal()` check calls routine (adequate confidence, no
critical risk warning, reasonable position size), still surfacing
anything bigger; Executive Mode auto-resolves everything. Every auto-
resolved decision is honestly tagged `resolvedBy: "auto"` on its
`CeoDecisionRecord`, never presented as the player's own call. **Market
Environment Simulation** (`market_environment.py`) classifies the whole
watchlist into bull/bear/sideways/high-volatility/low-volatility every
tick from the real aggregated daily price changes already on hand, keeps
a real timeline of actual regime changes, and now drives which pool of
market headlines the News desk draws from — a genuine, if modest,
"departments react to conditions" hookup. **Company Health & Stability**
(`company_health.py`) adds a second scorecard alongside the existing
`CompanyScore`, deliberately asking a different question ("is the
company stable and well-run?" vs. "is it winning?") from ten real
sub-metrics — risk warnings, agent activity, research completion,
portfolio P&L, agent energy, hall-of-fame count, signal-calibration
level, watchlist expansion, and education progress — with plain-language
recommendations naming whichever two metrics are weakest. All three
systems, plus a new COMPANY tab surfacing them, are covered by 33 new
backend tests. The brief's "Executive Reports" is deliberately not a new
report engine — it reuses Feature 18's existing Coach reporting — and
"NPC Interactions" (persistent relationships, remembered conversations)
has no new memory system behind it in this pass; both are documented
scope cuts rather than fabricated mechanics.

### v0.7 continued — Executive AI & Academy System

A tenth agent and a company-wide learning system. **Meridian, the Chief
Investment Officer** (`app/executive_review.py`), joins the roster with a
real profile, schedule, and a palette-swapped sprite generated by
comparing the base sprite sheet against all nine existing agents to find
exactly which pixels each one recolors — but never votes on a trade or
generates a research signal, per the brief. Its one real responsibility
is a new **Monthly Executive Review**, generated on the same monthly
cadence as Coach's own report but asking a different question: real
department activity, research/knowledge output, real analyst
disagreement (Debate Room challenge counts), and real "worth a second
look" flags, plus one true period-over-period figure — company score
change against the previous review's own stored score. A new
**Executive Boardroom** room (34×22 tiles, the largest room in the game)
hosts six live readouts — world market display, department performance,
department status, the briefing screen, a report-archive timeline, and
current objectives — deliberately with no duplicate Command Center tab,
since the brief specifically wants the room itself walkable "at any
time." The **AI Academy & Knowledge Network** gives every agent a real
Knowledge Branch and a real, cumulative Knowledge Points total that only
grows from actually-completed work (finished research, a finished
Academy project, real meeting attendance), crossing real tiers the same
way Signal Calibration's own level already does. A new non-market
research queue (`academy_research.py`) cycles six knowledge topics
through the team, permanently archiving every completion as the **Company
Knowledge Library**; a company-wide Academy Level (1-5, named tiers)
blends real points and real completions rather than five new physical
rooms. Surfaced on a new KNOWLEDGE tab — not "ACADEMY," since that name
was already taken by the pre-existing Trading Academy lesson curriculum.
**Mentorship** is this pass's most deliberate honesty call: with zero
seniority or relationship data anywhere in the codebase, "seniority" is
grounded in the one real number that legitimately reflects it — an
agent's own earned Knowledge Points — rather than a fabricated status
label; when two agents' real point gap crosses a threshold, a real
session transfers a small real bonus, logged with both agents' actual
numbers. A full relationship graph and in-world mentoring animations are
explicit, documented scope cuts, as is per-tier "expanded dialogue" (33
bespoke lines was out of scope) and new academy-flavored meeting
dialogue (a completed project instead publishes a real news headline).
33 new backend tests; the full Playwright suite (16 tests across three
spec files) passes clean.

## What's next for v0.8 (not started, not scoped)

These are candidate directions surfaced by v0.6/v0.7's design, not
commitments — nothing below has been designed, and per every version's
stop condition, work stops at the end of its own brief:

- **A real `MarketDataProvider` adapter.** The interface and mock
  implementation are already in place (`market_data.py`); the natural
  next step is one real vendor (Polygon, Finnhub, Alpha Vantage, Yahoo
  Finance, or Schwab) behind an API key, still with a mock fallback when
  no key is configured. This would also let `simulation.py` replace its
  placeholder backtest metrics with real historical-data-driven ones, and
  let `scanner.py` do true rolling-window breakout detection instead of
  its current current-quote-threshold-only approach.
- **Model-generated meeting discussion, coach commentary, and vote
  reasoning.** `discussion.py`, `coach.py`'s recommendations, and
  `voting.py`'s per-agent reasons are all templated flavor text tied to
  real state; the architecture was deliberately built so a future version
  could swap the template call for a real model call without touching the
  surrounding state machines.
- **A real sector taxonomy.** v0.6's "sector concentration" risk check is
  a per-symbol concentration proxy (see `risk_engine.py`'s module
  docstring) since `ResearchCategory` isn't a real sector system — a
  future version could add one and make Guardian's concentration checks
  sector-aware rather than symbol-aware.
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
  placeholder math. `broker.py` is already shaped for this (see its
  module docstring), but no such adapter exists or is wired in v0.6.
  Explicitly not live trading.
- **Tighter order/position/decision traceability.** v0.6 links a closed
  trade back to the `TradeDecision` that approved it via a best-effort
  "most recent matching-symbol decision" lookup (see `nexus.py`'s
  `_journal_closed_trades()`), since neither `PaperOrder` nor
  `PaperPosition` carries an explicit decision/order id through the full
  chain. A future version could add those fields for exact attribution.
