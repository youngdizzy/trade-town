"""Accounts — Design Bible Chapter 69 Part 1, the real capital-pool layer
behind the Multi-Account & Fund Management System.

`app/portfolio.py`'s single `PaperPortfolio` (the company's one trading
account) and `app/treasury.py`'s `TreasuryState` (the CEO's own isolated
capital) were this chapter's real precedent: two genuinely isolated
capital pools, already proven out. This module generalizes that same
pattern to more than two pools, honestly, rather than inventing a
parallel system:

- Every `Account` embeds a real `PaperPortfolio` (see schemas.py's
  `Account`), so `app/risk_engine.py`'s `portfolio_equity()` and every
  other function that already operates on a `PaperPortfolio` works on an
  account's own portfolio for free — no duplicated equity math.
- Capital allocation between the Treasury and an account reuses
  `app/treasury.py`'s own real, validated, transaction-recording
  `deposit()`/`withdraw()` functions directly (they're already generic
  over any `PaperPortfolio`, not hardcoded to the primary one) — never a
  second, parallel transfer mechanism.

Honest scope, not deferred silently: live trading execution (a new
TradeProposal opening a position IN a chosen non-primary account) is not
wired here. That would mean parameterizing the entire trading pipeline
(app/executive.py's proposal/resolve flow, the Trade Gatekeeper, Sentinel/
Guardian's risk checks) by account — a materially larger change than a
capital-ledger layer. What IS real: creating an account, giving it its
own editable RiskLimits profile, moving real capital into and out of it
from the Treasury, and tracking its own equity over time — a real,
CEO-manageable multi-account ledger, honestly short of live per-account
trading. See the Design Bible chapter's own Future Expansion section.
"""
from __future__ import annotations

from app.risk_engine import portfolio_equity
from app.schemas import Account, AccountType, PaperPortfolio, RiskLimits, Rule, RuleType, TreasuryState, Weekday
from app.treasury import deposit as treasury_deposit
from app.treasury import withdraw as treasury_withdraw

MAX_ACCOUNTS = 12

ACCOUNT_TYPE_LABELS: dict[AccountType, str] = {
    "personal": "Personal Trading Account",
    "ira": "IRA / Retirement Account",
    "business": "Business Trading Account",
    "prop_firm": "Prop Firm Challenge Account",
    "family": "Family Trust Account",
}


def default_risk_limits_for(account_type: AccountType, base: RiskLimits) -> RiskLimits:
    """A real starting risk profile per account — a copy of the CEO's own
    current global RiskLimits (no per-account-type defaults exist to draw
    from otherwise; the CEO can edit any account's profile afterward).
    Prop Firm accounts additionally start with a tighter default max
    drawdown (10%, never loosened from whatever the base already was) —
    the one real, checkable rule every real prop firm challenge shares,
    matching this chapter's own Part 2 (Prop Firm Rule Engine)."""
    if account_type == "prop_firm":
        return base.model_copy(update={"max_drawdown_pct": min(base.max_drawdown_pct, 10.0)})
    return base.model_copy()


def account_equity(account: Account) -> float:
    return portfolio_equity(account.portfolio)


def total_capital_across_accounts(portfolio: PaperPortfolio, treasury: TreasuryState, accounts: list[Account]) -> float:
    """The Master Dashboard's real cross-account aggregation — the
    primary PaperPortfolio's own equity, plus the Treasury, plus every
    sub-account's own real equity. Computed fresh, never stored, so it
    can never silently drift out of sync with the real balances it
    reads (same convention as app/treasury.py's reserve_percentage)."""
    return portfolio_equity(portfolio) + treasury.balance + sum(account_equity(a) for a in accounts)


def create_account(
    accounts: list[Account],
    *,
    name: str,
    account_type: AccountType,
    starting_balance: float,
    base_risk_limits: RiskLimits,
    account_id: str,
    now_iso: str,
) -> tuple[list[Account], str | None]:
    if len(accounts) >= MAX_ACCOUNTS:
        return accounts, f"Maximum of {MAX_ACCOUNTS} accounts reached."
    if not name.strip():
        return accounts, "Account name is required."
    if starting_balance <= 0:
        return accounts, "Starting balance must be greater than 0."
    portfolio = PaperPortfolio(
        cashBalance=starting_balance,
        startingBalance=starting_balance,
        positions=[],
        orders=[],
        tradeHistory=[],
        totalPnl=0.0,
        totalPnlPct=0.0,
        winCount=0,
        lossCount=0,
    )
    account = Account(
        id=account_id,
        name=name.strip(),
        accountType=account_type,
        portfolio=portfolio,
        riskLimits=default_risk_limits_for(account_type, base_risk_limits),
        createdAt=now_iso,
        peakEquity=starting_balance,
    )
    return [*accounts, account], None


def close_account(accounts: list[Account], account_id: str) -> tuple[list[Account], str | None]:
    """Real safety check, not a silent fund loss: an account can only be
    closed once it's been fully deallocated back to the Treasury (zero
    cash) and holds no open positions — never closed with real capital
    still sitting inside it."""
    account = next((a for a in accounts if a.id == account_id), None)
    if account is None:
        return accounts, f"No account with id {account_id!r}."
    if account.portfolio.cash_balance > 0 or account.portfolio.positions:
        return accounts, f"{account.name} still holds real capital or open positions — deallocate it back to the Treasury first."
    return [a for a in accounts if a.id != account_id], None


def _with_updated_peak_equity(account: Account) -> Account:
    """Design Bible Chapter 69 Part 2 — the Trailing Drawdown Engine's
    real high-water mark. Monotonically non-decreasing by definition (a
    real peak never moves down); called after every real change to an
    account's own equity so app/prop_firm.py's trailing-drawdown check
    always trails from the account's true historical peak, not a stale
    one."""
    current_equity = account_equity(account)
    if current_equity > account.peak_equity:
        return account.model_copy(update={"peak_equity": current_equity})
    return account


def allocate_capital(
    accounts: list[Account], treasury: TreasuryState, account_id: str, amount: float, *, sim_day: int, now_iso: str, transaction_id: str
) -> tuple[list[Account], TreasuryState, str | None]:
    """Treasury -> a chosen account. Reuses app/treasury.py's own real
    withdraw() (Treasury -> any PaperPortfolio) rather than a second
    transfer mechanism — every real validation and permanent
    TreasuryTransaction record it already produces applies here
    unchanged."""
    account = next((a for a in accounts if a.id == account_id), None)
    if account is None:
        return accounts, treasury, f"No account with id {account_id!r}."
    new_treasury, new_portfolio, error = treasury_withdraw(treasury, account.portfolio, amount, sim_day=sim_day, now_iso=now_iso, transaction_id=transaction_id)
    if error is not None:
        return accounts, treasury, error
    updated_account = _with_updated_peak_equity(account.model_copy(update={"portfolio": new_portfolio}))
    return [updated_account if a.id == account_id else a for a in accounts], new_treasury, None


def deallocate_capital(
    accounts: list[Account], treasury: TreasuryState, account_id: str, amount: float, *, sim_day: int, now_iso: str, transaction_id: str
) -> tuple[list[Account], TreasuryState, str | None]:
    """A chosen account -> Treasury. Reuses app/treasury.py's own real
    deposit() (any PaperPortfolio -> Treasury), same reasoning as
    allocate_capital above."""
    account = next((a for a in accounts if a.id == account_id), None)
    if account is None:
        return accounts, treasury, f"No account with id {account_id!r}."
    new_treasury, new_portfolio, error = treasury_deposit(treasury, account.portfolio, amount, sim_day=sim_day, now_iso=now_iso, transaction_id=transaction_id)
    if error is not None:
        return accounts, treasury, error
    updated_account = _with_updated_peak_equity(account.model_copy(update={"portfolio": new_portfolio}))
    return [updated_account if a.id == account_id else a for a in accounts], new_treasury, None


def configure_prop_firm_rules(
    accounts: list[Account],
    account_id: str,
    *,
    trailing_drawdown_limit_pct: float | None,
    consistency_limit_pct: float | None,
    challenge_start_sim_day: int | None,
    challenge_duration_days: int | None,
    challenge_profit_target_pct: float | None,
) -> tuple[list[Account], str | None]:
    """Design Bible Chapter 69 Part 2 — a real CEO control (any account
    type may set these, not exclusively Prop Firm-typed accounts) for
    the addendum systems this pass builds real computation for:
    Trailing Drawdown, Consistency, and Challenge Windows. Every field
    is optional and independently settable — a CEO can configure a
    trailing drawdown limit without also starting a challenge window."""
    account = next((a for a in accounts if a.id == account_id), None)
    if account is None:
        return accounts, f"No account with id {account_id!r}."
    if trailing_drawdown_limit_pct is not None and trailing_drawdown_limit_pct <= 0:
        return accounts, "Trailing drawdown limit must be greater than 0%."
    if consistency_limit_pct is not None and not (0 < consistency_limit_pct <= 100):
        return accounts, "Consistency limit must be between 0 and 100%."
    if challenge_duration_days is not None and challenge_duration_days <= 0:
        return accounts, "Challenge duration must be at least 1 day."
    updated = account.model_copy(
        update={
            "trailing_drawdown_limit_pct": trailing_drawdown_limit_pct,
            "consistency_limit_pct": consistency_limit_pct,
            "challenge_start_sim_day": challenge_start_sim_day,
            "challenge_duration_days": challenge_duration_days,
            "challenge_profit_target_pct": challenge_profit_target_pct,
        }
    )
    return [updated if a.id == account_id else a for a in accounts], None


def configure_evaluation_tracking(
    accounts: list[Account],
    account_id: str,
    *,
    evaluation_cost: float | None,
    payout_eligibility_min_profit_pct: float | None,
) -> tuple[list[Account], str | None]:
    """Prop-Firm Risk Intelligence Addendum, Piece 10a — Requirement 24.
    A real CEO control for the two evaluation/payout numbers this
    codebase never tracked before this piece. Both fields are optional
    and independently settable, same convention as
    configure_prop_firm_rules above."""
    account = next((a for a in accounts if a.id == account_id), None)
    if account is None:
        return accounts, f"No account with id {account_id!r}."
    if evaluation_cost is not None and evaluation_cost < 0:
        return accounts, "Evaluation cost cannot be negative."
    if payout_eligibility_min_profit_pct is not None and payout_eligibility_min_profit_pct <= 0:
        return accounts, "Payout eligibility minimum profit must be greater than 0%."
    updated = account.model_copy(
        update={
            "evaluation_cost": evaluation_cost,
            "payout_eligibility_min_profit_pct": payout_eligibility_min_profit_pct,
        }
    )
    return [updated if a.id == account_id else a for a in accounts], None


def mark_account_funded(accounts: list[Account], account_id: str, *, sim_day: int) -> tuple[list[Account], str | None]:
    """A real, explicit CEO action recording that an evaluation account
    has reached the funded stage — never an automatic pass/fail
    inference off the challenge profit target (that honest judgment call
    is Piece 10's job, a real evaluation-policy simulator). Idempotent
    refusal, not a silent overwrite: once funded_at_sim_day is set, it's
    a permanent historical fact this account shouldn't be able to
    quietly re-date."""
    account = next((a for a in accounts if a.id == account_id), None)
    if account is None:
        return accounts, f"No account with id {account_id!r}."
    if account.funded_stage_reached:
        return accounts, f"{account.name} was already marked funded on sim day {account.funded_at_sim_day}."
    updated = account.model_copy(update={"funded_stage_reached": True, "funded_at_sim_day": sim_day})
    return [updated if a.id == account_id else a for a in accounts], None


def record_account_payout(accounts: list[Account], account_id: str, *, amount: float) -> tuple[list[Account], str | None]:
    """A real, CEO-recorded payout amount, added to this account's
    permanent running total. Requires the account to already be marked
    funded — a real payout only makes sense once an evaluation has
    actually been passed, matching how funded-stage accounts work at a
    real prop firm."""
    account = next((a for a in accounts if a.id == account_id), None)
    if account is None:
        return accounts, f"No account with id {account_id!r}."
    if not account.funded_stage_reached:
        return accounts, f"{account.name} has not been marked funded yet — mark it funded before recording a payout."
    if amount <= 0:
        return accounts, "Payout amount must be greater than 0."
    updated = account.model_copy(update={"total_payouts_received": account.total_payouts_received + amount})
    return [updated if a.id == account_id else a for a in accounts], None


MAX_CUSTOM_RULES_PER_ACCOUNT = 20


def add_custom_rule(
    accounts: list[Account], account_id: str, *, rule_type: RuleType, label: str, limit: float, weekday: Weekday | None, rule_id: str
) -> tuple[list[Account], str | None]:
    """Design Bible Chapter 69 Part 3 — Custom Rule Builder (structured,
    not free-text — see app/rule_engine.py's module docstring for the
    honest scope). Adds one real Rule to this account's own list,
    evaluated by the one centralized app/rule_engine.py."""
    account = next((a for a in accounts if a.id == account_id), None)
    if account is None:
        return accounts, f"No account with id {account_id!r}."
    if len(account.custom_rules) >= MAX_CUSTOM_RULES_PER_ACCOUNT:
        return accounts, f"{account.name} already has the maximum of {MAX_CUSTOM_RULES_PER_ACCOUNT} custom rules."
    if rule_type != "no_trading_on_weekday" and limit <= 0:
        return accounts, "Rule limit must be greater than 0."
    if rule_type == "no_trading_on_weekday" and weekday is None:
        return accounts, "A weekday is required for a No Trading On Weekday rule."
    rule = Rule(id=rule_id, ruleType=rule_type, label=label, limit=limit, weekday=weekday, enabled=True)
    updated = account.model_copy(update={"custom_rules": [*account.custom_rules, rule]})
    return [updated if a.id == account_id else a for a in accounts], None


def remove_custom_rule(accounts: list[Account], account_id: str, rule_id: str) -> tuple[list[Account], str | None]:
    account = next((a for a in accounts if a.id == account_id), None)
    if account is None:
        return accounts, f"No account with id {account_id!r}."
    if not any(r.id == rule_id for r in account.custom_rules):
        return accounts, f"No rule with id {rule_id!r} on {account.name}."
    updated = account.model_copy(update={"custom_rules": [r for r in account.custom_rules if r.id != rule_id]})
    return [updated if a.id == account_id else a for a in accounts], None


def toggle_custom_rule(accounts: list[Account], account_id: str, rule_id: str, enabled: bool) -> tuple[list[Account], str | None]:
    account = next((a for a in accounts if a.id == account_id), None)
    if account is None:
        return accounts, f"No account with id {account_id!r}."
    if not any(r.id == rule_id for r in account.custom_rules):
        return accounts, f"No rule with id {rule_id!r} on {account.name}."
    updated_rules = [r.model_copy(update={"enabled": enabled}) if r.id == rule_id else r for r in account.custom_rules]
    updated = account.model_copy(update={"custom_rules": updated_rules})
    return [updated if a.id == account_id else a for a in accounts], None
