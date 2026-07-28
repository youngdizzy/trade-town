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
import { MarketObservatoryScene } from "@/game/scenes/MarketObservatoryScene";
import { ExecutiveBoardroomScene } from "@/game/scenes/ExecutiveBoardroomScene";
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
  private overlayOpen = false;

  private constructor(parent: HTMLElement) {
    // Full-screen React overlays (Newspaper, Company Memory, Coach
    // Dashboard) draw over the whole canvas but don't otherwise touch the
    // running scene — without this, the player keeps moving (invisibly,
    // since the overlay hides the world) while one is open, and since
    // none of them have a keyboard close (mouse-only "Close" button),
    // that reads as the game being stuck. `worldActive` below is
    // independent of `paused`/`ui:pause` (the ESC pause menu) so opening
    // the newspaper doesn't also pop up the Pause Menu.
    EventBus.on("world:overlayOpen", ({ open }) => {
      this.overlayOpen = open;
      if (this.worldActive) this.resetSceneKeys();
    });

    // Closing a dialogue with "E" (DialogueBox's own window keydown handler,
    // same pattern as the overlays above) races the *same* keypress against
    // Phaser's interact key on the scene: DialogueBox advances/closes first,
    // but the scene's own key still reads as freshly "just pressed" on its
    // next update() — without a reset, that stray press immediately re-opens
    // a new conversation with whichever agent is nearest (or, if the player
    // happens to be by the door, exits the room), which reads as the game
    // refusing to let you stop talking to an NPC.
    EventBus.on("dialogue:close", () => this.resetSceneKeys());

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
        MarketObservatoryScene,
        ExecutiveBoardroomScene,
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
    if (this.worldActive) this.resetSceneKeys();
    EventBus.emit("ui:pause", { paused: this.paused });
  }

  /**
   * Whether gameplay scenes should process movement/interaction this
   * frame — false while the ESC pause menu or any full-screen overlay
   * (Newspaper, Company Memory, Coach Dashboard) is open. LobbyScene and
   * RoomScene both check this at the top of `update()` and bail out
   * early rather than this class calling Phaser's own `scene.pause()` /
   * `.resume()`: those are QUEUED operations (applied on the SceneManager's
   * *next* update, not immediately — see ScenePlugin.pause()'s own
   * doc comment), and the original pause-menu code called
   * `game.scene.getScenes(true)` to find the scene to resume — `getScenes`'s
   * `isActive` filter means "status === RUNNING", which a just-paused scene
   * no longer satisfies, so that loop always iterated zero scenes and the
   * scene never actually resumed via ESC. This flag-based approach doesn't
   * depend on Phaser's scene-state machine at all, so it can't have that
   * class of bug.
   */
  get worldActive(): boolean {
    return !this.paused && !this.overlayOpen;
  }

  /**
   * Phaser's Key.JustDown flag is set by the raw browser keydown
   * regardless of whether anything is reading it, and only clears the
   * first time something calls JustDown() on it — which the gameplay
   * scenes don't do while worldActive is false (see above). Without this,
   * closing an overlay with Escape would leave the scene's own ESC key
   * "still just-pressed" the instant the world reactivates, immediately
   * re-triggering the pause menu; held movement keys have the same issue.
   */
  private resetSceneKeys(): void {
    this.game.scene.getScene(this.playerTransform.scene as SceneId)?.input.keyboard?.resetKeys();
  }
}
