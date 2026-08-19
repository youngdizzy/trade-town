"""CEO directive "Professional Trading Firm — Market-Analysis Knowledge
+ Session Intelligence Expansion," Phases 1-3 (extended by "Professional
Quant Trading Firm — Quant Intelligence + Market Analysis Completion
Phase," Phase B's real support/resistance levels) — a thin aggregator
that bundles app/technical_indicators.py's real indicator values and
app/technical_patterns.py's real pattern/structure reads into one
"technical desk briefing" for a symbol, so the frontend can fetch one
read instead of fanning out across many separate requests. No new
computation lives here — every field is a direct pass-through of an
already-real, already-tested function from those two modules. Never
wired into any live trading decision — see those modules' own
docstrings for why.
"""
from __future__ import annotations

from app.market_data import Candle
from app.schemas import TechnicalAnalysisRead, TechnicalIndicatorsRead
from app.technical_indicators import atr, ema, macd, rsi, sma, stochastic, vwap
from app.technical_patterns import (
    compute_fibonacci_levels,
    detect_candlestick_patterns,
    detect_fair_value_gaps,
    detect_order_block,
    detect_support_resistance_levels,
    label_swing_structure,
)


def compute_technical_indicators(symbol: str, candles: list[Candle]) -> TechnicalIndicatorsRead:
    macd_result = macd(candles)
    stochastic_result = stochastic(candles)
    computed = [v is not None for v in (sma(candles, period=20), rsi(candles), atr(candles))]
    detail = f"{sum(computed)} of 3 headline indicators computable from {len(candles)} real candle(s) on file." if candles else "No real candles on file for this symbol yet."
    return TechnicalIndicatorsRead(
        symbol=symbol,
        sma20=sma(candles, period=20),
        ema20=ema(candles, period=20),
        rsi14=rsi(candles),
        macdLine=macd_result[0] if macd_result else None,
        macdSignal=macd_result[1] if macd_result else None,
        macdHistogram=macd_result[2] if macd_result else None,
        stochasticPercentK=stochastic_result[0] if stochastic_result else None,
        stochasticPercentD=stochastic_result[1] if stochastic_result else None,
        atr14=atr(candles),
        vwap=vwap(candles),
        detail=detail,
    )


def compute_technical_analysis(symbol: str, candles: list[Candle]) -> TechnicalAnalysisRead:
    return TechnicalAnalysisRead(
        symbol=symbol,
        indicators=compute_technical_indicators(symbol, candles),
        swingStructure=label_swing_structure(symbol, candles),
        fairValueGaps=detect_fair_value_gaps(symbol, candles),
        candlestickPatterns=detect_candlestick_patterns(symbol, candles),
        fibonacci=compute_fibonacci_levels(symbol, candles),
        orderBlock=detect_order_block(symbol, candles),
        supportResistance=detect_support_resistance_levels(symbol, candles),
    )
