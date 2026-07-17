import type { AgentId, AgentLocation, TimeState } from "@/types";
import { AGENT_SCHEDULES, scheduleBlockForHour } from "./Schedule";

export interface UpcomingEvent {
  agentId: AgentId;
  hoursUntil: number;
  atHour: number;
  location: AgentLocation;
  task: string;
}

/**
 * Each agent's next schedule-block transition, computed client-side from
 * the same Schedule.ts data driving the offline fallback. Meetings are
 * deliberately excluded — NEXUS calls them at random (see
 * backend/app/nexus.py), so there's nothing genuine to predict there,
 * only the deterministic daily routine. Shared by BrainRoomHud and
 * Newspaper so both "Upcoming Events" sections agree.
 */
function nextTransition(agentId: AgentId, hour: number): UpcomingEvent | null {
  const blocks = AGENT_SCHEDULES[agentId];
  const current = scheduleBlockForHour(agentId, hour);
  const atHour = current.endHour % 24;
  const next = blocks.find((b) => b.startHour === atHour);
  if (!next) return null;
  const hoursUntil = ((atHour - hour + 24) % 24) || 24;
  return { agentId, hoursUntil, atHour, location: next.location, task: next.task };
}

export function upcomingEvents(agentIds: AgentId[], time: TimeState, limit = 4): UpcomingEvent[] {
  return agentIds
    .map((id) => nextTransition(id, time.hour))
    .filter((event): event is UpcomingEvent => event != null)
    .sort((a, b) => a.hoursUntil - b.hoursUntil)
    .slice(0, limit);
}
