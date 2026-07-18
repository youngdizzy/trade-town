import type {
  BacktestSession,
  CoachReport,
  CompanyScore,
  HallOfFameEntry,
  MeetingMinutes,
  MeetingState,
  MemoryRecord,
  NewsItem,
  PaperPortfolio,
  PerformanceSnapshot,
  ResearchItem,
  RiskLimits,
  RiskWarning,
  ScannerAlert,
  SimulationResult,
  Strategy,
  Task,
  TradeDecision,
  WatchlistEntry,
} from "@/types";
import { EventBus } from "./EventBus";

interface NexusSnapshot {
  tasks: Task[];
  whiteboards: Record<string, string>;
  meeting: MeetingState;
  news: NewsItem[];
  research: ResearchItem[];
  watchlist: WatchlistEntry[];
  memory: MemoryRecord[];
  meetingMinutes: MeetingMinutes[];
  paperPortfolio: PaperPortfolio;
  strategies: Strategy[];
  backtestSessions: BacktestSession[];
  simulationResults: SimulationResult[];
  hallOfFame: HallOfFameEntry[];
  coachReports: CoachReport[];
  companyScore: CompanyScore;
  performanceSnapshots: PerformanceSnapshot[];
  riskLimits: RiskLimits;
  riskWarnings: RiskWarning[];
  scannerAlerts: ScannerAlert[];
  decisions: TradeDecision[];
}

/**
 * Frontend mirror of the backend's NexusManager — holds the company-wide
 * state (tasks, whiteboards, meeting status, news feed, research queue,
 * watchlist, company memory, meeting minutes) that isn't tied to any
 * single agent. Diffs incoming server snapshots against the previous one
 * to emit the discrete events other systems (UI, dialogue) care about,
 * the same way NPCManager does per-agent.
 */
export class NexusManager {
  private static tasks: Task[] = [];
  private static whiteboards: Record<string, string> = {};
  private static meeting: MeetingState = { active: false, participants: [], discussion: [] };
  private static news: NewsItem[] = [];
  private static research: ResearchItem[] = [];
  private static watchlist: WatchlistEntry[] = [];
  private static memory: MemoryRecord[] = [];
  private static meetingMinutes: MeetingMinutes[] = [];
  private static paperPortfolio: PaperPortfolio = {
    cashBalance: 100_000,
    startingBalance: 100_000,
    positions: [],
    orders: [],
    tradeHistory: [],
    totalPnl: 0,
    totalPnlPct: 0,
    winCount: 0,
    lossCount: 0,
  };
  private static strategies: Strategy[] = [];
  private static backtestSessions: BacktestSession[] = [];
  private static simulationResults: SimulationResult[] = [];
  private static hallOfFame: HallOfFameEntry[] = [];
  private static coachReports: CoachReport[] = [];
  private static companyScore: CompanyScore = {
    overall: 50,
    researchQuality: 50,
    decisionQuality: 50,
    riskManagement: 50,
    paperTradingPerformance: 50,
    teamCoordination: 50,
    knowledgeGrowth: 0,
    simulationSuccess: 50,
    updatedAt: new Date().toISOString(),
  };
  private static performanceSnapshots: PerformanceSnapshot[] = [];
  private static riskLimits: RiskLimits = {
    maxPositionPct: 10,
    maxDailyLossPct: 5,
    maxDrawdownPct: 20,
    maxOpenPositions: 8,
    maxSectorConcentrationPct: 30,
    riskPerTradePct: 2,
  };
  private static riskWarnings: RiskWarning[] = [];
  private static scannerAlerts: ScannerAlert[] = [];
  private static decisions: TradeDecision[] = [];

  static getTasks(): Task[] {
    return this.tasks;
  }

  static getWhiteboard(boardId: string): string {
    return this.whiteboards[boardId] ?? "";
  }

  static getAllWhiteboards(): Record<string, string> {
    return this.whiteboards;
  }

  static getMeeting(): MeetingState {
    return this.meeting;
  }

  static getNews(): NewsItem[] {
    return this.news;
  }

  static getResearch(): ResearchItem[] {
    return this.research;
  }

  static getWatchlist(): WatchlistEntry[] {
    return this.watchlist;
  }

  static getMemory(): MemoryRecord[] {
    return this.memory;
  }

  static getMeetingMinutes(): MeetingMinutes[] {
    return this.meetingMinutes;
  }

  static getPaperPortfolio(): PaperPortfolio {
    return this.paperPortfolio;
  }

  static getStrategies(): Strategy[] {
    return this.strategies;
  }

  static getBacktestSessions(): BacktestSession[] {
    return this.backtestSessions;
  }

  static getSimulationResults(): SimulationResult[] {
    return this.simulationResults;
  }

  static getHallOfFame(): HallOfFameEntry[] {
    return this.hallOfFame;
  }

  static getCoachReports(): CoachReport[] {
    return this.coachReports;
  }

  static getCompanyScore(): CompanyScore {
    return this.companyScore;
  }

  static getPerformanceSnapshots(): PerformanceSnapshot[] {
    return this.performanceSnapshots;
  }

  static getRiskLimits(): RiskLimits {
    return this.riskLimits;
  }

  static getRiskWarnings(): RiskWarning[] {
    return this.riskWarnings;
  }

  static getScannerAlerts(): ScannerAlert[] {
    return this.scannerAlerts;
  }

  static getDecisions(): TradeDecision[] {
    return this.decisions;
  }

  static applyServerUpdate(update: NexusSnapshot): void {
    for (const task of update.tasks) {
      const previous = this.tasks.find((t) => t.id === task.id);
      if (!previous) EventBus.emit("task:assigned", task);
      else if (previous.status !== "completed" && task.status === "completed") EventBus.emit("task:completed", task);
    }
    this.tasks = update.tasks;

    for (const [boardId, text] of Object.entries(update.whiteboards)) {
      if (this.whiteboards[boardId] !== text) EventBus.emit("whiteboard:updated", { boardId, text });
    }
    this.whiteboards = update.whiteboards;

    if (!this.meeting.active && update.meeting.active) EventBus.emit("meeting:started", update.meeting);
    else if (this.meeting.active && !update.meeting.active) EventBus.emit("meeting:ended", undefined);
    this.meeting = update.meeting;

    if (update.news.length !== this.news.length) EventBus.emit("news:updated", update.news);
    this.news = update.news;

    for (const item of update.research) {
      const previous = this.research.find((r) => r.id === item.id);
      if (previous && previous.status !== "completed" && item.status === "completed") {
        EventBus.emit("research:completed", item);
      }
    }
    if (update.research !== this.research) EventBus.emit("research:updated", update.research);
    this.research = update.research;

    if (update.watchlist !== this.watchlist) EventBus.emit("watchlist:updated", update.watchlist);
    this.watchlist = update.watchlist;

    if (update.memory.length !== this.memory.length) EventBus.emit("memory:updated", update.memory);
    this.memory = update.memory;

    if (update.meetingMinutes.length !== this.meetingMinutes.length) {
      const newest = update.meetingMinutes[update.meetingMinutes.length - 1];
      if (newest) EventBus.emit("meeting:minutesRecorded", newest);
    }
    this.meetingMinutes = update.meetingMinutes;

    if (update.paperPortfolio !== this.paperPortfolio) EventBus.emit("portfolio:updated", update.paperPortfolio);
    this.paperPortfolio = update.paperPortfolio;

    if (update.strategies !== this.strategies) EventBus.emit("strategies:updated", update.strategies);
    this.strategies = update.strategies;

    if (update.simulationResults.length !== this.simulationResults.length) {
      const newest = update.simulationResults[update.simulationResults.length - 1];
      if (newest) EventBus.emit("simulation:completed", newest);
    }
    if (update.backtestSessions !== this.backtestSessions || update.simulationResults !== this.simulationResults) {
      EventBus.emit("simulation:updated", { sessions: update.backtestSessions, results: update.simulationResults });
    }
    this.backtestSessions = update.backtestSessions;
    this.simulationResults = update.simulationResults;

    if (update.hallOfFame.length !== this.hallOfFame.length) {
      const newest = update.hallOfFame[update.hallOfFame.length - 1];
      if (newest) EventBus.emit("hallOfFame:entryAdded", newest);
      EventBus.emit("hallOfFame:updated", update.hallOfFame);
    }
    this.hallOfFame = update.hallOfFame;

    if (update.coachReports.length !== this.coachReports.length) {
      const newest = update.coachReports[update.coachReports.length - 1];
      this.coachReports = update.coachReports;
      if (newest) EventBus.emit("coach:reportReceived", newest);
      EventBus.emit("coachReports:updated", update.coachReports);
    } else {
      this.coachReports = update.coachReports;
    }

    if (update.companyScore !== this.companyScore) EventBus.emit("companyScore:updated", update.companyScore);
    this.companyScore = update.companyScore;

    if (update.performanceSnapshots !== this.performanceSnapshots) EventBus.emit("performanceSnapshots:updated", update.performanceSnapshots);
    this.performanceSnapshots = update.performanceSnapshots;

    if (update.riskLimits !== this.riskLimits) EventBus.emit("riskLimits:updated", update.riskLimits);
    this.riskLimits = update.riskLimits;

    if (update.riskWarnings !== this.riskWarnings) EventBus.emit("riskWarnings:updated", update.riskWarnings);
    this.riskWarnings = update.riskWarnings;

    if (update.scannerAlerts.length !== this.scannerAlerts.length) {
      const newest = update.scannerAlerts[update.scannerAlerts.length - 1];
      if (newest) EventBus.emit("scanner:alertDetected", newest);
      EventBus.emit("scannerAlerts:updated", update.scannerAlerts);
    }
    this.scannerAlerts = update.scannerAlerts;

    if (update.decisions.length !== this.decisions.length) {
      const newest = update.decisions[update.decisions.length - 1];
      if (newest) EventBus.emit("decision:made", newest);
      EventBus.emit("decisions:updated", update.decisions);
    }
    this.decisions = update.decisions;
  }

  static loadFromSave(save: NexusSnapshot): void {
    this.tasks = save.tasks;
    this.whiteboards = save.whiteboards;
    this.meeting = save.meeting;
    this.news = save.news;
    this.research = save.research;
    this.watchlist = save.watchlist;
    this.memory = save.memory;
    this.meetingMinutes = save.meetingMinutes;
    this.paperPortfolio = save.paperPortfolio;
    this.strategies = save.strategies;
    this.backtestSessions = save.backtestSessions;
    this.simulationResults = save.simulationResults;
    this.hallOfFame = save.hallOfFame;
    this.coachReports = save.coachReports;
    this.companyScore = save.companyScore;
    this.performanceSnapshots = save.performanceSnapshots;
    this.riskLimits = save.riskLimits;
    this.riskWarnings = save.riskWarnings;
    this.scannerAlerts = save.scannerAlerts;
    this.decisions = save.decisions;
  }
}
