import Phaser from "phaser";
import { AnimatedActor } from "./AnimatedActor";
import { InputManager } from "@/game/systems/InputManager";
import { EventBus } from "@/game/systems/EventBus";
import { GameManager } from "@/game/systems/GameManager";
import type { Direction } from "@/types";

/** The player-controlled CEO character: smooth WASD/arrow movement, camera target, save-position source. */
export class PlayerController extends AnimatedActor {
  private input: InputManager;

  constructor(scene: Phaser.Scene, x: number, y: number, facing: Direction = "down") {
    super(scene, x, y, "characters/player/player", "You");
    this.facing = facing;
    this.input = new InputManager(scene);
    this.playAnim(false);
  }

  update(): void {
    // v0.7 — Input Priority fix: releases Phaser's own keydown capture on
    // WASD/arrows/E/ESC the instant a real text field has focus — without
    // this, movementActive alone only stops the game from *reading* the
    // key, not Phaser's lower-level preventDefault() on it, which would
    // otherwise still swallow every keystroke before it reaches the
    // field. See InputManager.syncCaptureWithFocus()'s own comment.
    this.input.syncCaptureWithFocus();

    // v0.7 — Input Priority fix: movement has its own gate, separate from
    // worldActive (interaction) — see GameManager.movementActive's own
    // comment for why.
    const movementActive = GameManager.getInstance()?.movementActive ?? true;
    const move = movementActive
      ? this.input.getMoveVector()
      : { x: 0, y: 0, direction: null, moving: false };
    this.setVelocityForDirection(move.x, move.y);
    if (move.direction) this.facing = move.direction;
    this.playAnim(move.moving);
    this.syncNameTag();
    this.nameTag.setVisible(false); // Player doesn't need a floating "You" label during normal play.

    if (move.moving) {
      EventBus.emit("player:move", { x: this.sprite.x, y: this.sprite.y });
    }
  }

  get interactPressed(): boolean {
    return this.input.interactJustPressed;
  }

  get pausePressed(): boolean {
    return this.input.pauseJustPressed;
  }
}
