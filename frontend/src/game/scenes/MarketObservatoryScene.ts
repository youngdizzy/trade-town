import { RoomScene } from "./RoomScene";
import type { AgentLocation, SceneId } from "@/types";

const STATIONS: { label: string; x: number; y: number }[] = [
  { label: "TECHNICAL", x: 40, y: 34 },
  { label: "NEWS/EVENTS", x: 216, y: 34 },
  { label: "MACRO", x: 40, y: 130 },
  { label: "RISK", x: 216, y: 130 },
  { label: "STRATEGY", x: 128, y: 158 },
];

/**
 * The Market Observatory — deep, immersive market analysis, in contrast
 * to the Global Command Center's fast quick-access overlay (see the
 * v0.6.2 brief: "The Global Command Center provides quick access. The
 * Market Observatory provides deep immersive analysis. Both must use the
 * same underlying market data and analysis systems"). This scene is only
 * the physical room — the actual readouts (candlestick chart, station
 * summaries) live in MarketObservatoryHud.tsx as a React overlay, same
 * split BrainRoomScene/BrainRoomHud already established, and they pull
 * from the exact same gameStore fields and /api/market endpoint the
 * Command Center's Overview tab and DecisionDetail chart already use —
 * not a second, disconnected data source.
 *
 * No agent has this as a scheduled home location (agentLocation: null,
 * same as CeoOfficeScene) — inventing agent presence here would be fake
 * activity the v0.6.2 brief explicitly warns against, since nothing in
 * schedule.py actually routes anyone here.
 */
export class MarketObservatoryScene extends RoomScene {
  protected sceneKey: SceneId = "MarketObservatoryScene";
  protected widthTiles = 18;
  protected heightTiles = 12;
  protected floorAsset = "tilesets/water-middle";
  protected roomLabel = "Market Observatory";
  protected agentLocation: AgentLocation | null = null;

  constructor() {
    super("MarketObservatoryScene");
  }

  protected onBuild(widthPx: number, heightPx: number): void {
    this.add.rectangle(widthPx / 2, heightPx / 2, widthPx, heightPx, 0x0c1420, 0.6).setDepth(1);
    this.buildStations();
    this.buildCentralDisplay(widthPx / 2, heightPx / 2 + 6);
  }

  private buildStations(): void {
    for (const station of STATIONS) {
      this.add.rectangle(station.x, station.y, 30, 18, 0x131e2e).setStrokeStyle(1, 0x4fd8ff, 0.5).setDepth(2);
      this.add
        .text(station.x, station.y, station.label, {
          fontFamily: "monospace",
          fontSize: "5px",
          color: "#4fd8ff",
          align: "center",
          resolution: 4,
        })
        .setOrigin(0.5)
        .setDepth(3);
    }
  }

  private buildCentralDisplay(cx: number, cy: number): void {
    const screen = this.add.rectangle(cx, cy, 64, 40, 0x060a12).setStrokeStyle(1, 0x3ce28a, 0.8).setDepth(3);
    this.tweens.add({
      targets: screen,
      alpha: { from: 0.75, to: 1 },
      duration: 1500,
      yoyo: true,
      repeat: -1,
      ease: "Sine.easeInOut",
    });
    // A few candle-shaped bars hint at the chart without duplicating the
    // real one — the actual live data renders in MarketObservatoryHud.
    const bars = [-24, -14, -4, 6, 16, 26];
    bars.forEach((dx, i) => {
      const up = i % 2 === 0;
      this.add.rectangle(cx + dx, cy + (up ? 4 : -4), 4, 10 + (i % 3) * 4, up ? 0x3ce28a : 0xff4d5e, 0.85).setDepth(4);
    });
    this.add
      .text(cx, cy - 28, "MARKET DISPLAY", { fontFamily: "monospace", fontSize: "6px", color: "#6c8299", resolution: 4 })
      .setOrigin(0.5)
      .setDepth(4);
  }
}
