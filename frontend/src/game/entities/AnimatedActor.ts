import Phaser from "phaser";
import type { Direction } from "@/types";
import { AssetLoader } from "@/game/systems/AssetLoader";

const SPEED = 90;

/**
 * Target on-screen gap (in pixels) between a character and its name tag.
 * Rooms use very different camera zoom levels (see CameraManager's
 * cover-fit zoom — a small room can need 2-3x the base zoom to fill the
 * viewport), so a fixed *world-space* offset would look fine in one room
 * and wildly detached in another. Dividing by the current zoom keeps the
 * gap visually consistent everywhere.
 */
const NAME_TAG_SCREEN_GAP_PX = 55;

/** Converts a desired on-screen pixel gap into the world-space offset that produces it at the scene's current camera zoom. */
export function screenGapToWorld(scene: Phaser.Scene, screenPx: number): number {
  return screenPx / scene.cameras.main.zoom;
}

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
      .text(x, y - screenGapToWorld(scene, NAME_TAG_SCREEN_GAP_PX), label, {
        fontFamily: "monospace",
        fontSize: "10px",
        color: "#f4e6c9",
        backgroundColor: "#241c14cc",
        padding: { x: 4, y: 2 },
        resolution: 4,
      })
      .setOrigin(0.5, 1)
      .setDepth(20);
  }

  /**
   * This sheet has no dedicated right-facing row (see animation-config.json)
   * — right movement reuses the left-facing animation with the sprite
   * mirrored horizontally, which is the standard Phaser approach for
   * asset packs that only ship one side direction.
   */
  protected playAnim(moving: boolean): void {
    const state = moving ? "walk" : "idle";
    const animFacing = this.facing === "right" ? "left" : this.facing;
    this.sprite.setFlipX(this.facing === "right");
    const key = AssetLoader.animKey(this.assetId, `${state}-${animFacing}`);
    if (this.scene.anims.exists(key) && this.sprite.anims.currentAnim?.key !== key) {
      this.sprite.play(key, true);
    }
  }

  protected setVelocityForDirection(dx: number, dy: number): void {
    // Live end-to-end QA pass (2026-08-26) found a real, reproducible
    // crash: Phaser's own GameObject.destroy() sets a sprite's `body` to
    // undefined (not null), so a call landing here on an already-
    // destroyed actor (root-caused to GameManager.applyLoadedTransform's
    // double scene-start race — see its own comment) threw
    // "Cannot read properties of undefined (reading 'setVelocity')" and
    // permanently wedged that scene's update() loop, since the throw
    // pre-empted the code that would otherwise clean up the stale entry.
    // This guard makes an already-destroyed actor's per-frame update a
    // harmless no-op instead, independent of whatever upstream state
    // led to it still being ticked.
    if (!this.sprite.body) return;
    this.sprite.setVelocity(dx * SPEED, dy * SPEED);
  }

  syncNameTag(): void {
    const gap = screenGapToWorld(this.scene, NAME_TAG_SCREEN_GAP_PX);
    this.nameTag.setPosition(this.sprite.x, this.sprite.y - gap);
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
