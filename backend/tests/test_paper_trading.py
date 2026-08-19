"""Covers app/paper_trading.py's tick_paper_trading() — specifically the
CEO directive "Next Professional Trading Firm Phase," Priority 1
(Execution Realism) slippage wiring on its hold-duration close. No test
file previously existed for this module's own logic (it was only ever
exercised indirectly through app/nexus.py's integration); scope here is
deliberately limited to the new slippage behavior, not a full audit of
the pre-existing hold/close mechanics.
"""
from __future__ import annotations

from app.market_intelligence import default_market_intelligence_state
from app.paper_trading import MAX_HOLD_MINUTES, tick_paper_trading
from app.portfolio import default_portfolio, open_position
from app.schemas import PaperPortfolio, TimeState, WatchlistEntry


def _watchlist(symbol: str = "AAPL", price: float = 105.0) -> list[WatchlistEntry]:
    return [
        WatchlistEntry(symbol=symbol, name=symbol, lastPrice=price, dailyChangePct=0.0, status="queued", researchProgress=0.0, assignedAgent=None)
    ]


def _long_position_past_max_hold() -> PaperPortfolio:
    return open_position(
        default_portfolio(),
        position_id="pos-1",
        symbol="AAPL",
        price=100.0,
        opened_by="scout",
        confidence=90.0,
        opened_sim_minutes=0,
        side="buy",
    )


def test_forced_close_at_max_hold_applies_real_slippage_when_market_intelligence_is_supplied():
    # Past MAX_HOLD_MINUTES the close is unconditional (no random roll),
    # so this is deterministic: a long position closes via a sell, which
    # must fill at-or-below the signal price.
    portfolio = _long_position_past_max_hold()
    now = TimeState(day=0, hour=0, minute=MAX_HOLD_MINUTES + 1)
    updated, closed = tick_paper_trading(
        portfolio, _watchlist(price=105.0), ("scout", "atlas"), now, market_intelligence=default_market_intelligence_state()
    )
    assert len(closed) == 1
    assert closed[0].exit_price <= 105.0
    assert closed[0].exit_slippage_bps > 0.0


def test_forced_close_at_max_hold_fills_at_exactly_signal_price_without_market_intelligence():
    portfolio = _long_position_past_max_hold()
    now = TimeState(day=0, hour=0, minute=MAX_HOLD_MINUTES + 1)
    updated, closed = tick_paper_trading(portfolio, _watchlist(price=105.0), ("scout", "atlas"), now)
    assert len(closed) == 1
    assert closed[0].exit_price == 105.0
    assert closed[0].exit_slippage_bps == 0.0
