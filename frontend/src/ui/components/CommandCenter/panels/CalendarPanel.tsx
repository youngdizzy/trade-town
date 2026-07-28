import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { NexusManager } from "@/game/systems/NexusManager";
import { api } from "@/net/api";
import { AGENT_IDS } from "@/types";
import type { AgentId, CalendarEvent, PlayerEventCategory } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { AGENT_SCHEDULES } from "@/game/systems/Schedule";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

const PLAYER_EVENT_LABEL: Record<PlayerEventCategory, string> = {
  emergency_meeting: "Emergency Meeting",
  company_holiday: "Company Holiday",
  extra_training_day: "Extra Training Day",
  research_marathon: "Research Marathon",
  hackathon: "Hackathon",
  strategy_day: "Strategy Day",
  celebration: "Celebration",
  town_hall: "Town Hall Meeting",
  other: "Custom Event",
};

function eventMinutes(e: CalendarEvent): number {
  return e.day * 1440 + e.hour * 60 + e.minute;
}

function formatWhen(e: CalendarEvent, nowDay: number): string {
  const dayLabel = e.day === nowDay ? "Today" : e.day === nowDay + 1 ? "Tomorrow" : `Day ${e.day}`;
  return `${dayLabel} · ${String(e.hour).padStart(2, "0")}:${String(e.minute).padStart(2, "0")}`;
}

/**
 * v0.7 Feature 36 — the CEO Calendar & Company Schedule. Every entry here
 * is real: system events are the fixed cadence checkpoints
 * nexus.tick() already runs on (weekly/monthly reports, the Reflection
 * Chamber, the daily Question of the Day) plus honest ESTIMATED research
 * completion dates — see backend/app/calendar.py's module docstring for
 * exactly which of the brief's calendar categories are real here and
 * which are explicitly cut (Academy Classes/Department Meetings have no
 * fixed slot, Employee Birthdays/Missed Meetings/Guest Lecturer etc. have
 * no real system behind them anywhere in this codebase). Player events
 * are informational only — creating one never changes department
 * behavior, the same "no fabricated mechanical effect" boundary Feature
 * 33's cut CEO Benefits list already established.
 */
export function CalendarPanel() {
  const { calendar, time, agents, meeting, meetingMinutes, research, agentKnowledge, settings } = useGameStore();
  const [selectedAgent, setSelectedAgent] = useState<AgentId>("scout");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState<PlayerEventCategory>("town_hall");
  const [title, setTitle] = useState("");
  const [day, setDay] = useState(String(time.day));
  const [hour, setHour] = useState("9");
  const [minute, setMinute] = useState("0");

  const nowMinutes = time.day * 1440 + time.hour * 60 + time.minute;
  const allEvents = useMemo(
    () => [...calendar.systemEvents, ...calendar.playerEvents].sort((a, b) => eventMinutes(a) - eventMinutes(b)),
    [calendar]
  );

  if (!agents) return <EmptyState>Agent state hasn&apos;t loaded yet.</EmptyState>;

  const todayEvents = allEvents.filter((e) => e.day === time.day);
  const tomorrowEvents = allEvents.filter((e) => e.day === time.day + 1);
  const weekEvents = allEvents.filter((e) => e.day > time.day + 1 && e.day <= time.day + 7);
  const monthEvents = allEvents.filter((e) => e.day > time.day + 7 && e.day <= time.day + 30);

  const nextEvent = allEvents.find((e) => eventMinutes(e) > nowMinutes) ?? null;
  const meetingsToday = meetingMinutes.filter((m) => m.day === time.day);

  const idleAgents = AGENT_IDS.filter((id) => agents[id] && (agents[id].location === "lobby" || agents[id].location === "break-room"));
  const workingCount = AGENT_IDS.length - idleAgents.length;

  const createEvent = async () => {
    if (busy || !title.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.createCalendarEvent(category, title.trim(), Number(day), Number(hour), Number(minute));
      NexusManager.setCalendar(res.calendar);
      setTitle("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const deleteEvent = async (eventId: string) => {
    if (busy) return;
    try {
      const res = await api.deleteCalendarEvent(eventId);
      NexusManager.setCalendar(res.calendar);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const agentState = agents[selectedAgent];
  const agentProfile = AGENT_PROFILES[selectedAgent];
  const agentSchedule = AGENT_SCHEDULES[selectedAgent];
  const agentResearch = research.find((r) => r.assignedAgent === selectedAgent && r.status === "in_progress") ?? null;
  const agentLevel = agentKnowledge[selectedAgent]?.level ?? null;
  const inActiveMeeting = meeting.active && meeting.participants.includes(selectedAgent);
  const lastLine = inActiveMeeting && meeting.discussion.length > 0 ? meeting.discussion[meeting.discussion.length - 1] : null;

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <Glass className="p-3 lg:col-span-3">
        <TerminalLabel>Executive View</TerminalLabel>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-3">
          <DataRow label="Current Event" value={meeting.active ? "Department meeting in progress" : "Normal operations"} />
          <DataRow label="Next Event" value={nextEvent ? `${nextEvent.title} — ${formatWhen(nextEvent, time.day)}` : "None scheduled"} />
          <DataRow label="Department Activity" value={`${workingCount} working / ${idleAgents.length} idle`} />
          <DataRow label="Meetings Today" value={String(meetingsToday.length)} />
          <DataRow label="Current Company Focus" value={settings.companyPriority.replace("_", " ").toUpperCase()} />
          <DataRow label="Upcoming Events (35d)" value={String(allEvents.length)} />
        </div>
        <p className="mt-2 text-[9px] text-cmd-textDim">
          Meetings are called spontaneously when conditions are right, not on a fixed schedule — there&apos;s no honest way to predict or track a
          &quot;missed&quot; one. See the Company tab for Time Controls.
        </p>
      </Glass>

      <EventListCard title="Today's Schedule" events={todayEvents} nowDay={time.day} onDelete={deleteEvent} emptyLabel="Nothing else scheduled today." />
      <EventListCard title="Tomorrow's Schedule" events={tomorrowEvents} nowDay={time.day} onDelete={deleteEvent} emptyLabel="Nothing scheduled yet." />
      <EventListCard title="Weekly Agenda" events={weekEvents} nowDay={time.day} onDelete={deleteEvent} emptyLabel="Nothing else this week." />
      <EventListCard title="Monthly Company Events" events={monthEvents} nowDay={time.day} onDelete={deleteEvent} emptyLabel="Nothing else this month." className="lg:col-span-2" />

      <Glass className="p-3">
        <TerminalLabel>Schedule a Custom Event</TerminalLabel>
        <p className="mb-2 text-[9px] text-cmd-textDim">Informational only — creating an event doesn&apos;t change department behavior.</p>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as PlayerEventCategory)}
          className="mb-1.5 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[10px] text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
        >
          {(Object.keys(PLAYER_EVENT_LABEL) as PlayerEventCategory[]).map((c) => (
            <option key={c} value={c}>
              {PLAYER_EVENT_LABEL[c]}
            </option>
          ))}
        </select>
        <input
          type="text"
          data-testid="calendar-event-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Event title…"
          maxLength={140}
          className="mb-1.5 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[10px] text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
        />
        <div className="mb-1.5 flex gap-1.5">
          <input type="number" data-testid="calendar-event-day" min={time.day} value={day} onChange={(e) => setDay(e.target.value)} className="w-16 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text focus:border-cmd-cyan/50 focus:outline-none" />
          <input type="number" data-testid="calendar-event-hour" min={0} max={23} value={hour} onChange={(e) => setHour(e.target.value)} className="w-14 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text focus:border-cmd-cyan/50 focus:outline-none" />
          <input type="number" data-testid="calendar-event-minute" min={0} max={59} value={minute} onChange={(e) => setMinute(e.target.value)} className="w-14 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text focus:border-cmd-cyan/50 focus:outline-none" />
        </div>
        <button
          type="button"
          onClick={() => void createEvent()}
          disabled={busy || !title.trim()}
          className="w-full rounded-sm border border-cmd-cyan/50 py-1.5 text-[10px] uppercase tracking-wider text-cmd-cyan transition-colors hover:bg-cmd-cyan/10 disabled:opacity-40"
        >
          {busy ? "…" : "Schedule Event"}
        </button>
        {error && <div className="mt-2 text-[9px] text-cmd-red">{error}</div>}
      </Glass>

      <Glass className="p-3 lg:col-span-3">
        <TerminalLabel>Live Schedule</TerminalLabel>
        <div className="mb-2 flex flex-wrap gap-1.5">
          {AGENT_IDS.map((id) => (
            <button
              key={id}
              type="button"
              onClick={() => setSelectedAgent(id)}
              className={`rounded-sm border px-2 py-1 text-[9px] uppercase tracking-wider transition-colors ${
                selectedAgent === id ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border/60 text-cmd-textDim hover:text-cmd-text"
              }`}
            >
              {AGENT_PROFILES[id].name}
            </button>
          ))}
        </div>
        {agentState ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <div className="mb-1.5 grid grid-cols-2 gap-x-4 gap-y-1">
                <DataRow label="Current Activity" value={agentState.currentTask} />
                <DataRow label="Current Room" value={agentState.location.replace("-", " ")} />
                <DataRow label="Mood" value={Math.round(agentState.mood)} />
                <DataRow label="Knowledge Level" value={agentLevel ? agentLevel.toUpperCase() : "—"} />
              </div>
              {agentResearch && (
                <div className="mt-1.5 text-[9px] text-cmd-textDim">
                  Researching <span className="text-cmd-text">{agentResearch.title}</span> — {Math.round(agentResearch.confidence)}% confidence
                </div>
              )}
              {lastLine && (
                <div className="mt-1.5 rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                  <span className="text-cmd-cyan">{AGENT_PROFILES[lastLine.speaker].name}:</span> <span className="text-cmd-textDim">&quot;{lastLine.line}&quot;</span>
                </div>
              )}
            </div>
            <div>
              <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">
                {agentProfile.name}&apos;s Real Daily Schedule
              </div>
              <div className="max-h-48 space-y-1 overflow-y-auto">
                {agentSchedule.map((block, i) => {
                  const active = time.hour >= block.startHour && time.hour < block.endHour;
                  return (
                    <div key={i} className={`flex items-center justify-between gap-2 rounded-sm border p-1.5 text-[9px] ${active ? "border-cmd-cyan/40 bg-cmd-cyan/5" : "border-cmd-border/40 bg-cmd-bg/40"}`}>
                      <span className="tabular-nums text-cmd-textDim">
                        {String(block.startHour).padStart(2, "0")}:00–{String(block.endHour).padStart(2, "0")}:00
                      </span>
                      <span className={`flex-1 truncate text-right ${active ? "text-cmd-cyan" : "text-cmd-text"}`}>{block.task}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          <EmptyState>Agent state hasn&apos;t loaded yet.</EmptyState>
        )}
      </Glass>
    </div>
  );
}

function EventListCard({
  title,
  events,
  nowDay,
  onDelete,
  emptyLabel,
  className = "",
}: {
  title: string;
  events: CalendarEvent[];
  nowDay: number;
  onDelete: (id: string) => void;
  emptyLabel: string;
  className?: string;
}) {
  return (
    <Glass className={`max-h-72 overflow-y-auto p-3 ${className}`}>
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>{title}</TerminalLabel>
        <StatusPill tone="cyan">{events.length}</StatusPill>
      </div>
      {events.length === 0 ? (
        <EmptyState>{emptyLabel}</EmptyState>
      ) : (
        <div className="space-y-1">
          {events.map((e) => (
            <div key={e.id} className="flex items-center justify-between gap-2 border-b border-cmd-border/40 py-1 text-[9px] last:border-0">
              <span className="w-20 flex-none tabular-nums text-cmd-textDim">{formatWhen(e, nowDay)}</span>
              <span className="flex-1 truncate text-cmd-text">{e.title}</span>
              {e.eligible !== null && <StatusPill tone={e.eligible ? "green" : "neutral"}>{e.eligible ? "READY" : "PENDING"}</StatusPill>}
              {e.source === "player" && (
                <button type="button" onClick={() => onDelete(e.id)} className="text-cmd-red underline-offset-2 hover:underline">
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </Glass>
  );
}
