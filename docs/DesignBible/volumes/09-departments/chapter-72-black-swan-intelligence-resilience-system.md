# Chapter 72 — Black Swan Intelligence & Resilience System (BSIRS)

**Status:** Part 1 (Early Warning Score, Risk Level, Stress Tests,
Scenario Simulations, Defensive Mode, Playbook, Crisis Briefings,
Post-Event Analysis) and Part 2 (Institutional Survival Score) both
implemented as real synthesis layers — backend (`app/black_swan.py`,
`app/routers/black_swan.py`) and frontend (a real `BLACKSWAN` Command
Center tab, `BlackSwanPanel.tsx`). See **Part 2** at the end of this chapter
for the Survival Score's own honesty boundary. The
brief asks TradeTown to detect and simulate Flash Crashes, Banking
Failures, Pandemics, Cyberattacks, Sovereign Debt Crises, and Broker
Failures with named historical calibration (2008, 2020, 1987, Dot-Com).
This codebase has none of that: no macro data (Chapter 71 already
established this), no real broker connection (`app/broker.py`'s own
docstring: "no code path that reaches a real order-execution endpoint"),
no sector/credit/funding data, and no historical black-swan dataset to
calibrate a probability against. What shipped instead is real: a new
**Early Warning Score** built entirely from eight already-real signals
this company had never combined into one stress read; a **Black Swan
Risk Level** (the named GREEN→CRITICAL tier Chapter 66 and Chapter 70
each already flagged as a real, un-built gap); portfolio-wide **Stress
Tests** and **Scenario Simulations** that extend `app/whatif.py`'s own
real volatility-scaled shock convention from one candidate trade to the
whole book; a real, CEO-controllable **Defensive Mode** that tightens
real `RiskLimits` and pauses new trade generation (never touches an open
position — see Implementation Notes for why); and a **Crisis Briefing** /
**Post-Event Analysis** pair that writes real, permanent Company Memory
and Knowledge Graph records. See Implementation Notes for the complete,
itemized honesty boundary.

## Executive Summary

The brief's thesis — "TradeTown should never assume normal market
conditions" — does not require a real 2008 dataset to be true. It
requires this company to notice, in real time, when its own already-real
signals (risk warnings, market quality, volatility, correlation,
concentration, regime agreement, news risk, macro health) are all
drifting toward stress at once, and to have a real, pre-built response
ready before that happens. That gap was real and closeable — Chapters 66
and 70 both independently named it and left it unbuilt. This chapter
closes it, and refuses to invent the historical-event layer this
codebase has no data to honestly support.

## Mission

Give the CEO one honest, always-current answer to "how much tail risk is
this company carrying right now, and why" — built from real signals this
company already computes every tick — plus a pre-built, real response
(Defensive Mode, a Playbook, on-demand Stress Tests) the CEO can act on
before a real drawdown happens, not just after.

## Philosophy

Most of this codebase's existing risk machinery (Sentinel, Guardian, the
Trade Gatekeeper) reacts to a single trade candidate or the portfolio's
own current drawdown. None of it asks the wider question a real risk
desk asks every morning: "if today were the day everything went wrong at
once, how bad would it be, and are we positioned defensively enough
right now?" Capital preservation outranks profit — every real mechanic
this chapter adds (Defensive Mode's tightened limits, the Stress Test's
honest recovery-time cut, the Playbook's manual-only position closes)
is built to be conservative by default, never to manufacture a number
that looks more sophisticated than the data backing it.

## Responsibilities

**Owns:** the Early Warning Score and Black Swan Risk Level (a genuinely
new named tier, GREEN/YELLOW/ORANGE/RED/CRITICAL — the exact gap Chapter
66's Ownership table and Chapter 70 Part 1's Emergency Board Meeting
table both already named and left unbuilt), the Black Swan Confidence
Read, the Situation Report / Narrative Engine, portfolio-wide Stress
Tests and Scenario Simulations, Defensive Mode (RiskLimits tightening +
new-proposal pause, CEO-controlled), the Black Swan Playbook, the Broker
Resilience read, Crisis Briefings, and Post-Event Analysis records.

**Does NOT own** (see Appendix E): any individual trade's risk gate
(Sentinel/Guardian, `app/risk_engine.py` — BSIRS reads their live warning
count, never recomputes or overrides a check), the Trade Gatekeeper
(`app/gatekeeper.py` — BSIRS does not add a Gatekeeper check this pass,
see Future Expansion), Market Regime/Quality/Correlation/Heat
classification (Chapters 65/56 and Market Intelligence — read-only,
exactly as Chapter 71 already established the same boundary), the
Economic Health Score (Chapter 71 — read-only input, not recomputed),
the Executive Board's real 9-department vote (`app/executive_intelligence.py`
— BSIRS's Crisis Briefing is a read-only situation report, never a new
vote), and closing or resizing any open position (never automatic,
anywhere in this chapter — see Implementation Notes).

## Ownership

Real code this chapter is authoritative over: `app/black_swan.py` (all
compute functions below), `app/routers/black_swan.py` (on-demand
endpoints), and the new `GameSaveState` fields
`black_swan_intelligence`/`black_swan_reports`/`defensive_mode`/
`black_swan_events`.

Six real, separate, already-shipped systems this chapter reads from but
never duplicates or recomputes:

- **Risk Engine** (`app/risk_engine.py`, v0.6) — the live `RiskWarning`
  list (Sentinel's hard gates, Guardian's standing watch) and
  `portfolio_equity()`. BSIRS's Active Risk Warnings factor and every
  Stress Test read these directly.
- **Market Intelligence** (`app/market_intelligence.py`) — real
  `MarketQualityScore`, `VolatilityRead` (current vs. historical-average
  volatility), `NewsRiskRead`, and per-symbol `LiquidityRead`. BSIRS's
  Market Stress, Volatility, News Severity, and Liquidity factors read
  these directly.
- **Portfolio Intelligence** (`app/portfolio_intelligence.py`, Chapter
  56) — real `CorrelationPair`s and `PortfolioHeat`. BSIRS's Correlation
  Breakdown and Concentration factors read these directly.
- **Regime Reconciliation** (`app/regime_reconciliation.py`, Chapter 65)
  — the real aligned/diverging read between the two independent regime
  classifiers. BSIRS's Regime Divergence factor calls
  `compute_regime_reconciliation()` fresh, the same "read, don't
  duplicate" pattern the module itself already established.
- **Economic Intelligence** (`app/economic_intelligence.py`, Chapter 71)
  — the real `EconomicHealthScore.tier`. BSIRS's Macro Instability factor
  reads it directly.
- **Accounts** (`app/accounts.py`, Chapter 69 Part 1) — every real
  Account's own `PaperPortfolio`. Stress Tests and Scenario Simulations
  accept any portfolio (the primary one or any Account's), so the
  brief's "run against Personal/IRA/Business/Prop Firm/Family" ask is
  real for free, without BSIRS inventing a second portfolio model.

## Inputs

`RiskWarning` list, `MarketIntelligenceState`, `PortfolioIntelligence`,
`MarketEnvironmentState`, `EconomicIntelligenceState.health.tier` — all
five already computed every tick by `app/nexus.py::tick()` before BSIRS
runs, so the always-current Early Warning Score adds no new real-data
dependency. Stress Tests and Scenario Simulations additionally take
whichever `PaperPortfolio` the CEO selects (primary or any Account) plus
that portfolio's own real held-symbol candles from
`app/market_data.py`.

## Outputs

- `BlackSwanIntelligenceState` (`state.black_swan_intelligence`) — the
  always-current read: Early Warning Score (8 named factors), Risk
  Level, Confidence Read. Recomputed fresh every tick, same convention
  as `company_health`/`portfolio_intelligence`/`economic_intelligence`.
- `BlackSwanReport` (`state.black_swan_reports`, capped at
  `MAX_BLACK_SWAN_REPORTS = 60`) — one permanent daily Situation Report,
  embedding that day's state plus a real, diffed narrative.
- `DefensiveModeState` (`state.defensive_mode`) — current activation
  status, trigger configuration, the real prior-`RiskLimits` snapshot
  (for exact revert), and the live recommendation list.
- `BlackSwanEventRecord` (`state.black_swan_events`, capped at
  `MAX_BLACK_SWAN_EVENTS = 40`) — one permanent Post-Event Analysis per
  completed Defensive Mode episode.
- `GET /api/black-swan/intelligence` — the current read.
- `GET /api/black-swan/reports` — the daily Situation Report history.
- `POST /api/black-swan/stress-test` — on-demand ladder (-10/-20/-35/
  -50/-70%) against a chosen portfolio.
- `POST /api/black-swan/scenario` — on-demand named scenario simulation
  against a chosen portfolio.
- `POST /api/black-swan/defensive-mode` — activate/deactivate, configure
  trigger tier and auto-trigger.
- `GET /api/black-swan/playbook` — the current Elevated Risk Response
  Playbook, live-populated with today's real recommendations.
- `GET /api/black-swan/events` — the permanent Post-Event Analysis
  history.

## Internal Workflow

1. Every tick, immediately after `economic_intelligence` is recomputed,
   `compute_black_swan_intelligence()` builds the eight named factors,
   the weighted Early Warning Score, the Risk Level tier, and the
   Confidence Read.
2. If `defensive_mode.auto_trigger_enabled` and the new tier has reached
   `defensive_mode.trigger_tier`, Defensive Mode auto-activates (applies
   the real `RiskLimits` tightening formula, snapshots the prior limits,
   sets the new-proposal pause). If auto-trigger is off, the tier crossing
   still surfaces as a normal `riskWarnings`-style signal for the CEO to
   act on manually.
3. The first time a tick's tier reaches RED or CRITICAL since the last
   Crisis Briefing, `generate_crisis_briefing()` fires once (not every
   tick), writing a permanent `CompanyMemory` record and a
   `black_swan_event` Knowledge Graph node.
4. Once per real in-game evening (`is_evening`, the same gate Chapters 71
   and Market Intelligence's own daily reports use),
   `generate_black_swan_report()` diffs the current read against the
   most recently stored report and records a new `BlackSwanReport`.
5. When Defensive Mode deactivates (a manual CEO action always; an
   auto-triggered episode also auto-deactivates the moment the tier next
   reads below its own `trigger_tier` — no separate "stability window"
   is fabricated), `deactivate_defensive_mode()` writes one permanent
   `BlackSwanEventRecord` — real portfolio equity at activation vs.
   deactivation, real duration, and a computed "largest contributing
   factor" lesson.
6. Stress Tests and Scenario Simulations are computed fresh per request,
   never persisted — the same "no reason to risk save-payload bloat for
   a read that's just as honest recomputed live" convention
   `app/whatif.py`'s own docstring already established.

## Decision Logic

**Early Warning Score** — eight named, independently-readable factors,
each 0–100 (higher = more stress), blended by a disclosed weighted
average:

| Factor | Weight | Source |
|---|---:|---|
| Active Risk Warnings | 0.20 | `min(100, 35×critical_count + 15×warning_count)` from the live `RiskWarning` list |
| Market Stress | 0.15 | Market Intelligence's `MarketQualityScore.tier`, inverted (avoid_trading 95 … excellent 5) |
| Volatility | 0.15 | `VolatilityRead.current_pct` vs. `historical_avg_pct` ratio, `30 + (ratio−1)×70`, clamped 0–100 |
| Liquidity | 0.10 | `100 − average(LiquidityRead.liquidity_score)` across currently-held symbols |
| Correlation Breakdown | 0.10 | `min(100, 20 × clustered pair count)` — the same real Pearson pairs Chapter 71 reads, weighted the opposite direction |
| Regime Divergence | 0.10 | `compute_regime_reconciliation()`'s aligned/diverging read, adjusted by its own cautious/opportunistic posture |
| News Severity | 0.10 | Market Intelligence's `NewsRiskRead.risk_level` (elevated 85 … low 15) |
| Macro Instability | 0.10 | Chapter 71's `EconomicHealthScore.tier`, inverted (critical 95 … thriving 10) |

**Black Swan Risk Level** — GREEN (<25) / YELLOW (<45) / ORANGE (<65) /
RED (<85) / CRITICAL (≥85) off the weighted overall score — the exact
"Safety Level / Capital Defense Mode" state machine Chapter 66's own
Ownership table and Chapter 70 Part 1's Emergency Board Meeting table
both named as a real, un-built gap, assembled here from real signals
rather than fabricated.

**Confidence Read** — same structure as Chapter 71's
`EconomicConfidenceRead`: a 50% floor, +6.25 points per factor backed by
genuine measurement (Liquidity needs ≥1 held symbol with data;
Correlation needs ≥2 open positions; all six others are always real),
capped at 100%. Supporting/contradicting evidence cites the specific
factors scoring above/below 50 (the "more stress" midpoint). The
alternative-outcome statement recomputes the score with only the single
worst-scoring factor swapped to a neutral 50 and reports whether that
alone would change the tier — this is BSIRS's honest answer to the
brief's "always explain WHY the estimate changed": every Situation
Report's narrative cites the specific real factor(s) that moved since
the last report, never invented causality.

**Portfolio Stress Test** — for a chosen portfolio and a shock percentage
(the brief's own -10/-20/-35/-50/-70% ladder), every open position's
current value is shocked uniformly; resulting equity, drawdown (vs. the
portfolio's real starting balance, the same fixed-reference convention
`total_pnl_pct` already uses), whether `RiskLimits.max_drawdown_pct`
would be breached, and whether resulting equity survives above zero are
all real, direct arithmetic. Recovery Time is a real but honestly-capped
projection: if the portfolio's trailing 30-day realized daily P&L
average is positive, days-to-recover = loss ÷ that average; otherwise the
result reports "N/A — no positive trailing performance to project a
recovery from," never a fabricated ETA.

**Scenario Simulation** — reuses `app/whatif.py`'s own real convention
(every shock expressed as a multiple of the symbol's own measured
per-bar volatility, never an absolute invented percentage), applied
across every open position at once instead of one candidate trade. Four
scenarios, each mechanically grounded, none carrying a fabricated
historical narrative: **Flash Crash** (reuses `whatif.py`'s own
`flash_crash` shock, −4× per-bar volatility, one instant bar), **Severe
Selloff** (a sustained −1.5× volatility drift over the hold window),
**Liquidity Freeze** (reuses `whatif.py`'s `liquidity_sweep` shock
convention, −2× volatility spike-and-fail-to-recover), and **Correlation
Breakdown Shock** (every position shocked in the same, worse-for-the-
portfolio direction at the largest single position's own measured
volatility — modeling "diversification fails exactly when it's needed").

## Department Cooperation

**Receives (read-only):** Risk Engine, Market Intelligence, Portfolio
Intelligence, Regime Reconciliation, Economic Intelligence, Accounts.

**Provides:** the Early Warning Score/Risk Level/Confidence Read and
Situation Reports to the CEO-facing dashboard; Crisis Briefings to
Company Memory (`category="alert"`) the moment the tier first crosses
into RED/CRITICAL; and Post-Event Analysis records to Company Memory
(`category="lesson"`) **and** the Knowledge Graph (a new
`black_swan_event` node type, sourced from the real, persisted
`BlackSwanEventRecord` list — same "same symbol, same category, direct
id link" honesty rule Chapter 61's own Knowledge Graph docstring already
enforces, never an inferred causal link). Crisis Briefings themselves are
computed fresh and written straight into Company Memory, not persisted
as a second list — the permanent record of a completed episode is the
Post-Event Analysis. Does **not** provide anything to the Trade
Gatekeeper or Executive Board vote pipeline this pass — see
Implementation Notes.

## CEO Controls

`defensive_mode.trigger_tier` (which Risk Level auto-activates Defensive
Mode — GREEN/YELLOW/ORANGE/RED/CRITICAL, default RED),
`defensive_mode.auto_trigger_enabled` (opt-in; off by default — the
brief's own "CEO may choose automatic or manual activation"), and manual
activate/deactivate at any time regardless of the auto-trigger setting.
No CEO-configurable Early Warning Score weight profile this pass (same
deliberate scope-limit Chapter 71 already chose for its own Economic
Health Score weights, to avoid scope creep beyond what the dashboard
actually needs).

## Learning System

Every completed Defensive Mode episode writes one permanent
`BlackSwanEventRecord` (Post-Event Analysis) via Company Memory's
`"lesson"` category and a new Knowledge Graph node — a real, queryable,
permanent record of what triggered it, how long it lasted, what the
portfolio's real equity did across the episode, and which factor
contributed most. No forecast is graded (there is no forecast made to
grade — the Confidence Read's alternative-outcome statement is
diagnostic, not predictive), matching Chapter 71's own identical
boundary for its Narrative Engine.

## KPIs

None fabricated. `EarlyWarningScore.overall`/`.tier` and the count of
real `BlackSwanEventRecord`s on file are the only published outputs;
there is no separate "how good has BSIRS been" accuracy metric because
BSIRS makes no falsifiable prediction (a Risk Level is a real-time
reading, never a forecast of a specific future event) to grade.

## Reports

**Daily Black Swan Situation Report only** (`BlackSwanReport`, once per
real in-game evening) plus **Crisis Briefings** (event-triggered, when
the tier first reaches RED/CRITICAL) and **Post-Event Analysis**
(episode-triggered, when Defensive Mode deactivates). The brief's own
Weekly/Monthly cadence, and any report keyed to a fabricated historical
event name, are explicitly cut — see Implementation Notes.

## Safety Systems

BSIRS has real, but deliberately bounded, safety authority. Defensive
Mode can automatically tighten `RiskLimits` (halving `max_position_pct`,
`max_daily_loss_pct`, `risk_per_trade_pct`, and `max_open_positions`)
and pause new AI-generated trade proposal generation — the same class of
automatic, reversible, forward-only action Chapter 66's `pause_trading`
and Chapter 67's Global Emergency Stop already established as safe.
BSIRS **never** closes, resizes, or otherwise touches an existing open
position automatically, anywhere, under any tier — see Implementation
Notes for why this line is drawn exactly here. BSIRS does not
participate in the Trade Gatekeeper pipeline this pass (see Future
Expansion).

## Dependencies

`app/risk_engine.py`, `app/market_intelligence.py`,
`app/portfolio_intelligence.py`, `app/regime_reconciliation.py`,
`app/economic_intelligence.py`, `app/accounts.py`, `app/whatif.py` (the
shock-convention constants it reuses), `app/memory.py`,
`app/knowledge_graph.py` — all read-only or additive. No new dependency
on any external service, API, or credential.

## Connected Features

`GET /api/black-swan/*` sits alongside `GET /api/market/economic-
intelligence` in the same "cross-signal reconciliation over real,
already-computed state" family. The Crisis Briefing/Post-Event Analysis
pair is this codebase's first Knowledge Graph writer outside Chapter
61's original launch set (research, Academy, trades, strategies) —
proof the graph's node-type list is meant to keep growing as real new
event types are added, exactly as that chapter's own docstring expects.

## Future Expansion

A Trade Gatekeeper wiring (BSIRS's Risk Level as one more advisory-only
check, identical in shape to Chapter 70 Part 3's Weighted Executive
Decision Engine wiring — not built here, to avoid bundling a decision-
pipeline change into this chapter's first pass); a CEO-configurable
Early Warning Score weight profile; per-Account Defensive Mode
(currently scoped to the CEO's global `RiskLimits` only); and — only if
this codebase ever gains a real broker connection (Chapter 68's own
gate) — real Broker Resilience monitoring in place of today's honest
static "SIMULATED" read.

## Company Principle

The greatest trading system is not the one that earns the most during
easy markets. It is the one that survives the hardest markets — and
survival starts with never claiming to know more about a coming crisis
than the company's own real data actually supports.

## Implementation Notes

**The honesty boundary, explicit and complete.** This codebase has no
historical black-swan dataset, no real broker connection, no macro/
credit/funding data (Chapter 71 already established this), and no
sector/asset-class taxonomy (Chapters 56/65/71 all already established
this). Given that, the brief's sections below are cut outright:

- **Named historical scenarios** (2008 Financial Crisis, 2020 Pandemic
  Crash, Dot-Com Collapse, 1987 Crash, Regional Banking Crisis, Interest
  Rate Shock, Oil Crisis, Currency Collapse) — no real calibration data
  exists for any of them; presenting a made-up shock magnitude under a
  real historical event's name would misrepresent it as calibrated. The
  four scenarios that shipped (Flash Crash, Severe Selloff, Liquidity
  Freeze, Correlation Breakdown Shock) are named for their real
  mechanism, not a real event, exactly like `app/whatif.py`'s own
  existing scenario set.
- **Banking Failure / Pandemic / Cyberattack / Sovereign Debt Crisis
  scenario types specifically** — would require fabricating sector,
  macro, or security data this codebase has zero real source for (no
  cybersecurity signal exists anywhere, confirmed against Chapter 66's
  own Future Expansion list).
- **A calibrated "Black Swan probability"** — no historical base rate
  exists to calibrate against; the Early Warning Score and Risk Level
  are real-time stress readings, never presented as a probability of a
  specific future event. "Likely Duration" and "Affected Asset Classes"
  are cut for the same reason (no asset-class taxonomy, no duration
  dataset) — Stress Tests report real per-category impact instead, using
  the real `CategoryExposure` this codebase already has.
- **Broker Resilience monitoring** (API failure, order delays, partial
  fills, connection loss detection) — `app/broker.py`'s own docstring
  confirms no real broker connection exists to monitor. BSIRS ships the
  honest static read instead: "SIMULATED — no real broker connection
  exists." Chapter 68's own architecture doc gates real monitoring
  behind an actual broker integration that does not exist yet.
- **Automatic emergency Executive Board meetings** — Chapter 70 Part 1
  already confirmed no automatic meeting-trigger mechanism exists for
  any event, and named Black Swan events specifically as one of the two
  (of seven) triggers with no underlying signal to fire from. BSIRS ships
  a **Crisis Briefing** instead — a real, permanent situation report
  reusing the exact same real signals a meeting would need, honestly
  named as a briefing rather than a vote, since no general-purpose,
  non-trade-scoped Decision Center exists for it to convene through
  (also confirmed absent by Chapter 70 Part 1).
- **Automatic position closing ("Close Weak Positions" applied
  automatically)** — `app/portfolio_intelligence.py`'s own docstring
  already states this codebase's binding principle: "risk is measured
  and displayed, never auto-hedged or auto-corrected without the
  player." Defensive Mode's "Close Weak Positions" recommendation lists
  the real worst-performing open positions by unrealized P&L, but the
  CEO must close them manually through the existing Trading Floor
  controls — this line is never crossed automatically, regardless of
  Risk Level or auto-trigger configuration.
- **"Reduce Leverage"** — cut outright; no margin or leverage concept
  exists anywhere in this codebase (100% simulated cash-account,
  long-only paper trading, confirmed by Chapter 68's own Ownership
  table).
- **"Increase Evidence Threshold"** — cut this pass; wiring a dynamic
  confidence-threshold override into `app/gatekeeper.py` is a real,
  separately-scopeable Gatekeeper change (see Future Expansion), not
  bundled into this chapter's first pass, the same deliberate boundary
  Chapter 71 drew around its own Gatekeeper wiring.
- **8 distinct named Playbooks** (Flash Crash Response, Broker Failure
  Response, Exchange Outage Response, Market Halt Response, Liquidity
  Crisis Response, Cyberattack Response, Pandemic Response, Bank Failure
  Response) — most reference subsystems that don't exist (a real broker,
  a real exchange connection, a cybersecurity signal). One real,
  generically-named **Elevated Risk Response Playbook** shipped instead,
  live-populated with today's actual Defensive Mode recommendations
  rather than eight static, partly-fictional documents.
- **A Communication Plan** section within the Playbook — cut; this is a
  single-player game with no other real stakeholders to communicate
  with.
- **Weekly/Monthly Situation Reports** — cut for this pass, same
  reasoning Chapter 71 already applied to its own report cadence.

**What IS real:** the Early Warning Score's eight factors, the Risk
Level tier, the Confidence Read, the Situation Report narrative, the
Portfolio Stress Test ladder, the four Scenario Simulations, Defensive
Mode's real `RiskLimits` tightening and new-proposal pause, the Elevated
Risk Response Playbook, the honest static Broker Resilience read, Crisis
Briefings, and Post-Event Analysis — all described in full under
Decision Logic above, each traceable to a real, already-computed signal
or a real, disclosed formula.

**Files changed this pass:** `app/schemas.py` (new
`BlackSwanRiskTier`/`BlackSwanSignalFactor`/`EarlyWarningScore`/
`BlackSwanConfidenceRead`/`BlackSwanIntelligenceState`/`BlackSwanReport`/
`DefensiveModeState`/`DefensiveModeRecommendation`/
`PortfolioStressTestResult`/`PortfolioScenarioResult`/`BlackSwanPlaybook`/
`BrokerResilienceRead`/`CrisisBriefing`/`BlackSwanEventRecord`, plus four
new `GameSaveState` fields); `app/black_swan.py` (new module); `app/
state.py` (default-state init); `app/nexus.py` (per-tick recompute +
Defensive Mode auto-trigger + Crisis Briefing/Post-Event Analysis
triggers + daily cadence); `app/save_modules.py` (module-field registry);
`app/ws_manager.py` (broadcast payload); `app/routers/black_swan.py`
(new router, 7 endpoints); `app/main.py` (router registration);
`tests/test_black_swan.py`. Verification: `mypy app/` clean, `ruff check
app/ tests/` clean, full `pytest -q` passing, zero regressions.

**What's genuinely still unbuilt:** every item in the honesty-boundary
list above, the Trade Gatekeeper wiring, a CEO-configurable weight
profile, and per-Account Defensive Mode — all deliberate, all
documented, none silently dropped.

---

## Part 2 — Institutional Survival Score

**Status:** Implemented (`app/black_swan.py`,
`GET /api/black-swan/survival-score`). A second brief asked for a
continuously-updating 0-100 Institutional Survival Score with a letter
grade (A+ through F), named Primary Strengths/Weaknesses, computed Top 5
Improvements, and an "Estimated Survival Probability," built from twelve
named inputs (Cash Reserves, Diversification, Leverage, Liquidity,
Concentration Risk, Drawdown Exposure, Broker Health, Counterparty Risk,
Rule Compliance, Black Swan Readiness, Stress Test Results, Portfolio
Correlations).

**The honesty boundary, explicit and complete.** Two of the twelve named
inputs are cut outright:

- **Leverage** — no margin or leverage concept exists anywhere in this
  codebase; Chapter 68's own architecture doc confirms 100% simulated
  cash-account, long-only paper trading. There is nothing real to score.
- **Counterparty Risk** — `app/broker.py` is pure in-process order logic
  with no real broker connection (its own docstring: "no code path that
  reaches a real order-execution endpoint"), so there is no real
  counterparty to be at risk from.

**"Estimated Survival Probability" is cut entirely.** This codebase has
no historical black-swan dataset to calibrate a statistical probability
against — the identical honesty rule Part 1 already applied to cut a
calibrated "Black Swan probability." The Survival Score itself (0-100,
with nine named, published factors) is the honest, transparent answer to
"how prepared is this company" — it is never presented as a forecasted
probability of surviving a specific future event.

**What IS real: nine named, published, weighted factors** — never a
black-box blend, the same convention every score in this Design Bible
already follows:

| Factor | Weight | Source |
|---|---:|---|
| Cash Reserves | 0.15 | Real `cash_pct_of_equity`, published thresholds |
| Drawdown Exposure | 0.15 | Real room remaining before `RiskLimits.max_drawdown_pct` |
| Stress Test Survival | 0.15 | Real count of the 5-level shock ladder survived without breach |
| Diversification | 0.10 | Reused from the Early Warning Score's own Correlation Breakdown factor, inverted |
| Concentration Risk | 0.10 | Portfolio Heat tier, published table |
| Liquidity | 0.10 | Reused from the Early Warning Score's own Liquidity factor, inverted |
| Rule Compliance | 0.10 | Reused from the Early Warning Score's own Active Risk Warnings factor, inverted |
| Black Swan Readiness | 0.10 | Half from whether Defensive Mode auto-trigger is configured, half from the inverse Early Warning Score |
| Broker Health | 0.05 | Fixed, disclosed baseline (80/100) — not a fabricated live number, for the identical reason `BrokerResilienceRead` above is static |

Three of the nine factors are **reused, never recomputed**, from the
Early Warning Score's own already-computed factors (Correlation
Breakdown, Liquidity, Active Risk Warnings) — inverted back from "how
stressed" to "how resilient," the same non-duplication discipline every
other cross-signal synthesis in this Design Bible already follows.

**Primary Strengths/Weaknesses** are the top/bottom three real, named,
scored factors. **Top 5 Improvements** are the five lowest-scoring
factors' own real detail strings — never generic filler like "diversify
more." Grade thresholds (A+ ≥95, A ≥85, B ≥70, C ≥55, D ≥40, F <40) are
disclosed and published, the same "conservative but arbitrary, no real
capital or regulatory requirement behind them" honesty note `RiskLimits`
itself already carries.

**Files changed this pass:** `app/schemas.py` (new
`InstitutionalSurvivalGrade`/`SurvivalScoreFactor`/
`InstitutionalSurvivalScore`, plus one new `GameSaveState` field);
`app/black_swan.py` (new `compute_institutional_survival_score()` and
supporting constants); `app/state.py` (default-state init); `app/nexus.py`
(per-tick recompute); `app/save_modules.py`; `app/ws_manager.py`;
`app/routers/black_swan.py` (new `GET /survival-score` endpoint);
`tests/test_black_swan.py` (16 additional tests). Verification: `mypy
app/` clean, `ruff check app/ tests/` clean, full `pytest -q` — 1198
passed (1159 pre-existing + 39 new across both Parts 1 and 2), zero
regressions.
