import Phaser from "phaser";
import { CameraManager } from "@/game/systems/CameraManager";
import { EventBus } from "@/game/systems/EventBus";
import { SaveManager } from "@/game/systems/SaveManager";
import { api } from "@/net/api";

/** Title screen: New Game, Continue, Settings. */
export class MainMenuScene extends Phaser.Scene {
  // Guards the ENTIRE New Game round trip (save check -> optional
  // confirmation dialog -> player's choice), not just the initial async
  // check, so rapid/repeat clicks on "New Game" while a check or dialog
  // is already in flight are a genuine no-op rather than stacking a
  // second check or a second dialog.
  private newGameFlowActive = false;

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
    this.makeButton(width / 2, height * 0.5 + 44, "Continue", () => void this.continueGame());
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
   * for exactly what this can and can't honestly claim about resetting
   * the backend save). Checks for real existing progress first; only
   * shows the confirmation dialog when there's genuinely something to
   * protect. */
  private startNewGame(): void {
    if (this.newGameFlowActive) return;
    this.newGameFlowActive = true;
    void this.runNewGameFlow().finally(() => {
      this.newGameFlowActive = false;
    });
  }

  private async runNewGameFlow(): Promise<void> {
    const existingDay = await this.existingProgressDay();
    if (existingDay === null) {
      this.beginNewGame();
      return;
    }
    const confirmed = await new Promise<boolean>((resolve) => {
      EventBus.once("ui:newGameConfirmResult", ({ confirmed }) => resolve(confirmed));
      EventBus.emit("ui:newGameConfirm", { day: existingDay });
    });
    if (confirmed) this.beginNewGame();
    // Cancelled: do nothing at all — no scene change, no API call, no
    // save mutation of any kind.
  }

  /** Real day of any existing save, or null when there's no save (fresh
   * deployment / backend unreachable) or the save is still genuinely
   * Day 1 (nothing to protect yet) — either way the normal New Game flow
   * should proceed without a confirmation. Reuses the exact same
   * GET /api/load call continueGame() below already makes. */
  private async existingProgressDay(): Promise<number | null> {
    try {
      const state = await api.loadGame();
      return state.time.day > 1 ? state.time.day : null;
    } catch {
      return null;
    }
  }

  private beginNewGame(): void {
    CameraManager.fadeOutThen(this, 250, () => {
      this.scene.start("LobbyScene", { spawnX: 160, spawnY: 200 });
    });
  }

  private async continueGame(): Promise<void> {
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
}
