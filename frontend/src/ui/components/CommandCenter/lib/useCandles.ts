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
 */
export function useCandles(symbol: string, timeframe: string, limit = 120): CandlesState {
  const [state, setState] = useState<CandlesState>({ candles: [], loading: true, error: null });
  const requestId = useRef(0);

  useEffect(() => {
    let cancelled = false;
    const id = ++requestId.current;

    const load = async () => {
      setState((prev) => ({ ...prev, loading: true }));
      try {
        const candles = await api.getCandles(symbol, timeframe, limit);
        if (!cancelled && id === requestId.current) setState({ candles, loading: false, error: null });
      } catch (err) {
        if (!cancelled && id === requestId.current) {
          setState((prev) => ({ candles: prev.candles, loading: false, error: err instanceof Error ? err.message : String(err) }));
        }
      }
    };

    void load();
    const interval = window.setInterval(() => void load(), REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [symbol, timeframe, limit]);

  return state;
}
