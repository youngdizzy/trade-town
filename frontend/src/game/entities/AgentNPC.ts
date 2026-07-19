import Phaser from "phaser";
import { AnimatedActor, screenGapToWorld } from "./AnimatedActor";
import type { AgentId, Direction } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { AssetLoader } from "@/game/systems/AssetLoader";

const WANDER_INTERVAL_MS = 3500;
const ARRIVE_THRESHOLD = 4;
const BADGE_SCREEN_GAP_PX = 26;

/**
 * One AI employee's in-scene visual representation: wanders gently within
 * whatever room it's currently spawned in. Task/mood/energy/location are
 * all owned by NPCManager (server-authoritative via NEXUS); this class
 * only handles rendering and idle wander movement. Used for all four
 * agents — the only per-agent differences are the id (for tint/label
 * lookup) and where the scene spawns it.
 *
 * Name tag visibility is *not* decided here — see RoomScene, which shows
 * at most one tag at a time (whichever agent is nearest the player).
 * Rooms like Brain Room and Meeting Room can legitimately hold all four
 * agents at once (that's the "Mission Control"/meeting design intent),
 * and their sprites sit closer together than a name tag is wide; if every
 * agent within some radius of the player showed its own tag independently,
 * two agents that are merely near *each other* (not just near the player)
 * would still produce overlapping, unreadable text. Interacting opens the
 * full React `DialogueBox` (owned by `DialogueManager`) — there is no
 * separate in-world speech bubble, to avoid two overlapping text UIs
 * firing off the same interact press.
 *
 * Each agent renders from its own palette-swapped sprite sheet (see
 * AgentProfile.spriteId and animation-config.json's
 * "_comment_agent_variants") instead of one shared sheet plus a whole-
 * image tint, so distinct hair/clothes colors — not just a color wash —
 * are what makes an agent recognizable at a glance in a crowded room.
 * Each agent also gets an always-visible badge glyph above its head
 * (unlike the name tag, never proximity-gated) and its own wander
 * radius/idle-pause chance drawn from `AgentProfile` — Atlas barely
 * moves, Scout roams widely, etc. — so identity reads through behavior
 * too, not just appearance.
 */
export class AgentNPC extends AnimatedActor {
  readonly agentId: AgentId;
  private readonly badge: Phaser.GameObjects.Text;
  private readonly wanderRadius: number;
  private readonly idlePauseChance: number;
  private homeX: number;
  private homeY: number;
  private target: { x: number; y: number } | null = null;
  private wanderTimer: Phaser.Time.TimerEvent;

  constructor(scene: Phaser.Scene, x: number, y: number, agentId: AgentId) {
    const profile = AGENT_PROFILES[agentId];
    super(scene, x, y, profile.spriteId, profile.name);
    this.agentId = agentId;
    this.wanderRadius = profile.wanderRadius;
    this.idlePauseChance = profile.idlePauseChance;
    this.homeX = x;
    this.homeY = y;
    this.sprite.play(AssetLoader.animKey(profile.spriteId, "idle-down"));
    this.nameTag.setVisible(false);

    this.badge = scene.add
      .text(x, y - screenGapToWorld(scene, BADGE_SCREEN_GAP_PX), profile.badge, {
        fontSize: "14px",
      })
      .setOrigin(0.5, 1)
      .setDepth(20);

    this.wanderTimer = scene.time.addEvent({
      delay: WANDER_INTERVAL_MS,
      loop: true,
      callback: () => this.pickNewTarget(),
    });
    this.pickNewTarget();
  }

  private pickNewTarget(): void {
    if (Math.random() < this.idlePauseChance) {
      this.target = null; // Pause and idle sometimes instead of always wandering.
      return;
    }
    const angle = Math.random() * Math.PI * 2;
    const radius = Math.random() * this.wanderRadius;
    this.target = {
      x: this.homeX + Math.cos(angle) * radius,
      y: this.homeY + Math.sin(angle) * radius,
    };
  }

  update(): void {
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
    this.badge.setPosition(this.sprite.x, this.sprite.y - screenGapToWorld(this.scene, BADGE_SCREEN_GAP_PX));
  }

  isNear(x: number, y: number, radius = 28): boolean {
    return Phaser.Math.Distance.Between(this.sprite.x, this.sprite.y, x, y) <= radius;
  }

  override destroy(): void {
    this.wanderTimer.destroy();
    this.badge.destroy();
    super.destroy();
  }
}

function dominantDirection(nx: number, ny: number): Direction {
  return Math.abs(nx) > Math.abs(ny) ? (nx > 0 ? "right" : "left") : ny > 0 ? "down" : "up";
}
