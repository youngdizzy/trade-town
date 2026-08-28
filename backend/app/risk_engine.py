"""RiskEngine — the "RiskEngine" role from the v0.6 brief, backing
Sentinel's (Risk Management) and Guardian's (Portfolio Protection) votes
on a trade candidate. Pure evaluation: given RiskLimits and the current
portfolio, decides whether a proposed trade — or the portfolio as a
whole — crosses a configured limit, and returns a RiskWarning describing
why. Never places, sizes, modifies, or cancels an order itself; that's
app/broker.py's job, and app/voting.py is the only caller that turns a
warning into a vote.

Sentinel's checks (`evaluate_sentinel_risk`) are the hard "can this trade
happen at all" gate: position size, open-position count, and portfolio
drawdown. Guardian's check (`evaluate_guardian_exposure`) is the softer
"should we be worried" concentration/exposure monitor — the same shape,
but framed as "this symbol/sector is already a large share of the
book" rather than "this one trade is too big." Both return `None` when
nothing is wrong, matching the "neutral unless there's something to flag"
convention already used by app/company_score.py's default-50 scores.

v0.7 Feature 49 — Professional Day Trading Program's "Daily Trading
Objectives." `max_daily_loss_pct` already existed on `RiskLimits` but was
never enforced anywhere (confirmed by grep before this feature — the
only readers were nexus.py's automation-mode scaling and RiskPanel.tsx's
display); this feature makes it real, and adds a real daily profit
target and a real max-trades-per-day limit alongside it. All three read
`PaperTrade.opened_sim_minutes`/`closed_sim_minutes` (already real,
already persisted, `// 1440` = the sim day a trade opened/closed on) —
zero new data. Deliberately routed through the exact same mechanism the
existing lifetime-drawdown check already uses (`evaluate_sentinel_risk`
returning a critical, symbol-scoped `RiskWarning`, which becomes the
proposal's own `risk_summary` and drives Sentinel's analyst vote to
"wait" — see app/executive.py's `_risk_vote` — which then fails
app/gatekeeper.py's `_risk_manager_check` if the CEO tries to force a
trade anyway) rather than inventing a second, parallel "stop trading"
mechanism. Once a daily objective is reached, every new proposal for
every symbol carries this same warning until the next sim day, so no
new position can open — trading for that symbol is not paused by a
separate flag, it fails the real Gatekeeper the same way any other
critical risk warning already does.

This is also why no separate "penalize forcing a trade after the daily
halt" Discipline factor was added (app/discipline.py): once the
Gatekeeper blocks it, no PaperTrade — and therefore no DisciplineReview
— is ever created for it, the exact same "structurally constant,
nothing real to score" case discipline.py's own module docstring already
documents for "did it pass the Gatekeeper."
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone

from app.analytics import max_drawdown_pct
from app.schemas import DailyObjectiveStatus, PaperPortfolio, PaperTrade, ProjectedLossPath, RiskBudgetStatus, RiskLimits, RiskWarning

# Position sizing floor/ceiling, mirroring app/portfolio.py's
# MIN_POSITION_SIZE — a proposed trade smaller than this isn't worth
# routing through the full risk/voting pipeline.
MIN_TRADE_VALUE = 100.0

SIM_MINUTES_PER_DAY = 1440

# Design Bible Chapter 67 (TTOS) Safety Settings — mirrors app/nexus.py's
# own WEEKLY_INTERVAL_DAYS/MONTHLY_INTERVAL_DAYS (not imported, to avoid
# a risk_engine.py -> nexus.py dependency; nexus.py already imports this
# module, never the reverse).
WEEKLY_INTERVAL_DAYS = 7
MONTHLY_INTERVAL_DAYS = 30


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_risk_limits() -> RiskLimits:
    return RiskLimits()


def trades_opened_today(trade_history: list[PaperTrade], sim_day: int) -> list[PaperTrade]:
    return [t for t in trade_history if t.opened_sim_minutes // SIM_MINUTES_PER_DAY == sim_day]


def trades_closed_today(trade_history: list[PaperTrade], sim_day: int) -> list[PaperTrade]:
    return [t for t in trade_history if t.closed_sim_minutes // SIM_MINUTES_PER_DAY == sim_day]


def distinct_trading_days(trade_history: list[PaperTrade]) -> int:
    """Prop-Firm Risk Intelligence Addendum, Piece 11b — Requirement 24's
    "number of trading days" data point. Counts distinct real sim days
    with at least one real closed trade, reusing the exact
    `closed_sim_minutes // SIM_MINUTES_PER_DAY` bucketing convention
    app/prop_firm.py's compute_consistency_status() already established
    — no new time-conversion logic."""
    return len({t.closed_sim_minutes // SIM_MINUTES_PER_DAY for t in trade_history})


def daily_realized_pnl_pct(portfolio: PaperPortfolio, sim_day: int) -> float:
    """Today's real realized P&L, as a % of the portfolio's real starting
    balance — the same fixed-reference convention app/portfolio.py's own
    `total_pnl_pct` already uses, just scoped to trades closed on this
    one sim day instead of the account's whole lifetime."""
    if portfolio.starting_balance <= 0:
        return 0.0
    realized = sum(t.pnl for t in trades_closed_today(portfolio.trade_history, sim_day))
    return realized / portfolio.starting_balance * 100


def weekly_realized_pnl_pct(portfolio: PaperPortfolio, sim_day: int) -> float:
    """This sim week's real realized P&L (the same 7-day week
    app/nexus.py's own weekly cadence uses), as a % of starting balance
    — the same shape as daily_realized_pnl_pct above, just a wider
    window."""
    if portfolio.starting_balance <= 0:
        return 0.0
    week = sim_day // WEEKLY_INTERVAL_DAYS
    realized = sum(t.pnl for t in portfolio.trade_history if (t.closed_sim_minutes // SIM_MINUTES_PER_DAY) // WEEKLY_INTERVAL_DAYS == week)
    return realized / portfolio.starting_balance * 100


def monthly_realized_pnl_pct(portfolio: PaperPortfolio, sim_day: int) -> float:
    """This sim month's real realized P&L (the same 30-day month
    app/nexus.py's own monthly cadence uses), as a % of starting
    balance."""
    if portfolio.starting_balance <= 0:
        return 0.0
    month = sim_day // MONTHLY_INTERVAL_DAYS
    realized = sum(t.pnl for t in portfolio.trade_history if (t.closed_sim_minutes // SIM_MINUTES_PER_DAY) // MONTHLY_INTERVAL_DAYS == month)
    return realized / portfolio.starting_balance * 100


def portfolio_equity(portfolio: PaperPortfolio) -> float:
    """Cash plus every open position's current market value — the
    denominator every percentage-based risk check is measured against."""
    positions_value = sum(p.quantity * p.current_price for p in portfolio.positions)
    return portfolio.cash_balance + positions_value


def recommended_quantity(limits: RiskLimits, portfolio: PaperPortfolio, price: float) -> float:
    """Sizes a new position at `risk_per_trade_pct` of equity, capped so
    it never exceeds `max_position_pct` either — the smaller of the two
    always wins, so tightening either limit alone is enough to shrink
    position sizes without touching the other."""
    if price <= 0:
        return 0.0
    equity = portfolio_equity(portfolio)
    risk_budget = equity * limits.risk_per_trade_pct / 100
    position_cap = equity * limits.max_position_pct / 100
    budget = min(risk_budget, position_cap)
    if budget < MIN_TRADE_VALUE:
        return 0.0
    return round(budget / price, 4)


def _sentinel_checks(
    limits: RiskLimits,
    portfolio: PaperPortfolio,
    *,
    symbol: str,
    proposed_value: float,
    sim_day: int,
) -> Iterator[RiskWarning]:
    """Every one of Sentinel's real trade-approval checks, in the same
    severity order `evaluate_sentinel_risk()` has always used — yields
    EVERY violation found, not just the first. `evaluate_sentinel_risk()`
    below takes only the first (its own long-standing "one clear reason"
    contract, unchanged); CEO directive "Portfolio Risk Engine +
    Firm-Wide Risk Governance" adds `evaluate_all_sentinel_checks()`,
    which takes all of them, for a real, fully-explained pre-trade risk
    decision — the exact same checks, never a second/parallel risk
    engine. v0.7 Feature 49 — Daily Trading Objectives are checked right
    after account-level equity and before the lifetime drawdown check:
    a day-scoped halt is the more common real event in normal play, and
    checking it early keeps the message the CEO actually sees relevant
    to *today*, not the account's whole history."""
    equity = portfolio_equity(portfolio)
    if equity <= 0:
        # Genuinely irrecoverable for this evaluation — every check below
        # divides by `equity`, so this one stops the generator instead of
        # yielding alongside checks that can't be meaningfully evaluated.
        yield RiskWarning(
            id=f"risk-{symbol}-{_now_iso()}",
            symbol=symbol,
            severity="critical",
            message="Portfolio equity is at or below zero — no new positions until it recovers.",
            createdAt=_now_iso(),
            code="risk_equity_exhausted",
        )
        return

    daily_pnl_pct = daily_realized_pnl_pct(portfolio, sim_day)
    if daily_pnl_pct <= -limits.max_daily_loss_pct:
        yield RiskWarning(
            id=f"risk-{symbol}-{_now_iso()}",
            symbol=symbol,
            severity="critical",
            message=f"Today's realized loss ({daily_pnl_pct:.1f}%) has hit the {limits.max_daily_loss_pct:.0f}% daily maximum loss — no new trades until tomorrow.",
            createdAt=_now_iso(),
            code="risk_daily_loss_limit",
        )

    if daily_pnl_pct >= limits.daily_profit_target_pct:
        yield RiskWarning(
            id=f"risk-{symbol}-{_now_iso()}",
            symbol=symbol,
            severity="critical",
            message=f"Today's realized profit ({daily_pnl_pct:.1f}%) has reached the {limits.daily_profit_target_pct:.0f}% daily target — protecting today's gain, no new trades until tomorrow.",
            createdAt=_now_iso(),
            code="risk_daily_profit_target",
        )

    # Design Bible Chapter 67 (TTOS) Safety Settings — the second and
    # third real circuit breakers, checked right after the daily ones
    # for the same reason: a week/month-scoped halt is a more common
    # real event than the lifetime drawdown check below it.
    weekly_pnl_pct = weekly_realized_pnl_pct(portfolio, sim_day)
    if weekly_pnl_pct <= -limits.max_weekly_loss_pct:
        yield RiskWarning(
            id=f"risk-{symbol}-{_now_iso()}",
            symbol=symbol,
            severity="critical",
            message=f"This week's realized loss ({weekly_pnl_pct:.1f}%) has hit the {limits.max_weekly_loss_pct:.0f}% weekly maximum loss — no new trades until next week.",
            createdAt=_now_iso(),
            code="risk_weekly_loss_limit",
        )

    monthly_pnl_pct = monthly_realized_pnl_pct(portfolio, sim_day)
    if monthly_pnl_pct <= -limits.max_monthly_loss_pct:
        yield RiskWarning(
            id=f"risk-{symbol}-{_now_iso()}",
            symbol=symbol,
            severity="critical",
            message=f"This month's realized loss ({monthly_pnl_pct:.1f}%) has hit the {limits.max_monthly_loss_pct:.0f}% monthly maximum loss — no new trades until next month.",
            createdAt=_now_iso(),
            code="risk_monthly_loss_limit",
        )

    trades_today_count = len(trades_opened_today(portfolio.trade_history, sim_day))
    if trades_today_count >= limits.max_trades_per_day:
        yield RiskWarning(
            id=f"risk-{symbol}-{_now_iso()}",
            symbol=symbol,
            severity="critical",
            message=f"{trades_today_count} trade(s) already opened today, at the {limits.max_trades_per_day}-trade daily maximum — no new trades until tomorrow.",
            createdAt=_now_iso(),
            code="risk_max_trades_per_day",
        )

    # CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance" —
    # a Phase 0 audit found this check previously compared
    # `portfolio.total_pnl_pct` (realized P&L relative to the account's
    # ORIGINAL starting balance) against the limit, which is a real
    # number but not a real drawdown: (a) it measures loss from the
    # starting balance, not from the account's own real peak, so an
    # account that ran up +50% before giving back 30% would still read
    # "+20%" and never trip this gate even though it just lived through a
    # real 30%-from-peak drawdown; (b) it only ever includes CLOSED
    # trades, so a large unrealized loss sitting in still-open positions
    # is invisible here until those positions actually close. Fixed by
    # reusing app/analytics.py's own real peak-to-trough
    # `max_drawdown_pct()` (unchanged for every other existing caller)
    # with the current real live equity (`portfolio_equity()`, cash plus
    # every open position's own current mark-to-market value) folded in
    # as one more point after the last closed trade.
    live_drawdown_pct = max_drawdown_pct(portfolio.trade_history, portfolio.starting_balance, current_equity=equity)
    if live_drawdown_pct >= limits.max_drawdown_pct:
        yield RiskWarning(
            id=f"risk-{symbol}-{_now_iso()}",
            symbol=symbol,
            severity="critical",
            message=f"Portfolio drawdown ({live_drawdown_pct:.1f}% from its own real peak equity) has hit the {limits.max_drawdown_pct:.0f}% limit — new trades paused.",
            createdAt=_now_iso(),
            code="risk_lifetime_drawdown",
        )

    if len(portfolio.positions) >= limits.max_open_positions:
        yield RiskWarning(
            id=f"risk-{symbol}-{_now_iso()}",
            symbol=symbol,
            severity="warning",
            message=f"Already at the {limits.max_open_positions}-open-position limit.",
            createdAt=_now_iso(),
            code="risk_max_open_positions",
        )

    position_pct = proposed_value / equity * 100
    if position_pct > limits.max_position_pct:
        yield RiskWarning(
            id=f"risk-{symbol}-{_now_iso()}",
            symbol=symbol,
            severity="critical",
            message=f"{symbol} position would be {position_pct:.1f}% of equity, exceeding the {limits.max_position_pct:.0f}% max position limit.",
            createdAt=_now_iso(),
            code="risk_position_size_limit",
        )


def evaluate_sentinel_risk(
    limits: RiskLimits,
    portfolio: PaperPortfolio,
    *,
    symbol: str,
    proposed_value: float,
    sim_day: int,
) -> RiskWarning | None:
    """Sentinel's trade-approval gate — unchanged contract: the first
    real violation found, in the same severity order as always, since a
    single clear reason is more useful in a vote's "reason" field than a
    combined list. See `_sentinel_checks()` above for the real checks
    themselves and `evaluate_all_sentinel_checks()` below for the full
    list."""
    return next(_sentinel_checks(limits, portfolio, symbol=symbol, proposed_value=proposed_value, sim_day=sim_day), None)


def evaluate_all_sentinel_checks(
    limits: RiskLimits,
    portfolio: PaperPortfolio,
    *,
    symbol: str,
    proposed_value: float,
    sim_day: int,
) -> list[RiskWarning]:
    """CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance"
    — every real Sentinel violation for this candidate trade, not just
    the first (see `evaluate_sentinel_risk()`'s own docstring for why
    that one stays single-reason). Feeds `evaluate_pretrade_risk_decision()`
    (app/portfolio_risk.py) so a rejected/reduced trade can show its full
    real reason list, never a black-box score."""
    return list(_sentinel_checks(limits, portfolio, symbol=symbol, proposed_value=proposed_value, sim_day=sim_day))


def evaluate_guardian_exposure(
    limits: RiskLimits,
    portfolio: PaperPortfolio,
    *,
    symbol: str,
) -> RiskWarning | None:
    """Guardian's concentration/exposure monitor. TradeTown doesn't track
    a real sector taxonomy (see app/watchlist.py's SEED_SYMBOLS — each
    symbol has a ResearchCategory, not a sector), so "concentration" here
    is measured per-symbol rather than per-sector: if adding to a
    position already held would push that single symbol's share of
    equity past the sector-concentration limit, that's treated as the
    same class of problem a real sector-concentration check would catch."""
    equity = portfolio_equity(portfolio)
    if equity <= 0:
        return None

    existing_value = sum(p.quantity * p.current_price for p in portfolio.positions if p.symbol == symbol)
    concentration_pct = existing_value / equity * 100
    if concentration_pct > limits.max_sector_concentration_pct:
        return RiskWarning(
            id=f"guardian-{symbol}-{_now_iso()}",
            symbol=symbol,
            severity="warning",
            message=f"{symbol} already makes up {concentration_pct:.1f}% of the portfolio, above the {limits.max_sector_concentration_pct:.0f}% concentration limit — recommend reducing exposure before adding more.",
            createdAt=_now_iso(),
            code="risk_concentration_limit",
        )

    return None


def monitor_portfolio(limits: RiskLimits, portfolio: PaperPortfolio) -> list[RiskWarning]:
    """Guardian's standing watch, independent of any new trade candidate
    — run every tick to catch a portfolio drifting into trouble even
    when nobody is proposing a new position. Returns zero or more
    warnings (unlike the single-warning gates above, since a passive
    monitor may have more than one thing worth flagging at once)."""
    warnings: list[RiskWarning] = []
    equity = portfolio_equity(portfolio)
    if equity <= 0:
        return warnings

    # Same real peak-to-trough fix as evaluate_sentinel_risk() above —
    # kept consistent so Guardian's standing watch never disagrees with
    # Sentinel's own hard gate about whether the portfolio is currently
    # in a real drawdown.
    live_drawdown_pct = max_drawdown_pct(portfolio.trade_history, portfolio.starting_balance, current_equity=equity)
    if live_drawdown_pct >= limits.max_drawdown_pct:
        warnings.append(
            RiskWarning(
                id=f"guardian-drawdown-{_now_iso()}",
                symbol="PORTFOLIO",
                severity="critical",
                message=f"Portfolio drawdown ({live_drawdown_pct:.1f}% from its own real peak equity) has breached the {limits.max_drawdown_pct:.0f}% limit — Guardian recommends reducing risk across the board.",
                createdAt=_now_iso(),
                code="risk_lifetime_drawdown",
            )
        )

    by_symbol: dict[str, float] = {}
    for pos in portfolio.positions:
        by_symbol[pos.symbol] = by_symbol.get(pos.symbol, 0.0) + pos.quantity * pos.current_price
    for symbol, value in by_symbol.items():
        concentration_pct = value / equity * 100
        if concentration_pct > limits.max_sector_concentration_pct:
            warnings.append(
                RiskWarning(
                    id=f"guardian-concentration-{symbol}-{_now_iso()}",
                    symbol=symbol,
                    severity="warning",
                    message=f"{symbol} is {concentration_pct:.1f}% of the portfolio — above the {limits.max_sector_concentration_pct:.0f}% concentration limit.",
                    createdAt=_now_iso(),
                    code="risk_concentration_limit",
                )
            )

    return warnings


def compute_daily_objective_status(limits: RiskLimits, portfolio: PaperPortfolio, sim_day: int) -> DailyObjectiveStatus:
    """v0.7 Feature 49 — a real-time readout of today's real trading
    activity against the CEO's configured Daily Trading Objectives,
    computed fresh every tick from `portfolio.trade_history` (the same
    'derived, recomputed rather than persisted' convention
    app/company_health.py and app/company_dna.py already use). Reports
    the same halt condition `evaluate_sentinel_risk` above actually
    enforces, so the Command Center can show *why* new trades stopped
    without duplicating the gating logic itself."""
    trades_today_count = len(trades_opened_today(portfolio.trade_history, sim_day))
    daily_pnl_pct = daily_realized_pnl_pct(portfolio, sim_day)

    profit_target_reached = daily_pnl_pct >= limits.daily_profit_target_pct
    max_loss_reached = daily_pnl_pct <= -limits.max_daily_loss_pct
    max_trades_reached = trades_today_count >= limits.max_trades_per_day

    halt_reason: str | None = None
    if max_loss_reached:
        halt_reason = f"Daily maximum loss reached ({daily_pnl_pct:.1f}% / -{limits.max_daily_loss_pct:.0f}%) — protecting capital, no new trades until tomorrow."
    elif profit_target_reached:
        halt_reason = f"Daily profit target reached ({daily_pnl_pct:+.1f}% / {limits.daily_profit_target_pct:.0f}%) — protecting today's gain, no new trades until tomorrow."
    elif max_trades_reached:
        halt_reason = f"Daily trade limit reached ({trades_today_count}/{limits.max_trades_per_day}) — no new trades until tomorrow."

    return DailyObjectiveStatus(
        simDay=sim_day,
        tradesToday=trades_today_count,
        realizedPnlPctToday=round(daily_pnl_pct, 2),
        profitTargetReached=profit_target_reached,
        maxLossReached=max_loss_reached,
        maxTradesReached=max_trades_reached,
        tradingHalted=profit_target_reached or max_loss_reached or max_trades_reached,
        haltReason=halt_reason,
        updatedAt=_now_iso(),
    )


def compute_risk_budget_status(limits: RiskLimits, portfolio: PaperPortfolio, sim_day: int) -> RiskBudgetStatus:
    """Prop-Firm Risk Intelligence Addendum, Piece 8 — "the system should
    understand the remaining permissible loss budget" before a trade is
    proposed, not just the raw current numbers a human would otherwise
    have to subtract by hand. Every input here is already real and
    already used elsewhere: `lifetime_drawdown_pct` is the exact same
    real peak-to-trough reading `evaluate_sentinel_risk` above already
    gates on (see app/analytics.py::max_drawdown_pct(), CEO directive
    "Portfolio Risk Engine + Firm-Wide Risk Governance"); `daily_
    realized_pnl_pct` is the same function `compute_daily_objective_
    status` above already calls. The only new arithmetic is "limit minus
    current usage, floored at 0" for the two *remaining* fields —
    packaging, not a new formula. Advisory only: this function is never
    called from any gate, only from the read-only status the CEO/agents
    see before deciding."""
    equity = portfolio_equity(portfolio)
    lifetime_drawdown_pct = max_drawdown_pct(portfolio.trade_history, portfolio.starting_balance, current_equity=equity)
    remaining_drawdown_budget_pct = max(0.0, limits.max_drawdown_pct - lifetime_drawdown_pct)

    daily_pnl_pct = daily_realized_pnl_pct(portfolio, sim_day)
    daily_loss_pct_today = max(0.0, -daily_pnl_pct)
    remaining_daily_loss_budget_pct = max(0.0, limits.max_daily_loss_pct - daily_loss_pct_today)
    daily_profit_pct_today = max(0.0, daily_pnl_pct)
    remaining_to_daily_profit_target_pct = max(0.0, limits.daily_profit_target_pct - daily_profit_pct_today)

    daily_status = compute_daily_objective_status(limits, portfolio, sim_day)

    return RiskBudgetStatus(
        equity=round(equity, 2),
        startingBalance=round(portfolio.starting_balance, 2),
        lifetimeDrawdownPct=round(lifetime_drawdown_pct, 2),
        maxDrawdownPct=limits.max_drawdown_pct,
        remainingDrawdownBudgetPct=round(remaining_drawdown_budget_pct, 2),
        dailyLossPctToday=round(daily_loss_pct_today, 2),
        maxDailyLossPct=limits.max_daily_loss_pct,
        remainingDailyLossBudgetPct=round(remaining_daily_loss_budget_pct, 2),
        dailyProfitPctToday=round(daily_profit_pct_today, 2),
        dailyProfitTargetPct=limits.daily_profit_target_pct,
        remainingToDailyProfitTargetPct=round(remaining_to_daily_profit_target_pct, 2),
        tradingHalted=daily_status.trading_halted,
        haltReason=daily_status.halt_reason,
        tradingDaysCount=distinct_trading_days(portfolio.trade_history),
        computedAt=_now_iso(),
    )


def project_loss_after_n_losses(limits: RiskLimits, portfolio: PaperPortfolio, n: int) -> ProjectedLossPath:
    """Prop-Firm Risk Intelligence Addendum, Piece 11a — Requirement 23:
    "projected loss after N consecutive losses." Compounds
    `risk_per_trade_pct` against current equity `n` times — the exact
    same per-trade risk sizing `recommended_quantity()` already uses,
    projected forward rather than applied to one trade. A deterministic
    worst-case path, not a probability distribution (that needs real
    Monte Carlo — Piece 10's job, not this function's). n=0 returns a
    single-point path at today's real equity, never a crash."""
    equity = portfolio_equity(portfolio)
    path = [round(equity, 2)]
    current = equity
    for _ in range(max(0, n)):
        current = current * (1 - limits.risk_per_trade_pct / 100.0)
        path.append(round(current, 2))
    projected_loss_pct = round((path[0] - path[-1]) / path[0] * 100.0, 2) if path[0] > 0 else 0.0
    return ProjectedLossPath(
        startingEquity=path[0],
        equityPath=path,
        consecutiveLosses=n,
        riskPerTradePct=limits.risk_per_trade_pct,
        projectedLossPct=projected_loss_pct,
        assumption=(
            "Assumes each loss trade loses exactly risk_per_trade_pct of equity at the time of that trade — "
            "a conservative worst-case assumption (real losses are often smaller due to stop management or partial "
            "fills), not a claim that every loss is always exactly this size."
        ),
        computedAt=_now_iso(),
    )
