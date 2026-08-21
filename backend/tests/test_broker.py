"""Covers app/broker.py's ExecutionProvider adapter interface — added for
Design Bible Chapter 68 (Institutional Broker Management System). Scope
is deliberately limited to the interface seam: PaperExecutionProvider is
a thin delegate to the existing place_order()/tick_broker() free
functions, so these tests confirm the delegation is exact, not that the
underlying order-fill logic changed (that's already covered indirectly
through app/nexus.py's integration).
"""
from __future__ import annotations

from app.broker import (
    ExecutionProvider,
    PaperExecutionProvider,
    _select_execution_provider,
    execution_provider,
    place_order,
    tick_broker,
)
from app.market_intelligence import default_market_intelligence_state
from app.portfolio import default_portfolio, open_position
from app.risk_engine import default_risk_limits
from app.schemas import TimeState


def _time(day: int = 1, hour: int = 9, minute: int = 30) -> TimeState:
    return TimeState(day=day, hour=hour, minute=minute)


def test_execution_provider_is_an_abstract_interface():
    assert ExecutionProvider.__abstractmethods__ == frozenset({"place_order", "tick_broker"})


def test_default_execution_provider_singleton_is_paper():
    assert isinstance(execution_provider, PaperExecutionProvider)


def test_select_execution_provider_defaults_to_paper(monkeypatch):
    monkeypatch.delenv("EXECUTION_PROVIDER", raising=False)
    assert isinstance(_select_execution_provider(), PaperExecutionProvider)


def test_select_execution_provider_falls_back_for_unknown_value(monkeypatch, caplog):
    monkeypatch.setenv("EXECUTION_PROVIDER", "charles_schwab")
    provider = _select_execution_provider()
    assert isinstance(provider, PaperExecutionProvider)


def test_paper_execution_provider_place_order_matches_free_function():
    provider = PaperExecutionProvider()
    portfolio = default_portfolio()

    via_provider = provider.place_order(
        portfolio,
        order_id="order-1",
        symbol="AAPL",
        side="buy",
        order_type="market",
        quantity=10,
        price=100.0,
        placed_by="quant",
        reason="test",
        confidence=80.0,
    )
    via_function = place_order(
        portfolio,
        order_id="order-1",
        symbol="AAPL",
        side="buy",
        order_type="market",
        quantity=10,
        price=100.0,
        placed_by="quant",
        reason="test",
        confidence=80.0,
    )
    # createdAt is a real wall-clock timestamp, so two independent calls
    # can legitimately differ by a few microseconds — compare everything
    # else, which the delegation should reproduce exactly.
    assert len(via_provider.orders) == len(via_function.orders) == 1
    assert via_provider.orders[0].model_copy(update={"created_at": ""}) == via_function.orders[0].model_copy(
        update={"created_at": ""}
    )


def test_paper_execution_provider_tick_broker_matches_free_function():
    provider = PaperExecutionProvider()
    portfolio = default_portfolio()
    portfolio = provider.place_order(
        portfolio,
        order_id="order-1",
        symbol="AAPL",
        side="buy",
        order_type="market",
        quantity=10,
        price=100.0,
        placed_by="quant",
        reason="test",
        confidence=80.0,
    )
    prices = {"AAPL": 101.0}
    time_state = _time()

    via_provider, provider_trades = provider.tick_broker(portfolio, prices, time_state)
    via_function, function_trades = tick_broker(portfolio, prices, time_state)
    # filledAt is a real wall-clock timestamp on the resolved order — see
    # the note above.
    assert [o.model_copy(update={"filled_at": ""}) for o in via_provider.orders] == [
        o.model_copy(update={"filled_at": ""}) for o in via_function.orders
    ]
    assert [p.model_copy(update={"opened_at": ""}) for p in via_provider.positions] == [
        p.model_copy(update={"opened_at": ""}) for p in via_function.positions
    ]
    assert provider_trades == function_trades


def test_paper_execution_provider_fills_a_market_order():
    provider = PaperExecutionProvider()
    portfolio = default_portfolio()
    portfolio = provider.place_order(
        portfolio,
        order_id="order-1",
        symbol="AAPL",
        side="buy",
        order_type="market",
        quantity=10,
        price=100.0,
        placed_by="quant",
        reason="test",
        confidence=80.0,
    )
    updated, _ = provider.tick_broker(portfolio, {"AAPL": 105.0}, _time())
    assert len(updated.positions) == 1
    assert updated.positions[0].symbol == "AAPL"


def test_tick_broker_threads_risk_limits_into_a_real_exit_fill():
    """Prop-Firm Risk Intelligence Addendum, Piece 10b — an exit order
    filling through tick_broker() must produce a trade with a real
    distance-to-drawdown-ceiling snapshot when risk_limits is supplied,
    and None when it isn't (same optional-parameter honesty as
    app/portfolio.py's close_position() itself)."""
    portfolio = open_position(
        default_portfolio(),
        position_id="pos-1",
        symbol="AAPL",
        price=100.0,
        opened_by="scout",
        confidence=90.0,
        opened_sim_minutes=0,
    )
    portfolio = place_order(
        portfolio,
        order_id="order-tp",
        symbol="AAPL",
        side="sell",
        order_type="take_profit",
        quantity=portfolio.positions[0].quantity,
        price=110.0,
        placed_by="scout",
        reason="test",
        confidence=90.0,
        linked_position_id="pos-1",
    )

    updated_with_limits, trades_with_limits = tick_broker(portfolio, {"AAPL": 110.0}, _time(), default_risk_limits())
    assert len(trades_with_limits) == 1
    assert trades_with_limits[0].distance_to_drawdown_ceiling_before_pct == 20.0

    updated_without_limits, trades_without_limits = tick_broker(portfolio, {"AAPL": 110.0}, _time())
    assert len(trades_without_limits) == 1
    assert trades_without_limits[0].distance_to_drawdown_ceiling_before_pct is None


class TestSlippage:
    """CEO directive "Next Professional Trading Firm Phase," Priority 1
    (Execution Realism, app/execution_quality.py)."""

    def test_a_market_order_fills_worse_than_its_signal_price_when_market_intelligence_is_supplied(self) -> None:
        portfolio = place_order(
            default_portfolio(),
            order_id="order-1",
            symbol="AAPL",
            side="buy",
            order_type="market",
            quantity=10,
            price=100.0,
            placed_by="quant",
            reason="test",
            confidence=80.0,
        )
        updated, _ = tick_broker(portfolio, {"AAPL": 100.0}, _time(), None, default_market_intelligence_state())
        assert len(updated.positions) == 1
        # A buy's real fill must be at-or-above the signal price -- never
        # a fabricated favorable fill.
        assert updated.positions[0].entry_price >= 100.0
        assert updated.positions[0].entry_slippage_bps > 0.0

    def test_a_market_order_fills_exactly_at_signal_price_when_no_market_intelligence_is_supplied(self) -> None:
        portfolio = place_order(
            default_portfolio(),
            order_id="order-1",
            symbol="AAPL",
            side="buy",
            order_type="market",
            quantity=10,
            price=100.0,
            placed_by="quant",
            reason="test",
            confidence=80.0,
        )
        updated, _ = tick_broker(portfolio, {"AAPL": 100.0}, _time())
        assert updated.positions[0].entry_price == 100.0
        assert updated.positions[0].entry_slippage_bps == 0.0

    def test_a_limit_take_profit_order_fills_at_exactly_its_price_never_slipped(self) -> None:
        # A limit order's whole definition is "this price or better" --
        # real slippage never touches it, even with real
        # MarketIntelligenceState supplied.
        portfolio = open_position(
            default_portfolio(),
            position_id="pos-1",
            symbol="AAPL",
            price=100.0,
            opened_by="scout",
            confidence=90.0,
            opened_sim_minutes=0,
        )
        portfolio = place_order(
            portfolio,
            order_id="order-tp",
            symbol="AAPL",
            side="sell",
            order_type="take_profit",
            quantity=portfolio.positions[0].quantity,
            price=110.0,
            placed_by="scout",
            reason="test",
            confidence=90.0,
            linked_position_id="pos-1",
        )
        updated, trades = tick_broker(portfolio, {"AAPL": 110.0}, _time(), None, default_market_intelligence_state())
        assert len(trades) == 1
        assert trades[0].exit_price == 110.0
        assert trades[0].exit_slippage_bps == 0.0

    def test_a_triggered_stop_loss_fills_worse_than_its_trigger_price(self) -> None:
        # A stop order becomes a market order the moment it triggers, in
        # any real market -- real slippage applies to it, unlike a limit
        # order.
        portfolio = open_position(
            default_portfolio(),
            position_id="pos-1",
            symbol="AAPL",
            price=100.0,
            opened_by="scout",
            confidence=90.0,
            opened_sim_minutes=0,
        )
        portfolio = place_order(
            portfolio,
            order_id="order-sl",
            symbol="AAPL",
            side="sell",
            order_type="stop_loss",
            quantity=portfolio.positions[0].quantity,
            price=95.0,
            placed_by="scout",
            reason="test",
            confidence=90.0,
            linked_position_id="pos-1",
        )
        updated, trades = tick_broker(portfolio, {"AAPL": 95.0}, _time(), None, default_market_intelligence_state())
        assert len(trades) == 1
        # A sell's real fill must be at-or-below the trigger price.
        assert trades[0].exit_price <= 95.0
        assert trades[0].exit_slippage_bps > 0.0


class TestGapThroughFill:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism," Phase 7 — a triggered stop/stop_loss fills at
    the worse of its trigger price and the real current tick price, not
    always exactly at the trigger. No `market_intelligence` is supplied
    in these tests (None) so slippage stays exactly zero and every
    assertion isolates the gap-through effect alone."""

    def test_a_sell_stop_loss_that_gapped_past_its_trigger_fills_at_the_worse_real_price(self) -> None:
        portfolio = open_position(
            default_portfolio(), position_id="pos-1", symbol="AAPL", price=100.0, opened_by="scout", confidence=90.0, opened_sim_minutes=0,
        )
        portfolio = place_order(
            portfolio, order_id="order-sl", symbol="AAPL", side="sell", order_type="stop_loss",
            quantity=portfolio.positions[0].quantity, price=95.0, placed_by="scout", reason="test", confidence=90.0, linked_position_id="pos-1",
        )
        # The market already gapped well below the 95.0 stop by this tick.
        updated, trades = tick_broker(portfolio, {"AAPL": 80.0}, _time())
        assert len(trades) == 1
        assert trades[0].exit_price == 80.0
        assert trades[0].exit_slippage_bps == 0.0

    def test_a_buy_stop_that_gapped_past_its_trigger_fills_at_the_worse_real_price(self) -> None:
        portfolio = place_order(
            default_portfolio(), order_id="order-stop", symbol="AAPL", side="buy", order_type="stop",
            quantity=10, price=100.0, placed_by="quant", reason="test", confidence=80.0,
        )
        # The market already gapped well above the 100.0 breakout trigger.
        updated, _ = tick_broker(portfolio, {"AAPL": 120.0}, _time())
        assert len(updated.positions) == 1
        assert updated.positions[0].entry_price == 120.0
        assert updated.positions[0].entry_slippage_bps == 0.0

    def test_a_stop_loss_triggering_exactly_at_its_price_still_fills_at_the_trigger_price(self) -> None:
        # No gap at all -- unchanged, established behavior.
        portfolio = open_position(
            default_portfolio(), position_id="pos-1", symbol="AAPL", price=100.0, opened_by="scout", confidence=90.0, opened_sim_minutes=0,
        )
        portfolio = place_order(
            portfolio, order_id="order-sl", symbol="AAPL", side="sell", order_type="stop_loss",
            quantity=portfolio.positions[0].quantity, price=95.0, placed_by="scout", reason="test", confidence=90.0, linked_position_id="pos-1",
        )
        updated, trades = tick_broker(portfolio, {"AAPL": 95.0}, _time())
        assert len(trades) == 1
        assert trades[0].exit_price == 95.0

    def test_a_stop_loss_that_has_not_yet_triggered_is_unaffected_by_the_gap_fix(self) -> None:
        portfolio = open_position(
            default_portfolio(), position_id="pos-1", symbol="AAPL", price=100.0, opened_by="scout", confidence=90.0, opened_sim_minutes=0,
        )
        portfolio = place_order(
            portfolio, order_id="order-sl", symbol="AAPL", side="sell", order_type="stop_loss",
            quantity=portfolio.positions[0].quantity, price=95.0, placed_by="scout", reason="test", confidence=90.0, linked_position_id="pos-1",
        )
        updated, trades = tick_broker(portfolio, {"AAPL": 96.0}, _time())
        assert trades == []
        assert len(updated.positions) == 1

    def test_a_limit_order_is_never_affected_by_the_gap_fix_even_when_price_gapped_far_through_it(self) -> None:
        portfolio = place_order(
            default_portfolio(), order_id="order-limit", symbol="AAPL", side="buy", order_type="limit",
            quantity=10, price=100.0, placed_by="quant", reason="test", confidence=80.0,
        )
        # Price gapped well below the limit -- a limit buy still fills at
        # exactly its own price, never chasing the more favorable real price.
        updated, _ = tick_broker(portfolio, {"AAPL": 80.0}, _time())
        assert len(updated.positions) == 1
        assert updated.positions[0].entry_price == 100.0
