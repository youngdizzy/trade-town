import Phaser from "phaser";
import type { EntityTransform, SceneId } from "@/types";
import { BootScene } from "@/game/scenes/BootScene";
import { PreloadScene } from "@/game/scenes/PreloadScene";
import { MainMenuScene } from "@/game/scenes/MainMenuScene";
import { LobbyScene } from "@/game/scenes/LobbyScene";
import { ScoutOfficeScene } from "@/game/scenes/ScoutOfficeScene";
import { CeoOfficeScene } from "@/game/scenes/CeoOfficeScene";
import { BrainRoomScene } from "@/game/scenes/BrainRoomScene";
import { MeetingRoomScene } from "@/game/scenes/MeetingRoomScene";
import { BreakRoomScene } from "@/game/scenes/BreakRoomScene";
import { SimulationLabScene } from "@/game/scenes/SimulationLabScene";
import { HallOfFameScene } from "@/game/scenes/HallOfFameScene";
import { PerformanceCenterScene } from "@/game/scenes/PerformanceCenterScene";
import { TradingFloorScene } from "@/game/scenes/TradingFloorScene";
import { EventBus } from "./EventBus";

const DEFAULT_PLAYER_TRANSFORM: EntityTransform = {
  scene: "LobbyScene",
  x: 160,
  y: 160,
  facing: "down",
};

/**
 * Top-level orchestrator. Owns the single Phaser.Game instance and the
 * cross-scene player transform (scenes are torn down/recreated on
 * transition, so anything that must survive a scene switch — like "where
 * is the player" for save serialization — lives here instead).
 */
export class GameManager {
  private static instance: GameManager | null = null;

  readonly game: Phaser.Game;
  playerTransform: EntityTransform = { ...DEFAULT_PLAYER_TRANSFORM };
  paused = false;

  private constructor(parent: HTMLElement) {
    this.game = new Phaser.Game({
      type: Phaser.AUTO,
      parent,
      backgroundColor: "#0b0b12",
      pixelArt: true,
      physics: {
        default: "arcade",
        arcade: { gravity: { x: 0, y: 0 }, debug: false },
      },
      scale: {
        mode: Phaser.Scale.RESIZE,
        autoCenter: Phaser.Scale.CENTER_BOTH,
        width: "100%",
        height: "100%",
      },
      scene: [
        BootScene,
        PreloadScene,
        MainMenuScene,
        LobbyScene,
        ScoutOfficeScene,
        CeoOfficeScene,
        BrainRoomScene,
        MeetingRoomScene,
        BreakRoomScene,
        SimulationLabScene,
        HallOfFameScene,
        PerformanceCenterScene,
        TradingFloorScene,
      ],
    });
  }

  static bootstrap(parent: HTMLElement): GameManager {
    if (this.instance) return this.instance;
    this.instance = new GameManager(parent);
    return this.instance;
  }

  static getInstance(): GameManager | null {
    return this.instance;
  }

  static destroy(): void {
    this.instance?.game.destroy(true);
    this.instance = null;
  }

  setPlayerTransform(transform: EntityTransform): void {
    this.playerTransform = transform;
  }

  applyLoadedTransform(transform: EntityTransform): void {
    this.playerTransform = transform;
    const scene = this.game.scene.getScene(transform.scene as SceneId);
    if (scene) {
      EventBus.emit("scene:transition", { to: transform.scene });
      this.game.scene.start(transform.scene, { spawnX: transform.x, spawnY: transform.y });
    }
  }

  togglePause(): void {
    this.paused = !this.paused;
    const active = this.game.scene.getScenes(true);
    for (const scene of active) {
      if (this.paused) scene.scene.pause();
      else scene.scene.resume();
    }
    EventBus.emit("ui:pause", { paused: this.paused });
  }
}
