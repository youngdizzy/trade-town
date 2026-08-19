"""PaperBroker — the "PaperBroker" role from the v0.6 brief. The only
module that turns an approved order into a filled position or a closed
trade. app/portfolio.py still owns the actual ledger arithmetic
(open_position/close_position); this module owns the order book —
placing orders and deciding, tick by tick, whether each one's fill
condition has been met yet.

Completely simulated. There is no brokerage SDK import anywhere in this
file, no API key it could use even if there were, and no code path that
reaches a real order-execution endpoint — the same permanent boundary
app/paper_trading.py has stated since v0.5.

Design Bible Chapter 68 (Institutional Broker Management System) adds a
real `ExecutionProvider` adapter interface below, mirroring
app/market_data.py's `MarketDataProvider` pattern exactly: an ABC that a
real broker connector (Charles Schwab, Interactive Brokers, Alpaca)
could implement later, plus one concrete `PaperExecutionProvider` that
simply delegates to the free functions in this module (still the only
order-execution code that exists). `_select_execution_provider()` reads
`EXECUTION_PROVIDER` from the environment the same way
`_select_provider()` reads `MARKET_DATA_PROVIDER` — only "paper" is
implemented, any other value falls back to paper with a warning. This
is an interface seam only. Chapter 68's "Live Trading Gate" (see
Appendix G) still applies in full: no SDK import, no credential
handling, and no real execution endpoint exist anywhere in this
codebase, and adding a real adapter class here in the future does not
by itself satisfy any of that gate's seven conditions.
"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.execution_quality import apply_slippage
from app.portfolio import close_position, open_position, sim_minutes
from app.schemas import (
    AgentId,
    MarketIntelligenceState,
    OrderSide,
    OrderType,
    PaperOrder,
    PaperPortfolio,
    PaperTrade,
    RiskLimits,
    TimeState,
)

logger = logging.getLogger("tradetown.broker")

# Resolved (filled/cancelled) orders are kept for a short audit trail —
# "Order History" in the v0.6 brief — capped the same way trade_history
# is capped in app/portfolio.py, so the list never grows unbounded.
# Orders otherwise stay open indefinitely until filled — there's no real
# time-in-force concept to honor since nothing here is a real order, so
# no expiry/cancellation-by-age is implemented.
MAX_ORDER_LOG = 40


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def place_order(
    portfolio: PaperPortfolio,
    *,
    order_id: str,
    symbol: str,
    side: OrderSide,
    order_type: OrderType,
    quantity: float,
    price: float,
    placed_by: AgentId,
    reason: str,
    confidence: float,
    linked_position_id: str | None = None,
) -> PaperPortfolio:
    """Appends a new "open" order to the book. Does not evaluate or fill
    it — that only happens on the next tick_broker() call, so a market
    order placed this tick is guaranteed to fill no earlier than the
    following tick, the same one-tick-of-latency every other NEXUS
    system already has."""
    if quantity <= 0 or price <= 0:
        return portfolio
    order = PaperOrder(
        id=order_id,
        symbol=symbol,
        side=side,
        orderType=order_type,
        quantity=quantity,
        price=price,
        status="open",
        placedBy=placed_by,
        reason=reason,
        confidence=confidence,
        linkedPositionId=linked_position_id,
        createdAt=_now_iso(),
    )
    return portfolio.model_copy(update={"orders": [*portfolio.orders, order]})


def _fill_price(order: PaperOrder, current_price: float) -> float | None:
    """Returns the price an order would trigger at this tick, or None if
    its trigger condition hasn't been met yet. "limit" and "take_profit"
    share one direction convention (buy fills at-or-below the target,
    sell fills at-or-above it) since a take-profit order is just a limit
    order attached to an existing position; "stop" and "stop_loss"
    share the opposite convention (buy fills at-or-above the trigger —
    a breakout entry — sell fills at-or-below it — a protective exit).
    See PaperOrder's docstring in schemas.py for the same explanation
    from the data-model side.

    CEO directive "Next Professional Trading Firm Phase," Priority 1
    (Execution Realism) — this is still the pre-slippage TRIGGER price
    only; tick_broker() below applies real slippage on top of this
    return value for "market" and triggered "stop"/"stop_loss" orders
    (both behave as a market order once their condition is met, in any
    real market). "limit"/"take_profit" orders fill at exactly this
    trigger price, unslipped — a limit order's whole definition is
    "this price or better," so leaving it exact IS the realistic
    behavior, not a gap. See app/execution_quality.py's module
    docstring for the full reasoning."""
    if order.order_type == "market":
        return current_price
    if order.order_type in ("limit", "take_profit"):
        if order.side == "buy" and current_price <= order.price:
            return order.price
        if order.side == "sell" and current_price >= order.price:
            return order.price
        return None
    if order.order_type in ("stop", "stop_loss"):
        if order.side == "buy" and current_price >= order.price:
            return order.price
        if order.side == "sell" and current_price <= order.price:
            return order.price
        return None
    return None


# Order types that behave as a market order from the moment their
# trigger condition is met, in any real market — so, per CEO directive
# "Next Professional Trading Firm Phase," Priority 1, real slippage
# applies to their fill. "limit"/"take_profit" are deliberately excluded
# (see _fill_price()'s docstring).
_SLIPPAGE_ELIGIBLE_ORDER_TYPES: frozenset[OrderType] = frozenset({"market", "stop", "stop_loss"})


def tick_broker(
    portfolio: PaperPortfolio,
    prices: dict[str, float],
    new_time: TimeState,
    risk_limits: RiskLimits | None = None,
    market_intelligence: MarketIntelligenceState | None = None,
) -> tuple[PaperPortfolio, list[PaperTrade]]:
    """Evaluates every open order against the current watchlist prices:
    fills it (opening a new position, or closing the position it's
    linked to) if its trigger condition is met, cancels it if it's
    expired unfilled, otherwise leaves it open for a future tick.
    Returns the updated portfolio and any trades that closed as a result
    of an exit order filling this tick.

    Piece 10b — `risk_limits`, when supplied, is threaded straight into
    close_position() for the real distance-to-drawdown-ceiling snapshot
    (see that function's own docstring).

    CEO directive "Next Professional Trading Firm Phase," Priority 1
    (Execution Realism) — `market_intelligence`, when supplied, drives
    real slippage on "market" and triggered "stop"/"stop_loss" fills via
    app/execution_quality.py; None (the default, for any caller or test
    fixture that hasn't been threaded through yet) means every fill
    stays exactly at its pre-slippage trigger price, unchanged from
    before this piece existed."""
    now_minutes = sim_minutes(new_time)
    open_orders = [o for o in portfolio.orders if o.status == "open"]
    if not open_orders:
        return portfolio, []

    resolved: list[PaperOrder] = []
    newly_closed: list[PaperTrade] = []

    for order in open_orders:
        price = prices.get(order.symbol)
        if price is None:
            continue

        trigger_price = _fill_price(order, price)
        if trigger_price is not None:
            slippage_bps = 0.0
            fill_price = trigger_price
            if order.order_type in _SLIPPAGE_ELIGIBLE_ORDER_TYPES:
                fill_price, slippage_bps = apply_slippage(
                    trigger_price, action_side=order.side, market_intelligence=market_intelligence, symbol=order.symbol
                )
            if order.linked_position_id:
                position = next((p for p in portfolio.positions if p.id == order.linked_position_id), None)
                if position is None:
                    # The linked position already closed some other way
                    # (e.g. app/paper_trading.py's hold-duration close) —
                    # this exit order has nothing left to act on.
                    resolved.append(order.model_copy(update={"status": "cancelled"}))
                    continue
                held_for = now_minutes - position.opened_sim_minutes
                reason = "Take-profit target reached" if order.order_type == "take_profit" else "Stop-loss triggered"
                market_conditions = f"{order.symbol} hit the {order.order_type.replace('_', ' ')} at {fill_price:.2f}."
                portfolio, trade = close_position(
                    portfolio,
                    position_id=order.linked_position_id,
                    exit_price=fill_price,
                    duration_minutes=held_for,
                    reason=reason,
                    market_conditions=market_conditions,
                    supporting_agents=[order.placed_by],
                    opposing_agents=[],
                    risk_limits=risk_limits,
                    exit_slippage_bps=slippage_bps,
                )
                if trade:
                    newly_closed.append(trade)
            else:
                portfolio = open_position(
                    portfolio,
                    position_id=f"pos-{order.id}",
                    symbol=order.symbol,
                    price=fill_price,
                    opened_by=order.placed_by,
                    confidence=order.confidence,
                    opened_sim_minutes=now_minutes,
                    side=order.side,
                    quantity=order.quantity,
                    entry_slippage_bps=slippage_bps,
                )
            resolved.append(order.model_copy(update={"status": "filled", "filled_price": fill_price, "filled_at": _now_iso()}))

    still_open = [o for o in portfolio.orders if o.status == "open" and o.id not in {r.id for r in resolved}]
    order_log = [*resolved, *[o for o in portfolio.orders if o.status != "open"]]
    if len(order_log) > MAX_ORDER_LOG:
        del order_log[: len(order_log) - MAX_ORDER_LOG]

    portfolio = portfolio.model_copy(update={"orders": [*still_open, *order_log]})
    return portfolio, newly_closed


class ExecutionProvider(ABC):
    """Adapter interface for turning an approved order into a filled
    position or a closed trade. A real implementation (Charles Schwab,
    Interactive Brokers, Alpaca, ...) would wrap that broker's order-
    execution API behind this same shape — app/nexus.py only ever calls
    `tick_broker()` on whatever provider is selected, so nothing
    downstream needs to change when a real adapter replaces the paper
    one. See this module's docstring and Design Bible Chapter 68 for why
    no such adapter exists yet."""

    @abstractmethod
    def place_order(
        self,
        portfolio: PaperPortfolio,
        *,
        order_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: float,
        placed_by: AgentId,
        reason: str,
        confidence: float,
        linked_position_id: str | None = None,
    ) -> PaperPortfolio: ...

    @abstractmethod
    def tick_broker(
        self,
        portfolio: PaperPortfolio,
        prices: dict[str, float],
        new_time: TimeState,
        risk_limits: RiskLimits | None = None,
        market_intelligence: MarketIntelligenceState | None = None,
    ) -> tuple[PaperPortfolio, list[PaperTrade]]: ...


class PaperExecutionProvider(ExecutionProvider):
    """The only ExecutionProvider implementation in this codebase.
    Delegates directly to this module's existing, unchanged
    place_order()/tick_broker() free functions — this class adds no new
    behavior, only the real seam a future adapter would implement
    instead."""

    def place_order(
        self,
        portfolio: PaperPortfolio,
        *,
        order_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: float,
        placed_by: AgentId,
        reason: str,
        confidence: float,
        linked_position_id: str | None = None,
    ) -> PaperPortfolio:
        return place_order(
            portfolio,
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            placed_by=placed_by,
            reason=reason,
            confidence=confidence,
            linked_position_id=linked_position_id,
        )

    def tick_broker(
        self,
        portfolio: PaperPortfolio,
        prices: dict[str, float],
        new_time: TimeState,
        risk_limits: RiskLimits | None = None,
        market_intelligence: MarketIntelligenceState | None = None,
    ) -> tuple[PaperPortfolio, list[PaperTrade]]:
        return tick_broker(portfolio, prices, new_time, risk_limits, market_intelligence)


def _select_execution_provider() -> ExecutionProvider:
    name = os.environ.get("EXECUTION_PROVIDER", "paper").strip().lower()
    if name not in ("", "paper"):
        logger.warning("EXECUTION_PROVIDER=%r has no real adapter in v0.6; falling back to paper execution.", name)
    return PaperExecutionProvider()


execution_provider: ExecutionProvider = _select_execution_provider()
