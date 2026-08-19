"""Covers app/cost_sensitivity.py — CEO directive "Professional Quant
Trading Firm — Quant Intelligence + Market Analysis Completion Phase
(Next Research + Validation Pass)," item 6. The critical guarantee this
file establishes: cost scenarios never re-simulate entries/exits — only
the real, already-closed trades' own realized R changes — and an open
trade is never assigned a fabricated cost.
"""
from __future__ import annotations

from app.cost_sensitivity import COST_SCENARIOS, _apply_cost_to_trades, run_cost_sensitivity
from app.schemas import EmaPullbackTradeRecord
from app.strategy_compiler import compile_strategy_text

_CEO_TEXT = (
    "Buy when price closes above the 50 EMA, then wait for at least two bearish candles, "
    "then enter when price closes above the previous swing high. Place the stop at the "
    "Chandelier Stop and target 2R."
)


def _trade(*, outcome: str, entry_price: float = 100.0, stop_price: float = 98.0, exit_price: float | None, r_multiple: float) -> EmaPullbackTradeRecord:
    return EmaPullbackTradeRecord(
        symbol="TEST",
        direction="long",
        entryTimestamp="2024-01-01T00:00:00+00:00",
        entryPrice=entry_price,
        stopPrice=stop_price,
        targetPrice=104.0,
        exitPrice=exit_price,
        outcome=outcome,  # type: ignore[arg-type]
        rMultipleRealized=r_multiple,
        entrySession="new_york",
        regimeTrend="trending_up",
        regimeVolatility="normal",
        breakoutCandleExtended=False,
        breakoutCandleRangeRatio=1.0,
        maeR=0.0,
        mfeR=r_multiple,
        barsHeld=5,
    )


class TestApplyCostToTrades:
    def test_zero_cost_returns_the_same_trades_unchanged(self) -> None:
        trades = [_trade(outcome="win", exit_price=104.0, r_multiple=2.0)]
        assert _apply_cost_to_trades(trades, 0.0) == trades

    def test_an_open_trade_is_never_assigned_a_fabricated_cost(self) -> None:
        trades = [_trade(outcome="open", exit_price=None, r_multiple=0.0)]
        adjusted = _apply_cost_to_trades(trades, 25.0)
        assert adjusted[0].r_multiple_realized == 0.0

    def test_a_real_closed_trade_is_reduced_by_a_real_round_trip_cost_in_r_terms(self) -> None:
        # entry=100, stop=98 -> risk=2.0. 25 bps/leg round trip in price
        # terms: 100 * (25/10_000) * 2 = 0.5. In R terms: 0.5 / 2.0 = 0.25R.
        trades = [_trade(outcome="win", entry_price=100.0, stop_price=98.0, exit_price=104.0, r_multiple=2.0)]
        adjusted = _apply_cost_to_trades(trades, 25.0)
        assert adjusted[0].r_multiple_realized == 1.75

    def test_cost_never_flips_an_open_trade_into_a_closed_one(self) -> None:
        trades = [_trade(outcome="open", exit_price=None, r_multiple=0.0)]
        adjusted = _apply_cost_to_trades(trades, 25.0)
        assert adjusted[0].outcome == "open"


class TestCostScenariosLadder:
    def test_scenarios_are_monotonically_non_decreasing_in_cost(self) -> None:
        bps_values = [bps for _label, bps in COST_SCENARIOS]
        assert bps_values == sorted(bps_values)

    def test_base_scenario_is_zero_friction(self) -> None:
        assert COST_SCENARIOS[0][1] == 0.0


class TestRunCostSensitivityRefusesRatherThanGuesses:
    def test_an_invalid_definition_is_refused(self) -> None:
        definition = compile_strategy_text(name="x", source_text="Buy when the moon is full.")
        result = run_cost_sensitivity(definition, symbols=["AAPL"])
        assert result.verdict == "insufficient_data"
        assert result.scenarios == []


class TestIntegrationAgainstTheCeoWorkedExample:
    def test_real_expectancy_is_monotonically_non_increasing_as_cost_rises(self) -> None:
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        result = run_cost_sensitivity(definition, symbols=["AAPL", "MSFT", "SPY", "QQQ"], candles_per_symbol=6000)
        expectancies = [s.bucket.expectancy_r for s in result.scenarios]
        assert all(e is not None for e in expectancies)
        for earlier, later in zip(expectancies, expectancies[1:]):
            assert later <= earlier  # type: ignore[operator]

    def test_trade_count_never_changes_across_scenarios(self) -> None:
        # The whole point: cost never re-simulates which trades happened,
        # only what they were really worth after real friction.
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        result = run_cost_sensitivity(definition, symbols=["AAPL", "MSFT", "SPY", "QQQ"], candles_per_symbol=6000)
        trade_counts = {s.bucket.trade_count for s in result.scenarios}
        assert len(trade_counts) == 1

    def test_verdict_is_one_of_the_real_disclosed_outcomes_and_matches_the_real_base_vs_stressed_comparison(self) -> None:
        # Deliberately does not assert which outcome this run finds --
        # app/market_data.py's own real (mock) walk is seeded per
        # (symbol, timeframe) only, not per test, so this must never
        # assert a specific win rate/verdict (the same real house
        # convention TestRunEmaPullbackResearchIntegration already
        # documents in tests/test_ema_pullback_research.py). What IS
        # always true, by construction: `cost_sensitive` can only be
        # reached when the base scenario was itself real and profitable.
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        result = run_cost_sensitivity(definition, symbols=["AAPL", "MSFT", "SPY", "QQQ"], candles_per_symbol=6000)
        assert result.verdict in ("cost_resilient", "cost_sensitive", "insufficient_data")
        if result.verdict in ("cost_resilient", "cost_sensitive"):
            assert result.scenarios[0].bucket.expectancy_r is not None and result.scenarios[0].bucket.expectancy_r > 0
        if result.verdict == "cost_sensitive":
            assert result.scenarios[-1].bucket.expectancy_r is not None and result.scenarios[-1].bucket.expectancy_r <= 0
