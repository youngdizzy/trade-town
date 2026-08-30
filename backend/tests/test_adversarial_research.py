"""Covers app/adversarial_research.py — CEO directive "TradeTown —
Phase 8: Autonomous Strategy Discovery + Adversarial Research Engine,"
Sections 8D-8I. Pure-function unit tests hand-build real
`EmaPullbackTradeRecord` fixtures (every nested field populated with
real, valid values) so each attack can be tested against exact,
hand-picked numbers; integration tests run the real
`run_adversarial_research()` entry point over a real compiled strategy
and real (mock) candle data end to end.
"""
from __future__ import annotations

from typing import Literal

from app.adversarial_research import (
    DEFAULT_MIN_TRADES_FOR_BUCKET_VERDICT,
    OUTLIER_REMOVAL_FRACTIONS,
    classify_regime_robustness,
    derive_failure_boundaries,
    evaluate_holdout_availability,
    run_adversarial_research,
    run_extended_cost_attack,
    run_outlier_removal_attack,
    run_sequence_attack,
    run_worst_period_attack,
)
from app.research_experiment import run_research_experiment
from app.schemas import EmaPullbackStatsBucket, EmaPullbackTradeRecord, ExtendedCostAttackResult, ExtendedCostAttackScenario, OutlierRemovalScenario, OutlierResilienceResult, ParameterSensitivityResult
from app.strategy_compiler import compile_strategy_text

_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."


def _trade(*, index: int, r: float, direction: Literal["long", "short"] = "long", session: Literal["new_york"] = "new_york") -> EmaPullbackTradeRecord:
    outcome: Literal["win", "loss"] = "win" if r >= 0 else "loss"
    return EmaPullbackTradeRecord(
        symbol="AAPL", direction=direction, entryTimestamp=f"2024-01-{(index % 27) + 1:02d}T10:00:00+00:00",
        entryPrice=100.0, stopPrice=95.0, targetPrice=110.0, exitPrice=100.0 + r * 5, outcome=outcome,
        rMultipleRealized=r, entrySession=session, regimeTrend="trending_up", regimeVolatility="normal",
        breakoutCandleExtended=False, breakoutCandleRangeRatio=1.0, maeR=min(0.0, r), mfeR=max(0.0, r), barsHeld=10,
    )


def _trades(r_values: list[float]) -> list[EmaPullbackTradeRecord]:
    return [_trade(index=i, r=r) for i, r in enumerate(r_values)]


def _bucket(**overrides: object) -> EmaPullbackStatsBucket:
    base: dict[str, object] = dict(
        label="x", tradeCount=100, winCount=60, lossCount=40, openCount=0, winRatePct=60.0, avgWinR=1.5, avgLossR=-1.0,
        expectancyR=0.5, profitFactor=1.5, maxDrawdownR=-3.0, largestWinR=2.0, largestLossR=-1.0, verdict="enough_evidence", detail="x",
    )
    base.update(overrides)
    return EmaPullbackStatsBucket(**base)  # type: ignore[arg-type]


class TestRunOutlierRemovalAttack:
    def test_zero_trades(self) -> None:
        result = run_outlier_removal_attack([])
        assert result.classification == "insufficient_evidence"
        assert result.scenarios[0].bucket.trade_count == 0

    def test_below_evidence_floor(self) -> None:
        result = run_outlier_removal_attack(_trades([1.0] * (DEFAULT_MIN_TRADES_FOR_BUCKET_VERDICT - 1)))
        assert result.classification == "insufficient_evidence"

    def test_negative_baseline_is_insufficient_evidence_not_forced(self) -> None:
        trades = _trades([-1.0] * 15 + [0.5] * 10)
        result = run_outlier_removal_attack(trades)
        assert result.classification == "insufficient_evidence"

    def test_robust_to_outliers(self) -> None:
        # Uniform, moderate wins — removing the top 10% barely dents expectancy.
        trades = _trades([1.0] * 80 + [-0.5] * 20)
        result = run_outlier_removal_attack(trades)
        assert result.classification == "robust_to_outliers"
        assert result.scenarios[0].bucket.expectancy_r is not None and result.scenarios[0].bucket.expectancy_r > 0

    def test_highly_outlier_dependent(self) -> None:
        # One massive winner carries the whole strategy; removing just the top 1% flips it negative.
        trades = _trades([50.0] + [-0.5] * 99)
        result = run_outlier_removal_attack(trades)
        assert result.classification == "highly_outlier_dependent"

    def test_moderately_outlier_dependent(self) -> None:
        # 90 small losses + 10 winners of equal size: removing the top 1%/5%
        # (a subset of the winners) still leaves a real positive edge, but
        # removing the top 10% (ALL ten winners) flips it negative.
        trades = _trades([-0.05] * 90 + [1.0] * 10)
        result = run_outlier_removal_attack(trades)
        assert result.classification == "moderately_outlier_dependent"
        assert result.scenarios[0].bucket.trade_count == 100

    def test_removal_fractions_match_declared_constant(self) -> None:
        trades = _trades([1.0] * 50 + [-0.5] * 50)
        result = run_outlier_removal_attack(trades)
        assert len(result.scenarios) == len(OUTLIER_REMOVAL_FRACTIONS) + 1  # +1 for baseline
        assert result.scenarios[1].trades_removed == 1  # top 1% of 100 = 1
        assert result.scenarios[2].trades_removed == 5  # top 5% of 100 = 5
        assert result.scenarios[3].trades_removed == 10  # top 10% of 100 = 10

    def test_never_removes_more_trades_than_exist(self) -> None:
        trades = _trades([1.0] * 5)  # tiny population, 10% of 5 rounds to 0 but floor is 1
        result = run_outlier_removal_attack(trades)
        for scenario in result.scenarios[1:]:
            assert scenario.trades_removed < len(trades)


class TestRunWorstPeriodAttack:
    def test_too_few_trades(self) -> None:
        result = run_worst_period_attack(_trades([1.0, -1.0]))
        assert result.window_trade_count == 0
        assert result.window_cumulative_r is None

    def test_finds_the_real_worst_contiguous_block(self) -> None:
        # 30 trades: a clearly worst contiguous stretch of losses in the middle.
        r_values = [1.0] * 10 + [-2.0] * 10 + [1.0] * 10
        result = run_worst_period_attack(_trades(r_values))
        assert result.window_trade_count > 0
        assert result.window_cumulative_r is not None and result.window_cumulative_r < 0

    def test_uniform_sequence_worst_window_equals_window_sum(self) -> None:
        r_values = [0.1] * 40
        result = run_worst_period_attack(_trades(r_values))
        assert result.window_cumulative_r is not None
        assert result.window_cumulative_r == round(0.1 * result.window_trade_count, 3)


class TestRunSequenceAttack:
    def test_below_evidence_floor(self) -> None:
        result = run_sequence_attack(_trades([1.0] * 5), definition_id="d", definition_version=1)
        assert result.reshuffle_count == 0
        assert result.baseline_max_drawdown_r is None

    def test_deterministic_for_same_definition(self) -> None:
        trades = _trades([2.0, -1.0, 3.0, -2.0, 1.0, -1.5, 2.5, -0.5, 1.0, -1.0] * 3)
        r1 = run_sequence_attack(trades, definition_id="def-1", definition_version=1)
        r2 = run_sequence_attack(trades, definition_id="def-1", definition_version=1)
        assert r1.worst_reshuffled_max_drawdown_r == r2.worst_reshuffled_max_drawdown_r
        assert r1.seed == r2.seed

    def test_different_definition_id_changes_the_seed(self) -> None:
        trades = _trades([2.0, -1.0, 3.0, -2.0, 1.0] * 6)
        r1 = run_sequence_attack(trades, definition_id="def-1", definition_version=1)
        r2 = run_sequence_attack(trades, definition_id="def-2", definition_version=1)
        assert r1.seed != r2.seed

    def test_worst_reshuffled_drawdown_is_never_less_than_baseline(self) -> None:
        trades = _trades([2.0, -1.0, 3.0, -2.0, 1.0, -1.5, 2.5, -0.5, 1.0, -1.0] * 3)
        result = run_sequence_attack(trades, definition_id="def-x", definition_version=1)
        assert result.worst_reshuffled_max_drawdown_r is not None and result.baseline_max_drawdown_r is not None
        assert result.worst_reshuffled_max_drawdown_r >= result.baseline_max_drawdown_r

    def test_all_wins_has_zero_drawdown(self) -> None:
        trades = _trades([1.0] * 25)
        result = run_sequence_attack(trades, definition_id="def-allwin", definition_version=1)
        assert result.baseline_max_drawdown_r == 0.0
        assert result.worst_reshuffled_max_drawdown_r == 0.0


class TestRunExtendedCostAttack:
    def test_expectancy_degrades_monotonically_with_more_cost(self) -> None:
        trades = _trades([1.0] * 60 + [-0.8] * 40)
        result = run_extended_cost_attack(trades)
        expectancies = [s.bucket.expectancy_r for s in result.scenarios]
        assert all(e is not None for e in expectancies)
        real_expectancies = [e for e in expectancies if e is not None]
        assert real_expectancies == sorted(real_expectancies, reverse=True)  # each harsher scenario is <= the previous

    def test_survives_beyond_stress_false_when_catastrophic_flips_negative(self) -> None:
        trades = _trades([0.3] * 60 + [-0.28] * 40)  # thin, cost-fragile edge
        result = run_extended_cost_attack(trades)
        assert result.survives_beyond_stress is False

    def test_zero_trades_produces_no_crash(self) -> None:
        result = run_extended_cost_attack([])
        assert result.survives_beyond_stress is None


class TestClassifyRegimeRobustness:
    def test_unknown_when_no_bucket_has_enough_evidence(self) -> None:
        buckets = [_bucket(label="trending", verdict="not_enough_evidence", expectancyR=None, tradeCount=3)]
        result = classify_regime_robustness(buckets, [])
        assert result.classification == "regime_unknown"

    def test_robust_when_every_evaluated_regime_is_positive(self) -> None:
        trend = [_bucket(label="trending_up", expectancyR=0.5), _bucket(label="trending_down", expectancyR=0.3)]
        vol = [_bucket(label="high", expectancyR=0.2)]
        result = classify_regime_robustness(trend, vol)
        assert result.classification == "regime_robust"
        assert set(result.proven_regimes) == {"trending_up", "trending_down", "high"}

    def test_specialist_when_mixed(self) -> None:
        trend = [_bucket(label="trending_up", expectancyR=0.5), _bucket(label="ranging", expectancyR=-0.2)]
        result = classify_regime_robustness(trend, [])
        assert result.classification == "regime_specialist"
        assert result.proven_regimes == ["trending_up"]
        assert result.fragile_regimes == ["ranging"]

    def test_fragile_when_every_evaluated_regime_is_negative(self) -> None:
        trend = [_bucket(label="trending_up", expectancyR=-0.1), _bucket(label="ranging", expectancyR=-0.4)]
        result = classify_regime_robustness(trend, [])
        assert result.classification == "regime_fragile"

    def test_insufficient_evidence_buckets_are_named_in_neither_list(self) -> None:
        trend = [_bucket(label="trending_up", expectancyR=0.5), _bucket(label="ranging", verdict="not_enough_evidence", expectancyR=None)]
        result = classify_regime_robustness(trend, [])
        assert "ranging" not in result.proven_regimes
        assert "ranging" not in result.fragile_regimes


class TestDeriveFailureBoundaries:
    def _outlier_result(self, *, baseline_dd: float = -3.0, flips_at: str | None = None) -> OutlierResilienceResult:
        scenarios = [OutlierRemovalScenario(label="baseline", tradesRemoved=0, bucket=_bucket(expectancyR=1.0, maxDrawdownR=baseline_dd))]
        for label, _fraction in OUTLIER_REMOVAL_FRACTIONS:
            exp = -0.1 if label == flips_at else 1.0
            scenarios.append(OutlierRemovalScenario(label=label, tradesRemoved=1, bucket=_bucket(expectancyR=exp)))
        return OutlierResilienceResult(scenarios=scenarios, classification="robust_to_outliers", detail="x")

    def _cost_result(self, *, flips: bool) -> ExtendedCostAttackResult:
        scenarios = [
            ExtendedCostAttackScenario(label="stressed", costBpsPerLeg=50.0, bucket=_bucket(expectancyR=(-0.1 if flips else 1.0))),
            ExtendedCostAttackScenario(label="extreme", costBpsPerLeg=150.0, bucket=_bucket(expectancyR=(-0.5 if flips else 0.8))),
            ExtendedCostAttackScenario(label="catastrophic", costBpsPerLeg=250.0, bucket=_bucket(expectancyR=(-1.0 if flips else 0.5))),
        ]
        return ExtendedCostAttackResult(scenarios=scenarios, survivesBeyondStress=not flips, detail="x")

    def _param_result(self, *, sweepable: bool = True) -> ParameterSensitivityResult:
        from app.schemas import ParameterSensitivityAxisResult, ParameterSensitivityPoint

        points = [
            ParameterSensitivityPoint(label="tight", value=2.0, bucket=_bucket(expectancyR=-0.2)),
            ParameterSensitivityPoint(label="base", value=3.0, bucket=_bucket(expectancyR=1.0)),
            ParameterSensitivityPoint(label="wide", value=4.0, bucket=_bucket(expectancyR=1.2)),
        ]
        stop_axis = ParameterSensitivityAxisResult(parameter="stop", sweepable=sweepable, baseValue=3.0, points=points, detail="x")
        return ParameterSensitivityResult(
            id="p", definitionId="d", definitionVersion=1, stopAxis=stop_axis, targetAxis=None, verdict="robust",
            detail="x", multipleTestingNote="x", dataHonestyNote="x", generatedAt="2024-01-01T00:00:00+00:00",
        )

    def test_cost_boundary_found_when_stressed_flips(self) -> None:
        boundaries = derive_failure_boundaries(
            definition_id="d", outlier_result=self._outlier_result(), extended_cost_result=self._cost_result(flips=True),
            parameter_sensitivity=self._param_result(), risk_per_trade_pct=2.0,
        )
        cost_boundary = next(b for b in boundaries if b.failure_boundary_type == "cost_bps")
        assert cost_boundary.failure_boundary_value == 50.0
        assert cost_boundary.distance_to_failure == 50.0

    def test_cost_boundary_none_when_never_observed_to_fail(self) -> None:
        boundaries = derive_failure_boundaries(
            definition_id="d", outlier_result=self._outlier_result(), extended_cost_result=self._cost_result(flips=False),
            parameter_sensitivity=self._param_result(), risk_per_trade_pct=2.0,
        )
        cost_boundary = next(b for b in boundaries if b.failure_boundary_type == "cost_bps")
        assert cost_boundary.failure_boundary_value is None
        assert cost_boundary.distance_to_failure is None

    def test_drawdown_boundary_uses_real_research_candidate_bound(self) -> None:
        from app.research_loop import RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT

        boundaries = derive_failure_boundaries(
            definition_id="d", outlier_result=self._outlier_result(baseline_dd=-3.0), extended_cost_result=self._cost_result(flips=False),
            parameter_sensitivity=self._param_result(), risk_per_trade_pct=2.0,
        )
        dd_boundary = next(b for b in boundaries if b.failure_boundary_type == "drawdown_pct")
        assert dd_boundary.failure_boundary_value == RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT
        assert dd_boundary.current_value == 6.0  # 3.0R * 2.0% risk-per-trade

    def test_outlier_boundary_found_at_the_real_flip_point(self) -> None:
        boundaries = derive_failure_boundaries(
            definition_id="d", outlier_result=self._outlier_result(flips_at="without top 5% winners"), extended_cost_result=self._cost_result(flips=False),
            parameter_sensitivity=self._param_result(), risk_per_trade_pct=2.0,
        )
        outlier_boundary = next(b for b in boundaries if b.failure_boundary_type == "outlier_removal_pct")
        assert outlier_boundary.failure_boundary_value == 5.0

    def test_parameter_boundary_skipped_when_not_sweepable(self) -> None:
        boundaries = derive_failure_boundaries(
            definition_id="d", outlier_result=self._outlier_result(), extended_cost_result=self._cost_result(flips=False),
            parameter_sensitivity=self._param_result(sweepable=False), risk_per_trade_pct=2.0,
        )
        assert not any(b.failure_boundary_type == "parameter_stop" for b in boundaries)

    def test_parameter_boundary_found_at_the_real_flip_point(self) -> None:
        boundaries = derive_failure_boundaries(
            definition_id="d", outlier_result=self._outlier_result(), extended_cost_result=self._cost_result(flips=False),
            parameter_sensitivity=self._param_result(sweepable=True), risk_per_trade_pct=2.0,
        )
        stop_boundary = next(b for b in boundaries if b.failure_boundary_type == "parameter_stop")
        assert stop_boundary.failure_boundary_value == 2.0
        assert stop_boundary.current_value == 3.0
        assert stop_boundary.distance_to_failure == 1.0

    def test_confidence_derived_from_real_sample_size(self) -> None:
        low_evidence = self._outlier_result()
        low_evidence.scenarios[0] = OutlierRemovalScenario(label="baseline", tradesRemoved=0, bucket=_bucket(expectancyR=1.0, tradeCount=5, maxDrawdownR=-1.0))
        boundaries = derive_failure_boundaries(
            definition_id="d", outlier_result=low_evidence, extended_cost_result=self._cost_result(flips=False),
            parameter_sensitivity=self._param_result(), risk_per_trade_pct=2.0,
        )
        assert all(b.confidence == "low" for b in boundaries)


class TestEvaluateHoldoutAvailability:
    def test_always_not_available_never_faked(self) -> None:
        result = evaluate_holdout_availability()
        assert result.status == "not_available"
        assert "MockMarketDataProvider" in result.reason or "mock" in result.reason.lower()


class TestRunAdversarialResearchIntegration:
    """Real, end-to-end tests over the actual compiled-strategy pipeline
    and real (mock) candle data — no mocked evidence anywhere."""

    def test_a_real_run_produces_a_complete_real_result(self) -> None:
        definition = compile_strategy_text(name="Adversarial Integration Test", source_text=_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL", "MSFT"])
        result = run_adversarial_research(
            definition,
            regime_trend_breakdown=record.backtest.regime_trend_breakdown,
            regime_volatility_breakdown=record.backtest.regime_volatility_breakdown,
            parameter_sensitivity=record.parameter_sensitivity,
            risk_per_trade_pct=2.0,
            result_id="adv-integration-1",
            generated_at="2024-01-01T00:00:00+00:00",
            symbols=["AAPL", "MSFT"],
        )
        assert result.data_provenance == "simulated"
        assert result.outlier_resilience.classification in ("robust_to_outliers", "moderately_outlier_dependent", "highly_outlier_dependent", "insufficient_evidence")
        assert result.regime_robustness.classification in ("regime_robust", "regime_specialist", "regime_fragile", "regime_unknown")
        assert isinstance(result.failure_boundaries, list) and len(result.failure_boundaries) >= 2

    def test_an_uncompilable_definition_never_crashes_the_suite(self) -> None:
        definition = compile_strategy_text(name="Moon Adversarial", source_text="Buy when the moon is full.")
        record = run_research_experiment(definition, symbols=["AAPL"])
        result = run_adversarial_research(
            definition,
            regime_trend_breakdown=record.backtest.regime_trend_breakdown,
            regime_volatility_breakdown=record.backtest.regime_volatility_breakdown,
            parameter_sensitivity=record.parameter_sensitivity,
            risk_per_trade_pct=2.0,
            result_id="adv-integration-2",
            generated_at="2024-01-01T00:00:00+00:00",
            symbols=["AAPL"],
        )
        assert result.outlier_resilience.scenarios[0].bucket.trade_count == 0
        assert result.data_provenance == "simulated"

    def test_never_touches_champion_challenger_or_hall_of_fame(self) -> None:
        """Section 8N/8O — proven by real module-level import inspection."""
        import app.adversarial_research as module

        assert not hasattr(module, "compare_champion_challenger")
        assert not hasattr(module, "promote_challenger")
        assert not hasattr(module, "qualifies_for_hall_of_fame")
        assert not hasattr(module, "evaluate_certification_readiness")
