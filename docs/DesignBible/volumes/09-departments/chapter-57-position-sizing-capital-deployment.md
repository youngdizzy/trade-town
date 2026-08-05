# Chapter 57 — Institutional Position Sizing & Capital Deployment Engine

**Status:** Target design. Not yet implemented. See [Volume 9's chapter
template](README.md) for what every section below must contain, and the
Implementation Notes at the bottom of this chapter for exactly what's
real today versus new here.

## Executive Summary

Professional traders know position sizing often determines profitability
more than entry quality — a mediocre setup with disciplined sizing can
outperform a perfect setup with reckless sizing. TradeTown treats capital
as inventory: allocated strategically, never emotionally. Today,
`app/risk_engine.py`'s `recommended_quantity()` sizes every position off
exactly two numbers (a flat percent-of-equity risk budget, capped by a
flat percent-of-equity position cap) with no regard for how strong the
evidence behind the trade actually is. This chapter's job is to replace
that flat model with one that asks not just "should this trade happen?"
(the Trade Gatekeeper's job, Chapter unassigned) but "exactly how much of
the company's capital has this specific opportunity earned?"

## Mission

TradeTown should never decide position size from emotion, confidence
alone, or intuition. Every dollar deployed must be justified through
evidence, probability, portfolio context, and company risk policy. The
objective is to maximize long-term compounding while minimizing
unnecessary drawdowns.

## Philosophy

TradeTown does not ask "how much money can we make?" — it asks "how much
capital deserves to be risked?" Capital is earned, not assumed. Risk is
purchased with evidence, not ignored. This is the same evidence-first
stance Company Law already establishes (Volume 2) and that the War Room
(Chapter 55) and Decision Vault (Chapter 54) already apply to *whether*
a trade happens; this chapter applies it to *how much*.

## Responsibilities

**This department owns:**

- Position Sizing
- Capital Deployment
- Trade Exposure sizing (not exposure *monitoring* — see Ownership)
- Position Scaling and Position Reduction
- Position Tier assignment
- Capital Preservation at the single-trade level

**This department explicitly does NOT own** (preventing overlap with
existing real departments):

- Approving or rejecting a trade outright — that is the Trade
  Gatekeeper's (`app/gatekeeper.py`) job; this engine only ever answers
  "how much," never "whether."
- Overriding Risk Authority — Sentinel/Guardian's real exposure and
  drawdown checks (`app/risk_engine.py`'s `evaluate_sentinel_risk()` /
  `evaluate_guardian_exposure()`) remain a hard ceiling this engine's
  output must always respect, never negotiate past.
- Executing trades — `app/broker.py`'s `PaperBroker` remains the only
  thing that ever places an order.
- Modifying strategy rules — `app/strategy_lab.py`'s Research Sandbox
  owns strategy definition and certification.
- Portfolio-wide correlation/heat monitoring — `app/portfolio_intelligence.py`
  (Chapter 56) already owns that read; this engine *consumes* it as an
  input (Portfolio Heat, correlation pairs) rather than recomputing it.

## Ownership

Target module: `backend/app/position_sizing.py` (new). Evolves — does
not duplicate — `app/risk_engine.py`'s existing `recommended_quantity()`;
when built, that function's real two-limit calculation becomes this
engine's floor/ceiling inputs, not a parallel, competing sizing path.

## Inputs

Real, already-computed values this engine would read (no new upstream
system required to source any of these):

- Evidence Score & Confidence Score — `app/decision_vault.py`'s
  `compute_evidence_score()`, `app/confidence.py`'s `DecisionConfidence`.
- Expected Value & Risk-to-Reward — `app/war_room.py`'s
  `ExpectedValueAnalysis`.
- Probability of Profit — `app/whatif.py`'s
  `ScenarioResult.probabilityOfProfitPct`.
- Market Quality & Liquidity Score — `app/market_intelligence.py`'s
  `MarketQualityScore`, `LiquidityRead`.
- Portfolio Heat & Correlation — `app/portfolio_intelligence.py`'s
  `PortfolioHeat`, `CorrelationPair`.
- Open Exposure & Category Concentration — `app/portfolio_intelligence.py`'s
  `CategoryExposure`; `app/gatekeeper.py`'s `MAX_CORRELATED_POSITIONS`
  check.
- Company Risk Limits — `app/schemas.py`'s `RiskLimits` (today:
  `maxPositionPct`, `maxDailyLossPct`, `maxDrawdownPct`,
  `maxOpenPositions`, `maxSectorConcentrationPct`, `riskPerTradePct`).
- Historical Performance — the Decision Vault's Similarity Engine
  (`find_similar_vault_entries()`), the closest real source for "how did
  similar setups actually perform."
- Volatility — `app/market_data.py`'s `volatility_pct()`.

## Outputs

- A final recommended position size (quantity and % of equity).
- A Position Tier assignment (see Decision Logic).
- A real, logged justification tying the size to its Evidence/Confidence/
  Expected Value inputs — never a bare number with no trail.
- Feed into the Daily/Capital Deployment/Exposure/Risk Budget/Position
  Quality/Capital Efficiency/Portfolio Heat reports (see Reports).

## Internal Workflow

```
Input (Evidence, Confidence, Expected Value, Probability, Market
Quality, Liquidity, Portfolio Heat, Open Exposure, Risk Limits)
  ↓
Analysis (score each input, apply the priority order in Decision Logic)
  ↓
Decision (assign a Position Tier, compute a target allocation)
  ↓
Validation (check against Risk Budget, Portfolio Heat ceiling, category
concentration, and Sentinel/Guardian's existing hard limits — any one
failing caps or zeroes the allocation, never the reverse)
  ↓
Execution (the validated size is handed to the Trade Gatekeeper /
PaperBroker — this engine never places the order itself)
  ↓
Learning (once the trade closes, compare allocated vs. optimal capital —
see Learning System)
```

## Decision Logic

**No single metric determines allocation.** Every position is scored
from Evidence, Confidence, Expected Value, Historical Similarity,
current Market Quality, Volatility, Liquidity, and Portfolio Correlation
— combined, not any one in isolation.

**Evidence always outweighs confidence.** A proposal reading 98%
Confidence but only 43% Evidence gets a *reduced* allocation, never a
maximum one — the same structural rule Chapter 55's Decision Score
already enforces at the trade-approval level (Evidence Score is a strict
subset of Confidence Score's own factors by construction), applied here
to sizing instead of approval.

**Evidence-based scaling** (illustrative, not a literal formula — the
real formula is implementation work, not a design-time invention):

- Weak evidence → smallest exploratory position.
- Medium evidence → a normal, standard position.
- Exceptional evidence + excellent probability + a healthy portfolio
  (low heat, low correlation) → the maximum tier this proposal's own
  numbers can justify.

**Position Tiers:**

| Tier | Name | When |
|---|---|---|
| 1 | Exploratory | Uncertain opportunity; smallest allocation |
| 2 | Standard | Healthy evidence; normal allocation |
| 3 | High Conviction | Exceptional evidence + probability + portfolio health |
| 4 | Institutional Allocation | Extremely rare; requires Risk Authority approval, Portfolio Intelligence approval, and Executive approval (Chapter 55's Decision Score clearing its threshold) before this engine may even propose it |

**Position Scaling** — a position may grow, but never immediately and
never from hope. Scale only when evidence improves, risk decreases,
probability increases, the market confirms the original thesis, and
capital is actually available. Never average down on a losing position
because of hope alone — that is exactly the "hopes vs. evidence" failure
mode the Executive Decision Simulator's own company principle (Chapter
55) already names.

**Position Reduction** — automatically propose a reduced allocation
when evidence weakens, confidence falls, risk increases, Portfolio Heat
rises, correlation to existing positions increases, market structure
changes, or an unexpected real news event appears. "Automatically
propose" — per Company Law (Volume 2) and this codebase's own
established v0.8 stop condition (`docs/ROADMAP.md`: "risk is measured
and displayed, never auto-hedged or auto-corrected without the player"),
this engine may never auto-execute a reduction; it surfaces the
recommendation for the same real approval path every other sizing
decision goes through.

**Capital Deployment Rules** — cash is itself a position. Holding cash
is an active decision, never a default failure state. TradeTown never
forces deployment; unused capital is acceptable, poor deployment is not.
`app/portfolio_intelligence.py`'s real `_opportunity_cost()` already
reads in this direction (an honest templated read on cash sitting idle
vs. pending proposals) — this engine's job is to act on that read at
the individual-position level, not to invent a second cash philosophy.

**Portfolio Context** — every new position's size additionally weighs
existing exposure, category concentration, correlation, strategy
allocation, and the company's real, current capital-preservation-first
priority ordering (`docs/DEVELOPMENT_RULES.md`'s Company Capital
Priorities).

**Risk Budget** — the day begins with a real, spendable risk budget
(daily/weekly maximum risk, maximum open risk, maximum Portfolio Heat).
Once exhausted, no further position may open, regardless of how strong
an individual proposal's evidence reads — a company-wide ceiling this
engine's own per-trade sizing must respect, not a per-trade decision it
can override.

## Department Cooperation

**Receives from:** Market Intelligence (quality, liquidity, volatility),
the Decision Vault / War Room (evidence, confidence, expected value,
historical similarity), Risk Authority (`app/risk_engine.py`,
`app/gatekeeper.py` — hard limits), Portfolio Intelligence (heat,
correlation, category exposure), Company DNA (long-run behavioral
adjustment).

**Provides to:** the Trade Gatekeeper (a sized proposal to approve or
reject), `PaperBroker` (the final validated quantity once approved), the
CEO Dashboard / Command Center (the real justification trail), Portfolio
Intelligence (a record of what was actually deployed, feeding its own
next-tick capital-efficiency read).

No isolated systems — this engine is a consumer of five real upstream
departments and a producer for two real downstream ones, never a
standalone calculator.

## CEO Controls

- Maximum Position Size (already real: `RiskLimits.maxPositionPct`)
- Maximum Daily Risk (already real: `RiskLimits.maxDailyLossPct`)
- Maximum Weekly Risk (new)
- Maximum Portfolio Heat as a hard ceiling, not just a reading (new —
  today Portfolio Heat is read-only per Chapter 56's own honesty
  boundary; making it CEO-configurable as a cap is a deliberate,
  different thing from auto-correcting it, and stays inside the v0.8
  stop condition since the CEO, not the system, sets and triggers it)
- Capital Allocation Limits per Position Tier (new)
- Scaling Rules (new — how aggressively Position Scaling is allowed to
  compound)
- Cash Reserve % (new)
- Day Trading / Swing Trading / Hybrid allocation split (new — see
  Volume 6's own honest note that these aren't yet distinct real modes;
  this control would be one of the first real steps toward making them
  so)
- Emergency Reduction Levels (new — a CEO-set trigger for when Position
  Reduction proposals should escalate to immediate review)

## Learning System

After every closed trade, compare the capital actually allocated against
what the position's real, closed-trade outcome shows would have been
optimal. Real questions asked of real data: was the position too large,
too small, or correct? Did the evidence at entry actually justify the
allocation given? Should future sizing for this evidence profile change?
This is the same "every completed task should make future decisions
better" convention `app/company_dna.py`'s `nudge_legacy()` already
applies elsewhere — this engine should feed Company DNA rather than grow
a second, parallel learning store.

## KPIs

Capital Efficiency (already real, Chapter 56's `CapitalEfficiency`),
Risk Efficiency, Average Position Quality, Portfolio Stability, Average
Drawdown (already real per-period, `app/analytics.py`'s
`PerformanceSnapshot.max_drawdown_pct`), Capital Utilization, Expected
Value (already real, Chapter 55), Risk-Adjusted Return.

## Reports

Daily Allocation Report, Capital Deployment Report, Cash Allocation
Report, Exposure Report, Risk Budget Report, Position Quality Report,
Capital Efficiency Report (already real, Chapter 56), Portfolio Heat
Report (already real, Chapter 56).

## Safety Systems

Never exceed the company Risk Budget. Never exceed the Portfolio Heat
ceiling once the CEO makes it a hard cap. Never exceed Capital Allocation
Limits. Never increase size from emotion — there is no "emotion" input
anywhere in this engine's real Inputs list, by construction, the same
way this codebase's Discipline Chamber structurally cannot see a trade's
pnl when scoring process. Never average down without new, real evidence.
Capital preservation is checked before every other objective, matching
Company Capital Priority #1 (`docs/DEVELOPMENT_RULES.md`).

## Dependencies

- Chapter 54 — Decision Memory System (Decision Vault): evidence score,
  historical similarity.
- Chapter 55 — Executive Decision Simulator (War Room): Expected Value,
  Decision Score, confidence-never-exceeds-evidence invariant.
- Chapter 56 — Enterprise Portfolio Intelligence: Portfolio Heat,
  correlation, capital efficiency, category exposure.
- Real Risk Authority (`app/risk_engine.py`, `app/gatekeeper.py`) — no
  dedicated "Institutional Risk Authority" chapter exists yet under this
  exact name; today Risk Authority's real function is distributed across
  Sentinel/Guardian's checks and the Trade Gatekeeper. This chapter
  depends on that real, existing function, not on a chapter number that
  doesn't exist yet.
- Future: real broker integration (Volume 10) — position sizing against
  real capital, not simulated, is out of scope until that volume moves
  past its current "no live broker exists" honesty boundary.

## Connected Features

Chapters 54, 55, 56 (above). Future connection, once written: a
dedicated Risk Authority chapter this engine's hard-limit inputs should
formally cite instead of pointing at scattered modules.

## Future Expansion

Multiple brokers, multiple accounts, retirement accounts, institutional
funds, managed accounts, client portfolios, international markets — all
require real broker/account infrastructure (Volume 10) this codebase
does not have yet. This engine's evidence-scaled sizing model is
designed to generalize to those contexts without a redesign (the
Position Tier / Risk Budget model doesn't assume a single account), but
none of them are real today.

## Company Principle

Capital is not spent. Capital is invested. Every dollar must earn the
right to enter the market. TradeTown protects capital first, compounds
capital second, and profits third.

## Implementation Notes

**What's real today:** `app/risk_engine.py`'s `recommended_quantity()`
(flat two-limit sizing: `min(risk_per_trade_pct, max_position_pct)` of
equity, no evidence input at all); `RiskLimits`'s six real CEO-
configurable fields; Portfolio Heat, correlation, and capital efficiency
as read-only signals (Chapter 56); Expected Value and Decision Score as
read-only signals (Chapter 55); the v0.8 stop condition forbidding any
auto-corrective action without the player.

**What's genuinely new in this chapter:** an evidence-and-confidence-
weighted sizing model replacing the flat calculation; the four-tier
Position Tier system; explicit Position Scaling/Reduction trigger rules;
a real, spendable daily/weekly Risk Budget (today `maxDailyLossPct` is a
single static ceiling, not a decrementing spendable budget); Portfolio
Heat promoted from a reading to an optional CEO-configurable hard cap;
Day/Swing/Hybrid allocation splits as a real, configurable control.

**What's explicitly out of scope until named volumes catch up:**
Institutional Allocation Tier's cross-department approval workflow
(depends on a real approval-routing mechanism this codebase doesn't have
yet); real multi-broker/multi-account capital deployment (Volume 10);
a literal position-sizing formula (a specific, tested weighting function
is implementation work, not something this design document should
invent and then treat as settled).

**Before implementation begins:** per Appendix G's Permanent Development
Policy, this chapter is the required design-first step. Implementation
would extend `app/risk_engine.py` rather than create a competing sizing
path, and should ship with the same rigor as Chapters 54–56 — real
tests, an honest scope-cut list, `mypy`/`ruff` clean, before any
frontend work begins.
