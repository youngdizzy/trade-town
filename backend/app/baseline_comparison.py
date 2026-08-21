"""app/baseline_comparison.py — CEO directive "Quant Research Factory /
Strategy Discovery Engine," Phase 5: a real, honest buy-and-hold
baseline, computed over the exact same real (mock) candle window a
research experiment's own backtest already tested.

RESEARCH FIRST. app/ema_pullback_research.py already has a real
"confirmed vs. naive-entry" baseline (`confirmed_vs_naive_baseline`) —
that compares two variants of the SAME strategy family (both use a
Chandelier Stop and R-multiple targets), never a market benchmark. No
buy-and-hold/market-benchmark computation existed anywhere else in this
codebase (confirmed by a full grep of backend/ and frontend/src for
"buy_and_hold"/"benchmark" before writing this module). This module adds
one, for the general compiled-strategy pipeline
(app/research_experiment.py's `ResearchExperimentRecord`), not just the
EMA-pullback reference strategy.

UNITS ARE DELIBERATELY NOT BLENDED. A compiled strategy's own real
backtest stats (`EmaPullbackStatsBucket`) are all in R-multiples — per-
trade risk units, never a % of account value, since this codebase's
compiled-strategy engine doesn't simulate real position sizing against a
starting account balance. A buy-and-hold return here is a % price change
over a period. These are honestly different units, and this module never
manufactures a single blended "strategy beat the market by X%" number
from them. What it DOES give a researcher: real regime context — was the
underlying market itself strongly trending during the tested window? A
strategy with modest positive expectancy in a market that was up 80%
over the same window deserves more scrutiny than the same expectancy in
a flat or down market. That is a real, standard quant-research sanity
check, not a performance comparison, and `BuyAndHoldBaseline`'s own
schema docstring repeats this so no downstream reader mistakes it for
one.

Candles are re-fetched (not passed in) from
app.market_data.market_data_provider.get_candles() using the exact same
(symbol, timeframe, limit) triple the backtest itself used — that
provider's own real, seeded RNG is deterministic per that triple (see
tests/test_market_data.py's
test_historical_candles_are_stable_across_repeated_calls), so this
always reads the identical real series the backtest already replayed,
never a different or resampled one.
"""
from __future__ import annotations

from app.market_data import market_data_provider
from app.schemas import BuyAndHoldBaseline


def compute_buy_and_hold_baseline(*, symbols: list[str], timeframe: str, candles_per_symbol: int) -> list[BuyAndHoldBaseline]:
    """One real entry per symbol that has at least 2 real candles in this
    exact window, in the same order as `symbols`. A symbol with fewer
    than 2 candles is skipped — a return over a single bar or no bars is
    not a real measurement, never fabricated as 0%."""
    baselines: list[BuyAndHoldBaseline] = []
    for symbol in symbols:
        candles = market_data_provider.get_candles(symbol, timeframe, candles_per_symbol)
        if len(candles) < 2:
            continue
        start_price = candles[0].close
        end_price = candles[-1].close
        return_pct = (end_price - start_price) / start_price * 100
        baselines.append(
            BuyAndHoldBaseline(
                symbol=symbol,
                startPrice=round(start_price, 4),
                endPrice=round(end_price, 4),
                returnPct=round(return_pct, 2),
                candleCount=len(candles),
            )
        )
    return baselines
