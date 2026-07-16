import type { GameSaveState } from "@/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`[api] ${init?.method ?? "GET"} ${path} failed: ${res.status} ${body}`);
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
};
