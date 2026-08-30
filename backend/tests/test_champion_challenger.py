"""Covers app/champion_challenger.py — CEO directive "TradeTown —
11/10 Self-Improving Quant Agent System," Section 1 (Champion vs
Challenger). `_decide_verdict()` is tested directly against hand-picked
numbers (including the directive's own two worked examples, translated
verbatim to this codebase's real R-multiple units) so the promotion
rule's exact real behavior is provable without depending on the mock
market data's own procedurally-generated numbers; `compare_champion_
challenger()`/`get_current_champion()`/`promote_challenger()` are
covered by real, reproducible end-to-end integration tests.
"""
from __future__ import annotations

import asyncio

from app.champion_challenger import (
    HIGH_TUNING_VERSION_THRESHOLD,
    MAX_DRAWDOWN_REGRESSION_PCT,
    MAX_EXPECTANCY_REGRESSION_PCT,
    MAX_PROFIT_FACTOR_REGRESSION_PCT,
    MIN_DRAWDOWN_IMPROVEMENT_PCT,
    MIN_EXPECTANCY_IMPROVEMENT_PCT,
    _classify_statistical_economic_evidence,
    _decide_verdict,
    compare_champion_challenger,
    get_current_champion,
    promote_challenger,
)
from app.quant_research_lab import OVERTESTED_FAMILY_THRESHOLD, file_quant_research_experiment
from app.research_experiment import run_research_experiment
from app.schemas import BootstrapComparisonResult, ChampionRecord
from app.state import GameState
from app.strategy_compiler import compile_strategy_text

_CHAMPION_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
_CHALLENGER_TEXT = "Buy when price closes above the 50 EMA and RSI is above 70, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
_INVALID_TEXT = "Buy when the moon is full."


def _sufficient_kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = dict(
        champion_evidence_sufficient=True,
        challenger_evidence_sufficient=True,
        challenger_conclusion_credible=True,
        champion_expectancy_r=0.20,
        challenger_expectancy_r=0.20,
        champion_max_drawdown_r=-0.10,
        challenger_max_drawdown_r=-0.10,
    )
    base.update(overrides)
    return base


class TestDecideVerdict:
    def test_insufficient_evidence_when_champion_below_the_real_sample_floor(self) -> None:
        verdict, reasoning = _decide_verdict(**_sufficient_kwargs(champion_evidence_sufficient=False))
        assert verdict == "insufficient_evidence"
        assert "evidence floor" in reasoning

    def test_insufficient_evidence_when_challenger_below_the_real_sample_floor(self) -> None:
        verdict, reasoning = _decide_verdict(**_sufficient_kwargs(challenger_evidence_sufficient=False))
        assert verdict == "insufficient_evidence"

    def test_a_non_credible_challenger_conclusion_retains_the_champion_regardless_of_numbers(self) -> None:
        # Even with a huge real expectancy improvement, an uncredible research conclusion blocks promotion.
        verdict, reasoning = _decide_verdict(**_sufficient_kwargs(challenger_conclusion_credible=False, challenger_expectancy_r=1.0))
        assert verdict == "champion_retained"
        assert "not credible" in reasoning

    def test_the_directives_own_first_worked_example_is_correctly_blocked(self) -> None:
        # A real expectancy improvement clears the bar, but a real, large drawdown
        # regression (10% -> 19%, +90% relative) blocks promotion via Path A.
        verdict, reasoning = _decide_verdict(
            **_sufficient_kwargs(champion_expectancy_r=0.20, challenger_expectancy_r=0.30, champion_max_drawdown_r=-0.10, challenger_max_drawdown_r=-0.19)
        )
        assert verdict == "champion_retained"

    def test_the_directives_own_second_worked_example_is_correctly_promoted(self) -> None:
        # Champion 28% / challenger 27% expectancy (a small, tolerated real regression);
        # champion 15% / challenger 8% max drawdown (a real, meaningful improvement) -- Path B.
        verdict, reasoning = _decide_verdict(
            **_sufficient_kwargs(champion_expectancy_r=0.28, challenger_expectancy_r=0.27, champion_max_drawdown_r=-0.15, challenger_max_drawdown_r=-0.08)
        )
        assert verdict == "challenger_recommended"
        assert "risk-adjusted" in reasoning

    def test_path_a_promotes_on_a_real_expectancy_gain_with_no_drawdown_regression(self) -> None:
        verdict, _ = _decide_verdict(**_sufficient_kwargs(champion_expectancy_r=0.20, challenger_expectancy_r=0.30, champion_max_drawdown_r=-0.10, challenger_max_drawdown_r=-0.10))
        assert verdict == "challenger_recommended"

    def test_neither_path_clears_its_bar_retains_the_champion(self) -> None:
        # A tiny, real improvement in both dimensions -- below both real thresholds.
        verdict, _ = _decide_verdict(**_sufficient_kwargs(champion_expectancy_r=0.20, challenger_expectancy_r=0.21, champion_max_drawdown_r=-0.10, challenger_max_drawdown_r=-0.099))
        assert verdict == "champion_retained"

    def test_a_champion_with_non_positive_expectancy_sets_no_proportional_bar(self) -> None:
        verdict, _ = _decide_verdict(**_sufficient_kwargs(champion_expectancy_r=-0.05, challenger_expectancy_r=0.01, champion_max_drawdown_r=-0.10, challenger_max_drawdown_r=-0.10))
        assert verdict == "challenger_recommended"

    def test_a_champion_with_non_positive_expectancy_and_a_still_non_positive_challenger_is_not_promoted(self) -> None:
        verdict, _ = _decide_verdict(**_sufficient_kwargs(champion_expectancy_r=-0.05, challenger_expectancy_r=-0.01, champion_max_drawdown_r=-0.10, challenger_max_drawdown_r=-0.10))
        assert verdict == "champion_retained"

    def test_missing_real_metrics_on_either_side_reads_insufficient_evidence(self) -> None:
        verdict, _ = _decide_verdict(**_sufficient_kwargs(challenger_expectancy_r=None))
        assert verdict == "insufficient_evidence"

    def test_thresholds_are_the_real_disclosed_constants_this_module_exports(self) -> None:
        assert MIN_EXPECTANCY_IMPROVEMENT_PCT == 10.0
        assert MAX_DRAWDOWN_REGRESSION_PCT == 15.0
        assert MIN_DRAWDOWN_IMPROVEMENT_PCT == 20.0
        assert MAX_EXPECTANCY_REGRESSION_PCT == 10.0
        assert MAX_PROFIT_FACTOR_REGRESSION_PCT == 20.0

    def test_the_directives_own_two_worked_examples_are_unaffected_by_the_new_profit_factor_gate(self) -> None:
        """Neither worked example test above passes profit_factor at
        all — confirming the new, optional non-regression check is
        skipped (never a forced call) when that evidence is absent,
        exactly like every other missing-evidence case this function
        already handles."""
        blocked, _ = _decide_verdict(**_sufficient_kwargs(champion_expectancy_r=0.28, challenger_expectancy_r=0.30, champion_max_drawdown_r=-0.10, challenger_max_drawdown_r=-0.19))
        assert blocked == "champion_retained"
        promoted, _ = _decide_verdict(**_sufficient_kwargs(champion_expectancy_r=0.28, challenger_expectancy_r=0.27, champion_max_drawdown_r=-0.15, challenger_max_drawdown_r=-0.08))
        assert promoted == "challenger_recommended"


class TestProfitFactorNonRegression:
    """CEO directive "TradeTown — Research Engine Hardening +
    Self-Improvement Implementation Pass," Phase 7 — closes the real,
    confirmed gap the prior forensic audit found: `_decide_verdict()`
    never read profit factor at all, so a challenger with a
    dramatically worse profit factor could still be recommended purely
    on the expectancy/drawdown tradeoff. Deliberately NOT a naive
    `challenger_pf > champion_pf` — a real non-regression guard layered
    on top of the existing tradeoff paths, never a replacement."""

    def test_path_a_promotion_is_blocked_by_a_meaningful_profit_factor_regression(self) -> None:
        # Path A alone (expectancy +50%, no drawdown regression) would recommend the challenger.
        verdict, reason = _decide_verdict(
            **_sufficient_kwargs(
                champion_expectancy_r=0.20, challenger_expectancy_r=0.30, champion_max_drawdown_r=-0.10, challenger_max_drawdown_r=-0.10,
                champion_profit_factor=2.0, challenger_profit_factor=1.4,  # -30%, past the real 20% bar
            )
        )
        assert verdict == "champion_retained"
        assert "profit factor regressed" in reason
        assert "2.00" in reason and "1.40" in reason

    def test_path_b_promotion_is_blocked_by_a_meaningful_profit_factor_regression(self) -> None:
        # Path B alone (drawdown improved 46.7%, expectancy only -3.6%) would recommend the challenger.
        verdict, reason = _decide_verdict(
            **_sufficient_kwargs(
                champion_expectancy_r=0.28, challenger_expectancy_r=0.27, champion_max_drawdown_r=-0.15, challenger_max_drawdown_r=-0.08,
                champion_profit_factor=1.8, challenger_profit_factor=1.0,  # -44.4%, past the real 20% bar
            )
        )
        assert verdict == "champion_retained"
        assert "profit factor regressed" in reason

    def test_a_small_profit_factor_regression_within_the_bar_still_promotes(self) -> None:
        verdict, _ = _decide_verdict(
            **_sufficient_kwargs(
                champion_expectancy_r=0.20, challenger_expectancy_r=0.30, champion_max_drawdown_r=-0.10, challenger_max_drawdown_r=-0.10,
                champion_profit_factor=2.0, challenger_profit_factor=1.7,  # -15%, within the real 20% bar
            )
        )
        assert verdict == "challenger_recommended"

    def test_an_improved_profit_factor_never_blocks_promotion(self) -> None:
        verdict, _ = _decide_verdict(
            **_sufficient_kwargs(
                champion_expectancy_r=0.20, challenger_expectancy_r=0.30, champion_max_drawdown_r=-0.10, challenger_max_drawdown_r=-0.10,
                champion_profit_factor=1.5, challenger_profit_factor=2.5,
            )
        )
        assert verdict == "challenger_recommended"

    def test_a_non_positive_champion_profit_factor_sets_no_proportional_bar_never_crashes(self) -> None:
        verdict, _ = _decide_verdict(
            **_sufficient_kwargs(
                champion_expectancy_r=0.20, challenger_expectancy_r=0.30, champion_max_drawdown_r=-0.10, challenger_max_drawdown_r=-0.10,
                champion_profit_factor=0.0, challenger_profit_factor=0.5,
            )
        )
        assert verdict == "challenger_recommended"

    def test_profit_factor_never_creates_a_promotion_on_its_own_the_base_tradeoff_still_gates_first(self) -> None:
        """A real profit factor improvement never rescues a challenger
        whose own expectancy/drawdown tradeoff didn't clear either
        path's bar in the first place — this is a non-regression guard,
        never a naive `challenger_pf > champion_pf` promotion rule."""
        verdict, _ = _decide_verdict(
            **_sufficient_kwargs(
                champion_expectancy_r=0.20, challenger_expectancy_r=0.21, champion_max_drawdown_r=-0.10, challenger_max_drawdown_r=-0.099,
                champion_profit_factor=1.0, challenger_profit_factor=5.0,
            )
        )
        assert verdict == "champion_retained"


class TestGetCurrentChampion:
    def test_no_history_reads_none_not_fabricated(self) -> None:
        assert get_current_champion([], strategy_family="Any Family") is None

    def test_the_most_recent_real_entry_for_the_family_wins(self) -> None:
        history = [
            ChampionRecord(id="c1", strategyFamily="Family A", definitionId="def-a1", definitionVersion=1, sourceComparisonId=None, promotedBy="quant", reasoning="first", promotedAt="2024-01-01T00:00:00+00:00"),
            ChampionRecord(id="c2", strategyFamily="Family B", definitionId="def-b1", definitionVersion=1, sourceComparisonId=None, promotedBy="quant", reasoning="first", promotedAt="2024-01-02T00:00:00+00:00"),
            ChampionRecord(id="c3", strategyFamily="Family A", definitionId="def-a2", definitionVersion=2, sourceComparisonId="cmp-1", promotedBy="quant", reasoning="beat v1", promotedAt="2024-01-03T00:00:00+00:00"),
        ]
        current = get_current_champion(history, strategy_family="Family A")
        assert current is not None
        assert current.id == "c3"
        assert current.definition_version == 2


class TestCompareChampionChallenger:
    def test_real_metrics_are_carried_through_verbatim_from_each_sides_own_record(self) -> None:
        champion_definition = compile_strategy_text(name="CC Champion", source_text=_CHAMPION_TEXT)
        challenger_definition = compile_strategy_text(name="CC Challenger", source_text=_CHALLENGER_TEXT)
        comparison = compare_champion_challenger(
            champion_definition,
            challenger_definition,
            strategy_family="CC Family",
            hypothesis="Filtering by RSI confirmation may cut false breakouts.",
            proposed_by="quant",
            comparison_id="cmp-1",
            generated_at="2024-01-01T00:00:00+00:00",
            symbols=["AAPL"],
        )
        assert comparison.champion_definition_id == champion_definition.id
        assert comparison.challenger_definition_id == challenger_definition.id
        assert comparison.verdict in ("challenger_recommended", "champion_retained", "insufficient_evidence")
        # Every real metric traces back to each side's own real research record -- proven by
        # independently recomputing both records and asserting the comparison matches exactly.
        champion_record = run_research_experiment(champion_definition, symbols=["AAPL"])
        challenger_record = run_research_experiment(challenger_definition, symbols=["AAPL"])
        assert comparison.champion_expectancy_r == champion_record.backtest.overall.expectancy_r
        assert comparison.challenger_expectancy_r == challenger_record.backtest.overall.expectancy_r
        assert comparison.champion_conclusion == champion_record.conclusion
        assert comparison.challenger_conclusion == challenger_record.conclusion

    def test_an_uncompilable_challenger_definition_reads_insufficient_evidence_never_a_silent_pass(self) -> None:
        champion_definition = compile_strategy_text(name="CC Champion 2", source_text=_CHAMPION_TEXT)
        challenger_definition = compile_strategy_text(name="CC Bad Challenger", source_text=_INVALID_TEXT)
        comparison = compare_champion_challenger(
            champion_definition,
            challenger_definition,
            strategy_family="CC Family 2",
            hypothesis="A hypothesis that never compiles.",
            proposed_by="quant",
            comparison_id="cmp-2",
            generated_at="2024-01-01T00:00:00+00:00",
            symbols=["AAPL"],
        )
        assert comparison.verdict == "insufficient_evidence"


class TestPromoteChallenger:
    def test_promoting_a_champion_retained_comparison_is_refused(self) -> None:
        champion_definition = compile_strategy_text(name="CC Champion 3", source_text=_CHAMPION_TEXT)
        challenger_definition = compile_strategy_text(name="CC Challenger 3", source_text=_CHALLENGER_TEXT)
        comparison = compare_champion_challenger(
            champion_definition,
            challenger_definition,
            strategy_family="CC Family 3",
            hypothesis="h",
            proposed_by="quant",
            comparison_id="cmp-3",
            generated_at="2024-01-01T00:00:00+00:00",
            symbols=["AAPL"],
        ).model_copy(update={"verdict": "champion_retained"})
        try:
            promote_challenger(comparison, promoted_by="quant", reasoning="should not be allowed", record_id="champ-1", promoted_at="2024-01-01T00:00:00+00:00")
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "champion_retained" in str(exc)

    def test_promoting_a_recommended_comparison_produces_a_real_champion_record(self) -> None:
        champion_definition = compile_strategy_text(name="CC Champion 4", source_text=_CHAMPION_TEXT)
        challenger_definition = compile_strategy_text(name="CC Challenger 4", source_text=_CHALLENGER_TEXT)
        comparison = compare_champion_challenger(
            champion_definition,
            challenger_definition,
            strategy_family="CC Family 4",
            hypothesis="h",
            proposed_by="quant",
            comparison_id="cmp-4",
            generated_at="2024-01-01T00:00:00+00:00",
            symbols=["AAPL"],
        ).model_copy(update={"verdict": "challenger_recommended"})
        record = promote_challenger(comparison, promoted_by="cio", reasoning="Cleared the real disclosed bar.", record_id="champ-2", promoted_at="2024-01-02T00:00:00+00:00")
        assert record.strategy_family == "CC Family 4"
        assert record.definition_id == challenger_definition.id
        assert record.definition_version == challenger_definition.version
        assert record.source_comparison_id == "cmp-4"
        assert record.promoted_by == "cio"


class TestChampionChallengerState:
    """Real, persisted end-to-end wiring through app/state.py — mirrors
    test_quant_research_lab.py's own TestSubmitQuantResearchExperimentState
    convention."""

    def test_a_submitted_comparison_is_really_persisted(self) -> None:
        state = GameState()
        champion_definition = compile_strategy_text(name="State Champion", source_text=_CHAMPION_TEXT)
        challenger_definition = compile_strategy_text(name="State Challenger", source_text=_CHALLENGER_TEXT)
        saved, comparison = asyncio.run(
            state.submit_champion_challenger_comparison(
                champion_definition,
                challenger_definition,
                strategy_family="State Family",
                hypothesis="RSI confirmation may cut false breakouts.",
                proposed_by="quant",
                symbols=["AAPL"],
            )
        )
        assert len(saved.challenger_comparisons) == 1
        assert saved.challenger_comparisons[0].id == comparison.id
        assert saved.challenger_comparisons[0].strategy_family == "State Family"

    def test_promoting_requires_a_real_persisted_comparison_id(self) -> None:
        state = GameState()
        try:
            asyncio.run(state.promote_champion_challenger(comparison_id="does-not-exist", promoted_by="quant", reasoning="x"))
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "does-not-exist" in str(exc)

    def test_two_comparisons_for_the_same_family_get_distinct_real_ids(self) -> None:
        state = GameState()
        champion_definition = compile_strategy_text(name="State Champion 2", source_text=_CHAMPION_TEXT)
        challenger_definition = compile_strategy_text(name="State Challenger 2", source_text=_CHALLENGER_TEXT)
        _, first = asyncio.run(
            state.submit_champion_challenger_comparison(
                champion_definition, challenger_definition, strategy_family="State Family 2", hypothesis="h1", proposed_by="quant", symbols=["AAPL"]
            )
        )
        saved, second = asyncio.run(
            state.submit_champion_challenger_comparison(
                champion_definition, challenger_definition, strategy_family="State Family 2", hypothesis="h2", proposed_by="quant", symbols=["AAPL"]
            )
        )
        assert first.id != second.id
        assert len(saved.challenger_comparisons) == 2


def _bootstrap_result(**overrides: object) -> BootstrapComparisonResult:
    base: dict[str, object] = dict(
        championSampleSize=30,
        challengerSampleSize=30,
        championMeanR=0.2,
        challengerMeanR=0.3,
        meanDifferenceEstimate=0.1,
        differenceCiLow=0.02,
        differenceCiHigh=0.18,
        confidenceLevelPct=95.0,
        probabilityChallengerBetterPct=97.0,
        method="iid_percentile_bootstrap",
        resamples=2000,
        evidenceState="sufficient_evidence",
        limitationNote="x",
    )
    base.update(overrides)
    return BootstrapComparisonResult(**base)  # type: ignore[arg-type]


class TestClassifyStatisticalEconomicEvidence:
    """CEO directive "TradeTown — Statistical Validation + Research
    Failure Taxonomy," Part 1 — the real, disclosed 2x2-plus-escape-hatch
    combination rule."""

    def test_insufficient_bootstrap_evidence_always_reads_insufficient_sample(self) -> None:
        result = _bootstrap_result(evidenceState="insufficient_evidence", differenceCiLow=None, differenceCiHigh=None, probabilityChallengerBetterPct=None)
        classification = _classify_statistical_economic_evidence(verdict="challenger_recommended", statistical_comparison=result)
        assert classification == "insufficient_sample"

    def test_both_statistically_supported_and_economically_meaningful_reads_both(self) -> None:
        result = _bootstrap_result(differenceCiLow=0.05)
        classification = _classify_statistical_economic_evidence(verdict="challenger_recommended", statistical_comparison=result)
        assert classification == "both"

    def test_statistically_supported_but_economically_retained_reads_statistically_supported_only(self) -> None:
        result = _bootstrap_result(differenceCiLow=0.05)
        classification = _classify_statistical_economic_evidence(verdict="champion_retained", statistical_comparison=result)
        assert classification == "statistically_supported_only"

    def test_economically_meaningful_but_ci_spans_zero_reads_economically_meaningful_only(self) -> None:
        result = _bootstrap_result(differenceCiLow=-0.05, differenceCiHigh=0.15)
        classification = _classify_statistical_economic_evidence(verdict="challenger_recommended", statistical_comparison=result)
        assert classification == "economically_meaningful_only"

    def test_neither_statistically_supported_nor_economically_meaningful_reads_neither(self) -> None:
        result = _bootstrap_result(differenceCiLow=-0.1, differenceCiHigh=0.1)
        classification = _classify_statistical_economic_evidence(verdict="champion_retained", statistical_comparison=result)
        assert classification == "neither"

    def test_a_negative_ci_excluding_zero_is_not_statistically_supported_for_the_challenger(self) -> None:
        # The challenger is statistically WORSE (CI entirely negative) -- never "supported".
        result = _bootstrap_result(differenceCiLow=-0.3, differenceCiHigh=-0.1)
        classification = _classify_statistical_economic_evidence(verdict="champion_retained", statistical_comparison=result)
        assert classification == "neither"

    def test_invalid_bootstrap_evidence_reads_invalid_evidence_never_insufficient_sample(self) -> None:
        # CEO directive "TradeTown — Research Engine Hardening +
        # Self-Improvement Implementation Pass," Phase 8 — a real,
        # distinct third state, never conflated with "insufficient
        # sample" (a different, honest condition: too few real
        # observations, not a non-finite one).
        result = _bootstrap_result(evidenceState="invalid_evidence", differenceCiLow=None, differenceCiHigh=None, probabilityChallengerBetterPct=None, championMeanR=None, challengerMeanR=None, meanDifferenceEstimate=None)
        classification = _classify_statistical_economic_evidence(verdict="challenger_recommended", statistical_comparison=result)
        assert classification == "invalid_evidence"


class TestCompareChampionChallengerStatisticalWiring:
    """Real end-to-end wiring of the new statistical/multiple-testing/
    tuning-exposure fields through compare_champion_challenger()."""

    def test_a_real_comparison_carries_a_real_statistical_comparison_and_classification(self) -> None:
        champion_definition = compile_strategy_text(name="Stat Wire Champion", source_text=_CHAMPION_TEXT)
        challenger_definition = compile_strategy_text(name="Stat Wire Challenger", source_text=_CHALLENGER_TEXT)
        comparison = compare_champion_challenger(
            champion_definition,
            challenger_definition,
            strategy_family="Stat Wire Family",
            hypothesis="h",
            proposed_by="quant",
            comparison_id="cmp-stat-1",
            generated_at="2024-01-01T00:00:00+00:00",
            symbols=["AAPL"],
        )
        assert comparison.statistical_comparison is not None
        assert comparison.classification in ("both", "statistically_supported_only", "economically_meaningful_only", "neither", "insufficient_sample")

    def test_no_research_archive_supplied_leaves_the_family_count_honestly_none(self) -> None:
        champion_definition = compile_strategy_text(name="Stat Wire Champion 2", source_text=_CHAMPION_TEXT)
        challenger_definition = compile_strategy_text(name="Stat Wire Challenger 2", source_text=_CHALLENGER_TEXT)
        comparison = compare_champion_challenger(
            champion_definition,
            challenger_definition,
            strategy_family="Stat Wire Family 2",
            hypothesis="h",
            proposed_by="quant",
            comparison_id="cmp-stat-2",
            generated_at="2024-01-01T00:00:00+00:00",
            symbols=["AAPL"],
        )
        assert comparison.research_family_experiment_count is None
        assert comparison.multiple_testing_risk is False

    def test_an_overtested_family_archive_flags_multiple_testing_risk(self) -> None:
        champion_definition = compile_strategy_text(name="Stat Wire Champion 3", source_text=_CHAMPION_TEXT)
        challenger_definition = compile_strategy_text(name="Stat Wire Challenger 3", source_text=_CHALLENGER_TEXT)
        record = run_research_experiment(challenger_definition, symbols=["AAPL"])
        existing = []
        for i in range(OVERTESTED_FAMILY_THRESHOLD):
            experiment = file_quant_research_experiment(
                record, experiment_id=f"exp-{i}", hypothesis=f"h{i}", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00", existing=existing
            )
            existing.append(experiment)
        comparison = compare_champion_challenger(
            champion_definition,
            challenger_definition,
            strategy_family="Stat Wire Family 3",
            hypothesis="h",
            proposed_by="quant",
            comparison_id="cmp-stat-3",
            generated_at="2024-01-01T00:00:00+00:00",
            symbols=["AAPL"],
            quant_research_experiments=existing,
        )
        assert comparison.research_family_experiment_count == OVERTESTED_FAMILY_THRESHOLD
        assert comparison.multiple_testing_risk is True

    def test_a_low_version_challenger_reads_no_high_tuning_exposure(self) -> None:
        champion_definition = compile_strategy_text(name="Stat Wire Champion 4", source_text=_CHAMPION_TEXT)
        challenger_definition = compile_strategy_text(name="Stat Wire Challenger 4", source_text=_CHALLENGER_TEXT)
        assert challenger_definition.version == 1
        comparison = compare_champion_challenger(
            champion_definition,
            challenger_definition,
            strategy_family="Stat Wire Family 4",
            hypothesis="h",
            proposed_by="quant",
            comparison_id="cmp-stat-4",
            generated_at="2024-01-01T00:00:00+00:00",
            symbols=["AAPL"],
        )
        assert comparison.challenger_tuning_version == 1
        assert comparison.high_tuning_exposure is False

    def test_a_heavily_revised_challenger_reads_high_tuning_exposure(self) -> None:
        champion_definition = compile_strategy_text(name="Stat Wire Champion 5", source_text=_CHAMPION_TEXT)
        challenger_definition = compile_strategy_text(name="Stat Wire Challenger 5", source_text=_CHALLENGER_TEXT, previous_version=HIGH_TUNING_VERSION_THRESHOLD)
        assert challenger_definition.version == HIGH_TUNING_VERSION_THRESHOLD + 1
        comparison = compare_champion_challenger(
            champion_definition,
            challenger_definition,
            strategy_family="Stat Wire Family 5",
            hypothesis="h",
            proposed_by="quant",
            comparison_id="cmp-stat-5",
            generated_at="2024-01-01T00:00:00+00:00",
            symbols=["AAPL"],
        )
        assert comparison.challenger_tuning_version == HIGH_TUNING_VERSION_THRESHOLD + 1
        assert comparison.high_tuning_exposure is True
