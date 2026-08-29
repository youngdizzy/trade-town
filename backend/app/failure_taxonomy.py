"""app/failure_taxonomy.py — CEO directive "TradeTown — Statistical
Validation + Research Failure Taxonomy," Part 2 (Failure Taxonomy):
"Replace free-text-only rejection reasons with a structured taxonomy
while preserving the existing human-readable explanation."

RESEARCH FIRST. `app/strategy_lab.py::generate_strategy_retirement_
outcome()` already builds a real `FailedStrategyArchiveEntry` for every
real strategy retirement that doesn't clear the Hall of Fame bar, from
real, already-computed evidence: `trade_count`/`win_rate`/
`profit_factor`/`avg_drawdown` (aggregated from that strategy's own
real `SimulationResult`s) and, when available, an independent
`ModelValidationReport` verdict. This module adds NO new evidence
source — `derive_failure_codes()` below reads the EXACT same real
numbers `generate_strategy_retirement_outcome()` already computes and
tags each one that crossed a real, already-used threshold
(`HALL_OF_FAME_MIN_TRADE_COUNT`/`HALL_OF_FAME_MIN_PROFIT_FACTOR`/
`HALL_OF_FAME_MAX_AVG_DRAWDOWN`/`HALL_OF_FAME_MIN_WIN_RATE`) with a
real, structured `FailureCodeEntry` — a second, coded label for a real
condition already being checked, never a new check. Those four
threshold constants stay owned and defined exactly once, in
`app/strategy_lab.py`; `derive_failure_codes()` takes them as real
parameters from that caller rather than re-importing them here, since
`app/strategy_lab.py` is the one that will call into this module (a
straight import the other way would be circular).

AN HONEST, DISCLOSED SUBSET OF THE DIRECTIVE'S OWN 35-CODE TAXONOMY.
`FailureCode` (app/schemas.py) defines the directive's own full,
requested vocabulary verbatim — real, valid vocabulary, useful even
before every code has a real derivation path wired to it. Today, a
`Strategy`'s own retirement decision only has real evidence for SIX of
those 35 codes (see `derive_failure_codes()` below) — this codebase has
no real walk-forward/cost-sensitivity/look-ahead-audit/benchmark
evidence wired into the SANDBOX strategy-retirement pipeline at all
(that evidence lives on the SEPARATE, parallel `ResearchExperimentRecord`/
`CompiledStrategyDefinition` pipeline — see `app/research_experiment.py`,
`app/champion_challenger.py` — a `Strategy` and a `CompiledStrategyDefinition`
are only optionally linked via `Strategy.compiled_definition_id`, and
`generate_strategy_retirement_outcome()` itself never reads that other
pipeline's results). Assigning e.g. `walk_forward_failure` or
`cost_sensitivity` here without that real evidence would be exactly the
kind of fabricated finding this whole codebase's own discipline
forbids. Wiring the two pipelines' evidence together so retirement can
honestly assign the rest of the taxonomy is real, tractable, disclosed
future work — not attempted in this pass.

SEVERITY IS A REAL, DISCLOSED, STATIC RATIONALE — NEVER COMPUTED PER
INSTANCE. `FAILURE_CODE_METADATA` below assigns one fixed
(category, severity) pair to every one of the directive's own 35 codes,
matching its own two explicit worked examples
(`insufficient_sample = HIGH`) exactly, and follows one consistent,
disclosed rule for the rest: a real data-integrity violation that would
make an ENTIRE result meaningless is `critical`
(`lookahead_detected`/`data_leakage`/`unacceptable_risk_of_ruin`); a
real sample-size/risk/robustness gap that undermines confidence in
otherwise-real evidence is `high`; a real but survivable performance/
execution shortfall is `medium`; a cosmetic/informational finding is
`low`. One reasonable, disclosed convention — not derived from any
formal risk-scoring study, and not the only valid one.
"""
from __future__ import annotations

from app.schemas import FailedStrategyArchiveEntry, FailureCategory, FailureCode, FailureCodeEntry, FailureModeCount, FailureSeverity, ModelValidationReport

# See this module's own docstring for the real, disclosed severity
# rationale. Every one of the directive's own 35 requested codes is
# covered here — most are real, valid vocabulary awaiting a future real
# evidence source, not yet assigned by derive_failure_codes() below.
FAILURE_CODE_METADATA: dict[FailureCode, tuple[FailureCategory, FailureSeverity]] = {
    # DATA_FAILURE
    "insufficient_data": ("data_failure", "high"),
    "missing_data": ("data_failure", "high"),
    "stale_data": ("data_failure", "medium"),
    "survivorship_risk": ("data_failure", "medium"),
    "lookahead_detected": ("data_failure", "critical"),
    "data_leakage": ("data_failure", "critical"),
    # STATISTICAL_FAILURE
    "insufficient_sample": ("statistical_failure", "high"),
    "weak_expectancy": ("statistical_failure", "medium"),
    "unstable_distribution": ("statistical_failure", "medium"),
    "statistical_uncertainty": ("statistical_failure", "medium"),
    "multiple_testing_risk": ("statistical_failure", "medium"),
    "selection_bias": ("statistical_failure", "high"),
    # RISK_FAILURE
    "excessive_drawdown": ("risk_failure", "high"),
    "unacceptable_risk_of_ruin": ("risk_failure", "critical"),
    "excessive_volatility": ("risk_failure", "medium"),
    "concentration_risk": ("risk_failure", "medium"),
    "poor_recovery": ("risk_failure", "low"),
    # PERFORMANCE_FAILURE
    "negative_net_return": ("performance_failure", "high"),
    "low_profit_factor": ("performance_failure", "medium"),
    "negative_expectancy": ("performance_failure", "high"),
    "benchmark_underperformance": ("performance_failure", "medium"),
    "inconsistent_returns": ("performance_failure", "medium"),
    # ROBUSTNESS_FAILURE
    "walk_forward_failure": ("robustness_failure", "high"),
    "out_of_sample_failure": ("robustness_failure", "high"),
    "regime_failure": ("robustness_failure", "medium"),
    "parameter_sensitivity": ("robustness_failure", "medium"),
    "cost_sensitivity": ("robustness_failure", "high"),
    "slippage_sensitivity": ("robustness_failure", "medium"),
    "fragile_edge": ("robustness_failure", "medium"),
    # EXECUTION_FAILURE
    "excessive_turnover": ("execution_failure", "low"),
    "unrealistic_fill_assumption": ("execution_failure", "medium"),
    "excessive_slippage": ("execution_failure", "medium"),
    "poor_liquidity": ("execution_failure", "medium"),
    "adverse_selection": ("execution_failure", "medium"),
    # RESEARCH_FAILURE
    "hypothesis_invalidated": ("research_failure", "medium"),
    "overfit": ("research_failure", "high"),
    "excessive_tuning": ("research_failure", "medium"),
    "duplicate_strategy": ("research_failure", "low"),
    "redundant_strategy": ("research_failure", "low"),
    "failed_challenger": ("research_failure", "low"),
    "champion_not_beaten": ("research_failure", "low"),
}


def _failure_code(code: FailureCode, evidence: str) -> FailureCodeEntry:
    category, severity = FAILURE_CODE_METADATA[code]
    return FailureCodeEntry(code=code, category=category, severity=severity, evidence=evidence)


def derive_failure_codes(
    *,
    trade_count: int,
    win_rate: float,
    profit_factor: float,
    avg_drawdown: float,
    avg_return: float,
    min_trade_count: int,
    min_profit_factor: float,
    max_avg_drawdown: float,
    min_win_rate: float,
    latest_model_validation: ModelValidationReport | None = None,
) -> list[FailureCodeEntry]:
    """The one real, structural derivation — every numeric argument is a
    real number `app/strategy_lab.py::generate_strategy_retirement_
    outcome()` already computes for this exact same strategy before
    calling this function (the four `min_*`/`max_*` thresholds are that
    same caller's own real `HALL_OF_FAME_MIN_TRADE_COUNT`/
    `HALL_OF_FAME_MIN_PROFIT_FACTOR`/`HALL_OF_FAME_MAX_AVG_DRAWDOWN`/
    `HALL_OF_FAME_MIN_WIN_RATE` constants, passed in rather than
    re-imported here to avoid a real circular import between this
    module and that one). Nothing here is recomputed independently, and
    nothing here can disagree with the free-text `whatFailed` that same
    caller already builds from the same real evidence. See this
    module's own docstring for exactly which 6 of the directive's 35
    codes this function can honestly assign today, and why the rest are
    real vocabulary without a wired evidence source yet."""
    codes: list[FailureCodeEntry] = []

    if trade_count < min_trade_count:
        codes.append(_failure_code("insufficient_sample", f"{trade_count} real trade(s) on file — below the real {min_trade_count}-trade Hall of Fame bar."))

    if avg_return <= 0:
        codes.append(_failure_code("negative_net_return", f"Real average return across this strategy's own runs was {avg_return:.2f}% — not positive."))
    elif profit_factor < min_profit_factor:
        codes.append(_failure_code("low_profit_factor", f"Real average profit factor {profit_factor:.2f} is below the real {min_profit_factor:.2f} Hall of Fame bar."))

    if avg_drawdown > max_avg_drawdown:
        codes.append(_failure_code("excessive_drawdown", f"Real average max drawdown {avg_drawdown:.1f}% exceeds the real {max_avg_drawdown:.1f}% bar."))

    if avg_return > 0 and win_rate < min_win_rate:
        codes.append(_failure_code("inconsistent_returns", f"Real average win rate {win_rate:.1f}% is below the real {min_win_rate:.1f}% Hall of Fame bar."))

    if latest_model_validation is not None and latest_model_validation.verdict != "approved":
        codes.append(
            _failure_code(
                "statistical_uncertainty",
                f"Independent Model Validation (Meridian/CIO) verdict was '{latest_model_validation.verdict.replace('_', ' ')}', not approved.",
            )
        )

    return codes


def compute_top_failure_modes(failed_archive: list[FailedStrategyArchiveEntry], *, max_examples_per_mode: int = 3) -> list[FailureModeCount]:
    """CEO directive "TradeTown — Statistical Validation + Research
    Failure Taxonomy," Part 2 (Failure Clustering) — a real, computed-
    fresh aggregation over every real `failureCodes` entry across the
    whole permanent Failed Archive. Entries filed before `failureCodes`
    existed contribute nothing (an honestly empty list, never a
    fabricated code) — never inflates or deflates a real count. Sorted
    by real occurrence count, most common first; a code with zero real
    occurrences is simply absent, never listed with a fabricated 0."""
    counts: dict[FailureCode, int] = {}
    examples: dict[FailureCode, list[str]] = {}
    for entry in failed_archive:
        seen_this_entry: set[FailureCode] = set()
        for failure_code in entry.failure_codes:
            if failure_code.code in seen_this_entry:
                continue  # one real strategy counts once per code, even if somehow tagged twice
            seen_this_entry.add(failure_code.code)
            counts[failure_code.code] = counts.get(failure_code.code, 0) + 1
            names = examples.setdefault(failure_code.code, [])
            if entry.strategy_name not in names and len(names) < max_examples_per_mode:
                names.append(entry.strategy_name)

    modes = [
        FailureModeCount(
            code=code,
            category=FAILURE_CODE_METADATA[code][0],
            severity=FAILURE_CODE_METADATA[code][1],
            occurrenceCount=count,
            exampleStrategyNames=examples.get(code, []),
        )
        for code, count in counts.items()
    ]
    modes.sort(key=lambda m: m.occurrence_count, reverse=True)
    return modes
