"""PaperBroker — the "PaperBroker" role from the v0.6 brief. The only
module that turns an approved order into a filled position or a closed
trade. app/portfolio.py still owns the actual ledger arithmetic
(open_position/close_position); this module owns the order book —
placing orders and deciding, tick by tick, whether each one's fill
condition has been met yet.

Completely simulated. There is no brokerage SDK import anywhere in this
file, no API key it could use even if there were, and no code path that
reaches a real order-execution endpoint — the same permanent boundary
app/paper_trading.py has stated since v0.5. The module is shaped so a
real adapter (Charles Schwab, Interactive Brokers, Alpaca) could
implement the same place_order()/tick_broker() calls behind a real
execution API later, mirroring app/market_data.py's MarketDataProvider
adapter pattern — but no such adapter exists or is wired in v0.6, and
wiring one in is an explicit future decision, not something this module
does by default.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.portfolio import close_position, open_position, sim_minutes
from app.schemas import AgentId, OrderSide, OrderType, PaperOrder, PaperPortfolio, PaperTrade, TimeState

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
    """Returns the price an order would fill at this tick, or None if
    its trigger condition hasn't been met yet. "limit" and "take_profit"
    share one direction convention (buy fills at-or-below the target,
    sell fills at-or-above it) since a take-profit order is just a limit
    order attached to an existing position; "stop" and "stop_loss"
    share the opposite convention (buy fills at-or-above the trigger —
    a breakout entry — sell fills at-or-below it — a protective exit).
    See PaperOrder's docstring in schemas.py for the same explanation
    from the data-model side."""
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


def tick_broker(
    portfolio: PaperPortfolio,
    prices: dict[str, float],
    new_time: TimeState,
) -> tuple[PaperPortfolio, list[PaperTrade]]:
    """Evaluates every open order against the current watchlist prices:
    fills it (opening a new position, or closing the position it's
    linked to) if its trigger condition is met, cancels it if it's
    expired unfilled, otherwise leaves it open for a future tick.
    Returns the updated portfolio and any trades that closed as a result
    of an exit order filling this tick."""
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

        fill_price = _fill_price(order, price)
        if fill_price is not None:
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
                )
            resolved.append(order.model_copy(update={"status": "filled", "filled_price": fill_price, "filled_at": _now_iso()}))

    still_open = [o for o in portfolio.orders if o.status == "open" and o.id not in {r.id for r in resolved}]
    order_log = [*resolved, *[o for o in portfolio.orders if o.status != "open"]]
    if len(order_log) > MAX_ORDER_LOG:
        del order_log[: len(order_log) - MAX_ORDER_LOG]

    portfolio = portfolio.model_copy(update={"orders": [*still_open, *order_log]})
    return portfolio, newly_closed
