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
    // Sized for up to two short wrapped lines of body text (see nexus.py's
    // _truncate() — server text is capped to fit this, not the other way
    // around, since Phaser's wordWrap only wraps width, not box height).
    scene.add.rectangle(x, y, 92, 58, 0xf4e6c9).setStrokeStyle(2, 0x241c14).setDepth(3);
    scene.add
      .text(x, y - 33, "WHITEBOARD", { fontFamily: "monospace", fontSize: "6px", color: "#f4e6c9", backgroundColor: "#241c14" })
      .setOrigin(0.5)
      .setDepth(3);
    this.text = scene.add
      .text(x, y, NexusManager.getWhiteboard(boardId), {
        fontFamily: "monospace",
        fontSize: "6px",
        lineSpacing: 3,
        color: "#241c14",
        align: "center",
        wordWrap: { width: 82 },
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
