import Phaser from "phaser";
import type { Direction } from "@/types";

export interface MoveVector {
  x: number;
  y: number;
  direction: Direction | null;
  moving: boolean;
}

/**
 * Normalizes keyboard input (WASD + arrow keys) into a movement vector and
 * exposes discrete action presses (interact / pause / menu). Scenes read
 * from one InputManager instance per scene rather than touching
 * scene.input directly, so control remapping only has to change one place.
 */
export class InputManager {
  private cursors: Phaser.Types.Input.Keyboard.CursorKeys;
  private wasd: { up: Phaser.Input.Keyboard.Key; down: Phaser.Input.Keyboard.Key; left: Phaser.Input.Keyboard.Key; right: Phaser.Input.Keyboard.Key };
  private interactKey: Phaser.Input.Keyboard.Key;
  private pauseKey: Phaser.Input.Keyboard.Key;

  constructor(scene: Phaser.Scene) {
    const keyboard = scene.input.keyboard;
    if (!keyboard) {
      throw new Error("[InputManager] Keyboard plugin unavailable on this scene.");
    }
    this.cursors = keyboard.createCursorKeys();
    this.wasd = {
      up: keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.W),
      down: keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.S),
      left: keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.A),
      right: keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.D),
    };
    this.interactKey = keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.E);
    this.pauseKey = keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.ESC);
  }

  getMoveVector(): MoveVector {
    const left = this.cursors.left?.isDown || this.wasd.left.isDown;
    const right = this.cursors.right?.isDown || this.wasd.right.isDown;
    const up = this.cursors.up?.isDown || this.wasd.up.isDown;
    const down = this.cursors.down?.isDown || this.wasd.down.isDown;

    let x = 0;
    let y = 0;
    if (left) x -= 1;
    if (right) x += 1;
    if (up) y -= 1;
    if (down) y += 1;

    let direction: Direction | null = null;
    if (y < 0) direction = "up";
    else if (y > 0) direction = "down";
    else if (x < 0) direction = "left";
    else if (x > 0) direction = "right";

    const moving = x !== 0 || y !== 0;
    if (moving && x !== 0 && y !== 0) {
      // Diagonal movement normalized; facing prioritizes vertical for sprite readability.
      const len = Math.sqrt(2);
      x /= len;
      y /= len;
    }

    return { x, y, direction, moving };
  }

  get interactJustPressed(): boolean {
    return Phaser.Input.Keyboard.JustDown(this.interactKey);
  }

  get pauseJustPressed(): boolean {
    return Phaser.Input.Keyboard.JustDown(this.pauseKey);
  }
}
