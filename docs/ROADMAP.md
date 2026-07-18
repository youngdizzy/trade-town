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
**Status: Completed**

No gameplay, no new systems, no trading. This version produced the
design and architecture documents every future version is built against
— the twelve documents in `docs/` alongside this roadmap
(`DESIGN_BIBLE.md`, `AI_AGENT_BIBLE.md`, `UI_UX_BIBLE.md`,
`COMPANY_LORE.md`, `NEXUS_ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`,
`CODING_STANDARDS.md`, `TASK_BACKLOG.md`, `KNOWN_LIMITATIONS.md`,
`FUTURE_ARCHITECTURE.md`, `ARCHITECTURE_REVIEW.md`) plus this file. v0.3
continued to run exactly as it did before this version — nothing in
`backend/` or `frontend/src/` changed as part of v0.4.

---

## Version 0.5 — Intelligence Evolution
**Status: Completed**

> **Note on scope drift:** this document originally planned v0.5 as a
> narrow "Coach explains, never scores" release, with Simulation Lab
> (v0.6), Paper Trading (v0.7), and Hall of Fame (part of v0.8) as
> separate later milestones. The v0.5 brief that actually started this
> version combined all of them into one release — per this document's
> own rule ("the brief for each version ... is the final word on what
> ships"), the brief supersedes the plan below it. What's documented
> here for v0.5 is what actually shipped; the old v0.6/v0.7 sections
> that predicted this content are removed rather than kept as stale
> duplicates. See `docs/VersionHistory.md` for the authoritative
> feature list.

Coach (a sixth agent, Performance & Improvement) reviews completed
research and closed paper trades and — unlike the original plan above —
does score, rank, and recommend, filing weekly/monthly `CoachReport`s
surfaced in a new Coach Dashboard. A Simulation Lab room runs
placeholder strategy backtests (`simulation.py`). A Paper Trading engine
(`portfolio.py`, `paper_trading.py`) opens and closes fully simulated
positions from high-confidence research completions — the first version
to spend the "future trade candidate" flags introduced in v0.3. A Hall
of Fame room celebrates the company's best records. A Learning System
turns every closed paper trade into a `lesson`/`mistake` Company Memory
record. A seven-metric Company Score is shown in the Brain Room.

**Depends on:** v0.3's `CompanyMemory`/`future_trade` records and
`MarketDataProvider` adapter pattern (both shipped). **Stop condition:**
no live brokerage support, no connection to any real broker, no
execution of a single real trade — every `PaperOrder`/`PaperPosition`/
`PaperTrade` is simulated bookkeeping only.

## Version 0.6 — Strategy Marketplace
**Scope (planned):** Player-authored or player-curated research
strategies (which symbols to prioritize, which research categories to
weight) become shareable, importable configurations — not code, not
plugins with arbitrary execution, just structured priority data
consumed by `research.py`'s existing rotation logic. This is the
first version where TradeTown's simulation becomes partially
player-authored rather than purely observed. v0.5's `Strategy` model
(currently agent-authored, used by the Simulation Lab) is the natural
extension point — a player-curated strategy would be a new `Strategy`
row like any agent-authored one, not a parallel data model.

**Depends on:** v0.3's `research.py` rotation logic (shipped), v0.5's
`Strategy`/Simulation Lab (shipped), a save-file schema extension for
shareable strategy configs. **Stop condition:** strategies configure
*priority and emphasis* within the existing research pipeline; they
cannot inject arbitrary code or bypass the one-active-item-per-agent
model.

## Version 0.7 — Risk Engine
**Scope (planned):** A company-wide risk posture becomes visible and
manageable beyond v0.5's single risk-score number — position
concentration across the paper portfolio, confidence-vs-outcome
calibration per agent (building on `coach.py`'s `AgentScore.
confidenceCalibration`, already computed per report), and a
dedicated risk-focused HUD panel. This is the last version before v1.0
and exists specifically to make the company's own fallibility legible
before any real-money question is even on the table.

**Depends on:** v0.5's Paper Trading (needs a ledger to compute risk
against) and Company Score (`riskManagement` metric, shipped as a
single number this version would break out further). **Stop condition:**
risk is measured and displayed, never auto-hedged or auto-corrected
without the player.

## Version 1.0 — Live Brokerage Support (re-authorization required)
**Scope (planned, gated):** The earliest point at which a real,
optional, explicitly opt-in brokerage connection becomes possible,
building on the `MarketDataProvider` adapter pattern for market data and
a parallel, separately-designed execution adapter for order placement.
This milestone does **not** ship a live connection by default — it ships
the *capability*, behind a deliberate, separately-scoped authorization
that must restate and re-affirm every boundary in `DESIGN_BIBLE.md`
before any order-placing code is written. Everything from v0.5–v0.7
(Coach, Simulation Lab, Paper Trading, Hall of Fame, Strategy
Marketplace, Risk Engine) exists specifically so this version has real
scaffolding to build on instead of starting from zero trust.

**Depends on:** v0.5 (Paper Trading, for the execution UX and ledger
model), v0.7 (Risk Engine, for pre-trade risk checks). **Stop condition:**
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
