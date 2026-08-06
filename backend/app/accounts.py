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
from app.schemas import Account, AccountType, PaperPortfolio, RiskLimits, TreasuryState
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
    updated_account = account.model_copy(update={"portfolio": new_portfolio})
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
    updated_account = account.model_copy(update={"portfolio": new_portfolio})
    return [updated_account if a.id == account_id else a for a in accounts], new_treasury, None
