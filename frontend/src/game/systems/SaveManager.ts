import type { ClientSaveSnapshot, EntityTransform, GameSaveState } from "@/types";
import { api } from "@/net/api";
import { EventBus } from "./EventBus";
import { GameManager } from "./GameManager";
import { NPCManager } from "./NPCManager";
import { NexusManager } from "./NexusManager";
import { TimeManager } from "./TimeManager";
import { SettingsManager } from "./SettingsManager";
import { dialogueManager } from "./DialogueManager";

const LOCAL_BACKUP_KEY = "tradetown:save-backup";

// v0.7 — Save Architecture Redesign. Mirrors backend/app/state.py's own
// MAX_DIALOGUE_HISTORY so the wire payload is bounded on both ends,
// rather than relying solely on the server-side truncation.
const MAX_DIALOGUE_HISTORY = 200;

/**
 * Builds the slim client-owned save payload and persists it via the
 * backend REST API, with a localStorage backup so a save is never lost if
 * the backend is briefly unreachable. Autosaves on an interval driven by
 * SettingsManager and exposes a manual save/load path for the UI buttons.
 *
 * v0.7 — Save Architecture Redesign: the backend's apply_client_save has
 * only ever read player/settings/dialogueHistory off a save POST — every
 * other field (agents, decisions, debates, research, ...) is already
 * server-authoritative, produced by the tick loop and persisted
 * independently of what the client sends. Building and shipping the full
 * ~50-field GameSaveState here was pure waste (a real, measured ~840KB
 * the server discarded on every autosave, and a synchronous
 * `localStorage.setItem` of the same size on every call — a genuine
 * main-thread hitch). `buildSnapshot()` now only builds what the client
 * actually owns. The full-state fetch (`api.loadGame()`/`load()` below)
 * is unaffected — reading everything to hydrate the UI is real and
 * necessary; it's only the write path that was over-broad.
 */
export class SaveManager {
  private static autosaveHandle: number | null = null;

  static buildSnapshot(): ClientSaveSnapshot {
    const game = GameManager.getInstance();
    return {
      player: game?.playerTransform ?? { scene: "LobbyScene", x: 160, y: 160, facing: "down" },
      settings: SettingsManager.current,
      dialogueHistory: dialogueManager.getHistory().slice(-MAX_DIALOGUE_HISTORY),
    };
  }

  static async save(): Promise<void> {
    const snapshot = this.buildSnapshot();
    EventBus.emit("save:started", undefined);
    try {
      localStorage.setItem(LOCAL_BACKUP_KEY, JSON.stringify(snapshot));
      const result = await api.saveGame(snapshot);
      EventBus.emit("save:completed", { at: result.updatedAt });
    } catch (err) {
      EventBus.emit("save:failed", { error: err instanceof Error ? err.message : String(err) });
    }
  }

  // v0.7 — Save Architecture Redesign: the only shape every caller of
  // load() actually needs is `.player` (MainMenuScene's continueGame()
  // starts the right scene at the right spawn point); the offline
  // fallback below genuinely can't produce a full GameSaveState (agents/
  // decisions/research only exist server-side now), so the return type
  // is narrowed to what's honestly always available either way.
  static async load(): Promise<{ player: EntityTransform }> {
    try {
      const state = await api.loadGame();
      this.applyState(state);
      return state;
    } catch (err) {
      // v0.7 — Save Architecture Redesign: the localStorage backup is now
      // the same slim ClientSaveSnapshot the server actually owns from
      // the client (see buildSnapshot() above) — agents/decisions/research/
      // everything else genuinely only exists server-side now, so there's
      // nothing dishonest to fabricate here. Applying the snapshot still
      // restores what the player actually cares about when reconnecting
      // (their own position, settings, and recent dialogue); the rest
      // repopulates for real the moment the WebSocket reconnects.
      const backup = localStorage.getItem(LOCAL_BACKUP_KEY);
      if (backup) {
        const snapshot = JSON.parse(backup) as ClientSaveSnapshot;
        this.applyClientSnapshot(snapshot);
        return snapshot;
      }
      throw err;
    }
  }

  static applyState(state: GameSaveState): void {
    NPCManager.loadAgents(state.agents);
    NexusManager.loadFromSave(state);
    TimeManager.setFromServer(state.time);
    SettingsManager.update(state.settings);
    dialogueManager.loadHistory(state.dialogueHistory);
    GameManager.getInstance()?.applyLoadedTransform(state.player);
    EventBus.emit("load:completed", state);
  }

  /** Offline-fallback counterpart to applyState() above, for when only the
   * slim localStorage backup is available (backend unreachable). Doesn't
   * touch NPCManager/NexusManager/TimeManager or emit `load:completed` —
   * there's no real agents/decisions/research data to apply from a
   * client-owned snapshot; that state repopulates for real once the
   * WebSocket connects. */
  static applyClientSnapshot(snapshot: ClientSaveSnapshot): void {
    SettingsManager.update(snapshot.settings);
    dialogueManager.loadHistory(snapshot.dialogueHistory);
    GameManager.getInstance()?.applyLoadedTransform(snapshot.player);
  }

  static startAutosave(): void {
    this.stopAutosave();
    const intervalMs = SettingsManager.current.autosaveIntervalSec * 1000;
    this.autosaveHandle = window.setInterval(() => {
      void this.save();
    }, intervalMs);
  }

  static stopAutosave(): void {
    if (this.autosaveHandle !== null) {
      window.clearInterval(this.autosaveHandle);
      this.autosaveHandle = null;
    }
  }
}
