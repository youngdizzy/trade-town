"""Covers app/portfolio.py's close_position() — added alongside v0.6.1's
Command Center monthly P&L view, which needs closed trades to carry an
accurate simulated-clock timestamp (see PaperTrade.closed_sim_minutes'
docstring in app/schemas.py for why this can't just reuse the real
wall-clock closed_at field)."""
from __future__ import annotations

from app.portfolio import TRANSACTION_COST_BPS, close_position, default_portfolio, mark_to_market, open_position
from app.risk_engine import default_risk_limits
from app.schemas import PaperPosition


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


class TestDistanceToDrawdownCeiling:
    """Prop-Firm Risk Intelligence Addendum, Piece 10b — Requirement
    24's "distance to failure boundary before/after trade," for the
    primary portfolio's own real drawdown ceiling (RiskLimits.
    max_drawdown_pct). risk_limits is optional so a caller that hasn't
    threaded it through yet gets an honest None, never a fabricated
    value."""

    def test_none_when_risk_limits_not_supplied(self) -> None:
        portfolio = _opened_portfolio()
        _, trade = close_position(
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
        assert trade.distance_to_drawdown_ceiling_before_pct is None
        assert trade.distance_to_drawdown_ceiling_after_pct is None

    def test_fresh_portfolio_starts_with_the_full_ceiling_as_distance_before(self) -> None:
        limits = default_risk_limits()  # max_drawdown_pct default 20.0
        portfolio = _opened_portfolio()
        _, trade = close_position(
            portfolio,
            position_id="pos-1",
            exit_price=110.0,
            duration_minutes=45,
            reason="Target hit",
            market_conditions="Trending up",
            supporting_agents=["scout"],
            opposing_agents=[],
            risk_limits=limits,
        )
        assert trade is not None
        assert trade.distance_to_drawdown_ceiling_before_pct == 20.0

    def test_a_real_winning_trade_increases_distance_after_vs_before(self) -> None:
        limits = default_risk_limits()
        portfolio = _opened_portfolio()
        _, trade = close_position(
            portfolio,
            position_id="pos-1",
            exit_price=150.0,  # a real, sizeable gain
            duration_minutes=45,
            reason="Target hit",
            market_conditions="Trending up",
            supporting_agents=["scout"],
            opposing_agents=[],
            risk_limits=limits,
        )
        assert trade is not None
        assert trade.distance_to_drawdown_ceiling_before_pct == 20.0
        # A real gain never shrinks the distance to the ceiling — floored
        # at the ceiling itself once lifetime drawdown is already zero.
        assert trade.distance_to_drawdown_ceiling_after_pct == 20.0

    def test_a_real_losing_trade_already_underwater_shrinks_distance_after(self) -> None:
        limits = default_risk_limits()
        portfolio = _opened_portfolio()
        # Simulate the portfolio already carrying a real 5% lifetime
        # drawdown before this trade closes.
        portfolio = portfolio.model_copy(update={"total_pnl": -5000.0, "total_pnl_pct": -5.0, "cash_balance": portfolio.cash_balance - 5000.0})
        _, trade = close_position(
            portfolio,
            position_id="pos-1",
            exit_price=80.0,  # a real loss on top of the existing drawdown
            duration_minutes=45,
            reason="Stop hit",
            market_conditions="Trending down",
            supporting_agents=[],
            opposing_agents=["scout"],
            risk_limits=limits,
        )
        assert trade is not None
        assert trade.distance_to_drawdown_ceiling_before_pct == 15.0  # 20.0 - 5.0
        assert trade.distance_to_drawdown_ceiling_after_pct is not None
        assert trade.distance_to_drawdown_ceiling_after_pct < trade.distance_to_drawdown_ceiling_before_pct

    def test_distance_floors_at_zero_past_the_ceiling(self) -> None:
        limits = default_risk_limits()
        portfolio = _opened_portfolio()
        # Already past the real 20% ceiling before this trade even closes.
        portfolio = portfolio.model_copy(update={"total_pnl": -25000.0, "total_pnl_pct": -25.0, "cash_balance": portfolio.cash_balance - 25000.0})
        _, trade = close_position(
            portfolio,
            position_id="pos-1",
            exit_price=100.0,
            duration_minutes=45,
            reason="n/a",
            market_conditions="n/a",
            supporting_agents=[],
            opposing_agents=[],
            risk_limits=limits,
        )
        assert trade is not None
        assert trade.distance_to_drawdown_ceiling_before_pct == 0.0


class TestMaeMfe:
    """CEO Company Health + Live Market Realism directive, Feature 24 —
    a real running watermark of the worst/best unrealized_pnl_pct a
    position has actually shown, updated every mark_to_market() tick
    from the same real live prices unrealized_pnl already reads, and
    copied onto the closed PaperTrade the same way trading_style is."""

    def test_fresh_position_starts_at_zero(self) -> None:
        portfolio = _opened_portfolio()
        assert portfolio.positions[0].mae_pct == 0.0
        assert portfolio.positions[0].mfe_pct == 0.0

    def test_a_price_drop_moves_mae_but_not_mfe(self) -> None:
        portfolio = _opened_portfolio()
        portfolio = mark_to_market(portfolio, {"AAPL": 90.0})  # entry was 100.0
        pos = portfolio.positions[0]
        assert pos.mae_pct == -10.0
        assert pos.mfe_pct == 0.0

    def test_a_price_rise_moves_mfe_but_not_mae(self) -> None:
        portfolio = _opened_portfolio()
        portfolio = mark_to_market(portfolio, {"AAPL": 120.0})  # entry was 100.0
        pos = portfolio.positions[0]
        assert pos.mae_pct == 0.0
        assert pos.mfe_pct == 20.0

    def test_the_watermark_holds_its_own_real_extreme_after_a_partial_recovery(self) -> None:
        portfolio = _opened_portfolio()
        portfolio = mark_to_market(portfolio, {"AAPL": 85.0})  # drops to -15%
        portfolio = mark_to_market(portfolio, {"AAPL": 95.0})  # recovers to -5%, still a real loss
        pos = portfolio.positions[0]
        # The worst it actually got was -15% — a partial recovery never
        # erases the real extreme that already happened.
        assert pos.mae_pct == -15.0
        assert pos.mfe_pct == 0.0

    def test_both_watermarks_can_move_across_a_real_round_trip(self) -> None:
        portfolio = _opened_portfolio()
        portfolio = mark_to_market(portfolio, {"AAPL": 110.0})  # +10%
        portfolio = mark_to_market(portfolio, {"AAPL": 88.0})  # -12%
        pos = portfolio.positions[0]
        assert pos.mfe_pct == 10.0
        assert pos.mae_pct == -12.0

    def test_close_position_copies_the_real_watermark_onto_the_trade(self) -> None:
        portfolio = _opened_portfolio()
        portfolio = mark_to_market(portfolio, {"AAPL": 92.0})  # dips to -8% first
        portfolio = mark_to_market(portfolio, {"AAPL": 108.0})  # then rallies to +8%
        _, trade = close_position(
            portfolio,
            position_id="pos-1",
            exit_price=108.0,
            duration_minutes=45,
            reason="Target hit",
            market_conditions="Trending up",
            supporting_agents=["scout"],
            opposing_agents=[],
        )
        assert trade is not None
        assert trade.mae_pct == -8.0
        assert trade.mfe_pct == 8.0

    def test_a_legacy_position_with_no_watermark_still_closes_cleanly(self) -> None:
        legacy_position = PaperPosition(
            id="legacy-1",
            symbol="AAPL",
            side="buy",
            quantity=10.0,
            entryPrice=100.0,
            currentPrice=100.0,
            unrealizedPnl=0.0,
            unrealizedPnlPct=0.0,
            openedBy="scout",
            confidence=90.0,
            openedAt="2024-01-01T00:00:00+00:00",
            openedSimMinutes=0,
        )
        assert legacy_position.mae_pct == 0.0
        assert legacy_position.mfe_pct == 0.0
        portfolio = default_portfolio().model_copy(update={"positions": [legacy_position]})
        _, trade = close_position(
            portfolio,
            position_id="legacy-1",
            exit_price=105.0,
            duration_minutes=30,
            reason="n/a",
            market_conditions="n/a",
            supporting_agents=[],
            opposing_agents=[],
        )
        assert trade is not None
        assert trade.mae_pct == 0.0
        assert trade.mfe_pct == 0.0


class TestTransactionCost:
    """Quantitative Research & Intelligence System, Piece 5 (Execution
    Quant) — open_position()/close_position() now deduct a real, flat
    TRANSACTION_COST_BPS cost from the cash ledger on every fill. These
    tests hand-verify the exact dollar amounts, confirming this is a real
    deduction (affecting cash/pnl), not a display-only number."""

    def test_open_position_deducts_real_entry_cost_from_cash(self) -> None:
        portfolio = _opened_portfolio()
        # Auto-sized: budget = 100_000 * 0.05 = 5_000; quantity = 50.0 @ $100.
        notional = 50.0 * 100.0
        entry_cost = round(notional * (TRANSACTION_COST_BPS / 10_000), 2)
        assert entry_cost == 2.5
        assert portfolio.positions[0].entry_cost_usd == entry_cost
        assert portfolio.cash_balance == 100_000.0 - notional - entry_cost

    def test_open_position_refuses_when_cash_cannot_cover_notional_plus_cost(self) -> None:
        # Exact notional match, explicit quantity — no room left for the
        # entry cost on top, so this must no-op, not go cash-negative.
        thin_portfolio = default_portfolio().model_copy(update={"cash_balance": 1_000.0})
        updated = open_position(
            thin_portfolio,
            position_id="pos-thin",
            symbol="AAPL",
            price=100.0,
            opened_by="scout",
            confidence=90.0,
            opened_sim_minutes=0,
            quantity=10.0,  # 10 * 100 == cash_balance exactly, cost pushes it over
        )
        assert updated is thin_portfolio

    def test_close_position_deducts_real_exit_cost_and_nets_pnl(self) -> None:
        portfolio = _opened_portfolio()
        _, trade = close_position(
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
        exit_cost = round(50.0 * 110.0 * (TRANSACTION_COST_BPS / 10_000), 2)
        assert exit_cost == 2.75
        # Hand-computed: gross_pnl = (110-100)*50 = 500; total_cost =
        # 2.5 + 2.75 = 5.25; net pnl = 494.75; pnl_pct on the $5,000
        # committed = 9.895%.
        assert trade.transaction_cost_usd == 5.25
        assert trade.pnl == 494.75
        assert trade.pnl_pct == 9.895

    def test_pre_piece_5_position_with_no_entry_cost_still_closes_cleanly(self) -> None:
        # A position "saved" before this piece existed — entry_cost_usd
        # defaults to 0.0 rather than failing to load or fabricating a
        # retroactive cost for a fill that never charged one.
        legacy_position = PaperPosition(
            id="legacy-1",
            symbol="AAPL",
            side="buy",
            quantity=10.0,
            entryPrice=100.0,
            currentPrice=100.0,
            unrealizedPnl=0.0,
            unrealizedPnlPct=0.0,
            openedBy="scout",
            confidence=90.0,
            openedAt="2024-01-01T00:00:00+00:00",
            openedSimMinutes=0,
        )
        assert legacy_position.entry_cost_usd == 0.0
        portfolio = default_portfolio().model_copy(update={"positions": [legacy_position]})
        _, trade = close_position(
            portfolio,
            position_id="legacy-1",
            exit_price=105.0,
            duration_minutes=30,
            reason="n/a",
            market_conditions="n/a",
            supporting_agents=[],
            opposing_agents=[],
        )
        assert trade is not None
        exit_cost = round(10.0 * 105.0 * (TRANSACTION_COST_BPS / 10_000), 2)
        assert trade.transaction_cost_usd == exit_cost  # entry side contributed 0.0
