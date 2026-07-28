"""TreasuryManager — v0.7 Feature 33, the CEO Treasury.

A second account, structurally isolated from `PaperPortfolio.cash_balance`
("Operating Capital"). Every function below that moves money takes the
CEO-initiated amount as an explicit parameter passed in by a router
handler reacting to a real player action (`POST /api/treasury/deposit`,
`/withdraw`, ...) — no automatic system anywhere else in this codebase
(paper_trading.py, broker.py, risk_engine.py, research.py, academy.py,
...) ever reads or writes `treasury.balance`. That is checked, not just
documented by convention: grep this codebase for `treasury` outside this
module, `app/state.py` (the three explicit CEO-action methods), and
`app/nexus.py` (the one Smart Savings Rule evaluation call, itself gated
on the CEO's own prior rule configuration) and there is nothing to find.

Smart Savings Rules are the one deliberate exception to "nothing touches
Treasury automatically" — but only because the CEO explicitly configured
them and can pause them at any time (the brief's own "Pause all
automatic transfers"), never a system acting on Treasury funds without
prior authorization. Two real rule types are offered, not three: the
brief's own "save 5% of monthly profit" and "save 10% after profitable
months" are the same real mechanic (saving a percentage of monthly
profit only makes sense — and only ever fires — when that profit is
positive), so `percent_of_monthly_profit` structurally never saves
against a loss rather than needing a second, mechanically-identical rule
type to express "only when profitable." `excess_above_reserve` is
genuinely distinct: it moves operating cash above a chosen dollar
reserve, independent of any period's profit.

CEO Benefits (the brief's list of future Treasury-funded spend
categories — Company Expansion, Emergency Funding, Building New
Departments, Buying Headquarters Upgrades, Special Story Events) are not
built here: none of those systems exist anywhere in this codebase to
spend real Treasury dollars into. The real, honest piece that is built
is the withdrawal itself — CEO-approved funds moving back into Operating
Capital, which the player can then use through whatever real
cash-consuming system already exists (currently: opening paper
positions). See docs/Architecture.md for the full scope note.
"""
from __future__ import annotations

from app.schemas import (
    PaperPortfolio,
    SavingsRuleType,
    SmartSavingsRule,
    TreasuryMonthlyReport,
    TreasuryState,
    TreasuryTransaction,
    TreasuryTransactionKind,
)

MAX_TREASURY_TRANSACTIONS = 150
MAX_TREASURY_MONTHLY_REPORTS = 24


def default_treasury(now_iso: str) -> TreasuryState:
    return TreasuryState(balance=0.0, lifetimeDeposits=0.0, largestBalance=0.0, transactions=[], savingsRules=[], monthlyReports=[], updatedAt=now_iso)


def reserve_percentage(treasury: TreasuryState, portfolio: PaperPortfolio) -> float:
    """Treasury balance as a share of the company's total real capital
    (Treasury + Operating Capital) — computed fresh, never stored, so it
    can never silently drift out of sync with the two real balances it
    reads."""
    total = treasury.balance + portfolio.cash_balance
    return (treasury.balance / total * 100) if total > 0 else 0.0


def _record_transaction(treasury: TreasuryState, *, kind: TreasuryTransactionKind, amount: float, note: str, sim_day: int, now_iso: str, transaction_id: str) -> TreasuryState:
    new_balance = treasury.balance + amount if kind in ("deposit", "auto_save") else treasury.balance - amount
    transaction = TreasuryTransaction(
        id=transaction_id,
        kind=kind,
        amount=amount,
        balanceAfter=round(new_balance, 2),
        note=note,
        simDay=sim_day,
        createdAt=now_iso,
    )
    transactions = [*treasury.transactions, transaction]
    if len(transactions) > MAX_TREASURY_TRANSACTIONS:
        del transactions[: len(transactions) - MAX_TREASURY_TRANSACTIONS]
    lifetime_deposits = treasury.lifetime_deposits + amount if kind in ("deposit", "auto_save") else treasury.lifetime_deposits
    return treasury.model_copy(
        update={
            "balance": round(new_balance, 2),
            "lifetime_deposits": round(lifetime_deposits, 2),
            "largest_balance": round(max(treasury.largest_balance, new_balance), 2),
            "transactions": transactions,
            "updated_at": now_iso,
        }
    )


def deposit(treasury: TreasuryState, portfolio: PaperPortfolio, amount: float, *, sim_day: int, now_iso: str, transaction_id: str) -> tuple[TreasuryState, PaperPortfolio, str | None]:
    """Operating Capital -> Treasury. A real, validated transfer — never
    more than Operating Capital actually holds."""
    if amount <= 0:
        return treasury, portfolio, "Deposit amount must be positive."
    if amount > portfolio.cash_balance:
        return treasury, portfolio, f"Operating Capital only holds ${portfolio.cash_balance:,.2f} — can't deposit ${amount:,.2f}."
    new_portfolio = portfolio.model_copy(update={"cash_balance": round(portfolio.cash_balance - amount, 2)})
    new_treasury = _record_transaction(treasury, kind="deposit", amount=amount, note="CEO deposit from Operating Capital.", sim_day=sim_day, now_iso=now_iso, transaction_id=transaction_id)
    return new_treasury, new_portfolio, None


def withdraw(treasury: TreasuryState, portfolio: PaperPortfolio, amount: float, *, sim_day: int, now_iso: str, transaction_id: str) -> tuple[TreasuryState, PaperPortfolio, str | None]:
    """Treasury -> Operating Capital. A real, validated transfer — never
    more than the Treasury actually holds. Always a deliberate CEO
    action, never automatic (see module docstring)."""
    if amount <= 0:
        return treasury, portfolio, "Withdrawal amount must be positive."
    if amount > treasury.balance:
        return treasury, portfolio, f"The Treasury only holds ${treasury.balance:,.2f} — can't withdraw ${amount:,.2f}."
    new_portfolio = portfolio.model_copy(update={"cash_balance": round(portfolio.cash_balance + amount, 2)})
    new_treasury = _record_transaction(treasury, kind="withdrawal", amount=amount, note="CEO withdrawal to Operating Capital.", sim_day=sim_day, now_iso=now_iso, transaction_id=transaction_id)
    return new_treasury, new_portfolio, None


def create_rule(treasury: TreasuryState, rule_type: SavingsRuleType, *, percent: float, reserve_target: float | None, now_iso: str, rule_id: str) -> tuple[TreasuryState, str | None]:
    if rule_type == "percent_of_monthly_profit" and not (0 < percent <= 100):
        return treasury, "Percent must be between 0 and 100."
    if rule_type == "excess_above_reserve" and (reserve_target is None or reserve_target < 0):
        return treasury, "Excess-above-reserve rules need a reserve target of 0 or more."
    rule = SmartSavingsRule(id=rule_id, ruleType=rule_type, percent=percent if rule_type == "percent_of_monthly_profit" else 0.0, reserveTarget=reserve_target if rule_type == "excess_above_reserve" else None, active=True, createdAt=now_iso)
    return treasury.model_copy(update={"savings_rules": [*treasury.savings_rules, rule], "updated_at": now_iso}), None


def toggle_rule(treasury: TreasuryState, rule_id: str, active: bool, *, now_iso: str) -> tuple[TreasuryState, str | None]:
    if not any(r.id == rule_id for r in treasury.savings_rules):
        return treasury, f"No savings rule found with id {rule_id!r}."
    rules = [r.model_copy(update={"active": active}) if r.id == rule_id else r for r in treasury.savings_rules]
    return treasury.model_copy(update={"savings_rules": rules, "updated_at": now_iso}), None


def pause_all_rules(treasury: TreasuryState, *, now_iso: str) -> TreasuryState:
    rules = [r.model_copy(update={"active": False}) for r in treasury.savings_rules]
    return treasury.model_copy(update={"savings_rules": rules, "updated_at": now_iso})


def apply_monthly_savings_rules(treasury: TreasuryState, portfolio: PaperPortfolio, *, monthly_profit_dollars: float, sim_day: int, now_iso: str, id_prefix: str) -> tuple[TreasuryState, PaperPortfolio]:
    """Called once, at the same monthly evening cadence nexus.py already
    uses for Coach/Executive Review/Reflection reports. Applies at most
    the latest active rule of each type — multiple simultaneous
    percent-of-profit rules would just be additive and confusing, so
    only the most recently created active one of each type fires."""
    latest_percent = next((r for r in reversed(treasury.savings_rules) if r.rule_type == "percent_of_monthly_profit" and r.active), None)
    latest_reserve = next((r for r in reversed(treasury.savings_rules) if r.rule_type == "excess_above_reserve" and r.active), None)

    if latest_percent is not None and monthly_profit_dollars > 0:
        amount = round(monthly_profit_dollars * latest_percent.percent / 100, 2)
        if amount > 0 and amount <= portfolio.cash_balance:
            portfolio = portfolio.model_copy(update={"cash_balance": round(portfolio.cash_balance - amount, 2)})
            treasury = _record_transaction(
                treasury, kind="auto_save", amount=amount, note=f"Smart Savings Rule: {latest_percent.percent:.0f}% of this month's ${monthly_profit_dollars:,.2f} profit.",
                sim_day=sim_day, now_iso=now_iso, transaction_id=f"{id_prefix}-percent",
            )

    if latest_reserve is not None and latest_reserve.reserve_target is not None and portfolio.cash_balance > latest_reserve.reserve_target:
        amount = round(portfolio.cash_balance - latest_reserve.reserve_target, 2)
        if amount > 0:
            portfolio = portfolio.model_copy(update={"cash_balance": round(portfolio.cash_balance - amount, 2)})
            treasury = _record_transaction(
                treasury, kind="auto_save", amount=amount, note=f"Smart Savings Rule: operating cash above the ${latest_reserve.reserve_target:,.2f} reserve moved to Treasury.",
                sim_day=sim_day, now_iso=now_iso, transaction_id=f"{id_prefix}-reserve",
            )

    return treasury, portfolio


def record_monthly_report(treasury: TreasuryState, *, month_ending_day: int, now_iso: str, report_id: str) -> TreasuryState:
    """A real summary of this month's Treasury activity, filtered from
    the same real transaction log the archive already holds — never a
    second, independently-tracked set of monthly totals."""
    window_start_day = month_ending_day - 30
    month_txns = [t for t in treasury.transactions if window_start_day < t.sim_day <= month_ending_day]
    deposits = sum(t.amount for t in month_txns if t.kind == "deposit")
    withdrawals = sum(t.amount for t in month_txns if t.kind == "withdrawal")
    auto_saved = sum(t.amount for t in month_txns if t.kind == "auto_save")
    report = TreasuryMonthlyReport(
        id=report_id,
        monthEndingDay=month_ending_day,
        deposits=round(deposits, 2),
        withdrawals=round(withdrawals, 2),
        autoSaved=round(auto_saved, 2),
        endingBalance=treasury.balance,
        createdAt=now_iso,
    )
    reports = [*treasury.monthly_reports, report]
    if len(reports) > MAX_TREASURY_MONTHLY_REPORTS:
        del reports[: len(reports) - MAX_TREASURY_MONTHLY_REPORTS]
    return treasury.model_copy(update={"monthly_reports": reports, "updated_at": now_iso})
