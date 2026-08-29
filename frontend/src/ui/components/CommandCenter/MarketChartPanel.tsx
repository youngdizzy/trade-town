import { useEffect, useState } from "react";
import { api } from "@/net/api";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { Candle, LiquidityRead, MarketStructureRead, MultiHorizonTrendScore, PaperPosition, SessionRangeRead, TechnicalAnalysisRead, TrendEnsembleReading } from "@/types";
import { CandlestickChart, type ChartOverlayLine, type ChartOverlayMarker, type ChartOverlayPolyline, type ChartOverlayZone } from "./CandlestickChart";
import { marketTickerStats } from "./lib/derive";
import { useCandles } from "./lib/useCandles";
import { Glass, TerminalLabel } from "./ui";

const FALLBACK_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"];

// CEO directive "Command Center + Professional Quant Trading Firm
// Upgrade," Phase 2 (Markets — chart overlays). Real hex colors for
// the canvas renderer — CandlestickChart.tsx has no Tailwind class
// access, it draws directly to a 2D context. Support/resistance tints
// green/red toward the real role backend/app/technical_patterns.py's
// detect_support_resistance_levels() already assigns (current close
// above/below); everything else gets its own distinct real color so
// no two overlay categories are visually confused with each other.
const SUPPORT_COLOR = "#5fd4a0";
const RESISTANCE_COLOR = "#ff8a8a";
const FIBONACCI_COLOR = "#f4c14e";
const FVG_BULLISH_COLOR = "#3ce28a";
const FVG_BEARISH_COLOR = "#ff4d5e";
const ORDER_BLOCK_COLOR = "#c084fc";
const CHART_PATTERN_COLOR = "#60a5fa";
const LIQUIDITY_COLOR = "#38bdf8";
const SESSION_RANGE_COLOR = "#94a3b8";
// CEO directive "AHL-Inspired Systematic Trend & Momentum Research
// Engine" — real, distinct colors for the Fast/Medium/Slow trend-engine
// horizons, kept visually decomposed (never blended into one line) per
// that directive's own explicit "never silently merge" requirement.
const TREND_FAST_COLOR = "#facc15";
const TREND_MEDIUM_COLOR = "#fb923c";
const TREND_SLOW_COLOR = "#f472b6";
// CEO directive "TradeTown — 11/10 Market Intelligence + Quant Research
// Engine" — real, distinct marker colors for the sweep/BOS/CHoCH point
// events, kept visually distinct from every existing overlay color.
const SWEEP_MARKER_COLOR = "#38bdf8";
const BOS_BULLISH_COLOR = "#3ce28a";
const BOS_BEARISH_COLOR = "#ff4d5e";
const CHOCH_COLOR = "#e879f9";

type OverlayCategory = "supportResistance" | "fibonacci" | "fairValueGaps" | "orderBlock" | "chartPatterns" | "liquidity" | "sessionRange" | "trendEngine" | "structure";
const OVERLAY_LABELS: Record<OverlayCategory, string> = {
  supportResistance: "S/R",
  fibonacci: "FIB",
  fairValueGaps: "FVG",
  orderBlock: "OB",
  chartPatterns: "PATTERNS",
  liquidity: "LIQUIDITY",
  sessionRange: "SESSION",
  trendEngine: "TREND",
  structure: "BOS/CHOCH",
};

// CEO directive "AHL-Inspired Systematic Trend & Momentum Research
// Engine," Phase 12/13/22 (previously deferred — see docs/Architecture.md's
// own "not built this pass" record for the Multi-Horizon Trend Engine
// follow-up). One real, sloped polyline per Fast/Medium/Slow bucket,
// anchored to REAL candle closes already on this chart (never the
// abstract raw_value alone) — `bucket.horizons[0]`'s own real
// `lookbackBars` picks the start candle, `evaluatedAtIndex` the end
// one, both real indices into the exact same candle series this chart
// is already rendering (same symbol/timeframe/limit as the fetch
// below), so the line is always reproducible from visible data.
function trendPolyline(bucket: MultiHorizonTrendScore, candles: Candle[], color: string, label: string): ChartOverlayPolyline | null {
  const horizon = bucket.horizons[0];
  if (!horizon) return null;
  const endIndex = bucket.evaluatedAtIndex;
  const startIndex = endIndex - horizon.lookbackBars;
  const startCandle = candles[startIndex];
  const endCandle = candles[endIndex];
  if (!startCandle || !endCandle) return null;
  return {
    points: [
      { timestamp: startCandle.timestamp, price: startCandle.close },
      { timestamp: endCandle.timestamp, price: endCandle.close },
    ],
    label: `${label} ${horizon.direction > 0 ? "▲" : horizon.direction < 0 ? "▼" : "—"} ${bucket.compositeScore.toFixed(1)}`,
    color,
  };
}

function buildOverlays(
  ta: TechnicalAnalysisRead | null,
  active: Record<OverlayCategory, boolean>,
  liquidityZones: { kind: "equal_highs" | "equal_lows"; price: number; touches: number }[],
  sessionRange: SessionRangeRead | null,
  firstCandleTimestamp: string | null,
  trend: TrendEnsembleReading | null,
  candles: Candle[],
  liquidity: LiquidityRead | null,
  structure: MarketStructureRead | null
): { lines: ChartOverlayLine[]; zones: ChartOverlayZone[]; polylines: ChartOverlayPolyline[]; markers: ChartOverlayMarker[] } {
  const lines: ChartOverlayLine[] = [];
  const zones: ChartOverlayZone[] = [];
  const polylines: ChartOverlayPolyline[] = [];
  const markers: ChartOverlayMarker[] = [];

  // CEO directive "TradeTown — 11/10 Market Intelligence + Quant
  // Research Engine" — Live Desk sweep + BOS/CHoCH markers. Both real
  // event timestamps come straight from backend/app/market_intelligence.py
  // (sweepTimestamp / lastBreakOfStructureTimestamp), never estimated.
  if (active.liquidity && liquidity?.sweepDetected && liquidity.sweepTimestamp !== null) {
    const sweepCandle = candles.find((c) => c.timestamp === liquidity.sweepTimestamp);
    if (sweepCandle) {
      markers.push({
        timestamp: liquidity.sweepTimestamp,
        price: liquidity.sweepDirection === "above_highs" ? sweepCandle.high : sweepCandle.low,
        label: `SWEEP ${liquidity.sweepDirection === "above_highs" ? "▲" : "▼"}`,
        color: SWEEP_MARKER_COLOR,
        shape: liquidity.sweepDirection === "above_highs" ? "up" : "down",
      });
    }
  }
  if (active.structure && structure && structure.lastBreakOfStructure !== "none" && structure.lastBreakOfStructureTimestamp !== null) {
    const breakCandle = candles.find((c) => c.timestamp === structure.lastBreakOfStructureTimestamp);
    if (breakCandle) {
      const isChoch = structure.changeOfCharacter !== "none";
      markers.push({
        timestamp: structure.lastBreakOfStructureTimestamp,
        price: structure.lastBreakOfStructure === "bullish" ? breakCandle.high : breakCandle.low,
        label: isChoch ? `CHoCH ${structure.changeOfCharacter === "bullish" ? "▲" : "▼"}` : `BOS ${structure.lastBreakOfStructure === "bullish" ? "▲" : "▼"}`,
        color: isChoch ? CHOCH_COLOR : structure.lastBreakOfStructure === "bullish" ? BOS_BULLISH_COLOR : BOS_BEARISH_COLOR,
        shape: structure.lastBreakOfStructure === "bullish" ? "up" : "down",
      });
    }
  }

  if (active.trendEngine && trend) {
    const fast = trendPolyline(trend.fast, candles, TREND_FAST_COLOR, "FAST");
    const medium = trendPolyline(trend.medium, candles, TREND_MEDIUM_COLOR, "MED");
    const slow = trendPolyline(trend.slow, candles, TREND_SLOW_COLOR, "SLOW");
    [fast, medium, slow].forEach((p) => p && polylines.push(p));
  }

  // CEO directive "Professional Quant Live Trading Desk" — Phase 0 audit
  // found both of these already real, already computed, and already
  // broadcast/fetchable, with zero prior chart consumption anywhere.
  // Pure wiring, no new backend math: real equal-high/equal-low price
  // clusters (app/market_intelligence.py::compute_liquidity()) and a
  // real session high/low (app/technical_patterns.py::
  // compute_session_range(), GET /api/market/session-range).
  if (active.liquidity) {
    liquidityZones.forEach((z) => {
      lines.push({ price: z.price, label: `${z.kind === "equal_highs" ? "EQH" : "EQL"} ${z.price.toFixed(2)} (${z.touches}x)`, color: LIQUIDITY_COLOR });
    });
  }
  if (active.sessionRange && sessionRange && firstCandleTimestamp !== null && (sessionRange.rangeHigh > 0 || sessionRange.rangeLow > 0)) {
    zones.push({
      from: firstCandleTimestamp,
      to: null,
      priceLow: sessionRange.rangeLow,
      priceHigh: sessionRange.rangeHigh,
      label: `${sessionRange.session.toUpperCase().replace(/_/g, " ")} RANGE`,
      color: SESSION_RANGE_COLOR,
    });
  }

  if (!ta) return { lines, zones, polylines, markers };

  if (active.supportResistance) {
    ta.supportResistance.levels.forEach((l) => {
      lines.push({ price: l.price, label: `${l.role === "support" ? "SUP" : "RES"} ${l.price.toFixed(2)} (${l.touches}x)`, color: l.role === "support" ? SUPPORT_COLOR : RESISTANCE_COLOR });
    });
  }
  if (active.fibonacci && ta.fibonacci.levels.length > 0) {
    ta.fibonacci.levels.forEach((l) => {
      lines.push({ price: l.price, label: `FIB ${l.ratio.toFixed(3)}`, color: FIBONACCI_COLOR });
    });
  }
  if (active.fairValueGaps) {
    ta.fairValueGaps.gaps
      .filter((g) => !g.filled)
      .forEach((g) => {
        zones.push({
          from: g.timestamp,
          to: null,
          priceLow: g.gapLow,
          priceHigh: g.gapHigh,
          label: `FVG ${g.direction === "bullish" ? "▲" : "▼"}`,
          color: g.direction === "bullish" ? FVG_BULLISH_COLOR : FVG_BEARISH_COLOR,
        });
      });
  }
  if (active.orderBlock && ta.orderBlock.direction !== "none" && ta.orderBlock.priceHigh !== null && ta.orderBlock.priceLow !== null && ta.orderBlock.timestamp !== null) {
    zones.push({
      from: ta.orderBlock.timestamp,
      to: null,
      priceLow: ta.orderBlock.priceLow,
      priceHigh: ta.orderBlock.priceHigh,
      label: "ORDER BLOCK",
      color: ORDER_BLOCK_COLOR,
    });
  }
  if (active.chartPatterns) {
    ta.chartPatterns.patterns.forEach((p) => {
      zones.push({
        from: p.formedAt,
        to: p.confirmedAt,
        priceLow: p.priceLow,
        priceHigh: p.priceHigh,
        label: p.patternType.replace(/_/g, " ").toUpperCase(),
        color: CHART_PATTERN_COLOR,
      });
    });
  }

  return { lines, zones, polylines, markers };
}

/**
 * General-purpose chart browser — symbol + timeframe pickers over the
 * watchlist, for looking at any tracked market without needing a
 * specific decision to drill into. `symbol`/`onSymbolChange` (and the
 * `timeframe` equivalents) are optional controlled-component props —
 * Professional Quant Live Trading Desk's Active Trades panel uses them
 * to re-center this same chart on a clicked trade's symbol/timeframe
 * without a second chart implementation; every existing caller that
 * doesn't pass them keeps its own original internal state, unchanged.
 */
export function MarketChartPanel({
  symbol: controlledSymbol,
  onSymbolChange,
  timeframe: controlledTimeframe,
  onTimeframeChange,
  selectedPosition,
}: {
  symbol?: string;
  onSymbolChange?: (symbol: string) => void;
  timeframe?: string;
  onTimeframeChange?: (timeframe: string) => void;
  /** CEO directive "AHL-Inspired Systematic Trend & Momentum Research
   * Engine" follow-up — a Phase 0 audit of the Live Desk found the
   * selected trade's own real entry/mark price never reached this
   * chart (only a secondary popup chart drew them). When the position's
   * own symbol matches whatever this chart is currently showing, its
   * real entryPrice/currentPrice draw as the same ENTRY/MARK lines
   * DecisionDetail's chart already uses. */
  selectedPosition?: PaperPosition | null;
} = {}) {
  const { watchlist, marketEnvironment, marketIntelligence } = useGameStore();
  const [internalSymbol, setInternalSymbol] = useState(watchlist[0]?.symbol ?? "AAPL");
  const [internalTimeframe, setInternalTimeframe] = useState("1h");
  const symbol = controlledSymbol ?? internalSymbol;
  const timeframe = controlledTimeframe ?? internalTimeframe;
  const setSymbol = onSymbolChange ?? setInternalSymbol;
  const setTimeframe = onTimeframeChange ?? setInternalTimeframe;
  const [timeframes, setTimeframes] = useState<string[]>(FALLBACK_TIMEFRAMES);
  const [technicalAnalysis, setTechnicalAnalysis] = useState<TechnicalAnalysisRead | null>(null);
  const [sessionRange, setSessionRange] = useState<SessionRangeRead | null>(null);
  const [trend, setTrend] = useState<TrendEnsembleReading | null>(null);
  const [activeOverlays, setActiveOverlays] = useState<Record<OverlayCategory, boolean>>({
    supportResistance: true,
    fibonacci: false,
    fairValueGaps: true,
    orderBlock: false,
    chartPatterns: false,
    liquidity: false,
    sessionRange: false,
    trendEngine: false,
    structure: false,
  });

  useEffect(() => {
    let cancelled = false;
    api
      .getTimeframes()
      .then((t) => !cancelled && setTimeframes(t))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!watchlist.some((w) => w.symbol === symbol) && watchlist[0]) setSymbol(watchlist[0].symbol);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only re-run when the watchlist's symbol set changes, not on every reference change
  }, [watchlist.map((w) => w.symbol).join(",")]);

  // CEO directive "Command Center + Professional Quant Trading Firm
  // Upgrade," Phase 2 (Markets — chart overlays). Reuses the existing
  // GET /api/market/technical-analysis "technical desk briefing"
  // (already real, already tested, previously only ever read by
  // MarketIntelPanel's Evidence Confluence card) — no new backend
  // endpoint, no new computation.
  useEffect(() => {
    let cancelled = false;
    api
      .getTechnicalAnalysis(symbol, timeframe, 100)
      .then((ta) => !cancelled && setTechnicalAnalysis(ta))
      .catch(() => !cancelled && setTechnicalAnalysis(null));
    return () => {
      cancelled = true;
    };
  }, [symbol, timeframe]);

  // Professional Quant Live Trading Desk — the session-range overlay's
  // real backend endpoint, keyed to the CURRENT live session
  // (marketIntelligence.session.current) since that's the only session
  // this codebase's own real candle history can meaningfully bound a
  // range for right now.
  const currentSession = marketIntelligence.session.current;
  useEffect(() => {
    let cancelled = false;
    api
      .getSessionRange(symbol, currentSession, timeframe, 100)
      .then((sr) => !cancelled && setSessionRange(sr))
      .catch(() => !cancelled && setSessionRange(null));
    return () => {
      cancelled = true;
    };
  }, [symbol, timeframe, currentSession]);

  // CEO directive "AHL-Inspired Systematic Trend & Momentum Research
  // Engine" follow-up — the real /trend-engine endpoint already existed
  // with zero chart consumption (see docs/Architecture.md's own record).
  // Only fetched while the TREND overlay is actually toggled on, same
  // on-demand convention as every other overlay category here; limit=100
  // matches useCandles() below so evaluatedAtIndex lines up with the
  // exact candles this chart renders.
  useEffect(() => {
    if (!activeOverlays.trendEngine) {
      setTrend(null);
      return;
    }
    let cancelled = false;
    api
      .getTrendEngineReading(symbol, timeframe, 100)
      .then((t) => !cancelled && setTrend(t))
      .catch(() => !cancelled && setTrend(null));
    return () => {
      cancelled = true;
    };
  }, [symbol, timeframe, activeOverlays.trendEngine]);

  const { candles, loading, error } = useCandles(symbol, timeframe, 100);
  const dataStatus = candles[0]?.dataStatus ?? null;
  const watchlistEntry = watchlist.find((w) => w.symbol === symbol);
  const ticker = marketTickerStats(candles, watchlistEntry);
  // Professional Quant Live Trading Desk — the same real, already-
  // broadcast MarketIntelligenceState.liquidity[] every other panel
  // reads (e.g. MarketIntelPanel), scoped to this chart's own symbol.
  const liquidityRead = marketIntelligence.liquidity.find((l) => l.symbol === symbol) ?? null;
  const liquidityZones = liquidityRead?.zones ?? [];
  // Same directive — the real, already-broadcast
  // MarketIntelligenceState.structure[] (Break of Structure/Change of
  // Character), previously unconsumed by any chart.
  const structureRead = marketIntelligence.structure.find((s) => s.symbol === symbol) ?? null;
  const overlays = buildOverlays(
    technicalAnalysis?.symbol === symbol ? technicalAnalysis : null,
    activeOverlays,
    liquidityZones,
    sessionRange?.symbol === symbol ? sessionRange : null,
    candles[0]?.timestamp ?? null,
    trend?.symbol === symbol ? trend : null,
    candles,
    liquidityRead,
    structureRead
  );
  // CEO directive "AHL-Inspired Systematic Trend & Momentum Research
  // Engine" follow-up — the real fix for the Live Desk chart gap this
  // directive's own Phase 0 audit found: a selected trade's own real
  // entry/mark price now actually reaches this chart, not just the
  // secondary DecisionDetail popup.
  const tradeOverlays =
    selectedPosition && selectedPosition.symbol === symbol
      ? { ...overlays, entry: selectedPosition.entryPrice, currentPrice: selectedPosition.currentPrice }
      : overlays;

  return (
    <Glass className="p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <TerminalLabel>Market Chart</TerminalLabel>
        <div className="flex gap-1.5">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="rounded-sm border border-cmd-border bg-cmd-bg px-1.5 py-0.5 text-[10px] text-cmd-text"
          >
            {watchlist.map((w) => (
              <option key={w.symbol} value={w.symbol}>
                {w.symbol}
              </option>
            ))}
          </select>
          <div className="flex gap-0.5">
            {timeframes.map((tf) => (
              <button
                key={tf}
                type="button"
                onClick={() => setTimeframe(tf)}
                className={`rounded-sm border px-1.5 py-0.5 text-[9px] uppercase transition-colors ${
                  timeframe === tf ? "border-cmd-cyan/50 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="mb-2 flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b border-cmd-border/50 pb-2 text-[10px]">
        <span className="text-lg font-semibold tabular-nums text-cmd-text">{ticker.price !== null ? `$${ticker.price.toFixed(2)}` : "—"}</span>
        {ticker.changePct !== null && (
          <span className={`tabular-nums font-medium ${ticker.changePct >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>
            {ticker.changePct >= 0 ? "+" : ""}
            {ticker.changePct.toFixed(2)}%
          </span>
        )}
        <span className="text-cmd-textDim">
          VOL <span className="tabular-nums text-cmd-text">{ticker.volume !== null ? Math.round(ticker.volume).toLocaleString() : "—"}</span>
        </span>
        <span className="text-cmd-textDim">
          VOLATILITY <span className="tabular-nums text-cmd-text">{ticker.volatilityPct !== null ? `${ticker.volatilityPct.toFixed(2)}%` : "—"}</span>
        </span>
        <span className="text-cmd-textDim">
          REGIME <span className="text-cmd-cyan">{marketEnvironment.label}</span>
        </span>
        <span className="uppercase text-cmd-textDim">{timeframe}</span>
      </div>
      <div className="mb-2 flex flex-wrap gap-1">
        {(Object.keys(OVERLAY_LABELS) as OverlayCategory[]).map((category) => (
          <button
            key={category}
            type="button"
            onClick={() => setActiveOverlays((prev) => ({ ...prev, [category]: !prev[category] }))}
            className={`rounded-sm border px-1.5 py-0.5 text-[8px] uppercase tracking-wide transition-colors ${
              activeOverlays[category] ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
            }`}
            title={`Toggle ${OVERLAY_LABELS[category]} overlay — real backend/app/technical_patterns.py data, never drawn unless real levels exist`}
          >
            {OVERLAY_LABELS[category]}
          </button>
        ))}
      </div>
      <CandlestickChart candles={candles} loading={loading} error={error} dataStatus={dataStatus} height={220} overlays={tradeOverlays} />
    </Glass>
  );
}
