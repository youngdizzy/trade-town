import Phaser from "phaser";
import type { Direction } from "@/types";
import { AssetLoader } from "@/game/systems/AssetLoader";

const SPEED = 90;

/**
 * Base class for any character rendered from the Player.png-style
 * directional sheet (idle/walk x 4 directions). Both PlayerController and
 * ScoutNPC extend this so direction/animation handling isn't duplicated.
 */
export class AnimatedActor {
  readonly sprite: Phaser.Physics.Arcade.Sprite;
  readonly nameTag: Phaser.GameObjects.Text;
  protected facing: Direction = "down";
  protected assetId: string;
  protected scene: Phaser.Scene;

  constructor(scene: Phaser.Scene, x: number, y: number, assetId: string, label: string) {
    this.scene = scene;
    this.assetId = assetId;
    this.sprite = scene.physics.add.sprite(x, y, assetId, 0);
    this.sprite.setSize(16, 18);
    this.sprite.setOffset(8, 12);
    this.sprite.setDepth(10);
    this.sprite.setCollideWorldBounds(true);

    this.nameTag = scene.add
      .text(x, y - 22, label, {
        fontFamily: "monospace",
        fontSize: "10px",
        color: "#f4e6c9",
        backgroundColor: "#241c14cc",
        padding: { x: 4, y: 2 },
      })
      .setOrigin(0.5, 1)
      .setDepth(20);
  }

  protected playAnim(moving: boolean): void {
    const state = moving ? "walk" : "idle";
    const key = AssetLoader.animKey(this.assetId, `${state}-${this.facing}`);
    if (this.scene.anims.exists(key) && this.sprite.anims.currentAnim?.key !== key) {
      this.sprite.play(key, true);
    }
  }

  protected setVelocityForDirection(dx: number, dy: number): void {
    this.sprite.setVelocity(dx * SPEED, dy * SPEED);
  }

  syncNameTag(): void {
    this.nameTag.setPosition(this.sprite.x, this.sprite.y - 22);
  }

  destroy(): void {
    this.sprite.destroy();
    this.nameTag.destroy();
  }

  get x(): number {
    return this.sprite.x;
  }
  get y(): number {
    return this.sprite.y;
  }
  get currentFacing(): Direction {
    return this.facing;
  }
}

export { SPEED as ACTOR_SPEED };
