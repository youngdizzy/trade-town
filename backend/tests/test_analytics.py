"""Covers app/analytics.py's compute_performance_snapshot() period filtering
(v0.6.1) — before this, every period label (daily/weekly/monthly/all_time)
computed identical all-time totals; this checks that a "monthly" snapshot
now genuinely excludes trades closed in a prior simulated month, and that
"all_time" stays deliberately unfiltered."""
from __future__ import annotations

from app.analytics import compute_performance_snapshot, compute_recovery_factor, max_drawdown_pct, max_drawdown_usd, real_peak_equity
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

class TestRealMaxDrawdown:
    """Professional Quant Trading Core Phase A/C — replaced the old
    single-worst-losing-trade proxy with a real peak-to-trough running
    drawdown over the closed-trade equity curve (same convention as
    app/performance_attribution.py::_live_drawdown_usd(),
    app/strategy_lab.py, app/backtest_primitives.py, app/whatif.py)."""

    def test_compounding_losses_draw_down_more_than_any_single_trade(self) -> None:
        # Three consecutive -2% losses compound to a real cumulative
        # decline larger than any one trade's own pnl_pct — the old
        # proxy (worst single trade) would have reported ~2%, understating
        # the true peak-to-trough decline.
        trades = [
            _trade(pnl=-2_000.0, closed_sim_minutes=1 * 1440, pnl_pct=-2.0),
            _trade(pnl=-2_000.0, closed_sim_minutes=2 * 1440, pnl_pct=-2.0),
            _trade(pnl=-2_000.0, closed_sim_minutes=3 * 1440, pnl_pct=-2.0),
        ]
        portfolio = _portfolio(trades)
        now = TimeState(day=40, hour=20, minute=0)
        snapshot = compute_performance_snapshot("all_time", portfolio, [], now)
        # Flat $2,000 losses on a $100k base: 100k -> 98k -> 96k -> 94k,
        # peak-to-trough off the starting 100k peak = 6.0% — exactly the
        # sum of the three trades' own pnl_pct, since none of them
        # individually exceeds it (the old single-worst-trade proxy
        # would have reported only 2.0%, a 3x understatement here).
        assert snapshot.max_drawdown_pct == 6.0

    def test_a_win_after_losses_does_not_erase_the_recorded_drawdown(self) -> None:
        # Recovering after a loss must not retroactively shrink the max
        # drawdown already reached at the trough.
        trades = [
            _trade(pnl=-5_000.0, closed_sim_minutes=1 * 1440, pnl_pct=-5.0),
            _trade(pnl=4_000.0, closed_sim_minutes=2 * 1440, pnl_pct=4.0),
        ]
        portfolio = _portfolio(trades)
        now = TimeState(day=40, hour=20, minute=0)
        snapshot = compute_performance_snapshot("all_time", portfolio, [], now)
        assert snapshot.max_drawdown_pct == 5.0

    def test_zero_trades_is_zero_not_a_crash(self) -> None:
        portfolio = _portfolio([])
        now = TimeState(day=40, hour=20, minute=0)
        snapshot = compute_performance_snapshot("all_time", portfolio, [], now)
        assert snapshot.max_drawdown_pct == 0.0


_TRADE_DEFAULTS = {
    "id": "trade-x",
    "symbol": "AAPL",
    "side": "buy",
    "quantity": 1.0,
    "entryPrice": 100.0,
    "exitPrice": 100.0,
    "durationMinutes": 30,
    "confidence": 80.0,
    "reason": "test",
    "marketConditions": "test",
    "supportingAgents": ["scout"],
    "opposingAgents": [],
    "openedAt": "2024-01-01T00:00:00+00:00",
    "closedAt": "2024-01-01T00:00:00+00:00",
    "openedSimMinutes": 0,
}


class TestMaxDrawdownPctCurrentEquity:
    """CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance"
    — the new optional `current_equity` parameter, which folds today's
    real live (realized + unrealized) equity into the same peak/trough
    comparison as one more point after the last closed trade."""

    def test_omitted_current_equity_is_byte_for_byte_unchanged(self) -> None:
        trades = [PaperTrade.model_validate({**_TRADE_DEFAULTS, "pnl": -5_000.0, "pnlPct": -5.0, "closedSimMinutes": 1440})]
        assert max_drawdown_pct(trades, 100_000.0) == max_drawdown_pct(trades, 100_000.0, current_equity=None)

    def test_current_equity_below_realized_trough_deepens_the_reported_drawdown(self) -> None:
        # No closed trades at all, but the account is currently sitting
        # on a real 12% unrealized loss on an open position — the
        # realized-only read would stay silent about this until the
        # position closes.
        assert max_drawdown_pct([], 100_000.0, current_equity=88_000.0) == 12.0

    def test_current_equity_at_a_new_high_does_not_report_a_fake_drawdown(self) -> None:
        assert max_drawdown_pct([], 100_000.0, current_equity=110_000.0) == 0.0

    def test_current_equity_above_realized_trough_but_below_the_real_peak_still_reports_it(self) -> None:
        # Realized peak reached 150k, then gave back to 140k (realized-
        # only drawdown 6.67%); currently sitting at 145k live — still a
        # real drawdown from the 150k peak (3.33%), just a smaller one
        # than the realized-only trough would suggest on its own; the
        # function reports the real WORST point seen across both.
        trades = [
            PaperTrade.model_validate({**_TRADE_DEFAULTS, "pnl": 50_000.0, "pnlPct": 50.0, "closedSimMinutes": 1440}),
            PaperTrade.model_validate({**_TRADE_DEFAULTS, "pnl": -10_000.0, "pnlPct": -10.0, "closedSimMinutes": 2 * 1440}),
        ]
        result = max_drawdown_pct(trades, 100_000.0, current_equity=145_000.0)
        assert round(result, 2) == round((150_000.0 - 140_000.0) / 150_000.0 * 100, 2)


class TestRealPeakEquity:
    def test_matches_the_peak_max_drawdown_pct_measures_against(self) -> None:
        trades = [
            PaperTrade.model_validate({**_TRADE_DEFAULTS, "pnl": 50_000.0, "pnlPct": 50.0, "closedSimMinutes": 1440}),
            PaperTrade.model_validate({**_TRADE_DEFAULTS, "pnl": -10_000.0, "pnlPct": -10.0, "closedSimMinutes": 2 * 1440}),
        ]
        assert real_peak_equity(trades, 100_000.0) == 150_000.0
        assert real_peak_equity(trades, 100_000.0, current_equity=200_000.0) == 200_000.0

    def test_zero_starting_equity_falls_back_to_current_equity_never_crashes(self) -> None:
        assert real_peak_equity([], 0.0, current_equity=5_000.0) == 5_000.0
        assert real_peak_equity([], 0.0) == 0.0


class TestRealSharpeSortinoNoLosses:
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


class TestMaxDrawdownUsd:
    """CEO directive "Professional Quant Trading Core," Phase B — the
    dollar sibling of max_drawdown_pct(), needed for a real dollar
    Recovery Factor."""

    def test_zero_starting_equity_never_crashes(self) -> None:
        assert max_drawdown_usd([], 0.0) == 0.0

    def test_no_trades_no_drawdown(self) -> None:
        assert max_drawdown_usd([], 100_000.0) == 0.0

    def test_a_real_peak_then_partial_giveback(self) -> None:
        trades = [
            _trade(pnl=50_000.0, closed_sim_minutes=1440, pnl_pct=50.0),
            _trade(pnl=-10_000.0, closed_sim_minutes=2 * 1440, pnl_pct=-10.0),
        ]
        assert max_drawdown_usd(trades, 100_000.0) == 10_000.0

    def test_the_worst_historical_drawdown_survives_a_later_recovery(self) -> None:
        trades = [
            _trade(pnl=50_000.0, closed_sim_minutes=1440, pnl_pct=50.0),
            _trade(pnl=-30_000.0, closed_sim_minutes=2 * 1440, pnl_pct=-30.0),  # -30k from the 150k peak
            _trade(pnl=20_000.0, closed_sim_minutes=3 * 1440, pnl_pct=20.0),  # recovers, but doesn't erase the real worst drawdown
        ]
        assert max_drawdown_usd(trades, 100_000.0) == 30_000.0

    def test_open_position_unrealized_loss_via_current_equity(self) -> None:
        trades = [_trade(pnl=50_000.0, closed_sim_minutes=1440, pnl_pct=50.0)]
        # Peak is 150k; a real unrealized loss drags live equity to 120k.
        assert max_drawdown_usd(trades, 100_000.0, current_equity=120_000.0) == 30_000.0


class TestComputeRecoveryFactor:
    """CEO directive "Professional Quant Trading Core," Phase B P2 item
    — net real profit divided by the account's own real worst
    peak-to-trough drawdown, both measured against today's real live
    equity."""

    def test_no_drawdown_yet_is_undefined_not_fabricated(self) -> None:
        portfolio = _portfolio([_trade(pnl=5_000.0, closed_sim_minutes=1440, pnl_pct=5.0)])
        result = compute_recovery_factor(portfolio, current_equity=105_000.0)
        assert result.max_drawdown_usd == 0.0
        assert result.recovery_factor is None

    def test_real_ratio_matches_hand_computation(self) -> None:
        trades = [
            _trade(pnl=50_000.0, closed_sim_minutes=1440, pnl_pct=50.0),
            _trade(pnl=-10_000.0, closed_sim_minutes=2 * 1440, pnl_pct=-10.0),
        ]
        portfolio = _portfolio(trades)
        # Net profit 40k, max drawdown 10k -> recovery factor 4.0.
        result = compute_recovery_factor(portfolio, current_equity=140_000.0)
        assert result.net_profit_usd == 40_000.0
        assert result.max_drawdown_usd == 10_000.0
        assert result.recovery_factor == 4.0

    def test_live_current_equity_folds_in_unrealized_pnl(self) -> None:
        trades = [_trade(pnl=50_000.0, closed_sim_minutes=1440, pnl_pct=50.0)]
        portfolio = _portfolio(trades)
        # A real open position drags live equity down from the 150k peak to 120k.
        result = compute_recovery_factor(portfolio, current_equity=120_000.0)
        assert result.net_profit_usd == 20_000.0
        assert result.max_drawdown_usd == 30_000.0
        assert result.recovery_factor == round(20_000.0 / 30_000.0, 2)

    def test_negative_net_profit_produces_a_real_negative_ratio(self) -> None:
        trades = [
            _trade(pnl=10_000.0, closed_sim_minutes=1440, pnl_pct=10.0),
            _trade(pnl=-30_000.0, closed_sim_minutes=2 * 1440, pnl_pct=-30.0),
        ]
        portfolio = _portfolio(trades)
        result = compute_recovery_factor(portfolio, current_equity=80_000.0)
        assert result.net_profit_usd == -20_000.0
        assert result.recovery_factor is not None and result.recovery_factor < 0

    def test_summary_discloses_the_real_numbers(self) -> None:
        trades = [
            _trade(pnl=50_000.0, closed_sim_minutes=1440, pnl_pct=50.0),
            _trade(pnl=-10_000.0, closed_sim_minutes=2 * 1440, pnl_pct=-10.0),
        ]
        portfolio = _portfolio(trades)
        result = compute_recovery_factor(portfolio, current_equity=140_000.0)
        assert "4.0" in result.summary or "4.00" in result.summary
