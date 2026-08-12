"""Covers app/rule_engine.py — Design Bible Chapter 69 Part 3, the
Institutional Rule Engine's one centralized evaluator for every
account's own Custom Rules. Each rule type is an individually
auditable, real comparison against the account's own already-real state
(RiskLimits fields, Part 2's trailing-drawdown/consistency computations,
the current weekday) — never a hidden blend. This module does not block
trades itself (see its own docstring's Rule Execution Order note); it
only evaluates.
"""
from __future__ import annotations

from app.accounts import create_account
from app.risk_engine import default_risk_limits
from app.rule_engine import CORRECTIVE_ACTIONS, RULE_TYPE_LABELS, evaluate_rules
from app.schemas import Account, PaperPosition, PaperTrade, Rule


def _account(*, starting_balance: float = 10_000.0, risk_limits_overrides: dict[str, object] | None = None) -> Account:
    base = default_risk_limits().model_copy(update=risk_limits_overrides or {})
    accounts, error = create_account(
        [], name="Rule Engine Test", account_type="personal", starting_balance=starting_balance, base_risk_limits=base, account_id="acct-1", now_iso="2026-01-01T00:00:00Z"
    )
    assert error is None
    return accounts[0]


def _with_rule(account: Account, rule: Rule) -> Account:
    return account.model_copy(update={"custom_rules": [*account.custom_rules, rule]})


def _rule(rule_type: str, *, limit: float = 10.0, weekday: str | None = None, enabled: bool = True) -> Rule:
    return Rule(id=f"rule-{rule_type}", ruleType=rule_type, label="", limit=limit, weekday=weekday, enabled=enabled)  # type: ignore[arg-type]


def _position(*, quantity: float = 1.0, price: float = 100.0) -> PaperPosition:
    return PaperPosition(
        id="pos-1", symbol="AAPL", side="buy", quantity=quantity, entryPrice=price, currentPrice=price,  # type: ignore[arg-type]
        unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="atlas", confidence=70.0,  # type: ignore[arg-type]
        openedAt="2026-01-01T00:00:00Z", openedSimMinutes=0,
    )


def _closed_trade(*, pnl: float, closed_sim_minutes: int) -> PaperTrade:
    return PaperTrade(
        id=f"trade-{closed_sim_minutes}", symbol="AAPL", side="buy", quantity=1.0, entryPrice=100.0, exitPrice=100.0 + pnl,  # type: ignore[arg-type]
        pnl=pnl, pnlPct=pnl, durationMinutes=60, confidence=70.0, reason="test", marketConditions="test",
        openedAt="2026-01-01T00:00:00Z", closedAt="2026-01-01T01:00:00Z", openedSimMinutes=closed_sim_minutes - 60, closedSimMinutes=closed_sim_minutes,
    )


class TestEvaluateRulesFramework:
    def test_no_rules_means_an_automatic_all_passed(self) -> None:
        account = _account()
        result = evaluate_rules(account, sim_day=1)
        assert result.checks == []
        assert result.all_passed is True

    def test_disabled_rules_are_skipped_entirely_not_auto_passed(self) -> None:
        account = _with_rule(_account(), _rule("max_open_positions", limit=0.0, enabled=False))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks == []
        assert result.all_passed is True

    def test_a_failing_rule_flips_all_passed_to_false_and_includes_a_corrective_action(self) -> None:
        account = _with_rule(_account(), _rule("max_open_positions", limit=0.0))
        portfolio = account.portfolio.model_copy(update={"positions": [_position()]})
        account = account.model_copy(update={"portfolio": portfolio})
        result = evaluate_rules(account, sim_day=1)
        assert result.all_passed is False
        assert result.checks[0].passed is False
        assert result.checks[0].corrective_action == CORRECTIVE_ACTIONS["max_open_positions"]

    def test_a_passing_rule_has_no_corrective_action(self) -> None:
        account = _with_rule(_account(), _rule("max_open_positions", limit=5.0))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks[0].passed is True
        assert result.checks[0].corrective_action is None

    def test_rule_with_no_label_falls_back_to_the_type_label(self) -> None:
        account = _with_rule(_account(), _rule("max_open_positions", limit=5.0))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks[0].label == RULE_TYPE_LABELS["max_open_positions"]

    def test_multiple_enabled_rules_are_each_evaluated_independently(self) -> None:
        account = _account()
        account = _with_rule(account, _rule("max_open_positions", limit=5.0))
        account = _with_rule(account, _rule("max_daily_loss_pct", limit=1.0))
        result = evaluate_rules(account, sim_day=1)
        assert len(result.checks) == 2


class TestMaxDailyLossRule:
    def test_passes_when_todays_loss_is_within_the_limit(self) -> None:
        account = _account()
        portfolio = account.portfolio.model_copy(update={"total_pnl_pct": -2.0})
        account = _with_rule(account.model_copy(update={"portfolio": portfolio}), _rule("max_daily_loss_pct", limit=5.0))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks[0].passed is True

    def test_fails_when_todays_loss_exceeds_the_limit(self) -> None:
        account = _account()
        portfolio = account.portfolio.model_copy(update={"total_pnl_pct": -8.0})
        account = _with_rule(account.model_copy(update={"portfolio": portfolio}), _rule("max_daily_loss_pct", limit=5.0))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks[0].passed is False

    def test_a_profitable_day_never_fails_a_loss_rule(self) -> None:
        account = _account()
        portfolio = account.portfolio.model_copy(update={"total_pnl_pct": 10.0})
        account = _with_rule(account.model_copy(update={"portfolio": portfolio}), _rule("max_daily_loss_pct", limit=1.0))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks[0].passed is True


class TestMaxDrawdownRule:
    def test_fails_once_lifetime_drawdown_from_starting_balance_exceeds_the_limit(self) -> None:
        account = _account(starting_balance=10_000.0)
        drained = account.portfolio.model_copy(update={"cash_balance": 8_000.0})  # 20% lifetime drawdown
        account = _with_rule(account.model_copy(update={"portfolio": drained}), _rule("max_drawdown_pct", limit=10.0))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks[0].passed is False


class TestMaxPositionSizeRule:
    def test_fails_when_the_largest_position_exceeds_the_pct_of_equity_limit(self) -> None:
        account = _account(starting_balance=1_000.0)
        big_position = _position(quantity=5.0, price=100.0)  # $500 of $1000 equity = 50%
        portfolio = account.portfolio.model_copy(update={"positions": [big_position], "cash_balance": 500.0})
        account = _with_rule(account.model_copy(update={"portfolio": portfolio}), _rule("max_position_pct", limit=25.0))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks[0].passed is False

    def test_passes_with_no_open_positions(self) -> None:
        account = _with_rule(_account(), _rule("max_position_pct", limit=10.0))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks[0].passed is True


class TestMaxOpenPositionsRule:
    def test_fails_once_open_count_exceeds_the_limit(self) -> None:
        account = _account()
        portfolio = account.portfolio.model_copy(update={"positions": [_position(), _position()]})
        account = _with_rule(account.model_copy(update={"portfolio": portfolio}), _rule("max_open_positions", limit=1.0))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks[0].passed is False


class TestMaxRiskPerTradeRule:
    def test_reads_the_accounts_own_configured_risk_per_trade_pct(self) -> None:
        account = _account(risk_limits_overrides={"risk_per_trade_pct": 3.0})
        account = _with_rule(account, _rule("max_risk_per_trade_pct", limit=2.0))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks[0].passed is False

    def test_passes_when_configured_risk_is_within_the_rule_limit(self) -> None:
        account = _account(risk_limits_overrides={"risk_per_trade_pct": 1.0})
        account = _with_rule(account, _rule("max_risk_per_trade_pct", limit=2.0))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks[0].passed is True


class TestTrailingDrawdownRule:
    def test_fails_once_the_accounts_own_trailing_drawdown_exceeds_the_rule_limit(self) -> None:
        account = _account(starting_balance=10_000.0)
        account = account.model_copy(update={"peak_equity": 10_000.0})
        drained = account.portfolio.model_copy(update={"cash_balance": 9_000.0})  # 10% trailing drawdown
        account = _with_rule(account.model_copy(update={"portfolio": drained}), _rule("trailing_drawdown_pct", limit=5.0))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks[0].passed is False


class TestConsistencyRule:
    def test_not_yet_applicable_passes_by_default(self) -> None:
        account = _with_rule(_account(), _rule("consistency_pct", limit=50.0))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks[0].passed is True
        assert "not yet applicable" in result.checks[0].detail.lower()

    def test_fails_once_one_days_profit_share_exceeds_the_rule_limit(self) -> None:
        account = _account()
        account = account.model_copy(update={"challenge_start_sim_day": 0})
        trades = [_closed_trade(pnl=100.0, closed_sim_minutes=1440 + 60), _closed_trade(pnl=900.0, closed_sim_minutes=2 * 1440 + 60)]
        portfolio = account.portfolio.model_copy(update={"trade_history": trades})
        account = _with_rule(account.model_copy(update={"portfolio": portfolio}), _rule("consistency_pct", limit=50.0))
        result = evaluate_rules(account, sim_day=5)
        assert result.checks[0].passed is False


class TestNoTradingOnWeekdayRule:
    def test_fails_on_the_configured_blocked_weekday(self) -> None:
        account = _with_rule(_account(), _rule("no_trading_on_weekday", weekday="monday"))
        result = evaluate_rules(account, sim_day=1)  # day 1 is a Monday
        assert result.checks[0].passed is False

    def test_passes_on_any_other_weekday(self) -> None:
        account = _with_rule(_account(), _rule("no_trading_on_weekday", weekday="monday"))
        result = evaluate_rules(account, sim_day=2)  # day 2 is a Tuesday
        assert result.checks[0].passed is True

    def test_no_weekday_configured_never_blocks(self) -> None:
        account = _with_rule(_account(), _rule("no_trading_on_weekday", weekday=None))
        result = evaluate_rules(account, sim_day=1)
        assert result.checks[0].passed is True
