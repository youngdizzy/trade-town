import type { AgentId, AgentState, MeetingMinutes, MeetingState, MemoryRecord, NewsItem, ResearchItem, Task, TimeState, WatchlistEntry } from "@/types";
import { EventBus } from "@/game/systems/EventBus";
import { TimeManager } from "@/game/systems/TimeManager";
import { NPCManager } from "@/game/systems/NPCManager";
import { NexusManager } from "@/game/systems/NexusManager";

type ServerMessage =
  | {
      type: "state";
      time: TimeState;
      agents: Record<AgentId, AgentState>;
      tasks: Task[];
      whiteboards: Record<string, string>;
      meeting: MeetingState;
      news: NewsItem[];
      research: ResearchItem[];
      watchlist: WatchlistEntry[];
      memory: MemoryRecord[];
      meetingMinutes: MeetingMinutes[];
    }
  | { type: "pong" };

function resolveWsUrl(): string {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws`;
}

/**
 * Maintains a live WebSocket connection to the backend simulation loop.
 * The backend keeps ticking Scout's research/schedule even when no client
 * is connected; this socket is what makes the office feel "alive" by
 * streaming those updates instead of requiring the client to poll.
 * Falls back to local simulation (NPCManager/TimeManager offline mode) if
 * the connection can't be established, with exponential backoff retries.
 */
export class GameSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempt = 0;
  private reconnectTimer: number | null = null;
  private closedByClient = false;

  connect(): void {
    this.closedByClient = false;
    this.open();
  }

  disconnect(): void {
    this.closedByClient = true;
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  private open(): void {
    const url = resolveWsUrl();
    const ws = new WebSocket(url);
    this.ws = ws;

    ws.onopen = () => {
      this.reconnectAttempt = 0;
      EventBus.emit("net:status", { connected: true });
      TimeManager.stopLocalFallback();
      NPCManager.stopOfflineFallback();
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string) as ServerMessage;
        if (msg.type === "state") {
          TimeManager.setFromServer(msg.time);
          NPCManager.applyServerUpdate(msg.agents);
          NexusManager.applyServerUpdate({
            tasks: msg.tasks,
            whiteboards: msg.whiteboards,
            meeting: msg.meeting,
            news: msg.news,
            research: msg.research,
            watchlist: msg.watchlist,
            memory: msg.memory,
            meetingMinutes: msg.meetingMinutes,
          });
        }
      } catch (err) {
        console.warn("[GameSocket] Failed to parse message", err);
      }
    };

    ws.onclose = () => {
      EventBus.emit("net:status", { connected: false });
      TimeManager.startLocalFallback();
      NPCManager.startOfflineFallback(() => TimeManager.current);
      if (!this.closedByClient) this.scheduleReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };
  }

  private scheduleReconnect(): void {
    this.reconnectAttempt += 1;
    const delay = Math.min(1000 * 2 ** this.reconnectAttempt, 15000);
    this.reconnectTimer = window.setTimeout(() => this.open(), delay);
  }
}

export const gameSocket = new GameSocket();
