import type { ScoutLocation } from "@/types";

export interface ScheduleBlock {
  startHour: number;
  endHour: number;
  location: ScoutLocation;
  task: string;
}

/**
 * Scout's daily routine. This is the client-side mirror of
 * backend/app/schedule.py — it's used as an offline fallback so the game
 * remains playable if the WebSocket connection to the backend drops; when
 * connected, the backend's tick is authoritative and overrides this.
 */
export const SCOUT_SCHEDULE: ScheduleBlock[] = [
  { startHour: 6, endHour: 9, location: "scout-office", task: "Scanning market news" },
  { startHour: 9, endHour: 12, location: "brain-room", task: "Back-testing a strategy" },
  { startHour: 12, endHour: 13, location: "lobby", task: "Resting" },
  { startHour: 13, endHour: 17, location: "scout-office", task: "Building a research memo" },
  { startHour: 17, endHour: 19, location: "brain-room", task: "Reviewing overnight positions" },
  { startHour: 19, endHour: 22, location: "lobby", task: "Resting" },
  { startHour: 22, endHour: 24, location: "scout-office", task: "Scanning market news" },
  { startHour: 0, endHour: 6, location: "scout-office", task: "Reviewing overnight positions" },
];

export function scheduleBlockForHour(hour: number): ScheduleBlock {
  const block = SCOUT_SCHEDULE.find((b) => hour >= b.startHour && hour < b.endHour);
  return block ?? SCOUT_SCHEDULE[0]!;
}
