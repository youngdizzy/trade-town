import Phaser from "phaser";
import { CameraManager } from "@/game/systems/CameraManager";
import { EventBus } from "@/game/systems/EventBus";
import { SaveManager } from "@/game/systems/SaveManager";

/** Title screen: New Game, Continue, Settings. */
export class MainMenuScene extends Phaser.Scene {
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

  private startNewGame(): void {
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
