"""Covers app/analytics.py's compute_performance_snapshot() period filtering
(v0.6.1) — before this, every period label (daily/weekly/monthly/all_time)
computed identical all-time totals; this checks that a "monthly" snapshot
now genuinely excludes trades closed in a prior simulated month, and that
"all_time" stays deliberately unfiltered."""
from __future__ import annotations

from app.analytics import compute_performance_snapshot
from app.schemas import PaperPortfolio, PaperTrade, TimeState


def _trade(*, pnl: float, closed_sim_minutes: int, pnl_pct: float = 1.0) -> PaperTrade:
    return PaperTrade(
        id=f"trade-{closed_sim_minutes}",
        symbol="AAPL",
        side="buy",
        quantity=1.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl,
        pnl=pnl,
        pnlPct=pnl_pct,
        durationMinutes=30,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        supportingAgents=["scout"],
        opposingAgents=[],
        openedAt="2024-01-01T00:00:00+00:00",
        closedAt="2024-01-01T00:00:00+00:00",
        openedSimMinutes=closed_sim_minutes - 30,
        closedSimMinutes=closed_sim_minutes,
    )


def _portfolio(trades: list[PaperTrade]) -> PaperPortfolio:
    win_count = sum(1 for t in trades if t.pnl > 0)
    loss_count = len(trades) - win_count
    total_pnl = sum(t.pnl for t in trades)
    return PaperPortfolio(
        cashBalance=100_000.0 + total_pnl,
        startingBalance=100_000.0,
        positions=[],
        orders=[],
        tradeHistory=trades,
        totalPnl=total_pnl,
        totalPnlPct=total_pnl / 100_000.0 * 100,
        winCount=win_count,
        lossCount=loss_count,
    )


def test_monthly_snapshot_excludes_trades_from_a_prior_month():
    # Month 1 = sim days 1-30 (minutes 1440-43200); month 2 starts day 31.
    month1_trade = _trade(pnl=500.0, closed_sim_minutes=10 * 1440)  # day 10
    month2_trade = _trade(pnl=-200.0, closed_sim_minutes=35 * 1440)  # day 35
    portfolio = _portfolio([month1_trade, month2_trade])
    now = TimeState(day=40, hour=20, minute=0)  # still inside month 2 (days 31-60)

    snapshot = compute_performance_snapshot("monthly", portfolio, [], now)

    assert snapshot.max_drawdown_pct >= 0  # sanity: month 2's own losing trade, not month 1's win
    # Only month 2's trade should count toward this month's win/loss split.
    assert snapshot.win_rate == 0.0  # the one trade in month 2 was a loss


def test_all_time_snapshot_stays_fully_cumulative():
    trades = [_trade(pnl=500.0, closed_sim_minutes=10 * 1440), _trade(pnl=-200.0, closed_sim_minutes=35 * 1440)]
    portfolio = _portfolio(trades)
    now = TimeState(day=40, hour=20, minute=0)

    snapshot = compute_performance_snapshot("all_time", portfolio, [], now)

    assert snapshot.return_pct == portfolio.total_pnl_pct
    assert snapshot.win_rate == 50.0  # one win, one loss across all time


class TestRealSharpeSortino:
    """Quantitative Research & Intelligence System, Piece 3 — real
    per-trade Sharpe/Sortino computed from PaperPortfolio.trade_history's
    own real pnl_pct sequence (mean/population-stdev; mean/downside-
    deviation), risk-free rate assumed 0. Never the old placeholder
    return/drawdown ratio, and Sortino is never a fixed multiple of
    Sharpe (the old `sharpe * 1.1` formula) — they diverge with real
    downside-only data."""

    def test_zero_trades_is_neutral_zero_not_a_crash(self) -> None:
        portfolio = _portfolio([])
        now = TimeState(day=40, hour=20, minute=0)
        snapshot = compute_performance_snapshot("all_time", portfolio, [], now)
        assert snapshot.sharpe_ratio == 0.0
        assert snapshot.sortino_ratio == 0.0

    def test_single_trade_has_undefined_stdev_and_is_zero(self) -> None:
        trades = [_trade(pnl=100.0, closed_sim_minutes=1440, pnl_pct=2.0)]
        portfolio = _portfolio(trades)
        now = TimeState(day=40, hour=20, minute=0)
        snapshot = compute_performance_snapshot("all_time", portfolio, [], now)
        # A single real return has no real variance to divide by — must
        # not fabricate a ratio from an undefined stdev.
        assert snapshot.sharpe_ratio == 0.0

    def test_real_formula_matches_hand_computed_population_stats(self) -> None:
        # Real, hand-verified pnl_pct sequence: [2.0, -1.0, 3.0, -2.0].
        # mean=0.5, population stdev≈2.0616 -> sharpe≈0.24;
        # downside-deviation≈1.1180 (only the two losing trades count)
        # -> sortino≈0.45. Confirms the real formula, not the old
        # `sharpe * 1.1` placeholder (which would give 0.264).
        trades = [
            _trade(pnl=200.0, closed_sim_minutes=1 * 1440, pnl_pct=2.0),
            _trade(pnl=-100.0, closed_sim_minutes=2 * 1440, pnl_pct=-1.0),
            _trade(pnl=300.0, closed_sim_minutes=3 * 1440, pnl_pct=3.0),
            _trade(pnl=-200.0, closed_sim_minutes=4 * 1440, pnl_pct=-2.0),
        ]
        portfolio = _portfolio(trades)
        now = TimeState(day=40, hour=20, minute=0)
        snapshot = compute_performance_snapshot("all_time", portfolio, [], now)
        assert snapshot.sharpe_ratio == 0.24
        assert snapshot.sortino_ratio == 0.45
        assert snapshot.sortino_ratio != round(snapshot.sharpe_ratio * 1.1, 2)

    def test_no_losing_trades_gives_zero_sortino_not_infinite(self) -> None:
        trades = [
            _trade(pnl=100.0, closed_sim_minutes=1 * 1440, pnl_pct=1.0),
            _trade(pnl=200.0, closed_sim_minutes=2 * 1440, pnl_pct=2.0),
        ]
        portfolio = _portfolio(trades)
        now = TimeState(day=40, hour=20, minute=0)
        snapshot = compute_performance_snapshot("all_time", portfolio, [], now)
        # No downside deviation to measure from — honestly 0.0, not a
        # fabricated "infinite" ratio.
        assert snapshot.sortino_ratio == 0.0
        # Sharpe is still real: identical returns (1.0, 2.0) have real,
        # nonzero variance, so this is not the "undefined stdev" case.
        assert snapshot.sharpe_ratio != 0.0
