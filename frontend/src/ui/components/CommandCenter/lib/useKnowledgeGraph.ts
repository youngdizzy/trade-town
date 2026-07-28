import { useEffect, useRef, useState } from "react";
import { api } from "@/net/api";
import type { KnowledgeGraph } from "@/types";

export interface KnowledgeGraphState {
  graph: KnowledgeGraph | null;
  loading: boolean;
  /** Human-readable fetch failure — network error, etc. */
  error: string | null;
}

const REFRESH_MS = 30_000;

/**
 * Fetches the Company Knowledge Graph (v0.7 Feature 25.5) and lightly
 * refreshes it (30s) so newly completed research/Academy projects show up
 * without the player needing to close and reopen the view. Only polls
 * while `enabled` (i.e. the graph view is actually open) — see
 * backend/app/knowledge_graph.py's module docstring for why this is
 * computed fresh server-side on every call rather than pushed over the
 * WebSocket like the rest of GameSaveState.
 */
export function useKnowledgeGraph(enabled: boolean): KnowledgeGraphState {
  const [state, setState] = useState<KnowledgeGraphState>({ graph: null, loading: true, error: null });
  const requestId = useRef(0);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    const id = ++requestId.current;

    const load = async () => {
      setState((prev) => ({ ...prev, loading: true }));
      try {
        const graph = await api.getKnowledgeGraph();
        if (!cancelled && id === requestId.current) setState({ graph, loading: false, error: null });
      } catch (err) {
        if (!cancelled && id === requestId.current) {
          setState((prev) => ({ graph: prev.graph, loading: false, error: err instanceof Error ? err.message : String(err) }));
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
