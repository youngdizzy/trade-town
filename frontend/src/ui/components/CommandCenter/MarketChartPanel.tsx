import { useEffect, useState } from "react";
import { api } from "@/net/api";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { TechnicalAnalysisRead } from "@/types";
import { CandlestickChart, type ChartOverlayLine, type ChartOverlayZone } from "./CandlestickChart";
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

type OverlayCategory = "supportResistance" | "fibonacci" | "fairValueGaps" | "orderBlock" | "chartPatterns";
const OVERLAY_LABELS: Record<OverlayCategory, string> = {
  supportResistance: "S/R",
  fibonacci: "FIB",
  fairValueGaps: "FVG",
  orderBlock: "OB",
  chartPatterns: "PATTERNS",
};

function buildOverlays(ta: TechnicalAnalysisRead | null, active: Record<OverlayCategory, boolean>): { lines: ChartOverlayLine[]; zones: ChartOverlayZone[] } {
  if (!ta) return { lines: [], zones: [] };
  const lines: ChartOverlayLine[] = [];
  const zones: ChartOverlayZone[] = [];

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

  return { lines, zones };
}

/** General-purpose chart browser — symbol + timeframe pickers over the watchlist, for looking at any tracked market without needing a specific decision to drill into. */
export function MarketChartPanel() {
  const { watchlist, marketEnvironment } = useGameStore();
  const [symbol, setSymbol] = useState(watchlist[0]?.symbol ?? "AAPL");
  const [timeframe, setTimeframe] = useState("1h");
  const [timeframes, setTimeframes] = useState<string[]>(FALLBACK_TIMEFRAMES);
  const [technicalAnalysis, setTechnicalAnalysis] = useState<TechnicalAnalysisRead | null>(null);
  const [activeOverlays, setActiveOverlays] = useState<Record<OverlayCategory, boolean>>({
    supportResistance: true,
    fibonacci: false,
    fairValueGaps: true,
    orderBlock: false,
    chartPatterns: false,
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

  const { candles, loading, error } = useCandles(symbol, timeframe, 100);
  const dataStatus = candles[0]?.dataStatus ?? null;
  const watchlistEntry = watchlist.find((w) => w.symbol === symbol);
  const ticker = marketTickerStats(candles, watchlistEntry);
  const overlays = buildOverlays(technicalAnalysis?.symbol === symbol ? technicalAnalysis : null, activeOverlays);

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
      <CandlestickChart candles={candles} loading={loading} error={error} dataStatus={dataStatus} height={220} overlays={overlays} />
    </Glass>
  );
}
