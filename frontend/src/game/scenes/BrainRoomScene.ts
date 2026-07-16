import { RoomScene } from "./RoomScene";
import type { ScoutLocation, SceneId } from "@/types";

/**
 * The "Brain Room" — where deep research/back-testing happens. Purely
 * decorative in v0.1 (architecture reserved for an AI-visualization
 * centerpiece in a future version); Scout spends part of his schedule here.
 */
export class BrainRoomScene extends RoomScene {
  protected sceneKey: SceneId = "BrainRoomScene";
  protected widthTiles = 12;
  protected heightTiles = 9;
  protected floorAsset = "tiles/water-middle";
  protected roomLabel = "Brain Room";
  protected scoutLocation: ScoutLocation | null = "brain-room";

  constructor() {
    super("BrainRoomScene");
  }

  protected onBuild(widthPx: number, heightPx: number): void {
    this.add.rectangle(widthPx / 2, heightPx / 2, widthPx, heightPx, 0x8a5cf6, 0.16).setDepth(1);
  }
}
