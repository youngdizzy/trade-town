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

AN HONEST, DISCLOSED SUBSET OF THE DIRECTIVE'S OWN 35-CODE TAXONOMY
(NOW 38 — CEO directive "TradeTown — Research Engine Hardening +
Self-Improvement Implementation Pass," Phase 2 added two real,
evidence-backed LIFECYCLE_FAILURE codes: `never_reached_required_stage`/
`founder_approval_rejected`, closing the confirmed gap where a strategy
clearing every numeric bar could still retire with `failureCodes: []`;
CEO directive "TradeTown — Next Major Implementation Pass, Phase 4-6"
added one real STATISTICAL_FAILURE code, `outlier_dependent`, derived
by the NEW `app/research_loop.py` module — see that module's own
docstring for why the Research Desk pipeline, not this function, is
the honest home for that derivation). `FailureCode` (app/schemas.py)
defines the directive's own full, requested vocabulary verbatim — real,
valid vocabulary, useful even before every code has a real derivation
path wired to it. Today, a `Strategy`'s own retirement decision only
has real evidence for EIGHT of those 38 codes (see `derive_failure_codes()`
below) — this codebase has
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

from app.quant_research_lab import HYPOTHESIS_OVERLAP_THRESHOLD, word_overlap_score
from app.schemas import (
    FailedStrategyArchiveEntry,
    FailureCategory,
    FailureCode,
    FailureCodeEntry,
    FailureModeCount,
    FailureSeverity,
    ModelValidationReport,
    SimilarFailedStrategyMatch,
    StrategyFounderApproval,
    StrategyStage,
)

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
    # CEO directive "TradeTown — Research Engine Hardening +
    # Self-Improvement Implementation Pass," Phase 2 — real evidence
    # exists for both (the strategy's own real `stage`/real
    # `StrategyFounderApproval` verdict), but neither reflects a
    # numeric backtest weakness, so `medium` (a real, survivable,
    # process-level shortfall) rather than `high`/`critical`.
    "never_reached_required_stage": ("research_failure", "medium"),
    "founder_approval_rejected": ("research_failure", "medium"),
    # CEO directive "TradeTown — Next Major Implementation Pass, Phase
    # 4-6" — real evidence exists (largestWinR vs. cumulative
    # expectancy), and an outlier-dependent edge undermines confidence
    # in an otherwise-real result without invalidating it outright, so
    # `high` — same rationale as `selection_bias`/`insufficient_sample`.
    "outlier_dependent": ("statistical_failure", "high"),
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
    strategy_stage: StrategyStage | None = None,
    latest_founder_approval: StrategyFounderApproval | None = None,
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
    caller already builds from the same real evidence. `strategy_stage`/
    `latest_founder_approval` are two more real, optional inputs (CEO
    directive "TradeTown — Research Engine Hardening + Self-Improvement
    Implementation Pass," Phase 2) closing a real, confirmed gap: the
    four numeric bars above can all pass while `qualifies_for_hall_of_fame`
    still fails on stage/Founder-Approval, previously producing an
    empty `failureCodes` list. See this module's own docstring for
    exactly which 8 of the directive's 37 codes this function can
    honestly assign today, and why the rest are real vocabulary without
    a wired evidence source yet."""
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

    # CEO directive "TradeTown — Research Engine Hardening +
    # Self-Improvement Implementation Pass," Phase 2 — closes the real,
    # confirmed gap the prior forensic audit proved reachable: a
    # strategy could clear every one of the four numeric bars above and
    # still retire into the Failed Archive with zero failure codes,
    # because `qualifies_for_hall_of_fame` (app/strategy_lab.py) also
    # requires `stage == "approved"` AND a real, approved Founder
    # Approval — two real, independent conditions this function never
    # read before. Both real inputs, both optional (default `None`) so
    # any caller that hasn't been threaded through them yet keeps
    # working — never a forced or fabricated code.
    if strategy_stage is not None and strategy_stage != "approved":
        codes.append(
            _failure_code(
                "never_reached_required_stage",
                f"Retired at real pipeline stage '{strategy_stage.replace('_', ' ')}' — never reached the real 'approved' stage Hall of Fame induction requires.",
            )
        )
    if latest_founder_approval is not None and latest_founder_approval.verdict != "approved":
        codes.append(
            _failure_code(
                "founder_approval_rejected",
                f"Real Founder Council verdict was '{latest_founder_approval.verdict}' — {latest_founder_approval.verdict_reason}",
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


# CEO directive "TradeTown — Research Engine Hardening +
# Self-Improvement Implementation Pass," Phase 3 — a real, disclosed
# "how similar is similar" bar, matching
# app/quant_research_lab.py::HYPOTHESIS_OVERLAP_THRESHOLD's own real
# convention rather than inventing a second number for the same
# underlying question.
FAILED_STRATEGY_OVERLAP_THRESHOLD = HYPOTHESIS_OVERLAP_THRESHOLD


def find_similar_failed_strategies(
    failed_archive: list[FailedStrategyArchiveEntry], *, hypothesis: str, strategy_name: str, max_matches: int = 5
) -> list[SimilarFailedStrategyMatch]:
    """CEO directive "TradeTown — Research Engine Hardening +
    Self-Improvement Implementation Pass," Phase 3 — "before a new
    research hypothesis is allowed into expensive evaluation... search
    failed strategies." The one real entry point for that search:
    checked BEFORE filing a new Quant Research Lab experiment (see
    app/state.py::submit_quant_research_experiment()), against the
    PERMANENT Failed Strategy Archive — never the separate, already-
    covered `quant_research_experiments` list
    (find_similar_experiments() already handles that).

    Matches on real word-overlap between `hypothesis + strategy_name`
    (the new proposal) and each archived entry's own real `strategy_
    name` + `what_failed` text (the closest real, honest proxy this
    archive has for a "why this one failed" description — it has no
    separate hypothesis field of its own). Returns every real match
    found, most recent first, capped at `max_matches` — an empty list
    is itself a real, honest result (no similar past failure on file),
    never fabricated as "clear." NEVER used to auto-reject the new
    proposal — see `classify_research_relationship()` in
    app/quant_research_lab.py for how this is surfaced as evidence,
    not a blocker."""
    proposal_text = f"{strategy_name} {hypothesis}"
    matches: list[SimilarFailedStrategyMatch] = []
    for entry in reversed(failed_archive):
        archive_text = f"{entry.strategy_name} {' '.join(entry.what_failed)}"
        overlap = word_overlap_score(proposal_text, archive_text)
        if overlap >= FAILED_STRATEGY_OVERLAP_THRESHOLD:
            matches.append(
                SimilarFailedStrategyMatch(
                    strategyArchiveId=entry.id,
                    strategyName=entry.strategy_name,
                    overlapScore=overlap,
                    reason=f"Strategy name/failure wording overlaps {overlap * 100:.0f}% (word-level, not semantic) with retired strategy {entry.strategy_name!r}.",
                    failedAtStage=entry.failed_at_stage,
                    failureCodes=[f.code for f in entry.failure_codes],
                    evidence=list(entry.what_failed),
                    simDay=entry.sim_day,
                )
            )
            if len(matches) >= max_matches:
                break
    return matches
