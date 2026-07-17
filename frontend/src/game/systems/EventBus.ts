import Phaser from "phaser";
import type {
  AgentId,
  AgentState,
  DialogueHistoryEntry,
  GameSaveState,
  MeetingState,
  NewsItem,
  SceneId,
  SettingsState,
  Task,
  TimeState,
} from "@/types";

/** Every event the game emits, keyed by name, with its payload type. */
export interface GameEvents {
  "scene:ready": { scene: string };
  "scene:transition": { to: string };
  "player:move": { x: number; y: number };
  "room:entered": { scene: SceneId };
  "room:left": { scene: SceneId };
  "agent:updated": { id: AgentId; state: AgentState };
  "agent:interact": { id: AgentId; transform: AgentState["transform"] };
  "dialogue:open": { lines: string[]; speaker: string };
  "dialogue:line": DialogueHistoryEntry;
  "dialogue:close": undefined;
  "time:tick": TimeState;
  "settings:changed": SettingsState;
  "save:started": undefined;
  "save:completed": { at: string };
  "save:failed": { error: string };
  "load:completed": GameSaveState;
  "ui:pause": { paused: boolean };
  "ui:settings": { open: boolean };
  "ui:newspaper": { open: boolean };
  "net:status": { connected: boolean };
  "task:assigned": Task;
  "task:completed": Task;
  "whiteboard:updated": { boardId: string; text: string };
  "meeting:started": MeetingState;
  "meeting:ended": undefined;
  "news:updated": NewsItem[];
}

type Handler<K extends keyof GameEvents> = (payload: GameEvents[K]) => void;

/**
 * Central pub/sub bus decoupling Phaser scenes, React UI, and the network
 * layer. Built on Phaser's EventEmitter since Phaser is already a
 * dependency; used as a plain singleton so React code doesn't need to know
 * about the Phaser.Game instance to listen for game events.
 */
class TypedEventBus {
  private emitter = new Phaser.Events.EventEmitter();

  on<K extends keyof GameEvents>(event: K, handler: Handler<K>): () => void {
    this.emitter.on(event, handler as (...args: unknown[]) => void);
    return () => this.emitter.off(event, handler as (...args: unknown[]) => void);
  }

  once<K extends keyof GameEvents>(event: K, handler: Handler<K>): void {
    this.emitter.once(event, handler as (...args: unknown[]) => void);
  }

  off<K extends keyof GameEvents>(event: K, handler: Handler<K>): void {
    this.emitter.off(event, handler as (...args: unknown[]) => void);
  }

  emit<K extends keyof GameEvents>(event: K, payload: GameEvents[K]): void {
    this.emitter.emit(event, payload);
  }

  removeAllListeners(): void {
    this.emitter.removeAllListeners();
  }
}

export const EventBus = new TypedEventBus();
