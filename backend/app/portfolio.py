"""PaperPortfolio bookkeeping — the "PortfolioManager" role from the v0.5
brief. Pure data operations only: opening/closing a simulated position and
marking open positions to market. No decision logic lives here (that's
app/paper_trading.py's job) — this module never decides *whether* to
trade, only how the ledger changes once told to.

Every dollar here is fictional. TradeTown never connects to a real
brokerage or spends real capital — see app/paper_trading.py's module
docstring for the full boundary statement.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import AgentId, OrderSide, PaperPortfolio, PaperPosition, PaperTrade, TimeState, TradingStyle

STARTING_BALANCE = 100_000.0
MAX_TRADE_HISTORY = 50

# Fraction of *current* cash committed to a single new paper position —
# keeps position sizing self-correcting (a smaller account opens smaller
# positions) without needing a separate risk-sizing model this early.
POSITION_SIZE_FRACTION = 0.05
MIN_POSITION_SIZE = 100.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sim_minutes(time: TimeState) -> int:
    """Simulated-clock minutes-since-epoch — hold/expiry durations across
    the paper-trading system (app/paper_trading.py, app/broker.py) are
    tracked against TradeTown's in-game clock, not wall-clock time, the
    same way research confidence advances by tick count rather than
    elapsed real time (see app/research.py)."""
    return time.day * 1440 + time.hour * 60 + time.minute


def default_portfolio() -> PaperPortfolio:
    return PaperPortfolio(
        cashBalance=STARTING_BALANCE,
        startingBalance=STARTING_BALANCE,
        positions=[],
        orders=[],
        tradeHistory=[],
        totalPnl=0.0,
        totalPnlPct=0.0,
        winCount=0,
        lossCount=0,
    )


def open_position(
    portfolio: PaperPortfolio,
    *,
    position_id: str,
    symbol: str,
    price: float,
    opened_by: AgentId,
    confidence: float,
    opened_sim_minutes: int,
    side: OrderSide = "buy",
    quantity: float | None = None,
    trading_style: TradingStyle | None = None,
) -> PaperPortfolio:
    """Commits POSITION_SIZE_FRACTION of current cash to a new position at
    `price`, unless the caller already knows the exact size it wants (see
    app/broker.py, which sizes fills via app/risk_engine.py's
    recommended_quantity() instead of this module's flat-fraction
    default). No-ops (returns the portfolio unchanged) if cash is too low
    to open a meaningful position, rather than opening a zero-size one.
    `trading_style` (Design Bible Chapter 74) — the real "day"/"swing"
    tag app/trading_modes.py's assign_trading_style() assigned to the
    TradeProposal this position was opened from; None for any caller
    that doesn't pass one (unchanged, pre-chapter behavior)."""
    if quantity is None:
        budget = max(portfolio.cash_balance * POSITION_SIZE_FRACTION, 0.0)
        if budget < MIN_POSITION_SIZE or price <= 0:
            return portfolio
        quantity = round(budget / price, 4)
    elif quantity <= 0 or price <= 0 or quantity * price > portfolio.cash_balance:
        return portfolio
    cost = quantity * price
    position = PaperPosition(
        id=position_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        entryPrice=price,
        currentPrice=price,
        unrealizedPnl=0.0,
        unrealizedPnlPct=0.0,
        openedBy=opened_by,
        confidence=confidence,
        openedAt=_now_iso(),
        openedSimMinutes=opened_sim_minutes,
        tradingStyle=trading_style,
    )
    return portfolio.model_copy(
        update={
            "cash_balance": portfolio.cash_balance - cost,
            "positions": [*portfolio.positions, position],
        }
    )


def mark_to_market(portfolio: PaperPortfolio, prices: dict[str, float]) -> PaperPortfolio:
    """Refreshes every open position's current_price/unrealized_pnl from a
    symbol->price map (the Watchlist's last prices) — called every tick so
    the Coach Dashboard and Brain Room HUD always show live paper P&L."""
    if not portfolio.positions:
        return portfolio
    updated: list[PaperPosition] = []
    for pos in portfolio.positions:
        price = prices.get(pos.symbol, pos.current_price)
        direction = 1 if pos.side == "buy" else -1
        pnl = (price - pos.entry_price) * pos.quantity * direction
        pnl_pct = ((price - pos.entry_price) / pos.entry_price * 100 * direction) if pos.entry_price else 0.0
        updated.append(pos.model_copy(update={"current_price": price, "unrealized_pnl": pnl, "unrealized_pnl_pct": pnl_pct}))
    return portfolio.model_copy(update={"positions": updated})


def close_position(
    portfolio: PaperPortfolio,
    *,
    position_id: str,
    exit_price: float,
    duration_minutes: int,
    reason: str,
    market_conditions: str,
    supporting_agents: list[AgentId],
    opposing_agents: list[AgentId],
) -> tuple[PaperPortfolio, PaperTrade | None]:
    """Realizes a position's P&L, returns cash to the balance, and appends
    a PaperTrade to the (capped) trade history. Returns the portfolio
    unchanged (and None) if the position id isn't found — closing an
    already-closed position is a no-op, not an error, since NEXUS may
    evaluate a close condition more than once before the position clears."""
    match = next((p for p in portfolio.positions if p.id == position_id), None)
    if match is None:
        return portfolio, None

    direction = 1 if match.side == "buy" else -1
    pnl = (exit_price - match.entry_price) * match.quantity * direction
    pnl_pct = ((exit_price - match.entry_price) / match.entry_price * 100 * direction) if match.entry_price else 0.0
    proceeds = match.quantity * exit_price

    trade = PaperTrade(
        id=f"trade-{position_id}",
        symbol=match.symbol,
        side=match.side,
        quantity=match.quantity,
        entryPrice=match.entry_price,
        exitPrice=exit_price,
        pnl=pnl,
        pnlPct=pnl_pct,
        durationMinutes=duration_minutes,
        confidence=match.confidence,
        reason=reason,
        marketConditions=market_conditions,
        supportingAgents=supporting_agents,
        opposingAgents=opposing_agents,
        openedAt=match.opened_at,
        closedAt=_now_iso(),
        openedSimMinutes=match.opened_sim_minutes,
        closedSimMinutes=match.opened_sim_minutes + duration_minutes,
        tradingStyle=match.trading_style,
    )
    history = [*portfolio.trade_history, trade]
    if len(history) > MAX_TRADE_HISTORY:
        del history[: len(history) - MAX_TRADE_HISTORY]

    total_pnl = portfolio.total_pnl + pnl
    total_pnl_pct = total_pnl / portfolio.starting_balance * 100 if portfolio.starting_balance else 0.0

    updated = portfolio.model_copy(
        update={
            "cash_balance": portfolio.cash_balance + proceeds,
            "positions": [p for p in portfolio.positions if p.id != position_id],
            "trade_history": history,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "win_count": portfolio.win_count + (1 if pnl > 0 else 0),
            "loss_count": portfolio.loss_count + (1 if pnl <= 0 else 0),
        }
    )
    return updated, trade
