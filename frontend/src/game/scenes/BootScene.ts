import Phaser from "phaser";

/** First scene to run. Kept intentionally empty — reserved for very early config (renderer flags, etc.) before assets load. */
export class BootScene extends Phaser.Scene {
  constructor() {
    super("BootScene");
  }

  create(): void {
    this.scene.start("PreloadScene");
  }
}
