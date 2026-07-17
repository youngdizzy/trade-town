import Phaser from "phaser";
import { AnimatedActor, screenGapToWorld } from "./AnimatedActor";
import type { Direction } from "@/types";

const WANDER_RADIUS = 40;
const WANDER_INTERVAL_MS = 3500;
const ARRIVE_THRESHOLD = 4;
const SPEECH_BUBBLE_SCREEN_GAP_PX = 95;

/**
 * Scout, TradeTown's one AI research employee. Wanders gently within his
 * current room so the office feels alive, exposes a speech bubble on
 * interact, and always shows a name tag. His task/mood/energy are owned by
 * NPCManager (server-authoritative); this class is purely the in-scene
 * visual representation plus idle wander movement.
 */
export class ScoutNPC extends AnimatedActor {
  private homeX: number;
  private homeY: number;
  private target: { x: number; y: number } | null = null;
  private wanderTimer: Phaser.Time.TimerEvent;
  private speechBubble: Phaser.GameObjects.Text | null = null;

  constructor(scene: Phaser.Scene, x: number, y: number) {
    super(scene, x, y, "player/player", "Scout");
    this.sprite.setTint(0xbfe3ff);
    this.homeX = x;
    this.homeY = y;
    this.sprite.play("player/player::idle-down");

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
    this.speechBubble?.setPosition(this.sprite.x, this.sprite.y - screenGapToWorld(this.scene, SPEECH_BUBBLE_SCREEN_GAP_PX));
  }

  isNear(x: number, y: number, radius = 28): boolean {
    return Phaser.Math.Distance.Between(this.sprite.x, this.sprite.y, x, y) <= radius;
  }

  showSpeechBubble(text: string, durationMs = 2500): void {
    this.speechBubble?.destroy();
    this.speechBubble = this.scene.add
      .text(this.sprite.x, this.sprite.y - screenGapToWorld(this.scene, SPEECH_BUBBLE_SCREEN_GAP_PX), text, {
        fontFamily: "monospace",
        fontSize: "9px",
        color: "#241c14",
        backgroundColor: "#f4e6c9",
        padding: { x: 4, y: 3 },
        wordWrap: { width: 120 },
      })
      .setOrigin(0.5, 1)
      .setDepth(25);
    this.scene.time.delayedCall(durationMs, () => {
      this.speechBubble?.destroy();
      this.speechBubble = null;
    });
  }

  override destroy(): void {
    this.wanderTimer.destroy();
    this.speechBubble?.destroy();
    super.destroy();
  }
}

function dominantDirection(nx: number, ny: number): Direction {
  return Math.abs(nx) > Math.abs(ny) ? (nx > 0 ? "right" : "left") : ny > 0 ? "down" : "up";
}
