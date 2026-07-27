"""Covers app/portfolio.py's close_position() — added alongside v0.6.1's
Command Center monthly P&L view, which needs closed trades to carry an
accurate simulated-clock timestamp (see PaperTrade.closed_sim_minutes'
docstring in app/schemas.py for why this can't just reuse the real
wall-clock closed_at field)."""
from __future__ import annotations

from app.portfolio import close_position, default_portfolio, open_position


def _opened_portfolio(opened_sim_minutes: int = 1000):
    portfolio = open_position(
        default_portfolio(),
        position_id="pos-1",
        symbol="AAPL",
        price=100.0,
        opened_by="scout",
        confidence=90.0,
        opened_sim_minutes=opened_sim_minutes,
    )
    return portfolio


def test_close_position_stamps_sim_minutes_from_open_plus_duration():
    portfolio = _opened_portfolio(opened_sim_minutes=1000)
    updated, trade = close_position(
        portfolio,
        position_id="pos-1",
        exit_price=110.0,
        duration_minutes=45,
        reason="Target hit",
        market_conditions="Trending up",
        supporting_agents=["scout"],
        opposing_agents=[],
    )
    assert trade is not None
    assert trade.opened_sim_minutes == 1000
    assert trade.closed_sim_minutes == 1045
    assert trade.closed_sim_minutes - trade.opened_sim_minutes == trade.duration_minutes
    assert updated.positions == []


def test_close_position_missing_id_is_a_noop():
    portfolio = _opened_portfolio()
    updated, trade = close_position(
        portfolio,
        position_id="does-not-exist",
        exit_price=110.0,
        duration_minutes=45,
        reason="n/a",
        market_conditions="n/a",
        supporting_agents=[],
        opposing_agents=[],
    )
    assert trade is None
    assert updated is portfolio
