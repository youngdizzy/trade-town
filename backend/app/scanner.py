"""ScannerManager — the "ScannerManager" role from the v0.6 brief,
backing Pulse's continuous market-scanning job. Reads quotes straight
from app.market_data's configured provider (mock in v0.6, same boundary
as app/watchlist.py — see that module's docstring) and flags gap
up/down, breakouts, volume spikes, and high-volatility moves as
ScannerAlert records.

Detection is threshold-based against the current quote only — no rolling
price history is kept (that would need a new persisted field on
GameSaveState for what is, today, flavor/discovery content rather than
something else depends on) — so "breakout" here means "a large move
confirmed by a volume spike in the same tick," not a true multi-period
range breakout. A real historical MarketDataProvider (see
app/market_data.py's module docstring) would let a future version do
proper rolling-window breakout detection without changing this module's
public shape.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from app.market_data import MarketDataProvider, Quote
from app.schemas import AlertType, ScannerAlert, WatchlistEntry

MAX_ALERTS = 30

GAP_THRESHOLD_PCT = 3.0
VOLATILITY_THRESHOLD_PCT = 4.0
VOLUME_SPIKE_THRESHOLD = 1_500_000.0
BREAKOUT_MOVE_PCT = 1.5

# Rolled per eligible symbol per tick — without this, every symbol
# crossing a threshold would alert every single tick it stays there,
# flooding the feed. Mirrors nexus.py's *_CHANCE_PER_TICK pacing
# convention (e.g. MEETING_CHANCE_PER_TICK) rather than inventing a
# second "don't spam" mechanism.
ALERT_CHANCE_PER_TICK = 0.35


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _classify(quote: Quote) -> AlertType | None:
    if quote.change_pct >= GAP_THRESHOLD_PCT:
        return "gap_up"
    if quote.change_pct <= -GAP_THRESHOLD_PCT:
        return "gap_down"
    if quote.volume >= VOLUME_SPIKE_THRESHOLD and abs(quote.change_pct) >= BREAKOUT_MOVE_PCT:
        return "breakout"
    if quote.volume >= VOLUME_SPIKE_THRESHOLD:
        return "volume_spike"
    if abs(quote.change_pct) >= VOLATILITY_THRESHOLD_PCT:
        return "high_volatility"
    return None


_ALERT_MESSAGE: dict[AlertType, str] = {
    "gap_up": "{symbol} gapped up {pct:.1f}% — watching for continuation.",
    "gap_down": "{symbol} gapped down {pct:.1f}% — watching for a reversal or further downside.",
    "breakout": "{symbol} broke out {pct:+.1f}% on a volume spike — a real move, not just noise.",
    "volume_spike": "{symbol} volume spiked well above its normal range with no clear price move yet.",
    "high_volatility": "{symbol} is swinging {pct:+.1f}% — elevated volatility worth monitoring.",
}


def tick_scanner(
    alerts: list[ScannerAlert],
    watchlist: list[WatchlistEntry],
    provider: MarketDataProvider,
) -> tuple[list[ScannerAlert], list[ScannerAlert]]:
    """One tick of Pulse's scan across the watchlist. Returns
    `(full_list, newly_detected)` — the same "full list + just happened"
    shape app/research.py's tick_research() already established — so the
    caller (nexus.py) can log/news only what's new this tick."""
    quotes = provider.get_quotes([entry.symbol for entry in watchlist])

    new_alerts: list[ScannerAlert] = []
    for entry in watchlist:
        quote = quotes.get(entry.symbol)
        if quote is None:
            continue
        alert_type = _classify(quote)
        if alert_type is None or random.random() >= ALERT_CHANCE_PER_TICK:
            continue
        new_alerts.append(
            ScannerAlert(
                id=f"alert-{entry.symbol}-{alert_type}-{_now_iso()}",
                symbol=entry.symbol,
                alertType=alert_type,
                message=_ALERT_MESSAGE[alert_type].format(symbol=entry.symbol, pct=quote.change_pct),
                detectedBy="pulse",
                createdAt=_now_iso(),
            )
        )

    combined = [*alerts, *new_alerts]
    if len(combined) > MAX_ALERTS:
        del combined[: len(combined) - MAX_ALERTS]
    return combined, new_alerts
