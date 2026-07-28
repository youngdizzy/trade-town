import type { AgentId, AgentState, DialogueHistoryEntry } from "@/types";
import { gameStore } from "@/state/gameStore";
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
    "Trading watchlist stories with whoever's around": ["Off the clock, but I still can't stop talking about tickers."],
    "Reading market history for fun": ["Reading about the '87 crash tonight. Old news, still good lessons."],
  },
  atlas: {
    "Reviewing overnight strategy": ["Overnight strategy holds. No changes needed yet."],
    "Assessing agent performance": ["Watching how the team's doing. Numbers are steady."],
    "Weighing strategic options": ["Weighing a few options. Not ready to decide yet."],
    "Finalizing decisions": ["Decision's made. I'll brief the team shortly."],
    "Reviewing the day one more time before letting it go": ["Even off the clock, I like to end the day with a clear head."],
    "Reading quietly": ["Not thinking about strategy right now. Just reading."],
  },
  echo: {
    "Charting technical patterns": [
      "This chart's forming a pattern I want to watch for another hour.",
      "Technicals are lining up. Might be something here.",
    ],
    "Studying monitor feeds": ["Three feeds up at once — trying to catch the moment things shift."],
    "Tracking momentum indicators": ["Momentum's strengthening on this one. Worth flagging."],
    "Watching an old chart pattern for fun, off the clock": ["Old habit — I still find these things beautiful, even off duty."],
    "Sketching new indicator ideas in a notebook": ["Sketching an idea I don't have data for yet. Just for me."],
  },
  nova: {
    "Reading quarterly reports": ["This quarterly report has a footnote worth a second read."],
    "Summarizing research findings": ["Summarizing findings — trying to keep it readable, not just accurate."],
    "Cross-checking Scout's notes": ["Cross-checking Scout's notes against the filings. Mostly lines up."],
    "Reading a novel, finally not about markets": ["Nice to read something without a single ticker symbol in it."],
    "Journaling a few thoughts from the day": ["Writing down what stuck with me today. Not for a report — just for me."],
  },
  scribe: {
    "Reviewing overnight logs": ["Reading through what happened while you were away. Nothing missed."],
    "Filing yesterday's minutes": ["Filing yesterday's meeting minutes. Everyone's on the record."],
    "Logging research updates": ["Writing up the latest research as it comes in."],
    "Cross-referencing the archive": ["Cross-referencing this against the archive for consistency."],
    "Writing in a personal journal, just for once": ["Some things don't belong in the company archive."],
    "Reading quietly": ["Everything else can wait until tomorrow."],
  },
  coach: {
    "Reviewing yesterday's paper trades": ["Going through yesterday's paper trades — a couple worth discussing at the review."],
    "Observing research in progress": ["Sitting in on research this morning. Just watching, not interrupting."],
    "Analyzing confidence calibration": ["Checking whether confidence scores actually track outcomes. It's close, not perfect."],
    "Reviewing simulation results": ["The Simulation Lab's latest run is in. Promising, but I want more data."],
    "Exercising to clear the mind": ["Working out clears my head better than any report does."],
    "Watching game film, but for fun this time": ["Watching old trades tonight — no notes, just enjoying the story."],
  },
  sentinel: {
    "Reviewing overnight risk exposure": ["Checking what the book looked like while nobody was watching. Clean so far."],
    "Monitoring position sizing": ["Every open position gets measured against the limits. No exceptions."],
    "Evaluating trade candidates": ["A candidate just came through voting. I'll say no if the sizing's off."],
    "Cross-checking risk against Coach's reports": ["Comparing my numbers against Coach's review. We usually agree."],
    "Finally letting the guard down for a few hours": ["Even I have to stop watching the exits eventually."],
    "Reading, off the clock": ["Reading something that isn't a risk report, for once."],
  },
  pulse: {
    "Scanning premarket movers": ["Premarket's already moving. I've got eyes on four symbols."],
    "Watching for breakouts": ["Watching for a real breakout, not just noise. Volume tells the story."],
    "Tracking volume spikes": ["Something just spiked. Checking if it's real or a fluke."],
    "Cross-referencing research with scanner alerts": ["Lining up my alerts against what research already flagged."],
    "Still glancing at a ticker out of habit": ["I told myself I'd stop checking. I haven't stopped checking."],
    "Playing a game to unwind": ["Trying to focus on something that isn't a chart for once."],
  },
  guardian: {
    "Checking overnight portfolio exposure": ["Exposure held steady overnight. Nothing to flag yet."],
    "Monitoring concentration risk": ["One symbol's creeping up as a share of the book. Watching it."],
    "Watching drawdown levels": ["Drawdown's within bounds, but I don't like getting close to the line."],
    "Reviewing portfolio performance": ["Reviewing how the portfolio's actually performing against the risk we took."],
    "Making sure everything is squared away before bed": ["Can't rest until everything's actually accounted for."],
    "Reading quietly": ["The one time of day nothing needs protecting."],
  },
  cio: {
    "Reviewing overnight department reports": [
      "Reading through what every department produced overnight. Steady work across the board.",
      "Nothing urgent in the overnight reports — a good sign, not a boring one.",
    ],
    "Sitting in on the research desk": ["Just observing today. The research desk does its best work when I stay quiet."],
    "Reviewing risk and execution together": ["Comparing Sentinel's read against what's actually being executed. They should always agree."],
    "Preparing the executive briefing": ["Drafting this month's briefing. I want it honest, not just optimistic."],
    "Reflecting on today's decisions, off the clock": ["Not reviewing anyone — just sitting with how today actually went."],
    "Reading, away from the boardroom": ["Away from the boardroom, I'm just reading. It's a relief, honestly."],
  },
  sage: {
    "Writing today's question": ["Still deciding what to ask everyone this morning. The right question matters more than any answer."],
    "Listening in on the research desk": ["I'm not here to check their work. I'm here to ask what they haven't asked yet."],
    "Asking Risk what it's most uncertain about": ["I just asked Sentinel what they're least sure of. That's usually more useful than what they're sure of."],
    "Holding a Thinking Session": ["No conclusions today — just better questions than we started with."],
    "Reviewing the day's reasoning": ["Not grading anyone. Just noticing which assumptions held up and which didn't."],
    "Sitting quietly with today's question, off the clock": ["I don't mind not knowing yet. That's usually where the real thinking starts."],
    "Reading something unrelated to work, for once": ["Even a mentor benefits from a question that isn't about the company."],
  },
};

/** Shared fallback lines for override-driven tasks (meetings/breaks), independent of agent personality. */
const OVERRIDE_LINES: Record<string, string[]> = {
  "In a meeting": ["Can this wait? We're mid-meeting.", "Good timing — we just wrapped up a point."],
  "Taking a break": ["Just grabbing a coffee. Back in a minute.", "Recharging. I'll be sharper shortly."],
  Resting: ["Taking five. Even AI needs a moment.", "Recharging. I'll be sharper in a few minutes."],
  // v0.7 Feature 35 — every agent's shared 0:00-6:00 off-duty block (see
  // schedule.py's own module docstring). One shared fallback rather than
  // eleven identical per-agent copies of the same real fact.
  Sleeping: ["Shh — I'm off the clock until morning.", "Catching real rest before the workday starts again."],
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
  cio: ["Good to see you.", "I was just reviewing the department reports.", "Do you have a moment for a quick update?"],
  sage: ["Ah. What's on your mind today?", "Good timing. I was just thinking about a question.", "Come in — no wrong questions here."],
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
    const depthLine = this.knowledgeDepthLine(agentId);
    if (depthLine) lines.push(depthLine);
    const recall = this.recallLine(agentId);
    if (recall) lines.push(recall);
    this.recordLines(agentId, lines);
    EventBus.emit("dialogue:open", { lines, speaker: profile.name });
    return { speaker: profile.name, lines };
  }

  /**
   * v0.7 Feature 31 — "higher [Knowledge] levels unlock richer dialogue,
   * deeper explanations." The honest, template-based version: no free-
   * form NLG exists in this codebase to actually vary explanation depth
   * per topic, so this surfaces the one real thing that does vary — the
   * agent's own real Knowledge Level (app/academy.py) — as a real,
   * deterministic line once they've actually reached "advanced" or
   * higher. A novice/beginner/intermediate agent has nothing extra to
   * say here yet, honestly.
   */
  private knowledgeDepthLine(agentId: AgentId): string | null {
    const { agentKnowledge } = gameStore.getSnapshot();
    const state = agentKnowledge[agentId];
    if (!state || state.tier < 3) return null;
    const byLevel: Partial<Record<string, string>> = {
      advanced: `I've built real depth in ${state.branch} now — ask me anything about it.`,
      expert: `${state.branch} is where I go deep. I can walk you through the reasoning, not just the answer.`,
      master: `At this point I don't just apply ${state.branch} — I question it. Every answer comes with what could prove it wrong.`,
      mentor: `I teach ${state.branch} now, not just practice it. If something's unclear, ask — I'll find the gap in my own explanation before you do.`,
    };
    return byLevel[state.level] ?? null;
  }

  /**
   * v0.7 Features 25.5/27/29/30 — a modest, honest slice of
   * "Institutional Memory." An agent recalls a real thing they were
   * actually part of — their own most recent completed Academy project,
   * a real Library of Mistakes case study from a decision they were a
   * real attendee of (Feature 27), or a real Reasoning Lab challenge
   * they actually contributed a real Debate turn to (Feature 29) —
   * referencing its real title/category and real in-game day. Never a
   * fabricated memory, and never claiming credit/involvement that isn't
   * actually real. All sources are tried and one is picked at random
   * from whichever actually has real content, rather than a single
   * coin-flip that could silently waste the chance on an empty source.
   *
   * Feature 30's real, checkable version of "historical knowledge is
   * referenced more often" as the company grows wiser: the base
   * one-in-three chance scales up with the company's own real Wisdom
   * tier (see recallChance()) — never a fabricated dialogue-quality
   * upgrade, just the same real recall sources surfacing more often.
   */
  private recallLine(agentId: AgentId): string | null {
    if (Math.random() > this.recallChance()) return null;
    const candidates = [this.academyRecall(agentId), this.caseStudyRecall(agentId), this.reasoningRecall(agentId)].filter((line): line is string => line !== null);
    if (candidates.length === 0) return null;
    return pick(candidates);
  }

  private recallChance(): number {
    const { wisdomState } = gameStore.getSnapshot();
    const byTier: Record<string, number> = {
      young_company: 1 / 4,
      developing_judgment: 1 / 3,
      institutional_memory: 0.4,
      seasoned_wisdom: 0.5,
      enduring_wisdom: 0.6,
    };
    return byTier[wisdomState.tier] ?? 1 / 3;
  }

  private academyRecall(agentId: AgentId): string | null {
    const { academyCompletedProjects } = gameStore.getSnapshot();
    const own = academyCompletedProjects.filter((p) => p.assignedAgent === agentId);
    if (own.length === 0) return null;
    const latest = own[own.length - 1];
    if (!latest) return null;
    return `I still think back on "${latest.title}" — that project taught me a lot.`;
  }

  private caseStudyRecall(agentId: AgentId): string | null {
    const { caseStudies, disciplineReviews } = gameStore.getSnapshot();
    const myDecisionIds = new Set(disciplineReviews.filter((r) => r.attendees.includes(agentId)).map((r) => r.decisionId));
    const own = caseStudies.filter((c) => myDecisionIds.has(c.decisionId));
    if (own.length === 0) return null;
    const latest = own[own.length - 1];
    if (!latest) return null;
    return `That "${latest.title}" case study from Day ${latest.simDay} still comes up — ${latest.symbol}, a real lesson we filed away.`;
  }

  private reasoningRecall(agentId: AgentId): string | null {
    const { reasoningChallenges } = gameStore.getSnapshot();
    const own = reasoningChallenges.filter((c) => c.contributions.some((contribution) => contribution.agentId === agentId));
    if (own.length === 0) return null;
    const latest = own[own.length - 1];
    if (!latest) return null;
    return `The Reasoning Lab's "${latest.title}" exercise on ${latest.symbol}, back on Day ${latest.simDay}, sharpened how I think about this.`;
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
