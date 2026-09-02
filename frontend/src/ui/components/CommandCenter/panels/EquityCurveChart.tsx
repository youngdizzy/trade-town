import { useEffect, useRef } from "react";
import { formatMoney } from "../lib/derive";

/** CEO directive "TradeTown — Paper Trading Performance & Evidence
 * Reporting 1.0," Phase 18 — a real performance timeline built from
 * actual chronological finalized outcomes, never a fabricated smooth
 * curve or an interpolated missing trade. `pnls` is the real, ordered
 * sequence of `PaperTrade.pnl` values from `paperPortfolio.tradeHistory`
 * (already the game's own real chronological order — trade_history is
 * append-only, see app/portfolio.py's close_position()); this component
 * computes nothing but a running cumulative sum on top of that real
 * sequence — no new backend read, no smoothing, no invented points
 * between real trades. Same canvas/devicePixelRatio convention
 * CandlestickChart.tsx already established, deliberately simplified —
 * a single equity line, not a full OHLC renderer."""
 */
const COLORS = {
  bg: "#0c1420",
  grid: "#1f3348",
  text: "#6c8299",
  line: "#4fd8ff",
  fillPositive: "rgba(60, 226, 138, 0.10)",
  fillNegative: "rgba(255, 77, 94, 0.10)",
  textPositive: "#3ce28a",
  textNegative: "#ff4d5e",
  zero: "#3a4d61",
};

export function EquityCurveChart({ startingBalance, pnls, height = 140 }: { startingBalance: number; pnls: number[]; height?: number }) {
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

      // Real, direct cumulative walk from starting equity — the same
      // "peak = max(peak, equity)" sequence app/analytics.py's
      // max_drawdown_pct() walks, just plotted point-by-point instead
      // of reduced to one worst-case number.
      let equity = startingBalance;
      const points = [equity, ...pnls.map((pnl) => (equity += pnl))];

      const plotLeft = 4;
      const plotRight = width - 8;
      const plotTop = 10;
      const plotBottom = height - 8;
      const plotWidth = Math.max(1, plotRight - plotLeft);
      const plotHeight = Math.max(1, plotBottom - plotTop);

      if (points.length < 2) {
        ctx.fillStyle = COLORS.text;
        ctx.font = "10px monospace";
        ctx.textAlign = "center";
        ctx.fillText("Not enough closed trades yet for an equity curve.", width / 2, height / 2);
        return;
      }

      const min = Math.min(...points, startingBalance);
      const max = Math.max(...points, startingBalance);
      const span = max - min || 1;
      const pad = span * 0.1;
      const yMin = min - pad;
      const yMax = max + pad;
      const x = (i: number) => plotLeft + (i / (points.length - 1)) * plotWidth;
      const y = (v: number) => plotBottom - ((v - yMin) / (yMax - yMin)) * plotHeight;

      // Starting-balance reference line.
      ctx.strokeStyle = COLORS.zero;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(plotLeft, y(startingBalance));
      ctx.lineTo(plotRight, y(startingBalance));
      ctx.stroke();
      ctx.setLineDash([]);

      // Fill between the line and the starting-balance reference —
      // green above, red below, matching this codebase's own win/loss
      // color convention elsewhere.
      const endEquity = points.at(-1) ?? startingBalance;
      ctx.fillStyle = endEquity >= startingBalance ? COLORS.fillPositive : COLORS.fillNegative;
      ctx.beginPath();
      ctx.moveTo(x(0), y(startingBalance));
      points.forEach((v, i) => ctx.lineTo(x(i), y(v)));
      ctx.lineTo(x(points.length - 1), y(startingBalance));
      ctx.closePath();
      ctx.fill();

      // The real equity line.
      ctx.strokeStyle = COLORS.line;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      points.forEach((v, i) => (i === 0 ? ctx.moveTo(x(i), y(v)) : ctx.lineTo(x(i), y(v))));
      ctx.stroke();

      // Axis labels — starting balance and current equity, real values only.
      ctx.fillStyle = COLORS.text;
      ctx.font = "9px monospace";
      ctx.textAlign = "left";
      ctx.fillText(formatMoney(startingBalance), plotLeft, y(startingBalance) - 3);
      ctx.textAlign = "right";
      ctx.fillStyle = endEquity >= startingBalance ? COLORS.textPositive : COLORS.textNegative;
      ctx.fillText(formatMoney(endEquity), plotRight, y(endEquity) - 4);
    };

    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(container);
    return () => observer.disconnect();
  }, [startingBalance, pnls, height]);

  return (
    <div ref={containerRef} className="w-full">
      <canvas ref={canvasRef} />
    </div>
  );
}
