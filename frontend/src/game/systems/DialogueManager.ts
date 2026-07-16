import type { DialogueHistoryEntry, ScoutState } from "@/types";
import { EventBus } from "./EventBus";

/** Flavor lines Scout can say, selected by his current task/mood/energy band. */
const TASK_LINES: Record<string, string[]> = {
  "Scanning market news": [
    "Cross-referencing three wire feeds for anything that moves the tape.",
    "Nothing alpha-worthy yet, but I've flagged two headlines for the CEO.",
  ],
  "Building a research memo": [
    "Drafting a memo on sector rotation. Give me another hour.",
    "I keep rewriting the summary — I want it tight before it reaches your desk.",
  ],
  "Back-testing a strategy": [
    "Running the strategy against five years of data. Sharpe ratio's looking decent.",
    "Back-test's still crunching. The Brain Room fans are earning their keep today.",
  ],
  "Reviewing overnight positions": [
    "Overnight book looks clean. No surprises while you were away.",
    "One position drifted past its band — I noted it for review.",
  ],
  Resting: [
    "Taking five. Even research analysts need a coffee.",
    "Recharging. I'll be sharper in a few minutes.",
  ],
};

const MOOD_FLAVOR = {
  low: ["Honestly, I'm a little burnt out.", "It's been a long stretch of research."],
  neutral: ["Steady as always.", "Nothing to report, just heads-down work."],
  high: ["Feeling great about today's findings!", "This is exactly the kind of work I enjoy."],
};

const GREETINGS = ["Hey, boss.", "Oh — good timing.", "Welcome back to the office."];

export interface DialogueSession {
  speaker: string;
  lines: string[];
}

/** Owns Scout's dialogue content, opens/advances conversations, and records history. */
export class DialogueManager {
  private history: DialogueHistoryEntry[] = [];

  loadHistory(entries: DialogueHistoryEntry[]): void {
    this.history = entries;
  }

  getHistory(): DialogueHistoryEntry[] {
    return this.history;
  }

  startScoutConversation(scout: ScoutState): DialogueSession {
    const greeting = pick(GREETINGS);
    const taskLines = TASK_LINES[scout.currentTask] ?? [
      `I'm currently focused on: ${scout.currentTask}.`,
    ];
    const moodBand = scout.mood < 35 ? "low" : scout.mood > 70 ? "high" : "neutral";
    const moodLine = pick(MOOD_FLAVOR[moodBand]);

    const lines = [greeting, pick(taskLines), moodLine];
    this.recordLines(lines);
    EventBus.emit("dialogue:open", { lines, speaker: "Scout" });
    return { speaker: "Scout", lines };
  }

  close(): void {
    EventBus.emit("dialogue:close", undefined);
  }

  private recordLines(lines: string[]): void {
    for (const line of lines) {
      const entry: DialogueHistoryEntry = {
        id: crypto.randomUUID(),
        speaker: "scout",
        line,
        timestamp: new Date().toISOString(),
      };
      this.history.push(entry);
      EventBus.emit("dialogue:line", entry);
    }
    // Cap history so saves don't grow unbounded.
    if (this.history.length > 200) {
      this.history = this.history.slice(-200);
    }
  }
}

function pick<T>(arr: T[]): T {
  const item = arr[Math.floor(Math.random() * arr.length)];
  if (item === undefined) {
    throw new Error("[DialogueManager] pick() called with an empty array");
  }
  return item;
}

export const dialogueManager = new DialogueManager();
