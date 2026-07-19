import { RoomScene } from "./RoomScene";
import { NexusManager } from "@/game/systems/NexusManager";
import type { AgentId, AgentLocation, CompanyScore, SceneId } from "@/types";

const SCORE_STYLE = {
  fontFamily: "monospace",
  fontSize: "8px",
  lineSpacing: 5,
  color: "#ffb08a",
  align: "left" as const,
};

function formatOverall(score: CompanyScore): string {
  return `OVERALL: ${score.overall.toFixed(0)}/100`;
}

function formatScoreCol1(score: CompanyScore): string {
  return [
    `Research  ${score.researchQuality.toFixed(0)}`,
    `Decisions ${score.decisionQuality.toFixed(0)}`,
    `Risk      ${score.riskManagement.toFixed(0)}`,
    `Paper P&L ${score.paperTradingPerformance.toFixed(0)}`,
  ].join("\n");
}

function formatScoreCol2(score: CompanyScore): string {
  return [
    `Teamwork   ${score.teamCoordination.toFixed(0)}`,
    `Knowledge  ${score.knowledgeGrowth.toFixed(0)}`,
    `Simulation ${score.simulationSuccess.toFixed(0)}`,
  ].join("\n");
}

/**
 * The Performance Center — Coach's home office (v0.5 brief, Feature 1).
 * The scoreboard mirrors the same seven CompanyScore metrics shown in the
 * Brain Room HUD (see backend/app/company_score.py); the full weekly/
 * monthly report with agent rankings and recommendations lives in the
 * Coach Dashboard React overlay, opened from the toolbar — this in-world
 * scoreboard is the at-a-glance version, the same relationship the Brain
 * Room's holographic core has to BrainRoomHud. The seven metrics are laid
 * out in two columns (rather than one tall stack) specifically so the
 * whole board fits within the box without the title/overall/metric text
 * ever needing to touch — a single-column stack overflowed the box and
 * overlapped the "OVERALL" line during gameplay testing.
 */
export class PerformanceCenterScene extends RoomScene {
  protected sceneKey: SceneId = "PerformanceCenterScene";
  protected widthTiles = 15;
  protected heightTiles = 13;
  protected floorAsset = "tilesets/water-tile";
  protected roomLabel = "Performance Center";
  protected agentLocation: AgentLocation | null = "performance-center";

  constructor() {
    super("PerformanceCenterScene");
  }

  protected onBuild(widthPx: number, heightPx: number): void {
    this.add.rectangle(widthPx / 2, heightPx / 2, widthPx, heightPx, 0x241608, 0.35).setDepth(1);
    this.buildScoreboard(widthPx, heightPx);
    this.buildDesk(widthPx, heightPx);
  }

  private buildScoreboard(widthPx: number, heightPx: number): void {
    const cx = widthPx / 2;
    const cy = heightPx / 2 - 30;
    this.add.rectangle(cx, cy, 200, 88, 0x0b0b12).setStrokeStyle(2, 0xff8c61, 0.8).setDepth(2);
    this.add
      .text(cx, cy - 36, "COMPANY SCOREBOARD", { fontFamily: "monospace", fontSize: "8px", color: "#f4e6c9", resolution: 4 })
      .setOrigin(0.5)
      .setDepth(3);
    const initial = NexusManager.getCompanyScore();
    this.addLiveText("companyScore:updated", cx, cy - 20, { ...SCORE_STYLE, align: "center" }, formatOverall, initial);
    this.addLiveText("companyScore:updated", cx - 48, cy + 12, SCORE_STYLE, formatScoreCol1, initial);
    this.addLiveText("companyScore:updated", cx + 48, cy + 12, SCORE_STYLE, formatScoreCol2, initial);
  }

  private buildDesk(widthPx: number, heightPx: number): void {
    const dx = widthPx / 2;
    const dy = heightPx - 18;
    this.add.rectangle(dx, dy, 40, 16, 0x241c14).setDepth(2);
    this.add.rectangle(dx - 10, dy - 8, 12, 8, 0x0b0b12).setStrokeStyle(1, 0x60d1ff, 0.6).setDepth(3);
    this.add.rectangle(dx + 10, dy - 8, 12, 8, 0x0b0b12).setStrokeStyle(1, 0x60d1ff, 0.6).setDepth(3);
  }

  protected override getAgentSpawnPoint(
    _agentId: AgentId,
    index: number,
    total: number,
    widthPx: number,
    heightPx: number,
  ): { x: number; y: number } {
    // The scoreboard occupies the room's upper section — spawn agents
    // down by the desk, well clear of the box (and its name-tag headroom)
    // above.
    const spacing = 30;
    const offset = (index - (total - 1) / 2) * spacing;
    return { x: widthPx / 2 + offset, y: heightPx - 40 };
  }
}
