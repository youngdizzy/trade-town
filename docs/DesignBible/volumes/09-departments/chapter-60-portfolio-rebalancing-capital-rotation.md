# Chapter 60 — Institutional Portfolio Rebalancing & Adaptive Capital Rotation

**Status:** Target design. Not yet implemented. See [Volume 9's chapter
template](README.md) for what every section below must contain, and the
Implementation Notes at the bottom of this chapter for exactly what's
real today versus new here.

## Executive Summary

Professional firms rarely ask "is this trade profitable?" in isolation —
they ask "does this improve the portfolio?" TradeTown should treat the
portfolio as a living system where every open position continuously
earns its place, not a set-and-forget collection of independent bets.

**Researched first — this is the largest real gap in this Design
Bible's trading pipeline so far.** Every open position in this codebase
today closes for exactly one reason: `app/paper_trading.py`'s
`tick_paper_trading()` marks positions to market, then — once a position
clears `MIN_HOLD_MINUTES` — rolls a flat `CLOSE_CHANCE_PER_TICK` random
chance every tick until it closes (or `MAX_HOLD_MINUTES` forces it).
The closing "reason" recorded (`"Take-profit target reached"` or
`"Stop-loss / thesis reassessment"`) is chosen purely from whether
current P&L is positive or negative — it is a label applied after a
timer-and-dice-roll decision, not a real cause. **No code anywhere
re-scores an open position against its own original thesis, compares it
to a currently-better opportunity, or closes it early because something
stronger appeared.** `PaperPosition` itself has no field recording the
Decision Score or Expected Value it was opened with, so there is nothing
to compare "then" against "now" even if the comparison logic existed.
This is not a small gap to close — it is the one this chapter exists
entirely to fill, and honest scoping below reflects that.

## Mission

The portfolio itself — not any single trade — is the company's primary
asset. This department continuously improves the whole portfolio by
reallocating capital toward stronger opportunities and reducing exposure
to weakening positions. Capital should migrate toward the highest-quality
opportunities available, never sit frozen in yesterday's decision.

## Philosophy

The portfolio is never finished; it is continuously evolving. Holding
yesterday's winner should never prevent owning tomorrow's better
opportunity. Every position must continuously justify its existence, not
just its entry.

## Responsibilities

**Owns:** continuous re-evaluation of every open position against the
real, currently-ranked opportunity queue (Chapter 59); Portfolio
Rebalancing and Capital Rotation recommendations; sector/correlation
exposure management over the live portfolio; Position Replacement
Analysis.

**Does NOT own** (see Appendix E): Trade Approval (Chapter 58), initial
Position Sizing (Chapter 57), Risk Veto Authority (Sentinel/Guardian,
unchanged), Broker Communication, or ranking the *pending* proposal
queue (Chapter 59 — this chapter only ever looks at positions capital
has *already* been committed to). This is the same deliberate boundary
Chapter 59's own Responsibilities section already establishes from the
other side.

## Ownership

Would require a genuinely new real field on `PaperPosition` (its own
Decision Score and Expected Value *at open time*, so "is this still one
of the best opportunities" has a real "then" to compare against "now" —
today `PaperPosition` records `confidence` alone, no Decision Score at
all) and a new real function to re-score an *open* position's *current*
Decision Score using the same real `build_decision_score()` machinery
Chapters 55/58 already use for new candidates. Would extend
`app/paper_trading.py`'s per-tick position loop (today: mark-to-market +
random-roll close only) with a real evaluation step, and would consume
Chapter 59's newly-ranked Opportunity Queue directly as the "stronger
opportunity" comparison set.

## Inputs

| Brief asks for | Already real, as |
|---|---|
| Current Portfolio / Open Positions | `PaperPortfolio.positions` |
| Trade Priority Scores / Opportunity Queue | Chapter 59's newly-ranked queue |
| Expected Value / Evidence / Confidence / Probability | Chapters 55/58's real machinery — but only ever computed for *new* candidates today, never re-run against an *open* position (the real gap) |
| Risk Reports | Sentinel/Guardian's `RiskWarning`s |
| Sector Exposure | `CategoryExposure` (Chapter 56) |
| Market Conditions | `MarketIntelligenceState` (Feature 51) |
| Portfolio Heat | `PortfolioHeat` (Chapter 56) |
| Capital Allocation | `PortfolioIntelligence` (Chapter 56) |
| Liquidity / Volatility | Already real per-symbol reads, folded into Decision Score today only for new candidates |
| Company DNA | `app/company_dna.py`'s five real traits — real, read-only, not wired as an input here, same honest gap every other chapter in this volume already flags |

## Portfolio Review Cycle

```
Current portfolio (real, every open position)
        v
Evaluate every position — NEW: re-run build_decision_score()'s real
machinery against each position's CURRENT market data, not just its
entry-time snapshot
        v
Compare against Chapter 59's real ranked Opportunity Queue
        v
Measure Portfolio Health (see below)
        v
Identify weak positions (real current score meaningfully below queue's
top candidates) and strong new opportunities
        v
Recommend capital rotation — a real, CEO-visible recommendation, never
an automatic close (see Safety Systems)
        v
Risk validation (Sentinel/Guardian, unchanged) -> CEO approval -> real
close_position() + real new proposal, both mechanisms already exist
```

## Portfolio Health Score

**Reuses, does not duplicate.** Every factor the brief names already has
a real source: Expected Value/Evidence/Confidence (Chapter 55, once
re-scored per open position — see Ownership), Diversification/Sector
Balance/Correlation (Chapter 56's `CategoryExposure`/`CorrelationPair`),
Risk Concentration/Portfolio Heat (Chapter 56's `PortfolioHeat`),
Capital Efficiency (Chapter 56's `CapitalEfficiency`), Liquidity
(already folded into Decision Score). `CompanyHealth.capitalHealth`
(Feature 50) is a related, already-real but company-wide (not
portfolio-specific) health measure — this chapter's Portfolio Health
Score is a new, narrower composite over the signals above, built the
same "combine real sub-scores, never invent one" way Chapter 55's own
Decision Score was built, not a second unrelated number.

## Capital Rotation

A real rotation recommendation requires a real, *measurable* comparison:
the position's own current re-scored Decision Score/Expected Value
versus the top of Chapter 59's ranked queue, by a CEO-configured margin
(see CEO Controls). "Expected Value improves, risk decreases,
diversification improves" are all real, checkable conditions once the
re-scoring machinery above exists — this section is not a wishlist, it
is exactly what the real comparison produces.

## Rebalancing Triggers

Every real trigger the brief names already has a real underlying signal
this codebase computes every tick: a new high-quality opportunity
(Chapter 59's queue, recomputed every tick), Portfolio Heat rising
(Chapter 56, recomputed every tick), sector concentration exceeding
limits (`RiskLimits.maxSectorConcentrationPct`, already checked),
economic regime changes (`MarketEnvironmentState`, Feature 22), major
news (`NewsItem`, real). None of these require a new *data source* —
only a new *consumer* (this chapter's review cycle) that actually acts
on signals that already exist but nothing currently reacts to for
already-open positions.

## Correlation Management

**Already partially real, at the wrong stage.** `app/gatekeeper.py`'s
`MAX_CORRELATED_POSITIONS` check (a hardcoded constant, per Chapter
58's own flagged-but-not-built scope cut) only ever runs at
trade-approval time, never continuously against the live, already-open
portfolio. Chapter 56's `CorrelationPair`s already compute real Pearson
correlation between currently-held symbols every tick — this chapter's
real job is consuming that already-real signal as a continuous
portfolio-level check, not computing a new one.

## Diversification Engine

Sector/strategy/timeframe/market diversity: sector balance is real
(Chapter 56's `CategoryExposure`); strategy diversity and timeframe
diversity are **not honestly measurable today** — this codebase has one
real trading mode and no Strategy-linkage on ordinary Trading Floor
positions (the same gap `DecisionScoreBreakdown.strategyHealthScore`
already documents as always `null` for exactly this reason). Not
fabricated here.

## Position Replacement Analysis

This is the chapter's real, central, and largest new capability: every
open position continuously asks "is this still one of the best
opportunities?" — answerable only once the position has a real current
Decision Score to compare against Chapter 59's real queue (see
Ownership's note on the new `PaperPosition` field this requires).
"Never replace positions without measurable improvement" is enforced by
construction: no recommendation is generated unless the comparison
produces a real, positive, CEO-visible delta.

## Capital Migration

Capital moving from weaker to stronger positions "gradually, never
emotionally, never impulsively" is enforced by the same real
`min(...)`-based narrowing discipline Chapter 57 already established for
sizing — this chapter recommends, Chapter 57 still sizes the replacement
trade, and the CEO still approves both the close and the new open,
exactly like every other trade in this codebase.

## CEO Controls

| Control | Status |
|---|---|
| Portfolio Review Frequency | **New** — how often the re-scoring cycle above runs; a real, cheap-to-add tick-count or sim-minute interval, the same convention `MEETING_CHANCE_PER_TICK`-style pacing already uses elsewhere. |
| Capital Rotation Sensitivity / Maximum Rotation % | **New** — the real margin a replacement candidate must clear before a recommendation is even generated. |
| Sector Allocation Limits | **Already real** — `RiskLimits.maxSectorConcentrationPct`. |
| Correlation Limits | **Partially real** — `app/gatekeeper.py`'s `MAX_CORRELATED_POSITIONS`, still a hardcoded constant (same flagged-but-not-built promotion Chapter 58 already noted). |
| Cash Reserve % | **Already real** — Chapter 57's `cashReservePct`. |
| Rotation Approval Requirements | **Already real by construction** — every close/open in this codebase already requires the same CEO/auto-resolution pipeline every other trade does; this chapter doesn't need a separate approval mechanism. |
| Swing vs. Day Allocation | **Not built** — no real distinct trading modes exist (same gap Chapters 57–59 already document). |
| Portfolio Health Threshold | **New**, once the Portfolio Health Score itself is real. |

## KPIs

Real once this chapter exists: Portfolio Health Score itself; real
Diversification/Correlation Reduction (both already-real Chapter 56
signals, now tracked over time as this chapter acts); Rotation Success
Rate (a real, gradeable "did the replacement's actual outcome beat the
position it replaced" comparison, the same honest grading discipline
Chapter 58's `GatekeeperRejection`/`OpportunityRejection` already use
for their own would-have-won/lost self-evaluation). **Not honestly
computable without a new ledger:** "Capital Migration Efficiency" as a
single number would need the same kind of real before/after portfolio
snapshot comparison this chapter's own real rotation records would
provide once built — not fabricated in advance of that data existing.

## Reports

Same "real aggregation, no new data source" pattern as every other
chapter here — a Portfolio Health Report and Capital Rotation Report are
both thin views over data this chapter's own real cycle produces.

## Learning System

After every real rotation: did the replacement's real subsequent
performance beat what the replaced position would have done? — a real,
answerable question once both positions' real P&L exists in
`PaperTrade` history, using the exact same "wait for real time to pass,
then check real data" convention `app/gatekeeper.py`'s
`grade_gatekeeper_rejections()` and Chapter 58's
`grade_opportunity_rejections()` already establish.

## Safety Systems

**Never an automatic close or rotation — a real, CEO-visible
recommendation only**, the same v0.8 stop condition ("risk is measured
and displayed, never auto-hedged or auto-corrected without the player")
Chapter 57's Portfolio Heat cap and Chapter 58's every gate already
respect. This chapter never closes a position or opens a replacement by
itself; it recommends, and the existing CEO/auto-resolution pipeline
decides, exactly like every other trade in this codebase. Never rotate
without a measurable, real improvement — enforced by construction, not
policy.

## Department Cooperation

**Receives from:** Chapter 59 (the ranked Opportunity Queue this
chapter's comparisons are measured against), Chapter 58 (Opportunity
Gatekeeper), Chapter 57 (Position Sizing, for the real replacement
trade's size), Risk Authority, Portfolio Intelligence (Chapter 56),
Research Division, Market Intelligence. **Sends to:** the CEO (real
rotation recommendations), the existing execution pipeline (unchanged —
a rotation is just a real close followed by a real new proposal, both
mechanisms this codebase already has).

## Dependencies

Chapter 56 (Enterprise Portfolio Intelligence — heat, correlation,
category exposure, capital efficiency), Chapter 57 (Institutional
Position Sizing — sizes the replacement trade), Chapter 58 (Institutional
Trade Filter & Opportunity Gatekeeper — the approval gate the
replacement trade still passes through like any other), Chapter 59
(Capital Priority & Opportunity Cost Engine — the ranked queue this
chapter compares open positions against). **The same named-dependency
note already made in Chapter 59 applies here too:** "Chapter 53 —
Probabilistic Trading Philosophy" does not exist anywhere in this
codebase or Design Bible, and the brief's own numbering for the
Executive Decision Simulator/Enterprise Portfolio Intelligence chapters
runs one behind this Design Bible's real numbering — checked directly,
not re-litigated per section here.

## Future Expansion

Multiple Portfolios, Retirement/Institutional/Client Accounts, Global/
Cross-Asset Markets, and Multi-Broker Capital Allocation all require
real infrastructure this codebase does not have yet (a live broker in
particular). AI Portfolio Managers, Adaptive Machine Learning
Rebalancing, and Economic Regime Rotation are real future directions,
not invented or stubbed here.

## Company Principle

A portfolio is never managed one trade at a time — it is managed as a
living ecosystem. Every position must continuously justify its
existence. TradeTown does not build collections of trades; it builds
portfolios.

## Implementation Notes

**What's real today:** `app/paper_trading.py`'s mark-to-market and
timer-based closing (unchanged, stays as the honest fallback for a
position nothing ever recommends rotating); every Chapter 55/56/57/58
signal this chapter's comparisons would consume; `app/gatekeeper.py`'s
`MAX_CORRELATED_POSITIONS` (a real but hardcoded, pre-approval-only
check).

**What's genuinely new in this chapter — and it is substantial:** a new
field on `PaperPosition` recording its own real Decision Score/Expected
Value at open time; a real function to re-score an *open* position's
*current* Decision Score using the same machinery Chapters 55/58 already
use for new candidates (today that machinery only ever runs for
proposals, never positions); a real per-tick or interval-based review
cycle in `app/paper_trading.py`; real, CEO-visible rotation
recommendations (never automatic); real grading of completed rotations
against what the replaced position would have done. This is
meaningfully larger than any prior chapter's real implementation gap —
honest scoping here matters more than usual.

**What's explicitly out of scope until named gaps close:** Strategy/
timeframe diversity measurement (no real Strategy-linkage on ordinary
positions exists); Swing vs. Day allocation (no real distinct trading
modes); any automatic close or rotation (forbidden by the same v0.8
stop condition every other chapter here already respects); "Capital
Migration Efficiency" as a single fabricated-in-advance number.

**Before implementation begins:** per Appendix G's Permanent Development
Policy, this chapter is the required design-first step, and — given the
size of the real gap this chapter closes — implementation should likely
be scoped into its own multi-slice plan (the new `PaperPosition` field
and re-scoring function as one real, independently-testable slice
before the review cycle and rotation-recommendation UI are attempted),
rather than one single pass. Should ship with the same rigor as every
other chapter in this volume: real tests, an honest scope-cut list,
`mypy`/`ruff` clean, backend committed and verified before any frontend
work begins.
