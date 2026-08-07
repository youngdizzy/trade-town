# Chapter 73.5 — Mobile Command Center & Remote Operations

**Status:** Implemented, backend (`app/travel_mode.py`,
`app/situation_room.py`, `app/routers/travel_mode.py`,
`app/routers/situation_room.py`) and frontend (real `SITUATIONROOM` and
`TRAVELMODE` Command Center tabs, `SituationRoomPanel.tsx` and
`TravelModePanel.tsx`). Numbered 73.5 (not 74) at the CEO's explicit
direction, so it sits between Chapter 73 (Compliance/Audit) and Chapter 75
(Company Trading Modes) without disturbing either chapter's real number.

Scoped as a real, honest subset — a responsive Command Center layout,
a single-screen Executive Situation Room, a CEO Priority Engine, and a
real Travel Mode operating posture (backend + frontend). TradeTown is
a single-player, accountless, browser-only game with one client type,
one simulated broker, no external accounts, and no native app shell —
confirmed fresh against the current codebase (223 commits) that it
still has no push-notification, biometric, speech-recognition,
wearable, geolocation, or offline-caching infrastructure of any kind.
The brief's "Mobile Command Center" is written for a native iOS/
Android app talking to a real brokerage; large parts of it (native
Push Notifications, Voice Commands, Watch Support, biometric/PIN/
Device Verification, service-worker Offline Mode, Location tracking,
multiple real brokerage-linked portfolios, "Lock Company") describe
infrastructure this codebase does not have and this pass does not
invent. What ships instead is real: the same Command Center the CEO
already uses on desktop, now genuinely usable one-handed on a phone
browser, a new single-screen "what needs my attention right now" view
built almost entirely from fields that already have one real computed
source, a formalized priority ranking that extends Chapter 67's
existing 3-tier toast system rather than replacing it, and a real,
CEO-configurable conservative operating posture (Travel Mode) that
composes with the exact same derived-override seam Company Priority
and Chapter 75's Daily Circuit Breaker already use — confirmed to be
one of exactly three tightening patterns this codebase has, never a
fourth, invented one. See Implementation Notes for the complete,
itemized honesty boundary.

## Executive Summary

The brief's real thesis — "the CEO should never lose awareness of the
company, wherever they are" — does not require a native app to be true
today. TradeTown already runs in any browser, including a phone's;
what it lacked was a layout that worked at phone width, one screen
that answers "what needs my attention right now" without hunting
across `GlobalStatusBar`/`QuickView`/`OverviewPanel` (three real,
overlapping-but-incomplete subsets of the same picture, confirmed by
fresh research — none of the three is a full synthesis today), and a
real notion of "I'm about to be away — get more careful while I'm
gone." This chapter builds exactly those three things, reusing real
data and real mechanics that already exist rather than duplicating
them under a new "mobile" brand.

## Mission

Make the company's real, already-computed state genuinely readable and
actionable from a phone-width browser window, and give the CEO a real
way to tell the company "be more careful, I won't be watching closely
for a while" — without fabricating infrastructure (accounts, push,
voice, biometrics, wearables, offline caching) this codebase has no
honest way to back yet.

## Philosophy

Awareness and control do not require a second app. They require the
same real state the desktop Command Center already renders, laid out
so a thumb and a 6-inch screen can use it, and one formal answer to
"of everything happening right now, what actually needs the CEO's eyes
first" — not three separate partial dashboards competing for
attention.

## Responsibilities

**Owns:** the Executive Situation Room aggregate (`SituationRoomState`,
computed fresh each request, almost entirely from fields that already
have exactly one real computed source — see Inputs), the CEO Priority
Engine (`rank_priorities()` — extends Chapter 67's existing
`critical`/`high`/`normal` toast tiers with a fourth `low` tier for
quiet, log-only items, never replacing the three that already exist),
Travel Mode (`TravelModeState`/`TravelModeSettings`, a real
CEO-configurable posture that derives a tightened `RiskLimits` and a
raised Gatekeeper confidence bar per tick, composing with Chapter 75's
own `_effective_risk_limits()`/`min_confidence_override` seam), and the
responsive Command Center layout (frontend-only, no new backend
surface).

**Does NOT own:** Emergency Stop itself (`app/emergency_stop.py` —
Situation Room and Quick Actions call the same real
`activate_emergency_stop()`/`resume_trading()` Chapter 67 already
wired, never a second implementation), the Operating Mode switch
(`settings.operating_mode` — reused, not duplicated; Travel Mode never
changes it), trade approve/reject/modify/hold/delegate (`app/
executive.py`'s four real actions — reused verbatim, see Inputs), or
Risk Limits enforcement (`app/risk_engine.py` — Travel Mode derives an
override the same way Company Priority and the Circuit Breaker already
do; it never adds a second enforcement path).

## Ownership

Real code this chapter is authoritative over: `app/situation_room.py`
(new — `compute_situation_room()`, `rank_priorities()`),
`app/travel_mode.py` (new — `activate_travel_mode()`,
`deactivate_travel_mode()`, `apply_travel_mode_tightening()`,
`should_auto_activate()`, `generate_travel_mode_briefing()`),
`app/routers/situation_room.py` (new, read-only),
`app/routers/travel_mode.py` (new). Extends (does not duplicate):
`app/audit_log.py`'s `_entries_from_memory()` (one new
`elif m.category == "alert" and m.title.startswith("Travel Mode")`
branch mapped to a new `travel_mode_change` `AuditEventCategory` value
— the exact template Chapter 75's `trading_mode_change`/
`circuit_breaker_tier` branches already established), `app/
gatekeeper.py` (`min_confidence_override` — already a parameter as of
Chapter 75, now fed by `max(circuit_breaker_bonus,
travel_mode_bonus)` rather than either alone), `app/nexus.py`
(`_effective_risk_limits()` — already the seam Company Priority and
Chapter 75 both use for exactly this kind of derived, per-tick
override; Travel Mode composes into it, it does not replace it).

## Inputs

Confirmed by fresh research to already have exactly one real computed
source, reused verbatim, never recomputed independently: `company_health.
overall`/`.tier` (Ch63), `portfolio_intelligence.heat.tier` (the
closest existing "Portfolio Health" signal, already documented as such
in `GlobalStatusBar.tsx`), `paper_portfolio.cash_balance` and open
`positions`, `risk_warnings`/`riskLevel()` (Sentinel/Guardian),
`market_environment.current`/`.label` (Ch65), `trading_modes` state
(Ch75), `economic_intelligence.health` (Ch71's real
`compute_economic_health()`), `black_swan_intelligence.warning.tier`
(Ch72's real `EarlyWarningScore`), `emergency_stop.active`, `settings.
operating_mode`. Two fields have no existing single source and are
computed fresh by this chapter: **Pending CEO Decisions**
(`len(trade_proposals)` — `TradeProposal` has no `status` field;
presence in the list *is* "pending," confirmed by fresh research) and
**Executive Consensus** (the most recently created pending
`TradeProposal`'s own real `analyst_votes` agreement rate — `Weighted
ExecutiveRecommendation.consensus_pct` is computed transiently at
decision-resolution time and never persisted, confirmed by fresh
research, so it cannot be read back for a "most recent" value; the
proposal's own real votes are the honest, always-available substitute).
Travel Mode additionally reads the sim-minute timestamp of the CEO's
most recent real action on a proposal (decide/hold/modify) for its
inactivity-based automatic activation.

## Outputs

- `GET /api/situation-room` — `SituationRoomState`: the thirteen-field
  single-screen summary (Company Health, Portfolio Health, Cash
  Position, Open Risk, Market Regime, Trading Mode, Economic Health,
  Black Swan Risk, Executive Consensus, Pending CEO Decisions, Broker
  Status, Automation Status, Emergency Alerts), plus
  `priorities: list[PriorityItem]` — the CEO Priority Engine's ranked
  output.
- `GET /api/travel-mode` — current `TravelModeState` (active, settings,
  activated-at, activation source).
- `POST /api/travel-mode/activate` / `/deactivate` — manual CEO toggle;
  deactivate returns the real Return-to-Operations briefing.
- `PATCH /api/travel-mode/settings` — updates `TravelModeSettings`
  (position-size cap, daily-risk cap, notification sensitivity,
  inactivity-based auto-activation on/off and its threshold).
- One new `AuditEventCategory` value (`travel_mode_change`) flows into
  Chapter 73's existing `GET /api/audit/log` — no new log surface, the
  same template Chapter 75 already used.

## Internal Workflow

1. `compute_situation_room()` reads the eleven already-real state
   sources plus the two newly-computed fields above, maps each to one
   of five severity bands (`good`/`caution`/`elevated`/`severe`/
   `critical`, a disclosed per-field threshold table — see Decision
   Logic), and returns one flat object — never a second,
   independently-computed read of any of these numbers.
2. `rank_priorities()` walks the same real backend sources (never the
   frontend's own toast/alert history, which is a client-side view
   built from the same underlying signals) and assigns each actionable
   item one of four tiers: `critical` (Emergency Stop active, a
   `critical` Risk Warning, a Black Swan `red`/`critical` tier),
   `high` (a pending CEO decision while Circuit Breaker tier ≥ 2, an
   `orange` Black Swan tier), `medium` (a pending decision below tier
   2, a `caution`-band field), `low` (everything else — real, logged,
   never surfaced as an interruption) — extending Chapter 67's
   existing three-tier `CyberNotifications` shape with a fourth tier
   for the first time.
3. On each `nexus.py` tick, if Travel Mode is active,
   `apply_travel_mode_tightening()` runs immediately after Chapter 75's
   own `apply_circuit_breaker_tightening()` inside
   `_effective_risk_limits()`, scaling `max_position_pct`/
   `risk_per_trade_pct`/`max_open_positions` by the CEO's own
   configured `TravelModeSettings`, and computes a confidence bonus the
   same way Chapter 75's tiers do — the two bonuses compose via
   `max()`, never silently overriding one another.
4. `should_auto_activate()` runs once per tick only when the CEO has
   enabled inactivity-based auto-activation: if `now -
   last_ceo_decision_sim_minutes >= settings.
   autoActivateAfterMinutes`, Travel Mode activates with
   `activationSource="auto_inactivity"` and an Audit Log entry is
   written; it never activates itself for any other reason (no
   calendar, no clock-time-of-day, no location — confirmed this
   codebase still has none of those at 223 commits).

## Decision Logic

**Situation Room severity bands** — a disclosed, five-tier mapping
table per field (e.g. Company Health: ≥80 `good`, ≥60 `caution`, ≥40
`elevated`, ≥20 `severe`, else `critical`; Black Swan Risk and Economic
Health reuse their own chapters' real tier names directly rather than
remapping them) — see `app/situation_room.py`'s module docstring for
the complete table. Every threshold is a plain, checkable cutoff over
a real number, the same "disclosed and simple on purpose" honesty
already established for Chapter 73's Compliance Score.

**Priority Engine tiers** — see Internal Workflow step 2. `critical`
items are the only ones this pass allows to bypass Travel Mode's
notification filter — matching the brief's own "only Critical
interrupts the CEO" rule for the addendum.

**Travel Mode tightening — reuses one of exactly three existing
patterns, confirmed by fresh research, never a fourth.** This
codebase has precisely three real mechanisms that already tighten
`RiskLimits` or the Gatekeeper's confidence bar: Company Priority's
`_effective_risk_limits()` (derived, non-persisted), Chapter 72's
Defensive Mode (persisted mutate-with-snapshot-restore via
`priorRiskLimits`), and Chapter 75's Daily Circuit Breaker (derived,
non-persisted, explicitly modeled on Company Priority's own pattern).
Travel Mode deliberately reuses the **derived, non-persisted** pattern
— composing into `_effective_risk_limits()` alongside Company Priority
and the Circuit Breaker — rather than Defensive Mode's snapshot-
restore, because Travel Mode's `active`/`settings` are already real,
CEO-owned persisted state in their own right (`TravelModeState`); a
second snapshot of `RiskLimits` underneath that would be a redundant,
driftable copy of state this chapter doesn't need. Factors: CEO-
configurable within a disclosed floor (position-size cap: 25%-75% of
the account's normal max, default 50%; daily-risk cap: 25%-75% of
normal, default 50%; `max_open_positions` halved, floor of 1) — the
identical factor-over-real-limits shape Defensive Mode and the Circuit
Breaker already use, not a new formula.

**Notification sensitivity filter** — three CEO-selectable levels
(`all`, `high_and_above` [default while Travel Mode is active],
`critical_only`) gate which Priority Engine tiers actually push a
toast via Chapter 67's existing `CyberNotifications` pipeline;
filtered-out items still land in the Priority Engine's own ranked list
and the Audit Log, so nothing is silently dropped — only its
interruption is suppressed, matching the brief's own "MEDIUM grouped...
LOW silently logged" instruction.

## Department Cooperation

**Receives (read-only):** Executive Board (`consensus_pct`-equivalent
via the pending proposal's own votes), Trade Gatekeeper, Risk Engine,
Market/Economic/Black Swan Intelligence, Chapter 75's Trading Modes,
Chapter 67's Alert Center/`CyberNotifications`, Chapter 73's Audit
Log.

**Provides:** a confidence bonus composed into the Gatekeeper
(alongside Chapter 75's own, via `max()`), a derived `RiskLimits`
override composed into `_effective_risk_limits()` (alongside Company
Priority and the Circuit Breaker), and one new Audit Log entry
category. Travel Mode is the third real mechanism to compose through
this same seam, not a fourth parallel one.

**Explicitly not wired this pass (disclosed, not silently dropped):**
Chapter 61's Knowledge Graph. Confirmed by fresh research: the
Knowledge Graph has no `MemoryRecord`-category edge type today, so a
Travel Mode `MemoryRecord` would not automatically appear in it
without new graph-side wiring this chapter does not add — noted under
Future Expansion.

## CEO Controls

`TravelModeSettings`: manual activate/deactivate, position-size cap,
daily-risk cap, notification sensitivity level, inactivity-based
auto-activation on/off and its threshold (15-240 simulated minutes).
No scheduled (calendar-based) activation — see Implementation Notes.

## Learning System

None built this pass. Travel Mode's tightening factors are CEO-set,
not learned or backtested — the same honesty already disclosed for
`RiskLimits` itself and reused unmodified here.

## KPIs

None new. Travel Mode's real effect is already visible through
existing numbers (Circuit Breaker tier, Company Health Score, realized
P&L while active) — no separate "Travel Mode performance score" is
computed or claimed.

## Reports

The Return-to-Full-Operations briefing: on deactivation,
`deactivate_travel_mode()`/`generate_travel_mode_briefing()` returns a
real summary built from real records covering the exact activation
window — CEO decisions resolved, Gatekeeper rejections, critical Risk
Warnings, Circuit Breaker tier-change `MemoryRecord`s, and realized
P&L — the same "build the summary from real records in the window,
never a templated recap" convention Chapter 72's Defensive Mode
deactivation (its own real Post-Event Analysis) already established.
No separate Morning/Midday/Evening daily briefs — see Implementation
Notes.

## Safety Systems

Travel Mode cannot itself activate Emergency Stop — it only tightens
`RiskLimits` and the Gatekeeper's confidence bar, composing with
existing safety systems rather than replacing them. It shares Chapter
75's own safety ceiling: at Circuit Breaker tier 4 or an active
Emergency Stop, Travel Mode's tightening is moot — the stricter real
control already governs.

## Dependencies

`app/trading_modes.py`, `app/gatekeeper.py`, `app/black_swan.py`,
`app/economic_intelligence.py`, `app/executive_intelligence.py`,
`app/audit_log.py`, `app/nexus.py`, `app/state.py`, `app/memory.py`
(`record()`'s real `max_records` cap param). No new external
dependency — no PWA plugin, no notification SDK.

## Connected Features

`GET /api/situation-room` sits alongside Chapter 73's `GET
/api/audit/overview` in the same "cross-cutting, computed-fresh,
read-only synthesis" family. Travel Mode sits directly beside Chapter
75's Trading Modes in `app/nexus.py`'s own override-composition
seam — the two are meant to be read together.

## Future Expansion

If this codebase ever gains real accounts/sessions, the biometric/
PIN/Device Verification and Remote Logout sections become buildable
without fabrication. If it ever gains a real push-notification relay
(a backend web-push subscription store plus a service worker), the
brief's Push Notifications section becomes a real, honest extension of
the Priority Engine's tiers rather than a new design. A `MemoryRecord`
-category edge type for Chapter 61's Knowledge Graph, so Travel Mode's
own activation history becomes graph-connected to the decisions made
during it. None of these are built here.

## Company Principle

The CEO's phone should show the same truth the desk does — not a
simplified copy of it, and never a feature that only pretends to exist
because the brief asked for it.

## Implementation Notes

**The honesty boundary, explicit and complete.** Cut outright rather
than half-built, because fresh research confirms this codebase still
has no real infrastructure to back them at 223 commits, and a
decorative version would violate this project's own
No-Placeholder-Systems rule:

- **Native Push Notifications (APNs/FCM), Voice Commands, Watch
  Support** — cut. No push-relay/device-token infrastructure, no
  speech-recognition engine, no watchOS/WearOS companion exists or is
  built here (confirmed: zero matches for any such infra anywhere in
  `frontend/src` or `backend/app`). Chapter 67's in-app
  `CyberNotifications`/Alert Center, now ranked by the new Priority
  Engine, is the honest browser-based analog for awareness; there is
  no honest analog for voice input or a wrist display.
- **Biometric Authentication, PIN, Device Verification, Session
  Timeout, Remote Logout, "Lock Company"** — cut entirely. Confirmed
  fresh (again matching Chapter 73's own earlier finding): zero
  authentication or session concept anywhere in this codebase, at any
  commit. There is exactly one player and one client; there is
  nothing to verify a device against and no session to lock or time
  out.
- **Offline Mode (cached dashboards, queued decisions, auto-sync)** —
  cut. No service worker, no PWA manifest, no `vite-plugin-pwa`
  anywhere in this repo (confirmed fresh by direct inspection of
  `vite.config.ts`/`index.html`/`package.json`). A browser tab with no
  network simply shows stale data, same as it always has — no new
  offline-queue mechanic is built.
- **Location field in Command History, Mobile Portfolios (Personal/
  IRA/Business/Prop Firm/Family), Mobile Broker Control (multiple
  connected brokerage accounts)** — cut. No geolocation API is called;
  there is one client, so a "device" field would always read the same
  constant. There is exactly one real, live-traded Company Portfolio
  in this codebase — no second real account type exists to show
  separately. `PaperBroker` is confirmed still 100% simulated with no
  external connection (its own module docstring: "no brokerage SDK
  import anywhere in this file... no code path that reaches a real
  order-execution endpoint") — there is no second broker, buying
  power, or connected-account list to control remotely.
- **Scheduled (calendar-based) Travel Mode activation** — cut. This
  codebase has no wall-clock/timezone/calendar concept tied to the
  player's real-life schedule — only a simulated in-game day counter.
  Inactivity-based automatic activation (Decision Logic above) is the
  one honest, measurable substitute: it reacts to a real signal (how
  long the CEO has actually gone without touching a pending decision)
  rather than a fabricated calendar.
- **A dedicated "Command History" log distinct from the Audit Log** —
  cut. Chapter 73 already built the real "timestamp/actor/action/
  result" pattern this brief asks for; Travel Mode's activate/
  deactivate events extend `AuditEventCategory` and flow into that
  same log rather than duplicating it under a new name.
- **A new Mobile Executive Board action set** — not needed. All four
  real CEO actions on a pending proposal (buy/sell/wait via
  `resolve_proposal`, Modify via `modify_proposal`, Hold/"Request More
  Research" via `hold_proposal`, Delegate as a `resolved_by`
  provenance tag) already exist and are reused verbatim — confirmed
  fresh, the full current list, no new action invented.

**What IS real:** the Executive Situation Room aggregate — eleven of
its thirteen fields reused verbatim from an already-real single
computed source, two computed fresh from already-persisted data — and
its disclosed severity-band table; the CEO Priority Engine's four-tier
ranking (extending Chapter 67's existing three); a real CEO-
configurable Travel Mode that composes through the same derived-
override seam Company Priority and the Circuit Breaker already share
(confirmed to be one of exactly three tightening patterns in this
codebase); inactivity-based automatic activation off a real timestamp;
a real Return-to-Operations briefing built from real records in the
activation window; a new Audit Log category following Chapter 75's
exact template; and a genuinely responsive (phone-width-usable)
Command Center layout — all described above.

**Files to change this pass:** `app/schemas.py` (new
`SituationRoomState`/`SituationRoomField`/`PriorityItem`/
`TravelModeState`/`TravelModeSettings`/`TravelModeBriefing`; extended
`AuditEventCategory`); `app/situation_room.py` (new module);
`app/travel_mode.py` (new module); `app/routers/situation_room.py`,
`app/routers/travel_mode.py` (new routers); `app/main.py` (router
registration); `app/nexus.py` (tick wiring, composing into
`_effective_risk_limits()`/`min_confidence_override`); `app/state.py`
(activate/deactivate/settings methods, bumping
`last_ceo_decision_sim_minutes` on the three real CEO-action call
sites); persistence's module map (wherever `trading_modes`/
`defensive_mode` are grouped, so Travel Mode is real, CEO-mutated
state, not `derived`); `app/ws_manager.py` (broadcast); `app/
audit_log.py` (one new `_entries_from_memory()` branch);
`tests/test_situation_room.py`, `tests/test_travel_mode.py`. Frontend:
a new `SituationRoomPanel`, a new `TravelModePanel`, responsive
breakpoints added to the Command Center shell and its densest panels.
Verification to run before marking complete: `mypy app/` clean, `ruff
check app/ tests/` clean, full `pytest -q` passing with zero
regressions; `tsc --noEmit`, `eslint`, `vite build` clean; a save/load
round-trip confirming an old save (predating these fields) migrates
cleanly; a full code review pass.

**What's genuinely still unbuilt:** every item in the honesty-boundary
list above, all deliberate and documented, none silently dropped.
