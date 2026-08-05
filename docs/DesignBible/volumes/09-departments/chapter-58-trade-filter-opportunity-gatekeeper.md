# Chapter 58 — Institutional Trade Filter & Opportunity Gatekeeper

**Status:** Target design. Not yet implemented. See [Volume 9's chapter
template](README.md) for what every section below must contain, and the
Implementation Notes at the bottom of this chapter for exactly what's
real today versus new here.

## Executive Summary

Professional firms make money by rejecting thousands of mediocre
opportunities for every one they take. TradeTown should be the same:
selective by design, never asking "what can we trade today?" but "what
has earned the right to be traded today?" No candidate setup is entitled
to company capital or the CEO's attention.

**Researched first — this is not a new scoring engine.** Almost every
real signal this chapter needs already exists, computed by Chapter 55's
Digital War Room: `app/war_room.py`'s `build_decision_score()` already
combines Evidence, Confidence, Risk, Expected Value, Market Quality,
Liquidity Quality, and Portfolio Compatibility into exactly the 0–100
composite this chapter's brief calls a "Trade Quality Score," checked
against exactly the same kind of threshold the brief describes
(`DECISION_SCORE_THRESHOLD = 70.0`). `build_expected_value_analysis()`
already computes a real, probability-weighted Expected Value read. This
chapter's real, novel contribution is not a second scoring system — it's
moving that already-real judgment to the correct point in the pipeline
(**before** a candidate becomes a CEO-facing `TradeProposal`, not after)
and making its threshold a real CEO control instead of a fixed constant.
See "The Real Gap" below.

## The Real Gap

Today, exactly one filter stands between a research item and the CEO's
desk: `app/nexus.py`'s `_generate_trade_proposals()` requires
`item.confidence >= FUTURE_TRADE_CONFIDENCE_THRESHOLD` and nothing else
— no Evidence Score, no Expected Value, no Market Quality check, no
Decision Score. Every research item that clears that single number
becomes a real `TradeProposal` the CEO must personally review. The War
Room's real Decision Score and Expected Value **are** computed for every
proposal (`build_war_room_session()`, called from the same
`_generate_trade_proposals()` loop) — but only *after* the proposal
already exists, purely as information for the CEO to read, never as a
gate. Nothing in this codebase today ever stops a low-quality proposal
from reaching the CEO; the CEO does all the filtering personally, every
time. `app/gatekeeper.py`'s Trade Gatekeeper (Feature 20) is a real,
separate, *later*-stage check — it runs only after the CEO has already
picked buy/sell, against a different checklist entirely (confidence,
risk-manager alignment, multi-agent agreement, the AI Debate outcome,
exposure, correlation, active risk warnings, Market Intelligence
quality) that does not include Expected Value or the Decision Score at
all. This chapter does not replace Feature 20 — it adds the missing
*earlier* stage: an opportunity-quality gate between proposal generation
and CEO visibility.

There is also no ranking today: pending proposals are a flat,
first-generated-first-shown list capped by `MAX_PENDING_PROPOSALS`, with
no "highest-quality opportunities rise to the top" ordering the brief's
Opportunity Queue calls for.

## Mission

TradeTown should never feel pressured to trade. This engine exists to
reject poor opportunities before they ever reach the CEO — not to find
trades, but to eliminate bad ones. Every rejected opportunity protects
company capital; every opportunity that reaches the CEO has already
earned that attention.

## Philosophy

Patience is a competitive advantage. The company is rewarded for
discipline, not activity. The market provides endless opportunities;
TradeTown only accepts the highest-quality ones. Saying "no" is a
successful decision, not a missed one. **This principle is already true
of this codebase today** — there is no forced-trading mechanic anywhere;
a day, or a week, with zero trades has always been a legitimate outcome.
This chapter makes that philosophy real and *active* (a genuine
pre-filter) rather than merely *possible* (the CEO happening to reject
everything personally).

## Responsibilities

**Owns:** Pre-proposal Trade Filtering, Opportunity Quality Scoring
(reusing, not duplicating, the Decision Score), Trade Qualification,
Market Quality Evaluation at the pre-proposal stage, Evidence
Verification at the pre-proposal stage, pre-proposal Trade Rejection and
its record, Opportunity Queue Prioritization.

**Does NOT own** (see Appendix E, the Decision Authority Matrix):
Risk Management (Sentinel/Guardian, `app/risk_engine.py`); Position
Sizing (Chapter 57, `app/position_sizing.py`); Execution or Broker
Communication (`app/portfolio.py`, `app/broker.py`); Portfolio
Allocation (`app/portfolio_intelligence.py`); the **post**-CEO-choice
final approval gate — that stays Feature 20's `app/gatekeeper.py`,
unchanged, running exactly where it runs today.

## Ownership

Would extend `app/nexus.py`'s `_generate_trade_proposals()` (the one
real point where a candidate currently becomes CEO-visible with no real
quality gate) and reuse `app/war_room.py`'s `build_decision_score()` /
`build_expected_value_analysis()` / `DECISION_SCORE_THRESHOLD` without
modification. Would extend `app/schemas.py` with a new CEO-configurable
threshold on `RiskLimits` and a new pre-proposal rejection record
(`GatekeeperRejection`'s own docstring assumes a `TradeProposal` and a
real `ceoChoice` already exist — neither exists yet at this earlier
stage, so this needs its own honestly-named sibling record, not a
forced fit into the existing shape).

## Inputs

Every input below is a real signal already computed elsewhere in this
codebase, mapped to where it actually lives:

| Brief asks for | Already real, as |
|---|---|
| Market Intelligence / Market Quality | `app/market_intelligence.py`'s `MarketIntelligenceState.quality` (the same `avoid_trading` tier Feature 20's Gatekeeper already checks) |
| Evidence Score | `app/confidence.py`'s `compute_evidence_score()`, already folded into `DecisionScoreBreakdown.evidenceScore` |
| Confidence Score | `DecisionConfidence.score`, already folded into `DecisionScoreBreakdown.confidenceScore` |
| Expected Value | `app/war_room.py`'s `build_expected_value_analysis()`, over WhatIf Simulation's 12 real scenarios |
| Risk Analysis | Sentinel/Guardian's real `RiskWarning`s, already folded into `DecisionScoreBreakdown.riskScore` |
| Liquidity | `LiquidityRead`, already folded into `DecisionScoreBreakdown.liquidityQualityScore` |
| Portfolio Heat / Current Exposure | Chapter 56's `PortfolioHeat`, and `app/gatekeeper.py`'s existing exposure/correlation checks |
| Company Risk Budget | Chapter 57's real spendable weekly deployment budget (`RiskLimits.maxWeeklyDeploymentPct`) |
| Historical Statistics | `app/decision_vault.py`'s similar-trade summary, already reused by the War Room |
| Company DNA | `app/company_dna.py`'s five real traits — real and read-only today, but **not currently wired as a trade filter input anywhere**; a genuine, honest gap this chapter could close, not a claim that it already does |

**Not built, and not invented here** (same honesty boundary
`app/confidence.py`'s and `app/gatekeeper.py`'s own module docstrings
already establish for this exact overlapping list): a real Economic
Calendar or scheduled/advance news timing (this codebase generates news
reactively, never in advance); a real bid/ask Spread (only a single
simulated last price exists per symbol); multi-timeframe confirmation
(only one timeframe is ever fetched, `app/executive.py`'s
`PROPOSAL_TIMEFRAME`).

## Outputs

An approved candidate becomes exactly the same real `TradeProposal` this
codebase already produces today — nothing about its shape changes. A
rejected candidate never becomes a `TradeProposal` at all, and is instead
recorded as a real pre-proposal rejection (see Learning System). Pending
proposals gain a real ranking: shown to the CEO ordered by their already-
computed Decision Score, highest first, rather than generation order.

## Internal Workflow

```
Research item crosses FUTURE_TRADE_CONFIDENCE_THRESHOLD  (unchanged, today's real gate)
        |
generate_proposal() builds the real candidate TradeProposal  (unchanged — the
        |                                                      analyst votes, Expected
        |                                                      Value, and Decision Score
        |                                                      all need a real proposal
        |                                                      shape to be computed from)
        v
Compute Decision Score + Expected Value  (the exact same real
        |                                  build_decision_score()/
        |                                  build_expected_value_analysis()
        |                                  War Room already runs — just called
        |                                  earlier in the tick, before the
        |                                  candidate is appended to the
        |                                  CEO-visible pending list, not after)
        v
Market Quality check (reuses Feature 20's avoid_trading tier check)
        v
Evidence / Expected Value / Decision Score vs. CEO-configured minimums
        v
   APPROVE ------------------------------> REJECT
        |                                       |
enters the pending list, ranked by      never shown to the CEO — recorded
Decision Score (the real new             as a real pre-proposal rejection,
Opportunity Queue)                        graded later the same honest way
        |                                 Feature 20's rejections already are
War Room session built as today
(unchanged — Chapter 55)
        |
Position Sizing (Chapter 57, unchanged)
        |
CEO decision -> Feature 20's Gatekeeper (unchanged, still the final check)
```

## Decision Logic

Evidence outweighs Confidence — already true by construction
(`DecisionScoreBreakdown.evidenceScore` and `.confidenceScore` are
independent reads, never conflated; see `app/war_room.py`'s
`evidence_never_exceeds_confidence()`). Expected Value must be real and
positive — reuses `ExpectedValueAnalysis.positiveExpectancy` directly,
never a second calculation. When signals conflict, the same priority
order Chapter 57 already established governs here too: Evidence and
Expected Value first (a trade with no real edge never proceeds
regardless of how confident any single agent is), then Market Quality
and Risk (a real edge still doesn't trade into unhealthy conditions or
an active critical warning), then Portfolio Context (heat, correlation,
the weekly deployment budget) last, since it's a real-time state read
that can change tick to tick independent of the setup's own quality.

## Department Cooperation

**Receives from:** Market Intelligence (Feature 51), the Research
Division, the Digital War Room's Decision Score and Expected Value
(Chapter 55), Risk Authority (Sentinel/Guardian), Portfolio Intelligence
(Chapter 56), and — once wired — Company DNA. **Sends approved
opportunities to:** the CEO (Executive Voting / the ranked pending
list), Chapter 57's Position Sizing Engine (unchanged — still runs
exactly where it runs today, after a proposal is CEO-visible), and
Feature 20's existing Gatekeeper (unchanged — still the real final check
after the CEO's own buy/sell/wait call).

## CEO Controls

| Control | Status |
|---|---|
| Minimum Trade Quality (Decision Score threshold) | **New.** Today's `DECISION_SCORE_THRESHOLD = 70.0` is a fixed constant, never CEO-configurable. |
| Minimum Expected Value | **New** as an explicit numeric floor; `positiveExpectancy` (>0) is already real but not currently a configurable gate. |
| Maximum Daily Trades | **Already real** — `RiskLimits.maxTradesPerDay` (v0.7 Feature 49). |
| Maximum Correlated Positions | **Partially real** — `app/gatekeeper.py`'s `MAX_CORRELATED_POSITIONS = 2` is a hardcoded constant today, a real candidate to promote to a CEO-configurable `RiskLimits` field. |
| Maximum Swing / Day Positions | **Not built.** Day/Swing/Hybrid as distinct real trading modes don't exist in this codebase — the same honest gap Chapter 57 and `docs/DesignBible/volumes/06-trading-operating-system.md` already document. A control that changed a label with no behavioral effect would be exactly the "no placeholder systems" violation Company Law forbids. |
| News Sensitivity / Volatility Sensitivity / Liquidity Requirements | **Not built** — no real economic calendar or advance-scheduled news exists to be "sensitive" to (see Inputs above); volatility/liquidity are already real read-only inputs to the Decision Score, not yet independent CEO thresholds. |

## Learning System

Every pre-proposal rejection is tracked and graded the exact same
honest way Feature 20's `GatekeeperRejection` already grades its own
blocked trades: no order was ever placed, so there's no real P&L to
report — instead, once `GATEKEEPER_EVAL_WINDOW_MINUTES` of simulated
time passes, the rejected symbol's own real subsequent watchlist price
movement answers "would this direction have been right?" purely and
honestly. This is not a new mechanism to invent — it's the same real
grading logic (`app/gatekeeper.py`'s `grade_gatekeeper_rejections()`)
applied to the new, earlier rejection stage. Where the standards
themselves should evolve from that record (Company DNA's `researchRigor`
trait already measures a related real signal) is a real, open question
this chapter doesn't resolve — see Future Expansion.

## KPIs

Real, computable from real records once this engine exists: Trade
Acceptance Rate and Rejection Rate (a straight count); Rejection
Accuracy (the real would-have-won / would-have-lost split, the same
metric Feature 20's existing rejections already produce); Average
Opportunity Quality of accepted vs. rejected candidates (their own real
Decision Score). **Not honestly computable without a new ledger this
chapter doesn't propose building:** "Capital Saved Through Rejections"
as a real dollar figure — there's no counterfactual "what would have
been risked" tracking anywhere in this codebase; a rejected candidate's
own `quantity * price` is a real, defensible proxy, but should be
labeled as an estimate, never presented as an audited saving.

## Reports

Every report the brief asks for is a thin aggregation view over records
that would already be real once this engine ships (the pending-list
history, the pre-proposal rejection log, the Decision Score already
attached to every candidate) — the same "no new data source, just a new
read" pattern this codebase's other Report sections already follow
(e.g. Executive Review's own reports). No report here would require
inventing new underlying data.

## Safety Systems

Never approve without real evidence, without positive Expected Value,
or while Market Quality reads `avoid_trading` — these are the gate's
entire job, enforced by construction rather than as an exception path.
"When company risk budget is exhausted" reuses Chapter 57's real weekly
deployment budget as an input here too, so a CEO learns a budget is
already spent at the opportunity stage rather than only discovering it
later when Position Sizing quietly narrows the trade to zero. "During
emergency market conditions" reuses the same `avoid_trading` Market
Quality tier Feature 20's existing Gatekeeper already checks — one real
signal, two real consumers, never two competing definitions of
"emergency."

## Dependencies

Chapter 55 (Executive Decision Simulator / War Room — the Decision Score
and Expected Value this chapter reuses), Chapter 56 (Enterprise
Portfolio Intelligence — Portfolio Heat), Chapter 57 (Institutional
Position Sizing & Capital Deployment Engine — the weekly deployment
budget), and the existing Feature 20 Gatekeeper (the later-stage check
this chapter is a new, earlier sibling to, not a replacement for). **A
note on the brief's other two named dependencies:** "Chapter 53 —
Probabilistic Trading Philosophy" and "Chapter 56 — Institutional Risk
Authority" (as the brief numbers it) do not exist anywhere in this
codebase or its Design Bible under those numbers or titles — checked
directly, the same way earlier chapters' non-existent numbering was
checked before this chapter was written rather than assumed. What the
brief calls "Institutional Risk Authority" is this codebase's real
Sentinel/Guardian risk system (`app/risk_engine.py`) plus Chapter 56's
real Portfolio Intelligence — already covered above under their real
names.

## Connected Features

The War Room (Chapter 55, WARROOM tab) and Position Sizing (Chapter 57,
also surfaced on the WARROOM tab) are the two existing real systems this
chapter sits directly between in the pipeline. Feature 20's Gatekeeper
(app/gatekeeper.py) remains a distinct, later, real connected feature —
this chapter explicitly does not merge with it or replace its checklist.

## Future Expansion

Machine Learning Opportunity Ranking, AI Consensus Voting on borderline
candidates, Adaptive Quality Thresholds (Company DNA's `researchRigor`
trait feeding back into the Minimum Trade Quality control over time),
Cross-Market Opportunity Comparison, and Multi-Broker Opportunity
Routing all require real infrastructure (a live broker, in particular)
this codebase does not have yet — see `docs/DesignBible/volumes/10-broker-live-trading.md`'s
own honest "does not exist today" note. None of these are invented or
stubbed here.

## Company Principle

TradeTown is judged not by how many trades it takes, but by how many
poor trades it successfully refuses. Every opportunity must earn the
right to become part of the company's future.

## Implementation Notes

**What's real today:** the entire real scoring machinery this chapter
needs — `app/war_room.py`'s `build_decision_score()`,
`build_expected_value_analysis()`, and `DECISION_SCORE_THRESHOLD`; the
Market Quality `avoid_trading` tier; Feature 20's `app/gatekeeper.py`
and its `GatekeeperRejection` would-have-won/would-have-lost grading
pattern; `RiskLimits.maxTradesPerDay`; `app/company_dna.py`'s five real
traits (read-only, not yet wired as a filter input).

**What's genuinely new in this chapter:** moving the Decision Score /
Expected Value computation earlier in `app/nexus.py`'s tick — computed
once, immediately after `generate_proposal()`, and used as a real
pre-proposal gate — rather than only after a candidate is already
CEO-visible; a CEO-configurable Minimum Trade Quality / Minimum Expected
Value threshold (today's 70-point bar is a fixed constant); a new,
honestly-separate pre-proposal rejection record (not a forced reuse of
`GatekeeperRejection`, which assumes a `TradeProposal` and a real CEO
choice already exist); the real Opportunity Queue ranking of pending
proposals by their already-computed Decision Score; promoting
`MAX_CORRELATED_POSITIONS` from a hardcoded constant to a real CEO
control.

**What's explicitly out of scope until named gaps close:** News/
Volatility Sensitivity controls (no real economic calendar exists);
Maximum Swing/Day Position controls (no real distinct trading modes
exist); a real "Capital Saved Through Rejections" dollar figure beyond
an honestly-labeled estimate.

**Before implementation begins:** per Appendix G's Permanent Development
Policy, this chapter is the required design-first step. Implementation
should extend `app/nexus.py`'s existing proposal-generation loop and
reuse `app/war_room.py`'s scoring functions directly, never compute a
second, competing Trade Quality Score — and should ship with the same
rigor as Chapter 57: real tests, an honest scope-cut list, `mypy`/`ruff`
clean, backend committed and verified before any frontend work begins.
