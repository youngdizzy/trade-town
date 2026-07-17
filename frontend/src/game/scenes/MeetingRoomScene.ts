import { RoomScene } from "./RoomScene";
import type { AgentId, AgentLocation, SceneId } from "@/types";

/**
 * Where the company gathers. Atlas calls this room home; NEXUS also pulls
 * multiple agents in here for occasional meetings (see backend/app/nexus.py
 * _maybe_call_meeting) — this scene doesn't know or care which case it is,
 * it just renders whoever's location is currently "meeting-room".
 */
export class MeetingRoomScene extends RoomScene {
  protected sceneKey: SceneId = "MeetingRoomScene";
  protected widthTiles = 15;
  protected heightTiles = 11;
  protected floorAsset = "tiles/farmland-tile";
  protected roomLabel = "Meeting Room";
  protected agentLocation: AgentLocation | null = "meeting-room";

  constructor() {
    super("MeetingRoomScene");
  }

  protected onBuild(widthPx: number, heightPx: number): void {
    this.add.rectangle(widthPx / 2, heightPx / 2, widthPx, heightPx, 0xffd166, 0.06).setDepth(1);
    this.buildTable(widthPx / 2, heightPx / 2 + 10);
    this.addWhiteboard(widthPx / 2, 30, "meeting-room");
  }

  private buildTable(cx: number, cy: number): void {
    this.add.rectangle(cx, cy, 76, 34, 0x8a5a34).setStrokeStyle(2, 0x5c3b20).setDepth(2);
    const seats: [number, number][] = [
      [cx - 32, cy - 26],
      [cx, cy - 26],
      [cx + 32, cy - 26],
      [cx - 32, cy + 26],
      [cx, cy + 26],
      [cx + 32, cy + 26],
    ];
    for (const [x, y] of seats) {
      this.add.circle(x, y, 5, 0x4a3624).setDepth(2);
    }
  }

  protected override getAgentSpawnPoint(
    _agentId: AgentId,
    index: number,
    _total: number,
    widthPx: number,
    heightPx: number,
  ): { x: number; y: number } {
    const seats: [number, number][] = [
      [widthPx / 2 - 32, heightPx / 2 - 16],
      [widthPx / 2, heightPx / 2 - 16],
      [widthPx / 2 + 32, heightPx / 2 - 16],
      [widthPx / 2 - 32, heightPx / 2 + 46],
    ];
    const seat = seats[index % seats.length]!;
    return { x: seat[0], y: seat[1] };
  }
}
