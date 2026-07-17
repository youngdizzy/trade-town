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
};

export function scheduleBlockForHour(agentId: AgentId, hour: number): ScheduleBlock {
  const blocks = AGENT_SCHEDULES[agentId];
  const block = blocks.find((b) => hour >= b.startHour && hour < b.endHour);
  return block ?? blocks[0]!;
}
