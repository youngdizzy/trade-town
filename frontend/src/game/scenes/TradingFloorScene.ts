import { RoomScene } from "./RoomScene";
import { EventBus } from "@/game/systems/EventBus";
import { NexusManager } from "@/game/systems/NexusManager";
import type { AgentId, AgentLocation, PaperPortfolio, RiskWarning, SceneId, WatchlistEntry } from "@/types";

const TICKER_STYLE = {
  fontFamily: "monospace",
  fontSize: "7px",
  color: "#5ce1ff",
  align: "left" as const,
};

const COMMAND_STYLE = {
  fontFamily: "monospace",
  fontSize: "7px",
  color: "#f4e6c9",
  align: "center" as const,
};

function formatTicker(watchlist: WatchlistEntry[]): string {
  if (watchlist.length === 0) return "No symbols on watchlist.";
  return watchlist
    .slice(0, 6)
    .map((w) => `${w.symbol.padEnd(7)} ${w.lastPrice.toFixed(2).padStart(8)} ${w.dailyChangePct >= 0 ? "+" : ""}${w.dailyChangePct.toFixed(1)}%`)
    .join("\n");
}

function formatCommand(portfolio: PaperPortfolio): string {
  return [
    `EQUITY $${(portfolio.cashBalance + portfolio.positions.reduce((sum, p) => sum + p.quantity * p.currentPrice, 0)).toFixed(0)}`,
    `P&L ${portfolio.totalPnlPct >= 0 ? "+" : ""}${portfolio.totalPnlPct.toFixed(1)}%`,
    `POSITIONS ${portfolio.positions.length}  ORDERS ${portfolio.orders.filter((o) => o.status === "open").length}`,
  ].join("\n");
}

/**
 * The Trading Floor — home to Sentinel (Risk Management), Pulse (Market
 * Scanner), and Guardian (Portfolio Protection), the v0.6 brief's paper
 * trading operations room. The market ticker and central command display
 * read live off NexusManager (the same "in-world at-a-glance, React
 * overlay for detail" split established by the Brain Room's holographic
 * core and Performance Center's scoreboard) rather than duplicating the
 * Brain Room HUD's full portfolio/risk/scanner detail in-world.
 */
export class TradingFloorScene extends RoomScene {
  protected sceneKey: SceneId = "TradingFloorScene";
  protected widthTiles = 22;
  protected heightTiles = 15;
  protected floorAsset = "tiles/water-tile";
  protected roomLabel = "Trading Floor";
  protected agentLocation: AgentLocation | null = "trading-floor";

  private statusLights: Phaser.GameObjects.Arc[] = [];
  private riskUnsubscribe: (() => void) | null = null;

  constructor() {
    super("TradingFloorScene");
  }

  protected onBuild(widthPx: number, heightPx: number): void {
    this.add.rectangle(widthPx / 2, heightPx / 2, widthPx, heightPx, 0x0c1420, 0.4).setDepth(1);
    this.buildWallMonitors(widthPx);
    this.buildTicker(widthPx);
    this.buildCentralCommand(widthPx / 2, heightPx / 2 - 6);
    this.buildAgentDesks(widthPx, heightPx);
    this.buildConferenceTable(widthPx, heightPx);
    this.buildServerCabinets(heightPx);
    this.buildStatusLights(widthPx);
  }

  /** Animated market boards along the back wall — flavor only, values aren't tied to real data (see Brain Room's monitor desks for the same "screens that pulse" pattern). */
  private buildWallMonitors(widthPx: number): void {
    const count = 5;
    for (let i = 0; i < count; i++) {
      const x = (widthPx / (count + 1)) * (i + 1);
      const y = 20;
      const screen = this.add.rectangle(x, y, 26, 16, 0x0b0b12).setStrokeStyle(1, 0x5ce1ff, 0.7).setDepth(3);
      this.tweens.add({
        targets: screen,
        alpha: { from: 0.6, to: 1 },
        duration: 1000 + Math.random() * 900,
        yoyo: true,
        repeat: -1,
        ease: "Sine.easeInOut",
      });
    }
  }

  private buildTicker(widthPx: number): void {
    const y = 42;
    this.add.rectangle(widthPx / 2, y, widthPx - 24, 40, 0x0b0b12).setStrokeStyle(1, 0x5ce1ff, 0.6).setDepth(2);
    this.add.text(widthPx / 2, y - 22, "MARKET TICKER", { fontFamily: "monospace", fontSize: "7px", color: "#5ce1ff", resolution: 4 }).setOrigin(0.5).setDepth(3);
    this.addLiveText("watchlist:updated", widthPx / 2, y, { ...TICKER_STYLE, lineSpacing: 3 }, formatTicker, NexusManager.getWatchlist());
  }

  private buildCentralCommand(cx: number, cy: number): void {
    this.add.rectangle(cx, cy, 84, 44, 0x0b0b12).setStrokeStyle(2, 0xff8c61, 0.85).setDepth(3);
    this.add.text(cx, cy - 20, "CENTRAL COMMAND", { fontFamily: "monospace", fontSize: "7px", color: "#ff8c61", resolution: 4 }).setOrigin(0.5).setDepth(4);
    this.addLiveText("portfolio:updated", cx, cy + 2, { ...COMMAND_STYLE, lineSpacing: 3 }, formatCommand, NexusManager.getPaperPortfolio());
  }

  /** Individual AI desks — one per Trading Floor agent, arranged around the room's edges (agents themselves spawn near their own desk, see getAgentSpawnPoint). */
  private buildAgentDesks(widthPx: number, heightPx: number): void {
    const desks: [number, number, number][] = [
      [widthPx * 0.2, heightPx - 40, 0xff5c5c], // Sentinel
      [widthPx * 0.5, heightPx - 40, 0x5ce1ff], // Pulse
      [widthPx * 0.8, heightPx - 40, 0x4a90d9], // Guardian
    ];
    for (const [x, y, tint] of desks) {
      this.add.rectangle(x, y, 28, 16, 0x241c14).setDepth(2);
      this.add.rectangle(x, y - 9, 22, 10, 0x0b0b12).setStrokeStyle(1, tint, 0.8).setDepth(3);
    }
  }

  private buildConferenceTable(widthPx: number, heightPx: number): void {
    const cx = widthPx - 48;
    const cy = heightPx / 2 + 30;
    this.add.ellipse(cx, cy, 46, 22, 0x2e2013).setStrokeStyle(1, 0xd9a441, 0.6).setDepth(2);
  }

  private buildServerCabinets(heightPx: number): void {
    const positions: [number, number][] = [
      [16, heightPx / 2 + 30],
      [16, heightPx / 2 + 46],
    ];
    for (const [x, y] of positions) {
      this.add.rectangle(x, y, 14, 14, 0x1a1a24).setStrokeStyle(1, 0x60d1ff, 0.5).setDepth(2);
      const light = this.add.circle(x + 4, y - 4, 1.2, 0x8fe3b0).setDepth(3);
      this.tweens.add({ targets: light, alpha: { from: 0.3, to: 1 }, duration: 600 + Math.random() * 500, yoyo: true, repeat: -1 });
    }
  }

  /** Green/yellow/red status lights reflecting Guardian's standing risk watch (riskWarnings) — the room's at-a-glance "is everything okay" readout. */
  private buildStatusLights(widthPx: number): void {
    for (let i = 0; i < 3; i++) {
      const light = this.add.circle(widthPx - 16, 12 + i * 8, 2, 0x8fe3b0).setDepth(5);
      this.statusLights.push(light);
    }
    this.applyRiskWarnings(NexusManager.getRiskWarnings());
    this.riskUnsubscribe = EventBus.on("riskWarnings:updated", (warnings) => this.applyRiskWarnings(warnings));
    this.events.once("shutdown", () => this.disconnectRiskWarnings());
  }

  private disconnectRiskWarnings(): void {
    this.riskUnsubscribe?.();
    this.riskUnsubscribe = null;
  }

  private applyRiskWarnings(warnings: RiskWarning[]): void {
    const hasCritical = warnings.some((w) => w.severity === "critical");
    const hasWarning = warnings.some((w) => w.severity === "warning");
    const color = hasCritical ? 0xff5c5c : hasWarning ? 0xd9a441 : 0x8fe3b0;
    for (const light of this.statusLights) light.setFillStyle(color);
  }

  protected override getAgentSpawnPoint(
    agentId: AgentId,
    _index: number,
    _total: number,
    widthPx: number,
    heightPx: number,
  ): { x: number; y: number } {
    const byAgent: Partial<Record<AgentId, number>> = { sentinel: 0.2, pulse: 0.5, guardian: 0.8 };
    const fraction = byAgent[agentId] ?? 0.5;
    return { x: widthPx * fraction, y: heightPx - 52 };
  }
}
