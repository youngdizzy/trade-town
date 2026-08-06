"""Institutional Rule Engine (IRE) — Design Bible Chapter 69 Part 3.

The one centralized evaluator every account's own Custom Rules run
through — never a second, account-specific enforcement path (that's
exactly the duplication this part's own Company Philosophy exists to
prevent). Grep-confirmed before this module existed: no Rule/
RuleProfile/RuleEngine class existed anywhere in this codebase; every
real risk check (app/risk_engine.py's evaluate_sentinel_risk(), the
Trade Gatekeeper's eight checks) was its own hardcoded Python function.

This module does NOT replace or duplicate those — Chapters 57/58/66's
real pre-trade veto pipeline for the primary account stays exactly as-is
(this Design Bible's own repeated warning against a second, competing
enforcement path). What this module adds is genuinely new: a real,
data-driven way for an account (any account from Part 1, not just Prop
Firm) to carry its own structured rules, checked by one shared,
transparent evaluator — each rule type is a simple, individually
auditable comparison, never a hidden blend, preserving the same "every
decision must be explainable" property the hardcoded checks already had.

Honest scope for the brief's own "Custom Rule Builder": this is a closed
set of named, structured rule types (RuleType in schemas.py), not a
free-text DSL or natural-language parser — no such parser exists
anywhere in this codebase, and building one is real, separate,
unstarted work. A CEO configures a rule by picking a type and a limit
(no code change required to add a *rule*), not by typing arbitrary text
(that would require a rule-authoring language this codebase doesn't
have). See the Design Bible chapter's own Custom Rule Builder section
for the exact honesty boundary against each of the brief's six examples.

Rule Execution Order: this evaluator checks an account's own current
state (its RiskLimits fields, Part 2's real trailing-drawdown/
consistency computations, and the current weekday) — it does not yet sit
inside a live pre-trade pipeline for non-primary accounts, since Part 1
confirmed live trading execution against a non-primary account isn't
wired yet. This module is the real evaluation logic the Design Bible's
own Rule Execution Order calls for; wiring it into an actual pre-trade
block for non-primary accounts is Future Expansion, named honestly
rather than silently assumed done.
"""
from __future__ import annotations

from app.accounts import account_equity
from app.prop_firm import compute_consistency_status, compute_trailing_drawdown, weekday_for
from app.schemas import Account, Rule, RuleCheckResult, RuleEvaluationResult, RuleType

# Design Bible Chapter 69 Part 3 — "suggest corrective actions" (one of
# the brief's four required behaviors on a rule failure, previously the
# only one of the four genuinely unbuilt — see Part 3's own Ownership
# table). A real, static, per-rule-type template, never a fabricated
# AI-generated suggestion.
CORRECTIVE_ACTIONS: dict[RuleType, str] = {
    "max_daily_loss_pct": "Stop trading for the rest of today, or raise this account's daily loss limit if the CEO intends to accept more risk.",
    "max_drawdown_pct": "Reduce position sizes or deallocate less capital until equity recovers above the drawdown floor.",
    "max_position_pct": "Reduce this position's size so it falls within the configured maximum share of account equity.",
    "max_open_positions": "Close an existing position before opening another.",
    "max_risk_per_trade_pct": "Size the next trade down so its real risk stays within the configured per-trade limit.",
    "trailing_drawdown_pct": "Reduce trading activity — equity has fallen too far from its own peak; consider deallocating less capital until it recovers.",
    "consistency_pct": "Spread gains across more trading days — one day is carrying too large a share of the challenge's cumulative profit.",
    "no_trading_on_weekday": "Wait until the next permitted trading day.",
}

RULE_TYPE_LABELS: dict[RuleType, str] = {
    "max_daily_loss_pct": "Max Daily Loss",
    "max_drawdown_pct": "Max Drawdown",
    "max_position_pct": "Max Position Size",
    "max_open_positions": "Max Open Positions",
    "max_risk_per_trade_pct": "Max Risk Per Trade",
    "trailing_drawdown_pct": "Trailing Drawdown",
    "consistency_pct": "Consistency Limit",
    "no_trading_on_weekday": "No Trading On Weekday",
}


def _check_rule(rule: Rule, account: Account, *, sim_day: int) -> RuleCheckResult:
    """One real, individually-inspectable comparison per rule type —
    never a combined or weighted evaluation. Each branch reads only the
    real, already-computed numbers named in its own comment; none of
    them are recomputed here a second time."""
    passed: bool
    detail: str

    if rule.rule_type == "max_daily_loss_pct":
        loss_pct = -account.portfolio.total_pnl_pct if account.portfolio.total_pnl_pct < 0 else 0.0
        passed = loss_pct <= rule.limit
        detail = f"Today's real loss is {loss_pct:.1f}% of equity, limit is {rule.limit:.1f}%."
    elif rule.rule_type == "max_drawdown_pct":
        starting = account.portfolio.starting_balance
        current = account_equity(account)
        lifetime_drawdown_pct = max(0.0, (starting - current) / starting * 100.0) if starting > 0 else 0.0
        passed = lifetime_drawdown_pct <= rule.limit
        detail = f"Lifetime drawdown from starting balance is {lifetime_drawdown_pct:.1f}%, limit is {rule.limit:.1f}%."
    elif rule.rule_type == "max_position_pct":
        current = account_equity(account)
        largest_position_pct = max((p.quantity * p.current_price / current * 100.0 for p in account.portfolio.positions), default=0.0) if current > 0 else 0.0
        passed = largest_position_pct <= rule.limit
        detail = f"Largest open position is {largest_position_pct:.1f}% of equity, limit is {rule.limit:.1f}%."
    elif rule.rule_type == "max_open_positions":
        open_count = len(account.portfolio.positions)
        passed = open_count <= rule.limit
        detail = f"{open_count} open position(s), limit is {rule.limit:.0f}."
    elif rule.rule_type == "max_risk_per_trade_pct":
        passed = account.risk_limits.risk_per_trade_pct <= rule.limit
        detail = f"Configured risk-per-trade is {account.risk_limits.risk_per_trade_pct:.1f}%, limit is {rule.limit:.1f}%."
    elif rule.rule_type == "trailing_drawdown_pct":
        drawdown = compute_trailing_drawdown(account)
        passed = drawdown.drawdown_pct <= rule.limit
        detail = f"Trailing drawdown from peak equity is {drawdown.drawdown_pct:.1f}%, limit is {rule.limit:.1f}%."
    elif rule.rule_type == "consistency_pct":
        consistency = compute_consistency_status(account, sim_day=sim_day)
        passed = not consistency.applicable or consistency.largest_single_day_share_pct <= rule.limit
        detail = (
            f"Largest single day is {consistency.largest_single_day_share_pct:.1f}% of cumulative profit, limit is {rule.limit:.1f}%."
            if consistency.applicable
            else "No challenge window configured — not yet applicable."
        )
    else:  # no_trading_on_weekday
        today = weekday_for(sim_day)
        passed = rule.weekday is None or today != rule.weekday
        detail = f"Today is {today}." + (f" Trading is blocked on {rule.weekday}." if rule.weekday else " No weekday configured.")

    return RuleCheckResult(
        ruleId=rule.id,
        label=rule.label or RULE_TYPE_LABELS[rule.rule_type],
        passed=passed,
        detail=detail,
        correctiveAction=None if passed else CORRECTIVE_ACTIONS[rule.rule_type],
    )


def evaluate_rules(account: Account, *, sim_day: int) -> RuleEvaluationResult:
    """The Institutional Rule Engine's one real entry point — every
    enabled rule on this account, checked individually and
    transparently. Disabled rules are skipped entirely (not evaluated
    as an automatic pass) so a CEO can see at a glance which rules are
    actually live."""
    checks = [_check_rule(rule, account, sim_day=sim_day) for rule in account.custom_rules if rule.enabled]
    return RuleEvaluationResult(
        accountId=account.id,
        simDay=sim_day,
        checks=checks,
        allPassed=all(c.passed for c in checks),
    )
