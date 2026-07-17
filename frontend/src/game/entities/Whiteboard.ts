import Phaser from "phaser";
import { NexusManager } from "@/game/systems/NexusManager";
import { EventBus } from "@/game/systems/EventBus";

/**
 * An office whiteboard prop that automatically updates its text whenever
 * NEXUS pushes a new value for its boardId (see NexusManager /
 * "whiteboard:updated"). Reused by every office that needs one instead of
 * each room hand-rolling its own text-sync logic.
 */
export class Whiteboard {
  private text: Phaser.GameObjects.Text;
  private unsubscribe: () => void;

  constructor(scene: Phaser.Scene, x: number, y: number, private boardId: string) {
    scene.add.rectangle(x, y, 72, 44, 0xf4e6c9).setStrokeStyle(2, 0x241c14).setDepth(3);
    scene.add
      .text(x, y - 26, "WHITEBOARD", { fontFamily: "monospace", fontSize: "6px", color: "#f4e6c9", backgroundColor: "#241c14" })
      .setOrigin(0.5)
      .setDepth(3);
    this.text = scene.add
      .text(x, y, NexusManager.getWhiteboard(boardId), {
        fontFamily: "monospace",
        fontSize: "7px",
        color: "#241c14",
        align: "center",
        wordWrap: { width: 64 },
      })
      .setOrigin(0.5)
      .setDepth(4);

    this.unsubscribe = EventBus.on("whiteboard:updated", ({ boardId: updatedId, text }) => {
      if (updatedId === this.boardId) this.text.setText(text);
    });
  }

  destroy(): void {
    this.unsubscribe();
    this.text.destroy();
  }
}
