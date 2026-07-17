import Phaser from "phaser";
import { AnimatedActor } from "./AnimatedActor";
import { InputManager } from "@/game/systems/InputManager";
import { EventBus } from "@/game/systems/EventBus";
import type { Direction } from "@/types";

/** The player-controlled CEO character: smooth WASD/arrow movement, camera target, save-position source. */
export class PlayerController extends AnimatedActor {
  private input: InputManager;

  constructor(scene: Phaser.Scene, x: number, y: number, facing: Direction = "down") {
    super(scene, x, y, "player/player", "You");
    this.facing = facing;
    this.input = new InputManager(scene);
    this.playAnim(false);
  }

  update(): void {
    const move = this.input.getMoveVector();
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
