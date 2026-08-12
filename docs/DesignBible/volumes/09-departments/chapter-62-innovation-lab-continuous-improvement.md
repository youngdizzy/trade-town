# Chapter 62 — Institutional Innovation Lab & Continuous Improvement Engine

**Status:** Partially implemented. All three pieces this chapter's own
research named as "genuinely new" are real: Knowledge Integration (every
strategy retirement now files a real Company Memory entry, not just the
existing Company DNA nudge), the Innovation Budget CEO control
(`RiskLimits.maxLimitedLiveCapital`), and Experiment Tiering
(`StrategyDossier.experimentTier`, computed from the strategy's own real
Monte Carlo projections). The rest of CEO Controls (Pilot Duration,
Automatic Promotion Rules) remain target design — see CEO Controls below
for why. See [Volume 9's chapter template](README.md) for what every
section below must contain, and the Implementation Notes at the bottom
of this chapter for exactly what's real today.

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

**Built** — `app/strategy_lab.py`'s `compute_experiment_tier()`, exposed
as `StrategyDossier.experimentTier`/`experimentTierRationale`
(`GET /api/sandbox/dossier`). Real magnitude, not a fabricated risk
score: the larger of the strategy's own projected upside
(`medianReturnPct`) or realized downside (`worstCaseDrawdownPct`) from
its own real Monte Carlo bootstrap, bucketed against three real (if
honestly arbitrary — the same "conservative but arbitrary" resolution
`RiskLimits`' own docstring already uses) thresholds:
`EXPERIMENT_TIER_MODERATE_PCT` (10%), `EXPERIMENT_TIER_MAJOR_PCT` (25%),
`EXPERIMENT_TIER_TRANSFORMATIONAL_PCT` (50%). Only ever set once a real
`StrategyMonteCarloResult` exists for that strategy — `None` before
then, never guessed. Surfaced in `StrategyCertificationView.tsx` as a
badge alongside the Monte Carlo Testing card.

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

**Real today, on both fronts named in the brief.** A retired strategy
that becomes a Hall of Fame entry already nudges Company DNA
(`app/state.py`'s retirement flow calls `nudge_legacy(...,
"research_rigor", STRATEGY_HALL_OF_FAME_NUDGE)`) — a real, checked
example of "successful innovations automatically update Company DNA."
**Now also real:** every retirement — Hall of Fame induction or Failed
Archive filing alike — writes a real `MemoryRecord` under the
`"strategy"` `MemoryCategory` (see `app/scribe.py`'s
`record_strategy_hall_of_fame_entry()`/`record_strategy_failed_archive_entry()`,
called from `app/state.py`'s `retire_strategy()`). `"strategy"` has been
a declared `MemoryCategory` — and already included in
`app/knowledge.py`'s `KNOWLEDGE_CATEGORIES` for the Company Knowledge
Library — since long before this chapter, but nothing ever actually
recorded one; this closes that real, pre-existing gap rather than
inventing a new category. **Still not real:** a Knowledge Graph node for
a retired strategy specifically documenting its Hall of Fame/Failed
Archive outcome — though a retired `Strategy` already becomes a real
`strategy`-type Knowledge Graph node via Chapter 61's own extension
(any non-`idea`-stage strategy qualifies, retired included), so the
graph already reflects retirement, just not yet the outcome split
itself as a separate, dedicated relation.

## CEO Controls

| Control | Status |
|---|---|
| Innovation Budget | **Built** — `RiskLimits.maxLimitedLiveCapital` (default $2,000, matching the prior fixed `MAX_LIMITED_LIVE_CAPITAL`) is now a real CEO-configurable field, threaded through `app/sandbox.py`'s `begin_limited_live()`. |
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

**What was actually built (Knowledge Integration):** every strategy
retirement — Hall of Fame induction or Failed Archive filing alike — now
also files a real `MemoryRecord` under the pre-existing but never-before
-populated `"strategy"` `MemoryCategory`. Two new `app/scribe.py`
wrappers (`record_strategy_hall_of_fame_entry()`,
`record_strategy_failed_archive_entry()`), called from `app/state.py`'s
`retire_strategy()` alongside the pre-existing Company DNA nudge — no
new persistence, no new category invented, closing a real, pre-existing
gap (the category already lived in `app/knowledge.py`'s
`KNOWLEDGE_CATEGORIES` for the Company Knowledge Library, with nothing
ever writing to it). Verified: 3 new tests confirming both entry types
become real `"strategy"`-category memories and respect the CEO's
`maxMemoryRecords`
(`tests/test_scribe.py`), 1 integration test confirming
`GameState.retire_strategy()` actually writes the memory end-to-end
(`tests/test_state.py`), and a live retirement (`POST
/api/sandbox/retire`) against the running dev server confirming the real
`MemoryRecord` appears in `GET /api/load/archive/knowledge_archive`
(the `memory` field lives in the `knowledge_archive` archive module, not
`GET /api/load`'s core response — a real detail this verification
surfaced, not a bug).

**What was actually built (Innovation Budget CEO control):** one new
`RiskLimits` field, `maxLimitedLiveCapital` (default $2,000, matching
the exact prior fixed constant `MAX_LIMITED_LIVE_CAPITAL`), threaded
through `app/sandbox.py`'s `begin_limited_live()` (its one real call
site, `app/state.py`'s `begin_strategy_limited_live()`). `POST
/api/risk-limits` extended with the field, validated (> 0). Verified: 2
new tests for the Sandbox's own ceiling behavior at a CEO-raised/
lowered cap (`tests/test_sandbox.py`), 2 CEO write-path tests
(`tests/test_state.py`), and a live `POST /api/risk-limits` call
confirming both the accepted value and the rejected one (`0` →
"Maximum Limited Live Capital must be a positive amount.").

**What was actually built (Experiment Tiering):** `app/strategy_lab.py`'s
`compute_experiment_tier()`, wired into `generate_strategy_dossier()` so
`StrategyDossier.experimentTier`/`experimentTierRationale` are real
whenever a Monte Carlo result exists (`None` otherwise — never guessed).
Real magnitude — the larger of projected upside or realized downside
from the strategy's own Monte Carlo bootstrap — bucketed against three
honestly-arbitrary-but-declared thresholds (10%/25%/50%), not a
fabricated risk score. Surfaced in `StrategyCertificationView.tsx` as a
tone-coded badge next to the Monte Carlo Testing card. Verified: 5 new
backend tests covering each tier boundary and confirming the larger-
magnitude side (upside vs. downside) drives the classification
(`tests/test_strategy_lab.py`), 2 dossier-level tests confirming
`experimentTier` is real when Monte Carlo exists and `None` when it
doesn't, `tsc`/`eslint`/`vite build` clean, and a live
`GET /api/sandbox/dossier` call against the running dev server returning
a real tier and rationale for a strategy with a real Monte Carlo result.

Across all three pieces: `mypy`/`ruff` clean, full backend suite
1039/1039 passing.

**What's explicitly out of scope until named gaps close:** Pilot
Duration and Automatic Promotion Rules (both would require new
state-tracking mechanisms — a real stage-entry timestamp check and a
background auto-advance path through `app/nexus.py`'s `tick()` — bigger,
riskier changes than a constant promotion, deliberately not attempted
alongside the three pieces above); "Innovation Success Rate" as the
brief frames it (would need to track abandoned ideas that never became a
real `Strategy` object — fabrication, not analysis); an actual automated
Design Bible-writing capability (see Design Bible Integration, above —
a category error, not a missing feature); Academic Research/
external-data ingestion (no such dependency exists in this codebase); a
dedicated Knowledge Graph relation for a retired strategy's specific
Hall of Fame/Failed Archive outcome (the strategy itself already becomes
a real graph node via Chapter 61's own extension — see Knowledge
Integration, above).

**Before implementation begins:** per Appendix G's Permanent Development
Policy, this chapter is the required design-first step, satisfied before
this pass began. The remaining CEO controls are a well-scoped, separate
future follow-up.

## Addendum — Statistical Evidence Gate on Strategy Retirement (Trading Psychology & Discipline, Piece B)

**Status:** Real, implemented (`app/strategy_lab.py`'s
`evaluate_retirement_readiness()`, enforced in `app/state.py`'s
`retire_strategy()`).

**Origin.** The second piece of a CEO-requested trading-psychology
roadmap (see Chapter 66's own Behavioral Circuit Breaker addendum for
Piece A and its full origin story). This piece traces to the CEO's
review's own Strategy Evaluation Discipline principle: "avoid strategy
hopping; if evidence insufficient, keep current strategy and continue
collecting data" and "a single bad run does not invalidate a strategy."

**The real gap.** `app/sandbox.py`'s `retire_strategy()` docstring
already said retirement was "expected to cite that strategy's own real
StrategyHealthAssessment... as the reason" — but nothing ever checked
that any real evidence existed at all. A strategy could be retired,
including a live `"approved"` strategy already committing real allocated
capital, after a single bad simulation run or zero runs, purely on CEO
impulse. This chapter's own Certification gate
(`evaluate_certification_readiness()`) already established the exact
"real, ENFORCED gate, `(bool, str)`" pattern for a different stage
transition (Limited Live Capital) — retirement had no equivalent.

**The fix.** `evaluate_retirement_readiness(strategy, results)` reuses
the identical `trade_count = sum(r.trade_count for r in
strategy_results)` computation `evaluate_certification_readiness()`
already uses — never a second, differently-defined "sample size."
`MIN_RETIREMENT_TRADE_COUNT = 10`, real and disclosed, deliberately
looser than Certification's own `CERTIFICATION_MIN_TRADE_COUNT = 20`
(retiring is not the same trust-earning bar as certifying for live
capital — the point is only "is there enough real evidence to conclude
anything at all," not a quality bar). Vacuously ready for a strategy
still at `"idea"`/`"research"`: those stages have no real
`SimulationResult` by construction, so there is no thin evidence to
gate — abandoning an untested idea is always a legitimate, ungated CEO
call. Once a strategy has entered real empirical testing
(`historical_backtest` or later, including a live `"approved"`
strategy), retirement requires the real minimum trade count on file;
below it, `retire_strategy()` returns a real, actionable error and the
strategy's stage does not change.

**What this does NOT do, by design.** It never blocks retirement of a
strategy with plenty of evidence and a genuinely good `StrategyHealth`
read — the CEO retains full authority over the actual decision (a
strategy might be abandoned for a legitimate business reason unrelated
to performance). It never forces the CEO's free-text reason to
literally cite the health read (the retirement form's placeholder
already invites this; enforcing it via string-matching would be fragile
over-engineering, not a real evidence check). It is a floor on evidence
quantity, never a judgment on evidence quality.

**Frontend.** `StrategyPipelineView.tsx`'s existing Retirement card
gains a real, mirrored evidence readout (`{totalTradeCount} real
trade(s) on file (needs ≥{MIN_RETIREMENT_TRADE_COUNT}...)`) once a
strategy has entered real testing — reusing the same real `ownResults`
this file already computes, not a second data source — plus the
existing shared `error` display duplicated next to the retire button
(previously only rendered in the Testing Environments card above,
easy to miss on this new failure mode).

**Verified:** 8 new pure-function tests
(`tests/test_strategy_lab.py::TestEvaluateRetirementReadiness` —
idea/research always ready, zero-evidence blocked, below/at/above the
threshold, cross-strategy result isolation, a live `"approved"`
strategy still gated), 4 new `GameState`-level tests
(`tests/test_state.py::TestRetireStrategy` — blocked with too few real
trades, allowed at the threshold, an untested idea ungated, a live
approved strategy still gated), full backend suite green (1508/1508),
`mypy`/`ruff` clean, `tsc -b --noEmit`/`npm run lint` clean. A live
retirement against the running dev server (`POST /api/sandbox/retire`
on a real strategy with 228 real trades on file) confirmed the
"sufficient evidence" path end-to-end through the actual HTTP API; the
"insufficient evidence" block is proven by the automated `GameState`-
level tests above exercising the identical code path, since every
strategy already in that dev save happened to carry well over the
10-trade minimum.

## Addendum — Model Validator (Quantitative Research & Intelligence System, Piece 4)

**Status:** Real, implemented (`app/model_validation.py`, generated
inside `app/state.py`'s `request_strategy_company_review()`). Advisory-
only.

**Origin.** A large CEO specification ("TradeTown Quantitative Research
& Intelligence System") asked for six real quant roles cooperating
without collapsing into one general-purpose "Quant AI," each with real
substance rather than a rename of existing agents — explicitly: *"The
goal is NOT to simply label existing AI agents as 'quants.'"* Research
found four of the six roles already real under different names (Chief
Quant = Vector, Risk Quant = Sentinel/Guardian/Keystone, Quant
Researcher = Vector + this chapter's own Strategy Lab pipeline), leaving
the Model Validator as the one genuine gap: no seat in the existing
5-reviewer `StrategyReview` panel was a standing, independent
validation authority whose job is specifically to challenge a
strategy's statistical soundness before it advances — *"A model should
not become an approved production strategy merely because the Research
Quant created it."* The CEO named **Meridian (CIO)** as that authority
and scoped this first piece as advisory-only, with fifteen binding
requirements covering independence, non-duplication of risk logic, a
four-state verdict, full auditability, and an explicit instruction not
to start further quant pieces until this one shipped, tested, and
verified.

**The design.** `generate_model_validation_report()` runs once per
`request_strategy_company_review()` call — the same real action that
already files a `StrategyReview`, confirmed by grep to be
`generate_strategy_review()`'s only call site in this codebase. Five
checks (sample size, regime breadth, tail risk, liquidity realism,
expectancy), each a `ModelValidationCheck` with `passed: bool | None`
(never coerced when unevaluable) and a `thresholdSource` string citing
exactly which existing constant it reused. Every threshold is a proven
reuse of this chapter's own Certification gate
(`CERTIFICATION_MIN_TRADE_COUNT`, the `len(tested) >= 2 and not
weak_buckets` regime-consistency pattern, `CERTIFICATION_MAX_RUIN_PCT`,
`StrategyLiquidityValidation.verdict` as-is, and the certification
gate's own `expectancy > 0` formula) — none invented for this piece.
The four-state verdict (`approved` / `rejected` / `needs_more_evidence`
/ `not_validatable`) never defaults to `approved`: a clear failure among
evaluated checks always yields `rejected` even when other checks remain
unevaluated, so missing evidence can never launder an
already-established failure.

**Independence, precisely.** Meridian does not re-derive these numbers
from a separate raw-data pipeline — none exists in this codebase.
Meridian reviews and challenges the same computed evidence (Monte Carlo
bootstrap, regime test, liquidity validation, real trade/expectancy
history) that Vector's research and Sentinel/Guardian/Keystone's risk
review also draw on. What is real here is **organizational/decision
independence**: Meridian did not author this strategy's research or
risk read, and — via `app/sandbox.py`'s `exclude_cio` parameter on
`_devils_advocate_verdict()`/`generate_strategy_review()` — cannot
simultaneously serve as this same review cycle's rotating Devil's
Advocate. This exclusion is a pure, stateless substitution keyed only on
`(strategy_id, existing_review_count)`: it never alters the underlying
rotation formula, never persists past the single call that sets it, and
never leaks between strategies — proven by a dedicated 6-case test
class (`TestDevilsAdvocateExclusionStatelessness` in
`tests/test_model_validation.py`) covering same-strategy scoping,
unrelated-strategy eligibility, post-cycle rotation recovery,
re-run idempotence, cross-strategy independence, and the untouched base
formula at every other rotation slot.

**Advisory-only, precisely.** `app/sandbox.py`'s
`apply_review_decision()` and `begin_company_review()` are byte-for-byte
unmodified — `apply_review_decision()`'s own signature has no
`ModelValidationReport` parameter, so it cannot read `verdict` even in
principle. The report is generated, persisted (`strategy_model_
validations` on `GameSaveState`), broadcast over WS, and surfaced to the
CEO purely for visibility. `TestAdvisoryOnlyProof` constructs the
identical Company Review scenario with and without a `rejected`
ModelValidationReport attached and asserts an identical stage
transition either way. **Future promotion criteria** (advisory →
blocking) is intentionally left undocumented as a specific number or
date here — the CEO's own requirement was that any such change be a
deliberate future decision the CEO makes explicitly, never a hardcoded
timer this piece invents on her behalf.

**No duplicated risk logic.** Nothing here reads or writes
`gatekeeper.py`, `risk_engine.py`, or any Circuit Breaker state — this
is not a second Risk Quant or a second Gatekeeper, per the CEO's own
explicit requirement.

**Verified:** 30 new pure-function tests
(`tests/test_model_validation.py` — each of the five checks'
pass/fail/not-evaluable states, four-state verdict logic including the
"missing evidence never launders a real failure" case, the six DA-
exclusion statelessness cases, the advisory-only proof, and two
no-fabricated-evidence checks), full backend suite green (1591/1591),
`mypy`/`ruff` clean, `tsc -b --noEmit`/`npm run lint`/`npm run build`
clean. Live-verified end-to-end against the real running dev backend:
a real strategy (News Momentum) was driven through Backtest → Market
Simulation → Paper Trading → Limited Live Capital → a real `POST
/api/sandbox/request-review` call, which returned a genuine `"approved"`
`ModelValidationReport` with real evidence strings (e.g. "378 real
trade(s) across 12 real run(s) on file," "Real probability of ruin 0.0%
across 200 real simulated paths") and `validatorAgentId: "cio"` —
confirmed again via a direct `GET /api/sandbox/model-validation` call.
The frontend card (`StrategyPipelineView.tsx`'s new "Model Validation —
Meridian" section) was code-reviewed against this exact live response
shape and the same props/typing this chapter's other cards already use;
a literal browser screenshot could not be captured in this session's
sandboxed Playwright environment, which crashes on an unrelated,
pre-existing tileset-texture-decode failure (`[TileWorld] Failed to
build tileset`) reproducing identically on a brand-new "New Game," with
zero files this piece touched anywhere in the crash's call path — the
same kind of environment-specific gap this chapter's own Piece B
addendum above already disclosed rather than silently claiming full
coverage.
