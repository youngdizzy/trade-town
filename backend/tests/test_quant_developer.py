"""Covers app/quant_developer.py — Quantitative Research & Intelligence
System, Piece 7 (Forge, the Quant Developer). This is a standing
engineering fact about the Monte Carlo bootstrap pipeline itself
(MONTE_CARLO_PATHS is a fixed global constant, not per-strategy), so
every test here checks the same real math against that one constant —
never a fabricated per-strategy read.
"""
from __future__ import annotations

from app.quant_developer import MIN_RELIABLE_TAIL_SAMPLES, assess_monte_carlo_reliability
from app.schemas import StrategyMonteCarloResult
from app.strategy_lab import MONTE_CARLO_PATHS


def _monte_carlo(*, paths_simulated: int = MONTE_CARLO_PATHS, strategy_id: str = "strategy-1") -> StrategyMonteCarloResult:
    return StrategyMonteCarloResult(
        id=f"montecarlo-{strategy_id}",
        strategyId=strategy_id,
        strategyName="Momentum Breakout",
        pathsSimulated=paths_simulated,
        tradesPerPath=25,
        sourceWinRate=55.0,
        sourceAvgWinPct=4.0,
        sourceAvgLossPct=-3.0,
        medianReturnPct=10.0,
        returnRangeLowPct=-5.0,
        returnRangeHighPct=25.0,
        medianMaxDrawdownPct=8.0,
        worstCaseDrawdownPct=20.0,
        probabilityOfProfitPct=65.0,
        probabilityOfRuinPct=5.0,
        capitalSurvivalPct=95.0,
        valueAtRisk95Pct=-10.0,
        valueAtRisk99Pct=-18.0,
        conditionalValueAtRisk95Pct=-14.0,
        conditionalValueAtRisk99Pct=-22.0,
        simDay=10,
        createdAt="2026-01-01T00:00:00+00:00",
    )


class TestAssessMonteCarloReliability:
    def test_tail_sample_counts_are_the_real_math_off_the_audited_constant(self) -> None:
        assessment = assess_monte_carlo_reliability([])
        assert assessment.paths_simulated == MONTE_CARLO_PATHS
        assert assessment.tail_sample_count_95_pct == int(MONTE_CARLO_PATHS * 0.05)
        assert assessment.tail_sample_count_99_pct == int(MONTE_CARLO_PATHS * 0.01)

    def test_with_the_real_200_path_constant_95_pct_reads_marginal_and_99_pct_unreliable(self) -> None:
        # Hand-verified against the real MONTE_CARLO_PATHS=200: 5% tail =
        # 10 samples (>= MIN_MARGINAL_TAIL_SAMPLES=10, < MIN_RELIABLE=20
        # -> "marginal"); 1% tail = 2 samples (< 10 -> "unreliable").
        assert MONTE_CARLO_PATHS == 200
        assessment = assess_monte_carlo_reliability([])
        assert assessment.tail_sample_count_95_pct == 10
        assert assessment.tail_sample_count_99_pct == 2
        assert assessment.verdict_95_pct == "marginal"
        assert assessment.verdict_99_pct == "unreliable"

    def test_recommended_path_count_is_real_math_not_a_fabricated_number(self) -> None:
        assessment = assess_monte_carlo_reliability([])
        assert assessment.recommended_paths_for_reliable_99_pct == int(MIN_RELIABLE_TAIL_SAMPLES / 0.01)
        assert assessment.recommended_paths_for_reliable_99_pct == 2000

    def test_real_results_audited_reflects_the_actual_list_length(self) -> None:
        results = [_monte_carlo(strategy_id="strategy-1"), _monte_carlo(strategy_id="strategy-2")]
        assessment = assess_monte_carlo_reliability(results)
        assert assessment.real_results_audited == 2

    def test_consistent_path_counts_across_every_real_result_is_flagged_true(self) -> None:
        results = [_monte_carlo(paths_simulated=MONTE_CARLO_PATHS), _monte_carlo(paths_simulated=MONTE_CARLO_PATHS, strategy_id="strategy-2")]
        assessment = assess_monte_carlo_reliability(results)
        assert assessment.observed_path_counts_consistent is True

    def test_a_real_drift_in_path_count_is_flagged_honestly_not_hidden(self) -> None:
        # A real StrategyMonteCarloResult on file that used a different
        # path count than the currently audited constant — this must be
        # caught, not silently assumed consistent.
        results = [_monte_carlo(paths_simulated=MONTE_CARLO_PATHS), _monte_carlo(paths_simulated=500, strategy_id="strategy-2")]
        assessment = assess_monte_carlo_reliability(results)
        assert assessment.observed_path_counts_consistent is False
        assert "inconsistency" in assessment.reasoning

    def test_no_real_results_on_file_is_still_a_real_zero_not_a_crash(self) -> None:
        assessment = assess_monte_carlo_reliability([])
        assert assessment.real_results_audited == 0
        assert assessment.observed_path_counts_consistent is True

    def test_threshold_source_discloses_this_is_a_new_assumption_not_an_existing_constant(self) -> None:
        assessment = assess_monte_carlo_reliability([])
        assert "disclosed" in assessment.threshold_source
        assert str(MIN_RELIABLE_TAIL_SAMPLES) in assessment.threshold_source

    def test_developer_agent_id_is_forge(self) -> None:
        assessment = assess_monte_carlo_reliability([])
        assert assessment.developer_agent_id == "forge"
