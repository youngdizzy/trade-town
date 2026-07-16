import type { ScoutState, TimeState } from "@/types";
import { scheduleBlockForHour } from "./Schedule";
import { EventBus } from "./EventBus";

const DEFAULT_SCOUT: ScoutState = {
  transform: { scene: "ScoutOfficeScene", x: 128, y: 96, facing: "down" },
  location: "scout-office",
  currentTask: "Scanning market news",
  mood: 65,
  energy: 80,
  memory: [],
};

/**
 * Registry of NPC simulation state. Only Scout exists in v0.1, but the API
 * is keyed by npc id so adding a second employee later doesn't require
 * restructuring this manager.
 */
export class NPCManager {
  private static npcs = new Map<string, ScoutState>([["scout", DEFAULT_SCOUT]]);
  private static offlineTickHandle: number | null = null;

  static getScout(): ScoutState {
    return this.npcs.get("scout")!;
  }

  static setScout(state: ScoutState): void {
    this.npcs.set("scout", state);
    EventBus.emit("scout:updated", state);
  }

  static loadScout(state: ScoutState): void {
    this.setScout(state);
  }

  /** Applies an authoritative snapshot pushed from the backend over WebSocket. */
  static applyServerUpdate(state: ScoutState): void {
    this.setScout(state);
  }

  /** Local simulation fallback used only while disconnected from the backend. */
  static startOfflineFallback(getTime: () => TimeState): void {
    if (this.offlineTickHandle !== null) return;
    this.offlineTickHandle = window.setInterval(() => {
      const time = getTime();
      const block = scheduleBlockForHour(time.hour);
      const current = this.getScout();
      const next: ScoutState = {
        ...current,
        location: block.location,
        currentTask: block.task,
        energy: Math.max(10, Math.min(100, current.energy + (block.task === "Resting" ? 4 : -1))),
        mood: Math.max(10, Math.min(100, current.mood + (Math.random() > 0.5 ? 1 : -1))),
      };
      this.setScout(next);
    }, 5000);
  }

  static stopOfflineFallback(): void {
    if (this.offlineTickHandle !== null) {
      window.clearInterval(this.offlineTickHandle);
      this.offlineTickHandle = null;
    }
  }
}
