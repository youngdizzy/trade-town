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

// v0.7 — Save Architecture Redesign Phase 3. A ClientSaveSnapshot is
// player/settings/dialogueHistory only — a real one measures a few KB
// (see docs/API.md's POST /api/save section). 512KB is a generous ceiling
// well above anything this shape can legitimately reach; if it's ever hit
// it means something is actually wrong (e.g. dialogue history bypassing
// its own MAX_DIALOGUE_HISTORY cap), and the honest response is a clear
// "too large" error naming the real byte count — not a chunked-upload
// protocol for a payload that's supposed to be provably small, which
// would just be more surface area for a bug to hide in.
const MAX_SAVE_BYTES = 512 * 1024;

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

  // v0.7 — Save Architecture Redesign Phase 3. Coalescing save queue: a
  // save is a full-state replacement, so queuing N identical payloads
  // behind an in-flight request is waste — at most one trailing call runs
  // after the in-flight one finishes, and it builds a *fresh* snapshot at
  // that point rather than replaying a stale one from when it was
  // requested. This is what turns "autosave fires while a manual save is
  // still in flight" (or two rapid manual-save clicks) from a race into a
  // clean sequence.
  private static inFlight: Promise<void> | null = null;
  private static trailingQueued = false;

  static buildSnapshot(): ClientSaveSnapshot {
    const game = GameManager.getInstance();
    return {
      player: game?.playerTransform ?? { scene: "LobbyScene", x: 160, y: 160, facing: "down" },
      settings: SettingsManager.current,
      dialogueHistory: dialogueManager.getHistory().slice(-MAX_DIALOGUE_HISTORY),
    };
  }

  static save(): Promise<void> {
    if (this.inFlight) {
      this.trailingQueued = true;
      return this.inFlight;
    }
    const run = this.performSave().finally(() => {
      this.inFlight = null;
      if (this.trailingQueued) {
        this.trailingQueued = false;
        void this.save();
      }
    });
    this.inFlight = run;
    return run;
  }

  private static async performSave(): Promise<void> {
    const snapshot = this.buildSnapshot();
    EventBus.emit("save:started", undefined);

    // Size-guard: the real defensive fallback in place of a chunked-upload
    // protocol (see MAX_SAVE_BYTES's own comment above) — a payload this
    // shape should never legitimately reach 512KB, so failing loudly with
    // the real byte count here surfaces a genuine bug immediately instead
    // of silently degrading into partial uploads.
    const payload = JSON.stringify(snapshot);
    const bytes = new TextEncoder().encode(payload).length;
    if (bytes > MAX_SAVE_BYTES) {
      EventBus.emit("save:failed", {
        error: `Save payload too large (${(bytes / 1024).toFixed(0)}KB, limit ${MAX_SAVE_BYTES / 1024}KB) — this indicates a real bug (e.g. dialogue history growing past its cap), not normal play.`,
      });
      return;
    }

    try {
      localStorage.setItem(LOCAL_BACKUP_KEY, payload);
      const result = await api.saveGame(snapshot);
      const failedModules = result.modules.filter((m) => !m.ok);
      if (failedModules.length > 0) {
        // v0.7 — Save Architecture Redesign Phase 3: structured, per-module
        // error reporting instead of a generic "Save Failed" — most saves
        // still succeeded (see persist_modules()'s per-module SAVEPOINT
        // isolation, backend/app/persistence.py), so this is real detail
        // about exactly what didn't, not a blanket failure.
        EventBus.emit("save:failed", {
          error: `${failedModules.length} of ${result.modules.length} save module(s) failed: ${failedModules.map((m) => `${m.name} (${m.error ?? "unknown error"})`).join(", ")}`,
        });
        return;
      }
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
