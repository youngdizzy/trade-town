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
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import PaperPortfolio, RiskLimits, RiskWarning

# Position sizing floor/ceiling, mirroring app/portfolio.py's
# MIN_POSITION_SIZE — a proposed trade smaller than this isn't worth
# routing through the full risk/voting pipeline.
MIN_TRADE_VALUE = 100.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_risk_limits() -> RiskLimits:
    return RiskLimits()


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


def evaluate_sentinel_risk(
    limits: RiskLimits,
    portfolio: PaperPortfolio,
    *,
    symbol: str,
    proposed_value: float,
) -> RiskWarning | None:
    """Sentinel's trade-approval gate. Checked in order of severity —
    the first violation found is the one reported, since a single clear
    reason is more useful in a vote's "reason" field than a combined
    list."""
    equity = portfolio_equity(portfolio)
    if equity <= 0:
        return RiskWarning(
            id=f"risk-{symbol}-{_now_iso()}",
            symbol=symbol,
            severity="critical",
            message="Portfolio equity is at or below zero — no new positions until it recovers.",
            createdAt=_now_iso(),
        )

    if portfolio.total_pnl_pct <= -limits.max_drawdown_pct:
        return RiskWarning(
            id=f"risk-{symbol}-{_now_iso()}",
            symbol=symbol,
            severity="critical",
            message=f"Portfolio drawdown ({portfolio.total_pnl_pct:.1f}%) has hit the {limits.max_drawdown_pct:.0f}% limit — new trades paused.",
            createdAt=_now_iso(),
        )

    if len(portfolio.positions) >= limits.max_open_positions:
        return RiskWarning(
            id=f"risk-{symbol}-{_now_iso()}",
            symbol=symbol,
            severity="warning",
            message=f"Already at the {limits.max_open_positions}-open-position limit.",
            createdAt=_now_iso(),
        )

    position_pct = proposed_value / equity * 100
    if position_pct > limits.max_position_pct:
        return RiskWarning(
            id=f"risk-{symbol}-{_now_iso()}",
            symbol=symbol,
            severity="critical",
            message=f"{symbol} position would be {position_pct:.1f}% of equity, exceeding the {limits.max_position_pct:.0f}% max position limit.",
            createdAt=_now_iso(),
        )

    return None


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

    if portfolio.total_pnl_pct <= -limits.max_drawdown_pct:
        warnings.append(
            RiskWarning(
                id=f"guardian-drawdown-{_now_iso()}",
                symbol="PORTFOLIO",
                severity="critical",
                message=f"Portfolio drawdown ({portfolio.total_pnl_pct:.1f}%) has breached the {limits.max_drawdown_pct:.0f}% limit — Guardian recommends reducing risk across the board.",
                createdAt=_now_iso(),
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
                )
            )

    return warnings
