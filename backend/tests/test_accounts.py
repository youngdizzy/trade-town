"""Covers app/accounts.py — Design Bible Chapter 69 Part 1, the
Multi-Account & Fund Management System's real capital-pool layer. Every
account operation reuses app/treasury.py's own real deposit()/withdraw()
and app/risk_engine.py's own portfolio_equity() — never a second,
parallel transfer or equity mechanism. See the module's own docstring
for the full honesty boundary (no live per-account trade execution yet).
"""
from __future__ import annotations

from app.accounts import (
    MAX_ACCOUNTS,
    account_equity,
    add_custom_rule,
    allocate_capital,
    close_account,
    configure_evaluation_tracking,
    configure_prop_firm_rules,
    create_account,
    deallocate_capital,
    default_risk_limits_for,
    mark_account_funded,
    record_account_payout,
    remove_custom_rule,
    toggle_custom_rule,
    total_capital_across_accounts,
)
from app.portfolio import STARTING_BALANCE, default_portfolio
from app.risk_engine import default_risk_limits
from app.schemas import Account, AccountType, PaperPosition
from app.treasury import default_treasury


def _account(*, account_type: AccountType = "personal", starting_balance: float = 10_000.0, account_id: str = "acct-1") -> Account:
    accounts, error = create_account(
        [],
        name="Test Account",
        account_type=account_type,
        starting_balance=starting_balance,
        base_risk_limits=default_risk_limits(),
        account_id=account_id,
        now_iso="2026-01-01T00:00:00Z",
    )
    assert error is None
    return accounts[0]


def _position(*, symbol: str = "AAPL", quantity: float = 10.0, price: float = 100.0) -> PaperPosition:
    return PaperPosition(
        id=f"pos-{symbol}",
        symbol=symbol,
        side="buy",  # type: ignore[arg-type]
        quantity=quantity,
        entryPrice=price,
        currentPrice=price,
        unrealizedPnl=0.0,
        unrealizedPnlPct=0.0,
        openedBy="atlas",  # type: ignore[arg-type]
        confidence=70.0,
        openedAt="2026-01-01T00:00:00Z",
        openedSimMinutes=0,
    )


class TestDefaultRiskLimitsFor:
    def test_non_prop_firm_gets_an_untouched_copy_of_the_base_limits(self) -> None:
        base = default_risk_limits()
        limits = default_risk_limits_for("personal", base)
        assert limits.max_drawdown_pct == base.max_drawdown_pct
        assert limits is not base

    def test_prop_firm_tightens_max_drawdown_to_10_pct_when_base_is_looser(self) -> None:
        base = default_risk_limits().model_copy(update={"max_drawdown_pct": 20.0})
        limits = default_risk_limits_for("prop_firm", base)
        assert limits.max_drawdown_pct == 10.0

    def test_prop_firm_never_loosens_a_base_already_tighter_than_10_pct(self) -> None:
        base = default_risk_limits().model_copy(update={"max_drawdown_pct": 5.0})
        limits = default_risk_limits_for("prop_firm", base)
        assert limits.max_drawdown_pct == 5.0


class TestAccountEquity:
    def test_equals_cash_balance_with_no_positions(self) -> None:
        account = _account(starting_balance=25_000.0)
        assert account_equity(account) == 25_000.0

    def test_includes_open_position_market_value(self) -> None:
        account = _account(starting_balance=10_000.0)
        position = _position(quantity=5.0, price=200.0)
        portfolio = account.portfolio.model_copy(update={"positions": [position], "cash_balance": account.portfolio.cash_balance - 1000.0})
        account = account.model_copy(update={"portfolio": portfolio})
        assert account_equity(account) == 9_000.0 + 1_000.0


class TestTotalCapitalAcrossAccounts:
    def test_sums_primary_portfolio_treasury_and_every_account(self) -> None:
        primary = default_portfolio()
        treasury = default_treasury("2026-01-01T00:00:00Z").model_copy(update={"balance": 5_000.0})
        accounts = [_account(starting_balance=1_000.0, account_id="a"), _account(starting_balance=2_000.0, account_id="b")]
        total = total_capital_across_accounts(primary, treasury, accounts)
        assert total == STARTING_BALANCE + 5_000.0 + 1_000.0 + 2_000.0


class TestCreateAccount:
    def test_creates_a_real_isolated_portfolio_with_the_given_starting_balance(self) -> None:
        accounts, error = create_account(
            [], name="My IRA", account_type="ira", starting_balance=15_000.0, base_risk_limits=default_risk_limits(), account_id="ira-1", now_iso="2026-01-01T00:00:00Z"
        )
        assert error is None
        assert len(accounts) == 1
        account = accounts[0]
        assert account.name == "My IRA"
        assert account.account_type == "ira"
        assert account.portfolio.cash_balance == 15_000.0
        assert account.portfolio.starting_balance == 15_000.0
        assert account.peak_equity == 15_000.0

    def test_rejects_a_blank_name(self) -> None:
        accounts, error = create_account([], name="   ", account_type="personal", starting_balance=1_000.0, base_risk_limits=default_risk_limits(), account_id="x", now_iso="now")
        assert error is not None
        assert accounts == []

    def test_rejects_a_non_positive_starting_balance(self) -> None:
        accounts, error = create_account([], name="X", account_type="personal", starting_balance=0.0, base_risk_limits=default_risk_limits(), account_id="x", now_iso="now")
        assert error is not None
        assert accounts == []

    def test_rejects_creation_past_the_max_account_cap(self) -> None:
        accounts: list[Account] = []
        for i in range(MAX_ACCOUNTS):
            accounts, error = create_account(accounts, name=f"A{i}", account_type="personal", starting_balance=1.0, base_risk_limits=default_risk_limits(), account_id=f"a{i}", now_iso="now")
            assert error is None
        accounts, error = create_account(accounts, name="One Too Many", account_type="personal", starting_balance=1.0, base_risk_limits=default_risk_limits(), account_id="overflow", now_iso="now")
        assert error is not None
        assert len(accounts) == MAX_ACCOUNTS


class TestCloseAccount:
    def test_closes_a_fully_deallocated_empty_account(self) -> None:
        account = _account(starting_balance=1_000.0)
        drained_portfolio = account.portfolio.model_copy(update={"cash_balance": 0.0})
        account = account.model_copy(update={"portfolio": drained_portfolio})
        accounts, error = close_account([account], account.id)
        assert error is None
        assert accounts == []

    def test_refuses_to_close_an_account_still_holding_real_cash(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = close_account([account], account.id)
        assert error is not None
        assert accounts == [account]

    def test_refuses_to_close_an_account_with_an_open_position(self) -> None:
        account = _account(starting_balance=1_000.0)
        drained_with_position = account.portfolio.model_copy(update={"cash_balance": 0.0, "positions": [_position()]})
        account = account.model_copy(update={"portfolio": drained_with_position})
        accounts, error = close_account([account], account.id)
        assert error is not None
        assert accounts == [account]

    def test_unknown_account_id_is_a_real_error_not_a_silent_noop(self) -> None:
        accounts, error = close_account([], "does-not-exist")
        assert error is not None


class TestAllocateAndDeallocateCapital:
    def test_allocate_moves_real_capital_from_treasury_into_the_account(self) -> None:
        account = _account(starting_balance=1_000.0)
        treasury = default_treasury("2026-01-01T00:00:00Z").model_copy(update={"balance": 5_000.0})
        accounts, new_treasury, error = allocate_capital([account], treasury, account.id, 2_000.0, sim_day=1, now_iso="2026-01-01T00:00:00Z", transaction_id="tx-1")
        assert error is None
        assert new_treasury.balance == 3_000.0
        assert accounts[0].portfolio.cash_balance == 3_000.0

    def test_allocate_updates_peak_equity_when_the_transfer_raises_it(self) -> None:
        account = _account(starting_balance=1_000.0)
        treasury = default_treasury("2026-01-01T00:00:00Z").model_copy(update={"balance": 5_000.0})
        accounts, _, error = allocate_capital([account], treasury, account.id, 2_000.0, sim_day=1, now_iso="2026-01-01T00:00:00Z", transaction_id="tx-1")
        assert error is None
        assert accounts[0].peak_equity == 3_000.0

    def test_allocate_rejects_more_than_the_treasury_actually_holds(self) -> None:
        account = _account(starting_balance=1_000.0)
        treasury = default_treasury("2026-01-01T00:00:00Z").model_copy(update={"balance": 500.0})
        accounts, new_treasury, error = allocate_capital([account], treasury, account.id, 2_000.0, sim_day=1, now_iso="2026-01-01T00:00:00Z", transaction_id="tx-1")
        assert error is not None
        assert new_treasury.balance == 500.0
        assert accounts[0].portfolio.cash_balance == 1_000.0

    def test_allocate_to_an_unknown_account_is_a_real_error(self) -> None:
        treasury = default_treasury("2026-01-01T00:00:00Z").model_copy(update={"balance": 5_000.0})
        accounts, new_treasury, error = allocate_capital([], treasury, "nope", 100.0, sim_day=1, now_iso="now", transaction_id="tx")
        assert error is not None
        assert new_treasury == treasury

    def test_deallocate_moves_real_capital_from_the_account_back_to_treasury(self) -> None:
        account = _account(starting_balance=3_000.0)
        treasury = default_treasury("2026-01-01T00:00:00Z")
        accounts, new_treasury, error = deallocate_capital([account], treasury, account.id, 1_000.0, sim_day=1, now_iso="2026-01-01T00:00:00Z", transaction_id="tx-2")
        assert error is None
        assert new_treasury.balance == 1_000.0
        assert accounts[0].portfolio.cash_balance == 2_000.0

    def test_deallocate_rejects_more_than_the_account_actually_holds(self) -> None:
        account = _account(starting_balance=500.0)
        treasury = default_treasury("2026-01-01T00:00:00Z")
        accounts, new_treasury, error = deallocate_capital([account], treasury, account.id, 1_000.0, sim_day=1, now_iso="now", transaction_id="tx")
        assert error is not None
        assert accounts[0].portfolio.cash_balance == 500.0
        assert new_treasury.balance == 0.0


class TestConfigurePropFirmRules:
    def test_sets_every_provided_field_on_the_target_account_only(self) -> None:
        target = _account(starting_balance=1_000.0, account_id="target")
        other = _account(starting_balance=1_000.0, account_id="other")
        accounts, error = configure_prop_firm_rules(
            [target, other],
            "target",
            trailing_drawdown_limit_pct=8.0,
            consistency_limit_pct=40.0,
            challenge_start_sim_day=1,
            challenge_duration_days=30,
            challenge_profit_target_pct=10.0,
        )
        assert error is None
        updated_target = next(a for a in accounts if a.id == "target")
        updated_other = next(a for a in accounts if a.id == "other")
        assert updated_target.trailing_drawdown_limit_pct == 8.0
        assert updated_target.consistency_limit_pct == 40.0
        assert updated_target.challenge_duration_days == 30
        assert updated_other.trailing_drawdown_limit_pct is None

    def test_rejects_a_non_positive_trailing_drawdown_limit(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = configure_prop_firm_rules(
            [account], account.id, trailing_drawdown_limit_pct=0.0, consistency_limit_pct=None, challenge_start_sim_day=None, challenge_duration_days=None, challenge_profit_target_pct=None
        )
        assert error is not None

    def test_rejects_a_consistency_limit_outside_0_to_100(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = configure_prop_firm_rules(
            [account], account.id, trailing_drawdown_limit_pct=None, consistency_limit_pct=150.0, challenge_start_sim_day=None, challenge_duration_days=None, challenge_profit_target_pct=None
        )
        assert error is not None

    def test_rejects_a_non_positive_challenge_duration(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = configure_prop_firm_rules(
            [account], account.id, trailing_drawdown_limit_pct=None, consistency_limit_pct=None, challenge_start_sim_day=1, challenge_duration_days=0, challenge_profit_target_pct=None
        )
        assert error is not None


class TestConfigureEvaluationTracking:
    def test_sets_both_fields_on_the_target_account_only(self) -> None:
        target = _account(starting_balance=1_000.0, account_id="target")
        other = _account(starting_balance=1_000.0, account_id="other")
        accounts, error = configure_evaluation_tracking([target, other], "target", evaluation_cost=150.0, payout_eligibility_min_profit_pct=8.0)
        assert error is None
        updated_target = next(a for a in accounts if a.id == "target")
        updated_other = next(a for a in accounts if a.id == "other")
        assert updated_target.evaluation_cost == 150.0
        assert updated_target.payout_eligibility_min_profit_pct == 8.0
        assert updated_other.evaluation_cost is None

    def test_rejects_a_negative_evaluation_cost(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = configure_evaluation_tracking([account], account.id, evaluation_cost=-1.0, payout_eligibility_min_profit_pct=None)
        assert error is not None

    def test_rejects_a_non_positive_payout_eligibility_threshold(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = configure_evaluation_tracking([account], account.id, evaluation_cost=None, payout_eligibility_min_profit_pct=0.0)
        assert error is not None

    def test_unknown_account_returns_an_error(self) -> None:
        accounts, error = configure_evaluation_tracking([], "nope", evaluation_cost=100.0, payout_eligibility_min_profit_pct=None)
        assert error is not None


class TestMarkAccountFunded:
    def test_marks_the_account_funded_on_the_real_sim_day(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = mark_account_funded([account], account.id, sim_day=12)
        assert error is None
        updated = accounts[0]
        assert updated.funded_stage_reached is True
        assert updated.funded_at_sim_day == 12

    def test_refuses_to_re_mark_an_already_funded_account(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = mark_account_funded([account], account.id, sim_day=12)
        assert error is None
        accounts, error = mark_account_funded(accounts, account.id, sim_day=99)
        assert error is not None
        assert accounts[0].funded_at_sim_day == 12

    def test_unknown_account_returns_an_error(self) -> None:
        accounts, error = mark_account_funded([], "nope", sim_day=1)
        assert error is not None


class TestRecordAccountPayout:
    def test_requires_the_account_to_already_be_funded(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = record_account_payout([account], account.id, amount=500.0)
        assert error is not None
        assert accounts[0].total_payouts_received == 0.0

    def test_adds_to_the_permanent_running_total_once_funded(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = mark_account_funded([account], account.id, sim_day=5)
        assert error is None
        accounts, error = record_account_payout(accounts, account.id, amount=500.0)
        assert error is None
        assert accounts[0].total_payouts_received == 500.0
        accounts, error = record_account_payout(accounts, account.id, amount=250.0)
        assert error is None
        assert accounts[0].total_payouts_received == 750.0

    def test_rejects_a_non_positive_amount(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = mark_account_funded([account], account.id, sim_day=5)
        assert error is None
        accounts, error = record_account_payout(accounts, account.id, amount=0.0)
        assert error is not None

    def test_unknown_account_returns_an_error(self) -> None:
        accounts, error = record_account_payout([], "nope", amount=100.0)
        assert error is not None


class TestCustomRules:
    def test_add_custom_rule_appends_a_real_rule_to_the_account(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = add_custom_rule([account], account.id, rule_type="max_open_positions", label="Cap positions", limit=3.0, weekday=None, rule_id="rule-1")
        assert error is None
        assert len(accounts[0].custom_rules) == 1
        assert accounts[0].custom_rules[0].enabled is True

    def test_no_trading_on_weekday_requires_a_weekday(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = add_custom_rule([account], account.id, rule_type="no_trading_on_weekday", label="No Friday trades", limit=0.0, weekday=None, rule_id="rule-1")
        assert error is not None
        assert accounts[0].custom_rules == []

    def test_non_weekday_rule_requires_a_positive_limit(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = add_custom_rule([account], account.id, rule_type="max_open_positions", label="Bad limit", limit=0.0, weekday=None, rule_id="rule-1")
        assert error is not None

    def test_rejects_adding_past_the_per_account_rule_cap(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts = [account]
        for i in range(20):
            accounts, error = add_custom_rule(accounts, account.id, rule_type="max_open_positions", label=f"Rule {i}", limit=3.0, weekday=None, rule_id=f"rule-{i}")
            assert error is None
        accounts, error = add_custom_rule(accounts, account.id, rule_type="max_open_positions", label="Overflow", limit=3.0, weekday=None, rule_id="overflow")
        assert error is not None
        assert len(accounts[0].custom_rules) == 20

    def test_remove_custom_rule_deletes_only_the_named_rule(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, _ = add_custom_rule([account], account.id, rule_type="max_open_positions", label="Keep", limit=3.0, weekday=None, rule_id="keep")
        accounts, _ = add_custom_rule(accounts, account.id, rule_type="max_open_positions", label="Remove", limit=3.0, weekday=None, rule_id="remove")
        accounts, error = remove_custom_rule(accounts, account.id, "remove")
        assert error is None
        assert [r.id for r in accounts[0].custom_rules] == ["keep"]

    def test_remove_unknown_rule_is_a_real_error(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, error = remove_custom_rule([account], account.id, "does-not-exist")
        assert error is not None

    def test_toggle_custom_rule_flips_enabled_state(self) -> None:
        account = _account(starting_balance=1_000.0)
        accounts, _ = add_custom_rule([account], account.id, rule_type="max_open_positions", label="Toggle me", limit=3.0, weekday=None, rule_id="toggle")
        accounts, error = toggle_custom_rule(accounts, account.id, "toggle", False)
        assert error is None
        assert accounts[0].custom_rules[0].enabled is False
