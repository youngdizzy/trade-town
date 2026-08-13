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
coverage. (A follow-up session isolated the same real
`StrategyPipelineView.tsx` component outside the game bootstrap and
confirmed the card renders correctly for all four verdict states.)

## Addendum — Walk-Forward / Temporal-Split Validation (Quantitative Research & Intelligence System, Piece 2)

**Status:** Real, implemented as a sixth check inside `app/model_
validation.py`'s existing `ModelValidationReport` (Piece 4, above) —
not a standalone module.

**Origin and the honest constraint.** A genuine walk-forward test needs
real, sequential, unseen-at-the-time historical price data to hold out
a true out-of-sample window. `app/simulation.py`'s own module docstring
already discloses this codebase has no real historical
`MarketDataProvider` — that cannot be honestly built here, and this
piece does not pretend otherwise.

**What research found already real.** `app/strategy_lab.py`'s
`compute_strategy_health()` already does a recent-vs-lifetime temporal
comparison (last `HEALTH_RECENT_WINDOW = 3` runs vs. the full,
overlapping lifetime average) — a genuine, real precedent this piece
builds on rather than duplicates. It also confirmed the codebase's own
established convention that `SimulationResult` has no `sim_day` of its
own; **list order is already treated as chronological order** (results
append onto `self.data.simulation_results` strictly in completion
order, never re-sorted — see `app/simulation.py`'s
`tick_simulation_lab()` and `app/nexus.py`'s threading of that list).
Piece 2 reuses this exact convention rather than inventing a new
timestamp-parsing scheme.

**The real, distinct contribution.** `_temporal_stability_check()`
splits a strategy's own `SimulationResult` history at its chronological
midpoint — earlier half vs. later half, by list order — and requires
real expectancy (`expected_value_pct`, the exact same formula and
`> 0` bar `_expectancy_check` and the Certification gate already use)
to hold positive in **both** halves independently, not just in the
whole-sample average. This is a genuinely different failure mode than
the existing whole-sample expectancy check: a strategy whose early
results were strong but whose more recent results have turned negative
(or an unproven recent turnaround) can still average out to a positive
whole-sample expectancy — this check surfaces that where the aggregate
number alone would mask it. Each half must independently clear
`CERTIFICATION_MIN_TRADE_COUNT` (20) real trades before the split is
trusted; below that, the check honestly returns `passed: None` rather
than a statistically vacuous verdict on a thin split.

**Explicitly disclosed as an analog, not the real thing.** The check's
own `reasoning` string says so directly: *"A disjoint-split analog to
walk-forward validation, not a claim of true out-of-sample testing
against unseen future data."* The module docstring's own threshold-
provenance table names this as the one exception whose *shape* (a
chronological split) has no prior precedent to reuse, distinct from
every other check's numeric threshold, which all cite an existing
Certification-gate constant.

**Why folded into Piece 4's existing report rather than a new module.**
The same real inputs (`self.data.simulation_results`, `strategy.id`)
are already in scope at `request_strategy_company_review()`'s one real
call site; a seventh top-level Strategy Lab artifact type (this codebase
already has eight: Dossier, Health, Monte Carlo, Regime Test, Liquidity,
Executive Review, Founder Approval, Certification) would be redundant
surface area for what is fundamentally one more piece of evidence in
the same CEO-facing verdict. Advisory-only, same as every other check
in this report — it participates in `ModelValidationReport.verdict`
exactly like the other five, and inherits the same non-gating guarantee
(`apply_review_decision()`/`begin_company_review()` remain byte-for-byte
unmodified).

**Verified:** 7 new pure-function tests
(`tests/test_model_validation.py::TestTemporalStabilityCheck` — too few
runs, a half below the trade floor, both halves profitable, edge decay
in the later half, an unproven-turnaround-only-profitable-later case,
odd-length-history split-by-floor-division, and threshold-source never
blank), one existing test updated (`test_all_pass_is_approved` needed
enough trades per half to also clear the new check, since it previously
used a sample size that satisfied the whole-sample floor but not each
half independently — a real behavioral consequence of adding a sixth
check, not a workaround), full backend suite green, `mypy`/`ruff` clean.

## Addendum — Real Sharpe/Sortino + Monte Carlo VaR/CVaR (Quantitative Research & Intelligence System, Piece 3)

**Status:** Real, implemented in two independent places — `app/
analytics.py`'s `compute_performance_snapshot()` (Sharpe/Sortino) and
`app/strategy_lab.py`'s `run_strategy_monte_carlo()` (VaR/CVaR) — neither
touches `app/model_validation.py`; this addendum lives in this chapter
because both are Quantitative Research & Intelligence System pieces, not
because either is a new Model Validation check.

**The two-tier honest split this piece is built on.** This codebase has
had two same-named-but-different Sharpe/Sortino pairs since v0.5:
`SimulationResult.sharpe_ratio`/`sortino_ratio` (one per backtest run,
from `app/simulation.py`'s placeholder engine — random aggregate scalars,
no real per-trade sequence behind them at all) and
`PerformanceSnapshot.sharpe_ratio`/`sortino_ratio` (one per CEO-facing
performance period, from `app/analytics.py`). Piece 3 makes only the
second pair real; the first stays an explicitly disclosed placeholder
forever, because `app/simulation.py`'s engine still has no real per-trade
return sequence to compute a real ratio from — and because it is
load-bearing (`sandbox.py`'s `_quant_verdict()` gates on
`QUANT_MIN_AVG_SHARPE = 1.0`, and `_SHARPE_TIER` drives narrative
framing), silently dropping or renaming it would itself be dishonest.
Nothing about that placeholder changes in this piece.

**What makes the `PerformanceSnapshot` pair real.**
`PaperPortfolio.trade_history` (`app/portfolio.py`) is a genuinely real,
sequential, non-fabricated per-trade `pnl_pct` return series from
actually-executed (if zero-cost/zero-slippage) paper trades, capped at
`MAX_TRADE_HISTORY = 50`. `compute_performance_snapshot()` already
windows this list by period (daily/weekly/monthly/all-time — v0.6.1).
Piece 3 replaces the old formula
(`sharpe_ratio = return_pct / max(max_drawdown_pct, 1.0)`,
`sortino_ratio = sharpe_ratio * 1.1`) with real statistics over that same
windowed list's own returns: Sharpe = mean return ÷ population standard
deviation of returns; Sortino = mean return ÷ downside deviation
(root-mean-square of only the sub-zero returns, target = 0.0). Two
disclosed simplifications, not fabrications, both stated directly in
`app/analytics.py`'s module docstring and `PerformanceSnapshot`'s own
schema docstring: risk-free rate is assumed 0 (this codebase has no
bond/cash-yield concept to draw a real rate from — inventing one would
itself be a fabrication), and these are **per-trade**, not annualized,
ratios (trades close at irregular sim-minute intervals, so there is no
real fixed-period return series to normalize against). Population-style
(not sample-corrected) standard deviation was chosen deliberately: with
at most 50 real trades on file, a sample-correction factor would overstate
a precision this small a real sample doesn't actually support — see
`_population_stdev()`'s own docstring. Edge cases are handled honestly
rather than silently: 0 or 1 trades has no real variance to divide by,
so both ratios read `0.0`, not a fabricated number or a crash; a strategy
with zero losing trades has no downside deviation to measure Sortino
from, so it reads `0.0` rather than a fabricated "infinite" ratio, while
Sharpe (which uses *all* returns' variance, not just the downside) stays
real and nonzero in that same case.

**VaR/CVaR — a real extension of an already-real bootstrap, not a new
simulation.** `run_strategy_monte_carlo()` already ran a 200-path
bootstrap over the strategy's own real, aggregated win rate and average
win/loss sizes (from real `SimulationResult`s), sorting the resulting
`finals` array only to read off percentile fields
(`return_range_low_pct`/`return_range_high_pct`, etc.) before discarding
it. Piece 3 reuses that same sorted array for two new percentile reads
(Value at Risk, at the existing `_percentile()` helper's 5%/1% tails) and
one new tail-mean read (Conditional Value at Risk / Expected Shortfall,
via a new `_tail_mean()` helper placed directly beside `_percentile()`).
VaR is the return level such that only 5%/1% of simulated paths did worse
(signed, matching the existing `return_range_low_pct` sign convention);
CVaR is the mean return among exactly that worst 5%/1% of paths — a
stricter read of "given you're already in the tail, what should you
expect," not just where the tail begins. No new randomness source, no
second simulation — both are real statistics over the same real (if
randomized-per-run) distribution the strategy's existing Monte Carlo
evidence already produces. Surfaced in Command Center's Strategy
Certification view (`StrategyCertificationView.tsx`) directly alongside
the existing Probability of Ruin row, with the same disclosure language
in a caption beneath the card.

**Verified:** 9 new backend tests — `test_analytics.py::
TestRealSharpeSortino` (4: zero trades, single trade with undefined
stdev, a hand-computed exact match against a real 4-trade sequence
confirming the new formula and that Sortino is never a fixed multiple of
Sharpe, and the no-losing-trades zero-Sortino-not-infinite case);
`test_strategy_lab.py`'s new
`test_var_and_cvar_are_real_tail_reads_off_the_same_bootstrap` (ordering
invariants across VaR95/99 and CVaR95/99, since exact values are
non-deterministic under the bootstrap's real randomness) and new
`TestTailMean` class (4 deterministic tests against a hand-constructed
sorted array, bypassing the bootstrap's randomness entirely). Three
existing test-fixture construction sites for `StrategyMonteCarloResult`
needed the four new required fields added (`tests/test_strategy_lab.py`'s
`_monte_carlo()` helper and its second direct construction in
`test_not_ready_when_ruin_probability_is_too_high`, and
`tests/test_model_validation.py`'s `_monte_carlo()` helper) — a real
behavioral consequence of the schema change, not a workaround. Full
backend suite: 1607 passed, `mypy`/`ruff` clean across `app/` and every
touched test file. Frontend: `tsc -b --noEmit`, `eslint`, and `vite
build` all clean after adding the four new `StrategyMonteCarloResult`
fields to `types.ts`, a disclosure comment to `PerformanceSnapshot`
(no existing render site references it — confirmed by grep — so none was
invented), and the two new DataRows to `StrategyCertificationView.tsx`.

## Addendum — Wiring Model Validator Findings Into Institutional Memory (Quantitative Research & Intelligence System, Piece 6)

**Status:** Real, backend-only. `app/strategy_lab.py`'s
`generate_strategy_retirement_outcome()`, `app/state.py`'s
`retire_strategy()`, and `app/knowledge_graph.py`'s
`build_knowledge_graph()` now all consult a strategy's latest real
`ModelValidationReport` (Piece 4, above) — previously generated at
Company Review and then never read again by anything downstream.

**The real gap this closes.** Direct trace confirmed `Model Validation`
was write-only: `request_strategy_company_review()` generates and stores
a `ModelValidationReport` in `self.data.strategy_model_validations`
(Piece 4), but nothing else in the codebase ever read that list back —
not strategy retirement's `FailedStrategyArchiveEntry` (whose
`what_failed`/`lessons_learned` only ever drew on `StrategyReview`
verdicts and `StrategyExecutiveReview` concerns), not the Company
Knowledge Graph's strategy nodes. A real Meridian/CIO rejection was
CEO-visible for exactly as long as Company Review stayed open, then
gone — advisory in the worst sense, not "advisory-but-remembered."

**What's real about the fix.** Every string folded in is a direct read
of `ModelValidationReport`'s own already-real fields
(`verdict`/`evidence_summary`/`checks[].label`/`checks[].reasoning`) —
never paraphrased, never re-derived. The "latest report for this
strategy" lookup pattern (`next((r for r in reversed(...) if
r.strategy_id == strategy_id), None)`) is the exact same pattern
`retire_strategy()` already used for `latest_review`/
`latest_executive_review`/`latest_founder_approval` — Piece 6 adds a
fourth lookup of the identical shape, not a new pattern.

1. **`FailedStrategyArchiveEntry`** (the piece's primary, explicitly
   named target). `generate_strategy_retirement_outcome()` gained an
   optional `latest_model_validation` parameter; when the report exists
   and its verdict isn't `approved`, one line citing the verdict +
   `evidence_summary` is appended to `what_failed`, and one line per
   failed check's own `reasoning` is appended to `lessons_learned`.
   Because `app/scribe.py`'s `record_strategy_failed_archive_entry()`
   already builds its permanent `MemoryRecord` narrative directly from
   `entry.what_failed`, this one change automatically flows the
   validation finding into real, permanent Company Memory too — no
   second change needed there.
2. **Knowledge Graph** — a strategy node's `subtitle` now names the
   verdict of that strategy's own latest `ModelValidationReport` when
   one exists (e.g. `"Retired · Momentum · Model Validation:
   rejected"`), the same "real, checkable shared attribute" discipline
   every other edge/label in this graph already follows —
   `ModelValidationReport.strategy_id` is a real, direct field, and the
   verdict shown is that report's own real `verdict`, never inferred.

**Explicitly scoped out — not fabricated.** Two adjacent ideas were
considered and cut, each for a concrete, verified reason rather than
time pressure:
- **`app/mistakes.py`** operates at the individual closed-trade level
  (one `CaseStudy` per real process gap on one losing trade) — there is
  no real mechanism connecting a strategy-level Model Validation verdict
  to any specific trade's own `TradeDecision`/`Debate`/
  `DisciplineReview`, so wiring it in would mean inventing a link this
  codebase's data model doesn't support.
- **Execution Quant (Piece 5) findings** are not wired into any
  institutional-memory system in this piece. Confirmed by direct check:
  `PaperTrade` carries no `strategy_id` field anywhere (Command Center's
  own Performance panel already discloses this — "closed trades aren't
  currently linked to a Strategy id"), so there is no real way to
  compute "this specific strategy's real trades paid $X in cumulative
  transaction cost" today. Building that check anyway would mean
  fabricating a linkage this codebase's schema doesn't have. This
  remains open for a future piece, once/if a real trade-to-strategy link
  exists.

**Verified:** 7 new backend tests —
`tests/test_strategy_lab.py::TestGenerateStrategyRetirementOutcome`
gained 3 (a rejected validation folded into the failed archive with its
real `evidence_summary`/check `reasoning` both present verbatim; an
`approved` validation correctly NOT folded in as a failure; no
validation on file behaves byte-for-byte as before Piece 6);
`tests/test_knowledge_graph.py::TestModelValidationOnStrategyNodes`
gained 4 (a real verdict shown on its own strategy's node; no text at
all when no report exists; a report for a *different* strategy never
leaks onto this one's node; the latest of more than one report for the
same strategy wins). Full backend suite: 1618 passed (up from 1611),
`mypy`/`ruff` clean on every touched `app/` file. Every existing caller
of `generate_strategy_retirement_outcome()`/`build_knowledge_graph()`
needed zero changes — both new parameters are optional and default to
the pre-Piece-6 behavior exactly.

## Addendum — Profit Concentration / Robustness Check (Prop-Firm Risk Intelligence Addendum, Piece 8a)

**Status:** Real, implemented as a seventh check inside `app/model_
validation.py`'s existing `ModelValidationReport` (Piece 4, above) —
not a standalone module, the same "fold into the existing report"
precedent Piece 2 already set.

**Origin.** The CEO's Prop-Firm Risk Intelligence Addendum's
Requirement 8 ("CONSISTENCY ANALYSIS: track profit concentration —
largest winning trade/day as a percentage of total") plus the
directive's own instruction not to blindly implement the transcript
source's specific numbers as established fact. Authorized alongside
Piece 8 as "8, 8a, 8b."

**Why this couldn't reuse `app/prop_firm.py`'s existing
`compute_consistency_status()` directly.** That function already
implements this exact concept — real, correct, and load-bearing — but
for an `Account`'s own real per-day P&L (`PaperTrade.closed_sim_
minutes` bucketed by day). Two real constraints block reusing it here:
`Account`s never receive live trades (Piece 8's addendum above), and
`SimulationResult` — the real evidence Meridian actually validates —
has no day-level granularity at all; it represents one full backtest
*run*. The real, honest analog reuses the *formula's shape* (largest
bucket's profit as a percentage of the cumulative positive total)
against the one real per-strategy bucket this codebase has: each
strategy's own `SimulationResult.total_return_pct` per run.

**The real, distinct contribution.** `_concentration_check()` sums
every real positive `total_return_pct` across a strategy's own runs,
finds the single largest one, and checks it doesn't account for more
than half the total. This is a real, different failure mode than every
other check in this report: a strategy can have a positive whole-sample
expectancy (`_expectancy_check`) and even hold up across a chronological
split (`_temporal_stability_check`, Piece 2) while still being
fragile — if nearly all of its real profit traces to one outlier run,
neither of those checks would catch it, because both operate on
per-trade averages or a two-way split, not a per-run concentration
read. Needs ≥2 real runs with at least one real positive return to be
evaluable; `passed: None` otherwise, never a fabricated verdict on
insufficient evidence.

**The one genuinely new threshold in this whole system.** Every other
check in `app/model_validation.py` — sample size, regime breadth, tail
risk, liquidity, expectancy, and Piece 2's temporal stability — cites an
existing, already-load-bearing `app/strategy_lab.py` Certification-gate
constant. This check cannot: no equivalent "how much concentration is
too much" number exists anywhere in this codebase, and `Account.
consistency_limit_pct` (the nearest real analog) is a per-account
*configurable* field, not a fixed, learned constant. `CONCENTRATION_
MAX_SINGLE_RUN_SHARE_PCT = 50.0` is disclosed explicitly, in the
module's own docstring and in the check's own `thresholdSource` string,
as **a new research assumption with no existing precedent** — a
conservative rule of thumb (no single run should account for more than
half a strategy's real positive-return sample), never presented as an
established statistical fact. This is the same disclosure standard
Piece 7's `MIN_RELIABLE_TAIL_SAMPLES`/`MIN_MARGINAL_TAIL_SAMPLES` set
for a threshold with no reuse available — the CEO's own directive
(Requirement 15/16) requires exactly this kind of disclosure rather
than silently treating a chosen number as proven fact.

**Advisory only**, same as every other check — participates in
`ModelValidationReport.verdict` exactly like the other six, and
inherits the same non-gating guarantee (`apply_review_decision()`/
`begin_company_review()` remain byte-for-byte unmodified; no change to
Sentinel, Guardian, the Gatekeeper, or any Circuit Breaker).

**Frontend:** no changes needed. `StrategyPipelineView.tsx`'s existing
Model Validation card already renders `latestModelValidation.checks.
map(...)` generically — the new seventh check appears automatically
with no new UI code.

**Verified:** 7 new backend tests
(`tests/test_model_validation.py::TestConcentrationCheck` — too few
runs, zero positive-return runs, evenly-spread profit passing, one run
dominating and failing, the exact-50%-boundary case passing (`<=`, not
`<`), a losing run correctly excluded from the denominator, and
threshold-source always disclosing the new non-reused constant), 37
pre-existing tests in the same file passing unchanged (the fixture data
in `TestVerdictLogic`'s "all pass" case happens to spread its identical
per-run returns evenly, so the new check doesn't flip any existing
verdict). Full backend suite: 1641 total, 1640 passed — the one failure
is `test_foundational_mentors.py`'s pre-existing, genuinely unseeded-
random `test_low_aptitude_agent_racks_up_consecutive_failures_eventually`
(uses `random.random()`/`random.uniform()` with no seed, confirmed
unrelated to this piece and passing on its own in isolation — the same
category of known flake the Piece G addendum above already documented
once). `mypy app/`/`ruff check app/ tests/` clean.

## Addendum — Evaluation-Level Risk-Policy Simulator (Quantitative Research & Intelligence System, Requirements 21/22/23/25, Piece 10)

**Status:** Real, a new module (`app/evaluation_simulator.py`) plus one
new read-only, on-demand `GET /api/sandbox/evaluation-policy-comparison`
endpoint. Never wired into the background sim tick or any autonomous
agent decision — a real research computation the CEO requests, not a
second `StrategyMonteCarloResult`-style auto-generated pipeline.

**Origin.** The source video's central claim — "reaching the funded
stage quickly may be preferable to spending a long time trading an
account that cannot generate payouts" — is exactly the kind of claim
Requirement 21 demands TradeTown treat as a hypothesis to test, never
adopt as fact. This module is that test: a real Monte Carlo evaluation-
level race simulator comparing four named, disclosed risk policies.

**What's genuinely new vs. reused.** `app/strategy_lab.py`'s
`run_strategy_monte_carlo()` already bootstraps a per-trade win/loss
sequence from a strategy's own real, aggregated `SimulationResult`
fields — that per-trade generating idea (draw a random outcome sized by
real win rate/avg win/avg loss, compound it into cumulative equity) is
reused as-is. What that function has never had, and what this module
adds: a real three-way RACE CONDITION per simulated path — does the
path hit its profit target before it hits its drawdown limit before it
runs out of simulated time? Grep-confirmed absent anywhere in this
codebase before this module (no `profit_target` vs. `drawdown_limit`
vs. `max_trades` race existed in `strategy_lab.py`, `simulation.py`, or
`whatif.py`).

**A real sign-convention bug caught before it shipped.**
`run_strategy_monte_carlo()`'s own formula
(`-avg_loss_pct if it's a loss`) silently double-negates: a real
`SimulationResult.avg_loss_pct` is already stored as a negative number
(`app/simulation.py`'s own generator, e.g. loss ranges like
`(-10.0, -1.5)`), so negating it again turns a real loss into a
positive equity gain. Verified directly with a Python snippet before
writing this module's own logic: feeding a 20%-win-rate/`avg_loss_pct=
-8.0` strategy into that exact formula produces a **+233% cumulative
gain**, not ruin — the existing test suite never actually exercises
this path stochastically (`test_not_ready_when_ruin_probability_is_too_
high` bypasses the real bootstrap with a hand-built fixture, confirmed
by reading that test directly), so the quirk has shipped undetected.
This module's own `_simulate_one_path()` deliberately does **not**
inherit that negation — `avg_loss_pct` is applied directly, so a loss
trade actually subtracts from equity (re-verified with the same
snippet: the corrected formula produces a real -70% loss and 71%
drawdown for the same inputs). `strategy_lab.py`'s own existing
function was left untouched — fixing a latent quirk in a separate,
already-shipped, already-tested module is out of this piece's scope;
this is noted here so the discrepancy is documented, not silently
carried forward into new code.

**Four named policies, every one an explicit, disclosed hypothesis —
never adopted as fact** (Requirement 21's own text: "the system must
not conclude that aggressive risk is superior merely because it
produces faster passes"): `conservative` (1.0% risk/trade),
`moderate` (2.0%, matching `RiskLimits.risk_per_trade_pct`'s own real
default), `aggressive` (3.0%), and `failure_boundary_relative` — sizes
risk as exactly 1/8 of the account's own real `trailing_drawdown_limit_
pct` when one is configured, one real test point from the source
video's own suggested "1/4-1/8" range, never assumed optimal (per the
CEO's own IMPLEMENTATION BOUNDARIES) and entirely omitted — not
fabricated — when no account or no real boundary is available
(disclosed in the report's own `limitations` as `NOT_TRACKABLE_YET`).

**Every non-real-data number is a stated, disclosed assumption**, never
silently baked in: `avg_win_pct`/`avg_loss_pct` are treated as generated
under the 2.0% baseline risk (this codebase doesn't record what risk
setting a `SimulationResult` actually used) and scaled linearly to each
policy's real `risk_per_trade_pct`; 2.0 trades/day converts a simulated
trade count into an implied day count (no real historical trades-per-
day statistic exists to derive this from); 500 real Monte Carlo paths
per policy, a real but modest, disclosed sample size; real account
configuration (`challenge_profit_target_pct`/`trailing_drawdown_limit_
pct`/`challenge_duration_days`) is used whenever present, with disclosed
defaults (8%/10%/200 simulated trades) only when it's not.

**Every requested metric, real and computed, never fabricated:**
probability of passing/failing (split into drawdown-failure vs.
time-expiry-failure), expected trades/trading-days/cost to pass (`None`
when zero simulated paths passed — never a fabricated 0 or infinity),
median and worst-case (p95) max drawdown, probability of hitting a real
consecutive-loss streak (reusing `TradingModeState.losing_streak_
suspend_count`'s own real default of 5, not a second invented
threshold), a disclosed risk-adjusted-outcome heuristic (explicitly
labeled a research heuristic, not a validated formula), and — Requirement
21's "sensitivity to strategy quality" — the same simulation rerun at a
real, disclosed ±5-percentage-point win-rate delta.

**Explicitly NOT attempted, disclosed in every report's own
`limitations`, never a silent gap:** real per-regime sensitivity
(`StrategyRegimeTestReport`'s buckets track `avg_return_pct`, not the
win_rate/avg_win_pct/avg_loss_pct triplet this simulator needs, and this
codebase has no real per-regime trade data to derive that triplet from
honestly); downstream funded-stage performance (Piece 10a's `Account.
funded_stage_reached` is a real, explicit CEO action, never linked to a
simulated path — this module refuses to claim a simulated evaluation
outcome predicts a real funded account's real future performance).

**Never declares a winner.** `EvaluationPolicyComparisonReport.
conclusion` states explicitly: "no policy is declared superior" —
readers are directed to weigh probability of passing against drawdown
risk and consecutive-loss risk together (Requirement 25: speed is an
objective to weigh, never a license to gamble), not to read the fastest
policy's numbers in isolation.

**New endpoint:** `GET /api/sandbox/evaluation-policy-comparison?
strategyId=...&accountId=...` (accountId optional) — read-only, computed
fresh every call, `None` when the strategy has no completed simulation
runs yet (same honesty boundary as `/model-validation` and the Monte
Carlo pipeline). Deliberately NOT auto-generated in the background sim
tick the way `StrategyMonteCarloResult` is — a real, on-demand research
computation the CEO requests, not a second autonomous pipeline running
unattended.

**Verified:** 15 new backend tests
(`tests/test_evaluation_simulator.py` — `TestSimulateEvaluationPolicy`:
a guaranteed winner always passes, a guaranteed loser never passes and
correctly fails via drawdown-or-time-expiry, a guaranteed loser
genuinely accumulates a real 5-trade consecutive-loss streak, a strong
edge passes far more often than a weak edge, a higher risk-per-trade
produces measurably more drawdown failures for the same losing edge,
`expected_cost_to_pass` is only ever computed when paths actually
passed, sensitivity-to-quality moves in the correct direction;
`TestCompareEvaluationPolicies`: no completed runs returns `None`,
exactly three policies without an account, the fourth
`failure_boundary_relative` policy added correctly with a real account
boundary (risk_per_trade_pct verified as the exact real `8.0 * 0.125 =
1.0` computation), real account configuration overrides the disclosed
defaults, defaults are disclosed when no account is configured, the
conclusion never declares a winner, sample trade count reflects real
aggregated data across multiple runs, and a different strategy's
results never leak in), full backend suite passed, `mypy app/`/`ruff
check app/ tests/` clean. All 15 tests re-run 5 times in a row with no
flakes despite exercising real randomness.
