import Phaser from "phaser";
import { AnimatedActor } from "./AnimatedActor";
import type { AgentId, Direction } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";

const WANDER_RADIUS = 40;
const WANDER_INTERVAL_MS = 3500;
const ARRIVE_THRESHOLD = 4;
/**
 * Rooms like Brain Room and Meeting Room can legitimately hold all four
 * agents at once (that's the "Mission Control"/meeting design intent), but
 * their sprites sit closer together than a name tag is wide. Rather than
 * fight that with ever-increasing spacing, tags only show up close — the
 * same convention as Stardew-style top-down games — so a crowded room
 * reads as a crowd instead of a wall of overlapping text.
 */
const NAME_TAG_VISIBLE_RADIUS = 32;

/**
 * One AI employee's in-scene visual representation: wanders gently within
 * whatever room it's currently spawned in and shows a name tag when the
 * player is nearby (interacting opens the full DialogueBox, owned by
 * DialogueManager, rather than an in-world bubble). Task/mood/energy/
 * location are all owned by NPCManager (server-authoritative via NEXUS);
 * this class only handles rendering and idle wander movement. Used for all
 * four agents — the only per-agent differences are the id (for tint/label
 * lookup) and where the scene spawns it.
 */
export class AgentNPC extends AnimatedActor {
  readonly agentId: AgentId;
  private homeX: number;
  private homeY: number;
  private target: { x: number; y: number } | null = null;
  private wanderTimer: Phaser.Time.TimerEvent;

  constructor(scene: Phaser.Scene, x: number, y: number, agentId: AgentId) {
    const profile = AGENT_PROFILES[agentId];
    super(scene, x, y, "player/player", profile.name);
    this.agentId = agentId;
    this.sprite.setTint(profile.tint);
    this.homeX = x;
    this.homeY = y;
    this.sprite.play("player/player::idle-down");
    this.nameTag.setVisible(false);

    this.wanderTimer = scene.time.addEvent({
      delay: WANDER_INTERVAL_MS,
      loop: true,
      callback: () => this.pickNewTarget(),
    });
    this.pickNewTarget();
  }

  private pickNewTarget(): void {
    if (Math.random() < 0.4) {
      this.target = null; // Pause and idle sometimes instead of always wandering.
      return;
    }
    const angle = Math.random() * Math.PI * 2;
    const radius = Math.random() * WANDER_RADIUS;
    this.target = {
      x: this.homeX + Math.cos(angle) * radius,
      y: this.homeY + Math.sin(angle) * radius,
    };
  }

  update(playerX: number, playerY: number): void {
    if (this.target) {
      const dx = this.target.x - this.sprite.x;
      const dy = this.target.y - this.sprite.y;
      const dist = Math.hypot(dx, dy);
      if (dist < ARRIVE_THRESHOLD) {
        this.target = null;
        this.setVelocityForDirection(0, 0);
        this.playAnim(false);
      } else {
        const nx = dx / dist;
        const ny = dy / dist;
        this.setVelocityForDirection(nx, ny);
        this.facing = dominantDirection(nx, ny);
        this.playAnim(true);
      }
    } else {
      this.setVelocityForDirection(0, 0);
      this.playAnim(false);
    }
    this.syncNameTag();
    this.nameTag.setVisible(this.isNear(playerX, playerY, NAME_TAG_VISIBLE_RADIUS));
  }

  isNear(x: number, y: number, radius = 28): boolean {
    return Phaser.Math.Distance.Between(this.sprite.x, this.sprite.y, x, y) <= radius;
  }

  override destroy(): void {
    this.wanderTimer.destroy();
    super.destroy();
  }
}

function dominantDirection(nx: number, ny: number): Direction {
  return Math.abs(nx) > Math.abs(ny) ? (nx > 0 ? "right" : "left") : ny > 0 ? "down" : "up";
}
