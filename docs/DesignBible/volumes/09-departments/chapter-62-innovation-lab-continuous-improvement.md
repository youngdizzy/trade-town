# Chapter 62 — Institutional Innovation Lab & Continuous Improvement Engine

**Status:** Target design. Not yet implemented. See [Volume 9's chapter
template](README.md) for what every section below must contain, and the
Implementation Notes at the bottom of this chapter for exactly what's
real today versus new here.

## Executive Summary

"TradeTown should never assume its current systems are optimal." **A
naming collision, checked and flagged first:** this codebase already has
a module named `app/innovation.py` (v0.7 Feature 41) — but it is a
narrow, individual-agent skill ladder ("Innovation Points," earned only
through real Devil's Advocate `ChallengeReport`s), not an R&D pipeline.
It is not what this brief means by "Innovation Lab" and is not
duplicated or reused as the core of this chapter — it's a separate, real
system that happens to share a name, the same kind of collision
`app/decision_vault.py`'s own module docstring already flagged for
"Feature 53."

**Researched first, and — like Chapter 61 — the real finding is that
almost the entire brief already exists.** `app/sandbox.py`'s real,
8-stage gated pipeline (idea → research → historical_backtest →
market_simulation → paper_trading → limited_live_capital →
company_review → approved → retired) and `app/strategy_lab.py`'s
enrichment layer on top of it (Monte Carlo, Market Regime, Liquidity,
Risk, a real 9-department Executive Review, Founder Approval, and formal
Certification) together are, stage-for-stage, this brief's own
Innovation Pipeline and Validation Requirements sections — already
built, already fully surfaced in the Command Center's Strategy Lab
panels.

## Mission

One clear purpose: give every already-real strategy-improvement idea a
gated, evidence-based path from idea to production — and make sure a
successful one actually updates the company, not just a private strategy
record.

## Philosophy

"Ideas earn implementation through testing" is already this codebase's
real, enforced behavior, not aspiration: `app/sandbox.py`'s
`stage_index()`/`_advance()` functions physically prevent a `Strategy`
from skipping a stage — there is no code path that moves an idea
directly into `approved` or `limited_live_capital` without passing
through every earlier real gate first.

## Responsibilities

**Owns:** the stage-gated pipeline itself and its own validation
standards; extending it with the two genuinely new pieces this chapter
identifies (Experiment Tiering, CEO-configurable controls).

**Does NOT own:** Production Trading, Risk Approval (a certified
strategy still has to clear the ordinary Trade Gatekeeper/Opportunity
Gatekeeper on every real trade it generates — certification is a
prerequisite, not a bypass), Trade Execution, Broker Communication,
Capital Allocation (Chapter 57's Position Sizing still sizes every
individual trade a certified strategy generates).

## Ownership

| System | Module | What it really does |
|---|---|---|
| Idea / Strategy object | `app/simulation.py`'s `Strategy` | Already real (v0.5), scoped by the same `ResearchCategory` a `Strategy.focus_category` uses. |
| The gated pipeline | `app/sandbox.py` | `STAGE_ORDER`: `idea → research → historical_backtest → market_simulation → paper_trading → limited_live_capital → company_review → approved → retired`. `begin_paper_trial()`, `begin_limited_live()`, `generate_strategy_review()`, `apply_review_decision()`, `retire_strategy_stage()` are the real, enforced gate functions. `MAX_LIMITED_LIVE_CAPITAL = 2000.0` is a real, hardcoded pilot-capital ceiling — no pilot ever risks more than a fixed, small amount. |
| Monte Carlo Testing | `app/strategy_lab.py` | A real trade-sequence bootstrap over the strategy's own aggregated win rate and average win/loss sizes — a new, small, purpose-built bootstrap, deliberately not a second copy of `app/whatif.py`'s own (differently-scoped) Monte Carlo engine. |
| Market Regime Testing | `app/strategy_lab.py` | Reuses the real 13-way `MarketIntelligenceRegime` this codebase already computes every tick — not a second regime taxonomy. |
| Risk Review / 9-department Executive Review | `app/strategy_lab.py` | Real `StrategyDepartmentOpinion`s from Quant, Risk, Decision Intelligence, and Founders, each grounded in the strategy's own real `StrategyReview`/`StrategyMonteCarloResult`. |
| Certification | `app/strategy_lab.py`'s `compute_strategy_certification()` (v0.7 Feature 53 — note: this codebase's own Feature 53, unrelated to the brief's "Chapter 53," see Dependencies) | A real, formal, ENFORCED checklist gating the Limited Live Capital stage — not a suggestion. |
| Hall of Fame / Failed Archive | `app/sandbox.py`/`app/strategy_lab.py`, `app/state.py`'s retirement flow | A retired strategy becomes either a real `strategy_hall_of_fame` entry or a real `strategy_failed_archive` entry — never silently discarded either way. |
| Frontend | `SandboxPanel.tsx`, `StrategyPipelineView`, `StrategyCertificationView`, `StrategyEvolutionView`, `StrategyExecutiveDashboardView`, `StrategyFailedArchiveView`, `StrategyHallOfFameView`, `StrategyHealthView`, `StrategyLibraryView` | Already shipped — the entire pipeline above is already visible and navigable, not backend-only. |

## Inputs

Company Memory, Knowledge Graph (Chapter 61 — itself still target-design
but its underlying real stores already feed this pipeline: `ResearchItem`,
`SimulationResult`), Trade History, Backtesting Results, Simulation
Results, CEO Requests (`apply_review_decision()` already takes a real CEO
approve/reject call at Company Review), Performance/Risk/Portfolio
Reports — all real today. **Not real:** Academic Research, Industry
Developments, Technology Research as external inputs — this codebase has
no external data-feed or document-ingestion capability of any kind
(confirmed the same way `app/decision_vault.py`'s own module docstring
already confirmed no LLM/HTTP dependency exists), so these stay
explicitly out of scope rather than faked.

## Innovation Pipeline

The brief's own eleven-step pipeline (New Idea → Research → Feasibility
Review → Simulation → Backtesting → Stress Testing → Risk Review →
Executive Review → Pilot Deployment → Performance Monitoring →
Production Approval) maps, stage-for-stage, onto the real, already-
enforced pipeline in the Ownership table above:

```
New Idea              -> Strategy(stage="idea")
Research                 -> stage="research"           (real ResearchItem work)
Feasibility Review        -> stage="historical_backtest" (a real pass/fail)
Simulation                -> stage="market_simulation"
Backtesting                -> already folded into historical_backtest, above
Stress Testing             -> Monte Carlo + Market Regime (app/strategy_lab.py)
Risk Review                -> the Risk department opinion + Certification
Executive Review            -> the real 9-department StrategyExecutiveReview
Pilot Deployment            -> stage="limited_live_capital" (capped at $2,000)
Performance Monitoring       -> StrategyHealthAssessment (already real)
Production Approval          -> stage="approved" (or "retired" -> Hall of
                                Fame / Failed Archive)
```

"Ideas never move directly into live trading" is not a policy statement
here — it's a real, tested code invariant.

## Research Categories

Already real and reused, not duplicated: `ResearchCategory` (the same
taxonomy `ResearchItem`/`Strategy.focus_category` already use). The
brief's broader list (AI Improvements, Infrastructure, Broker
Integrations, User Experience) describes categories of improvement to
the *codebase itself*, which is outside what an in-game system can
honestly represent — see Design Bible Integration, below.

## Experiment Classification

**Not built.** No `Strategy`/`StrategyReview` carries anything like the
brief's Tier 1–4 (Minor/Moderate/Major/Transformational) classification
today. A real tier could reasonably reuse the strategy's own already-real
`StrategyMonteCarloResult`/projected-capital-at-risk as its basis (larger
projected capital or a larger Company DNA nudge on success implies a
higher tier) — a genuine, scoped design direction, not built here.

## Validation Requirements

Already real and enforced via Certification (`compute_strategy_certification()`,
above) — Expected Value, Risk Reduction, Reliability are each backed by
a real `StrategyCertificationRequirement`. **Not separately modeled:**
Execution Speed, Scalability, Maintainability as named, distinct
certification requirements — no real signal in this codebase measures
any of the three today.

## Simulation First

Already the real, enforced order (see Innovation Pipeline, above) — a
strategy cannot reach `limited_live_capital` without first clearing
`market_simulation`, and cannot reach `approved` without first clearing
`limited_live_capital`.

## Knowledge Integration

**Partially real today.** A retired strategy that becomes a Hall of Fame
entry already nudges Company DNA (`app/state.py`'s retirement flow calls
`nudge_legacy(..., "research_rigor", STRATEGY_HALL_OF_FAME_NUDGE)`) — a
real, checked example of "successful innovations automatically update
Company DNA." **Not yet real:** an equivalent update to Company Memory,
the Knowledge Graph, or "Training Materials" specifically — a Hall of
Fame entry is stored in its own real list but isn't yet also written as
a `MemoryRecord` or a Knowledge Graph node the way this chapter's own
Chapter 61 dependency would make possible.

## CEO Controls

| Control | Status |
|---|---|
| Innovation Budget | **Not built** — `MAX_LIMITED_LIVE_CAPITAL` ($2,000) is a fixed constant, not CEO-configurable. |
| Research Priority | **Overlaps** with `ResearchItem.priority`, already real — not a new control this chapter adds. |
| Experiment Approval | **Already real** — `apply_review_decision()` at Company Review is a genuine CEO approve/reject gate. |
| Pilot Duration | **Not built** — no minimum/maximum time-in-stage exists for `limited_live_capital`. |
| Validation Standards | **Already real** — Certification's own requirement checklist, but its bar is fixed, not CEO-adjustable. |
| Risk Tolerance | **Overlaps** with the existing, already-real `RiskLimits` — not a second, competing risk dial. |
| Innovation Categories | **Overlaps** with `ResearchCategory` — already real. |
| Automatic Promotion Rules | **Not built** — every stage advance today requires an explicit function call, never a background auto-promotion. |
| Research Focus | **Overlaps** with `ResearchItem.priority`/`focus_category` — already real. |

## KPIs

Already real and computable: Successful Innovations (Hall of Fame count),
Company Improvement Rate (Company DNA's own real trait trend). **Not
honestly computable without fabrication:** "Innovation Success Rate" as
a company-wide percentage (would need a denominator of *every* idea ever
started, including ones abandoned before ever becoming a real `Strategy`
object — this codebase only tracks ideas once they exist as one);
"Average Validation Time" (no timestamp is stamped at each individual
stage transition today, only at creation and the current state).

## Reports

Already real, thin reads over the pipeline above: the Strategy Lab's own
panels already are the Innovation Pipeline Report, the Pilot Performance
Report (`StrategyHealthAssessment`), and the Executive Innovation
Summary (`StrategyExecutiveReview`). **Not yet built:** a dedicated
"Innovation ROI Report" combining a strategy's real pilot-stage P&L
against `MAX_LIMITED_LIVE_CAPITAL` into one explicit ROI figure — the
underlying numbers are real, the combined view is not.

## Learning System

Already real per retired strategy: `generate_strategy_review()`/
`apply_review_decision()` already ask "did it improve the company, what
failed, what succeeded" against real Monte Carlo/regime/liquidity/risk
signals, and a failed strategy becomes a real, permanent
`strategy_failed_archive` entry rather than being discarded — "failure
is valuable when documented" is already true here.

## Safety Systems

Already real: no strategy can bypass Risk Authority (every trade a
certified strategy generates still goes through the ordinary Gatekeeper
pipeline unchanged); `MAX_LIMITED_LIVE_CAPITAL` already caps pilot
exposure; a retired strategy is preserved in either the Hall of Fame or
the Failed Archive, never deleted. **Not built:** an explicit rollback
mechanism for an `approved` strategy that later starts underperforming —
today `StrategyHealthAssessment` can flag it, but nothing automatically
reverts its stage.

## Department Cooperation

**Receives from:** Knowledge Graph (Chapter 61), Research Division,
Company Memory, Executive Intelligence, Risk Authority, CEO Requests —
all real today except Chapter 61's own graph extension. **Provides:**
Improved Strategies (real, via the Hall of Fame), Company DNA
Enhancements (real, via the retirement nudge above). **Not yet
provided:** Improved Systems, Improved Workflows, Improved Training,
Design Bible Updates — see Design Bible Integration, below, for why the
last one specifically stays out of scope.

## Dependencies

Chapter 54 (Decision Memory System), Chapter 55 (Executive Decision
Simulator), Chapter 56 (Enterprise Portfolio Intelligence), Chapter 57
(Position Sizing), Chapter 58 (Opportunity Gatekeeper), Chapter 59
(Capital Priority Engine — fully implemented), Chapter 61 (Knowledge
Graph & Company Memory Engine — this chapter's own Knowledge Integration
section depends directly on Chapter 61's graph extension). Chapter 60
(Portfolio Rebalancing) is cited by the brief but is itself still
target-design only. **A note on the brief's other named dependency:**
"Chapter 53 — Probabilistic Trading Philosophy" does not exist anywhere
in this codebase or Design Bible under that number or title — the same
non-existent reference already checked and flagged in Chapters 58, 59,
and 61. (This codebase's own real "Feature 53" is Company Certification,
inside `app/strategy_lab.py` — an unrelated collision, noted once here
rather than re-litigated per section.)

## Connected Features

Chapter 61 (Knowledge Graph, upstream — this chapter's own retired
strategies are exactly the kind of new node type Chapter 61's own
"genuinely new" section already names as a real, closeable extension).

## Future Expansion

Machine Learning Research, Autonomous Strategy Discovery, AI-to-AI
Brainstorming, Academic Paper Analysis all require a real embedding/LLM
or external-data dependency this codebase does not have — the same
honesty boundary Chapter 61's own Future Expansion section already
establishes.

## Design Bible Integration

**Explicitly out of scope, and stated directly rather than faked.** The
brief asks that every approved innovation "automatically update the
Design Bible" — but the Design Bible is this project's real,
human-authored engineering documentation (the very document this chapter
is itself a part of), not in-game state a simulated company can write to
from inside its own game loop. A simulated system that claimed to
"auto-write documentation" would be exactly the fabricated-capability
trap this codebase's own discipline exists to prevent. What genuinely
can and should update automatically — Company Memory, the Knowledge
Graph, Company DNA — are named explicitly in Knowledge Integration,
above, and are real, in-game state this chapter can honestly own.

## Company Principle

Every improvement must be measurable. Every innovation must earn its
place through the same real, enforced gates every other strategy has
already had to clear — and the company that learns the fastest becomes
the company that lasts the longest, because it never trades an idea it
hasn't actually tested.

## Implementation Notes

**What's real today:** the overwhelming majority of this chapter — the
entire 8-stage gated pipeline (`app/sandbox.py`), its full enrichment
layer of Monte Carlo/Market Regime/Liquidity/Risk/9-department Executive
Review/Founder Approval/formal Certification (`app/strategy_lab.py`), a
real, working Hall of Fame / Failed Archive split with a confirmed real
Company DNA nudge on success, and a fully shipped frontend across eight
distinct Strategy Lab views. Like Chapter 61, this chapter's research
finding is that the brief describes a system that is already, in very
large part, built.

**What's genuinely new in this chapter:** Experiment Tiering (Tier
1–4), scoped from the strategy's own already-real Monte Carlo/
capital-at-risk signals; promoting the named fixed constants
(`MAX_LIMITED_LIVE_CAPITAL`, pilot duration, automatic promotion) to
real CEO-configurable controls; extending the retirement flow's existing
Company DNA nudge to also write a real Company Memory entry and (once
Chapter 61's graph extension exists) a real Knowledge Graph node, so a
retired strategy's outcome becomes genuinely cross-referenceable, not
just a private list entry.

**What's explicitly out of scope until named gaps close:** "Innovation
Success Rate" as the brief frames it (would need to track abandoned
ideas that never became a real `Strategy` object — fabrication, not
analysis); an actual automated Design Bible-writing capability (see
Design Bible Integration, above — a category error, not a missing
feature); Academic Research/external-data ingestion (no such dependency
exists in this codebase).

**Before implementation begins:** per Appendix G's Permanent Development
Policy, this chapter is the required design-first step. Given how much
of the pipeline already exists and is already enforced, implementation
should be scoped narrowly to Experiment Tiering, the named CEO controls,
and the retirement-to-Knowledge-Graph link — not a re-implementation of
`app/sandbox.py`/`app/strategy_lab.py`'s already-working gates.
