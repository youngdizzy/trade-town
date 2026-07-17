import { RoomScene } from "./RoomScene";
import type { AgentLocation, SceneId } from "@/types";

/** Scout's primary workspace. Scout is present here whenever his schedule places him at "scout-office". */
export class ScoutOfficeScene extends RoomScene {
  protected sceneKey: SceneId = "ScoutOfficeScene";
  protected widthTiles = 14;
  protected heightTiles = 10;
  protected floorAsset = "tiles/path-middle";
  protected roomLabel = "Scout's Office";
  protected agentLocation: AgentLocation | null = "scout-office";

  constructor() {
    super("ScoutOfficeScene");
  }

  protected onBuild(widthPx: number, heightPx: number): void {
    this.add.rectangle(widthPx / 2, heightPx / 2, widthPx, heightPx, 0x4caf6a, 0.08).setDepth(1);
    this.add.image(widthPx - 32, 32, "outdoor-decoration/chest").setScale(1.5).setDepth(2);
    this.addWhiteboard(40, 32, "scout-office");
  }
}
