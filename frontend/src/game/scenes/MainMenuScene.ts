import Phaser from "phaser";
import { CameraManager } from "@/game/systems/CameraManager";
import { EventBus } from "@/game/systems/EventBus";
import { SaveManager } from "@/game/systems/SaveManager";
import { api } from "@/net/api";
import type { GameSaveState, RunSummary } from "@/types";

/** Title screen: New Game, Continue, Settings.
 *
 * CEO directive "Proper Multi-Run / Save Isolation System" — New Game
 * now genuinely creates a separate, independently-persisted run
 * (POST /api/runs) rather than the earlier purely-cosmetic scene
 * transition, and Continue picks from every real, persisted run when
 * more than one exists (see RunPicker.tsx) rather than always loading
 * the single global save. */
export class MainMenuScene extends Phaser.Scene {
  // Guards the ENTIRE New Game round trip (run listing -> optional
  // confirmation dialog -> player's choice -> run creation), not just
  // the initial async check, so rapid/repeat clicks on "New Game" while
  // a check or dialog is already in flight are a genuine no-op rather
  // than stacking a second check, dialog, or run.
  private newGameFlowActive = false;
  // Same guard for Continue, covering run listing -> optional picker ->
  // activation.
  private continueFlowActive = false;

  constructor() {
    super("MainMenuScene");
  }

  create(): void {
    const { width, height } = this.scale;
    this.cameras.main.setZoom(1);
    CameraManager.fadeIn(this);

    this.add.image(width / 2, height * 0.32, "props/house-1-wood-base-blue").setScale(3).setAlpha(0.35);

    this.add
      .text(width / 2, height * 0.28, "TradeTown", {
        fontFamily: "monospace",
        fontSize: "42px",
        color: "#d9a441",
      })
      .setOrigin(0.5)
      .setShadow(3, 3, "#241c14", 0, false, true);

    this.add
      .text(width / 2, height * 0.28 + 42, "an AI investment company simulation", {
        fontFamily: "monospace",
        fontSize: "12px",
        color: "#f4e6c9",
      })
      .setOrigin(0.5);

    this.makeButton(width / 2, height * 0.5, "New Game", () => this.startNewGame());
    this.makeButton(width / 2, height * 0.5 + 44, "Continue", () => this.startContinue());
    this.makeButton(width / 2, height * 0.5 + 88, "Settings", () => EventBus.emit("ui:settings", { open: true }));

    EventBus.emit("scene:ready", { scene: "MainMenuScene" });
  }

  private makeButton(x: number, y: number, label: string, onClick: () => void): void {
    const text = this.add
      .text(x, y, label, {
        fontFamily: "monospace",
        fontSize: "16px",
        color: "#f4e6c9",
        backgroundColor: "#2b2118",
        padding: { x: 18, y: 8 },
      })
      .setOrigin(0.5)
      .setInteractive({ useHandCursor: true });

    text.on("pointerover", () => text.setColor("#d9a441"));
    text.on("pointerout", () => text.setColor("#f4e6c9"));
    text.on("pointerdown", onClick);
  }

  /** Safe "New Game" entry point (see NewGameConfirm.tsx's own docstring
   * for exactly what this creates and why the current run is never at
   * risk). Checks the currently active run's real day first; only shows
   * the confirmation dialog when there's genuinely a run worth naming. */
  private startNewGame(): void {
    if (this.newGameFlowActive) return;
    this.newGameFlowActive = true;
    void this.runNewGameFlow().finally(() => {
      this.newGameFlowActive = false;
    });
  }

  private async runNewGameFlow(): Promise<void> {
    const activeDay = await this.activeRunDayWorthProtecting();
    if (activeDay === null) {
      await this.createAndEnterNewRun();
      return;
    }
    const confirmed = await new Promise<boolean>((resolve) => {
      EventBus.once("ui:newGameConfirmResult", ({ confirmed }) => resolve(confirmed));
      EventBus.emit("ui:newGameConfirm", { day: activeDay });
    });
    if (confirmed) await this.createAndEnterNewRun();
    // Cancelled: do nothing at all — no scene change, no API call, no
    // run created, no mutation of any kind.
  }

  /** The currently active run's real day, or null when there's no real
   * run to protect yet (a fresh deployment with nothing registered, the
   * backend unreachable, or the active run is still genuinely Day 1) —
   * any of those should proceed straight through without a confirmation. */
  private async activeRunDayWorthProtecting(): Promise<number | null> {
    try {
      const active = await api.getActiveRun();
      return active && active.currentDay !== null && active.currentDay > 1 ? active.currentDay : null;
    } catch {
      return null;
    }
  }

  private async createAndEnterNewRun(): Promise<void> {
    const state = await api.createRun();
    this.applyStateAndTransition(state);
  }

  /** Safe "Continue" entry point. Lists every real, persisted run:
   * none -> falls through to New Game's own creation flow (the honest
   * "no save exists" case); exactly one -> loads it directly, the same
   * minimal-friction behavior Continue always had; more than one ->
   * shows RunPicker and waits for the player's real choice. A listing
   * failure (backend genuinely unreachable) falls back to the pre-
   * existing SaveManager offline-localStorage-backed path rather than
   * losing that resilience. */
  private startContinue(): void {
    if (this.continueFlowActive) return;
    this.continueFlowActive = true;
    void this.runContinueFlow().finally(() => {
      this.continueFlowActive = false;
    });
  }

  private async runContinueFlow(): Promise<void> {
    let runs: RunSummary[];
    try {
      runs = await api.listRuns();
    } catch {
      await this.continueViaLegacySaveManager();
      return;
    }

    if (runs.length === 0) {
      await this.createAndEnterNewRun();
      return;
    }

    const [onlyRun] = runs;
    if (runs.length === 1 && onlyRun) {
      const state = await api.activateRun(onlyRun.runId);
      this.applyStateAndTransition(state);
      return;
    }

    const runId = await new Promise<string | null>((resolve) => {
      EventBus.once("ui:runPickerResult", ({ runId }) => resolve(runId));
      EventBus.emit("ui:runPicker", { runs });
    });
    if (runId === null) return; // player closed the picker without choosing -- stay on the title screen
    const state = await api.activateRun(runId);
    this.applyStateAndTransition(state);
  }

  /** Pre-existing Continue behavior, kept as the fallback for a genuinely
   * unreachable backend (SaveManager.load() has its own offline
   * localStorage-backed recovery this new flow can't replicate without
   * first knowing which/how-many runs exist, which requires the network
   * round trip that just failed). */
  private async continueViaLegacySaveManager(): Promise<void> {
    try {
      const state = await SaveManager.load();
      CameraManager.fadeOutThen(this, 250, () => {
        this.scene.start(state.player.scene, { spawnX: state.player.x, spawnY: state.player.y });
      });
    } catch {
      // No save yet (fresh deployment) — fall back to a new game instead of stalling on the menu.
      this.startNewGame();
    }
  }

  private applyStateAndTransition(state: GameSaveState): void {
    SaveManager.applyState(state);
    CameraManager.fadeOutThen(this, 250, () => {
      this.scene.start(state.player.scene, { spawnX: state.player.x, spawnY: state.player.y });
    });
  }
}
