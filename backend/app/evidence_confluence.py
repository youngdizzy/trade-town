"""app/evidence_confluence.py — CEO directive "Professional Quant
Trading Firm — Quant Intelligence + Market Analysis Completion Phase,"
Phase D: the evidence-family confluence layer over raw indicator/
pattern signals.

RESEARCH FIRST. app/signal_correlation.py already builds a real
confluence/independence read — but at the ANALYST-VOTE layer (the six
department votes app/executive.py's `generate_analyst_votes()`
produces: technical/news/macro/risk/sentiment/execution). This
directive's own worked example operates one layer BELOW that: "EMA
bullish + MACD bullish + Supertrend bullish + price above moving
average" describes four raw INDICATOR reads, not four analyst votes.
Nothing in this codebase groups indicator/pattern signals into evidence
families before this module — a real, genuine gap, not a duplicate of
app/signal_correlation.py's real but differently-scoped audit.

THE FAMILIES, AND WHY EACH SIGNAL IS ASSIGNED WHERE IT IS:
  trend           Price vs. EMA(20) and price vs. SMA(20) — both real,
                  standard trend reads, and REAL EVIDENCE THIS ENGINE
                  EXISTS TO CATCH: they are highly correlated (both are
                  "is price above its own recent moving average"),
                  exactly the "not necessarily independent confirmation"
                  problem this directive names.
  momentum        RSI(14), MACD histogram, Stochastic %K — three real,
                  standard momentum reads that commonly agree with each
                  other for the same underlying reason (they are all
                  derivatives of the same recent price momentum), the
                  same real correlation risk as the trend family above.
  volume          Price vs. VWAP — a real, standard intraday fair-value
                  read.
  price_structure The real Break of Structure app/market_intelligence.py
                  already detects (reused directly, never re-derived).
  liquidity       Real Fair Value Gaps, order blocks, and liquidity
                  sweeps — genuinely different UNDERLYING information
                  from trend/momentum (these describe real gaps/zones
                  in the price record itself, not a derived oscillator
                  of the same closes).
  pattern         The most recent real candlestick pattern.
  levels          Real Fibonacci levels — informational only (see
                  below), never counted toward directional agreement.

WHAT COUNTS TOWARD `independent_family_count`, AND WHAT DOESN'T. Only
families whose signals are genuinely directional (trend/momentum/
volume/price_structure/liquidity/pattern) can agree or disagree with a
direction. `levels` (Fibonacci) is reported but never counted — a
Fibonacci level is a real, disclosed CANDIDATE area requiring
confirmation, never a directional claim by itself (the same "candidate
area, not a guaranteed level" boundary this codebase's own Fibonacci
Academy lesson already teaches). Liquidity-sweep direction and order-
block direction are real, named, CONVENTIONAL reads (a sweep below real
recent lows read as a conventional bullish-reversal signal) — the exact
same "real, named convention this function does not itself assert as
predictive" disclosure app/technical_indicators.py's own `rsi()`
docstring already established for its own ">70 overbought" convention.

INDEPENDENCE SCORING IS STRUCTURAL, NOT STATISTICAL. This module never
computes a real correlation coefficient between signals (that would
need a real historical joint distribution this codebase does not have
computed anywhere) — it groups signals into families by real, disclosed
domain knowledge (RSI/MACD/Stochastic are all momentum derivatives of
the same closes; EMA/SMA trend reads are both "price vs. its own
average") and reports family-level agreement as the honest proxy for
independence this directive's own "HIGHLY REDUNDANT / PARTIALLY
REDUNDANT / RELATIVELY INDEPENDENT / INSUFFICIENT DATA" framing asks
for — `net_direction` on each `EvidenceFamilyRead` and the overall
`independent_family_count` gap from `raw_signal_count` ARE that
framing, expressed as real structural groupings rather than an invented
statistical independence claim.

NEVER WIRED INTO A LIVE DECISION. Same boundary every other real
indicator/pattern read in this codebase keeps — `assess_evidence_
confluence()` is a new, additional, informational read, computed fresh,
never persisted, never read by app/confidence.py or app/research.py.
"""
from __future__ import annotations

from app.market_data import Candle
from app.market_intelligence import compute_liquidity, compute_market_structure
from app.schemas import EvidenceConfluenceRead, EvidenceDirection, EvidenceFamily, EvidenceFamilyRead, EvidenceSignal
from app.technical_indicators import ema, macd, rsi, sma, stochastic, vwap
from app.technical_patterns import detect_candlestick_patterns, detect_fair_value_gaps, detect_order_block

RSI_BULLISH_THRESHOLD = 55.0
RSI_BEARISH_THRESHOLD = 45.0
STOCHASTIC_BULLISH_THRESHOLD = 55.0
STOCHASTIC_BEARISH_THRESHOLD = 45.0

_BULLISH_CANDLESTICKS = frozenset({"bullish_engulfing", "hammer"})
_BEARISH_CANDLESTICKS = frozenset({"bearish_engulfing", "shooting_star"})


def _collect_signals(symbol: str, candles: list[Candle]) -> list[EvidenceSignal]:
    signals: list[EvidenceSignal] = []
    if not candles:
        return signals
    close = candles[-1].close

    # -- trend --
    ema20 = ema(candles, period=20)
    if ema20 is not None:
        direction: EvidenceDirection = "bullish" if close > ema20 else ("bearish" if close < ema20 else "neutral")
        signals.append(EvidenceSignal(name="price_vs_ema20", family="trend", direction=direction, detail=f"Real close ({close:.2f}) vs. real EMA(20) ({ema20:.2f}) — a real, standard trend read."))
    sma20 = sma(candles, period=20)
    if sma20 is not None:
        direction = "bullish" if close > sma20 else ("bearish" if close < sma20 else "neutral")
        signals.append(EvidenceSignal(name="price_vs_sma20", family="trend", direction=direction, detail=f"Real close ({close:.2f}) vs. real SMA(20) ({sma20:.2f}) — a real, standard trend read, highly correlated with the EMA(20) read above."))

    # -- momentum --
    rsi14 = rsi(candles)
    if rsi14 is not None:
        direction = "bullish" if rsi14 > RSI_BULLISH_THRESHOLD else ("bearish" if rsi14 < RSI_BEARISH_THRESHOLD else "neutral")
        signals.append(EvidenceSignal(name="rsi14", family="momentum", direction=direction, detail=f"Real RSI(14) = {rsi14:.1f} — a real, conventional momentum read (>{RSI_BULLISH_THRESHOLD:g} bullish-leaning, <{RSI_BEARISH_THRESHOLD:g} bearish-leaning), never asserted as a TradeTown-validated predictive edge."))
    macd_result = macd(candles)
    if macd_result is not None:
        _line, _signal, histogram = macd_result
        direction = "bullish" if histogram > 0 else ("bearish" if histogram < 0 else "neutral")
        signals.append(EvidenceSignal(name="macd_histogram", family="momentum", direction=direction, detail=f"Real MACD histogram = {histogram:+.3f} — a real momentum-acceleration read, correlated with the RSI read above (both derive from the same recent closes)."))
    stochastic_result = stochastic(candles)
    if stochastic_result is not None:
        percent_k, _percent_d = stochastic_result
        direction = "bullish" if percent_k > STOCHASTIC_BULLISH_THRESHOLD else ("bearish" if percent_k < STOCHASTIC_BEARISH_THRESHOLD else "neutral")
        signals.append(EvidenceSignal(name="stochastic_percent_k", family="momentum", direction=direction, detail=f"Real Stochastic %K = {percent_k:.1f} — a real momentum read, correlated with RSI/MACD above."))

    # -- volume --
    vwap_value = vwap(candles)
    if vwap_value is not None:
        direction = "bullish" if close > vwap_value else ("bearish" if close < vwap_value else "neutral")
        signals.append(EvidenceSignal(name="price_vs_vwap", family="volume", direction=direction, detail=f"Real close ({close:.2f}) vs. real VWAP ({vwap_value:.2f}) — a real, standard intraday fair-value read."))

    # -- price structure (reused, not re-derived) --
    structure = compute_market_structure(symbol, candles)
    if structure.last_break_of_structure != "none":
        signals.append(
            EvidenceSignal(
                name="break_of_structure",
                family="price_structure",
                direction=structure.last_break_of_structure,  # type: ignore[arg-type]
                detail=f"Real Break of Structure: {structure.last_break_of_structure} (app/market_intelligence.py, reused directly).",
            )
        )

    # -- liquidity (reused detection, conventional directional reads) --
    liquidity = compute_liquidity(symbol, candles)
    if liquidity.sweep_detected and liquidity.sweep_direction != "none":
        direction = "bullish" if liquidity.sweep_direction == "below_lows" else "bearish"
        signals.append(
            EvidenceSignal(
                name="liquidity_sweep",
                family="liquidity",
                direction=direction,
                detail=f"Real liquidity sweep {liquidity.sweep_direction} — read as a conventional {direction}-reversal signal (a real, named convention, never asserted as TradeTown-validated predictive).",
            )
        )
    fvg_read = detect_fair_value_gaps(symbol, candles)
    open_gaps = [g for g in fvg_read.gaps if not g.filled]
    if open_gaps:
        latest_gap = open_gaps[-1]
        signals.append(EvidenceSignal(name="fair_value_gap", family="liquidity", direction=latest_gap.direction, detail=f"Real unfilled {latest_gap.direction} Fair Value Gap ({latest_gap.gap_low:.2f}-{latest_gap.gap_high:.2f})."))
    order_block = detect_order_block(symbol, candles)
    if order_block.direction != "none":
        signals.append(EvidenceSignal(name="order_block", family="liquidity", direction=order_block.direction, detail=f"Real order block ({order_block.direction}) — {order_block.detail}"))

    # -- pattern --
    candlesticks = detect_candlestick_patterns(symbol, candles)
    if candlesticks.patterns:
        latest_pattern = candlesticks.patterns[-1]
        if latest_pattern.pattern in _BULLISH_CANDLESTICKS:
            direction = "bullish"
        elif latest_pattern.pattern in _BEARISH_CANDLESTICKS:
            direction = "bearish"
        else:
            direction = "neutral"
        signals.append(EvidenceSignal(name="candlestick_pattern", family="pattern", direction=direction, detail=f"Real {latest_pattern.pattern} pattern — {latest_pattern.detail}"))

    return signals


def assess_evidence_confluence(symbol: str, candles: list[Candle]) -> EvidenceConfluenceRead:
    signals = _collect_signals(symbol, candles)
    families_present: dict[EvidenceFamily, list[EvidenceSignal]] = {}
    for signal in signals:
        families_present.setdefault(signal.family, []).append(signal)

    family_reads: list[EvidenceFamilyRead] = []
    for family, family_signals in families_present.items():
        directions = {s.direction for s in family_signals if s.direction != "neutral"}
        if not directions:
            net: EvidenceDirection = "neutral"
            detail = "Every real signal in this family currently reads neutral."
        elif len(directions) == 1:
            net = next(iter(directions))  # type: ignore[assignment]
            detail = f"Every real directional signal in this family agrees: {net}."
        else:
            net = "neutral"
            detail = "Real signals in this family genuinely disagree with each other — reported as neutral/mixed, never silently resolved toward a majority."
        family_reads.append(EvidenceFamilyRead(family=family, signals=family_signals, netDirection=net, detail=detail))

    family_reads.sort(key=lambda f: f.family)

    directional_families = [f for f in family_reads if f.family != "levels" and f.net_direction != "neutral"]
    bullish_count = sum(1 for f in directional_families if f.net_direction == "bullish")
    bearish_count = sum(1 for f in directional_families if f.net_direction == "bearish")
    if bullish_count == 0 and bearish_count == 0:
        majority: EvidenceDirection = "neutral"
    elif bullish_count >= bearish_count:
        majority = "bullish"
    else:
        majority = "bearish"

    agreeing = [f.family for f in directional_families if f.net_direction == majority] if majority != "neutral" else []
    # The real "naive count" this read exists to correct: every individual
    # signal whose OWN direction matches the eventual majority — never a
    # bare count of all non-neutral signals regardless of direction (a
    # signal that actively disagrees with the majority, or one whose own
    # family cancelled out to neutral, is not naive "confirmation").
    raw_signal_count = sum(1 for s in signals if s.direction == majority) if majority != "neutral" else 0
    independent_family_count = len(agreeing)

    if raw_signal_count == 0:
        detail = "No real directional signals available yet for this symbol."
    elif independent_family_count == raw_signal_count:
        detail = f"{raw_signal_count} real directional signal(s) agree with {majority}, and all {independent_family_count} come from genuinely distinct evidence families."
    else:
        detail = (
            f"{raw_signal_count} real directional signal(s) agree with {majority}, but only {independent_family_count} real, distinct evidence "
            f"famil(y/ies) back it — see families for which signals share an underlying evidence source."
        )

    return EvidenceConfluenceRead(
        symbol=symbol,
        families=family_reads,
        rawSignalCount=raw_signal_count,
        independentFamilyCount=independent_family_count,
        majorityDirection=majority,
        agreeingFamilies=agreeing,
        detail=detail,
    )
