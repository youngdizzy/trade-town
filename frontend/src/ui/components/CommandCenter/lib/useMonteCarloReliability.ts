import { useEffect, useRef, useState } from "react";
import { api } from "@/net/api";
import type { MonteCarloReliabilityAssessment } from "@/types";

export interface MonteCarloReliabilityState {
  assessment: MonteCarloReliabilityAssessment | null;
  loading: boolean;
  /** Human-readable fetch failure — network error, etc. */
  error: string | null;
}

const REFRESH_MS = 30_000;

/**
 * Fetches Forge's Monte Carlo Reliability Assessment (Quantitative
 * Research & Intelligence System, Piece 7) and lightly refreshes it
 * (30s) so a real path-count drift shows up without needing to close
 * and reopen the view — same pattern as useKnowledgeGraph, since this
 * is also computed fresh server-side on every call rather than pushed
 * over the WebSocket (see backend/app/quant_developer.py's module
 * docstring for why it's a standing pipeline fact, not per-strategy
 * state).
 */
export function useMonteCarloReliability(enabled: boolean): MonteCarloReliabilityState {
  const [state, setState] = useState<MonteCarloReliabilityState>({ assessment: null, loading: true, error: null });
  const requestId = useRef(0);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    const id = ++requestId.current;

    const load = async () => {
      setState((prev) => ({ ...prev, loading: true }));
      try {
        const assessment = await api.getMonteCarloReliability();
        if (!cancelled && id === requestId.current) setState({ assessment, loading: false, error: null });
      } catch (err) {
        if (!cancelled && id === requestId.current) {
          setState((prev) => ({ assessment: prev.assessment, loading: false, error: err instanceof Error ? err.message : String(err) }));
        }
      }
    };

    void load();
    const interval = window.setInterval(() => void load(), REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [enabled]);

  return state;
}
