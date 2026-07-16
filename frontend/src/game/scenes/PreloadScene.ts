import Phaser from "phaser";
import { AssetLoader } from "@/game/systems/AssetLoader";

/** Loads every discovered asset via AssetLoader and builds shared animations before the menu appears. */
export class PreloadScene extends Phaser.Scene {
  private progressBox!: Phaser.GameObjects.Rectangle;
  private progressBar!: Phaser.GameObjects.Rectangle;

  constructor() {
    super("PreloadScene");
  }

  preload(): void {
    const { width, height } = this.scale;
    this.cameras.main.setBackgroundColor("#0b0b12");

    this.add
      .text(width / 2, height / 2 - 40, "TradeTown", {
        fontFamily: "monospace",
        fontSize: "28px",
        color: "#d9a441",
      })
      .setOrigin(0.5);

    this.progressBox = this.add.rectangle(width / 2, height / 2 + 10, 220, 14, 0x241c14).setOrigin(0.5);
    this.progressBar = this.add.rectangle(width / 2 - 108, height / 2 + 10, 4, 10, 0x4caf6a).setOrigin(0, 0.5);

    this.load.on("progress", (value: number) => {
      this.progressBar.width = 216 * value;
    });

    AssetLoader.preloadAll(this);
  }

  create(): void {
    AssetLoader.createAnimations(this);
    this.progressBox.destroy();
    this.progressBar.destroy();
    this.scene.start("MainMenuScene");
  }
}
