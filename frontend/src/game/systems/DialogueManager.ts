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
  coach: {
    "Reviewing yesterday's paper trades": ["Going through yesterday's paper trades — a couple worth discussing at the review."],
    "Observing research in progress": ["Sitting in on research this morning. Just watching, not interrupting."],
    "Analyzing confidence calibration": ["Checking whether confidence scores actually track outcomes. It's close, not perfect."],
    "Reviewing simulation results": ["The Simulation Lab's latest run is in. Promising, but I want more data."],
    "Evening performance review": ["Wrapping up today's performance review. Nothing that surprises me."],
    "Drafting recommendations": ["Drafting a couple of recommendations for the team. Nothing harsh, just honest."],
    "Standing by": ["Standing by. Always happy to talk through a trade after the fact."],
  },
  sentinel: {
    "Reviewing overnight risk exposure": ["Checking what the book looked like while nobody was watching. Clean so far."],
    "Monitoring position sizing": ["Every open position gets measured against the limits. No exceptions."],
    "Evaluating trade candidates": ["A candidate just came through voting. I'll say no if the sizing's off."],
    "Cross-checking risk against Coach's reports": ["Comparing my numbers against Coach's review. We usually agree."],
    "Setting tomorrow's risk limits": ["Tightening a limit for tomorrow. Today taught us something."],
    "Auditing the day's approvals": ["Going back through everything I approved today. Show your work."],
    "Standing watch": ["Someone has to say no. Might as well be me."],
  },
  pulse: {
    "Scanning premarket movers": ["Premarket's already moving. I've got eyes on four symbols."],
    "Watching for breakouts": ["Watching for a real breakout, not just noise. Volume tells the story."],
    "Tracking volume spikes": ["Something just spiked. Checking if it's real or a fluke."],
    "Cross-referencing research with scanner alerts": ["Lining up my alerts against what research already flagged."],
    "Scanning after-hours activity": ["After-hours is thin, but thin doesn't mean nothing's happening."],
    "Compiling the day's alerts": ["Wrapping today's alerts into a summary for the morning."],
    "Monitoring overnight volatility": ["Volatility never fully sleeps. Neither do I, apparently."],
  },
  guardian: {
    "Checking overnight portfolio exposure": ["Exposure held steady overnight. Nothing to flag yet."],
    "Monitoring concentration risk": ["One symbol's creeping up as a share of the book. Watching it."],
    "Watching drawdown levels": ["Drawdown's within bounds, but I don't like getting close to the line."],
    "Reviewing portfolio performance": ["Reviewing how the portfolio's actually performing against the risk we took."],
    "Recommending risk reductions": ["I recommended trimming a position today. Sentinel agreed."],
    "Filing the day's exposure report": ["Filing today's exposure report. Everything's accounted for."],
    "Standing watch over the book": ["Someone has to watch the whole book, not just one trade at a time."],
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
  coach: ["Got a minute for a quick review?", "Hey, boss — good timing.", "Let's talk performance."],
  sentinel: ["Boss.", "Before you ask — yes, I already checked.", "What's the risk question this time?"],
  pulse: ["Boss! Good, you're here.", "Four alerts since you last checked in.", "Hey — you're just in time."],
  guardian: ["Checking in on exposure?", "Boss. The book's in good shape.", "Good timing — I just finished a pass."],
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
