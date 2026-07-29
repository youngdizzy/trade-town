import Phaser from "phaser";
import type { Direction } from "@/types";
import { isTypingInTextField } from "./inputFocus";

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
// v0.7 — Input Priority fix. Phaser's addKey()/createCursorKeys() default
// to enableCapture=true, which calls the native event's preventDefault()
// on keydown for every key in this list *regardless of DOM focus* — a
// separate, lower-level mechanism from GameManager.movementActive's own
// isTypingInTextField() check (which only gates whether this game's own
// code reads the key, not whether the browser's default text-input
// behavior happens at all). Without also toggling capture here, a
// focused Command Center text field would still have every keystroke it
// receives silently swallowed before a single character ever reaches the
// input's value. See `syncCaptureWithFocus()` below.
const CAPTURED_KEYS = "W,A,S,D,UP,DOWN,LEFT,RIGHT,E,ESC";

export class InputManager {
  private keyboard: Phaser.Input.Keyboard.KeyboardPlugin;
  private cursors: Phaser.Types.Input.Keyboard.CursorKeys;
  private wasd: { up: Phaser.Input.Keyboard.Key; down: Phaser.Input.Keyboard.Key; left: Phaser.Input.Keyboard.Key; right: Phaser.Input.Keyboard.Key };
  private interactKey: Phaser.Input.Keyboard.Key;
  private pauseKey: Phaser.Input.Keyboard.Key;
  private capturing = true;

  constructor(scene: Phaser.Scene) {
    const keyboard = scene.input.keyboard;
    if (!keyboard) {
      throw new Error("[InputManager] Keyboard plugin unavailable on this scene.");
    }
    this.keyboard = keyboard;
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

  /** Call every frame (see PlayerController.update()). Releases capture
   * on WASD/arrows/E/ESC the instant a real text field gains focus, so
   * typing works exactly as it would on any other web page, and restores
   * it the instant focus leaves — this is independent of, and layered
   * underneath, GameManager.movementActive's own "don't move the player
   * while typing" check above it. */
  syncCaptureWithFocus(): void {
    const shouldCapture = !isTypingInTextField();
    if (shouldCapture === this.capturing) return;
    this.capturing = shouldCapture;
    if (shouldCapture) this.keyboard.addCapture(CAPTURED_KEYS);
    else this.keyboard.removeCapture(CAPTURED_KEYS);
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
