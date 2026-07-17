import type { AgentId, AgentState, DialogueHistoryEntry } from "@/types";
import { AGENT_PROFILES } from "./AgentProfiles";
import { EventBus } from "./EventBus";

/** Flavor lines per agent, selected by their current task. Falls back to a generic line if the task isn't recognized. */
const AGENT_TASK_LINES: Record<AgentId, Record<string, string[]>> = {
  scout: {
    "Scanning market news": [
      "Cross-referencing three wire feeds for anything that moves the tape.",
      "Nothing alpha-worthy yet, but I've flagged two headlines for the CEO.",
    ],
    "Building a research memo": [
      "Drafting a memo on sector rotation. Give me another hour.",
      "I keep rewriting the summary — I want it tight before it reaches your desk.",
    ],
    "Back-testing a strategy": [
      "Running a strategy against five years of data in the Brain Room.",
      "Back-test's still crunching. The fans are earning their keep today.",
    ],
    "Reviewing overnight positions": [
      "Overnight book looks clean. No surprises while you were away.",
      "One position drifted past its band — I noted it for review.",
    ],
  },
  atlas: {
    "Reviewing overnight strategy": ["Overnight strategy holds. No changes needed yet."],
    "Assessing agent performance": ["Watching how the team's doing. Numbers are steady."],
    "Weighing strategic options": ["Weighing a few options. Not ready to decide yet."],
    "Finalizing decisions": ["Decision's made. I'll brief the team shortly."],
    "Planning tomorrow's priorities": ["Tomorrow's priorities are mostly set."],
    "Reviewing the day": ["Reviewing how today went before I close out."],
    "Standing by": ["Standing by. Call if you need a decision."],
  },
  echo: {
    "Charting technical patterns": [
      "This chart's forming a pattern I want to watch for another hour.",
      "Technicals are lining up. Might be something here.",
    ],
    "Studying monitor feeds": ["Three feeds up at once — trying to catch the moment things shift."],
    "Tracking momentum indicators": ["Momentum's strengthening on this one. Worth flagging."],
    "Scanning overnight charts": ["Overnight charts look quiet, but I'm still scanning."],
    "Monitoring after-hours signals": ["After-hours is thin, but I don't like missing things."],
  },
  nova: {
    "Reading quarterly reports": ["This quarterly report has a footnote worth a second read."],
    "Summarizing research findings": ["Summarizing findings — trying to keep it readable, not just accurate."],
    "Cross-checking Scout's notes": ["Cross-checking Scout's notes against the filings. Mostly lines up."],
    "Reading overnight filings": ["A few overnight filings came in. Reading through them now."],
    "Reviewing archived reports": ["Going back through the archive for context on this one."],
  },
  scribe: {
    "Reviewing overnight logs": ["Reading through what happened while you were away. Nothing missed."],
    "Filing yesterday's minutes": ["Filing yesterday's meeting minutes. Everyone's on the record."],
    "Logging research updates": ["Writing up the latest research as it comes in."],
    "Cross-referencing the archive": ["Cross-referencing this against the archive for consistency."],
    "Indexing the day's discoveries": ["Indexing today's discoveries so they're easy to find later."],
    "Archiving overnight records": ["Archiving the overnight records. The log never sleeps."],
  },
};

/** Shared fallback lines for override-driven tasks (meetings/breaks), independent of agent personality. */
const OVERRIDE_LINES: Record<string, string[]> = {
  "In a meeting": ["Can this wait? We're mid-meeting.", "Good timing — we just wrapped up a point."],
  "Taking a break": ["Just grabbing a coffee. Back in a minute.", "Recharging. I'll be sharper shortly."],
  Resting: ["Taking five. Even AI needs a moment.", "Recharging. I'll be sharper in a few minutes."],
};

const MOOD_FLAVOR = {
  low: ["Honestly, I'm a little burnt out.", "It's been a long stretch of work."],
  neutral: ["Steady as always.", "Nothing to report, just heads-down work."],
  high: ["Feeling great about today's progress!", "This is exactly the kind of work I enjoy."],
};

const AGENT_GREETINGS: Record<AgentId, string[]> = {
  scout: ["Hey, boss.", "Oh — good timing.", "Welcome back to the office."],
  atlas: ["Boss.", "Good to see you.", "What's on your mind?"],
  echo: ["Oh, hey!", "Check this chart out — actually, what's up?", "Perfect timing."],
  nova: ["Hi there.", "One second... okay, hi.", "Good timing, I just finished a section."],
  scribe: ["Everything's on the record.", "Ah, boss. I was just writing you in.", "One moment — let me finish this line."],
};

export interface DialogueSession {
  speaker: string;
  lines: string[];
}

/** Owns every agent's dialogue content, opens/advances conversations, and records history. */
export class DialogueManager {
  private history: DialogueHistoryEntry[] = [];

  loadHistory(entries: DialogueHistoryEntry[]): void {
    this.history = entries;
  }

  getHistory(): DialogueHistoryEntry[] {
    return this.history;
  }

  startConversation(agentId: AgentId, agent: AgentState): DialogueSession {
    const profile = AGENT_PROFILES[agentId];
    const greeting = pick(AGENT_GREETINGS[agentId]);
    const taskLines = AGENT_TASK_LINES[agentId][agent.currentTask] ?? OVERRIDE_LINES[agent.currentTask] ?? [
      `I'm currently focused on: ${agent.currentTask}.`,
    ];
    const moodBand = agent.mood < 35 ? "low" : agent.mood > 70 ? "high" : "neutral";
    const moodLine = pick(MOOD_FLAVOR[moodBand]);

    const lines = [greeting, pick(taskLines), moodLine];
    this.recordLines(agentId, lines);
    EventBus.emit("dialogue:open", { lines, speaker: profile.name });
    return { speaker: profile.name, lines };
  }

  close(): void {
    EventBus.emit("dialogue:close", undefined);
  }

  private recordLines(agentId: AgentId, lines: string[]): void {
    for (const line of lines) {
      const entry: DialogueHistoryEntry = {
        id: crypto.randomUUID(),
        speaker: agentId,
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
