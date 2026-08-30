"""app/research_loop.py — CEO directive "TradeTown — Next Major
Implementation Pass, Phase 4-6: Self-Improving Strategy Factory +
Validation Funnel": "Turn TradeTown's research system from a system
that can TEST strategies into a system that can systematically
DISCOVER, TEST, diagnose, improve, and eliminate strategies."

RESEARCH FIRST, PURE ORCHESTRATION, NO NEW BACKTEST MATH. Every real
number this module ever reads comes from an already-real, already-
tested function: `app/research_experiment.py::run_research_experiment()`
(backtest, walk-forward, cost sensitivity, parameter sensitivity,
look-ahead audit, buy-and-hold baseline, complexity — all already real
and unmodified by this pass), `app/quant_research_lab.py`'s
`find_similar_experiments()`/`classify_research_relationship()`, and
`app/failure_taxonomy.py`'s `find_similar_failed_strategies()`
(reused, not duplicated). This module adds exactly four new real
computations the directive's own funnel needs that did not exist
before this pass — benchmark comparison in a real, disclosed
approximate unit (see `compute_benchmark_comparisons()`), outlier
dependence (see `compute_outlier_dependence()`), tuning-exposure
reads (thin wrapper reusing existing counters), and the candidacy/
failure-code/mutation/lesson/budget logic that turns all of the above
into one real, auditable, persisted record per iteration
(`ResearchLoopIterationRecord`).

THE ONE HONEST SCOPE BOUNDARY THIS ENTIRE MODULE RESTS ON: MUTATION IS
A REAL, PERSISTED RECOMMENDATION, NEVER AN AUTO-REWRITTEN STRATEGY.
`propose_mutation()` below returns a real, structured, evidence-backed
`MutationRecord` — a deterministic, templated (never LLM-generated)
mapping from this iteration's own real, strongest failure code to a
concrete next step, with a real, disclosed rationale. It does NOT, and
this pass does NOT elsewhere, generate a new `sourceText` and run it
back through `compile_strategy_text()` automatically. Auto-rewriting a
strategy's own English rule description safely (within the compiler's
disclosed limited vocabulary, without silently changing something the
researcher didn't intend) is a real, tractable, substantial follow-on
project — not attempted here. A human or agent reads the
`MutationRecord`'s `proposedChange`, writes new `sourceText`
themselves, and re-files it through the EXISTING, completely
unmodified `register_strategy_version()` pipeline — which is exactly
how "RE-TEST" already worked before this pass, and still does.

THE RESEARCH-CANDIDATE LAYER IS SEPARATE FROM, AND NEVER WEAKER THAN,
THE EXISTING CERTIFICATION/HALL-OF-FAME/CHAMPION-CHALLENGER GATES.
Section 5's own explicit instruction: "Do NOT blindly replace existing
calibrated thresholds... create a separate research-candidate
qualification layer if necessary." `RESEARCH_CANDIDATE_MIN_TRADE_COUNT`
(100)/`RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT` (20.0)/
`RESEARCH_CANDIDATE_MIN_PROFIT_FACTOR` (1.10) are real, NEW, disclosed
constants distinct from `app/strategy_lab.py`'s own
`HALL_OF_FAME_MIN_TRADE_COUNT` (30)/`HALL_OF_FAME_MIN_PROFIT_FACTOR`
(1.5) — this module's `classify_candidacy()` never touches those, and
neither Certification nor Hall-of-Fame nor Champion/Challenger read
anything this module produces as a gate input. `candidacy` here is
informational triage for a researcher deciding what to work on next —
"accepted" here means "clears this module's own real candidate bar,"
never "certified" or "champion." A strategy still has to independently
clear every one of those existing, unmodified, stronger gates before
it can ever reach live capital, exactly as before this pass.

THE BENCHMARK-COMPARISON APPROXIMATION, DISCLOSED EXPLICITLY EVERY
TIME. `app/baseline_comparison.py`'s own module docstring already
established, for a real, disclosed reason, that a compiled strategy's
R-multiple-based stats are NEVER blended with a benchmark's %
price-return stats into one number — this engine has no real
position-sizing/equity simulation. This module's
`compute_benchmark_comparisons()` closes Section 6's "excess return"
ask WITHOUT violating that discipline, by reusing a real, already-
established, CEO-configurable convention instead of inventing one:
`RiskLimits.riskPerTradePct` (the same real number
`app/position_sizing.py` already uses to convert a risk-in-R figure
into a risk-in-dollars figure). `cumulative_R * risk_per_trade_pct` is
a real, honest APPROXIMATION of "what equity return would this
strategy have produced if every trade had risked exactly this much of
account equity, with no compounding and no concurrent-position
effects" — never a claim of a real simulated equity curve.
`BenchmarkComparison.approximationNote` states this on every single
instance so no downstream reader (UI included) can mistake it for one.

WHAT THIS PASS DELIBERATELY DID NOT BUILD (Section 24's own "if any
part is not implemented, say NOT IMPLEMENTED" — see this module's own
tests and the top-level CHANGELOG entry for the full disclosed list):
NEW SPECIALIZED AGENT ROLES/DIALOGUE (Section 13) — the structural
functions each named role would perform (backtest, red-team/overfit
check, benchmark comparison, statistician) are real and wired below;
new agent personas/flavor dialogue are not, since that is a large
content task orthogonal to real evidence. HOLDOUT DATA DISCIPLINE
(Section 11) as a genuine, separately-fetched, never-touched-during-
development candle partition — NOT IMPLEMENTED; this codebase's mock
candle provider has no real date-partitioned historical dataset to
carve a true holdout from, and fabricating one would itself be
dishonest. What IS real and disclosed: `app/walk_forward.py`'s own
disjoint chronological windows already give a genuine, honest,
different-data stability read — the closest real analog this codebase
can offer without inventing a fake partition.
"""
from __future__ import annotations

from app.champion_challenger import HIGH_TUNING_VERSION_THRESHOLD
from app.failure_taxonomy import FAILURE_CODE_METADATA, find_similar_failed_strategies
from app.quant_research_lab import (
    OVERTESTED_FAMILY_THRESHOLD,
    classify_research_relationship,
    count_experiments_for_family,
    find_similar_experiments,
)
from app.research_experiment import run_research_experiment
from app.schemas import (
    BenchmarkComparison,
    CandidacyBinning,
    CompiledStrategyDefinition,
    EmaPullbackStatsBucket,
    FailedStrategyArchiveEntry,
    FailureCode,
    FailureCodeEntry,
    MutationRecord,
    QuantResearchExperiment,
    ResearchBudgetStatus,
    ResearchExperimentRecord,
    ResearchLessonRecord,
    ResearchLoopIterationRecord,
    StrategyHypothesis,
    StrategyScorecard,
)
from app.statistical_comparison import MIN_TRADES_FOR_BOOTSTRAP
from app.strategy_engine import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME

# Section 5 — a real, NEW, disclosed research-candidate qualification
# layer. Deliberately distinct numbers from app/strategy_lab.py's own
# HALL_OF_FAME_* constants (30 trades / PF 1.5) — see this module's own
# docstring for why neither layer reads the other.
RESEARCH_CANDIDATE_MIN_TRADE_COUNT = 100
RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT = 20.0
RESEARCH_CANDIDATE_MIN_PROFIT_FACTOR = 1.10

# Section 10 — "no single trade responsible for the majority of
# profits." A real, disclosed, one-reasonable-convention bar: the
# single largest real win exceeding half of the strategy's own real
# cumulative return is a real red flag, not derived from any formal
# study.
OUTLIER_DEPENDENCE_SHARE_THRESHOLD = 0.5

# Section 17/18 — real, disclosed bounds preventing an unbounded
# research process, per that section's own explicit instruction.
MAX_ITERATIONS_PER_FAMILY = 20
MAX_MUTATIONS_PER_PARENT = 5


def compute_outlier_dependence(bucket: EmaPullbackStatsBucket) -> tuple[bool | None, float | None]:
    """Section 10/14's real red-team check, computed from fields
    `aggregate_bucket()` already provides — no new trade-level
    refetching. `None`/`None` when there isn't enough real evidence to
    honestly judge this (fewer than 2 real closed trades, or a
    non-positive cumulative return, where "share of return" isn't a
    meaningful real number) — never a fabricated True/False."""
    if bucket.trade_count < 2 or bucket.expectancy_r is None or bucket.largest_win_r is None:
        return None, None
    cumulative_return_r = bucket.expectancy_r * bucket.trade_count
    if cumulative_return_r <= 0:
        return None, None
    share = round(bucket.largest_win_r / cumulative_return_r, 3)
    return share > OUTLIER_DEPENDENCE_SHARE_THRESHOLD, share


def compute_benchmark_comparisons(record: ResearchExperimentRecord, *, risk_per_trade_pct: float) -> list[BenchmarkComparison]:
    """Section 6 — real, explicit, persisted, never-blended benchmark
    comparison. See this module's own docstring for the exact real
    `riskPerTradePct` approximation and why it is disclosed on every
    instance. Matches each real `BuyAndHoldBaseline` entry to that same
    real symbol's own real `instrumentBreakdown` bucket — a symbol
    with no matching bucket (never traded, or traded but never closed
    a trade) is honestly skipped, never compared against a fabricated
    strategy return."""
    bucket_by_symbol = {b.label: b for b in record.backtest.instrument_breakdown}
    comparisons: list[BenchmarkComparison] = []
    for baseline in record.buy_and_hold_baseline:
        bucket = bucket_by_symbol.get(baseline.symbol)
        if bucket is None or bucket.expectancy_r is None or bucket.trade_count == 0:
            continue
        strategy_total_return_r = round(bucket.expectancy_r * bucket.trade_count, 3)
        strategy_equity_return_approx_pct = round(strategy_total_return_r * risk_per_trade_pct, 3)
        excess_return_approx_pct = round(strategy_equity_return_approx_pct - baseline.return_pct, 3)
        comparisons.append(
            BenchmarkComparison(
                symbol=baseline.symbol,
                benchmarkReturnPct=baseline.return_pct,
                strategyTotalReturnR=strategy_total_return_r,
                strategyEquityReturnApproxPct=strategy_equity_return_approx_pct,
                excessReturnApproxPct=excess_return_approx_pct,
                riskPerTradePctUsed=risk_per_trade_pct,
                beatsBenchmark=excess_return_approx_pct > 0,
                approximationNote=(
                    f"Approximate — assumes every trade risked exactly {risk_per_trade_pct:.1f}% of equity (this "
                    "codebase's own configured RiskLimits.riskPerTradePct), no compounding, no concurrent-position "
                    "effects. Never a claim of a real simulated equity curve. See app/baseline_comparison.py's own "
                    "docstring for why R-multiples and % price returns are otherwise never blended."
                ),
            )
        )
    return comparisons


def _regime_failure_present(record: ResearchExperimentRecord) -> bool:
    """A real regime bucket with enough real evidence AND a real
    negative expectancy is a genuine, evidence-backed regime-dependency
    red flag — never inferred from an untested (verdict is None)
    bucket."""
    for bucket in (*record.backtest.regime_trend_breakdown, *record.backtest.regime_volatility_breakdown):
        if bucket.verdict == "enough_evidence" and bucket.expectancy_r is not None and bucket.expectancy_r < 0:
            return True
    return False


def derive_research_failure_codes(
    record: ResearchExperimentRecord,
    *,
    outlier_dependent: bool | None,
    benchmark_comparisons: list[BenchmarkComparison],
    research_relationship: str,
    research_family_experiment_count: int | None,
    tuning_version: int,
    min_trade_count: int = RESEARCH_CANDIDATE_MIN_TRADE_COUNT,
    min_profit_factor: float = RESEARCH_CANDIDATE_MIN_PROFIT_FACTOR,
    max_drawdown_pct: float = RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT,
    risk_per_trade_pct: float = 2.0,
) -> list[FailureCodeEntry]:
    """Section 7 — a real, evidence-backed research-diagnostic pass
    over the Research Desk pipeline, which (unlike
    app/strategy_lab.py's Sandbox-facing `derive_failure_codes()`) DOES
    have real walk-forward/cost-sensitivity/look-ahead/benchmark
    evidence — closing the exact gap app/failure_taxonomy.py's own
    docstring named as future work. Every code below traces to a real,
    already-computed field; never a fabricated finding. `UNKNOWN`/
    `INSUFFICIENT EVIDENCE` per Section 7's own instruction is what an
    empty return means when nothing real crossed a threshold — never
    papered over with an invented code."""
    bucket = record.backtest.overall
    codes: list[FailureCodeEntry] = []

    def _code(code: FailureCode, evidence: str) -> FailureCodeEntry:
        category, severity = FAILURE_CODE_METADATA[code]
        return FailureCodeEntry(code=code, category=category, severity=severity, evidence=evidence)

    if record.look_ahead_audit.verdict == "violations_found":
        codes.append(_code("lookahead_detected", f"{len(record.look_ahead_audit.violations)} real look-ahead violation(s) found in this definition's own setup detection."))
    if bucket.trade_count < min_trade_count:
        codes.append(_code("insufficient_sample", f"{bucket.trade_count} real closed trade(s) on file — below the real {min_trade_count}-trade research-candidate bar."))
    if bucket.trade_count < MIN_TRADES_FOR_BOOTSTRAP:
        codes.append(_code("statistical_uncertainty", f"{bucket.trade_count} real closed trade(s) — below the real {MIN_TRADES_FOR_BOOTSTRAP}-trade statistical-evidence floor."))
    if bucket.expectancy_r is not None and bucket.expectancy_r <= 0:
        codes.append(_code("negative_net_return", f"Real expectancy {bucket.expectancy_r:+.3f}R — not positive."))
    elif bucket.profit_factor is not None and bucket.profit_factor < min_profit_factor:
        codes.append(_code("low_profit_factor", f"Real profit factor {bucket.profit_factor:.2f} is below the real {min_profit_factor:.2f} research-candidate bar."))
    if bucket.max_drawdown_r is not None:
        drawdown_pct_approx = abs(bucket.max_drawdown_r) * risk_per_trade_pct
        if drawdown_pct_approx > max_drawdown_pct:
            codes.append(
                _code(
                    "excessive_drawdown",
                    f"Real max drawdown {bucket.max_drawdown_r:.2f}R (~{drawdown_pct_approx:.1f}% at {risk_per_trade_pct:.1f}% risk/trade) "
                    f"exceeds the real {max_drawdown_pct:.0f}% research-candidate bar.",
                )
            )
    if record.walk_forward.verdict == "unstable":
        codes.append(_code("walk_forward_failure", f"Real walk-forward verdict: unstable across {len(record.walk_forward.symbols)} real symbol(s)' own chronological windows."))
    if record.cost_sensitivity.verdict == "cost_sensitive":
        codes.append(_code("cost_sensitivity", "Real cost/slippage sensitivity sweep verdict: cost sensitive — the edge does not survive this codebase's own real transaction-cost constants."))
    if record.parameter_sensitivity.verdict == "fragile":
        codes.append(_code("parameter_sensitivity", "Real parameter-sensitivity sweep verdict: fragile — expectancy sign disagrees across the real swept neighborhood."))
    if outlier_dependent:
        codes.append(_code("outlier_dependent", "The single largest real winning trade accounts for more than half of this strategy's own real cumulative return."))
    if _regime_failure_present(record):
        codes.append(_code("regime_failure", "At least one real, sufficiently-evidenced regime bucket shows real negative expectancy."))
    if any(not c.beats_benchmark for c in benchmark_comparisons):
        losing = [c.symbol for c in benchmark_comparisons if not c.beats_benchmark]
        codes.append(_code("benchmark_underperformance", f"Real approximate equity return trails real buy-and-hold on: {', '.join(losing)}."))
    if research_relationship == "near_duplicate":
        codes.append(_code("duplicate_strategy", "This hypothesis/definition name real-word-overlaps an already-tested experiment or failed strategy above the real near-duplicate bar."))
    if research_family_experiment_count is not None and research_family_experiment_count >= OVERTESTED_FAMILY_THRESHOLD:
        codes.append(_code("multiple_testing_risk", f"This strategy name has already been tested {research_family_experiment_count} times in the real Quant Research Lab archive."))
    if tuning_version >= HIGH_TUNING_VERSION_THRESHOLD:
        codes.append(_code("excessive_tuning", f"This is real revision v{tuning_version} of the same strategy name."))
    return codes


# Section 15 — the real, disclosed priority order this module's own
# `classify_candidacy()` follows. Data-integrity violations that would
# make the whole result meaningless are checked first (never "mostly
# fine"); missing evidence next (never a forced call); everything else
# in descending real severity. One reasonable, disclosed convention,
# matching this codebase's own established priority-order idiom (see
# app/research_experiment.py's `_synthesize_conclusion()`).
_CRITICAL_CODES: frozenset[FailureCode] = frozenset({"lookahead_detected", "data_leakage"})
_EVIDENCE_CODES: frozenset[FailureCode] = frozenset({"insufficient_sample", "statistical_uncertainty"})
_OVERFIT_CODES: frozenset[FailureCode] = frozenset({"walk_forward_failure", "cost_sensitivity", "parameter_sensitivity", "outlier_dependent", "regime_failure"})
_PERFORMANCE_CODES: frozenset[FailureCode] = frozenset({"negative_net_return", "low_profit_factor"})
_TUNING_CODES: frozenset[FailureCode] = frozenset({"multiple_testing_risk", "excessive_tuning"})


def classify_candidacy(
    *,
    trade_count: int,
    failure_codes: list[FailureCodeEntry],
    research_relationship: str,
    benchmark_comparisons: list[BenchmarkComparison],
    min_trade_count: int = RESEARCH_CANDIDATE_MIN_TRADE_COUNT,
) -> tuple[CandidacyBinning, str]:
    """Section 15 — the one real, disclosed classification rule.
    Purely informational triage — see this module's own docstring for
    why nothing here ever gates Certification/Hall-of-Fame/Champion-
    Challenger."""
    present = {c.code for c in failure_codes}
    if present & _CRITICAL_CODES:
        return "rejected", "A real data-integrity violation (look-ahead or data leakage) was found — no other evidence is meaningful until it's fixed."
    if present & _EVIDENCE_CODES:
        return "insufficient_evidence", "Below the real minimum evidence floor for a candidacy decision — re-run with more real history."
    if research_relationship == "near_duplicate":
        return "duplicate", "This hypothesis/definition real-word-overlaps an already-tested idea above the real near-duplicate bar."
    if "excessive_drawdown" in present:
        return "risk_failed", "Real drawdown exceeds the real research-candidate risk bar."
    if present & _PERFORMANCE_CODES:
        return "rejected", "Real expectancy or profit factor fails the real research-candidate performance bar."
    if present & _OVERFIT_CODES:
        return "overfit", "Real walk-forward, cost-sensitivity, parameter-sensitivity, outlier-dependence, or regime evidence flags this as fragile/overfit."
    if any(not c.beats_benchmark for c in benchmark_comparisons):
        return "benchmark_failed", "Real approximate equity return does not beat the real buy-and-hold benchmark on at least one tested symbol."
    if present & _TUNING_CODES:
        return "fragile", "Real multiple-testing or tuning exposure is elevated — no numeric failure, but confidence in this specific pass is reduced."
    if trade_count >= min_trade_count and benchmark_comparisons and all(c.beats_benchmark for c in benchmark_comparisons) and not present:
        return "accepted", "Clears every real research-candidate requirement this module checks: sample size, drawdown, profit factor, expectancy, cost resilience, walk-forward stability, and the real benchmark comparison."
    return "promising", "Real evidence is favorable so far but has not yet cleared every real research-candidate requirement (commonly: not enough symbols with a real benchmark comparison yet, or below the full trade-count bar)."


# Section 3 — a real, disclosed, deterministic (never LLM-generated)
# mapping from a real failure code to a real, concrete next step. One
# reasonable, disclosed template per code; a strategy with multiple
# real failure codes gets a mutation proposal for its single most
# severe one (matching this module's own priority order), never a
# vague multi-parameter shotgun change (Section 3's own explicit "BAD:
# change RSI from 30 to 28... GOOD: [a specific, reasoned, targeted
# change]").
_MUTATION_TEMPLATES: dict[FailureCode, tuple[str, str, str]] = {
    "excessive_drawdown": (
        "Widen the stop or add a volatility-normalization filter before entry.",
        "The strategy's own real max drawdown exceeded the research-candidate risk bar.",
        "A wider stop or a volatility filter should reduce the size and frequency of the worst real losing streaks without eliminating the core edge.",
    ),
    "cost_sensitivity": (
        "Reduce trade frequency (tighter entry confirmation) or widen the target to improve the real reward-to-cost ratio.",
        "The strategy's real expectancy does not survive this codebase's own real transaction-cost/slippage constants.",
        "Fewer, larger-edge trades should dilute the real fixed per-trade cost drag.",
    ),
    "walk_forward_failure": (
        "Add a trend/regime confirmation filter requiring the setup to persist across more than one real bar before entry.",
        "The strategy's real edge did not hold up consistently across independent real chronological windows.",
        "A stricter confirmation requirement should filter out the specific windows where the edge was real but unstable.",
    ),
    "parameter_sensitivity": (
        "Widen the acceptable parameter range for the swept input, or replace the fragile numeric threshold with a relative (percentile-based) one.",
        "Real expectancy sign disagreed across neighboring real parameter values — the current setting is not robust.",
        "A less precisely-tuned, more relative threshold should behave consistently across nearby real parameter choices.",
    ),
    "outlier_dependent": (
        "Add a target cap or partial-profit-taking rule so no single real trade can dominate cumulative return.",
        "A single real winning trade accounted for more than half of this strategy's own real cumulative return.",
        "Capping the largest real wins should reveal whether a real, repeatable edge exists independent of that one outlier.",
    ),
    "regime_failure": (
        "Add an explicit regime filter excluding the real regime bucket that showed negative expectancy.",
        "At least one real, sufficiently-evidenced regime bucket showed real negative expectancy.",
        "Excluding that real regime should raise overall expectancy at the cost of some real trade frequency.",
    ),
    "benchmark_underperformance": (
        "Reconsider whether this symbol/timeframe genuinely has an exploitable inefficiency, or test a materially different entry mechanism.",
        "The real approximate equity return trailed the real buy-and-hold benchmark.",
        "A materially different mechanism (not a parameter tweak) is needed — beating a strong real passive return requires a real edge, not noise.",
    ),
    "low_profit_factor": (
        "Tighten the stop relative to the target, or add a confirmation filter to reduce the real loss rate.",
        "Real profit factor is below the research-candidate bar.",
        "A tighter risk/reward ratio or fewer, higher-quality entries should raise real profit factor.",
    ),
    "negative_net_return": (
        "Re-examine the core entry/exit mechanism — the real edge as specified is not present in this real (mock) data.",
        "Real expectancy is not positive across the tested window.",
        "A materially different hypothesis, not a parameter tweak, is warranted.",
    ),
}


def propose_mutation(
    failure_codes: list[FailureCodeEntry],
    *,
    parent_definition_id: str,
    parent_definition_version: int,
    parent_iteration_id: str,
    mutation_number: int,
    mutation_id: str,
    created_at: str,
) -> MutationRecord | None:
    """Section 3 — `None` (never a fabricated recommendation) when no
    real failure code this module recognizes a template for is
    present. See this module's own docstring for the real, disclosed
    boundary: this is a persisted RECOMMENDATION, never an
    auto-applied strategy rewrite."""
    if not failure_codes:
        return None
    ordered_priority: list[FailureCode] = [
        "excessive_drawdown",
        "negative_net_return",
        "low_profit_factor",
        "walk_forward_failure",
        "cost_sensitivity",
        "parameter_sensitivity",
        "outlier_dependent",
        "regime_failure",
        "benchmark_underperformance",
    ]
    present = {c.code for c in failure_codes}
    target = next((code for code in ordered_priority if code in present), None)
    if target is None or target not in _MUTATION_TEMPLATES:
        return None
    proposed_change, reason, expected_effect = _MUTATION_TEMPLATES[target]
    return MutationRecord(
        id=mutation_id,
        parentDefinitionId=parent_definition_id,
        parentDefinitionVersion=parent_definition_version,
        parentIterationId=parent_iteration_id,
        mutationNumber=mutation_number,
        observedFailureCodes=[target],
        proposedChange=proposed_change,
        reason=reason,
        expectedEffect=expected_effect,
        validationRequirements="Must clear the same real research funnel this parent went through — historical backtest, cost stress, walk-forward, regime, parameter robustness, statistical evidence, and benchmark comparison — before any candidacy decision is honored.",
        createdAt=created_at,
    )


def evaluate_research_budget(
    quant_research_experiments: list[QuantResearchExperiment],
    research_iterations: list[ResearchLoopIterationRecord],
    *,
    strategy_family: str,
    parent_definition_id: str | None,
) -> ResearchBudgetStatus:
    """Section 18 — reuses `count_experiments_for_family()` (the same
    real counter Champion/Challenger's own multiple-testing flag
    already uses) rather than a second counting mechanism."""
    experiments_attempted = count_experiments_for_family(quant_research_experiments, definition_name=strategy_family)
    mutations_for_this_parent = sum(1 for r in research_iterations if r.mutation is not None and r.mutation.parent_definition_id == parent_definition_id) if parent_definition_id else 0
    stopped = experiments_attempted >= MAX_ITERATIONS_PER_FAMILY or mutations_for_this_parent >= MAX_MUTATIONS_PER_PARENT
    stop_reason = None
    if experiments_attempted >= MAX_ITERATIONS_PER_FAMILY:
        stop_reason = f"Real experiment count for this family ({experiments_attempted}) reached the real {MAX_ITERATIONS_PER_FAMILY}-iteration budget."
    elif mutations_for_this_parent >= MAX_MUTATIONS_PER_PARENT:
        stop_reason = f"Real mutation count for this parent ({mutations_for_this_parent}) reached the real {MAX_MUTATIONS_PER_PARENT}-mutation-per-parent budget."
    return ResearchBudgetStatus(
        strategyFamily=strategy_family,
        experimentsAttempted=experiments_attempted,
        mutationsForThisParent=mutations_for_this_parent,
        maxIterationsPerFamily=MAX_ITERATIONS_PER_FAMILY,
        maxMutationsPerParent=MAX_MUTATIONS_PER_PARENT,
        stopped=stopped,
        stopReason=stop_reason,
    )


def generate_research_lesson(
    *,
    lesson_id: str,
    strategy_family: str,
    definition_id: str,
    definition_version: int,
    iteration_id: str,
    parent_definition_id: str | None,
    mutation_id: str | None,
    hypothesis: str,
    candidacy: CandidacyBinning,
    candidacy_reason: str,
    scorecard: StrategyScorecard,
    trade_count: int,
    created_at: str,
) -> ResearchLessonRecord:
    """Section 9 — a real, persisted, deterministic, templated lesson
    (never an LLM prompt saying "remember this") filed after EVERY
    completed iteration, success or failure. `confidence_pct` is a
    real, disclosed function of real sample size — never fabricated."""
    key_metrics = []
    if scorecard.expectancy_r is not None:
        key_metrics.append(f"expectancy {scorecard.expectancy_r:+.3f}R")
    if scorecard.profit_factor is not None:
        key_metrics.append(f"PF {scorecard.profit_factor:.2f}")
    if scorecard.max_drawdown_r is not None:
        key_metrics.append(f"max DD {scorecard.max_drawdown_r:.2f}R")
    if scorecard.excess_return_approx_pct is not None:
        key_metrics.append(f"excess return (approx) {scorecard.excess_return_approx_pct:+.1f}%")
    confidence_pct = round(min(100.0, trade_count / RESEARCH_CANDIDATE_MIN_TRADE_COUNT * 100.0), 1)
    lesson = f'"{strategy_family}" (v{definition_version}) — {candidacy.replace("_", " ")}: {candidacy_reason}'
    return ResearchLessonRecord(
        id=lesson_id,
        strategyFamily=strategy_family,
        definitionId=definition_id,
        definitionVersion=definition_version,
        iterationId=iteration_id,
        parentDefinitionId=parent_definition_id,
        mutationId=mutation_id,
        hypothesis=hypothesis,
        candidacy=candidacy,
        reason=candidacy_reason,
        keyMetrics=key_metrics,
        confidencePct=confidence_pct,
        lesson=lesson,
        createdAt=created_at,
    )


def run_research_loop_iteration(
    hypothesis: StrategyHypothesis,
    definition: CompiledStrategyDefinition,
    *,
    quant_research_experiments: list[QuantResearchExperiment],
    research_iterations: list[ResearchLoopIterationRecord],
    failed_archive: list[FailedStrategyArchiveEntry],
    risk_per_trade_pct: float,
    iteration_id: str,
    mutation_id: str,
    created_at: str,
    symbols: list[str] | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    candles_per_symbol: int = DEFAULT_CANDLES_PER_SYMBOL,
) -> ResearchLoopIterationRecord:
    """The one real entry point — Sections 1/4's full funnel in one
    call: HISTORICAL_BACKTEST/COST_TEST/WALK_FORWARD (all via the
    already-real `run_research_experiment()`) -> REGIME_TEST/
    ROBUSTNESS_TEST/STATISTICAL_VALIDATION (real fields already on that
    record) -> BENCHMARK_COMPARISON (new, this module) ->
    FAILURE_DIAGNOSIS (new, this module) -> candidacy decision. Never
    persists anything itself — matches this codebase's own established
    convention (pure functions in app/*.py, persistence only in
    app/state.py under its lock); never mutates `champion_history` or
    any existing gate's own state."""
    record = run_research_experiment(definition, symbols=symbols, timeframe=timeframe, candles_per_symbol=candles_per_symbol)
    bucket = record.backtest.overall

    similar_experiments = find_similar_experiments(quant_research_experiments, hypothesis=hypothesis.hypothesis, definition_id=definition.id, timeframe=timeframe)
    similar_failed = find_similar_failed_strategies(failed_archive, hypothesis=hypothesis.hypothesis, strategy_name=definition.name)
    research_relationship = classify_research_relationship(similar_experiments, similar_failed)

    benchmark_comparisons = compute_benchmark_comparisons(record, risk_per_trade_pct=risk_per_trade_pct)
    outlier_dependent, largest_win_share = compute_outlier_dependence(bucket)
    research_family_experiment_count = count_experiments_for_family(quant_research_experiments, definition_name=definition.name)

    failure_codes = derive_research_failure_codes(
        record,
        outlier_dependent=outlier_dependent,
        benchmark_comparisons=benchmark_comparisons,
        research_relationship=research_relationship,
        research_family_experiment_count=research_family_experiment_count,
        tuning_version=definition.version,
        risk_per_trade_pct=risk_per_trade_pct,
    )
    candidacy, candidacy_reason = classify_candidacy(
        trade_count=bucket.trade_count,
        failure_codes=failure_codes,
        research_relationship=research_relationship,
        benchmark_comparisons=benchmark_comparisons,
    )

    total_return_r = round(bucket.expectancy_r * bucket.trade_count, 3) if bucket.expectancy_r is not None else None
    excess_return_values = [c.excess_return_approx_pct for c in benchmark_comparisons]
    scorecard = StrategyScorecard(
        tradeCount=bucket.trade_count,
        winRatePct=bucket.win_rate_pct,
        avgWinR=bucket.avg_win_r,
        avgLossR=bucket.avg_loss_r,
        expectancyR=bucket.expectancy_r,
        profitFactor=bucket.profit_factor,
        maxDrawdownR=bucket.max_drawdown_r,
        totalReturnR=total_return_r,
        benchmarkReturnPct=(benchmark_comparisons[0].benchmark_return_pct if benchmark_comparisons else None),
        excessReturnApproxPct=(round(sum(excess_return_values) / len(excess_return_values), 3) if excess_return_values else None),
        costSensitivityVerdict=record.cost_sensitivity.verdict,
        walkForwardVerdict=record.walk_forward.verdict,
        regimeRobustnessVerdict=("weak" if _regime_failure_present(record) else "robust"),
        parameterRobustnessVerdict=record.parameter_sensitivity.verdict,
        lookAheadVerdict=record.look_ahead_audit.verdict,
        statisticalEvidenceState=("sufficient_evidence" if bucket.trade_count >= MIN_TRADES_FOR_BOOTSTRAP else "insufficient_evidence"),
        tuningExposureVersion=definition.version,
        researchFamilyExperimentCount=research_family_experiment_count,
        outlierDependent=outlier_dependent,
        largestWinShareOfReturnPct=(round(largest_win_share * 100, 1) if largest_win_share is not None else None),
    )

    # CEO directive "TradeTown — Phase 7: Autonomous Strategy Evolution
    # Engine" — fixed a real, confirmed latent inconsistency: the args
    # below already fell back to definition.id/definition.version
    # whenever hypothesis.parent_definition_id was None, but the outer
    # guard used to skip calling propose_mutation() entirely in that
    # exact case, making that fallback dead code. A hypothesis with no
    # explicit lineage (a fresh, non-mutated idea) still has a real
    # definition it is testing FROM — propose_mutation() now always
    # runs, self-referencing that same definition as its own "parent to
    # mutate from" when no earlier lineage exists. Required for
    # app/research_factory.py's generation-0 seed hypotheses to receive
    # a first real mutation proposal at all; every hypothesis that DOES
    # carry an explicit parent behaves identically to before this fix.
    mutation = propose_mutation(
        failure_codes,
        parent_definition_id=hypothesis.parent_definition_id or definition.id,
        parent_definition_version=hypothesis.parent_definition_version or definition.version,
        parent_iteration_id=iteration_id,
        mutation_number=1,
        mutation_id=mutation_id,
        created_at=created_at,
    )

    budget = evaluate_research_budget(quant_research_experiments, research_iterations, strategy_family=definition.name, parent_definition_id=hypothesis.parent_definition_id)

    return ResearchLoopIterationRecord(
        id=iteration_id,
        strategyFamily=definition.name,
        hypothesis=hypothesis,
        experiment=record,
        scorecard=scorecard,
        benchmarkComparisons=benchmark_comparisons,
        failureCodes=failure_codes,
        candidacy=candidacy,
        candidacyReason=candidacy_reason,
        similarExperiments=similar_experiments,
        similarFailedStrategies=similar_failed,
        researchRelationship=research_relationship,
        mutation=mutation,
        budget=budget,
        createdAt=created_at,
    )
