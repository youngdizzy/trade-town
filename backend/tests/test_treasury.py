"""Covers app/treasury.py — v0.7 Feature 33, the CEO Treasury."""
from __future__ import annotations

from datetime import datetime, timezone

from app.portfolio import default_portfolio
from app.treasury import (
    MAX_TREASURY_MONTHLY_REPORTS,
    MAX_TREASURY_TRANSACTIONS,
    apply_monthly_savings_rules,
    create_rule,
    default_treasury,
    deposit,
    pause_all_rules,
    record_monthly_report,
    reserve_percentage,
    toggle_rule,
    withdraw,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TestDefaultTreasury:
    def test_starts_empty(self) -> None:
        treasury = default_treasury(_now_iso())
        assert treasury.balance == 0.0
        assert treasury.lifetime_deposits == 0.0
        assert treasury.largest_balance == 0.0
        assert treasury.transactions == []
        assert treasury.savings_rules == []
        assert treasury.monthly_reports == []


class TestReservePercentage:
    def test_zero_when_both_accounts_empty(self) -> None:
        treasury = default_treasury(_now_iso())
        portfolio = default_portfolio().model_copy(update={"cash_balance": 0.0})
        assert reserve_percentage(treasury, portfolio) == 0.0

    def test_reflects_real_split_between_accounts(self) -> None:
        treasury = default_treasury(_now_iso()).model_copy(update={"balance": 25_000.0})
        portfolio = default_portfolio().model_copy(update={"cash_balance": 75_000.0})
        assert reserve_percentage(treasury, portfolio) == 25.0


class TestDeposit:
    def test_moves_real_cash_from_operating_capital(self) -> None:
        treasury = default_treasury(_now_iso())
        portfolio = default_portfolio()
        starting_cash = portfolio.cash_balance
        new_treasury, new_portfolio, error = deposit(
            treasury, portfolio, 1_000.0, sim_day=1, now_iso=_now_iso(), transaction_id="treasury-deposit-1"
        )
        assert error is None
        assert new_treasury.balance == 1_000.0
        assert new_treasury.lifetime_deposits == 1_000.0
        assert new_treasury.largest_balance == 1_000.0
        assert new_portfolio.cash_balance == starting_cash - 1_000.0
        assert len(new_treasury.transactions) == 1
        assert new_treasury.transactions[0].kind == "deposit"
        assert new_treasury.transactions[0].balance_after == 1_000.0

    def test_rejects_non_positive_amount(self) -> None:
        treasury = default_treasury(_now_iso())
        portfolio = default_portfolio()
        new_treasury, new_portfolio, error = deposit(treasury, portfolio, 0.0, sim_day=1, now_iso=_now_iso(), transaction_id="x")
        assert error is not None
        assert new_treasury == treasury
        assert new_portfolio == portfolio

    def test_rejects_deposit_larger_than_operating_cash(self) -> None:
        treasury = default_treasury(_now_iso())
        portfolio = default_portfolio()
        new_treasury, new_portfolio, error = deposit(
            treasury, portfolio, portfolio.cash_balance + 1.0, sim_day=1, now_iso=_now_iso(), transaction_id="x"
        )
        assert error is not None
        assert "Operating Capital" in error
        assert new_treasury == treasury
        assert new_portfolio == portfolio


class TestWithdraw:
    def test_moves_real_cash_back_to_operating_capital(self) -> None:
        treasury = default_treasury(_now_iso()).model_copy(update={"balance": 5_000.0})
        portfolio = default_portfolio()
        starting_cash = portfolio.cash_balance
        new_treasury, new_portfolio, error = withdraw(
            treasury, portfolio, 2_000.0, sim_day=1, now_iso=_now_iso(), transaction_id="treasury-withdraw-1"
        )
        assert error is None
        assert new_treasury.balance == 3_000.0
        assert new_portfolio.cash_balance == starting_cash + 2_000.0
        assert new_treasury.transactions[0].kind == "withdrawal"

    def test_rejects_non_positive_amount(self) -> None:
        treasury = default_treasury(_now_iso()).model_copy(update={"balance": 5_000.0})
        portfolio = default_portfolio()
        new_treasury, new_portfolio, error = withdraw(treasury, portfolio, -5.0, sim_day=1, now_iso=_now_iso(), transaction_id="x")
        assert error is not None
        assert new_treasury == treasury
        assert new_portfolio == portfolio

    def test_rejects_withdrawal_larger_than_treasury_balance(self) -> None:
        treasury = default_treasury(_now_iso()).model_copy(update={"balance": 100.0})
        portfolio = default_portfolio()
        new_treasury, new_portfolio, error = withdraw(treasury, portfolio, 101.0, sim_day=1, now_iso=_now_iso(), transaction_id="x")
        assert error is not None
        assert "Treasury only holds" in error
        assert new_treasury == treasury
        assert new_portfolio == portfolio

    def test_never_touches_treasury_without_an_explicit_ceo_amount(self) -> None:
        """The Treasury's core guarantee (see treasury.py's module docstring):
        every balance-changing call takes an explicit CEO-initiated amount —
        there is no path that derives it from anywhere else."""
        treasury = default_treasury(_now_iso()).model_copy(update={"balance": 1_000.0})
        portfolio = default_portfolio()
        new_treasury, _, error = withdraw(treasury, portfolio, 0.0, sim_day=1, now_iso=_now_iso(), transaction_id="x")
        assert error is not None
        assert new_treasury.balance == 1_000.0


class TestCreateRule:
    def test_percent_of_profit_rule(self) -> None:
        treasury = default_treasury(_now_iso())
        new_treasury, error = create_rule(treasury, "percent_of_monthly_profit", percent=10.0, reserve_target=None, now_iso=_now_iso(), rule_id="rule-1")
        assert error is None
        assert len(new_treasury.savings_rules) == 1
        rule = new_treasury.savings_rules[0]
        assert rule.rule_type == "percent_of_monthly_profit"
        assert rule.percent == 10.0
        assert rule.reserve_target is None
        assert rule.active is True

    def test_percent_rule_rejects_out_of_range_percent(self) -> None:
        treasury = default_treasury(_now_iso())
        new_treasury, error = create_rule(treasury, "percent_of_monthly_profit", percent=0.0, reserve_target=None, now_iso=_now_iso(), rule_id="rule-1")
        assert error is not None
        assert new_treasury == treasury

        new_treasury, error = create_rule(treasury, "percent_of_monthly_profit", percent=150.0, reserve_target=None, now_iso=_now_iso(), rule_id="rule-1")
        assert error is not None
        assert new_treasury == treasury

    def test_excess_above_reserve_rule(self) -> None:
        treasury = default_treasury(_now_iso())
        new_treasury, error = create_rule(treasury, "excess_above_reserve", percent=0.0, reserve_target=20_000.0, now_iso=_now_iso(), rule_id="rule-2")
        assert error is None
        rule = new_treasury.savings_rules[0]
        assert rule.rule_type == "excess_above_reserve"
        assert rule.reserve_target == 20_000.0
        assert rule.percent == 0.0

    def test_excess_above_reserve_rule_rejects_missing_target(self) -> None:
        treasury = default_treasury(_now_iso())
        new_treasury, error = create_rule(treasury, "excess_above_reserve", percent=0.0, reserve_target=None, now_iso=_now_iso(), rule_id="rule-2")
        assert error is not None
        assert new_treasury == treasury

        new_treasury, error = create_rule(treasury, "excess_above_reserve", percent=0.0, reserve_target=-1.0, now_iso=_now_iso(), rule_id="rule-2")
        assert error is not None
        assert new_treasury == treasury


class TestToggleRule:
    def test_toggles_a_real_existing_rule(self) -> None:
        treasury, _ = create_rule(default_treasury(_now_iso()), "percent_of_monthly_profit", percent=5.0, reserve_target=None, now_iso=_now_iso(), rule_id="rule-1")
        updated, error = toggle_rule(treasury, "rule-1", False, now_iso=_now_iso())
        assert error is None
        assert updated.savings_rules[0].active is False

    def test_rejects_unknown_rule_id(self) -> None:
        treasury = default_treasury(_now_iso())
        updated, error = toggle_rule(treasury, "does-not-exist", False, now_iso=_now_iso())
        assert error is not None
        assert updated == treasury


class TestPauseAllRules:
    def test_pauses_every_active_rule(self) -> None:
        treasury, _ = create_rule(default_treasury(_now_iso()), "percent_of_monthly_profit", percent=5.0, reserve_target=None, now_iso=_now_iso(), rule_id="rule-1")
        treasury, _ = create_rule(treasury, "excess_above_reserve", percent=0.0, reserve_target=10_000.0, now_iso=_now_iso(), rule_id="rule-2")
        paused = pause_all_rules(treasury, now_iso=_now_iso())
        assert all(not r.active for r in paused.savings_rules)


class TestApplyMonthlySavingsRules:
    def test_percent_rule_saves_a_real_share_of_profit(self) -> None:
        treasury, _ = create_rule(default_treasury(_now_iso()), "percent_of_monthly_profit", percent=10.0, reserve_target=None, now_iso=_now_iso(), rule_id="rule-1")
        portfolio = default_portfolio()
        new_treasury, new_portfolio = apply_monthly_savings_rules(
            treasury, portfolio, monthly_profit_dollars=1_000.0, sim_day=30, now_iso=_now_iso(), id_prefix="treasury-auto-30"
        )
        assert new_treasury.balance == 100.0
        assert new_portfolio.cash_balance == portfolio.cash_balance - 100.0
        assert new_treasury.transactions[0].kind == "auto_save"

    def test_percent_rule_does_not_fire_on_a_losing_month(self) -> None:
        treasury, _ = create_rule(default_treasury(_now_iso()), "percent_of_monthly_profit", percent=10.0, reserve_target=None, now_iso=_now_iso(), rule_id="rule-1")
        portfolio = default_portfolio()
        new_treasury, new_portfolio = apply_monthly_savings_rules(
            treasury, portfolio, monthly_profit_dollars=-500.0, sim_day=30, now_iso=_now_iso(), id_prefix="treasury-auto-30"
        )
        assert new_treasury.balance == 0.0
        assert new_portfolio == portfolio

    def test_inactive_rule_does_not_fire(self) -> None:
        treasury, _ = create_rule(default_treasury(_now_iso()), "percent_of_monthly_profit", percent=10.0, reserve_target=None, now_iso=_now_iso(), rule_id="rule-1")
        treasury, _ = toggle_rule(treasury, "rule-1", False, now_iso=_now_iso())
        portfolio = default_portfolio()
        new_treasury, new_portfolio = apply_monthly_savings_rules(
            treasury, portfolio, monthly_profit_dollars=1_000.0, sim_day=30, now_iso=_now_iso(), id_prefix="treasury-auto-30"
        )
        assert new_treasury.balance == 0.0
        assert new_portfolio == portfolio

    def test_excess_above_reserve_moves_only_the_real_surplus(self) -> None:
        treasury, _ = create_rule(default_treasury(_now_iso()), "excess_above_reserve", percent=0.0, reserve_target=20_000.0, now_iso=_now_iso(), rule_id="rule-2")
        portfolio = default_portfolio().model_copy(update={"cash_balance": 25_000.0})
        new_treasury, new_portfolio = apply_monthly_savings_rules(
            treasury, portfolio, monthly_profit_dollars=0.0, sim_day=30, now_iso=_now_iso(), id_prefix="treasury-auto-30"
        )
        assert new_treasury.balance == 5_000.0
        assert new_portfolio.cash_balance == 20_000.0

    def test_excess_above_reserve_does_nothing_when_already_under_target(self) -> None:
        treasury, _ = create_rule(default_treasury(_now_iso()), "excess_above_reserve", percent=0.0, reserve_target=20_000.0, now_iso=_now_iso(), rule_id="rule-2")
        portfolio = default_portfolio().model_copy(update={"cash_balance": 5_000.0})
        new_treasury, new_portfolio = apply_monthly_savings_rules(
            treasury, portfolio, monthly_profit_dollars=0.0, sim_day=30, now_iso=_now_iso(), id_prefix="treasury-auto-30"
        )
        assert new_treasury.balance == 0.0
        assert new_portfolio.cash_balance == 5_000.0

    def test_both_rules_can_fire_together(self) -> None:
        treasury, _ = create_rule(default_treasury(_now_iso()), "percent_of_monthly_profit", percent=10.0, reserve_target=None, now_iso=_now_iso(), rule_id="rule-1")
        treasury, _ = create_rule(treasury, "excess_above_reserve", percent=0.0, reserve_target=20_000.0, now_iso=_now_iso(), rule_id="rule-2")
        portfolio = default_portfolio().model_copy(update={"cash_balance": 25_000.0})
        new_treasury, new_portfolio = apply_monthly_savings_rules(
            treasury, portfolio, monthly_profit_dollars=1_000.0, sim_day=30, now_iso=_now_iso(), id_prefix="treasury-auto-30"
        )
        # 10% of profit ($100) plus the surplus above the reserve, computed
        # against cash *after* the percent-rule deposit already left it.
        assert new_treasury.balance == 100.0 + (24_900.0 - 20_000.0)
        assert len(new_treasury.transactions) == 2


class TestRecordMonthlyReport:
    def test_sums_only_transactions_in_the_trailing_thirty_days(self) -> None:
        treasury = default_treasury(_now_iso())
        treasury, _, _ = deposit(treasury, default_portfolio(), 1_000.0, sim_day=1, now_iso=_now_iso(), transaction_id="old-deposit")
        treasury, _, _ = deposit(treasury, default_portfolio(), 500.0, sim_day=40, now_iso=_now_iso(), transaction_id="recent-deposit")
        reported = record_monthly_report(treasury, month_ending_day=45, now_iso=_now_iso(), report_id="report-1")
        report = reported.monthly_reports[0]
        assert report.deposits == 500.0
        assert report.ending_balance == treasury.balance

    def test_caps_the_report_history(self) -> None:
        treasury = default_treasury(_now_iso())
        for day in range(MAX_TREASURY_MONTHLY_REPORTS + 10):
            treasury = record_monthly_report(treasury, month_ending_day=day * 30, now_iso=_now_iso(), report_id=f"report-{day}")
        assert len(treasury.monthly_reports) == MAX_TREASURY_MONTHLY_REPORTS


class TestTransactionCap:
    def test_caps_the_transaction_history(self) -> None:
        treasury = default_treasury(_now_iso())
        portfolio = default_portfolio().model_copy(update={"cash_balance": 10_000_000.0})
        for i in range(MAX_TREASURY_TRANSACTIONS + 20):
            treasury, portfolio, error = deposit(treasury, portfolio, 1.0, sim_day=1, now_iso=_now_iso(), transaction_id=f"deposit-{i}")
            assert error is None
        assert len(treasury.transactions) == MAX_TREASURY_TRANSACTIONS
        assert treasury.lifetime_deposits == MAX_TREASURY_TRANSACTIONS + 20
