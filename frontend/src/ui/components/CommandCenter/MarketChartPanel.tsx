import { useEffect, useState } from "react";
import { api } from "@/net/api";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { CandlestickChart } from "./CandlestickChart";
import { marketTickerStats } from "./lib/derive";
import { useCandles } from "./lib/useCandles";
import { Glass, TerminalLabel } from "./ui";

const FALLBACK_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"];

/** General-purpose chart browser — symbol + timeframe pickers over the watchlist, for looking at any tracked market without needing a specific decision to drill into. */
export function MarketChartPanel() {
  const { watchlist, marketEnvironment } = useGameStore();
  const [symbol, setSymbol] = useState(watchlist[0]?.symbol ?? "AAPL");
  const [timeframe, setTimeframe] = useState("1h");
  const [timeframes, setTimeframes] = useState<string[]>(FALLBACK_TIMEFRAMES);

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

  const { candles, loading, error } = useCandles(symbol, timeframe, 100);
  const dataStatus = candles[0]?.dataStatus ?? null;
  const watchlistEntry = watchlist.find((w) => w.symbol === symbol);
  const ticker = marketTickerStats(candles, watchlistEntry);

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
      <CandlestickChart candles={candles} loading={loading} error={error} dataStatus={dataStatus} height={220} />
    </Glass>
  );
}
