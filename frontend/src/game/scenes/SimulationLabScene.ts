import { RoomScene } from "./RoomScene";
import { NexusManager } from "@/game/systems/NexusManager";
import type { AgentId, AgentLocation, SceneId } from "@/types";

const TEXT_STYLE = {
  fontFamily: "monospace",
  fontSize: "6px",
  lineSpacing: 4,
  color: "#60d1ff",
  align: "left" as const,
};

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function formatQueue({ sessions }: { sessions: { status: string; strategyName: string; symbol: string; progress: number }[] }): string {
  const active = sessions.filter((s) => s.status !== "completed").slice(0, 2);
  if (active.length === 0) return "QUEUE: idle";
  const lines = active.map((s) => `${s.status === "running" ? "▶" : "•"} ${truncate(s.strategyName, 14)} ${s.progress.toFixed(0)}%`);
  return ["QUEUE:", ...lines].join("\n");
}

function formatResults({ results }: { results: { strategyName: string; symbol: string; totalReturnPct: number }[] }): string {
  const recent = results.slice(-2).reverse();
  if (recent.length === 0) return "RESULTS: none yet";
  const lines = recent.map((r) => `${truncate(r.strategyName, 12)} ${r.totalReturnPct >= 0 ? "+" : ""}${r.totalReturnPct.toFixed(1)}%`);
  return ["RESULTS:", ...lines].join("\n");
}

/**
 * The Simulation Lab — servers, research terminals, and strategy consoles
 * running backend/app/simulation.py's placeholder backtests (see that
 * module's docstring — historical data is placeholder, no real
 * MarketDataProvider yet). Coach is the only agent whose schedule brings
 * them here (see backend/app/schedule.py); the live queue/results readouts
 * work regardless of who's physically present, the same way BrainRoomHud's
 * data doesn't depend on which agents are in the Brain Room.
 */
export class SimulationLabScene extends RoomScene {
  protected sceneKey: SceneId = "SimulationLabScene";
  protected widthTiles = 17;
  protected heightTiles = 11;
  protected floorAsset = "tiles/cliff-tile";
  protected roomLabel = "Simulation Lab";
  protected agentLocation: AgentLocation | null = "simulation-lab";

  constructor() {
    super("SimulationLabScene");
  }

  protected onBuild(widthPx: number, heightPx: number): void {
    this.add.rectangle(widthPx / 2, heightPx / 2, widthPx, heightPx, 0x0c1a24, 0.5).setDepth(1);
    this.buildServerRacks(widthPx, heightPx);
    this.buildConsoles(widthPx, heightPx);
  }

  private buildServerRacks(widthPx: number, _heightPx: number): void {
    const rackCount = 5;
    const startX = widthPx / 2 - ((rackCount - 1) * 20) / 2;
    for (let i = 0; i < rackCount; i++) {
      const x = startX + i * 20;
      const y = 22;
      this.add.rectangle(x, y, 16, 28, 0x1a2530).setStrokeStyle(1, 0x2f4a5c).setDepth(2);
      for (let led = 0; led < 4; led++) {
        const blink = this.add.circle(x - 5 + (led % 2) * 10, y - 9 + Math.floor(led / 2) * 8, 1.4, 0x60ffb0).setDepth(3);
        this.tweens.add({
          targets: blink,
          alpha: { from: 1, to: 0.2 },
          duration: 500 + Math.random() * 900,
          yoyo: true,
          repeat: -1,
        });
      }
    }
  }

  private buildConsoles(widthPx: number, heightPx: number): void {
    // A central simulation console (queue on top, results below) flanked
    // by two research terminals.
    const cy = heightPx / 2 + 4;
    this.add.rectangle(widthPx / 2, cy, 130, 66, 0x0b1620).setStrokeStyle(2, 0x60d1ff, 0.6).setDepth(2);
    const initial = { sessions: NexusManager.getBacktestSessions(), results: NexusManager.getSimulationResults() };
    this.addLiveText("simulation:updated", widthPx / 2, cy - 15, TEXT_STYLE, formatQueue, initial);
    this.addLiveText("simulation:updated", widthPx / 2, cy + 15, { ...TEXT_STYLE, color: "#8fe3b0" }, formatResults, initial);

    for (const dx of [-46, 46]) {
      const tx = widthPx / 2 + dx;
      const ty = heightPx - 26;
      this.add.rectangle(tx, ty, 24, 15, 0x241c14).setDepth(2);
      this.add.rectangle(tx, ty - 9, 20, 13, 0x0b0b12).setStrokeStyle(1, 0xb388ff, 0.7).setDepth(3);
    }
  }

  protected override getAgentSpawnPoint(
    _agentId: AgentId,
    index: number,
    total: number,
    widthPx: number,
    heightPx: number,
  ): { x: number; y: number } {
    // The simulation console occupies the room's center — spawn agents
    // below it, near the research terminals.
    const spacing = 30;
    const offset = (index - (total - 1) / 2) * spacing;
    return { x: widthPx / 2 + offset, y: heightPx - 40 };
  }
}
