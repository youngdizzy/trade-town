import { RoomScene } from "./RoomScene";
import { NexusManager } from "@/game/systems/NexusManager";
import type { AgentId, AgentLocation, CompanyScore, SceneId } from "@/types";

const SCORE_STYLE = {
  fontFamily: "monospace",
  fontSize: "6px",
  lineSpacing: 3,
  color: "#ff8c61",
  align: "left" as const,
};

function formatScore(score: CompanyScore): string {
  return [
    `Research   ${score.researchQuality.toFixed(0)}`,
    `Decisions  ${score.decisionQuality.toFixed(0)}`,
    `Risk       ${score.riskManagement.toFixed(0)}`,
    `Paper P&L  ${score.paperTradingPerformance.toFixed(0)}`,
    `Teamwork   ${score.teamCoordination.toFixed(0)}`,
    `Knowledge  ${score.knowledgeGrowth.toFixed(0)}`,
    `Simulation ${score.simulationSuccess.toFixed(0)}`,
  ].join("\n");
}

function formatOverall(score: CompanyScore): string {
  return `OVERALL: ${score.overall.toFixed(0)}/100`;
}

/**
 * The Performance Center — Coach's home office (v0.5 brief, Feature 1).
 * The scoreboard mirrors the same seven CompanyScore metrics shown in the
 * Brain Room HUD (see backend/app/company_score.py); the full weekly/
 * monthly report with agent rankings and recommendations lives in the
 * Coach Dashboard React overlay, opened from the toolbar — this in-world
 * scoreboard is the at-a-glance version, the same relationship the Brain
 * Room's holographic core has to BrainRoomHud.
 */
export class PerformanceCenterScene extends RoomScene {
  protected sceneKey: SceneId = "PerformanceCenterScene";
  protected widthTiles = 15;
  protected heightTiles = 10;
  protected floorAsset = "tiles/water-tile";
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
    const cy = heightPx / 2 - 4;
    this.add.rectangle(cx, cy, 130, 100, 0x0b0b12).setStrokeStyle(2, 0xff8c61, 0.8).setDepth(2);
    this.add
      .text(cx, cy - 42, "COMPANY SCOREBOARD", { fontFamily: "monospace", fontSize: "6px", color: "#f4e6c9" })
      .setOrigin(0.5)
      .setDepth(3);
    this.addLiveText("companyScore:updated", cx, cy - 30, { ...SCORE_STYLE, align: "center" }, formatOverall, NexusManager.getCompanyScore());
    this.addLiveText("companyScore:updated", cx - 24, cy + 8, SCORE_STYLE, formatScore, NexusManager.getCompanyScore());
  }

  private buildDesk(widthPx: number, heightPx: number): void {
    const dx = widthPx / 2;
    const dy = heightPx - 22;
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
    // The scoreboard occupies the room's center — spawn agents in front of
    // the desk instead, the same way BrainRoomScene keeps agents clear of
    // its holographic core.
    const spacing = 30;
    const offset = (index - (total - 1) / 2) * spacing;
    return { x: widthPx / 2 + offset, y: heightPx - 34 };
  }
}
