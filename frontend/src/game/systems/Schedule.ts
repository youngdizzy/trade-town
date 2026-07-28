import type { AgentId, AgentLocation } from "@/types";

export interface ScheduleBlock {
  startHour: number;
  endHour: number;
  location: AgentLocation;
  task: string;
}

/**
 * Each agent's daily routine. This is the client-side mirror of
 * backend/app/schedule.py — used as an offline fallback so the game
 * remains playable if the WebSocket connection to the backend drops.
 * Meetings/breaks are NOT modeled here (they're server-driven overrides);
 * offline mode just shows each agent following their base schedule.
 */
export const AGENT_SCHEDULES: Record<AgentId, ScheduleBlock[]> = {
  scout: [
    { startHour: 6, endHour: 9, location: "scout-office", task: "Scanning market news" },
    { startHour: 9, endHour: 12, location: "brain-room", task: "Back-testing a strategy" },
    { startHour: 12, endHour: 13, location: "lobby", task: "Resting" },
    { startHour: 13, endHour: 17, location: "scout-office", task: "Building a research memo" },
    { startHour: 17, endHour: 19, location: "brain-room", task: "Reviewing overnight positions" },
    { startHour: 19, endHour: 22, location: "lobby", task: "Resting" },
    { startHour: 22, endHour: 24, location: "scout-office", task: "Scanning market news" },
    { startHour: 0, endHour: 6, location: "scout-office", task: "Reviewing overnight positions" },
  ],
  atlas: [
    { startHour: 6, endHour: 9, location: "meeting-room", task: "Reviewing overnight strategy" },
    { startHour: 9, endHour: 12, location: "brain-room", task: "Assessing agent performance" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 16, location: "meeting-room", task: "Weighing strategic options" },
    { startHour: 16, endHour: 19, location: "brain-room", task: "Finalizing decisions" },
    { startHour: 19, endHour: 22, location: "meeting-room", task: "Planning tomorrow's priorities" },
    { startHour: 22, endHour: 24, location: "meeting-room", task: "Reviewing the day" },
    { startHour: 0, endHour: 6, location: "meeting-room", task: "Standing by" },
  ],
  echo: [
    { startHour: 6, endHour: 10, location: "brain-room", task: "Charting technical patterns" },
    { startHour: 10, endHour: 11, location: "break-room", task: "Refilling coffee" },
    { startHour: 11, endHour: 15, location: "brain-room", task: "Studying monitor feeds" },
    { startHour: 15, endHour: 16, location: "lobby", task: "Stretching legs" },
    { startHour: 16, endHour: 20, location: "brain-room", task: "Tracking momentum indicators" },
    { startHour: 20, endHour: 22, location: "lobby", task: "Resting" },
    { startHour: 22, endHour: 24, location: "brain-room", task: "Scanning overnight charts" },
    { startHour: 0, endHour: 6, location: "brain-room", task: "Monitoring after-hours signals" },
  ],
  nova: [
    { startHour: 7, endHour: 11, location: "brain-room", task: "Reading quarterly reports" },
    { startHour: 11, endHour: 12, location: "lobby", task: "Taking a walk" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Lunch break" },
    { startHour: 13, endHour: 17, location: "brain-room", task: "Summarizing research findings" },
    { startHour: 17, endHour: 19, location: "scout-office", task: "Cross-checking Scout's notes" },
    { startHour: 19, endHour: 22, location: "lobby", task: "Resting" },
    { startHour: 22, endHour: 24, location: "brain-room", task: "Reading overnight filings" },
    { startHour: 0, endHour: 7, location: "brain-room", task: "Reviewing archived reports" },
  ],
  scribe: [
    { startHour: 6, endHour: 9, location: "brain-room", task: "Reviewing overnight logs" },
    { startHour: 9, endHour: 12, location: "meeting-room", task: "Filing yesterday's minutes" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 17, location: "brain-room", task: "Logging research updates" },
    { startHour: 17, endHour: 19, location: "scout-office", task: "Cross-referencing the archive" },
    { startHour: 19, endHour: 22, location: "lobby", task: "Resting" },
    { startHour: 22, endHour: 24, location: "brain-room", task: "Indexing the day's discoveries" },
    { startHour: 0, endHour: 6, location: "brain-room", task: "Archiving overnight records" },
  ],
  coach: [
    { startHour: 6, endHour: 9, location: "performance-center", task: "Reviewing yesterday's paper trades" },
    { startHour: 9, endHour: 12, location: "brain-room", task: "Observing research in progress" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 17, location: "performance-center", task: "Analyzing confidence calibration" },
    { startHour: 17, endHour: 19, location: "simulation-lab", task: "Reviewing simulation results" },
    { startHour: 19, endHour: 22, location: "performance-center", task: "Evening performance review" },
    { startHour: 22, endHour: 24, location: "performance-center", task: "Drafting recommendations" },
    { startHour: 0, endHour: 6, location: "performance-center", task: "Standing by" },
  ],
  sentinel: [
    { startHour: 6, endHour: 9, location: "trading-floor", task: "Reviewing overnight risk exposure" },
    { startHour: 9, endHour: 12, location: "trading-floor", task: "Monitoring position sizing" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 17, location: "trading-floor", task: "Evaluating trade candidates" },
    { startHour: 17, endHour: 19, location: "performance-center", task: "Cross-checking risk against Coach's reports" },
    { startHour: 19, endHour: 22, location: "trading-floor", task: "Setting tomorrow's risk limits" },
    { startHour: 22, endHour: 24, location: "trading-floor", task: "Auditing the day's approvals" },
    { startHour: 0, endHour: 6, location: "trading-floor", task: "Standing watch" },
  ],
  pulse: [
    { startHour: 6, endHour: 9, location: "trading-floor", task: "Scanning premarket movers" },
    { startHour: 9, endHour: 12, location: "trading-floor", task: "Watching for breakouts" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 17, location: "trading-floor", task: "Tracking volume spikes" },
    { startHour: 17, endHour: 19, location: "brain-room", task: "Cross-referencing research with scanner alerts" },
    { startHour: 19, endHour: 22, location: "trading-floor", task: "Scanning after-hours activity" },
    { startHour: 22, endHour: 24, location: "trading-floor", task: "Compiling the day's alerts" },
    { startHour: 0, endHour: 6, location: "trading-floor", task: "Monitoring overnight volatility" },
  ],
  guardian: [
    { startHour: 6, endHour: 9, location: "trading-floor", task: "Checking overnight portfolio exposure" },
    { startHour: 9, endHour: 12, location: "trading-floor", task: "Monitoring concentration risk" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 17, location: "trading-floor", task: "Watching drawdown levels" },
    { startHour: 17, endHour: 19, location: "performance-center", task: "Reviewing portfolio performance" },
    { startHour: 19, endHour: 22, location: "trading-floor", task: "Recommending risk reductions" },
    { startHour: 22, endHour: 24, location: "trading-floor", task: "Filing the day's exposure report" },
    { startHour: 0, endHour: 6, location: "trading-floor", task: "Standing watch over the book" },
  ],
  cio: [
    { startHour: 6, endHour: 9, location: "executive-boardroom", task: "Reviewing overnight department reports" },
    { startHour: 9, endHour: 12, location: "brain-room", task: "Sitting in on the research desk" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 16, location: "trading-floor", task: "Reviewing risk and execution together" },
    { startHour: 16, endHour: 19, location: "executive-boardroom", task: "Preparing the executive briefing" },
    { startHour: 19, endHour: 22, location: "meeting-room", task: "Encouraging cross-department collaboration" },
    { startHour: 22, endHour: 24, location: "executive-boardroom", task: "Reviewing the day's decisions" },
    { startHour: 0, endHour: 6, location: "executive-boardroom", task: "Standing by" },
  ],
  sage: [
    { startHour: 6, endHour: 8, location: "brain-room", task: "Writing today's question" },
    { startHour: 8, endHour: 11, location: "brain-room", task: "Listening in on the research desk" },
    { startHour: 11, endHour: 12, location: "trading-floor", task: "Asking Risk what it's most uncertain about" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 16, location: "meeting-room", task: "Holding a Thinking Session" },
    { startHour: 16, endHour: 19, location: "brain-room", task: "Reviewing the day's reasoning" },
    { startHour: 19, endHour: 22, location: "meeting-room", task: "Coaching whoever asks" },
    { startHour: 22, endHour: 24, location: "brain-room", task: "Reading the day's lessons" },
    { startHour: 0, endHour: 6, location: "brain-room", task: "Sitting with an open question" },
  ],
};

export function scheduleBlockForHour(agentId: AgentId, hour: number): ScheduleBlock {
  const blocks = AGENT_SCHEDULES[agentId];
  const block = blocks.find((b) => hour >= b.startHour && hour < b.endHour);
  return block ?? blocks[0]!;
}
