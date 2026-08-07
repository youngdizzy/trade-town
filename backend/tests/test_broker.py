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
from app.portfolio import default_portfolio
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
