import { RoomScene } from "./RoomScene";
import type { AgentLocation, SceneId } from "@/types";

/**
 * Where agents recover energy. No agent calls this room a permanent home —
 * everyone visits briefly (NEXUS applies a short "break" location override
 * when an agent's energy dips low, see backend/app/nexus.py) then returns
 * to their normal schedule.
 */
export class BreakRoomScene extends RoomScene {
  protected sceneKey: SceneId = "BreakRoomScene";
  protected widthTiles = 12;
  protected heightTiles = 9;
  protected floorAsset = "tiles/beach-tile";
  protected roomLabel = "Break Room";
  protected agentLocation: AgentLocation | null = "break-room";

  constructor() {
    super("BreakRoomScene");
  }

  protected onBuild(widthPx: number, heightPx: number): void {
    this.add.rectangle(widthPx / 2, heightPx / 2, widthPx, heightPx, 0xd97b4a, 0.1).setDepth(1);

    // Coffee counter along the back wall.
    this.add.rectangle(widthPx / 2, 26, 60, 16, 0x8a5a34).setStrokeStyle(2, 0x5c3b20).setDepth(2);
    this.add.circle(widthPx / 2 - 16, 22, 5, 0x241c14).setDepth(3); // coffee pot
    this.add.circle(widthPx / 2 + 16, 22, 5, 0x241c14).setDepth(3);

    // A small round table with seats for chatting.
    const tx = widthPx / 2;
    const ty = heightPx / 2 + 20;
    this.add.circle(tx, ty, 16, 0x8a5a34).setStrokeStyle(2, 0x5c3b20).setDepth(2);
    for (const [dx, dy] of [
      [-22, 0],
      [22, 0],
      [0, -22],
      [0, 22],
    ] as [number, number][]) {
      this.add.circle(tx + dx, ty + dy, 5, 0x4a3624).setDepth(2);
    }

    this.add.image(24, heightPx - 24, "outdoor-decoration/chest").setScale(1.2).setDepth(2);
  }
}
