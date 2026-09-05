import { useEffect, useRef } from "react";
import type { Candle } from "@/types";
import { EmptyState } from "./ui";

const COLORS = {
  bg: "#0c1420",
  grid: "#1f3348",
  text: "#6c8299",
  bull: "#3ce28a",
  bear: "#ff4d5e",
  entry: "#4fd8ff",
  current: "#ffb443",
};

/** "Terminal 2.1" directive — a real, pre-existing formatting bug this
 * pass's own live verification surfaced: every price label on this
 * chart (axis gridlines, ENTRY/MARK/SL/TP overlay text) used a flat
 * `.toFixed(2)`, which silently renders as "0.00" for any real
 * sub-$0.01 price — exactly what most Memecoin Sniper prices actually
 * are (see app/memecoin_sniper.py's own price generation). The exact
 * frontend analog of the backend `_round_price()` fix from the prior
 * Sniper pass (app/market_data.py) — same problem, same magnitude-
 * aware fix, on the display side this time. `>= 1` keeps the original
 * 2-decimal behavior exactly (zero change for every stock/futures/FX
 * symbol this chart already rendered correctly); `< 1` scales decimal
 * count to the price's own magnitude. */
function fmtPrice(price: number): string {
  if (price <= 0) return "0.00";
  if (price >= 1) return price.toFixed(2);
  const magnitude = Math.floor(Math.log10(price));
  const decimals = Math.min(10, 3 - magnitude);
  return price.toFixed(decimals);
}

/** CEO directive "Command Center + Professional Quant Trading Firm
 * Upgrade," Phase 2 (Markets area — chart overlays). A horizontal
 * price level (support/resistance, a Fibonacci ratio) — real prices
 * from backend/app/technical_patterns.py, never invented. */
export interface ChartOverlayLine {
  price: number;
  label: string;
  color: string;
}

/** A real price×time region — a Fair Value Gap, an Order Block, or a
 * confirmed chart pattern (double top/bottom, trendline break). `to`
 * null means the zone is still open (e.g. an unfilled FVG) and is
 * drawn out to the right edge of the visible candles rather than a
 * fabricated end point. */
export interface ChartOverlayZone {
  from: string;
  to: string | null;
  priceLow: number;
  priceHigh: number;
  label: string;
  color: string;
}

/** CEO directive "AHL-Inspired Systematic Trend & Momentum Research
 * Engine" — a real, sloped line through two or more real (timestamp,
 * price) points, e.g. a trend-engine horizon's own real start/end
 * candle. Distinct from ChartOverlayLine (a single flat level) — this
 * is this chart's first primitive that can actually slope. */
export interface ChartOverlayPolyline {
  points: { timestamp: string; price: number }[];
  label: string;
  color: string;
}

/** CEO directive "TradeTown — 11/10 Market Intelligence + Quant
 * Research Engine" — a real, single (timestamp, price) event: a
 * liquidity sweep or a Break of Structure/Change of Character, each
 * with its own real triggering candle's timestamp
 * (backend/app/market_intelligence.py's sweepTimestamp /
 * lastBreakOfStructureTimestamp — never a re-derived or estimated
 * position). Distinct from every other primitive here: not a level, not
 * a zone, not a slope — a single point in time. */
export interface ChartOverlayMarker {
  timestamp: string;
  price: number;
  label: string;
  color: string;
  /** "up"/"down" draws a small triangle in that direction (a break or a
   * sweep has a real directional sense); "dot" draws a plain circle. */
  shape: "up" | "down" | "dot";
}

export interface ChartOverlays {
  /** The order's fill price, if a real order was placed for this symbol — never a fabricated stop/target. */
  entry?: number;
  /** The open position's live mark price, if one exists for this symbol. */
  currentPrice?: number;
  /** CEO directive "Memecoin Sniper + Professional Trading Terminal UI
   * Correction" — a real, currently-active stop-loss price for the
   * position this chart is focused on. Same prominent dashed-level
   * treatment as entry/currentPrice (never the fainter analysis-line
   * style `lines` below uses) since a stop is just as operationally
   * important as the entry/mark themselves. Renders as `stopLabel` if
   * given (e.g. "TRAILING SL"), else "SL". */
  stopPrice?: number;
  stopLabel?: string;
  /** Same treatment as stopPrice, for a real take-profit target. */
  targetPrice?: number;
  targetLabel?: string;
  lines?: ChartOverlayLine[];
  zones?: ChartOverlayZone[];
  polylines?: ChartOverlayPolyline[];
  markers?: ChartOverlayMarker[];
}

/**
 * Hand-rolled canvas candlestick renderer — no charting library dependency
 * for what's fundamentally bars + wicks + a price axis. Every value drawn
 * comes straight from a real Candle (see app/market_data.py); this
 * component never invents price levels, it only draws the ones passed in
 * via `overlays`.
 */
export function CandlestickChart({
  candles,
  loading,
  error,
  dataStatus,
  overlays,
  height = 260,
}: {
  candles: Candle[];
  loading: boolean;
  error: string | null;
  dataStatus: string | null;
  overlays?: ChartOverlays;
  height?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const draw = () => {
      const dpr = window.devicePixelRatio || 1;
      const width = container.clientWidth;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = COLORS.bg;
      ctx.fillRect(0, 0, width, height);

      if (candles.length === 0) return;

      const priceAxisWidth = 56;
      const timeAxisHeight = 18;
      const plotLeft = 4;
      const plotRight = width - priceAxisWidth;
      const plotTop = 8;
      const plotBottom = height - timeAxisHeight;
      const plotWidth = Math.max(1, plotRight - plotLeft);
      const plotHeight = Math.max(1, plotBottom - plotTop);

      // "Terminal 2.2" directive — the y-axis is driven ONLY by real
      // candle highs/lows, never by overlay levels (entry/stop/target/
      // markers). A prior version folded every overlay value into this
      // same min/max, which meant a stop/target set far from the actual
      // price action (a normal thing for a wide-R memecoin trade) could
      // stretch the visible range so far that the real candle bodies/
      // wicks compressed to sub-pixel — i.e. "no candles visible" while
      // the data was correct all along. Overlay levels outside this
      // candle-driven range are still drawn (see `yForOverlay` below),
      // clamped to the plot edge with a real price label and a "beyond
      // range" arrow — never silently hidden, never allowed to distort
      // the actual price-action scale.
      const candleValues = candles.flatMap((c) => [c.high, c.low]);
      const candleMin = Math.min(...candleValues);
      const candleMax = Math.max(...candleValues);
      const candleSpan = candleMax - candleMin || candleMax * 0.02 || 1;
      const pad = candleSpan * 0.12;
      const yMin = candleMin - pad;
      const yMax = candleMax + pad;
      const yFor = (price: number) => plotBottom - ((price - yMin) / (yMax - yMin)) * plotHeight;
      // For overlay-only values (never candle highs/lows, which are by
      // construction always inside [yMin, yMax]): clamps the drawn
      // position to just inside the plot area and reports which edge it
      // clamped to, so callers can render an honest "beyond visible
      // range" indicator instead of quietly drawing at the wrong price.
      const yForOverlay = (price: number): { y: number; clampedAbove: boolean; clampedBelow: boolean } => {
        const raw = yFor(price);
        if (raw < plotTop) return { y: plotTop + 1, clampedAbove: true, clampedBelow: false };
        if (raw > plotBottom) return { y: plotBottom - 1, clampedAbove: false, clampedBelow: true };
        return { y: raw, clampedAbove: false, clampedBelow: false };
      };
      const slotWidth = plotWidth / candles.length;
      // Maps a real overlay timestamp to the x-position of its nearest
      // real candle (index-based slotting, the same spacing every candle
      // already uses) — never a true time-scale axis, but honest: it
      // never invents a position for a moment outside the visible range.
      const xFor = (timestamp: string) => {
        const t = new Date(timestamp).getTime();
        let nearest = 0;
        let nearestDiff = Infinity;
        candles.forEach((c, i) => {
          const diff = Math.abs(new Date(c.timestamp).getTime() - t);
          if (diff < nearestDiff) {
            nearestDiff = diff;
            nearest = i;
          }
        });
        return plotLeft + slotWidth * nearest + slotWidth / 2;
      };

      // Zones (Fair Value Gaps / Order Blocks / confirmed chart
      // patterns) — drawn first, as a background wash, so real candle
      // bodies/wicks stay fully visible on top of them.
      overlays?.zones?.forEach((z) => {
        const xStart = xFor(z.from);
        const xEnd = z.to !== null ? xFor(z.to) : plotRight;
        const yTop = yForOverlay(z.priceHigh).y;
        const yBottom = yForOverlay(z.priceLow).y;
        ctx.fillStyle = z.color;
        ctx.globalAlpha = 0.18;
        ctx.fillRect(Math.min(xStart, xEnd), yTop, Math.max(2, Math.abs(xEnd - xStart)), Math.max(1, yBottom - yTop));
        ctx.globalAlpha = 1;
        ctx.strokeStyle = z.color;
        ctx.globalAlpha = 0.5;
        ctx.strokeRect(Math.min(xStart, xEnd), yTop, Math.max(2, Math.abs(xEnd - xStart)), Math.max(1, yBottom - yTop));
        ctx.globalAlpha = 1;
        ctx.fillStyle = z.color;
        ctx.font = "8px monospace";
        ctx.fillText(z.label, Math.min(xStart, xEnd) + 2, yTop - 2);
        ctx.font = "9px monospace";
      });

      // Grid + price axis labels
      ctx.strokeStyle = COLORS.grid;
      ctx.fillStyle = COLORS.text;
      ctx.font = "9px monospace";
      ctx.textBaseline = "middle";
      const gridLines = 4;
      for (let i = 0; i <= gridLines; i++) {
        const price = yMin + ((yMax - yMin) * i) / gridLines;
        const y = yFor(price);
        ctx.beginPath();
        ctx.moveTo(plotLeft, y);
        ctx.lineTo(plotRight, y);
        ctx.globalAlpha = 0.5;
        ctx.stroke();
        ctx.globalAlpha = 1;
        ctx.fillText(fmtPrice(price), plotRight + 4, y);
      }

      // Candles
      const bodyWidth = Math.max(1, slotWidth * 0.6);
      candles.forEach((c, i) => {
        const cx = plotLeft + slotWidth * i + slotWidth / 2;
        const bull = c.close >= c.open;
        ctx.strokeStyle = bull ? COLORS.bull : COLORS.bear;
        ctx.fillStyle = bull ? COLORS.bull : COLORS.bear;
        ctx.beginPath();
        ctx.moveTo(cx, yFor(c.high));
        ctx.lineTo(cx, yFor(c.low));
        ctx.stroke();
        const yOpen = yFor(c.open);
        const yClose = yFor(c.close);
        const bodyTop = Math.min(yOpen, yClose);
        const bodyHeight = Math.max(1, Math.abs(yClose - yOpen));
        ctx.fillRect(cx - bodyWidth / 2, bodyTop, bodyWidth, bodyHeight);
      });

      // Real sloped lines (e.g. a trend-engine horizon's own real
      // start/end candle) — drawn through actual (timestamp, price)
      // points, never a single flat level like ChartOverlayLine below.
      overlays?.polylines?.forEach((p) => {
        if (p.points.length < 2) return;
        ctx.strokeStyle = p.color;
        ctx.globalAlpha = 0.85;
        ctx.beginPath();
        p.points.forEach((pt, i) => {
          const x = xFor(pt.timestamp);
          const y = yForOverlay(pt.price).y;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.stroke();
        ctx.globalAlpha = 1;
        const last = p.points[p.points.length - 1];
        if (last) {
          ctx.fillStyle = p.color;
          ctx.font = "8px monospace";
          ctx.fillText(p.label, xFor(last.timestamp) + 3, yForOverlay(last.price).y);
          ctx.font = "9px monospace";
        }
      });

      // Point-in-time markers (liquidity sweep / Break of Structure /
      // Change of Character) — each a real single (timestamp, price)
      // event, drawn as a small triangle/dot at its own real triggering
      // candle, never a fabricated position.
      overlays?.markers?.forEach((m) => {
        const x = xFor(m.timestamp);
        const { y, clampedAbove, clampedBelow } = yForOverlay(m.price);
        ctx.fillStyle = m.color;
        ctx.strokeStyle = m.color;
        ctx.beginPath();
        if (m.shape === "up") {
          ctx.moveTo(x, y - 6);
          ctx.lineTo(x - 5, y + 3);
          ctx.lineTo(x + 5, y + 3);
        } else if (m.shape === "down") {
          ctx.moveTo(x, y + 6);
          ctx.lineTo(x - 5, y - 3);
          ctx.lineTo(x + 5, y - 3);
        } else {
          ctx.arc(x, y, 3.5, 0, Math.PI * 2);
        }
        ctx.closePath();
        ctx.fill();
        ctx.font = "8px monospace";
        // A marker whose real price falls outside the candle-driven
        // visible range is still drawn (clamped to the plot edge), with
        // an arrow disclosing that its real price lies further off in
        // that direction — never silently repositioned without saying so.
        const offScale = clampedAbove ? " ▲" : clampedBelow ? " ▼" : "";
        ctx.fillText(`${m.label}${offScale}`, x + 6, m.shape === "down" ? y - 4 : y + 4);
        ctx.font = "9px monospace";
      });

      // Overlays — only ever real values (entry fill price / live mark price)
      const drawLevel = (price: number, color: string, label: string) => {
        const { y, clampedAbove, clampedBelow } = yForOverlay(price);
        ctx.strokeStyle = color;
        ctx.setLineDash([4, 3]);
        ctx.beginPath();
        ctx.moveTo(plotLeft, y);
        ctx.lineTo(plotRight, y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = color;
        const offScale = clampedAbove ? " ▲ beyond range" : clampedBelow ? " ▼ beyond range" : "";
        // Keep the label inside the plot area even when clamped to the
        // very top edge (a fixed y-6 offset would otherwise draw above
        // plotTop and get clipped by the canvas).
        const labelY = clampedAbove ? y + 10 : y - 6;
        ctx.fillText(`${label}${offScale}`, plotLeft + 2, labelY);
      };
      if (overlays?.entry !== undefined) drawLevel(overlays.entry, COLORS.entry, `ENTRY ${fmtPrice(overlays.entry)}`);
      if (overlays?.currentPrice !== undefined) drawLevel(overlays.currentPrice, COLORS.current, `MARK ${fmtPrice(overlays.currentPrice)}`);
      if (overlays?.stopPrice !== undefined) drawLevel(overlays.stopPrice, COLORS.bear, `${overlays.stopLabel ?? "SL"} ${fmtPrice(overlays.stopPrice)}`);
      if (overlays?.targetPrice !== undefined) drawLevel(overlays.targetPrice, COLORS.bull, `${overlays.targetLabel ?? "TP"} ${fmtPrice(overlays.targetPrice)}`);

      // Analysis overlay lines (support/resistance, Fibonacci) — a
      // finer dash than the real order-price lines above, so a genuine
      // fill/mark price never gets visually confused with an analysis
      // read that has no claim of being acted on.
      overlays?.lines?.forEach((l) => {
        const y = yForOverlay(l.price).y;
        ctx.strokeStyle = l.color;
        ctx.setLineDash([2, 4]);
        ctx.globalAlpha = 0.7;
        ctx.beginPath();
        ctx.moveTo(plotLeft, y);
        ctx.lineTo(plotRight, y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.globalAlpha = 1;
        ctx.fillStyle = l.color;
        ctx.font = "8px monospace";
        ctx.fillText(l.label, plotLeft + 2, y + 8);
        ctx.font = "9px monospace";
      });

      // Time axis — first/mid/last timestamps only, to stay readable at any width
      ctx.fillStyle = COLORS.text;
      ctx.textBaseline = "top";
      const labelIndices = [0, Math.floor(candles.length / 2), candles.length - 1];
      labelIndices.forEach((i) => {
        const c = candles[i];
        if (!c) return;
        const x = plotLeft + slotWidth * i + slotWidth / 2;
        const label = new Date(c.timestamp).toLocaleString(undefined, { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
        ctx.textAlign = i === 0 ? "left" : i === candles.length - 1 ? "right" : "center";
        ctx.fillText(label, x, plotBottom + 3);
      });
      ctx.textAlign = "left";
    };

    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(container);
    return () => observer.disconnect();
  }, [candles, overlays, height]);

  if (loading && candles.length === 0) {
    return (
      <div style={{ height }} className="flex items-center justify-center text-cmd-textDim">
        Loading chart…
      </div>
    );
  }
  if (error) {
    return (
      <div style={{ height }} className="flex items-center justify-center text-cmd-red">
        Chart data unavailable — {error}
      </div>
    );
  }
  if (candles.length === 0) {
    return <EmptyState>No candle data for this symbol/timeframe.</EmptyState>;
  }

  return (
    <div ref={containerRef} className="relative w-full">
      <canvas ref={canvasRef} className="block w-full" />
      {dataStatus && (
        <span className="absolute left-1 top-1 rounded-sm border border-cmd-amber/50 bg-cmd-bg/80 px-1.5 py-0.5 text-[8px] uppercase tracking-wider text-cmd-amber">
          {dataStatus}
        </span>
      )}
    </div>
  );
}
