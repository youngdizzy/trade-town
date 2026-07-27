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

export interface ChartOverlays {
  /** The order's fill price, if a real order was placed for this symbol — never a fabricated stop/target. */
  entry?: number;
  /** The open position's live mark price, if one exists for this symbol. */
  currentPrice?: number;
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

      const values = candles.flatMap((c) => [c.high, c.low]);
      if (overlays?.entry !== undefined) values.push(overlays.entry);
      if (overlays?.currentPrice !== undefined) values.push(overlays.currentPrice);
      const min = Math.min(...values);
      const max = Math.max(...values);
      const span = max - min || 1;
      const pad = span * 0.08;
      const yMin = min - pad;
      const yMax = max + pad;
      const yFor = (price: number) => plotBottom - ((price - yMin) / (yMax - yMin)) * plotHeight;

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
        ctx.fillText(price.toFixed(2), plotRight + 4, y);
      }

      // Candles
      const slot = plotWidth / candles.length;
      const bodyWidth = Math.max(1, slot * 0.6);
      candles.forEach((c, i) => {
        const cx = plotLeft + slot * i + slot / 2;
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

      // Overlays — only ever real values (entry fill price / live mark price)
      const drawLevel = (price: number, color: string, label: string) => {
        const y = yFor(price);
        ctx.strokeStyle = color;
        ctx.setLineDash([4, 3]);
        ctx.beginPath();
        ctx.moveTo(plotLeft, y);
        ctx.lineTo(plotRight, y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = color;
        ctx.fillText(label, plotLeft + 2, y - 6);
      };
      if (overlays?.entry !== undefined) drawLevel(overlays.entry, COLORS.entry, `ENTRY ${overlays.entry.toFixed(2)}`);
      if (overlays?.currentPrice !== undefined) drawLevel(overlays.currentPrice, COLORS.current, `MARK ${overlays.currentPrice.toFixed(2)}`);

      // Time axis — first/mid/last timestamps only, to stay readable at any width
      ctx.fillStyle = COLORS.text;
      ctx.textBaseline = "top";
      const labelIndices = [0, Math.floor(candles.length / 2), candles.length - 1];
      labelIndices.forEach((i) => {
        const c = candles[i];
        if (!c) return;
        const x = plotLeft + slot * i + slot / 2;
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
