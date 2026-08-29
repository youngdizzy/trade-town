"""Covers app/statistical_comparison.py — CEO directive "TradeTown —
Statistical Validation + Research Failure Taxonomy," Part 1. Every
number here is either a real, hand-computable statistic over a
synthetic sample (the pure bootstrap primitive) or comes from a real
compiled-strategy backtest (the integration path) — never a fabricated
confidence interval.
"""
from __future__ import annotations

from app.statistical_comparison import (
    BOOTSTRAP_METHOD,
    MIN_TRADES_FOR_BOOTSTRAP,
    bootstrap_compare_samples,
    run_statistical_comparison,
)
from app.strategy_compiler import compile_strategy_text


class TestBootstrapCompareSamples:
    def test_below_the_real_minimum_sample_on_champion_side_reads_insufficient_evidence(self) -> None:
        champion = [0.5] * (MIN_TRADES_FOR_BOOTSTRAP - 1)
        challenger = [0.5] * MIN_TRADES_FOR_BOOTSTRAP
        result = bootstrap_compare_samples(champion, challenger, seed_parts=("a",))
        assert result.evidence_state == "insufficient_evidence"
        assert result.difference_ci_low is None
        assert result.difference_ci_high is None
        assert result.probability_challenger_better_pct is None
        assert result.champion_sample_size == MIN_TRADES_FOR_BOOTSTRAP - 1

    def test_below_the_real_minimum_sample_on_challenger_side_reads_insufficient_evidence(self) -> None:
        champion = [0.5] * MIN_TRADES_FOR_BOOTSTRAP
        challenger = [0.5] * (MIN_TRADES_FOR_BOOTSTRAP - 1)
        result = bootstrap_compare_samples(champion, challenger, seed_parts=("a",))
        assert result.evidence_state == "insufficient_evidence"

    def test_at_exactly_the_real_minimum_sample_reads_sufficient_evidence(self) -> None:
        champion = [0.5] * MIN_TRADES_FOR_BOOTSTRAP
        challenger = [0.5] * MIN_TRADES_FOR_BOOTSTRAP
        result = bootstrap_compare_samples(champion, challenger, seed_parts=("a",))
        assert result.evidence_state == "sufficient_evidence"

    def test_identical_samples_produce_a_real_zero_point_estimate(self) -> None:
        sample = [1.0, -0.5, 0.8, -1.2, 0.3] * 5
        result = bootstrap_compare_samples(sample, sample, seed_parts=("identical",))
        assert result.mean_difference_estimate == 0.0
        assert result.champion_mean_r == result.challenger_mean_r

    def test_a_clearly_superior_challenger_sample_reads_a_positive_ci_excluding_zero(self) -> None:
        champion = [-1.0, -0.5, 0.2, -0.8, -0.3] * 6
        challenger = [2.0, 1.5, 2.2, 1.8, 2.5] * 6
        result = bootstrap_compare_samples(champion, challenger, seed_parts=("superior",))
        assert result.evidence_state == "sufficient_evidence"
        assert result.difference_ci_low is not None
        assert result.difference_ci_low > 0
        assert result.probability_challenger_better_pct == 100.0

    def test_a_clearly_inferior_challenger_sample_reads_a_negative_ci_excluding_zero(self) -> None:
        champion = [2.0, 1.5, 2.2, 1.8, 2.5] * 6
        challenger = [-1.0, -0.5, 0.2, -0.8, -0.3] * 6
        result = bootstrap_compare_samples(champion, challenger, seed_parts=("inferior",))
        assert result.difference_ci_high is not None
        assert result.difference_ci_high < 0
        assert result.probability_challenger_better_pct == 0.0

    def test_a_statistically_uncertain_challenger_produces_a_ci_spanning_zero(self) -> None:
        champion = [1.0, -0.9, 1.1, -1.0, 0.95, -1.05, 1.0, -0.95] * 3
        challenger = [1.05, -0.95, 1.0, -1.0, 1.1, -1.0, 0.9, -1.05] * 3
        result = bootstrap_compare_samples(champion, challenger, seed_parts=("uncertain",))
        assert result.difference_ci_low is not None and result.difference_ci_high is not None
        assert result.difference_ci_low <= 0 <= result.difference_ci_high

    def test_the_same_inputs_and_seed_parts_produce_the_exact_same_deterministic_result(self) -> None:
        champion = [0.5, -0.3, 1.1, -0.8, 0.2] * 5
        challenger = [0.9, -0.1, 1.4, -0.5, 0.6] * 5
        first = bootstrap_compare_samples(champion, challenger, seed_parts=("repro", "1"))
        second = bootstrap_compare_samples(champion, challenger, seed_parts=("repro", "1"))
        assert first == second

    def test_different_seed_parts_are_free_to_produce_a_different_real_resample_path(self) -> None:
        champion = [0.5, -0.3, 1.1, -0.8, 0.2] * 5
        challenger = [0.9, -0.1, 1.4, -0.5, 0.6] * 5
        first = bootstrap_compare_samples(champion, challenger, seed_parts=("a",))
        second = bootstrap_compare_samples(champion, challenger, seed_parts=("b",))
        # The real point estimates are identical (same real data); only the
        # bootstrap-derived CI bounds may legitimately differ by seed.
        assert first.mean_difference_estimate == second.mean_difference_estimate

    def test_the_real_method_and_confidence_level_are_always_disclosed(self) -> None:
        champion = [0.5] * MIN_TRADES_FOR_BOOTSTRAP
        challenger = [0.5] * MIN_TRADES_FOR_BOOTSTRAP
        result = bootstrap_compare_samples(champion, challenger, seed_parts=("a",))
        assert result.method == BOOTSTRAP_METHOD
        assert result.confidence_level_pct == 95.0
        assert "IID" in result.limitation_note or "independent" in result.limitation_note.lower()

    def test_an_all_winning_sample_against_an_all_losing_sample(self) -> None:
        champion = [-1.0] * MIN_TRADES_FOR_BOOTSTRAP
        challenger = [2.0] * MIN_TRADES_FOR_BOOTSTRAP
        result = bootstrap_compare_samples(champion, challenger, seed_parts=("a",))
        assert result.champion_mean_r == -1.0
        assert result.challenger_mean_r == 2.0
        assert result.mean_difference_estimate == 3.0

    def test_zero_trades_on_both_sides_reads_insufficient_evidence_not_a_crash(self) -> None:
        result = bootstrap_compare_samples([], [], seed_parts=("empty",))
        assert result.evidence_state == "insufficient_evidence"
        assert result.champion_sample_size == 0
        assert result.challenger_sample_size == 0


class TestRunStatisticalComparison:
    def test_two_real_compiled_definitions_over_real_candle_data_produce_a_real_result(self) -> None:
        champion_definition = compile_strategy_text(
            name="Stat Champion",
            source_text="Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R.",
        )
        challenger_definition = compile_strategy_text(
            name="Stat Challenger",
            source_text="Buy when price closes above the 50 EMA and RSI is above 70, then enter when price closes above the previous swing high. Place a 2% stop and 4% target.",
        )
        result = run_statistical_comparison(champion_definition, challenger_definition, symbols=["AAPL", "QQQ", "SPY"])
        assert result.champion_sample_size >= 0
        assert result.challenger_sample_size >= 0
        assert result.method == BOOTSTRAP_METHOD

    def test_an_uncompilable_definition_produces_zero_real_trades_never_a_crash(self) -> None:
        champion_definition = compile_strategy_text(name="Stat Champion 2", source_text="Buy when the moon is full.")
        challenger_definition = compile_strategy_text(name="Stat Challenger 2", source_text="Buy when the moon is full.")
        result = run_statistical_comparison(champion_definition, challenger_definition, symbols=["AAPL"])
        assert result.champion_sample_size == 0
        assert result.evidence_state == "insufficient_evidence"

    def test_reproducible_across_two_real_runs_of_the_exact_same_two_definitions(self) -> None:
        champion_definition = compile_strategy_text(
            name="Stat Champion 3",
            source_text="Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R.",
        )
        challenger_definition = compile_strategy_text(
            name="Stat Challenger 3",
            source_text="Buy when price closes above the 50 EMA and RSI is above 70, then enter when price closes above the previous swing high. Place a 2% stop and 4% target.",
        )
        first = run_statistical_comparison(champion_definition, challenger_definition, symbols=["AAPL", "QQQ", "SPY", "MSFT", "NVDA", "TSLA"])
        second = run_statistical_comparison(champion_definition, challenger_definition, symbols=["AAPL", "QQQ", "SPY", "MSFT", "NVDA", "TSLA"])
        assert first == second
