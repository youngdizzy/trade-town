"""CEO directive "Next Professional Trading Firm Phase," Priority 5 —
Research Data Integrity.

RESEARCH FIRST (per the directive's own mandatory rule): audited every
subsystem that could plausibly back a trading decision for what data it
actually consumes.

  - `app/market_data.py`'s `MockMarketDataProvider` is the only real
    `MarketDataProvider` implementation in this codebase (confirmed:
    `_select_provider()` recognizes no other `MARKET_DATA_PROVIDER`
    value) — a genuine regime-switching stochastic process (volatility
    clustering, momentum persistence, mean reversion), never a real
    exchange/broker feed. `get_candles()` always returns exactly the
    requested candle count (no gaps — this mock generator has no
    concept of a missing bar), and is deterministically seeded from
    `(symbol, timeframe)` only, never wall-clock time, so a given
    symbol/timeframe's historical series is stable across repeated
    fetches within the same run. `get_quote()`'s live walk uses an
    UNSEEDED RNG (`random.Random()` with no seed) and is therefore
    genuinely NOT reproducible run-to-run — a real, disclosed
    distinction between the two, not an oversight.
  - `app/market_intelligence.py` (Volatility/Liquidity/Structure/
    Quality reads) performs real technical-analysis math over that same
    mock candle series — the ANALYSIS is real, the underlying price
    data is simulated, not fabricated on top of.
  - `app/research.py`'s confidence gauge and `app/simulation.py`'s
    backtest metrics (confirmed by grep: zero `get_candles()` calls in
    either file) are both pure random-number generation with NO
    underlying price series at all — a materially different, weaker
    category than "simulated," named `synthetic` here so the CEO can
    tell them apart.
  - No real broker/market-data adapter and no user-data upload/import
    mechanism exist anywhere in this codebase (grep-confirmed) — both
    honestly `unavailable`, not silently omitted.

THE HONESTY BOUNDARY: this ships as ONE whole-codebase audit report,
not a provenance field grafted onto `ResearchItem`/`SimulationResult`
themselves — tagging either of those with a candle-derived category
would be fabricated, since neither ever touches candle data at all (see
above). If a future piece gives Research/Sandbox a real technical-
analysis foundation, per-item provenance becomes honestly buildable
then; it isn't yet.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.market_data import MarketDataProvider
from app.schemas import DataCategory, DataProvenanceReport, DataSourceRead, WatchlistEntry

# A representative sample size for the live coverage check below — not
# the app's own real candle-window sizing (that's each caller's own
# concern, e.g. CANDLE_WINDOW in market_intelligence.py), just enough
# to get a real, non-trivial requested-vs-delivered comparison.
SAMPLE_CANDLE_REQUEST = 20
SAMPLE_TIMEFRAME = "1h"
FALLBACK_SAMPLE_SYMBOL = "AAPL"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _live_candle_source_read(watchlist: list[WatchlistEntry], provider: MarketDataProvider) -> DataSourceRead:
    symbol = watchlist[0].symbol if watchlist else FALLBACK_SAMPLE_SYMBOL
    try:
        candles = provider.get_candles(symbol, SAMPLE_TIMEFRAME, SAMPLE_CANDLE_REQUEST)
    except ValueError:
        return DataSourceRead(
            subsystem="Live Quotes & Candles (Watchlist, Charts, Market Intelligence)",
            category="unavailable",
            detail=f"The configured provider could not serve {SAMPLE_TIMEFRAME} candles for {symbol!r} on this live check.",
            reproducible=None,
            coveragePct=0.0,
        )
    delivered = len(candles)
    coverage_pct = round(delivered / SAMPLE_CANDLE_REQUEST * 100.0, 1) if SAMPLE_CANDLE_REQUEST else 0.0
    candle_status = candles[0].data_status if candles else "no_data"
    category: DataCategory = "simulated" if candle_status == "simulated" else "unavailable"
    return DataSourceRead(
        subsystem="Live Quotes & Candles (Watchlist, Charts, Market Intelligence)",
        category=category,
        detail=(
            f"Live check against the configured MarketDataProvider: requested {SAMPLE_CANDLE_REQUEST} "
            f"{SAMPLE_TIMEFRAME} candles for {symbol!r}, delivered {delivered}, each stamped "
            f"data_status={candle_status!r}. A regime-switching stochastic process, not a real exchange feed."
        ),
        reproducible=True,
        coveragePct=coverage_pct,
    )


def compute_data_provenance_report(watchlist: list[WatchlistEntry], provider: MarketDataProvider) -> DataProvenanceReport:
    sources = [
        _live_candle_source_read(watchlist, provider),
        DataSourceRead(
            subsystem="Research Desk (ResearchItem confidence)",
            category="synthetic",
            detail=(
                "app/research.py's confidence gauge climbs a random amount each tick "
                "(CONFIDENCE_GAIN_RANGE); it never calls get_candles() and is not derived "
                "from any price series."
            ),
            reproducible=False,
            coveragePct=None,
        ),
        DataSourceRead(
            subsystem="Sandbox Backtests (SimulationResult)",
            category="synthetic",
            detail=(
                "app/simulation.py's _placeholder_backtest_metrics draws win rate/avg win/avg "
                "loss from hand-chosen random ranges per TestScenario; it never calls "
                "get_candles() and has no real per-trade return sequence behind it."
            ),
            reproducible=False,
            coveragePct=None,
        ),
        DataSourceRead(
            subsystem="Strategy Lab — Monte Carlo Testing",
            category="synthetic",
            detail=(
                "app/strategy_lab.py bootstraps trade sequences from a Strategy's own real "
                "aggregated SimulationResult stats — a real statistical technique applied to "
                "an underlying source that is itself synthetic (see Sandbox Backtests above)."
            ),
            reproducible=False,
            coveragePct=None,
        ),
        DataSourceRead(
            subsystem="Strategy Lab — Liquidity & Market Structure Validation",
            category="simulated",
            detail=(
                "Reuses app/market_intelligence.py's real compute_liquidity()/"
                "compute_market_structure() against the strategy's own watched symbols — "
                "real technical-analysis math over the same simulated candle series as "
                "Live Quotes & Candles above."
            ),
            reproducible=True,
            coveragePct=None,
        ),
        DataSourceRead(
            subsystem="Real market data (any live broker/exchange feed)",
            category="unavailable",
            detail=(
                "MarketDataProvider(ABC) has exactly one concrete implementation "
                "(MockMarketDataProvider); no other MARKET_DATA_PROVIDER value is recognized. "
                "Design Bible Chapter 68's Live Trading Gate is not satisfied."
            ),
            reproducible=None,
            coveragePct=None,
        ),
        DataSourceRead(
            subsystem="User-provided data (CSV/API upload)",
            category="unavailable",
            detail="No data upload or import endpoint exists anywhere in this codebase.",
            reproducible=None,
            coveragePct=None,
        ),
    ]
    return DataProvenanceReport(sources=sources, updatedAt=_now_iso())
