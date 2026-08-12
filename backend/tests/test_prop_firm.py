"""Covers app/prop_firm.py — Design Bible Chapter 69 Part 2, the Prop
Firm Rule Engine's real status computations (Trailing Drawdown,
Consistency, Scaling Milestones, Challenge Windows, Compliance Score).
This module only computes honest readouts — it never blocks a trade
itself (see app/rule_engine.py for enforcement). Every number here must
trace back to a real formula over an Account's own real state, never a
fabricated stand-in.
"""
from __future__ import annotations

from app.accounts import create_account
from app.prop_firm import (
    LEVERAGE_NOTE,
    SCALING_TIER_THRESHOLDS_PCT,
    compute_challenge_progress,
    compute_compliance_score,
    compute_consistency_status,
    compute_prop_firm_status,
    compute_scaling_status,
    compute_trailing_drawdown,
    weekday_for,
)
from app.risk_engine import default_risk_limits
from app.schemas import Account, PaperTrade


def _account(*, starting_balance: float = 10_000.0) -> Account:
    accounts, error = create_account(
        [], name="Prop Firm Test", account_type="prop_firm", starting_balance=starting_balance, base_risk_limits=default_risk_limits(), account_id="pf-1", now_iso="2026-01-01T00:00:00Z"
    )
    assert error is None
    return accounts[0]


def _trade(*, pnl: float, closed_sim_minutes: int) -> PaperTrade:
    return PaperTrade(
        id=f"trade-{closed_sim_minutes}-{pnl}",
        symbol="AAPL",
        side="buy",  # type: ignore[arg-type]
        quantity=10.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl,
        pnl=pnl,
        pnlPct=pnl,
        durationMinutes=60,
        confidence=70.0,
        reason="test",
        marketConditions="test",
        openedAt="2026-01-01T00:00:00Z",
        closedAt="2026-01-01T01:00:00Z",
        openedSimMinutes=closed_sim_minutes - 60,
        closedSimMinutes=closed_sim_minutes,
    )


class TestWeekdayFor:
    def test_day_1_is_a_monday(self) -> None:
        assert weekday_for(1) == "monday"

    def test_day_7_is_a_sunday(self) -> None:
        assert weekday_for(7) == "sunday"

    def test_day_8_wraps_back_to_monday(self) -> None:
        assert weekday_for(8) == "monday"


class TestTrailingDrawdown:
    def test_zero_drawdown_at_a_fresh_peak(self) -> None:
        account = _account(starting_balance=10_000.0)
        status = compute_trailing_drawdown(account)
        assert status.drawdown_pct == 0.0
        assert status.breached is False

    def test_real_drawdown_computed_from_peak_to_current_equity(self) -> None:
        account = _account(starting_balance=10_000.0)
        account = account.model_copy(update={"peak_equity": 10_000.0})
        drained = account.portfolio.model_copy(update={"cash_balance": 9_000.0})
        account = account.model_copy(update={"portfolio": drained})
        status = compute_trailing_drawdown(account)
        assert status.drawdown_pct == 10.0

    def test_breaches_when_drawdown_reaches_the_configured_limit(self) -> None:
        account = _account(starting_balance=10_000.0)
        account = account.model_copy(update={"peak_equity": 10_000.0, "trailing_drawdown_limit_pct": 5.0})
        drained = account.portfolio.model_copy(update={"cash_balance": 9_400.0})
        account = account.model_copy(update={"portfolio": drained})
        status = compute_trailing_drawdown(account)
        assert status.drawdown_pct == 6.0
        assert status.breached is True

    def test_no_limit_configured_never_breaches(self) -> None:
        account = _account(starting_balance=10_000.0)
        account = account.model_copy(update={"peak_equity": 10_000.0})
        drained = account.portfolio.model_copy(update={"cash_balance": 1_000.0})
        account = account.model_copy(update={"portfolio": drained})
        status = compute_trailing_drawdown(account)
        assert status.breached is False


class TestConsistencyStatus:
    def test_not_applicable_with_no_challenge_window_configured(self) -> None:
        account = _account(starting_balance=10_000.0)
        status = compute_consistency_status(account, sim_day=5)
        assert status.applicable is False
        assert status.breached is False

    def test_computes_real_largest_day_share_from_closed_trades(self) -> None:
        account = _account(starting_balance=10_000.0)
        account = account.model_copy(update={"challenge_start_sim_day": 0, "consistency_limit_pct": 50.0})
        trades = [
            _trade(pnl=100.0, closed_sim_minutes=1 * 1440 + 60),
            _trade(pnl=300.0, closed_sim_minutes=2 * 1440 + 60),
        ]
        portfolio = account.portfolio.model_copy(update={"trade_history": trades})
        account = account.model_copy(update={"portfolio": portfolio})
        status = compute_consistency_status(account, sim_day=5)
        assert status.applicable is True
        assert status.cumulative_profit == 400.0
        assert status.largest_single_day_profit == 300.0
        assert status.largest_single_day_share_pct == 75.0
        assert status.breached is True

    def test_trades_before_the_challenge_window_are_excluded(self) -> None:
        account = _account(starting_balance=10_000.0)
        account = account.model_copy(update={"challenge_start_sim_day": 3, "consistency_limit_pct": 50.0})
        trades = [_trade(pnl=1_000.0, closed_sim_minutes=1 * 1440 + 60)]  # before day 3
        portfolio = account.portfolio.model_copy(update={"trade_history": trades})
        account = account.model_copy(update={"portfolio": portfolio})
        status = compute_consistency_status(account, sim_day=5)
        assert status.cumulative_profit == 0.0
        assert status.breached is False

    def test_not_breached_when_cumulative_profit_is_zero_or_negative(self) -> None:
        account = _account(starting_balance=10_000.0)
        account = account.model_copy(update={"challenge_start_sim_day": 0, "consistency_limit_pct": 10.0})
        trades = [_trade(pnl=-500.0, closed_sim_minutes=1 * 1440 + 60)]
        portfolio = account.portfolio.model_copy(update={"trade_history": trades})
        account = account.model_copy(update={"portfolio": portfolio})
        status = compute_consistency_status(account, sim_day=5)
        assert status.breached is False


class TestScalingStatus:
    def test_tier_zero_below_the_first_threshold(self) -> None:
        account = _account(starting_balance=10_000.0)
        status = compute_scaling_status(account)
        assert status.current_tier == 0
        assert status.next_tier_growth_threshold_pct == SCALING_TIER_THRESHOLDS_PCT[0]

    def test_advances_a_tier_once_growth_crosses_a_threshold(self) -> None:
        account = _account(starting_balance=10_000.0)
        account = account.model_copy(update={"peak_equity": 11_500.0})  # +15%, past the 10% tier
        status = compute_scaling_status(account)
        assert status.current_tier == 1
        assert status.equity_growth_pct == 15.0

    def test_no_next_threshold_once_past_the_final_tier(self) -> None:
        account = _account(starting_balance=10_000.0)
        account = account.model_copy(update={"peak_equity": 25_000.0})  # +150%, past every tier
        status = compute_scaling_status(account)
        assert status.current_tier == len(SCALING_TIER_THRESHOLDS_PCT)
        assert status.next_tier_growth_threshold_pct is None


class TestChallengeProgress:
    def test_not_applicable_with_no_challenge_window_configured(self) -> None:
        account = _account(starting_balance=10_000.0)
        status = compute_challenge_progress(account, sim_day=5)
        assert status.applicable is False

    def test_computes_real_days_elapsed_and_profit_pct(self) -> None:
        account = _account(starting_balance=10_000.0)
        account = account.model_copy(update={"challenge_start_sim_day": 2, "challenge_duration_days": 30, "challenge_profit_target_pct": 10.0, "peak_equity": 10_500.0})
        drained = account.portfolio.model_copy(update={"cash_balance": 10_500.0})
        account = account.model_copy(update={"portfolio": drained})
        status = compute_challenge_progress(account, sim_day=7)
        assert status.applicable is True
        assert status.days_elapsed == 5
        assert status.days_remaining == 25
        assert status.profit_pct == 5.0

    def test_on_pace_reflects_whether_profit_is_ahead_of_the_required_linear_rate(self) -> None:
        account = _account(starting_balance=10_000.0)
        account = account.model_copy(update={"challenge_start_sim_day": 0, "challenge_duration_days": 10, "challenge_profit_target_pct": 10.0})
        ahead = account.portfolio.model_copy(update={"cash_balance": 10_600.0})  # +6% after half the window (required pace 5%)
        account_ahead = account.model_copy(update={"portfolio": ahead})
        status_ahead = compute_challenge_progress(account_ahead, sim_day=5)
        assert status_ahead.on_pace is True

        behind = account.portfolio.model_copy(update={"cash_balance": 10_100.0})  # +1%, behind the 5% required pace
        account_behind = account.model_copy(update={"portfolio": behind})
        status_behind = compute_challenge_progress(account_behind, sim_day=5)
        assert status_behind.on_pace is False


class TestComplianceScore:
    def test_a_fresh_account_scores_a_perfect_100(self) -> None:
        account = _account(starting_balance=10_000.0)
        score = compute_compliance_score(account, sim_day=1)
        assert score.overall == 100.0
        assert score.rule_compliance == 100.0

    def test_score_degrades_as_drawdown_approaches_its_limit(self) -> None:
        account = _account(starting_balance=10_000.0)
        account = account.model_copy(update={"peak_equity": 10_000.0, "trailing_drawdown_limit_pct": 10.0})
        drained = account.portfolio.model_copy(update={"cash_balance": 9_500.0})  # 5% drawdown, halfway to the 10% limit
        account = account.model_copy(update={"portfolio": drained})
        score = compute_compliance_score(account, sim_day=1)
        assert score.drawdown_safety == 50.0
        assert score.overall < 100.0


class TestComputePropFirmStatus:
    def test_bundles_every_real_sub_computation_and_the_honest_leverage_note(self) -> None:
        account = _account(starting_balance=10_000.0)
        status = compute_prop_firm_status(account, sim_day=3)
        assert status.account_id == account.id
        assert status.weekday == weekday_for(3)
        assert status.leverage_note == LEVERAGE_NOTE
        assert status.trailing_drawdown is not None
        assert status.consistency is not None
        assert status.scaling is not None
        assert status.challenge is not None
        assert status.compliance_score is not None
