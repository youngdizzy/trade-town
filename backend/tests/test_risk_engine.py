"""Covers app/risk_engine.py, including v0.7 Feature 49's Daily Trading
Objectives extension. Every check reads real PaperPortfolio/PaperTrade
fields — no fabricated signal.
"""
from __future__ import annotations

from app.risk_engine import (
    compute_daily_objective_status,
    compute_risk_budget_status,
    daily_realized_pnl_pct,
    distinct_trading_days,
    evaluate_all_sentinel_checks,
    evaluate_guardian_exposure,
    evaluate_sentinel_risk,
    monthly_realized_pnl_pct,
    portfolio_equity,
    project_loss_after_n_losses,
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
        assert warning.code == "risk_daily_loss_limit"

    def test_daily_profit_target_reached_blocks_new_trades(self) -> None:
        limits = RiskLimits(dailyProfitTargetPct=3.0)
        win = _trade(pnl=4000.0, opened_sim_minutes=1440, closed_sim_minutes=1440 + 30)
        portfolio = _portfolio(trades=[win], starting=100_000.0)
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=1000.0, sim_day=1)
        assert warning is not None
        assert warning.severity == "critical"
        assert "daily target" in warning.message.lower()
        assert warning.code == "risk_daily_profit_target"

    def test_max_trades_per_day_reached_blocks_new_trades(self) -> None:
        limits = RiskLimits(maxTradesPerDay=2)
        opened = [_trade(opened_sim_minutes=1440 + i, closed_sim_minutes=1440 + i + 10) for i in range(2)]
        portfolio = _portfolio(trades=opened, starting=100_000.0)
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=1000.0, sim_day=1)
        assert warning is not None
        assert warning.severity == "critical"
        assert "daily maximum" in warning.message.lower() or "trade" in warning.message.lower()
        assert warning.code == "risk_max_trades_per_day"

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
        assert warning.code == "risk_equity_exhausted"


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
        assert warning.code == "risk_weekly_loss_limit"

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
        assert warning.code == "risk_monthly_loss_limit"

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


class TestComputeRiskBudgetStatus:
    """Prop-Firm Risk Intelligence Addendum, Piece 8 — "the system should
    understand the remaining permissible loss budget" before a trade is
    proposed. Every value here traces to a field/function this codebase
    already had (portfolio.total_pnl_pct, daily_realized_pnl_pct,
    compute_daily_objective_status) — these tests confirm the packaging
    is correct, not a new formula."""

    def test_fresh_portfolio_has_full_remaining_budget(self) -> None:
        limits = RiskLimits(maxDrawdownPct=20.0, maxDailyLossPct=5.0, dailyProfitTargetPct=3.0)
        portfolio = _portfolio(starting=100_000.0, cash=100_000.0, total_pnl_pct=0.0)
        status = compute_risk_budget_status(limits, portfolio, sim_day=1)
        assert status.equity == 100_000.0
        assert status.starting_balance == 100_000.0
        assert status.lifetime_drawdown_pct == 0.0
        assert status.remaining_drawdown_budget_pct == 20.0
        assert status.daily_loss_pct_today == 0.0
        assert status.remaining_daily_loss_budget_pct == 5.0
        assert status.trading_halted is False

    def test_lifetime_drawdown_reduces_the_real_remaining_budget(self) -> None:
        # A real lifetime loss, read off the same total_pnl_pct field
        # evaluate_sentinel_risk's own lifetime-drawdown check reads.
        limits = RiskLimits(maxDrawdownPct=20.0)
        portfolio = _portfolio(starting=100_000.0, cash=92_000.0, total_pnl_pct=-8.0)
        status = compute_risk_budget_status(limits, portfolio, sim_day=1)
        assert status.lifetime_drawdown_pct == 8.0
        assert status.remaining_drawdown_budget_pct == 12.0

    def test_drawdown_past_the_limit_floors_remaining_budget_at_zero(self) -> None:
        limits = RiskLimits(maxDrawdownPct=10.0)
        portfolio = _portfolio(starting=100_000.0, cash=85_000.0, total_pnl_pct=-15.0)
        status = compute_risk_budget_status(limits, portfolio, sim_day=1)
        assert status.lifetime_drawdown_pct == 15.0
        assert status.remaining_drawdown_budget_pct == 0.0

    def test_todays_real_loss_reduces_the_real_remaining_daily_budget(self) -> None:
        limits = RiskLimits(maxDailyLossPct=5.0)
        trades = [_trade(pnl=-2000.0, opened_sim_minutes=1440, closed_sim_minutes=1440 + 30)]
        portfolio = _portfolio(trades=trades, starting=100_000.0)
        status = compute_risk_budget_status(limits, portfolio, sim_day=1)
        assert status.daily_loss_pct_today == 2.0
        assert status.remaining_daily_loss_budget_pct == 3.0
        assert status.daily_profit_pct_today == 0.0

    def test_todays_real_profit_tracks_remaining_distance_to_target(self) -> None:
        limits = RiskLimits(dailyProfitTargetPct=3.0)
        trades = [_trade(pnl=1000.0, opened_sim_minutes=1440, closed_sim_minutes=1440 + 30)]
        portfolio = _portfolio(trades=trades, starting=100_000.0)
        status = compute_risk_budget_status(limits, portfolio, sim_day=1)
        assert status.daily_profit_pct_today == 1.0
        assert status.remaining_to_daily_profit_target_pct == 2.0
        assert status.daily_loss_pct_today == 0.0

    def test_halted_state_is_read_directly_from_compute_daily_objective_status(self) -> None:
        # Never a second, independently-derived halt decision — must
        # match compute_daily_objective_status exactly, since that's the
        # function evaluate_sentinel_risk's own real gate is built on.
        limits = RiskLimits(maxDailyLossPct=2.0)
        trades = [_trade(pnl=-3000.0, opened_sim_minutes=1440, closed_sim_minutes=1440 + 30)]
        portfolio = _portfolio(trades=trades, starting=100_000.0)
        daily_status = compute_daily_objective_status(limits, portfolio, sim_day=1)
        budget_status = compute_risk_budget_status(limits, portfolio, sim_day=1)
        assert budget_status.trading_halted == daily_status.trading_halted
        assert budget_status.halt_reason == daily_status.halt_reason
        assert budget_status.trading_halted is True

    def test_not_halted_state_has_no_reason(self) -> None:
        limits = RiskLimits()
        portfolio = _portfolio(starting=100_000.0)
        status = compute_risk_budget_status(limits, portfolio, sim_day=1)
        assert status.trading_halted is False
        assert status.halt_reason is None

    def test_trading_days_count_reflects_real_distinct_days(self) -> None:
        limits = RiskLimits()
        trades = [
            _trade(pnl=100.0, closed_sim_minutes=30),
            _trade(pnl=-50.0, closed_sim_minutes=1440 + 30),
            _trade(pnl=20.0, closed_sim_minutes=1440 + 90),
        ]
        portfolio = _portfolio(trades=trades, starting=100_000.0)
        status = compute_risk_budget_status(limits, portfolio, sim_day=1)
        assert status.trading_days_count == 2


class TestDistinctTradingDays:
    """Prop-Firm Risk Intelligence Addendum, Piece 11b — Requirement 24's
    "number of trading days" data point, reusing the exact
    closed_sim_minutes // SIM_MINUTES_PER_DAY bucketing convention
    app/prop_firm.py's compute_consistency_status() already established."""

    def test_counts_distinct_days_not_trade_count(self) -> None:
        trades = [_trade(pnl=10.0, closed_sim_minutes=30), _trade(pnl=10.0, closed_sim_minutes=60), _trade(pnl=10.0, closed_sim_minutes=90)]
        assert distinct_trading_days(trades) == 1

    def test_counts_multiple_real_distinct_days(self) -> None:
        trades = [_trade(pnl=10.0, closed_sim_minutes=30), _trade(pnl=10.0, closed_sim_minutes=1440 + 30), _trade(pnl=10.0, closed_sim_minutes=2880 + 30)]
        assert distinct_trading_days(trades) == 3

    def test_empty_history_is_zero(self) -> None:
        assert distinct_trading_days([]) == 0


class TestEvaluateSentinelRiskExisting:
    def test_zero_equity_blocks_trading(self) -> None:
        limits = RiskLimits()
        portfolio = _portfolio(cash=0.0)
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=100.0, sim_day=0)
        assert warning is not None
        assert warning.severity == "critical"

    def test_lifetime_drawdown_blocks_trading(self) -> None:
        """CEO directive "Portfolio Risk Engine + Firm-Wide Risk
        Governance" — this now measures a REAL peak-to-trough drawdown
        (app/analytics.py::max_drawdown_pct()), not the bare
        `total_pnl_pct` field, so the portfolio needs a real closed loss
        behind it, not just a fabricated summary number. Generous
        weekly/monthly loss limits isolate the drawdown gate specifically
        (a large-enough loss also breaches those, checked earlier); `cash`
        is set to the real post-trade balance so the live-equity read
        (`portfolio_equity()`) agrees with the trade history instead of
        implying a second, fake loss on top of it."""
        limits = RiskLimits(maxDrawdownPct=20.0, maxWeeklyLossPct=90.0, maxMonthlyLossPct=90.0)
        portfolio = _portfolio(trades=[_trade(pnl=-25_000.0, opened_sim_minutes=0, closed_sim_minutes=30)], cash=75_000.0)
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=100.0, sim_day=5)
        assert warning is not None
        assert "drawdown" in warning.message.lower()
        assert warning.code == "risk_lifetime_drawdown"

    def test_lifetime_drawdown_uses_real_peak_not_starting_balance(self) -> None:
        """The bug this fix closes: an account that ran up a real gain
        before giving some back must still be measured from its own real
        peak, not from where it started — `total_pnl_pct` alone would
        have read "+15%" here and never tripped this gate even though
        the account just lived through a real 23%-from-peak drawdown."""
        limits = RiskLimits(maxDrawdownPct=20.0, maxWeeklyLossPct=90.0, maxMonthlyLossPct=90.0)
        portfolio = _portfolio(
            trades=[
                _trade(pnl=50_000.0, opened_sim_minutes=0, closed_sim_minutes=30),
                _trade(pnl=-35_000.0, opened_sim_minutes=1440, closed_sim_minutes=1470),
            ],
            cash=115_000.0,
        )
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=100.0, sim_day=5)
        assert warning is not None
        assert warning.code == "risk_lifetime_drawdown"

    def test_lifetime_drawdown_ignores_stale_gain_when_still_within_limit(self) -> None:
        limits = RiskLimits(maxDrawdownPct=20.0, maxWeeklyLossPct=90.0, maxMonthlyLossPct=90.0)
        portfolio = _portfolio(
            trades=[
                _trade(pnl=50_000.0, opened_sim_minutes=0, closed_sim_minutes=30),
                _trade(pnl=-10_000.0, opened_sim_minutes=1440, closed_sim_minutes=1470),
            ],
            cash=140_000.0,
        )
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=100.0, sim_day=5)
        assert warning is None


class TestEvaluateAllSentinelChecks:
    """CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance"
    — `evaluate_all_sentinel_checks()` must return every real violation,
    not just the one `evaluate_sentinel_risk()` reports, and the two
    must never disagree about the FIRST one (same underlying checks,
    same order)."""

    def test_no_violations_returns_empty_list(self) -> None:
        limits = RiskLimits()
        portfolio = _portfolio()
        assert evaluate_all_sentinel_checks(limits, portfolio, symbol="AAPL", proposed_value=100.0, sim_day=0) == []

    def test_multiple_real_violations_are_all_returned(self) -> None:
        # Both the max-open-positions limit AND the position-size limit
        # are real violations on this same candidate at once.
        from app.schemas import PaperPosition

        position = PaperPosition(
            id="pos-1",
            symbol="MSFT",
            side="buy",  # type: ignore[arg-type]
            quantity=10.0,
            entryPrice=50.0,
            currentPrice=50.0,
            unrealizedPnl=0.0,
            unrealizedPnlPct=0.0,
            openedBy="sentinel",  # type: ignore[arg-type]
            confidence=80.0,
            openedAt="2024-01-01T00:00:00+00:00",
        )
        limits = RiskLimits(maxOpenPositions=1, maxPositionPct=1.0)
        portfolio = _portfolio(positions=[position], cash=10_000.0, starting=10_000.0)
        checks = evaluate_all_sentinel_checks(limits, portfolio, symbol="AAPL", proposed_value=5_000.0, sim_day=0)
        codes = {c.code for c in checks}
        assert "risk_max_open_positions" in codes
        assert "risk_position_size_limit" in codes
        assert len(checks) >= 2

    def test_first_of_many_matches_evaluate_sentinel_risk(self) -> None:
        from app.schemas import PaperPosition

        position = PaperPosition(
            id="pos-1",
            symbol="MSFT",
            side="buy",  # type: ignore[arg-type]
            quantity=10.0,
            entryPrice=50.0,
            currentPrice=50.0,
            unrealizedPnl=0.0,
            unrealizedPnlPct=0.0,
            openedBy="sentinel",  # type: ignore[arg-type]
            confidence=80.0,
            openedAt="2024-01-01T00:00:00+00:00",
        )
        limits = RiskLimits(maxOpenPositions=1, maxPositionPct=1.0)
        portfolio = _portfolio(positions=[position], cash=10_000.0, starting=10_000.0)
        checks = evaluate_all_sentinel_checks(limits, portfolio, symbol="AAPL", proposed_value=5_000.0, sim_day=0)
        single = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=5_000.0, sim_day=0)
        assert single is not None
        assert checks[0].code == single.code

    def test_equity_exhausted_stops_at_one_check_not_a_crash(self) -> None:
        limits = RiskLimits()
        portfolio = _portfolio(cash=0.0, starting=100_000.0)
        checks = evaluate_all_sentinel_checks(limits, portfolio, symbol="AAPL", proposed_value=100.0, sim_day=0)
        assert len(checks) == 1
        assert checks[0].code == "risk_equity_exhausted"

    def test_position_too_large_is_rejected(self) -> None:
        limits = RiskLimits(maxPositionPct=10.0)
        portfolio = _portfolio(cash=10_000.0, starting=10_000.0)
        warning = evaluate_sentinel_risk(limits, portfolio, symbol="AAPL", proposed_value=5000.0, sim_day=0)
        assert warning is not None
        assert "max position" in warning.message.lower()
        assert warning.code == "risk_position_size_limit"


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
        assert warning.code == "risk_concentration_limit"

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


class TestProjectLossAfterNLosses:
    """Prop-Firm Risk Intelligence Addendum, Piece 11a — Requirement 23:
    "projected loss after N consecutive losses." Compounds
    risk_per_trade_pct against current equity, the exact same sizing
    math recommended_quantity() already uses, projected forward — a
    deterministic worst-case path, never a probability."""

    def test_zero_losses_returns_a_single_point_path_at_current_equity(self) -> None:
        limits = RiskLimits(riskPerTradePct=2.0)
        portfolio = _portfolio(cash=100_000.0, starting=100_000.0)
        path = project_loss_after_n_losses(limits, portfolio, 0)
        assert path.equity_path == [100_000.0]
        assert path.starting_equity == 100_000.0
        assert path.projected_loss_pct == 0.0

    def test_compounds_risk_per_trade_pct_across_each_loss(self) -> None:
        limits = RiskLimits(riskPerTradePct=10.0)
        portfolio = _portfolio(cash=100_000.0, starting=100_000.0)
        path = project_loss_after_n_losses(limits, portfolio, 3)
        # 100_000 -> 90_000 -> 81_000 -> 72_900 (each step -10%)
        assert path.equity_path == [100_000.0, 90_000.0, 81_000.0, 72_900.0]
        assert path.consecutive_losses == 3
        assert path.risk_per_trade_pct == 10.0
        assert path.projected_loss_pct == 27.1

    def test_real_thresholds_produce_a_larger_projected_loss_at_five_than_at_three(self) -> None:
        # Real losing-streak thresholds this codebase already uses
        # (TradingModeState.losing_streak_pause_count=3,
        # losing_streak_suspend_count=5) — not arbitrary numbers.
        limits = RiskLimits(riskPerTradePct=5.0)
        portfolio = _portfolio(cash=100_000.0, starting=100_000.0)
        at_pause = project_loss_after_n_losses(limits, portfolio, 3)
        at_suspend = project_loss_after_n_losses(limits, portfolio, 5)
        assert at_suspend.projected_loss_pct > at_pause.projected_loss_pct

    def test_assumption_is_always_disclosed(self) -> None:
        limits = RiskLimits(riskPerTradePct=2.0)
        portfolio = _portfolio(cash=100_000.0, starting=100_000.0)
        path = project_loss_after_n_losses(limits, portfolio, 5)
        assert "risk_per_trade_pct" in path.assumption
        assert "worst-case" in path.assumption.lower()

    def test_zero_equity_never_crashes(self) -> None:
        limits = RiskLimits(riskPerTradePct=2.0)
        portfolio = _portfolio(cash=0.0, starting=100_000.0)
        path = project_loss_after_n_losses(limits, portfolio, 5)
        assert path.equity_path[0] == 0.0
        assert path.projected_loss_pct == 0.0
