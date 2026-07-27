import type { AgentEnergy, Candle, GameSaveState } from "@/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    let detail = body;
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      if (parsed.detail) detail = parsed.detail;
    } catch {
      // body wasn't JSON (or had no `detail`) — fall back to the raw text above
    }
    throw new Error(detail || `[api] ${init?.method ?? "GET"} ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

export const api = {
  loadGame: () => request<GameSaveState>("/load"),
  saveGame: (state: GameSaveState) =>
    request<{ ok: true; updatedAt: string }>("/save", {
      method: "POST",
      body: JSON.stringify(state),
    }),
  health: () => request<{ status: string }>("/health"),
  getCandles: (symbol: string, timeframe: string, limit = 150) =>
    request<Candle[]>(`/market/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&limit=${limit}`),
  getTimeframes: () => request<string[]>("/market/timeframes"),
  spendEnergy: (action: string, researchId?: string) =>
    request<{ agentEnergy: AgentEnergy }>("/energy/spend", {
      method: "POST",
      body: JSON.stringify({ action, researchId: researchId ?? null }),
    }),
};
