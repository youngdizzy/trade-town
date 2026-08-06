"""Covers app/risk_engine.py, including v0.7 Feature 49's Daily Trading
Objectives extension. Every check reads real PaperPortfolio/PaperTrade
fields — no fabricated signal.
"""
from __future__ import annotations

from app.risk_engine import (
    compute_daily_objective_status,
    daily_realized_pnl_pct,
    evaluate_guardian_exposure,
    evaluate_sentinel_risk,
    monthly_realized_pnl_pct,
    portfolio_equity,
    recommended_quantity,
    trades_closed_today,
    trades_opened_today,
    weekly_realized_pnl_pct,
)
from app.schemas import PaperPortfolio, PaperTrade, RiskLimits


def _trade(*, pnl: float = 0.0, opened_sim_minutes: int = 0, closed_sim_minutes: int = 30) -> PaperTrade:
    return PaperTrade(
        id=f"trade-{opened_sim_minutes}-{closed_sim_minutes}",
        symbol="AAPL",
        side="buy",  # type: ignore[arg-type]
        quantity=1.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl,
        pnl=pnl,
        pnlPct=pnl,
        durationMinutes=closed_sim_minutes - opened_sim_minutes,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        supportingAgents=["scout"],  # type: ignore[arg-type]
        opposingAgents=[],
        openedAt="2024-01-01T00:00:00+00:00",
        closedAt="2024-01-01T00:00:00+00:00",
        openedSimMinutes=opened_sim_minutes,
        closedSimMinutes=closed_sim_minutes,
    )


def _portfolio(*, trades: list[PaperTrade] | None = None, cash: float = 100_000.0, starting: float = 100_000.0, total_pnl_pct: float = 0.0, positions: list | None = None) -> PaperPortfolio:
    trades = trades or []
    return PaperPortfolio(
        cashBalance=cash,
        startingBalance=starting,
        positions=positions or [],
        orders=[],
        tradeHistory=trades,
        totalPnl=0.0,
        totalPnlPct=total_pnl_pct,
        winCount=0,
        lossCount=0,
    )


class TestTodaysTradeHelpers:
    def test_trades_opened_today_filters_by_sim_day(self) -> None:
        today = _trade(opened_sim_minutes=2 * 1440 + 60, closed_sim_minutes=2 * 1440 + 90)
        yesterday = _trade(opened_sim_minutes=1 * 1440 + 60, closed_sim_minutes=1 * 1440 + 90)
        assert trades_opened_today([today, yesterday], sim_day=2) == [today]

    def test_trades_closed_today_filters_by_sim_day(self) -> None:
        today = _trade(opened_sim_minutes=2 * 1440 - 30, closed_sim_minutes=2 * 1440 + 30)
        assert trades_closed_today([today], sim_day=2) == [today]
        assert trades_closed_today([today], sim_day=1) == []

    def test_daily_realized_pnl_pct_only_counts_trades_closed_today(self) -> None:
        today_win = _trade(pnl=1000.0, opened_sim_minutes=2 * 1440, closed_sim_minutes=2 * 1440 + 30)
        yesterday_loss = _trade(pnl=-5000.0, opened_sim_minutes=1 * 1440, closed_sim_minutes=1 * 1440 + 30)
        portfolio = _portfolio(trades=[today_win, yesterday_loss], starting=100_000.0)
        assert daily_realized_pnl_pct(portfolio, sim_day=2) == 1.0

    def test_daily_realized_pnl_pct_is_zero_with_no_starting_balance(self) -> None:
        portfolio = _portfolio(trades=[_trade(pnl=100.0)], starting=0.0)
        assert daily_realized_pnl_pct(portfolio, sim_day=0) == 0.0


class TestEvaluateSentinelRiskDailyObjectives:
    def test_daily_max_loss_reached_blocks_new_trades(self) -> None:
        limits = RiskLimits(maxDailyLossPct=5.0)
        loss = _trade(pnl=-6000.0, opened_sim_minutes=1440, closed_sim_minutes=1440 + 30)
        portfolio = _portfolio(trades=[loss], starting=100_000.0)
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=1000.0, sim_day=1)
        assert warning is not None
        assert warning.severity == "critical"
        assert "daily maximum loss" in warning.message.lower()

    def test_daily_profit_target_reached_blocks_new_trades(self) -> None:
        limits = RiskLimits(dailyProfitTargetPct=3.0)
        win = _trade(pnl=4000.0, opened_sim_minutes=1440, closed_sim_minutes=1440 + 30)
        portfolio = _portfolio(trades=[win], starting=100_000.0)
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=1000.0, sim_day=1)
        assert warning is not None
        assert warning.severity == "critical"
        assert "daily target" in warning.message.lower()

    def test_max_trades_per_day_reached_blocks_new_trades(self) -> None:
        limits = RiskLimits(maxTradesPerDay=2)
        opened = [_trade(opened_sim_minutes=1440 + i, closed_sim_minutes=1440 + i + 10) for i in range(2)]
        portfolio = _portfolio(trades=opened, starting=100_000.0)
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=1000.0, sim_day=1)
        assert warning is not None
        assert warning.severity == "critical"
        assert "daily maximum" in warning.message.lower() or "trade" in warning.message.lower()

    def test_yesterdays_trades_do_not_count_against_todays_objectives(self) -> None:
        limits = RiskLimits(maxTradesPerDay=1, maxDailyLossPct=1.0, dailyProfitTargetPct=1.0)
        yesterday_loss = _trade(pnl=-5000.0, opened_sim_minutes=0, closed_sim_minutes=30)
        portfolio = _portfolio(trades=[yesterday_loss], starting=100_000.0)
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=1000.0, sim_day=1)
        assert warning is None

    def test_none_reached_yields_no_warning(self) -> None:
        limits = RiskLimits()
        portfolio = _portfolio(trades=[], starting=100_000.0)
        assert evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=1000.0, sim_day=1) is None

    def test_equity_check_still_takes_priority_over_daily_objectives(self) -> None:
        limits = RiskLimits()
        portfolio = _portfolio(trades=[], cash=0.0, starting=100_000.0)
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=1000.0, sim_day=1)
        assert warning is not None
        assert "equity" in warning.message.lower()


class TestWeeklyAndMonthlyLossLimits:
    """Design Bible Chapter 67 (TTOS) Safety Settings — the second and
    third real circuit breakers, mirroring the daily one's own tests
    above but scoped to a 7-day week / 30-day month."""

    def test_weekly_realized_pnl_pct_sums_the_whole_sim_week_not_just_today(self) -> None:
        # Both trades close within sim week 0 (days 0-6), on different days.
        day1_loss = _trade(pnl=-2000.0, opened_sim_minutes=1 * 1440, closed_sim_minutes=1 * 1440 + 30)
        day3_win = _trade(pnl=500.0, opened_sim_minutes=3 * 1440, closed_sim_minutes=3 * 1440 + 30)
        portfolio = _portfolio(trades=[day1_loss, day3_win], starting=100_000.0)
        assert weekly_realized_pnl_pct(portfolio, sim_day=3) == -1.5

    def test_last_weeks_trades_do_not_count_against_this_week(self) -> None:
        last_week_loss = _trade(pnl=-5000.0, opened_sim_minutes=2 * 1440, closed_sim_minutes=2 * 1440 + 30)
        portfolio = _portfolio(trades=[last_week_loss], starting=100_000.0)
        assert weekly_realized_pnl_pct(portfolio, sim_day=9) == 0.0  # day 9 is week 1, day 2 is week 0

    def test_weekly_max_loss_reached_blocks_new_trades(self) -> None:
        limits = RiskLimits(maxWeeklyLossPct=5.0, maxDailyLossPct=100.0)  # loose daily so only weekly can fire
        loss = _trade(pnl=-6000.0, opened_sim_minutes=1 * 1440, closed_sim_minutes=1 * 1440 + 30)
        portfolio = _portfolio(trades=[loss], starting=100_000.0)
        # sim_day=3 is the same week as the loss (day 1), but a different
        # day, so the daily check (scoped to day 3 only) sees nothing.
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=1000.0, sim_day=3)
        assert warning is not None
        assert warning.severity == "critical"
        assert "weekly maximum loss" in warning.message.lower()

    def test_monthly_realized_pnl_pct_sums_the_whole_sim_month(self) -> None:
        week0_loss = _trade(pnl=-1000.0, opened_sim_minutes=1 * 1440, closed_sim_minutes=1 * 1440 + 30)
        week2_win = _trade(pnl=200.0, opened_sim_minutes=15 * 1440, closed_sim_minutes=15 * 1440 + 30)
        portfolio = _portfolio(trades=[week0_loss, week2_win], starting=100_000.0)
        assert monthly_realized_pnl_pct(portfolio, sim_day=20) == -0.8

    def test_last_months_trades_do_not_count_against_this_month(self) -> None:
        last_month_loss = _trade(pnl=-5000.0, opened_sim_minutes=5 * 1440, closed_sim_minutes=5 * 1440 + 30)
        portfolio = _portfolio(trades=[last_month_loss], starting=100_000.0)
        assert monthly_realized_pnl_pct(portfolio, sim_day=35) == 0.0  # day 35 is month 1, day 5 is month 0

    def test_monthly_max_loss_reached_blocks_new_trades(self) -> None:
        limits = RiskLimits(maxMonthlyLossPct=5.0, maxDailyLossPct=100.0, maxWeeklyLossPct=100.0)
        loss = _trade(pnl=-6000.0, opened_sim_minutes=1 * 1440, closed_sim_minutes=1 * 1440 + 30)
        portfolio = _portfolio(trades=[loss], starting=100_000.0)
        # sim_day=20 is the same month as the loss (day 1) but a
        # different week, so neither daily nor weekly fires.
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=1000.0, sim_day=20)
        assert warning is not None
        assert warning.severity == "critical"
        assert "monthly maximum loss" in warning.message.lower()

    def test_within_all_limits_yields_no_warning(self) -> None:
        limits = RiskLimits(maxWeeklyLossPct=10.0, maxMonthlyLossPct=15.0)
        small_loss = _trade(pnl=-500.0, opened_sim_minutes=1 * 1440, closed_sim_minutes=1 * 1440 + 30)
        portfolio = _portfolio(trades=[small_loss], starting=100_000.0)
        assert evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=1000.0, sim_day=3) is None


class TestComputeDailyObjectiveStatus:
    def test_reports_real_trade_count_and_pnl(self) -> None:
        limits = RiskLimits(maxTradesPerDay=6, dailyProfitTargetPct=3.0, maxDailyLossPct=5.0)
        trades = [_trade(pnl=100.0, opened_sim_minutes=1440, closed_sim_minutes=1440 + 30)]
        portfolio = _portfolio(trades=trades, starting=100_000.0)
        status = compute_daily_objective_status(limits, portfolio, sim_day=1)
        assert status.trades_today == 1
        assert status.realized_pnl_pct_today == 0.1
        assert status.trading_halted is False
        assert status.halt_reason is None

    def test_max_loss_reached_sets_halted_and_reason(self) -> None:
        limits = RiskLimits(maxDailyLossPct=2.0)
        trades = [_trade(pnl=-3000.0, opened_sim_minutes=1440, closed_sim_minutes=1440 + 30)]
        portfolio = _portfolio(trades=trades, starting=100_000.0)
        status = compute_daily_objective_status(limits, portfolio, sim_day=1)
        assert status.max_loss_reached is True
        assert status.trading_halted is True
        assert status.halt_reason is not None
        assert "loss" in status.halt_reason.lower()

    def test_profit_target_takes_priority_in_message_only_when_loss_not_also_reached(self) -> None:
        limits = RiskLimits(dailyProfitTargetPct=2.0)
        trades = [_trade(pnl=3000.0, opened_sim_minutes=1440, closed_sim_minutes=1440 + 30)]
        portfolio = _portfolio(trades=trades, starting=100_000.0)
        status = compute_daily_objective_status(limits, portfolio, sim_day=1)
        assert status.profit_target_reached is True
        assert status.max_loss_reached is False
        assert status.halt_reason is not None
        assert "target" in status.halt_reason.lower()

    def test_max_trades_reached_sets_halted(self) -> None:
        limits = RiskLimits(maxTradesPerDay=1)
        trades = [_trade(opened_sim_minutes=1440, closed_sim_minutes=1440 + 30)]
        portfolio = _portfolio(trades=trades, starting=100_000.0)
        status = compute_daily_objective_status(limits, portfolio, sim_day=1)
        assert status.max_trades_reached is True
        assert status.trading_halted is True


class TestEvaluateSentinelRiskExisting:
    def test_zero_equity_blocks_trading(self) -> None:
        limits = RiskLimits()
        portfolio = _portfolio(cash=0.0)
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=100.0, sim_day=0)
        assert warning is not None
        assert warning.severity == "critical"

    def test_lifetime_drawdown_blocks_trading(self) -> None:
        limits = RiskLimits(maxDrawdownPct=20.0)
        portfolio = _portfolio(total_pnl_pct=-25.0)
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=100.0, sim_day=0)
        assert warning is not None
        assert "drawdown" in warning.message.lower()

    def test_position_too_large_is_rejected(self) -> None:
        limits = RiskLimits(maxPositionPct=10.0)
        portfolio = _portfolio(cash=10_000.0, starting=10_000.0)
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=5000.0, sim_day=0)
        assert warning is not None
        assert "max position" in warning.message.lower()


class TestGuardianAndSizing:
    def test_recommended_quantity_respects_the_smaller_budget(self) -> None:
        limits = RiskLimits(riskPerTradePct=2.0, maxPositionPct=50.0)
        portfolio = _portfolio(cash=10_000.0, starting=10_000.0)
        qty = recommended_quantity(limits, portfolio, price=10.0)
        assert qty == round(10_000.0 * 0.02 / 10.0, 4)

    def test_guardian_flags_over_concentrated_symbol(self) -> None:
        from app.schemas import PaperPosition

        limits = RiskLimits(maxSectorConcentrationPct=10.0)
        position = PaperPosition(
            id="pos-1",
            symbol="AAPL",
            side="buy",  # type: ignore[arg-type]
            quantity=100.0,
            entryPrice=50.0,
            currentPrice=50.0,
            unrealizedPnl=0.0,
            unrealizedPnlPct=0.0,
            openedBy="sentinel",  # type: ignore[arg-type]
            confidence=80.0,
            openedAt="2024-01-01T00:00:00+00:00",
        )
        portfolio = _portfolio(cash=0.0, starting=10_000.0, positions=[position])
        warning = evaluate_guardian_exposure(limits, portfolio, symbol="AAPL")
        assert warning is not None
        assert "concentration" in warning.message.lower()

    def test_portfolio_equity_sums_cash_and_positions(self) -> None:
        from app.schemas import PaperPosition

        position = PaperPosition(
            id="pos-1",
            symbol="AAPL",
            side="buy",  # type: ignore[arg-type]
            quantity=10.0,
            entryPrice=50.0,
            currentPrice=55.0,
            unrealizedPnl=50.0,
            unrealizedPnlPct=10.0,
            openedBy="sentinel",  # type: ignore[arg-type]
            confidence=80.0,
            openedAt="2024-01-01T00:00:00+00:00",
        )
        portfolio = _portfolio(cash=1000.0, positions=[position])
        assert portfolio_equity(portfolio) == 1000.0 + 10.0 * 55.0
