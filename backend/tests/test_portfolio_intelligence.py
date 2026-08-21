"""Covers app/portfolio_intelligence.py — v0.7 Feature 56, Enterprise
Portfolio Intelligence. Every read here must trace back to a real
PaperPortfolio position/trade or a real candle-derived correlation —
never a fabricated relationship or score (see the module's own
docstring for the full honesty boundary).
"""
from __future__ import annotations

from app.market_data import Candle, MarketDataProvider, Quote
from app.portfolio_intelligence import (
    CORRELATION_CLUSTER_THRESHOLD,
    _capital_efficiency,
    _category_exposure,
    _correlation_pairs,
    _exposure_summary,
    _heat,
    _opportunity_cost,
    _strategy_exposure,
    count_correlated_positions,
    pearson_correlation,
    returns,
    compute_portfolio_intelligence,
)
from app.schemas import PaperPortfolio, PaperPosition, PaperTrade


class _FakeProvider(MarketDataProvider):
    """A test double whose candle series per symbol is fully controlled,
    unlike MockMarketDataProvider's real-but-random walk — needed to
    construct known-correlated / known-uncorrelated return series."""

    def __init__(self, closes_by_symbol: dict[str, list[float]]) -> None:
        self._closes_by_symbol = closes_by_symbol

    def get_quote(self, symbol: str) -> Quote:
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        closes = self._closes_by_symbol.get(symbol)
        if closes is None:
            raise ValueError(f"no fixture data for {symbol!r}")
        return [
            Candle(symbol=symbol, timeframe=timeframe, timestamp=f"2026-01-01T{i:02d}:00:00Z", open=c, high=c, low=c, close=c, volume=1000.0, data_status="simulated")
            for i, c in enumerate(closes)
        ]


def _position(
    *,
    position_id: str = "pos-1",
    symbol: str = "AAPL",
    quantity: float = 10.0,
    current_price: float = 100.0,
    side: str = "buy",
    strategy_id: str | None = None,
) -> PaperPosition:
    return PaperPosition(
        id=position_id,
        symbol=symbol,
        side=side,  # type: ignore[arg-type]
        quantity=quantity,
        entryPrice=100.0,
        currentPrice=current_price,
        unrealizedPnl=(current_price - 100.0) * quantity,
        unrealizedPnlPct=(current_price - 100.0) / 100.0 * 100,
        openedBy="sentinel",  # type: ignore[arg-type]
        confidence=80.0,
        openedAt="2026-01-01T00:00:00Z",
        openedSimMinutes=0,
        strategyId=strategy_id,
    )


def _trade(*, trade_id: str = "trade-1", symbol: str = "AAPL", pnl: float = 10.0, entry_price: float = 100.0, quantity: float = 10.0, duration_minutes: int = 60) -> PaperTrade:
    return PaperTrade(
        id=trade_id,
        symbol=symbol,
        side="buy",  # type: ignore[arg-type]
        quantity=quantity,
        entryPrice=entry_price,
        exitPrice=entry_price + pnl / quantity,
        pnl=pnl,
        pnlPct=pnl / (entry_price * quantity) * 100 if entry_price else 0.0,
        durationMinutes=duration_minutes,
        confidence=80.0,
        reason="test reason",
        marketConditions="test conditions",
        openedAt="2026-01-01T00:00:00Z",
        closedAt="2026-01-01T01:00:00Z",
    )


def _portfolio(*, cash_balance: float = 90000.0, starting_balance: float = 100000.0, positions: list[PaperPosition] | None = None, trade_history: list[PaperTrade] | None = None) -> PaperPortfolio:
    positions = positions or []
    total_pnl = sum(p.unrealized_pnl for p in positions)
    equity = cash_balance + sum(p.quantity * p.current_price for p in positions)
    return PaperPortfolio(
        cashBalance=cash_balance,
        startingBalance=starting_balance,
        positions=positions,
        orders=[],
        tradeHistory=trade_history or [],
        totalPnl=total_pnl,
        totalPnlPct=(equity - starting_balance) / starting_balance * 100 if starting_balance else 0.0,
        winCount=0,
        lossCount=0,
    )


class TestPearson:
    def test_perfectly_correlated_series_returns_one(self) -> None:
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert pearson_correlation(a, a) == 1.0

    def test_perfectly_inverse_series_returns_negative_one(self) -> None:
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        b = [5.0, 4.0, 3.0, 2.0, 1.0]
        assert round(pearson_correlation(a, b), 6) == -1.0

    def test_fewer_than_three_points_returns_zero_rather_than_a_fake_read(self) -> None:
        assert pearson_correlation([1.0, 2.0], [1.0, 2.0]) == 0.0

    def test_zero_variance_series_returns_zero_not_a_crash(self) -> None:
        assert pearson_correlation([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) == 0.0


class TestReturns:
    def test_computes_bar_to_bar_pct_change(self) -> None:
        assert returns([100.0, 110.0, 99.0]) == [0.1, -0.1]

    def test_empty_and_single_price_series_return_empty(self) -> None:
        assert returns([]) == []
        assert returns([100.0]) == []


class TestCategoryExposure:
    def test_empty_portfolio_returns_no_exposure(self) -> None:
        assert _category_exposure(_portfolio(), equity=100000.0) == []

    def test_groups_by_real_symbol_category_and_sums_value(self) -> None:
        portfolio = _portfolio(positions=[_position(position_id="p1", symbol="AAPL", quantity=10.0, current_price=100.0), _position(position_id="p2", symbol="MSFT", quantity=5.0, current_price=200.0)])
        exposures = _category_exposure(portfolio, equity=100000.0)
        categories = {e.category: e for e in exposures}
        assert categories["company"].value == 1000.0
        assert categories["company"].position_count == 1
        assert categories["stock"].value == 1000.0

    def test_multiple_positions_in_the_same_category_are_combined(self) -> None:
        portfolio = _portfolio(positions=[_position(position_id="p1", symbol="SPY", quantity=10.0, current_price=100.0), _position(position_id="p2", symbol="QQQ", quantity=10.0, current_price=100.0)])
        exposures = _category_exposure(portfolio, equity=100000.0)
        index_exposure = next(e for e in exposures if e.category == "index")
        etf_exposure = next(e for e in exposures if e.category == "etf")
        assert index_exposure.value == 1000.0
        assert etf_exposure.value == 1000.0

    def test_unknown_symbol_not_in_symbol_category_is_skipped(self) -> None:
        portfolio = _portfolio(positions=[_position(symbol="UNKNOWN-XYZ")])
        assert _category_exposure(portfolio, equity=100000.0) == []

    def test_sorted_by_pct_of_equity_descending(self) -> None:
        portfolio = _portfolio(positions=[_position(position_id="p1", symbol="AAPL", quantity=1.0, current_price=100.0), _position(position_id="p2", symbol="MSFT", quantity=50.0, current_price=100.0)])
        exposures = _category_exposure(portfolio, equity=100000.0)
        assert exposures[0].category == "stock"
        assert exposures[0].pct_of_equity >= exposures[1].pct_of_equity

    def test_zero_equity_reports_zero_pct_rather_than_dividing_by_zero(self) -> None:
        portfolio = _portfolio(positions=[_position()])
        exposures = _category_exposure(portfolio, equity=0.0)
        assert exposures[0].pct_of_equity == 0.0


class TestCorrelationPairs:
    def test_fewer_than_two_symbols_returns_empty(self) -> None:
        portfolio = _portfolio(positions=[_position(symbol="AAPL")])
        provider = _FakeProvider({})
        assert _correlation_pairs(portfolio, provider) == []

    def test_known_correlated_pair_is_reported(self) -> None:
        closes = [100.0 + i for i in range(10)]
        portfolio = _portfolio(positions=[_position(position_id="p1", symbol="AAPL"), _position(position_id="p2", symbol="MSFT")])
        provider = _FakeProvider({"AAPL": closes, "MSFT": [c * 2 for c in closes]})
        pairs = _correlation_pairs(portfolio, provider)
        assert len(pairs) == 1
        assert pairs[0].symbol_a == "AAPL"
        assert pairs[0].symbol_b == "MSFT"
        assert pairs[0].correlation >= CORRELATION_CLUSTER_THRESHOLD
        assert pairs[0].direction == "positive"

    def test_known_inversely_correlated_pair_reports_negative_direction(self) -> None:
        closes = [100.0 + i for i in range(10)]
        # A reciprocal price path — not a mirrored arithmetic sequence,
        # whose *returns* (not raw prices) don't actually anti-correlate —
        # produces genuinely inverse bar-to-bar returns.
        inverse_closes = [10000.0 / c for c in closes]
        portfolio = _portfolio(positions=[_position(position_id="p1", symbol="AAPL"), _position(position_id="p2", symbol="MSFT")])
        provider = _FakeProvider({"AAPL": closes, "MSFT": inverse_closes})
        pairs = _correlation_pairs(portfolio, provider)
        assert len(pairs) == 1
        assert pairs[0].direction == "negative"

    def test_uncorrelated_pair_below_threshold_is_not_reported(self) -> None:
        # Two independently-drifting price paths (correlation ~0.22 per
        # statistics.correlation, well under CORRELATION_CLUSTER_THRESHOLD).
        aapl = [100.0, 100.84, 97.96, 96.64, 95.04, 96.38, 97.41, 99.7, 97.23, 96.77]
        msft = [50.0, 49.71, 48.82, 47.88, 47.15, 47.89, 47.17, 46.84, 47.36, 47.47]
        portfolio = _portfolio(positions=[_position(position_id="p1", symbol="AAPL"), _position(position_id="p2", symbol="MSFT")])
        provider = _FakeProvider({"AAPL": aapl, "MSFT": msft})
        pairs = _correlation_pairs(portfolio, provider)
        assert pairs == []

    def test_symbol_the_provider_cannot_price_is_skipped_not_crashed(self) -> None:
        portfolio = _portfolio(positions=[_position(position_id="p1", symbol="AAPL"), _position(position_id="p2", symbol="MSFT")])
        provider = _FakeProvider({"AAPL": [100.0 + i for i in range(10)]})
        assert _correlation_pairs(portfolio, provider) == []


class TestCountCorrelatedPositions:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism," Phase 4 — the real, pre-proposal-stage
    correlation read app/opportunity_gatekeeper.py's new gate consumes."""

    def test_a_real_correlated_held_position_is_counted(self) -> None:
        closes = [100.0 + i for i in range(10)]
        portfolio = _portfolio(positions=[_position(position_id="p1", symbol="MSFT")])
        provider = _FakeProvider({"AAPL": closes, "MSFT": [c * 2 for c in closes]})
        assert count_correlated_positions("AAPL", portfolio, provider) == 1

    def test_an_uncorrelated_held_position_is_not_counted(self) -> None:
        aapl = [100.0, 100.84, 97.96, 96.64, 95.04, 96.38, 97.41, 99.7, 97.23, 96.77]
        msft = [50.0, 49.71, 48.82, 47.88, 47.15, 47.89, 47.17, 46.84, 47.36, 47.47]
        portfolio = _portfolio(positions=[_position(position_id="p1", symbol="MSFT")])
        provider = _FakeProvider({"AAPL": aapl, "MSFT": msft})
        assert count_correlated_positions("AAPL", portfolio, provider) == 0

    def test_counts_multiple_real_correlated_positions(self) -> None:
        closes = [100.0 + i for i in range(10)]
        portfolio = _portfolio(
            positions=[
                _position(position_id="p1", symbol="MSFT"),
                _position(position_id="p2", symbol="QQQ"),
            ]
        )
        provider = _FakeProvider({"AAPL": closes, "MSFT": [c * 2 for c in closes], "QQQ": [c * 3 for c in closes]})
        assert count_correlated_positions("AAPL", portfolio, provider) == 2

    def test_the_candidate_symbol_itself_is_never_counted_against_itself(self) -> None:
        closes = [100.0 + i for i in range(10)]
        portfolio = _portfolio(positions=[_position(position_id="p1", symbol="AAPL")])
        provider = _FakeProvider({"AAPL": closes})
        assert count_correlated_positions("AAPL", portfolio, provider) == 0

    def test_no_real_candle_history_for_the_candidate_returns_zero_not_a_crash(self) -> None:
        portfolio = _portfolio(positions=[_position(position_id="p1", symbol="MSFT")])
        provider = _FakeProvider({"MSFT": [100.0 + i for i in range(10)]})
        assert count_correlated_positions("AAPL", portfolio, provider) == 0

    def test_no_real_candle_history_for_a_held_symbol_is_skipped_not_crashed(self) -> None:
        closes = [100.0 + i for i in range(10)]
        portfolio = _portfolio(positions=[_position(position_id="p1", symbol="MSFT")])
        provider = _FakeProvider({"AAPL": closes})
        assert count_correlated_positions("AAPL", portfolio, provider) == 0

    def test_empty_portfolio_returns_zero(self) -> None:
        closes = [100.0 + i for i in range(10)]
        provider = _FakeProvider({"AAPL": closes})
        assert count_correlated_positions("AAPL", _portfolio(positions=[]), provider) == 0


class TestHeat:
    def test_empty_portfolio_is_cool_with_zero_readings(self) -> None:
        heat = _heat(_portfolio(positions=[]), equity=100000.0, category_exposure=[])
        assert heat.tier == "cool"
        assert heat.total_capital_at_risk_pct == 0.0
        assert heat.hottest_category is None

    def test_zero_equity_is_cool_rather_than_dividing_by_zero(self) -> None:
        heat = _heat(_portfolio(positions=[_position()]), equity=0.0, category_exposure=[])
        assert heat.tier == "cool"

    def test_tier_thresholds_from_cool_to_overheated(self) -> None:
        for capital_at_risk_pct, expected_tier in [(10.0, "cool"), (30.0, "warm"), (60.0, "hot"), (80.0, "overheated")]:
            equity = 100000.0
            position_value = equity * capital_at_risk_pct / 100
            portfolio = _portfolio(positions=[_position(quantity=1.0, current_price=position_value)])
            heat = _heat(portfolio, equity=equity, category_exposure=[])
            assert heat.tier == expected_tier, f"{capital_at_risk_pct}% should be {expected_tier}, got {heat.tier}"

    def test_unrealized_drawdown_only_reports_when_portfolio_is_net_negative(self) -> None:
        losing = _portfolio(positions=[_position(current_price=90.0)])
        losing = losing.model_copy(update={"total_pnl_pct": -5.0})
        heat = _heat(losing, equity=100000.0, category_exposure=[])
        assert heat.unrealized_drawdown_pct == 5.0

        winning = _portfolio(positions=[_position(current_price=110.0)])
        winning = winning.model_copy(update={"total_pnl_pct": 5.0})
        heat = _heat(winning, equity=100000.0, category_exposure=[])
        assert heat.unrealized_drawdown_pct == 0.0

    def test_hottest_category_reads_the_top_exposure(self) -> None:
        portfolio = _portfolio(positions=[_position(symbol="AAPL", quantity=50.0, current_price=100.0)])
        exposure = _category_exposure(portfolio, equity=100000.0)
        heat = _heat(portfolio, equity=100000.0, category_exposure=exposure)
        assert heat.hottest_category == "company"
        assert heat.hottest_category_pct == exposure[0].pct_of_equity


class TestCapitalEfficiency:
    def test_no_trade_history_returns_honest_zero(self) -> None:
        efficiency = _capital_efficiency(_portfolio(trade_history=[]))
        assert efficiency.profit_per_dollar == 0.0
        assert efficiency.trades_measured == 0

    def test_averages_profit_per_dollar_across_real_trades(self) -> None:
        trades = [_trade(trade_id="t1", pnl=10.0, entry_price=100.0, quantity=10.0), _trade(trade_id="t2", pnl=-20.0, entry_price=100.0, quantity=10.0)]
        efficiency = _capital_efficiency(_portfolio(trade_history=trades))
        assert efficiency.trades_measured == 2
        assert efficiency.profit_per_dollar == round((0.01 + -0.02) / 2, 4)

    def test_zero_capital_locked_trade_is_excluded_not_a_division_by_zero(self) -> None:
        trades = [_trade(trade_id="t1", pnl=10.0, entry_price=0.0, quantity=10.0)]
        efficiency = _capital_efficiency(_portfolio(trade_history=trades))
        assert efficiency.trades_measured == 0
        assert efficiency.profit_per_dollar == 0.0

    def test_profit_per_dollar_hour_normalizes_by_real_hold_duration(self) -> None:
        fast = _capital_efficiency(_portfolio(trade_history=[_trade(pnl=10.0, entry_price=100.0, quantity=10.0, duration_minutes=60)]))
        slow = _capital_efficiency(_portfolio(trade_history=[_trade(pnl=10.0, entry_price=100.0, quantity=10.0, duration_minutes=600)]))
        assert fast.profit_per_dollar_hour > slow.profit_per_dollar_hour


class TestOpportunityCost:
    def test_high_cash_with_pending_proposals_names_the_real_count(self) -> None:
        text = _opportunity_cost(cash_pct_of_equity=80.0, pending_proposal_count=3)
        assert "3 real trade proposal" in text

    def test_high_cash_with_no_pending_proposals_reads_as_deliberate_patience(self) -> None:
        text = _opportunity_cost(cash_pct_of_equity=90.0, pending_proposal_count=0)
        assert "deliberate patience" in text

    def test_low_cash_warns_about_little_room_to_act(self) -> None:
        text = _opportunity_cost(cash_pct_of_equity=5.0, pending_proposal_count=0)
        assert "little room" in text


class TestExposureSummary:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism" — real long/short/net/gross exposure, the one
    concept the directive's own audit confirmed grep-zero anywhere in
    this codebase before this pass."""

    def test_all_long_reads_gross_equals_net_equals_long_value(self) -> None:
        positions = [_position(position_id="p1", symbol="AAPL", quantity=10.0, current_price=100.0, side="buy")]
        portfolio = _portfolio(cash_balance=99000.0, positions=positions)
        exposure = _exposure_summary(portfolio, equity=100000.0)
        assert exposure.long_value == 1000.0
        assert exposure.short_value == 0.0
        assert exposure.net_exposure == 1000.0
        assert exposure.gross_exposure == 1000.0
        assert exposure.long_position_count == 1
        assert exposure.short_position_count == 0

    def test_offsetting_long_and_short_reduces_net_but_not_gross(self) -> None:
        positions = [
            _position(position_id="p1", symbol="AAPL", quantity=10.0, current_price=100.0, side="buy"),
            _position(position_id="p2", symbol="MSFT", quantity=10.0, current_price=100.0, side="sell"),
        ]
        portfolio = _portfolio(cash_balance=98000.0, positions=positions)
        exposure = _exposure_summary(portfolio, equity=100000.0)
        assert exposure.long_value == 1000.0
        assert exposure.short_value == 1000.0
        # Net exposure — a real directional bias reading — cancels out...
        assert exposure.net_exposure == 0.0
        # ...but gross exposure — total capital genuinely at work — does not.
        assert exposure.gross_exposure == 2000.0

    def test_pct_fields_are_real_percentages_of_equity(self) -> None:
        positions = [_position(position_id="p1", quantity=10.0, current_price=100.0, side="buy")]
        portfolio = _portfolio(cash_balance=99000.0, positions=positions)
        exposure = _exposure_summary(portfolio, equity=100000.0)
        assert exposure.gross_exposure_pct == 1.0
        assert exposure.net_exposure_pct == 1.0

    def test_zero_equity_never_divides_by_zero(self) -> None:
        exposure = _exposure_summary(_portfolio(positions=[]), equity=0.0)
        assert exposure.gross_exposure_pct == 0.0
        assert exposure.net_exposure_pct == 0.0

    def test_empty_portfolio_reads_all_real_zeros(self) -> None:
        exposure = _exposure_summary(_portfolio(positions=[]), equity=100000.0)
        assert exposure.long_value == 0.0
        assert exposure.short_value == 0.0
        assert exposure.net_exposure == 0.0
        assert exposure.gross_exposure == 0.0


class TestStrategyExposure:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism" — the live analogue of compute_strategy_
    performance() (closed trades only). Groups OPEN positions by
    PaperPosition.strategy_id."""

    def test_groups_open_positions_by_real_strategy_id(self) -> None:
        positions = [
            _position(position_id="p1", symbol="AAPL", quantity=10.0, current_price=100.0, strategy_id="strategy-momentum"),
            _position(position_id="p2", symbol="MSFT", quantity=5.0, current_price=100.0, strategy_id="strategy-momentum"),
            _position(position_id="p3", symbol="GLD", quantity=1.0, current_price=100.0, strategy_id="strategy-value"),
        ]
        portfolio = _portfolio(positions=positions)
        reads = _strategy_exposure(portfolio, equity=100000.0)
        by_id = {r.strategy_id: r for r in reads}
        assert by_id["strategy-momentum"].position_count == 2
        assert by_id["strategy-momentum"].value == 1500.0
        assert by_id["strategy-value"].position_count == 1

    def test_a_position_with_no_strategy_selected_is_its_own_honest_bucket(self) -> None:
        positions = [
            _position(position_id="p1", symbol="AAPL", quantity=10.0, current_price=100.0, strategy_id="strategy-momentum"),
            _position(position_id="p2", symbol="MSFT", quantity=10.0, current_price=100.0, strategy_id=None),
        ]
        portfolio = _portfolio(positions=positions)
        reads = _strategy_exposure(portfolio, equity=100000.0)
        by_id = {r.strategy_id: r for r in reads}
        assert None in by_id
        assert by_id[None].position_count == 1
        assert by_id[None].value == 1000.0
        # The unattributed bucket is never folded into the real strategy's numbers.
        assert by_id["strategy-momentum"].value == 1000.0

    def test_long_and_short_value_are_tracked_separately_within_a_strategy(self) -> None:
        positions = [
            _position(position_id="p1", symbol="AAPL", quantity=10.0, current_price=100.0, side="buy", strategy_id="strategy-momentum"),
            _position(position_id="p2", symbol="MSFT", quantity=5.0, current_price=100.0, side="sell", strategy_id="strategy-momentum"),
        ]
        portfolio = _portfolio(positions=positions)
        reads = _strategy_exposure(portfolio, equity=100000.0)
        read = next(r for r in reads if r.strategy_id == "strategy-momentum")
        assert read.long_value == 1000.0
        assert read.short_value == 500.0
        assert read.value == 1500.0

    def test_empty_portfolio_produces_no_reads(self) -> None:
        assert _strategy_exposure(_portfolio(positions=[]), equity=100000.0) == []

    def test_reads_sorted_by_value_descending(self) -> None:
        positions = [
            _position(position_id="p1", symbol="AAPL", quantity=1.0, current_price=100.0, strategy_id="strategy-small"),
            _position(position_id="p2", symbol="MSFT", quantity=10.0, current_price=100.0, strategy_id="strategy-big"),
        ]
        portfolio = _portfolio(positions=positions)
        reads = _strategy_exposure(portfolio, equity=100000.0)
        assert [r.strategy_id for r in reads] == ["strategy-big", "strategy-small"]

    def test_balanced_cash_has_no_immediate_concern(self) -> None:
        text = _opportunity_cost(cash_pct_of_equity=40.0, pending_proposal_count=0)
        assert "no immediate opportunity-cost concern" in text


class TestComputePortfolioIntelligence:
    def test_end_to_end_with_open_correlated_positions(self) -> None:
        closes = [100.0 + i for i in range(10)]
        positions = [_position(position_id="p1", symbol="AAPL", quantity=10.0, current_price=110.0), _position(position_id="p2", symbol="MSFT", quantity=10.0, current_price=110.0)]
        portfolio = _portfolio(cash_balance=50000.0, positions=positions, trade_history=[_trade()])
        provider = _FakeProvider({"AAPL": closes, "MSFT": [c * 2 for c in closes]})

        result = compute_portfolio_intelligence(portfolio, provider, pending_proposal_count=1)

        assert result.category_exposure != []
        assert result.correlation_pairs != []
        assert result.capital_efficiency.trades_measured == 1
        assert 0.0 <= result.cash_pct_of_equity <= 100.0
        assert result.cash_pct_of_equity + result.deployed_pct_of_equity == 100.0

    def test_all_cash_portfolio_reports_empty_exposure_and_correlation(self) -> None:
        provider = _FakeProvider({})
        result = compute_portfolio_intelligence(_portfolio(positions=[]), provider, pending_proposal_count=0)
        assert result.category_exposure == []
        assert result.correlation_pairs == []
        assert result.cash_pct_of_equity == 100.0
        assert result.deployed_pct_of_equity == 0.0
