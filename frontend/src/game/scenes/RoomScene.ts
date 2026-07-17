import Phaser from "phaser";
import type { AgentId, AgentLocation, SceneId } from "@/types";
import { AGENT_IDS } from "@/types";
import { PlayerController } from "@/game/entities/PlayerController";
import { AgentNPC } from "@/game/entities/AgentNPC";
import { Whiteboard } from "@/game/entities/Whiteboard";
import { CameraManager } from "@/game/systems/CameraManager";
import { SceneManager, type SceneTransitionData } from "@/game/systems/SceneManager";
import { createGroundLayer, createPerimeterWalls, createZone } from "@/game/systems/TileWorld";
import { EventBus } from "@/game/systems/EventBus";
import { GameManager } from "@/game/systems/GameManager";
import { NPCManager } from "@/game/systems/NPCManager";
import { dialogueManager } from "@/game/systems/DialogueManager";
import { gameStore } from "@/state/gameStore";

const TILE_SIZE = 16;

/**
 * How close the player must be to an agent before its name tag shows.
 * Only the single *nearest* agent within this radius ever shows a tag (see
 * the tag-visibility block in `update()`) — rooms like Brain Room can
 * legitimately hold all four agents clustered together, and two agents
 * that are near each other (not just near the player) would otherwise
 * both light up their tags and produce overlapping, unreadable text.
 */
const NAME_TAG_RADIUS = 36;

/**
 * Shared base for every enterable interior room (Scout Office, CEO Office,
 * Brain Room, Meeting Room, Break Room). Handles the floor, perimeter
 * walls, player spawn, camera, pause key, the door back to the Lobby, and
 * agent presence/dialogue for however many agents call this room home —
 * subclasses only declare their layout constants and add flavor via the
 * onBuild/onUpdate hooks.
 */
export abstract class RoomScene extends Phaser.Scene {
  protected abstract sceneKey: SceneId;
  protected abstract widthTiles: number;
  protected abstract heightTiles: number;
  protected abstract floorAsset: string;
  protected abstract roomLabel: string;
  /** Which location this room represents; any agent currently at this location is spawned here. Null if agents never appear here. */
  protected abstract agentLocation: AgentLocation | null;

  protected player!: PlayerController;
  protected doorZone!: Phaser.GameObjects.Zone;
  protected walls!: Phaser.Physics.Arcade.StaticGroup;
  protected agents = new Map<AgentId, AgentNPC>();
  private whiteboards: Whiteboard[] = [];
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

    this.refreshAgentPresence();
    this.onBuild(this.widthPx, this.heightPx);
    EventBus.emit("scene:ready", { scene: this.sceneKey });
    EventBus.emit("room:entered", { scene: this.sceneKey });
  }

  update(): void {
    this.player.update();
    for (const agent of this.agents.values()) agent.update();

    const nearestForTag = this.nearestAgent(NAME_TAG_RADIUS);
    for (const agent of this.agents.values()) {
      agent.nameTag.setVisible(agent === nearestForTag);
    }

    GameManager.getInstance()?.setPlayerTransform({
      scene: this.sceneKey,
      x: this.player.x,
      y: this.player.y,
      facing: this.player.currentFacing,
    });

    if (this.player.pausePressed) {
      GameManager.getInstance()?.togglePause();
    }

    // Phaser's JustDown() consumes the "just pressed" state on read, so it
    // must be read exactly once per frame — read it into a local here
    // rather than calling the interactPressed getter again below, or the
    // second call would always see it as already-consumed and never fire.
    // DialogueBox also listens for E on the window to advance/close an open
    // conversation, independently of this Phaser key — while a dialogue is
    // showing, this scene must ignore E entirely so the same press can't
    // simultaneously start a new conversation or leave the room out from
    // under an open dialogue box.
    const dialogueOpen = gameStore.getSnapshot().dialogue.open;
    const interacted = this.player.interactPressed && !dialogueOpen;

    const nearDoor = Phaser.Geom.Intersects.RectangleToRectangle(
      this.player.sprite.getBounds(),
      this.doorZone.getBounds(),
    );

    // Mutually exclusive: if the player is close enough to overlap both the
    // door zone and an agent's interact radius at once (rooms are small),
    // exiting takes priority. Firing both off the same press would open a
    // dialogue in the very frame the scene tears down, leaving a React
    // dialogue box stuck on screen with nothing left to close it.
    if (interacted && !nearDoor) {
      const nearest = this.nearestAgent();
      if (nearest) {
        dialogueManager.startConversation(nearest.agentId, NPCManager.getAgent(nearest.agentId));
      }
    }

    this.refreshAgentPresence();

    if (nearDoor && interacted) {
      EventBus.emit("room:left", { scene: this.sceneKey });
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
    for (const agent of this.agents.values()) agent.destroy();
    this.agents.clear();
    for (const board of this.whiteboards) board.destroy();
    this.whiteboards = [];
  }

  /** Adds a whiteboard prop and registers it for automatic cleanup on shutdown — subclasses don't need their own shutdown() override just to destroy one. */
  protected addWhiteboard(x: number, y: number, boardId: string): void {
    this.whiteboards.push(new Whiteboard(this, x, y, boardId));
  }

  private nearestAgent(radius = 28): AgentNPC | null {
    let closest: AgentNPC | null = null;
    let closestDist = Infinity;
    for (const agent of this.agents.values()) {
      if (!agent.isNear(this.player.x, this.player.y, radius)) continue;
      const dist = Phaser.Math.Distance.Between(this.player.x, this.player.y, agent.x, agent.y);
      if (dist < closestDist) {
        closest = agent;
        closestDist = dist;
      }
    }
    return closest;
  }

  /** Spawns/despawns agents to match their server-driven schedule location. */
  private refreshAgentPresence(): void {
    if (!this.agentLocation) return;
    const present = AGENT_IDS.filter((id) => NPCManager.getAgent(id).location === this.agentLocation);

    for (const id of present) {
      if (this.agents.has(id)) continue;
      const index = present.indexOf(id);
      const spawn = this.getAgentSpawnPoint(id, index, present.length, this.widthPx, this.heightPx);
      const npc = new AgentNPC(this, spawn.x, spawn.y, id);
      this.agents.set(id, npc);
      this.physics.add.collider(this.player.sprite, npc.sprite);
    }

    for (const [id, npc] of this.agents) {
      if (!present.includes(id)) {
        npc.destroy();
        this.agents.delete(id);
      }
    }
  }

  /** Override to customize where agents spawn in a given room. Defaults to spreading them evenly around room center. */
  protected getAgentSpawnPoint(
    _agentId: AgentId,
    index: number,
    total: number,
    widthPx: number,
    heightPx: number,
  ): { x: number; y: number } {
    const spacing = 32;
    const offset = (index - (total - 1) / 2) * spacing;
    return { x: widthPx / 2 + offset, y: heightPx / 2 - 10 };
  }

  /** Hook for subclasses to add props, decoration, etc. after the base room is built. */
  protected onBuild(_widthPx: number, _heightPx: number): void {}

  /** Hook for subclasses to run per-frame logic beyond the shared player/agent/door handling. */
  protected onUpdate(): void {}
}
