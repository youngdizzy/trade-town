"""PaperTradingManager — decides *when* to close a simulated position;
app/portfolio.py owns the ledger arithmetic once told what to do.

Through v0.5 this module also decided *when to open* a position, straight
from a high-confidence completed research item. v0.6 moves that decision
behind a vote: every trade candidate now goes through app/voting.py +
app/decision.py + app/risk_engine.py before app/broker.py places an
order, and positions open when that order fills (see
app/broker.py's tick_broker()) rather than being opened directly here.
This module keeps its mark-to-market and hold-duration-based closing
logic exactly as v0.5 shipped it — that gameplay behavior (positions
mark live, close after a random roll once past a minimum hold) is
unchanged, only *how a position gets opened in the first place* moved.

This module — and everything downstream of it — never connects to a real
brokerage. There is no brokerage SDK import anywhere in this file, no API
key it could use even if there were, and no code path that reaches a real
order-execution endpoint. Every "trade" here is a row in
GameSaveState.paper_portfolio, nothing more. This boundary is intentional
and permanent for TradeTown — see docs/DESIGN_BIBLE.md's "What TradeTown
Is NOT" and every version's own stop condition.
"""
from __future__ import annotations

import random

from app.portfolio import close_position, mark_to_market, sim_minutes
from app.schemas import AgentId, PaperPortfolio, PaperTrade, TimeState, WatchlistEntry

MIN_HOLD_MINUTES = 120
MAX_HOLD_MINUTES = 720
# Once a position has cleared MIN_HOLD_MINUTES, roll this chance every
# tick to close it — the same "memoryless random roll once eligible"
# shape as MEETING_CHANCE_PER_TICK / BREAK_CHANCE_PER_TICK in nexus.py,
# reused here rather than inventing a second pacing mechanism.
CLOSE_CHANCE_PER_TICK = 0.12


def tick_paper_trading(
    portfolio: PaperPortfolio,
    watchlist: list[WatchlistEntry],
    all_agent_ids: tuple[AgentId, ...],
    new_time: TimeState,
) -> tuple[PaperPortfolio, list[PaperTrade]]:
    """One tick of paper-trading upkeep: mark every open position to
    market, then roll closes for positions that have cleared their
    minimum hold. Returns the updated portfolio and the trades (if any)
    that closed this tick, so the caller (nexus.tick()) can hand them to
    Scribe/Coach for logging. Opening a position is app/broker.py's job
    now — see this module's docstring."""
    now_minutes = sim_minutes(new_time)
    prices = {w.symbol: w.last_price for w in watchlist}

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
