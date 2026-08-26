"""Covers app/whatif.py — v0.7 Feature 16, the What-If Simulation Lab.
Every scenario's magnitude must trace back to the symbol's own real
candle series (via trend_pct/volatility_pct); only each scenario's
direction/multiplier is a documented, fixed modeling assumption.
"""
from __future__ import annotations

import random

from app.market_data import Candle
from app.whatif import _SCENARIO_PARAMS, run_whatif_simulation


def _candles(closes: list[float], *, high_low_spread_pct: float = 1.0) -> list[Candle]:
    candles = []
    for i, close in enumerate(closes):
        spread = close * (high_low_spread_pct / 100)
        candles.append(
            Candle(
                symbol="NEXA",
                timeframe="1h",
                timestamp=f"2026-01-01T{i:02d}:00:00Z",
                open=close,
                high=close + spread,
                low=close - spread,
                close=close,
                volume=1000.0,
                data_status="simulated",
            )
        )
    return candles


def _uptrend_candles() -> list[Candle]:
    return _candles([100 + i * 0.5 for i in range(30)])


def _downtrend_candles() -> list[Candle]:
    return _candles([100 - i * 0.5 for i in range(30)])


def _flat_candles() -> list[Candle]:
    return _candles([100.0 for _ in range(30)])


class TestRunWhatifSimulationDeterminism:
    """Professional Research → Certification → Paper → Capital
    Allocation Pipeline — an audit found this module's Monte Carlo used
    the bare, unseeded global `random` module, so identical what-if
    questions could get different real answers on every re-run. This
    confirms the fix."""

    def test_identical_symbol_and_candles_produce_identical_results(self) -> None:
        first = run_whatif_simulation("NEXA", _uptrend_candles())
        second = run_whatif_simulation("NEXA", _uptrend_candles())
        assert first == second


class TestRunWhatifSimulation:
    def test_all_twelve_scenarios_present(self) -> None:
        sim = run_whatif_simulation("NEXA", _flat_candles())
        assert len(sim.scenarios) == 12
        assert {s.scenario_type for s in sim.scenarios} == set(_SCENARIO_PARAMS.keys())

    def test_percentiles_are_internally_monotonic(self) -> None:
        sim = run_whatif_simulation("NEXA", _uptrend_candles())
        for s in sim.scenarios:
            assert s.reward_range_low_pct <= s.most_likely_pct <= s.reward_range_high_pct

    def test_probability_of_profit_is_a_real_percentage(self) -> None:
        sim = run_whatif_simulation("NEXA", _uptrend_candles())
        for s in sim.scenarios:
            assert 0.0 <= s.probability_of_profit_pct <= 100.0

    def test_bullish_continuation_skews_more_positive_than_bearish_reversal(self) -> None:
        random.seed(1)
        sim = run_whatif_simulation("NEXA", _flat_candles())
        bullish = next(s for s in sim.scenarios if s.scenario_type == "bullish_continuation")
        bearish = next(s for s in sim.scenarios if s.scenario_type == "bearish_reversal")
        assert bullish.most_likely_pct > bearish.most_likely_pct

    def test_flash_crash_has_worse_max_risk_than_sideways_consolidation(self) -> None:
        random.seed(2)
        sim = run_whatif_simulation("NEXA", _flat_candles())
        crash = next(s for s in sim.scenarios if s.scenario_type == "flash_crash")
        sideways = next(s for s in sim.scenarios if s.scenario_type == "sideways_consolidation")
        assert crash.max_risk_pct < sideways.max_risk_pct

    def test_trend_failure_fades_a_real_uptrend_downward(self) -> None:
        random.seed(3)
        sim = run_whatif_simulation("NEXA", _uptrend_candles())
        failure = next(s for s in sim.scenarios if s.scenario_type == "trend_failure")
        assert failure.most_likely_pct < 0

    def test_trend_failure_fades_a_real_downtrend_upward(self) -> None:
        random.seed(4)
        sim = run_whatif_simulation("NEXA", _downtrend_candles())
        failure = next(s for s in sim.scenarios if s.scenario_type == "trend_failure")
        assert failure.most_likely_pct > 0

    def test_baseline_reflects_the_real_measured_trend_direction(self) -> None:
        random.seed(5)
        up = run_whatif_simulation("NEXA", _uptrend_candles())
        random.seed(5)
        down = run_whatif_simulation("NEXA", _downtrend_candles())
        assert up.baseline.most_likely_pct > down.baseline.most_likely_pct

    def test_best_and_worst_case_are_real_scenario_types(self) -> None:
        sim = run_whatif_simulation("NEXA", _uptrend_candles())
        scenario_types = {s.scenario_type for s in sim.scenarios}
        assert sim.best_case_scenario in scenario_types
        assert sim.worst_case_scenario in scenario_types

    def test_every_scenario_has_a_real_invalidation_condition(self) -> None:
        sim = run_whatif_simulation("NEXA", _flat_candles())
        for s in sim.scenarios:
            assert s.invalidation != ""

    def test_handles_a_short_candle_sample_without_crashing(self) -> None:
        sim = run_whatif_simulation("NEXA", _candles([100.0, 101.0]))
        assert len(sim.scenarios) == 12
