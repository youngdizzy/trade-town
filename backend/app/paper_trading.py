"""PaperTradingManager — decides *when* to open and close a simulated
position; app/portfolio.py owns the ledger arithmetic once told what to
do.

This module — and everything downstream of it — never connects to a real
brokerage. There is no brokerage SDK import anywhere in this file, no API
key it could use even if there were, and no code path that reaches a real
order-execution endpoint. Every "trade" here is a row in
GameSaveState.paper_portfolio, nothing more. This boundary is intentional
and permanent for TradeTown v0.5 — see docs/DESIGN_BIBLE.md's "What
TradeTown Is NOT" and the v0.5 brief's own stop condition.
"""
from __future__ import annotations

import random

from app.portfolio import close_position, mark_to_market, open_position
from app.scribe import FUTURE_TRADE_CONFIDENCE_THRESHOLD
from app.schemas import AgentId, PaperPortfolio, PaperTrade, ResearchItem, TimeState, WatchlistEntry

MIN_HOLD_MINUTES = 120
MAX_HOLD_MINUTES = 720
# Once a position has cleared MIN_HOLD_MINUTES, roll this chance every
# tick to close it — the same "memoryless random roll once eligible"
# shape as MEETING_CHANCE_PER_TICK / BREAK_CHANCE_PER_TICK in nexus.py,
# reused here rather than inventing a second pacing mechanism.
CLOSE_CHANCE_PER_TICK = 0.12


def _sim_minutes(time: TimeState) -> int:
    return time.day * 1440 + time.hour * 60 + time.minute


def tick_paper_trading(
    portfolio: PaperPortfolio,
    completed_research: list[ResearchItem],
    watchlist: list[WatchlistEntry],
    all_agent_ids: tuple[AgentId, ...],
    new_time: TimeState,
) -> tuple[PaperPortfolio, list[PaperTrade]]:
    """One tick of paper-trading orchestration: open positions for
    freshly-flagged high-confidence candidates, mark every open position
    to market, then roll closes for positions that have cleared their
    minimum hold. Returns the updated portfolio and the trades (if any)
    that closed this tick, so the caller (nexus.tick()) can hand them to
    Scribe/Coach for logging."""
    now_minutes = _sim_minutes(new_time)
    prices = {w.symbol: w.last_price for w in watchlist}

    held_symbols = {p.symbol for p in portfolio.positions}
    for item in completed_research:
        if item.confidence < FUTURE_TRADE_CONFIDENCE_THRESHOLD or not item.symbol:
            continue
        if item.symbol in held_symbols:
            continue
        price = prices.get(item.symbol)
        if price is None:
            continue
        portfolio = open_position(
            portfolio,
            position_id=f"pos-{item.id}",
            symbol=item.symbol,
            price=price,
            opened_by=item.assigned_agent,
            confidence=item.confidence,
            opened_sim_minutes=now_minutes,
        )
        held_symbols.add(item.symbol)

    portfolio = mark_to_market(portfolio, prices)

    closed: list[PaperTrade] = []
    for pos in list(portfolio.positions):
        held_for = now_minutes - pos.opened_sim_minutes
        if held_for < MIN_HOLD_MINUTES:
            continue
        if held_for < MAX_HOLD_MINUTES and random.random() >= CLOSE_CHANCE_PER_TICK:
            continue
        exit_price = prices.get(pos.symbol, pos.current_price)
        reason = "Take-profit target reached" if pos.unrealized_pnl > 0 else "Stop-loss / thesis reassessment"
        market_conditions = f"{pos.symbol} moved from {pos.entry_price:.2f} to {exit_price:.2f} over a {held_for}-minute simulated hold."
        supporting = [pos.opened_by]
        opposing = [aid for aid in all_agent_ids if aid not in (pos.opened_by, "coach")][:1]
        portfolio, trade = close_position(
            portfolio,
            position_id=pos.id,
            exit_price=exit_price,
            duration_minutes=held_for,
            reason=reason,
            market_conditions=market_conditions,
            supporting_agents=supporting,
            opposing_agents=opposing,
        )
        if trade:
            closed.append(trade)

    return portfolio, closed
