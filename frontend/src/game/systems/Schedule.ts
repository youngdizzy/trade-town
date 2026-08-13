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
 *
 * v0.7 Feature 35 — every agent's workday now runs 6:00-20:00, followed
 * by a real 20:00-22:00 wind-down, a 22:00-24:00 evening activity, and a
 * shared 0:00-6:00 "Sleeping" block at the existing break-room location —
 * see schedule.py's own module docstring for the full scope note.
 */
export const AGENT_SCHEDULES: Record<AgentId, ScheduleBlock[]> = {
  scout: [
    { startHour: 6, endHour: 9, location: "scout-office", task: "Scanning market news" },
    { startHour: 9, endHour: 12, location: "brain-room", task: "Back-testing a strategy" },
    { startHour: 12, endHour: 13, location: "lobby", task: "Resting" },
    { startHour: 13, endHour: 17, location: "scout-office", task: "Building a research memo" },
    { startHour: 17, endHour: 20, location: "brain-room", task: "Reviewing overnight positions" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Trading watchlist stories with whoever's around" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Reading market history for fun" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
  atlas: [
    { startHour: 6, endHour: 9, location: "meeting-room", task: "Reviewing overnight strategy" },
    { startHour: 9, endHour: 12, location: "brain-room", task: "Assessing agent performance" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 16, location: "meeting-room", task: "Weighing strategic options" },
    { startHour: 16, endHour: 20, location: "brain-room", task: "Finalizing decisions" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Reviewing the day one more time before letting it go" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Reading quietly" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
  echo: [
    { startHour: 6, endHour: 10, location: "brain-room", task: "Charting technical patterns" },
    { startHour: 10, endHour: 11, location: "break-room", task: "Refilling coffee" },
    { startHour: 11, endHour: 15, location: "brain-room", task: "Studying monitor feeds" },
    { startHour: 15, endHour: 16, location: "lobby", task: "Stretching legs" },
    { startHour: 16, endHour: 20, location: "brain-room", task: "Tracking momentum indicators" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Watching an old chart pattern for fun, off the clock" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Sketching new indicator ideas in a notebook" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
  nova: [
    { startHour: 6, endHour: 11, location: "brain-room", task: "Reading quarterly reports" },
    { startHour: 11, endHour: 12, location: "lobby", task: "Taking a walk" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Lunch break" },
    { startHour: 13, endHour: 17, location: "brain-room", task: "Summarizing research findings" },
    { startHour: 17, endHour: 20, location: "scout-office", task: "Cross-checking Scout's notes" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Reading a novel, finally not about markets" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Journaling a few thoughts from the day" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
  scribe: [
    { startHour: 6, endHour: 9, location: "brain-room", task: "Reviewing overnight logs" },
    { startHour: 9, endHour: 12, location: "meeting-room", task: "Filing yesterday's minutes" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 17, location: "brain-room", task: "Logging research updates" },
    { startHour: 17, endHour: 20, location: "scout-office", task: "Cross-referencing the archive" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Writing in a personal journal, just for once" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Reading quietly" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
  coach: [
    { startHour: 6, endHour: 9, location: "performance-center", task: "Reviewing yesterday's paper trades" },
    { startHour: 9, endHour: 12, location: "brain-room", task: "Observing research in progress" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 17, location: "performance-center", task: "Analyzing confidence calibration" },
    { startHour: 17, endHour: 20, location: "simulation-lab", task: "Reviewing simulation results" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Exercising to clear the mind" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Watching game film, but for fun this time" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
  sentinel: [
    { startHour: 6, endHour: 9, location: "trading-floor", task: "Reviewing overnight risk exposure" },
    { startHour: 9, endHour: 12, location: "trading-floor", task: "Monitoring position sizing" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 17, location: "trading-floor", task: "Evaluating trade candidates" },
    { startHour: 17, endHour: 20, location: "performance-center", task: "Cross-checking risk against Coach's reports" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Finally letting the guard down for a few hours" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Reading, off the clock" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
  pulse: [
    { startHour: 6, endHour: 9, location: "trading-floor", task: "Scanning premarket movers" },
    { startHour: 9, endHour: 12, location: "trading-floor", task: "Watching for breakouts" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 17, location: "trading-floor", task: "Tracking volume spikes" },
    { startHour: 17, endHour: 20, location: "brain-room", task: "Cross-referencing research with scanner alerts" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Still glancing at a ticker out of habit" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Playing a game to unwind" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
  guardian: [
    { startHour: 6, endHour: 9, location: "trading-floor", task: "Checking overnight portfolio exposure" },
    { startHour: 9, endHour: 12, location: "trading-floor", task: "Monitoring concentration risk" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 17, location: "trading-floor", task: "Watching drawdown levels" },
    { startHour: 17, endHour: 20, location: "performance-center", task: "Reviewing portfolio performance" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Making sure everything is squared away before bed" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Reading quietly" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
  cio: [
    { startHour: 6, endHour: 9, location: "executive-boardroom", task: "Reviewing overnight department reports" },
    { startHour: 9, endHour: 12, location: "brain-room", task: "Sitting in on the research desk" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 16, location: "trading-floor", task: "Reviewing risk and execution together" },
    { startHour: 16, endHour: 20, location: "executive-boardroom", task: "Preparing the executive briefing" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Reflecting on today's decisions, off the clock" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Reading, away from the boardroom" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
  sage: [
    { startHour: 6, endHour: 8, location: "brain-room", task: "Writing today's question" },
    { startHour: 8, endHour: 11, location: "brain-room", task: "Listening in on the research desk" },
    { startHour: 11, endHour: 12, location: "trading-floor", task: "Asking Risk what it's most uncertain about" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 16, location: "meeting-room", task: "Holding a Thinking Session" },
    { startHour: 16, endHour: 20, location: "brain-room", task: "Reviewing the day's reasoning" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Sitting quietly with today's question, off the clock" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Reading something unrelated to work, for once" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
  // v0.7 Feature 39 — the Original Founders. Mirrors backend/app/schedule.py exactly.
  keystone: [
    { startHour: 6, endHour: 9, location: "trading-floor", task: "Reviewing overnight risk with Sentinel and Guardian" },
    { startHour: 9, endHour: 11, location: "executive-boardroom", task: "Studying yesterday's closed trades for discipline lapses" },
    { startHour: 11, endHour: 12, location: "lobby", task: "Walking the campus" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 16, location: "trading-floor", task: "Watching how the desk handles pressure" },
    { startHour: 16, endHour: 18, location: "meeting-room", task: "Holding office hours on risk discipline" },
    { startHour: 18, endHour: 20, location: "executive-boardroom", task: "Weighing today's decisions against the firm's own history" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Sitting with the day's numbers, off the clock" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Reading quietly" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
  compass: [
    { startHour: 6, endHour: 9, location: "brain-room", task: "Reading yesterday's research with fresh eyes" },
    { startHour: 9, endHour: 11, location: "brain-room", task: "Watching the research desk work" },
    { startHour: 11, endHour: 12, location: "lobby", task: "Walking the campus" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 16, location: "meeting-room", task: "Holding an open discussion on company philosophy" },
    { startHour: 16, endHour: 18, location: "brain-room", task: "Reviewing the day's reasoning challenges" },
    { startHour: 18, endHour: 20, location: "hall-of-fame", task: "Looking over the company's own history for lessons" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Following a curiosity that has nothing to do with work" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Reading quietly" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
  // v0.7 — the Chief Quantitative Strategist. See backend/app/black_box.py.
  quant: [
    { startHour: 6, endHour: 9, location: "simulation-lab", task: "Reviewing overnight backtest results" },
    { startHour: 9, endHour: 12, location: "simulation-lab", task: "Running the Black Box project's daily analysis" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 16, location: "brain-room", task: "Cross-checking findings with the research desk" },
    { startHour: 16, endHour: 19, location: "simulation-lab", task: "Writing up the day's progress" },
    { startHour: 19, endHour: 20, location: "executive-boardroom", task: "Reporting Black Box progress to the CEO" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Still turning the day's numbers over, off the clock" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Reading quietly" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
  // Quantitative Research & Intelligence System, Piece 7 — the Quant
  // Developer. See backend/app/quant_developer.py.
  forge: [
    { startHour: 6, endHour: 9, location: "simulation-lab", task: "Auditing overnight Monte Carlo runs for sample reliability" },
    { startHour: 9, endHour: 12, location: "simulation-lab", task: "Stress-testing the bootstrap pipeline" },
    { startHour: 12, endHour: 13, location: "break-room", task: "Resting" },
    { startHour: 13, endHour: 16, location: "simulation-lab", task: "Checking every real result against the audited path count" },
    { startHour: 16, endHour: 19, location: "simulation-lab", task: "Writing up today's reliability findings" },
    { startHour: 19, endHour: 20, location: "executive-boardroom", task: "Flagging any tooling gaps to the CEO" },
    { startHour: 20, endHour: 22, location: "break-room", task: "Tinkering with a side project, off the clock" },
    { startHour: 22, endHour: 24, location: "break-room", task: "Reading a systems-engineering paper" },
    { startHour: 0, endHour: 6, location: "break-room", task: "Sleeping" },
  ],
};

export function scheduleBlockForHour(agentId: AgentId, hour: number): ScheduleBlock {
  const blocks = AGENT_SCHEDULES[agentId];
  const block = blocks.find((b) => hour >= b.startHour && hour < b.endHour);
  return block ?? blocks[0]!;
}

/** v0.7 Feature 38 — the Campus Map's employee-tracking "Destination"
 * readout. Every agent's blocks cover the full 24 hours with no gaps, so
 * the next block always starts exactly where the current one ends —
 * this just looks that block up directly rather than re-deriving it. */
export function nextScheduleBlock(agentId: AgentId, hour: number): ScheduleBlock {
  const blocks = AGENT_SCHEDULES[agentId];
  const current = scheduleBlockForHour(agentId, hour);
  const nextStart = current.endHour % 24;
  return blocks.find((b) => b.startHour === nextStart) ?? blocks[0]!;
}

/** Every AgentLocation any of the 11 agents' real schedules ever route
 * them through, computed once at module load — the Campus Map's
 * "Related Departments" per building. */
export const LOCATIONS_TO_AGENTS: Partial<Record<AgentLocation, AgentId[]>> = (() => {
  const map: Partial<Record<AgentLocation, AgentId[]>> = {};
  for (const [agentId, blocks] of Object.entries(AGENT_SCHEDULES) as [AgentId, ScheduleBlock[]][]) {
    for (const block of blocks) {
      const list = map[block.location] ?? [];
      if (!list.includes(agentId)) list.push(agentId);
      map[block.location] = list;
    }
  }
  return map;
})();
