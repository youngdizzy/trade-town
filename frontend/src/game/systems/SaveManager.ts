import type { GameSaveState } from "@/types";
import { api } from "@/net/api";
import { EventBus } from "./EventBus";
import { GameManager } from "./GameManager";
import { NPCManager } from "./NPCManager";
import { NexusManager } from "./NexusManager";
import { TimeManager } from "./TimeManager";
import { SettingsManager } from "./SettingsManager";
import { dialogueManager } from "./DialogueManager";

const LOCAL_BACKUP_KEY = "tradetown:save-backup";

/**
 * Collects a snapshot of the full game state and persists it via the
 * backend REST API, with a localStorage backup so a save is never lost if
 * the backend is briefly unreachable. Autosaves on an interval driven by
 * SettingsManager and exposes a manual save/load path for the UI buttons.
 */
export class SaveManager {
  private static autosaveHandle: number | null = null;

  static buildSnapshot(): GameSaveState {
    const game = GameManager.getInstance();
    return {
      version: "0.6",
      player: game?.playerTransform ?? { scene: "LobbyScene", x: 160, y: 160, facing: "down" },
      agents: NPCManager.getAllAgents(),
      tasks: NexusManager.getTasks(),
      whiteboards: NexusManager.getAllWhiteboards(),
      meeting: NexusManager.getMeeting(),
      news: NexusManager.getNews(),
      research: NexusManager.getResearch(),
      watchlist: NexusManager.getWatchlist(),
      memory: NexusManager.getMemory(),
      meetingMinutes: NexusManager.getMeetingMinutes(),
      paperPortfolio: NexusManager.getPaperPortfolio(),
      strategies: NexusManager.getStrategies(),
      backtestSessions: NexusManager.getBacktestSessions(),
      simulationResults: NexusManager.getSimulationResults(),
      hallOfFame: NexusManager.getHallOfFame(),
      coachReports: NexusManager.getCoachReports(),
      companyScore: NexusManager.getCompanyScore(),
      performanceSnapshots: NexusManager.getPerformanceSnapshots(),
      riskLimits: NexusManager.getRiskLimits(),
      riskWarnings: NexusManager.getRiskWarnings(),
      scannerAlerts: NexusManager.getScannerAlerts(),
      decisions: NexusManager.getDecisions(),
      tradeProposals: NexusManager.getTradeProposals(),
      ceoDecisions: NexusManager.getCeoDecisions(),
      debates: NexusManager.getDebates(),
      gatekeeperRejections: NexusManager.getGatekeeperRejections(),
      agentEnergy: NexusManager.getAgentEnergy(),
      signalCalibration: NexusManager.getSignalCalibration(),
      playerVsAi: NexusManager.getPlayerVsAi(),
      education: NexusManager.getEducation(),
      viewedTradeNotificationIds: NexusManager.getViewedTradeNotificationIds(),
      time: TimeManager.current,
      settings: SettingsManager.current,
      dialogueHistory: dialogueManager.getHistory(),
      updatedAt: new Date().toISOString(),
    };
  }

  static async save(): Promise<void> {
    const snapshot = this.buildSnapshot();
    EventBus.emit("save:started", undefined);
    try {
      localStorage.setItem(LOCAL_BACKUP_KEY, JSON.stringify(snapshot));
      const result = await api.saveGame(snapshot);
      EventBus.emit("save:completed", { at: result.updatedAt });
    } catch (err) {
      EventBus.emit("save:failed", { error: err instanceof Error ? err.message : String(err) });
    }
  }

  static async load(): Promise<GameSaveState> {
    try {
      const state = await api.loadGame();
      this.applyState(state);
      return state;
    } catch (err) {
      const backup = localStorage.getItem(LOCAL_BACKUP_KEY);
      if (backup) {
        const state = JSON.parse(backup) as GameSaveState;
        this.applyState(state);
        return state;
      }
      throw err;
    }
  }

  static applyState(state: GameSaveState): void {
    NPCManager.loadAgents(state.agents);
    NexusManager.loadFromSave(state);
    TimeManager.setFromServer(state.time);
    SettingsManager.update(state.settings);
    dialogueManager.loadHistory(state.dialogueHistory);
    GameManager.getInstance()?.applyLoadedTransform(state.player);
    EventBus.emit("load:completed", state);
  }

  static startAutosave(): void {
    this.stopAutosave();
    const intervalMs = SettingsManager.current.autosaveIntervalSec * 1000;
    this.autosaveHandle = window.setInterval(() => {
      void this.save();
    }, intervalMs);
  }

  static stopAutosave(): void {
    if (this.autosaveHandle !== null) {
      window.clearInterval(this.autosaveHandle);
      this.autosaveHandle = null;
    }
  }
}
