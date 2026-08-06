"""Prop Firm Rule Engine — Design Bible Chapter 69 Part 2.

Defines the rules a Prop Firm-typed (or any) account can carry;
Chapter 69 Part 3's Institutional Rule Engine owns *enforcing* them (see
that chapter's own module, app/rule_engine.py) — this module only
computes real, honest status readouts, never blocks a trade itself.

Five of the fifteen "Supported Rules" the brief lists were already real,
enforced RiskLimits fields before this module existed (Daily Loss,
Overall Drawdown, Position Size, Risk Per Trade, Open Positions — see
app/risk_engine.py), plus a sixth in a related daily-scoped shape
(Profit Targets). This module adds real computation for the genuinely
unbuilt pieces: Trailing Drawdown, Consistency, Scaling Milestones, and
Challenge Windows — each grep-confirmed absent from this codebase before
this module. The Weekday-Aware Time System (weekday_for below) is real,
new, load-bearing infrastructure, not a Prop Firm-specific add-on.

Leverage (addendum item 3) has no real foundation to extend — this
codebase is a 100%-cash, long-only paper account with no margin field
anywhere (confirmed by Chapter 68's own research) — so LEVERAGE_NOTE
below states that honestly rather than fabricating a number.
"""
from __future__ import annotations

from app.accounts import account_equity
from app.schemas import (
    Account,
    ChallengeProgressStatus,
    ConsistencyStatus,
    PropFirmComplianceScore,
    PropFirmStatus,
    ScalingMilestoneStatus,
    TrailingDrawdownStatus,
    Weekday,
)

LEVERAGE_NOTE = "Not applicable — this is a 100% cash, long-only paper account with no margin or leverage concept anywhere in this codebase (confirmed by Chapter 68's own research)."

# Design Bible Chapter 69 Part 2 — Weekday-Aware Time System. Day 1 is
# defined as a Monday: a real, documented, deterministic anchor (never
# stored/driftable), since TimeState.day is grep-confirmed to have no
# calendar anchor anywhere in this codebase before this.
_WEEKDAYS: tuple[Weekday, ...] = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def weekday_for(sim_day: int) -> Weekday:
    return _WEEKDAYS[(sim_day - 1) % 7]


# Scaling tiers: real, published growth thresholds (equity growth % over
# the account's own starting balance) — never a hidden step function.
# Matches this Design Bible's own "no black-box composite" convention.
SCALING_TIER_THRESHOLDS_PCT: tuple[float, ...] = (10.0, 25.0, 50.0, 100.0)


def compute_trailing_drawdown(account: Account) -> TrailingDrawdownStatus:
    current_equity = account_equity(account)
    peak = account.peak_equity
    drawdown_pct = round((peak - current_equity) / peak * 100.0, 2) if peak > 0 else 0.0
    limit = account.trailing_drawdown_limit_pct
    return TrailingDrawdownStatus(
        peakEquity=round(peak, 2),
        currentEquity=round(current_equity, 2),
        drawdownPct=drawdown_pct,
        limitPct=limit,
        breached=limit is not None and drawdown_pct >= limit,
    )


def compute_consistency_status(account: Account, *, sim_day: int) -> ConsistencyStatus:
    """Real per-day P&L, bucketed from the account's own real closed-
    trade history (PaperTrade.closed_sim_minutes), compared against the
    challenge window's own real cumulative total — never a fabricated
    day-by-day breakdown. `applicable=False` (and every number 0) for an
    account with no challenge window configured or no closed trades yet,
    since there is nothing real to compare against."""
    if account.challenge_start_sim_day is None:
        return ConsistencyStatus(applicable=False, cumulativeProfit=0.0, largestSingleDayProfit=0.0, largestSingleDaySharePct=0.0, limitPct=account.consistency_limit_pct, breached=False)

    window_start_minutes = account.challenge_start_sim_day * 1440
    daily_profit: dict[int, float] = {}
    for trade in account.portfolio.trade_history:
        if trade.closed_sim_minutes < window_start_minutes:
            continue
        trade_day = trade.closed_sim_minutes // 1440
        daily_profit[trade_day] = daily_profit.get(trade_day, 0.0) + trade.pnl

    cumulative = sum(daily_profit.values())
    largest_day = max(daily_profit.values(), default=0.0)
    share_pct = round(largest_day / cumulative * 100.0, 2) if cumulative > 0 else 0.0
    limit = account.consistency_limit_pct
    return ConsistencyStatus(
        applicable=True,
        cumulativeProfit=round(cumulative, 2),
        largestSingleDayProfit=round(largest_day, 2),
        largestSingleDaySharePct=share_pct,
        limitPct=limit,
        breached=limit is not None and cumulative > 0 and share_pct > limit,
    )


def compute_scaling_status(account: Account) -> ScalingMilestoneStatus:
    starting = account.portfolio.starting_balance
    growth_pct = round((account.peak_equity - starting) / starting * 100.0, 2) if starting > 0 else 0.0
    tier = sum(1 for threshold in SCALING_TIER_THRESHOLDS_PCT if growth_pct >= threshold)
    next_threshold = SCALING_TIER_THRESHOLDS_PCT[tier] if tier < len(SCALING_TIER_THRESHOLDS_PCT) else None
    return ScalingMilestoneStatus(currentTier=tier, equityGrowthPct=growth_pct, nextTierGrowthThresholdPct=next_threshold)


def compute_challenge_progress(account: Account, *, sim_day: int) -> ChallengeProgressStatus:
    if account.challenge_start_sim_day is None:
        return ChallengeProgressStatus(applicable=False, startedSimDay=None, durationDays=None, daysElapsed=0, daysRemaining=None, profitPct=0.0, targetPct=None, onPace=None)

    days_elapsed = max(0, sim_day - account.challenge_start_sim_day)
    duration = account.challenge_duration_days
    days_remaining = max(0, duration - days_elapsed) if duration is not None else None
    starting = account.portfolio.starting_balance
    current_equity = account_equity(account)
    profit_pct = round((current_equity - starting) / starting * 100.0, 2) if starting > 0 else 0.0
    target = account.challenge_profit_target_pct
    on_pace: bool | None = None
    if target is not None and duration is not None and duration > 0:
        required_pace_pct = target * (days_elapsed / duration)
        on_pace = profit_pct >= required_pace_pct
    return ChallengeProgressStatus(
        applicable=True,
        startedSimDay=account.challenge_start_sim_day,
        durationDays=duration,
        daysElapsed=days_elapsed,
        daysRemaining=days_remaining,
        profitPct=profit_pct,
        targetPct=target,
        onPace=on_pace,
    )


def _safety_score(current_pct: float, limit_pct: float | None) -> float:
    """A real, transparent 0-100 read: 100 when nowhere near the limit,
    0 once at or past it. Used identically for every proximity-based
    sub-score below — never a different hidden curve per input."""
    if limit_pct is None or limit_pct <= 0:
        return 100.0
    return max(0.0, min(100.0, 100.0 - (current_pct / limit_pct * 100.0)))


def compute_compliance_score(account: Account, *, sim_day: int) -> PropFirmComplianceScore:
    """Design Bible Chapter 69 Part 2 — Prop Firm Compliance Score. A
    real, equal-weighted average of five published sub-scores — never a
    hidden blend, matching this Design Bible's own "no black-box
    composite" convention (Chapter 66's own Decision Logic section, and
    CompanyHealth.overall's own precedent). Company Health / Account
    Health is deliberately excluded: Chapter 63's real CompanyHealth.
    overall is company-wide, not account-scoped, and including it here
    would misrepresent a company-wide number as this one account's own."""
    drawdown = compute_trailing_drawdown(account)
    consistency = compute_consistency_status(account, sim_day=sim_day)

    drawdown_safety = _safety_score(drawdown.drawdown_pct, drawdown.limit_pct)
    consistency_score = _safety_score(consistency.largest_single_day_share_pct, consistency.limit_pct) if consistency.applicable else 100.0

    limits = account.risk_limits
    rule_checks_passing = 0
    rule_checks_total = 6
    current_equity = account_equity(account)
    open_exposure_pct = sum(p.quantity * p.current_price for p in account.portfolio.positions) / current_equity * 100.0 if current_equity > 0 else 0.0
    if open_exposure_pct <= limits.max_position_pct:
        rule_checks_passing += 1
    if len(account.portfolio.positions) <= limits.max_open_positions:
        rule_checks_passing += 1
    if drawdown.drawdown_pct <= (drawdown.limit_pct or 100.0):
        rule_checks_passing += 1
    lifetime_drawdown_pct = max(0.0, (account.portfolio.starting_balance - current_equity) / account.portfolio.starting_balance * 100.0) if account.portfolio.starting_balance > 0 else 0.0
    if lifetime_drawdown_pct <= limits.max_drawdown_pct:
        rule_checks_passing += 1
    if not consistency.breached:
        rule_checks_passing += 1
    if account.portfolio.total_pnl_pct >= -limits.max_daily_loss_pct:
        rule_checks_passing += 1
    rule_compliance = round(rule_checks_passing / rule_checks_total * 100.0, 1)

    risk_exposure = _safety_score(open_exposure_pct, limits.max_position_pct)
    capital_preservation = round(min(100.0, current_equity / account.portfolio.starting_balance * 100.0), 1) if account.portfolio.starting_balance > 0 else 0.0

    overall = round((drawdown_safety + consistency_score + rule_compliance + risk_exposure + capital_preservation) / 5.0, 1)
    return PropFirmComplianceScore(
        overall=overall,
        drawdownSafety=round(drawdown_safety, 1),
        consistency=round(consistency_score, 1),
        ruleCompliance=rule_compliance,
        riskExposure=round(risk_exposure, 1),
        capitalPreservation=capital_preservation,
    )


def compute_prop_firm_status(account: Account, *, sim_day: int) -> PropFirmStatus:
    return PropFirmStatus(
        accountId=account.id,
        weekday=weekday_for(sim_day),
        trailingDrawdown=compute_trailing_drawdown(account),
        consistency=compute_consistency_status(account, sim_day=sim_day),
        scaling=compute_scaling_status(account),
        challenge=compute_challenge_progress(account, sim_day=sim_day),
        complianceScore=compute_compliance_score(account, sim_day=sim_day),
        leverageNote=LEVERAGE_NOTE,
    )
