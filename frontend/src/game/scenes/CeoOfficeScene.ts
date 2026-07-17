import { RoomScene } from "./RoomScene";
import { Whiteboard } from "@/game/entities/Whiteboard";
import type { AgentLocation, SceneId } from "@/types";

/** The player's own office. No agent ever has this as a home location — it's the CEO's private space. */
export class CeoOfficeScene extends RoomScene {
  protected sceneKey: SceneId = "CeoOfficeScene";
  protected widthTiles = 14;
  protected heightTiles = 10;
  protected floorAsset = "tiles/farmland-tile";
  protected roomLabel = "CEO Office";
  protected agentLocation: AgentLocation | null = null;

  private whiteboard: Whiteboard | null = null;

  constructor() {
    super("CeoOfficeScene");
  }

  protected onBuild(widthPx: number, heightPx: number): void {
    this.add.rectangle(widthPx / 2, heightPx / 2, widthPx, heightPx, 0xd9a441, 0.08).setDepth(1);
    this.add.image(widthPx / 2, 40, "outdoor-decoration/chest").setScale(1.5).setDepth(2);
    this.whiteboard = new Whiteboard(this, widthPx - 40, 32, "ceo-office");
  }

  shutdown(): void {
    super.shutdown();
    this.whiteboard?.destroy();
    this.whiteboard = null;
  }
}
