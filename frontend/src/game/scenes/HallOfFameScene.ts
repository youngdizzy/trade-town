import { RoomScene } from "./RoomScene";
import { NexusManager } from "@/game/systems/NexusManager";
import type { AgentId, AgentLocation, HallOfFameEntry, SceneId } from "@/types";

const PLAQUE_STYLE = {
  fontFamily: "monospace",
  fontSize: "6px",
  lineSpacing: 2,
  color: "#241c14",
  align: "center" as const,
  wordWrap: { width: 66 },
};

function formatHallOfFame(entries: HallOfFameEntry[]): string {
  if (entries.length === 0) return "No records yet.\nTradeTown's first\nchampion awaits.";
  const latest = entries[entries.length - 1];
  return latest ? `${latest.title}\n${latest.value.toFixed(1)}` : "";
}

/**
 * The Hall of Fame — trophies, banners, and framed reports celebrating
 * TradeTown's best strategies, simulations, research, and streaks (see
 * backend/app/hall_of_fame.py's evaluate_hall_of_fame()). No agent's
 * schedule sends them here by default; it's a company showcase room, not a
 * workspace.
 */
export class HallOfFameScene extends RoomScene {
  protected sceneKey: SceneId = "HallOfFameScene";
  protected widthTiles = 17;
  protected heightTiles = 11;
  protected floorAsset = "tiles/path-tile";
  protected roomLabel = "Hall of Fame";
  protected agentLocation: AgentLocation | null = "hall-of-fame";

  constructor() {
    super("HallOfFameScene");
  }

  protected onBuild(widthPx: number, heightPx: number): void {
    this.add.rectangle(widthPx / 2, heightPx / 2, widthPx, heightPx, 0x2a2210, 0.35).setDepth(1);
    this.buildBanners(widthPx);
    this.buildTrophyCases(widthPx, heightPx);
    this.buildPlaque(widthPx, heightPx);
  }

  private buildBanners(widthPx: number): void {
    const colors = [0xd9a441, 0xc9a3ff, 0x60d1ff, 0x9be7b0];
    const spacing = widthPx / (colors.length + 1);
    colors.forEach((color, i) => {
      const x = spacing * (i + 1);
      this.add.rectangle(x, 20, 14, 30, color, 0.85).setStrokeStyle(1, 0x241c14).setDepth(2);
      this.add.triangle(x, 36, -7, 0, 7, 0, 0, 6, color, 0.85).setDepth(2);
    });
  }

  private buildTrophyCases(widthPx: number, heightPx: number): void {
    const positions: [number, number][] = [
      [26, heightPx - 30],
      [widthPx - 26, heightPx - 30],
    ];
    for (const [x, y] of positions) {
      this.add.rectangle(x, y, 26, 34, 0xf4e6c9, 0.15).setStrokeStyle(1, 0xd9a441).setDepth(2);
      const cup = this.add.circle(x, y + 6, 6, 0xffd166).setStrokeStyle(1, 0x8a6a1a).setDepth(3);
      this.tweens.add({ targets: cup, y: y + 2, duration: 1600, yoyo: true, repeat: -1, ease: "Sine.easeInOut" });
      this.add.rectangle(x, y + 14, 10, 3, 0x8a6a1a).setDepth(3);
    }
  }

  private buildPlaque(widthPx: number, heightPx: number): void {
    const px = widthPx / 2;
    const py = heightPx / 2 + 4;
    this.add.rectangle(px, py, 78, 40, 0xf4e6c9).setStrokeStyle(2, 0x241c14).setDepth(2);
    this.add
      .text(px, py - 16, "LATEST INDUCTEE", { fontFamily: "monospace", fontSize: "6px", color: "#8a6a1a" })
      .setOrigin(0.5)
      .setDepth(3);
    this.addLiveText("hallOfFame:updated", px, py + 2, PLAQUE_STYLE, formatHallOfFame, NexusManager.getHallOfFame());
  }

  protected override getAgentSpawnPoint(
    _agentId: AgentId,
    index: number,
    total: number,
    widthPx: number,
    heightPx: number,
  ): { x: number; y: number } {
    // The inductee plaque occupies the room's center — spawn agents near
    // the trophy cases along the side walls instead.
    const spacing = 30;
    const offset = (index - (total - 1) / 2) * spacing;
    return { x: widthPx / 2 + offset, y: heightPx - 46 };
  }
}
