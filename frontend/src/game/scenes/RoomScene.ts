import Phaser from "phaser";
import type { ScoutLocation, SceneId } from "@/types";
import { PlayerController } from "@/game/entities/PlayerController";
import { ScoutNPC } from "@/game/entities/ScoutNPC";
import { CameraManager } from "@/game/systems/CameraManager";
import { SceneManager, type SceneTransitionData } from "@/game/systems/SceneManager";
import { createGroundLayer, createPerimeterWalls, createZone } from "@/game/systems/TileWorld";
import { EventBus } from "@/game/systems/EventBus";
import { GameManager } from "@/game/systems/GameManager";
import { NPCManager } from "@/game/systems/NPCManager";
import { dialogueManager } from "@/game/systems/DialogueManager";

const TILE_SIZE = 16;

/**
 * Shared base for every enterable interior room (Scout Office, CEO Office,
 * Brain Room). Handles the floor, perimeter walls, player spawn, camera,
 * pause key, the door back to the Lobby, and Scout's presence/dialogue —
 * subclasses only declare their layout constants and add flavor via the
 * onBuild/onUpdate hooks.
 */
export abstract class RoomScene extends Phaser.Scene {
  protected abstract sceneKey: SceneId;
  protected abstract widthTiles: number;
  protected abstract heightTiles: number;
  protected abstract floorAsset: string;
  protected abstract roomLabel: string;
  /** Which schedule location this room represents, or null if Scout never appears here. */
  protected abstract scoutLocation: ScoutLocation | null;

  protected player!: PlayerController;
  protected doorZone!: Phaser.GameObjects.Zone;
  protected walls!: Phaser.Physics.Arcade.StaticGroup;
  protected scout: ScoutNPC | null = null;
  private widthPx = 0;
  private heightPx = 0;

  create(data: SceneTransitionData): void {
    this.widthPx = this.widthTiles * TILE_SIZE;
    this.heightPx = this.heightTiles * TILE_SIZE;

    createGroundLayer(this, {
      tileAssetId: this.floorAsset,
      tileSize: TILE_SIZE,
      widthTiles: this.widthTiles,
      heightTiles: this.heightTiles,
    });

    this.walls = createPerimeterWalls(this, this.widthPx, this.heightPx, TILE_SIZE);

    const spawnX = data?.spawnX ?? this.widthPx / 2;
    const spawnY = data?.spawnY ?? this.heightPx - TILE_SIZE * 2;
    this.player = new PlayerController(this, spawnX, spawnY);
    this.physics.add.collider(this.player.sprite, this.walls);

    this.doorZone = createZone(this, this.widthPx / 2, this.heightPx - TILE_SIZE / 2, TILE_SIZE * 2, TILE_SIZE);
    this.add
      .text(this.widthPx / 2, this.heightPx - TILE_SIZE * 1.5, "Exit", {
        fontFamily: "monospace",
        fontSize: "8px",
        color: "#f4e6c9",
      })
      .setOrigin(0.5);

    // Screen-space (not world-space) so it stays visible even in small rooms
    // where the "cover" zoom (see CameraManager) lets the camera scroll
    // beyond the room's own height — a world-anchored label at the top of
    // the room would otherwise scroll out of view whenever the player is
    // near the bottom of a room shorter than the viewport.
    this.add
      .text(this.cameras.main.width / 2, 10, this.roomLabel, {
        fontFamily: "monospace",
        fontSize: "10px",
        color: "#d9a441",
        backgroundColor: "#241c14aa",
        padding: { x: 6, y: 2 },
      })
      .setOrigin(0.5, 0)
      .setScrollFactor(0)
      .setDepth(30);

    CameraManager.follow(this, this.player.sprite, { x: 0, y: 0, width: this.widthPx, height: this.heightPx });
    CameraManager.fadeIn(this);

    GameManager.getInstance()?.setPlayerTransform({
      scene: this.sceneKey,
      x: spawnX,
      y: spawnY,
      facing: "down",
    });

    this.refreshScoutPresence();
    this.onBuild(this.widthPx, this.heightPx);
    EventBus.emit("scene:ready", { scene: this.sceneKey });
  }

  update(): void {
    this.player.update();
    this.scout?.update();

    GameManager.getInstance()?.setPlayerTransform({
      scene: this.sceneKey,
      x: this.player.x,
      y: this.player.y,
      facing: this.player.currentFacing,
    });

    if (this.player.pausePressed) {
      GameManager.getInstance()?.togglePause();
    }

    if (this.scout && this.player.interactPressed && this.scout.isNear(this.player.x, this.player.y)) {
      const session = dialogueManager.startScoutConversation(NPCManager.getScout());
      this.scout.showSpeechBubble(session.lines[0] ?? "...");
    }

    this.refreshScoutPresence();

    const nearDoor = Phaser.Geom.Intersects.RectangleToRectangle(
      this.player.sprite.getBounds(),
      this.doorZone.getBounds(),
    );
    if (nearDoor && this.player.interactPressed) {
      SceneManager.goTo(this, "LobbyScene", {
        spawnX: this.registry.get("lobbyReturnX") ?? 160,
        spawnY: this.registry.get("lobbyReturnY") ?? 220,
        fromScene: this.sceneKey,
      });
      return;
    }

    this.onUpdate();
  }

  shutdown(): void {
    this.scout?.destroy();
    this.scout = null;
  }

  /** Spawns/despawns Scout to match his server-driven schedule location. */
  private refreshScoutPresence(): void {
    if (!this.scoutLocation) return;
    const shouldBePresent = NPCManager.getScout().location === this.scoutLocation;
    if (shouldBePresent && !this.scout) {
      const spawn = this.getScoutSpawnPoint(this.widthPx, this.heightPx);
      this.scout = new ScoutNPC(this, spawn.x, spawn.y);
      this.physics.add.collider(this.player.sprite, this.scout.sprite);
    } else if (!shouldBePresent && this.scout) {
      this.scout.destroy();
      this.scout = null;
    }
  }

  /** Override to customize where Scout spawns in a given room. Defaults to room center. */
  protected getScoutSpawnPoint(widthPx: number, heightPx: number): { x: number; y: number } {
    return { x: widthPx / 2, y: heightPx / 2 - 10 };
  }

  /** Hook for subclasses to add props, decoration, etc. after the base room is built. */
  protected onBuild(_widthPx: number, _heightPx: number): void {}

  /** Hook for subclasses to run per-frame logic beyond the shared player/scout/door handling. */
  protected onUpdate(): void {}
}
