import { RoomScene } from "./RoomScene";
import { EventBus } from "@/game/systems/EventBus";
import { NexusManager } from "@/game/systems/NexusManager";
import type { AcademyState, AgentId, AgentLocation, CompanyHealth, CompanyScore, ExecutiveReview, MarketEnvironmentState, SceneId } from "@/types";

const BODY_STYLE = { fontFamily: "monospace", fontSize: "6px", color: "#f4e6c9", align: "left" as const, lineSpacing: 3, resolution: 4 };
const DIM_STYLE = { fontFamily: "monospace", fontSize: "6px", color: "#8a8a9a", align: "left" as const, lineSpacing: 3, resolution: 4 };

function formatMarketDisplay(env: MarketEnvironmentState): string {
  return `WORLD MARKET DISPLAY\n\n${env.label}\n${env.detail}`;
}

function formatStatusWall(health: CompanyHealth): string {
  return [
    "DEPARTMENT STATUS WALL",
    "",
    `Overall ${health.overall.toFixed(0)} (${health.tier.replace("_", " ").toUpperCase()})`,
    `Stability ${health.operationalStability.toFixed(0)}  Efficiency ${health.departmentEfficiency.toFixed(0)}`,
    `Morale ${health.employeeMorale.toFixed(0)}  Research ${health.researchProgress.toFixed(0)}`,
  ].join("\n");
}

function formatPerformanceOverview(score: CompanyScore): string {
  return [
    "DEPARTMENT PERFORMANCE OVERVIEW",
    "",
    `Research ${score.researchQuality.toFixed(0)}  Decisions ${score.decisionQuality.toFixed(0)}  Risk ${score.riskManagement.toFixed(0)}`,
    `Paper P&L ${score.paperTradingPerformance.toFixed(0)}  Teamwork ${score.teamCoordination.toFixed(0)}  Sim ${score.simulationSuccess.toFixed(0)}`,
  ].join("\n");
}

function formatBriefing(reviews: ExecutiveReview[]): string {
  const latest = reviews[reviews.length - 1];
  if (!latest) return "EXECUTIVE BRIEFING\n\nNo Executive Review yet — the first arrives at month's end.";
  const connection = latest.knowledgeConnections[0];
  const body = connection ? `${latest.summary}\n\n${connection}` : latest.summary;
  return `EXECUTIVE BRIEFING\n\n${body}`;
}

function formatTimeline(reviews: ExecutiveReview[]): string {
  const lines =
    reviews.length === 0
      ? ["No prior reviews on file."]
      : [...reviews]
          .reverse()
          .slice(0, 3)
          .map((r) => `${r.companyScore.toFixed(0)}/100 (${r.companyScoreChange >= 0 ? "+" : ""}${r.companyScoreChange.toFixed(1)}) — ${r.researchCompleted} research`);
  return ["COMPANY TIMELINE / REPORT ARCHIVE", "", ...lines].join("\n");
}

function formatObjectives(reviews: ExecutiveReview[], academy: AcademyState): string {
  const latest = reviews[reviews.length - 1];
  const goals = latest?.longTermGoals ?? ["No standing goals yet — set after the first Executive Review."];
  return ["CURRENT OBJECTIVES", "", ...goals.slice(0, 2), `Academy: Level ${academy.level} — ${academy.levelLabel}`].join("\n");
}

/**
 * The Executive Boardroom — v0.7 Feature 24, Meridian (the CIO)'s home
 * office and the room housing the Monthly Executive Review. Every
 * readout here is a real, already-computed backend value (companyHealth,
 * companyScore, marketEnvironment, the executiveReviews history) — the
 * same "in-world at-a-glance" pattern the Trading Floor's ticker and the
 * Performance Center's scoreboard already establish, not a duplicate
 * detail view (there is deliberately no dedicated Command Center tab for
 * Executive Reviews — this room is the one place to read them, matching
 * the brief's "the player can enter the room at any time").
 *
 * Sized larger than most rooms (34x22 tiles, vs. Trading Floor's 22x15)
 * specifically because it hosts six separate live readouts rather than
 * two or three — an early pass at Trading-Floor scale produced
 * overlapping, edge-clipped panels once real content was on screen.
 */
export class ExecutiveBoardroomScene extends RoomScene {
  protected sceneKey: SceneId = "ExecutiveBoardroomScene";
  protected widthTiles = 34;
  protected heightTiles = 22;
  protected floorAsset = "tilesets/cliff-tile";
  protected roomLabel = "Executive Boardroom";
  protected agentLocation: AgentLocation | null = "executive-boardroom";

  constructor() {
    super("ExecutiveBoardroomScene");
  }

  protected onBuild(widthPx: number, heightPx: number): void {
    this.add.rectangle(widthPx / 2, heightPx / 2, widthPx, heightPx, 0x0c0f1a, 0.5).setDepth(1);

    const cx = widthPx / 2;
    // Row 1 — three displays across the top, evenly spaced with margin.
    const row1Y = 58;
    const colWidth = 165;
    const col1X = 12 + colWidth / 2;
    const col2X = cx;
    const col3X = widthPx - 12 - colWidth / 2;

    this.add.rectangle(col1X, row1Y, colWidth, 68, 0x0b0b12).setStrokeStyle(1, 0x4fd8ff, 0.65).setDepth(2);
    this.addLiveText("marketEnvironment:updated", col1X, row1Y, { ...BODY_STYLE, wordWrap: { width: colWidth - 16 } }, formatMarketDisplay, NexusManager.getMarketEnvironment());

    this.add.rectangle(col2X, row1Y, colWidth, 68, 0x0b0b12).setStrokeStyle(1, 0xff8c61, 0.65).setDepth(2);
    this.addLiveText("companyScore:updated", col2X, row1Y, { ...BODY_STYLE, wordWrap: { width: colWidth - 16 } }, formatPerformanceOverview, NexusManager.getCompanyScore());

    this.add.rectangle(col3X, row1Y, colWidth, 68, 0x0b0b12).setStrokeStyle(1, 0x8fe3b0, 0.65).setDepth(2);
    this.addLiveText("companyHealth:updated", col3X, row1Y, { ...BODY_STYLE, wordWrap: { width: colWidth - 16 } }, formatStatusWall, NexusManager.getCompanyHealth());

    // Row 2 — the strategy table, centered in the remaining floor space.
    this.buildStrategyTable(cx, heightPx / 2 - 20);

    // Row 3 — the briefing screen (left, wider for paragraph text) and a
    // stacked timeline/objectives column (right).
    const row3Y = heightPx - 90;
    this.buildBriefingScreen(12 + 220 / 2, row3Y, 220, 100);
    this.buildTimelineAndObjectives(widthPx - 12 - 230 / 2, row3Y, 230);
  }

  /** The large interactive strategy table — flavor centerpiece the rest of the room's displays surround. */
  private buildStrategyTable(cx: number, cy: number): void {
    this.add.ellipse(cx, cy, 130, 52, 0x1a1f2e).setStrokeStyle(1, 0xd4af37, 0.6).setDepth(2);
    this.add.ellipse(cx, cy, 108, 36, 0x0e1220).setStrokeStyle(1, 0x4fd8ff, 0.35).setDepth(3);
    const glow = this.add.circle(cx, cy, 3, 0xd4af37, 0.8).setDepth(4);
    this.tweens.add({ targets: glow, scale: { from: 0.8, to: 1.8 }, alpha: { from: 0.8, to: 0.15 }, duration: 1600, repeat: -1, ease: "Sine.easeOut" });
  }

  private buildBriefingScreen(x: number, y: number, w: number, h: number): void {
    this.add.rectangle(x, y, w, h, 0x0b0b12).setStrokeStyle(1, 0xd4af37, 0.7).setDepth(2);
    this.addLiveText("executiveReviews:updated", x, y, { ...BODY_STYLE, color: "#f4e6c9", wordWrap: { width: w - 16 } }, formatBriefing, NexusManager.getExecutiveReviews());
  }

  private buildTimelineAndObjectives(x: number, y: number, w: number): void {
    const timelineY = y - 27;
    const objectivesY = y + 33;
    this.add.rectangle(x, timelineY, w, 54, 0x0b0b12).setStrokeStyle(1, 0xb388ff, 0.6).setDepth(2);
    this.addLiveText("executiveReviews:updated", x, timelineY, { ...DIM_STYLE, wordWrap: { width: w - 16 } }, formatTimeline, NexusManager.getExecutiveReviews());

    this.add.rectangle(x, objectivesY, w, 44, 0x0b0b12).setStrokeStyle(1, 0xff8c61, 0.6).setDepth(2);
    // Depends on both executiveReviews (long-term goals) and academyState
    // (the Academy level line) — addLiveText only tracks one event, so
    // this one readout self-manages both subscriptions directly.
    const objectivesText = this.add
      .text(x, objectivesY, formatObjectives(NexusManager.getExecutiveReviews(), NexusManager.getAcademyState()), { ...DIM_STYLE, wordWrap: { width: w - 16 } })
      .setOrigin(0.5)
      .setDepth(4);
    const refreshObjectives = () => objectivesText.setText(formatObjectives(NexusManager.getExecutiveReviews(), NexusManager.getAcademyState()));
    const unsubReviews = EventBus.on("executiveReviews:updated", refreshObjectives);
    const unsubAcademy = EventBus.on("academyState:updated", refreshObjectives);
    this.events.once("shutdown", () => {
      unsubReviews();
      unsubAcademy();
    });
  }

  protected override getAgentSpawnPoint(
    agentId: AgentId,
    index: number,
    total: number,
    widthPx: number,
    heightPx: number,
  ): { x: number; y: number } {
    if (agentId === "cio") return { x: widthPx / 2, y: heightPx / 2 + 44 };
    const spacing = 34;
    const offset = (index - (total - 1) / 2) * spacing;
    return { x: widthPx / 2 + offset, y: heightPx / 2 + 44 + 20 };
  }
}
