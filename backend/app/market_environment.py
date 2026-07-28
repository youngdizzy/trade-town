"""MarketEnvironment — v0.7 Feature 22, the simulated market's living
regime.

Computed every tick from the exact same real per-symbol signal the
frontend's own (now-superseded) client-side `marketRegimeHeuristic`
already used — `WatchlistEntry.dailyChangePct`, refreshed every tick by
`watchlist.tick_watchlist()` from the real (mock) `MarketDataProvider`
random walk — aggregated across the whole watchlist rather than fetched
fresh, so this costs nothing extra per tick. This module is the one
persisted, authoritative reading; the old client-only heuristic in
`frontend/src/ui/components/CommandCenter/lib/derive.ts` is kept only as
a zero-argument fallback for a render that happens before the first
server snapshot arrives.

Only five named regimes (never a probability, never a "prediction" of
what happens next — this describes the *current* aggregate state, same
as `voting.py`'s vote counts never predict a future price): bull, bear,
sideways, high_volatility, low_volatility. A real news/economic/liquidity
*event* system beyond this classification (per the v0.7 brief's longer
example list) has no dedicated real data source in this codebase — see
`app/nexus.py`'s `MARKET_HEADLINES_BY_REGIME` for the one honest hookup
that does exist (the random market headline pool is now chosen from the
real current regime's own pool instead of one shared pool, which is a
real, deterministic dependency on the computed regime, not a fabricated
"event").
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import MarketEnvironmentEntry, MarketEnvironmentRegime, MarketEnvironmentState, WatchlistEntry

# Average |daily change %| across the watchlist above which the market
# reads as "high volatility" regardless of direction — same rough
# magnitude threshold the old client heuristic used for its own
# "HIGH VOLATILITY" label.
HIGH_VOLATILITY_THRESHOLD = 3.0
# Below this, the market isn't really moving either way.
LOW_VOLATILITY_THRESHOLD = 0.4
# Average signed daily change % above which a clear directional trend
# claims "bull"/"bear" over "sideways".
TREND_THRESHOLD = 1.0

_LABEL: dict[MarketEnvironmentRegime, str] = {
    "bull": "BULL MARKET",
    "bear": "BEAR MARKET",
    "sideways": "SIDEWAYS",
    "high_volatility": "HIGH VOLATILITY",
    "low_volatility": "LOW VOLATILITY",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def evaluate_market_environment(watchlist: list[WatchlistEntry]) -> tuple[MarketEnvironmentRegime, str, str]:
    """Returns (regime, label, detail). Empty watchlist reads as
    "sideways" — an honest "nothing to measure yet" default, not a
    fabricated bull/bear call."""
    if not watchlist:
        return "sideways", _LABEL["sideways"], "No symbols on the watchlist yet."

    changes = [w.daily_change_pct for w in watchlist]
    avg = sum(changes) / len(changes)
    avg_abs = sum(abs(c) for c in changes) / len(changes)

    regime: MarketEnvironmentRegime
    if avg_abs >= HIGH_VOLATILITY_THRESHOLD:
        regime = "high_volatility"
    elif avg_abs <= LOW_VOLATILITY_THRESHOLD:
        regime = "low_volatility"
    elif avg >= TREND_THRESHOLD:
        regime = "bull"
    elif avg <= -TREND_THRESHOLD:
        regime = "bear"
    else:
        regime = "sideways"

    detail = (
        f"Aggregated over {len(watchlist)} tracked symbol{'s' if len(watchlist) != 1 else ''} — "
        f"avg move {avg:+.2f}%, avg |move| {avg_abs:.2f}%."
    )
    return regime, _LABEL[regime], detail


def default_market_environment() -> MarketEnvironmentState:
    return MarketEnvironmentState(current="sideways", label=_LABEL["sideways"], detail="No data yet.", changedSimMinutes=0, updatedAt=_now_iso(), timeline=[])


def tick_market_environment(state: MarketEnvironmentState, watchlist: list[WatchlistEntry], now_sim_minutes: int) -> tuple[MarketEnvironmentState, bool]:
    """Recomputes the regime and, only on a real change from the
    previous tick's regime, appends one MarketEnvironmentEntry to the
    timeline. Returns (new_state, changed) — callers use `changed` to
    decide whether a real regime-change NewsItem is worth publishing."""
    regime, label, detail = evaluate_market_environment(watchlist)
    changed = regime != state.current
    if not changed:
        return state.model_copy(update={"label": label, "detail": detail, "updated_at": _now_iso()}), False

    entry = MarketEnvironmentEntry(id=f"env-{regime}-{now_sim_minutes}", regime=regime, label=label, detail=detail, simMinutes=now_sim_minutes, createdAt=_now_iso())
    timeline = [*state.timeline, entry]
    new_state = MarketEnvironmentState(
        current=regime,
        label=label,
        detail=detail,
        changedSimMinutes=now_sim_minutes,
        updatedAt=_now_iso(),
        timeline=timeline,
    )
    return new_state, True
