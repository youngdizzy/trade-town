import Phaser from "phaser";
import type { SceneId } from "@/types";
import { CameraManager } from "./CameraManager";
import { EventBus } from "./EventBus";

export interface SceneTransitionData {
  /** Omit to let the target scene fall back to its own default spawn point (e.g. next to its exit door). */
  spawnX?: number;
  spawnY?: number;
  fromScene?: SceneId;
}

/** Handles cross-scene transitions with a consistent fade + spawn-point handoff. */
export class SceneManager {
  static goTo(scene: Phaser.Scene, target: SceneId, data: SceneTransitionData): void {
    EventBus.emit("scene:transition", { to: target });
    CameraManager.fadeOutThen(scene, 250, () => {
      scene.scene.start(target, data);
    });
  }
}
