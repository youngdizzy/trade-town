import { useEffect, useRef, useState } from "react";
import { api } from "@/net/api";
import type { Candle } from "@/types";

export interface CandlesState {
  candles: Candle[];
  loading: boolean;
  /** Human-readable fetch failure — network error, bad symbol, unsupported timeframe, etc. */
  error: string | null;
}

const REFRESH_MS = 30_000;

/**
 * Fetches OHLC candles for one symbol/timeframe and keeps them lightly
 * refreshed (30s) so the chart's rightmost bar tracks the mock's live
 * price without needing a WebSocket channel of its own. Chart data is
 * deliberately never pulled from gameStore/EventBus — see
 * app/routers/market.py's docstring on why it isn't part of
 * GameSaveState at all.
 *
 * "Terminal 2.2" directive — `historical` (an optional real `{ endTime,
 * anchorPrice }` pair, e.g. a closed trade's own `closedAt`/`exitPrice`)
 * anchors the fetch to that real past instant/price instead of the
 * always-"now" default (see app/market_data.py's
 * MockMarketDataProvider.get_candles's own docstring for why that
 * default silently broke a closed trade's chart). A historical window
 * never changes — the trade is over — so this also skips the 30s
 * refresh interval in that mode instead of re-fetching identical data
 * forever (Part XXIV: no excessive/pointless polling).
 */
export function useCandles(symbol: string, timeframe: string, limit = 120, historical?: { endTime: string; anchorPrice: number }): CandlesState {
  const [state, setState] = useState<CandlesState>({ candles: [], loading: true, error: null });
  const requestId = useRef(0);
  const endTime = historical?.endTime;
  const anchorPrice = historical?.anchorPrice;

  useEffect(() => {
    let cancelled = false;
    const id = ++requestId.current;

    const load = async () => {
      setState((prev) => ({ ...prev, loading: true }));
      try {
        const candles = await api.getCandles(symbol, timeframe, limit, endTime !== undefined ? { endTime, anchorPrice } : undefined);
        if (!cancelled && id === requestId.current) setState({ candles, loading: false, error: null });
      } catch (err) {
        if (!cancelled && id === requestId.current) {
          setState((prev) => ({ candles: prev.candles, loading: false, error: err instanceof Error ? err.message : String(err) }));
        }
      }
    };

    void load();
    // A historical (endTime-anchored) window is for a closed trade —
    // it never changes, so it's fetched once, not polled.
    const interval = endTime === undefined ? window.setInterval(() => void load(), REFRESH_MS) : null;
    return () => {
      cancelled = true;
      if (interval !== null) window.clearInterval(interval);
    };
  }, [symbol, timeframe, limit, endTime, anchorPrice]);

  return state;
}
