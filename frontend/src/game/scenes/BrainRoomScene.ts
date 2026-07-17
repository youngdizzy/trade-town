import { RoomScene } from "./RoomScene";
import type { AgentId, AgentLocation, SceneId } from "@/types";

/**
 * The "Brain Room" — Mission Control. A holographic core sits in the
 * center (procedural Phaser graphics/tweens, not imported art, per the
 * "use only supplied assets" rule), surrounded by monitor props. Echo and
 * Nova both call this room home; the detailed Company/Agent/Task/Discovery
 * readouts live in the React BrainRoomHud overlay (see
 * ui/components/BrainRoomHud.tsx) rather than as in-world text, so they
 * stay legible at any camera zoom.
 */
export class BrainRoomScene extends RoomScene {
  protected sceneKey: SceneId = "BrainRoomScene";
  protected widthTiles = 18;
  protected heightTiles = 12;
  protected floorAsset = "tiles/water-middle";
  protected agentLocation: AgentLocation | null = "brain-room";
  protected roomLabel = "Brain Room";

  constructor() {
    super("BrainRoomScene");
  }

  protected onBuild(widthPx: number, heightPx: number): void {
    this.add.rectangle(widthPx / 2, heightPx / 2, widthPx, heightPx, 0x1a1030, 0.55).setDepth(1);
    this.buildMonitorDesks(widthPx, heightPx);
    this.buildHolographicCore(widthPx / 2, heightPx / 2);
  }

  private buildMonitorDesks(widthPx: number, heightPx: number): void {
    const positions: [number, number][] = [
      [28, 26],
      [widthPx - 28, 26],
      [28, heightPx - 26],
      [widthPx - 28, heightPx - 26],
    ];
    for (const [x, y] of positions) {
      this.add.rectangle(x, y, 26, 16, 0x241c14).setDepth(2); // desk
      const screen = this.add.rectangle(x, y - 10, 22, 14, 0x0b0b12).setStrokeStyle(1, 0x60d1ff, 0.7).setDepth(3);
      this.tweens.add({
        targets: screen,
        alpha: { from: 0.7, to: 1 },
        duration: 1200 + Math.random() * 600,
        yoyo: true,
        repeat: -1,
        ease: "Sine.easeInOut",
      });
    }
  }

  private buildHolographicCore(cx: number, cy: number): void {
    const ringColors = [0x8a5cf6, 0xb388ff, 0x60d1ff];
    ringColors.forEach((color, i) => {
      const ring = this.add.circle(cx, cy, 10 + i * 7, color, 0.22).setStrokeStyle(1, color, 0.85).setDepth(5);
      this.tweens.add({
        targets: ring,
        scale: { from: 0.85, to: 1.2 },
        alpha: { from: 0.5, to: 0.12 },
        duration: 1400 + i * 350,
        yoyo: true,
        repeat: -1,
        ease: "Sine.easeInOut",
      });
      this.tweens.add({
        targets: ring,
        angle: 360,
        duration: 8000 + i * 2000,
        repeat: -1,
      });
    });

    const core = this.add.circle(cx, cy, 6, 0xffffff, 0.9).setDepth(6);
    this.tweens.add({ targets: core, alpha: { from: 0.55, to: 1 }, scale: { from: 0.9, to: 1.1 }, duration: 900, yoyo: true, repeat: -1 });

    this.add
      .text(cx, cy + 30, "MARKET CORE", { fontFamily: "monospace", fontSize: "7px", color: "#b388ff" })
      .setOrigin(0.5)
      .setDepth(5);
  }

  protected override getAgentSpawnPoint(
    _agentId: AgentId,
    index: number,
    total: number,
    widthPx: number,
    heightPx: number,
  ): { x: number; y: number } {
    const spacing = 38;
    const offset = (index - (total - 1) / 2) * spacing;
    return { x: widthPx / 2 + offset, y: heightPx / 2 + 52 };
  }
}
