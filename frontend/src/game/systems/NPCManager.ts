import type { AgentId, AgentState, TimeState } from "@/types";
import { AGENT_IDS } from "@/types";
import { AGENT_PROFILES, LOCATION_TO_SCENE } from "./AgentProfiles";
import { scheduleBlockForHour } from "./Schedule";
import { EventBus } from "./EventBus";

function defaultAgentState(id: AgentId): AgentState {
  const profile = AGENT_PROFILES[id];
  const block = scheduleBlockForHour(id, 8);
  return {
    transform: { scene: LOCATION_TO_SCENE[profile.homeLocation], x: 100, y: 80, facing: "down" },
    location: profile.homeLocation,
    currentTask: block.task,
    mood: 65,
    energy: 80,
    memory: [],
    override: null,
  };
}

/**
 * Registry of NPC simulation state, keyed by agent id. Backend NEXUS is
 * authoritative; this mirrors whatever it last broadcast and falls back to
 * a local per-agent schedule simulation while offline.
 */
export class NPCManager {
  private static agents = new Map<AgentId, AgentState>(AGENT_IDS.map((id) => [id, defaultAgentState(id)]));
  private static offlineTickHandle: number | null = null;

  static getAgent(id: AgentId): AgentState {
    return this.agents.get(id)!;
  }

  static getAllAgents(): Record<AgentId, AgentState> {
    const result = {} as Record<AgentId, AgentState>;
    for (const id of AGENT_IDS) result[id] = this.agents.get(id)!;
    return result;
  }

  static setAgent(id: AgentId, state: AgentState): void {
    this.agents.set(id, state);
    EventBus.emit("agent:updated", { id, state });
  }

  /**
   * Applies a full agent-roster snapshot (WS tick or a loaded save) as one
   * atomic update. Previously this called setAgent() per agent, firing one
   * "agent:updated" event per id — gameStore's listener re-reads the whole
   * map on every fire (see gameStore.ts), so a mid-loop event exposed a
   * torn snapshot where only some agents reflected the new tick and the
   * rest were still last tick's values. Caught via a real gameplay
   * screenshot showing an agent's location and current-task text from two
   * different schedule blocks at once. The Map is now fully updated before
   * a single event fires, so every listener always sees a consistent
   * snapshot.
   */
  static loadAgents(states: Record<AgentId, AgentState>): void {
    let last: { id: AgentId; state: AgentState } | null = null;
    for (const id of AGENT_IDS) {
      if (!states[id]) continue;
      this.agents.set(id, states[id]);
      last = { id, state: states[id] };
    }
    if (last) EventBus.emit("agent:updated", last);
  }

  /** Applies an authoritative snapshot pushed from the backend over WebSocket. */
  static applyServerUpdate(states: Record<AgentId, AgentState>): void {
    this.loadAgents(states);
  }

  /** Local simulation fallback used only while disconnected from the backend. */
  static startOfflineFallback(getTime: () => TimeState): void {
    if (this.offlineTickHandle !== null) return;
    this.offlineTickHandle = window.setInterval(() => {
      const time = getTime();
      for (const id of AGENT_IDS) {
        const block = scheduleBlockForHour(id, time.hour);
        const current = this.getAgent(id);
        const next: AgentState = {
          ...current,
          location: block.location,
          currentTask: block.task,
          transform: { ...current.transform, scene: LOCATION_TO_SCENE[block.location] },
          energy: Math.max(10, Math.min(100, current.energy + (block.task === "Resting" ? 4 : -1))),
          mood: Math.max(10, Math.min(100, current.mood + (Math.random() > 0.5 ? 1 : -1))),
        };
        this.setAgent(id, next);
      }
    }, 5000);
  }

  static stopOfflineFallback(): void {
    if (this.offlineTickHandle !== null) {
      window.clearInterval(this.offlineTickHandle);
      this.offlineTickHandle = null;
    }
  }
}
