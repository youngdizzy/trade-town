# Chapter 65 — Market Regime Detection & Adaptive Strategy Engine

**Status:** One real slice implemented (backend + Command Center card).
Unlike a blank-slate chapter, this one describes a real, substantial
overlap: two independent, already-real, indicator-driven regime
classifiers exist in this codebase today, each with a historical
timeline, and one of them already computes a genuine Regime Confidence
Score. This chapter's smallest honest slice — reconciling the two into
one CEO-facing read, plus a read-only posture recommendation — is now
real, via `GET /api/market/regime-reconciliation` and the Company tab's
new Regime Reconciliation card. What still does not exist is the rest of
the brief's ask — CEO-configurable Adaptive Strategy Profiles per
regime, and an Automatic Adaptation mechanism that lets a detected
regime move any real company lever. See
[Volume 9's chapter template](README.md) for what every section below
must contain, and the Implementation Notes at the bottom for the exact
honesty boundary between what's real today and what a future
implementation would add.

## Executive Summary

Professional firms recognize that no single strategy performs best in
every market. TradeTown should identify the current market regime
before deciding how aggressively to trade. **Researched first, and the
finding here is more nuanced than Chapters 61–63's "already built under
a different name":** regime *detection* is real and already built —
twice over, in two separate modules that don't agree with each other —
but regime-*driven automatic control* of the company's real risk and
trading levers is a genuine, still-open gap. The company adapts to the
market; the market never adapts to the company — that principle is
honored by the detection layer today, but nothing yet acts on it
automatically.

## Mission

Give the CEO an honest, unified read on the market's current regime,
backed by real confidence, and — only when the CEO explicitly permits
it — let that regime recommend or apply real adjustments to the
company's own trading posture, never silently and never past the
CEO's own configured safety limits.

## Philosophy

A great strategy used in the wrong environment becomes a poor strategy.
Adaptation is a competitive advantage, but flexibility must always be
supported by evidence — never by excitement, and never by inventing a
number nothing in this codebase actually measures.

## Responsibilities

**Owns:** Market Regime Classification (already real, split across two
modules — see Ownership), Regime Confidence Scoring (already real),
Strategy-vs-Regime Evidence Matching (already real, at the Strategy Lab
level), and — the genuine new work — reconciling the two existing
regime reads into one CEO-facing answer, Adaptive Strategy Profiles,
and Automatic Adaptation.

**Does NOT own** (see Appendix E): Trade Execution, Risk Veto Authority
(Chapter 58's Trade Gatekeeper — this chapter may *recommend* a change
to a CEO-configurable risk lever, but the actual veto authority over any
single trade stays with the Gatekeeper, never duplicated here), Position
Sizing (Chapter 57 — this chapter never computes a trade's quantity;
at most it recommends new values for the same CEO-configurable
`RiskLimits` fields Chapter 57 already reads), Broker Communication.

## Ownership

Two real, separate, already-shipped classifiers this chapter does
**not** own but must honestly account for, both real and already
authoritative over their own domain:

| Real system | What it already does | Where it lives |
|---|---|---|
| `app/market_environment.py` (v0.7 Feature 22) | A coarse 5-way classifier (`bull`/`bear`/`sideways`/`high_volatility`/`low_volatility`) over aggregated real watchlist daily-change data — simple threshold math, no confidence score, no historical-pattern comparison. Real capped timeline (`MAX_MARKET_ENVIRONMENT_HISTORY = 100`) on real regime changes only. | `MarketEnvironmentState`, surfaced in the COMPANY tab's Market Environment card. |
| `app/market_intelligence.py` (v0.7 Feature 51) | A rich 13-way classifier (`strong_bull_trend`/`strong_bear_trend`/`weak_uptrend`/`weak_downtrend`/`sideways_range`/`expansion`/`compression`/`high_volatility`/`low_volatility`/`accumulation`/`distribution`/`liquidity_hunt`/`transitional`) over real OHLCV trend/volatility/structure/liquidity math. Already computes a real `MarketQualityScore` (`confidencePct` 0–90, `tier`: excellent/good/average/poor/avoid_trading) and `historicalSimilarity` (a real count of matching prior days). Real capped report/learning history. | `MarketIntelligenceState`, its own dedicated MARKETINTEL tab. |

Neither module reads the other. Neither is CEO-configurable in any way
today — no sensitivity, no minimum-confidence floor, no override.
`app/strategy_lab.py`'s `StrategyRegimeTestReport` already tags a
strategy's real backtested performance against each of the 13
`MarketIntelligenceRegime` buckets and downgrades a Strategy Executive
Review stance to `recommend_waiting` when today's live regime matches a
`weak` bucket — genuine regime-aware strategy governance, already real,
at review time only. `app/gatekeeper.py` and
`app/opportunity_gatekeeper.py` already gate on `MarketQualityScore.tier
== "avoid_trading"` as a binary pass/fail — real, but binary, never
graduated by confidence.

**Now real:** a reconciliation read (`app/regime_reconciliation.py`'s
`compute_regime_reconciliation()`) — one canonical `agreement`
(aligned/diverging) and `posture` (cautious/normal/opportunistic) read,
built entirely from the two real sources above via the existing
`REGIME_CONSISTENCY_MAP` (promoted from `market_intelligence.py`'s
private `_REGIME_CONSISTENCY_MAP`, never a third invented classifier),
computed fresh per request and never persisted. **Still not built:**
`AdaptiveStrategyProfile` schemas per regime, and the automatic-adaptation
write path (which would still only ever call the *existing*
`POST /api/risk-limits` endpoint — never a new, parallel write path to
`RiskLimits`).

## Inputs

Every input a real future implementation could honestly use already
exists: `MarketEnvironmentState` (5-way regime + timeline),
`MarketIntelligenceState` (13-way regime, `MarketQualityScore`,
volatility/session/momentum/liquidity/structure reads),
`StrategyRegimeTestReport` (per-strategy regime-bucket performance),
`RiskLimits` (every CEO-configurable lever a recommendation could
target). **Not a real input anywhere:** interest rates, an economic
calendar, sector-rotation data, or sentiment beyond the market-quality
composite already computed — this codebase has no real feed for any of
those, so a future implementation must not invent one (see Chapter 56's
own precedent for `NewsRiskRead`/institutional-activity being honestly
labeled as *proxies*, not the real thing the brief names).

## Outputs

**Real today:** `MarketEnvironmentState` (current regime + timeline),
`MarketIntelligenceState` (regime, `MarketQualityScore`,
`StrategyMatch`), `StrategyRegimeTestReport`, and now
`RegimeReconciliation` (`environmentRegime`/`environmentLabel`,
`intelligenceRegime`/`intelligenceLabel`, `qualityTier`,
`confidencePct`, `agreement`, `posture`, a plain-language `rationale`)
via `GET /api/market/regime-reconciliation`. **Not built:** an
`AdaptiveStrategyProfile` object per regime, any automatically-applied
change to a real `RiskLimits` field.

## Internal Workflow

**Real today, split across two independent pipelines:**
`app/market_environment.py`'s `evaluate_market_environment()` runs every
tick against aggregated watchlist data → `tick_market_environment()`
appends a timeline entry only on a real regime change.
`app/market_intelligence.py`'s `_classify_regime()` runs daily against
real OHLCV trend/volatility/structure/liquidity signals →
`compute_market_quality_score()` scores confidence/tier →
`compute_strategy_match()` recommends/avoids specific strategies →
`compute_historical_similarity()` compares against the real report
archive → the next day, `MarketIntelligenceLearningEntry` grades
yesterday's call against real outcomes. **Genuinely not built:** any
step reconciling the two, and any step past classification that
recommends a full `AdaptiveStrategyProfile` (risk budget, position size
guidance, trade-frequency guidance, swing-vs-day preference, capital
reserve, evidence/confidence-threshold guidance) or automatically
applies one.

## Decision Logic

**Real today:** `_classify_regime()`'s ordered-threshold logic (trend%,
volatility%, volatility-expansion ratio, liquidity-sweep share,
reversal share, volume-trend ratio) and `compute_market_quality_score()`'s
weighted composite (volatility-band fit, structure clarity, session
liquidity, sweep risk, news activity, capped at 90) — both real,
transparent, checkable formulas, never a black box, matching this
codebase's "no hidden weighting" convention. **Genuinely not built:**
any formula translating a regime + confidence into a recommended risk
posture. A future implementation's own Decision Logic would need to be
designed the same way — real, named, bounded, and explicitly NOT a
reuse of Chapter 59's trade-level Priority Score or Chapter 64's
goal-level urgency formula, since a regime-driven risk posture is a
structurally different computation over structurally different inputs.

## Department Cooperation

**Would receive from:** the two existing regime engines (Market
Environment, Market Intelligence), Chapter 61 (Knowledge Graph — real
historical pattern data already partially used via
`compute_historical_similarity()`), Chapter 62 (Innovation Lab — a
regime-driven research-focus recommendation). **Would send to:** the
CEO (a reconciled regime read + recommended profile), Chapter 57/58/59
(recommended values for their own already-CEO-configurable fields,
applied only through their own existing endpoints, never a new write
path this chapter owns).

## CEO Controls

| Control | Status |
|---|---|
| Regime Sensitivity | **Not built** — neither existing regime engine exposes a threshold knob. |
| Minimum Confidence floor | **Not built as a CEO-set control** — `MarketQualityScore.confidence_pct` now feeds a fixed, code-level `OPPORTUNISTIC_MIN_CONFIDENCE_PCT = 70.0` threshold inside `compute_regime_reconciliation()`'s posture read; no CEO-facing floor exists to change it. |
| Automatic Adaptation (toggle) | **Not built** — nothing in this codebase auto-adjusts any real lever from a detected regime today; the new posture recommendation is read-only, never applied to any `RiskLimits` field automatically. `SettingsState.company_priority` remains the closest existing "profile" concept, still CEO-set only. |
| Strategy Profiles (per-regime editor) | **Not built.** |
| Risk Multipliers (per-regime) | **Not built** — the one existing multiplier concept, `PRIORITY_RISK_TIGHTEN_FACTOR = 0.8` for `company_priority == "risk_reduction"`, is manually chosen by the CEO, not regime-driven. |
| Manual Override | **Already real in spirit** — the CEO's existing Operating Mode (learning/assisted/executive) and every `RiskLimits` field remain the CEO's own manual controls regardless of what any future regime recommendation says; nothing in this codebase can override a CEO's manual `POST /api/risk-limits` call. |

## Learning System

**Real today, at the Market Intelligence layer only:**
`MarketIntelligenceLearningEntry` already grades yesterday's regime
call against real next-day trade outcomes via
`_REGIME_CONSISTENCY_MAP`. **Not built:** any learning loop over a
regime-driven *adaptation* (there is no adaptation yet to learn from).

## KPIs

**Partially computable today:** Regime Detection Accuracy is a real,
checkable number via the existing Learning Loop above. **Not honestly
computable:** Strategy Performance by Regime beyond what
`StrategyRegimeTestReport` already buckets, Adaptation Success Rate,
Drawdown Reduction attributable to adaptation, False Regime
Classification Rate as a single unified figure (the two engines
disagree, so "false" would need to be defined against one canonical
source that doesn't exist yet).

## Reports

**Real today:** the Market Environment historical timeline, the Market
Intelligence report archive (60 days), the regime-learning archive.
**Not built:** a unified Regime Transition Report reconciling both
engines, an Adaptation History report (nothing adapts automatically
yet, so there is nothing to log), an Executive Market Summary distinct
from what `MarketIntelPanel.tsx` already shows.

## Safety Systems

Never change strategies without evidence — already respected: every
existing regime read is derived from real data, never invented. Never
increase risk because of excitement — a future Automatic Adaptation
must inherit the same recommend-only-until-CEO-permits boundary
Chapter 64's Resource Allocation already established, and must never
write past a CEO's own configured hard limits (`max_position_pct`,
`max_drawdown_pct` stay Chapter 57's exclusive domain, never writable
by a regime recommendation). Never ignore Risk Authority — any
regime-recommended change still passes through Chapter 58's Gatekeeper
on the next trade, exactly like a manual CEO change would.

## Dependencies

Chapter 61 (Knowledge Graph — real historical-pattern data), Chapter 56
(Enterprise Portfolio Intelligence — this chapter's real
`market_intelligence.py` module lives under that same v0.7 feature
umbrella), Chapter 57/58/59 (Position Sizing / Opportunity Gatekeeper /
Capital Priority — the real endpoints any future recommendation would
write through, never duplicate). **A note on the brief's own named
dependency:** "Chapter 53 — Probabilistic Trading Philosophy" does not
exist anywhere in this codebase or Design Bible under that number or
title — the same non-existent reference already checked and flagged in
Chapters 58, 59, and 60's own Dependencies sections; this brief repeats
the same citation and it is no more real here than there. Chapters
54–56 as named in the brief ("Executive Decision Simulator,"
"Enterprise Portfolio Intelligence," "Institutional Risk Authority")
are off by one against this volume's own real numbering: the brief's
"Chapter 54 — Executive Decision Simulator" is this volume's real
Chapter 55 (War Room); the brief's "Chapter 55 — Enterprise Portfolio
Intelligence" is this volume's real Chapter 56. The brief's
"Chapter 56 — Institutional Risk Authority" has no matching chapter at
all under this volume's real numbering (56 is Enterprise Portfolio
Intelligence, not Risk Authority) — the real risk-authority machinery
this brief is pointing at is distributed across the real Chapters 57/58
instead (Position Sizing, Trade Gatekeeper), never chaptered as its own
"Risk Authority" department. Both Chapters 54–56 remain pending in this
volume's own README regardless (real backend + frontend already
shipped, chapter not yet written) — the real systems exist, just not
under the brief's exact numbering.

## Connected Features

Chapter 64 (Strategic Planning — a regime-aware goal, e.g. "hold
portfolio return positive through a high-volatility regime," is a
plausible future `GoalMetric`, not invented here). Chapter 66 (Safety
Framework, this same batch — an extreme/avoid_trading regime read is
one of several real signals a future Safety Pyramid would consume, see
that chapter's own Dependencies).

## Future Expansion

Machine Learning Regime Detection, Global/Cross-Asset/Sector Regime
Analysis, Economic Cycle Modeling, Predictive Regime Forecasting all
require either more real market history than a fresh game has, real
multi-asset data this codebase's mock provider doesn't carry, or an LLM
dependency this codebase does not have (see Chapter 61's own Future
Expansion section for the same confirmed absence) — not invented or
stubbed here.

## Company Principle

TradeTown studies the market, understands the environment, and adapts
intelligently while remaining disciplined — but it only ever adapts
using numbers it actually computed, and only ever as far as the CEO
has explicitly permitted.

## Implementation Notes

**What's real today, found by direct research before this chapter was
written (not assumed):** two independent, real, indicator-driven regime
classifiers (`app/market_environment.py`'s 5-way, `app/market_intelligence.py`'s
13-way), a real Regime Confidence Score (`MarketQualityScore.confidence_pct`
+ `tier`), real regime-vs-strategy evidence matching at two levels
(department-level `StrategyMatch`, per-strategy `StrategyRegimeTestReport`),
a real binary regime-quality trading gate in both Gatekeepers, a real
Learning Loop grading yesterday's regime call, and two separate,
already-real Command Center surfaces (COMPANY tab's Market Environment
card, the dedicated MARKETINTEL tab) showing all of it. None of this
needed to be rebuilt, and this chapter does not claim otherwise.

**What was built (the smallest honest first slice):**
`app/regime_reconciliation.py`'s `compute_regime_reconciliation()`
combines `MarketEnvironmentState` and `MarketIntelligenceState` into one
`RegimeReconciliation` read — `agreement` (`aligned`/`diverging`,
computed by checking the intelligence engine's regime against the
existing `REGIME_CONSISTENCY_MAP`, promoted from
`market_intelligence.py`'s private `_REGIME_CONSISTENCY_MAP` rather than
duplicated) and `posture` (`cautious`/`normal`/`opportunistic`, derived
from `MarketQualityScore.tier` and `confidence_pct` against a fixed
`OPPORTUNISTIC_MIN_CONFIDENCE_PCT` threshold — `avoid_trading`/`poor`
tiers are always cautious regardless of confidence). Exposed via
`GET /api/market/regime-reconciliation`, computed fresh per request,
never persisted as a second driftable copy. Surfaced on the Command
Center's Company tab as a new "Regime Reconciliation" card, above the
existing Market Environment card. The posture is a read-only
recommendation only — nothing writes it to any `RiskLimits` field.

**What's still genuinely not built, and what a real future
implementation would need to design first (per Appendix G's Permanent
Development Policy — design before code):** an `AdaptiveStrategyProfile`
object per regime; an Automatic Adaptation toggle and its own real,
transparent, bounded formula for translating regime + confidence into a
recommended change to already-CEO-configurable `RiskLimits` fields; and
CEO Controls for sensitivity, a CEO-facing minimum-confidence floor,
per-regime profiles, and risk multipliers.
