# TradeTown Roadmap

**Status:** Canonical. This is the ordered, numbered plan for every future
version of TradeTown, from the current release through v2.0. It exists so
that "what comes next" is never a fresh conversation — it's a lookup.

Two rules govern every entry below, inherited directly from
`DESIGN_BIBLE.md`:

1. **Each version is a complete, standalone deliverable.** No version
   ships "half a feature" that only becomes useful once a later version
   arrives. If a milestone can't stand on its own, it's scoped wrong.
2. **No version accelerates the trading boundary.** Nothing before v1.0
   executes, queues, or connects to a real brokerage — see
   `DESIGN_BIBLE.md`'s "What TradeTown Is NOT" and every version's own
   stop condition below. v1.0 itself only enables a real connection if
   explicitly re-authorized at that time; it does not ship one by default.

Every future milestone below is a **plan**, not a commitment to exact
scope — the brief for each version, written when that version actually
starts, is the final word on what ships. This document is the backlog of
intent; `TASK_BACKLOG.md` is the backlog of individual tasks; neither
overrides a version's own brief once that brief exists.

---

## Version 0.1 — Foundation
**Status: Completed**

One employee (Scout), a small HQ (Lobby + Scout Office + CEO Office +
Brain Room), a live backend simulation, save/load, and Docker Compose
deployment with an nginx reverse proxy. See `docs/VersionHistory.md`.

## Version 0.2 — Multi-Agent Office
**Status: Completed**

Three more agents (Atlas, Echo, Nova), two new rooms (Meeting Room, Break
Room), the `Task` system, NEXUS orchestration (meetings, breaks,
whiteboards, discovery news), and a newspaper stand. Generalized the
single-agent architecture to an arbitrary roster. See
`docs/VersionHistory.md`.

## Version 0.3 — Intelligence & Research
**Status: Completed**

A fifth agent (Scribe), a `MarketDataProvider` interface with a mock
adapter, a rotating research queue across an 8-symbol watchlist, meeting
discussions and minutes, `CompanyMemory`, and an upgraded Brain Room HUD
and newspaper. A follow-up pass made every agent visually/behaviorally
distinct and fixed several bugs found through live gameplay testing
(frozen task text, duplicate task ids, stacked modals, whiteboard
placement clipping — see `CHANGELOG.md`). See `docs/VersionHistory.md`.

## Version 0.4 — Architecture Foundation
**Status: In progress (this milestone)**

No gameplay, no new systems, no trading. This version produces the
design and architecture documents every future version is built against
— the twelve documents in `docs/` alongside this roadmap
(`DESIGN_BIBLE.md`, `AI_AGENT_BIBLE.md`, `UI_UX_BIBLE.md`,
`COMPANY_LORE.md`, `NEXUS_ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`,
`CODING_STANDARDS.md`, `TASK_BACKLOG.md`, `KNOWN_LIMITATIONS.md`,
`FUTURE_ARCHITECTURE.md`, `ARCHITECTURE_REVIEW.md`) plus this file. v0.3
continues to run exactly as it did before this version started — nothing
in `backend/` or `frontend/src/` changes as part of v0.4.

**Explicitly not in v0.4:** any new gameplay system, any change to
NEXUS's tick behavior, any new agent, any trading or brokerage code of
any kind.

---

## Version 0.5 — Coach
**Scope (planned):** The player's first real interaction beyond
"walk and read." Coach is a new agent whose job is the player, not the
market — it reviews the flagged "future trade candidate" records already
being logged in `CompanyMemory` (see `scribe.py`'s
`FUTURE_TRADE_CONFIDENCE_THRESHOLD`) and helps the player reason about
which ones held up, using only information the company already
generated. No new market logic; Coach is a UI/dialogue/pedagogy feature
built entirely on existing `CompanyMemory` data. See
`FUTURE_ARCHITECTURE.md` for exactly how Coach attaches to NEXUS without
a rewrite.

**Depends on:** v0.3's `CompanyMemory` and `future_trade` records
(shipped). **Stop condition:** Coach explains and asks questions; Coach
never scores, ranks, or recommends an action.

## Version 0.6 — Simulation Lab
**Scope (planned):** A sandboxed replay environment where a flagged
research candidate can be tested against historical price data with zero
real risk and zero real money — "what would have happened" as a pure
data exercise. Requires a second `MarketDataProvider` implementation
capable of serving historical (not live) series through the same
interface (`backend/app/market_data.py`), and a new Simulation Lab room
in the HQ. Results are logged to `CompanyMemory` like any other research
artifact.

**Depends on:** v0.3's `MarketDataProvider` adapter pattern (shipped),
v0.5's Coach (for reviewing simulation results, planned). **Stop
condition:** the Lab never executes a real order and never connects to
a live feed — historical data only.

## Version 0.7 — Paper Trading
**Scope (planned):** The first version where the company can "place" a
trade — against a simulated, zero-stakes paper ledger, not a real
brokerage account. This is the version that finally spends the "future
trade candidate" flags introduced in v0.3: Atlas can convert a
high-confidence candidate into a paper position, and the company tracks
simulated P&L. Still zero real money, zero brokerage connection.

**Depends on:** v0.6's Simulation Lab (candidates should be
lab-tested before paper execution), v0.5's Coach (for reviewing paper
trade outcomes). **Stop condition:** no real capital, no real brokerage
API, ever — this is a ledger of pretend numbers, clearly labeled as such
everywhere it appears in the UI.

## Version 0.8 — Strategy Marketplace
**Scope (planned):** Player-authored or player-curated research
strategies (which symbols to prioritize, which research categories to
weight) become shareable, importable configurations — not code, not
plugins with arbitrary execution, just structured priority data
consumed by `research.py`'s existing rotation logic. This is the
first version where TradeTown's simulation becomes partially
player-authored rather than purely observed.

**Depends on:** v0.3's `research.py` rotation logic (shipped), a save-file schema
extension for shareable strategy configs. **Stop condition:** strategies
configure *priority and emphasis* within the existing research pipeline;
they cannot inject arbitrary code or bypass the one-active-item-per-agent
model.

Also planned for this milestone: **Hall of Fame**, a read-only ranked
view over `CompanyMemory` and (once v0.7 exists) Ledger's paper P&L
records — celebrating the best-calibrated agents and highest-conviction
research calls. It shares this milestone's "surface what's already
recorded, don't generate new state" spirit closely enough to ship
alongside it, though it could equally ship as its own point release if
v0.8 grows too large. See `FUTURE_ARCHITECTURE.md` for exactly how it
attaches to existing data with no new write path.

## Version 0.9 — Risk Engine
**Scope (planned):** A company-wide risk posture becomes visible and
manageable — position concentration (across the paper ledger from v0.7),
confidence-vs-outcome calibration per agent, and a new risk-focused HUD
panel. This is the last version before v1.0 and exists specifically to
make the company's own fallibility legible before any real-money
question is even on the table.

**Depends on:** v0.7's Paper Trading (needs a ledger to compute risk
against). **Stop condition:** risk is measured and displayed, never
auto-hedged or auto-corrected without the player.

## Version 1.0 — Live Brokerage Support (re-authorization required)
**Scope (planned, gated):** The earliest point at which a real,
optional, explicitly opt-in brokerage connection becomes possible,
building on the `MarketDataProvider` adapter pattern for market data and
a parallel, separately-designed execution adapter for order placement.
This milestone does **not** ship a live connection by default — it ships
the *capability*, behind a deliberate, separately-scoped authorization
that must restate and re-affirm every boundary in `DESIGN_BIBLE.md`
before any order-placing code is written. Everything from v0.5–v0.9
(Coach, Simulation Lab, Paper Trading, Strategy Marketplace, Risk Engine)
exists specifically so this version has real scaffolding to build on
instead of starting from zero trust.

**Depends on:** v0.7 (Paper Trading, for the execution UX and ledger
model), v0.9 (Risk Engine, for pre-trade risk checks). **Stop condition:**
this document does not pre-authorize brokerage code — that authorization
is a separate, explicit decision made at v1.0's own kickoff, not implied
by this roadmap entry existing.

---

## Version 1.x — Platform Era (directional, not yet scoped)

Versions past 1.0 shift TradeTown's ambition from "one company" to "a
genre." Each is a placeholder direction, not a committed scope — actual
briefs are written when each version starts:

- **v1.1 — Custom Agents.** Player-authored agent personalities
  (dialogue style, research focus, schedule) layered on the existing
  `AgentProfile`/`AGENT_SCHEDULES` data model, without touching NEXUS's
  orchestration logic.
- **v1.2 — Multi-Company Saves.** More than one company/save slot per
  installation, breaking the current "single-tenant" assumption
  documented in `docs/Architecture.md` — the single largest architectural
  change on this entire roadmap, and the reason `KNOWN_LIMITATIONS.md`
  flags single-tenancy as a scaling concern today.
- **v1.3 — Companion/Mobile View.** A read-only companion surface (phone
  browser, second monitor) for checking on the company without the full
  Phaser client — built on the same WebSocket state broadcast already
  used by the desktop client, no new backend surface needed.
- **v1.4 — Live Ops & Telemetry.** Opt-in, privacy-respecting analytics
  on which rooms/agents/panels players actually engage with, to guide
  v2.0 planning honestly instead of by guesswork.

## Version 2.0 — TradeTown as a Platform (directional, not yet scoped)

The long-range vision from `DESIGN_BIBLE.md`: a marketplace of
user-authored agents and strategies, multi-company play, and TradeTown
as a genre rather than a single game. v2.0 is intentionally the horizon
line of this roadmap, not a committed feature list — it exists here so
that every decision made between v0.4 and v1.0 can be checked against
"does this make v2.0 easier or harder," the same way every decision
today is checked against `DESIGN_BIBLE.md`'s pillars.
