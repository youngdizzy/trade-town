# Chapter 71 — Economic Intelligence Center (EIC)

**Status:** Implemented as a real cross-signal synthesis layer — backend
(`app/economic_intelligence.py`, `GET /api/market/economic-
intelligence` and `.../reports`) and frontend (a real `ECONINTEL`
Command Center tab, `EconomicIntelPanel.tsx`). This chapter's brief was written as if
TradeTown had live feeds into central banks, an economic calendar, and
global news — it has none of these (see `app/market_data.py`'s own
module docstring: "this repo holds no API keys"). Most of the brief's
named sections are therefore explicit, documented cuts, not partial
implementations. What shipped is real: a new Economic Health Score, an
Economic Confidence Engine, and a Market Narrative Engine, all built
honestly from three departments' already-real state (Market Environment,
Market Intelligence, Portfolio Intelligence) that had no shared read
until now. See the Implementation Notes for the full honesty boundary.

## Executive Summary

The brief's thesis — "TradeTown should never analyze charts in
isolation; every market exists inside a larger economic environment" —
is sound, but this codebase's "larger economic environment" is not a
real macro feed. It is the company's own already-real trading-signal
state, computed once in three separate places (regime, market quality,
portfolio correlation/concentration) with no single view tying them
together. That gap is real and closeable; a live Federal Reserve feed is
not. This chapter closes the real gap and names the unreal one honestly
rather than fabricating it.

## Mission

Give the CEO one honest, evidence-cited answer to "how healthy is our
current operating environment, and why" — built entirely from real,
already-computed signals, never from an invented macro number — with
confidence and named supporting/contradicting evidence attached to every
read, exactly as the brief's own Economic Confidence Engine section
requires.

## Philosophy

Markets move because of people; people respond to economics. This
codebase cannot honestly claim to model "economics" in the macro sense —
it has no inflation, interest rate, GDP, or central bank data anywhere.
What it *can* honestly claim is a real trading-signal environment (a
regime, a quality read, a correlation structure), and the discipline this
whole Design Bible already applies everywhere else — never invent a
number with no real backing signal — applies here without exception.

## Responsibilities

**Owns:** the Economic Health Score (five named, published factors —
never a black-box blend), the Economic Confidence Engine (confidence,
evidence quality, named supporting/contradicting evidence, key
assumptions, one computed alternative-outcome statement), and the Market
Narrative Engine (a real, evidence-cited daily diff against the
company's own last stored report).

**Does NOT own** (see Appendix E): Market Regime classification (Chapter
65's `app/market_environment.py` — EIC reads it, never recomputes it),
Market Quality/News Risk/session/volatility/momentum/liquidity reads
(the Market Intelligence Department, `app/market_intelligence.py` —
same, read-only), Correlation/Category Exposure/Portfolio Heat (Chapter
56's `app/portfolio_intelligence.py` — same, read-only), any Executive
Board vote (see Ownership below), and Trade Gatekeeper authority (EIC
does not feed the Gatekeeper in this pass — see Implementation Notes).

## Ownership

Three real, separate, already-shipped systems this chapter reads from
but does not own or duplicate:

- **Market Environment** (`app/market_environment.py`, Chapter 65) — the
  real 5-way regime (bull/bear/sideways/high_volatility/low_volatility).
  EIC's Regime Favorability factor reads `current`/`label` directly.
- **Market Intelligence** (`app/market_intelligence.py`) — the real
  `MarketQualityScore` (0-100) and `NewsRiskRead` (low/moderate/elevated,
  a named proxy for the count of on-file market-category news). EIC's
  Market Quality and News Risk factors read these directly.
- **Portfolio Intelligence** (`app/portfolio_intelligence.py`, Chapter
  56) — the real `CorrelationPair` list (Pearson correlation from real
  mock candle returns, pre-filtered to pairs clearing
  `CORRELATION_CLUSTER_THRESHOLD`) and `PortfolioHeat` (largest
  position/concentration tier). EIC's Correlation Clustering and
  Concentration factors read these directly.

EIC's own new ownership is strictly the synthesis on top: the weighted
Economic Health Score, the Confidence Engine wrapper, and the Narrative
Engine's day-over-day diff. It never recomputes a value one of the three
systems above already owns.

## Inputs

`MarketEnvironmentState` (current tick), `MarketIntelligenceState`
(current tick), `PortfolioIntelligence` (current tick) — all three
already computed every tick by `app/nexus.py::tick()` before EIC runs,
so EIC adds no new real-data dependency and no new per-tick cost beyond
five cheap table lookups and a weighted sum.

## Outputs

- `EconomicIntelligenceState` (`state.economic_intelligence`) — the
  always-current read: regime, market quality tier, `EconomicHealthScore`,
  `EconomicConfidenceRead`, the current correlation pairs/category
  exposure/news risk. Recomputed fresh every tick, same "cheap, never a
  stale second copy" convention as `company_health`/`portfolio_intelligence`.
- `EconomicIntelligenceReport` (`state.economic_intelligence_reports`,
  capped at `MAX_ECONOMIC_INTELLIGENCE_REPORTS = 60`) — one permanent
  daily snapshot, embedding that day's `EconomicIntelligenceState` plus a
  real `MarketNarrativeEntry`.
- `GET /api/market/economic-intelligence` — the current read.
- `GET /api/market/economic-intelligence/reports` — the daily history.

## Internal Workflow

1. Every tick, immediately after `portfolio_intelligence` is recomputed,
   `compute_economic_intelligence()` builds the five named factors and
   the weighted `EconomicHealthScore`, then wraps it in an
   `EconomicConfidenceRead`.
2. Once per real in-game evening (`is_evening`, the same gate Market
   Intelligence's own daily Executive Market Brief uses),
   `generate_economic_intelligence_report()` diffs the current read
   against the most recently stored daily report (never the previous
   tick, to avoid re-narrating the same read every five simulated
   minutes) and records a new `EconomicIntelligenceReport`.
3. The Narrative Engine names only real, computed deltas — a regime
   change, a health-tier change, a news-risk-level change, a change in
   the count of clustered correlation pairs — never invented causality.

## Decision Logic

**Economic Health Score** — five named, independently-readable factors,
each 0-100, blended by a disclosed (not fitted/backtested) weighted
average:

| Factor | Weight | Source |
|---|---:|---|
| Regime Favorability | 0.25 | Market Environment regime → published table (bull 85 … bear 30) |
| Market Quality | 0.25 | Market Intelligence's own `MarketQualityScore.score`, passed through |
| News Risk | 0.20 | Market Intelligence's `NewsRiskRead.risk_level` → published table |
| Correlation Clustering | 0.15 | `100 - 20 × (clustered pair count)`, floored at 20 |
| Concentration | 0.15 | Portfolio Heat tier → published table (cool 90 … overheated 15) |

Tier boundaries reuse Market Intelligence's own 80/65/45/25/0 scale
(`thriving`/`stable`/`cautious`/`stressed`/`critical`).

**Economic Confidence Engine** — confidence starts at a 40% floor and
gains 12 points per factor backed by genuine measurement (Regime/
Quality/News Risk are always real; Concentration needs ≥1 open position;
Correlation needs ≥2), capped at 100%. Evidence quality is `thin`
(≤3 real factors), `moderate` (4), or `strong` (5). Supporting/
contradicting evidence lists cite the specific factors scoring
above/below 60. The alternative-outcome statement is computed, not
templated: it recomputes the score with only the single worst-scoring
factor swapped to a neutral 60 and reports whether that alone would
change the tier.

## Department Cooperation

**Receives (read-only):** Market Environment, Market Intelligence,
Portfolio Intelligence.

**Provides:** the Economic Health Score, Confidence Read, and daily
Narrative to the CEO-facing dashboard/report. Does **not** currently
provide anything to the Executive Board, Trade Gatekeeper, or any other
decision pipeline — see Implementation Notes for why, and for the
precedent (Chapter 70 Part 3) for how that could change as an explicit
future addendum.

## CEO Controls

None yet. EIC is read-only in this pass — no CEO-configurable weight
profile, no override. A future pass could offer the same kind of
CEO-selectable weighting Chapter 70 Part 3's Weighted Executive Decision
Engine already established (`WeightProfile`), but that is not built here
to avoid scope creep beyond what the daily brief actually needs.

## Learning System

None built this pass. The Narrative Engine's day-over-day diff is real
evidence of change, but there is no formal grading loop (no "did the
Economic Health Score's tier correctly anticipate what happened next" —
that would require a forecast this module deliberately does not make).
Market Intelligence's own Learning Loop is the closer real analog and is
not duplicated here.

## KPIs

None fabricated. `EconomicHealthScore.overall`, `.tier`, and
`EconomicConfidenceRead.confidence_pct` are the real, already-published
outputs; there is no separate "how good has EIC been" metric because EIC
makes no falsifiable prediction to grade.

## Reports

**Daily Economic Intelligence Brief only** (`EconomicIntelligenceReport`,
once per real in-game evening). The brief's own Weekly Economic Summary,
Monthly Outlook, Quarterly Economic Forecast, Sector Rotation Report, and
Macro Risk Report are explicitly cut — see Implementation Notes.

## Safety Systems

EIC has no safety authority and does not participate in the Trade
Gatekeeper pipeline (Chapters 58/66/70 Part 3 addendum) in this pass. It
cannot block, delay, or approve a trade. It is a read-only intelligence
layer, the same standing Market Intelligence itself had before it was
separately, explicitly wired into the Executive Board as a ninth voting
department.

## Dependencies

`app/market_environment.py`, `app/market_intelligence.py`,
`app/portfolio_intelligence.py` — read-only. No new dependency on any
external service, API, or credential (there are none in this codebase to
depend on).

## Connected Features

`GET /api/market/economic-intelligence` and `.../reports` sit alongside
`GET /api/market/regime-reconciliation` (Chapter 65) in
`app/routers/market.py` — both are cross-signal reconciliation endpoints
over the same underlying real state, not chart data.

## Future Expansion

A CEO-configurable weight profile (mirroring Chapter 70 Part 3's
`WeightProfile`); a Weekly/Monthly Economic Outlook report reusing the
existing `WEEKLY_INTERVAL_DAYS`/`MONTHLY_INTERVAL_DAYS` cadence hooks;
and — only if a future addendum explicitly asks for it, per the Chapter
70 Part 3 precedent — wiring the Economic Health Score into the Trade
Gatekeeper as one more advisory-only check, identical in shape to the
Weighted Executive Decision Engine's own wiring.

## Company Principle

Understand the real environment before analyzing a single chart — but
never claim to understand an environment this company has no real data
for. Honesty about what is and isn't known is itself a form of economic
intelligence.

## Implementation Notes

**The honesty boundary, explicit and complete.** This codebase has zero
real macroeconomic data sources: no API keys, no live feed of any kind
(`app/market_data.py`'s own docstring: "this repo holds no API keys"),
and `app/market_intelligence.py` had already, independently, named "any
real economic calendar" as something explicitly not built for the same
reason. Given that, the brief's sections below are cut outright rather
than half-built:

- **Central Bank Intelligence** (Fed/ECB/BOJ/BOE/PBOC rate decisions,
  minutes, speeches) — no real data source anywhere.
- **A real Economic Calendar** (CPI/PPI/NFP/FOMC/GDP releases, consensus
  estimates, Treasury auctions) — already an explicit prior cut in
  `market_intelligence.py`; not reopened here.
- **Global Event Intelligence** (wars, elections, disasters, geopolitical
  conflicts) with estimated probability/severity/impact — no real
  geopolitical data source; inventing a probability for an event that
  doesn't exist in this codebase is exactly the fabrication
  `app/confidence.py`'s own docstring already refuses to do.
- **Real macro indicators and any AI forecast of them** (inflation,
  interest rates, GDP, unemployment, PMI, Treasury yields, DXY, global
  liquidity, recession probability, rate expectations) — no real data
  source, and critically, no mechanic anywhere in this codebase these
  numbers would even feed: there is no bond market, no currency market,
  no interest-rate-sensitive position. An invented interest rate here
  would be decorative, not functional — the exact "fake progression"
  this Design Bible forbids.
- **A Sector Impact Engine keyed to real named sectors** (Technology,
  Financials, Healthcare, ...) — this codebase has no real sector
  taxonomy anywhere; `app/portfolio_intelligence.py`'s own
  `CategoryExposure` docstring and `app/risk_engine.py`'s
  `evaluate_guardian_exposure()` both already established this identical
  honesty note before this chapter existed. Category-based exposure (the
  real thing this codebase has) is read, not renamed into a fake sector.
- **Scenario Planning** (Bull/Base/Bear/Black Swan cases with
  probability/positioning) tied to macro outcomes this module does not
  forecast — cut. `app/whatif.py`'s "SIMULATED"-labeled Simulation Lab is
  the closer real fit for hypothetical position outcomes and already
  exists; not duplicated here.
- **Weekly/Monthly/Quarterly reports, Sector Rotation Report, Macro Risk
  Report** — cut for this pass; see Future Expansion. Building five
  separate report types over the same five real factors would fragment
  one honest daily synthesis into redundant documents.

**What IS real:** the Economic Health Score's five factors, the
Confidence Engine, and the Narrative Engine — all described in full
under Decision Logic above, each traceable to a real, already-computed
signal this codebase produced before this chapter existed.

**Deliberate scope decision — not a 10th Executive Board vote.**
`ExecutiveDepartmentRole` is unchanged. EIC's own signal set overlaps
heavily with Market Intelligence's (both read the same regime); adding a
structurally-near-duplicate voting seat would cut against this Design
Bible's "avoid duplicate systems and overlapping responsibilities"
principle for no real new information. EIC ships as a standalone
dashboard/report layer instead — see the Chapter 70 Part 3 addendum
(Weighted Executive Decision Engine wired into the Trade Gatekeeper) for
the established precedent that an advisory system gets wired into a
decision pipeline only as an explicit, separately-scoped follow-up, not
bundled into its first pass.

**Files changed this pass:** `app/schemas.py` (new
`EconomicHealthTier`/`EconomicSignalFactor`/`EconomicHealthScore`/
`EconomicConfidenceRead`/`MarketNarrativeEntry`/`EconomicIntelligenceState`/
`EconomicIntelligenceReport`, plus two new `GameSaveState` fields);
`app/economic_intelligence.py` (new module); `app/state.py` (default-state
init); `app/nexus.py` (per-tick recompute + daily cadence + snapshot
dict); `app/save_modules.py` (module-field registry); `app/ws_manager.py`
(broadcast payload); `app/routers/market.py` (two new GET endpoints);
`tests/test_economic_intelligence.py` (21 tests: factor scoring, tier
boundaries, confidence evidence classification, narrative diffing —
including an explicit test that the narrative never mentions "fed",
"interest rate", "inflation", "gdp", or "central bank" — report-cap
trimming, and two real end-to-end nexus tests proving the daily cadence
actually fires via `GameState.advance_time("workday_end", ...)`).
Verification: `mypy app/` clean, `ruff check app/ tests/` clean, full
`pytest -q` — 1159 passed (1138 pre-existing + 21 new), zero regressions.

**What's genuinely still unbuilt:** every item in the honesty-boundary
list above, a CEO-configurable weight profile, Weekly/Monthly reports,
and any Gatekeeper/Executive Board wiring — all deliberate, all
documented, none silently dropped.
