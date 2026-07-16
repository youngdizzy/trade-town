import { useSyncExternalStore } from "react";
import { gameStore, type GameUiState } from "@/state/gameStore";

export function useGameStore(): GameUiState {
  return useSyncExternalStore(gameStore.subscribe, gameStore.getSnapshot);
}
