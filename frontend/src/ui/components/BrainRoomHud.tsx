import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { upcomingEvents } from "@/game/systems/UpcomingEvents";
import type { AgentId, TimeState } from "@/types";

const AGENT_ORDER: AgentId[] = ["scout", "atlas", "echo", "nova", "scribe"];
const RESEARCHER_ORDER: AgentId[] = ["scout", "atlas", "echo", "nova"];

function formatClock(time: TimeState): string {
  return `Day ${time.day} · ${String(time.hour).padStart(2, "0")}:${String(time.minute).padStart(2, "0")}`;
}

/**
 * The Brain Room's "Mission Control" readouts. Rendered as a React
 * overlay (not in-world Phaser text) so it stays legible regardless of
 * the room's camera zoom; the holographic core and monitor props in
 * BrainRoomScene are the "physical" centerpiece, this panel is the actual
 * readable dashboard. All progress/confidence bars use a CSS transition
 * on width so they visibly animate as values change tick to tick, rather
 * than snapping.
 */
export function BrainRoomHud() {
  const { currentScene, agents, tasks, news, research, watchlist, time } = useGameStore();
  if (currentScene !== "BrainRoomScene" || !agents) return null;

  const working = AGENT_ORDER.filter((id) => !["lobby", "break-room"].includes(agents[id].location)).length;
  const avgMood = Math.round(AGENT_ORDER.reduce((sum, id) => sum + agents[id].mood, 0) / AGENT_ORDER.length);
  const avgEnergy = Math.round(AGENT_ORDER.reduce((sum, id) => sum + agents[id].energy, 0) / AGENT_ORDER.length);

  const recentTasks = [...tasks].reverse().slice(0, 6);
  const discoveries = news.filter((n) => n.category === "discovery").slice(-4).reverse();
  const marketHeadlines = news.filter((n) => n.category === "market").slice(-3).reverse();
  const activeResearch = RESEARCHER_ORDER.map((id) => research.find((r) => r.assignedAgent === id && r.status === "in_progress")).filter(
    (item): item is NonNullable<typeof item> => item != null,
  );

  const upcoming = upcomingEvents(AGENT_ORDER, time);

  return (
    <div className="pointer-events-none absolute right-3 top-16 bottom-24 w-72 overflow-y-auto rounded border border-[#60d1ff]/40 bg-panel/90 p-3 font-pixel text-[10px] text-parchment shadow-pixel">
      <Section title="Market Clock">
        <div className="text-gold">{formatClock(time)}</div>
      </Section>

      <Section title="Company Status">
        <div>{working} of {AGENT_ORDER.length} agents actively working</div>
        <div>Average mood: {avgMood} · Average energy: {avgEnergy}</div>
      </Section>

      <Section title="Agent Status">
        {AGENT_ORDER.map((id) => {
          const profile = AGENT_PROFILES[id];
          const agent = agents[id];
          return (
            <div key={id} className="mb-1.5">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: `#${profile.tint.toString(16).padStart(6, "0")}` }} />
                <span className="text-gold">{profile.name}</span>
                <span className="opacity-60">— {agent.location.replace("-", " ")}</span>
              </div>
              <div className="truncate pl-3.5 opacity-80">{agent.currentTask}</div>
            </div>
          );
        })}
      </Section>

      <Section title="Research Queue">
        {activeResearch.length === 0 && <div className="opacity-50">No active research.</div>}
        {activeResearch.map((item) => (
          <div key={item.id} className="mb-2">
            <div className="flex items-center justify-between gap-1.5">
              <span className="truncate text-gold">{AGENT_PROFILES[item.assignedAgent].name}: {item.title}</span>
              <span className="shrink-0 opacity-70">{Math.round(item.confidence)}%</span>
            </div>
            <ConfidenceBar value={item.confidence} />
          </div>
        ))}
      </Section>

      <Section title="Watchlist">
        {watchlist.length === 0 && <div className="opacity-50">No symbols tracked yet.</div>}
        {watchlist.map((entry) => (
          <div key={entry.symbol} className="mb-2">
            <div className="flex items-center justify-between gap-1.5">
              <span className="text-gold">{entry.symbol}</span>
              <span className={entry.dailyChangePct >= 0 ? "text-bullish" : "text-bearish"}>
                ${entry.lastPrice.toFixed(2)} ({entry.dailyChangePct >= 0 ? "+" : ""}{entry.dailyChangePct.toFixed(2)}%)
              </span>
            </div>
            <div className="flex items-center justify-between gap-1.5 opacity-70">
              <span className="truncate">{entry.name}</span>
              <span>{entry.assignedAgent ? AGENT_PROFILES[entry.assignedAgent].name : "—"}</span>
            </div>
            <ConfidenceBar value={entry.researchProgress} />
          </div>
        ))}
      </Section>

      <Section title="Current Tasks">
        {recentTasks.length === 0 && <div className="opacity-50">No tasks logged yet.</div>}
        {recentTasks.map((task) => (
          <div key={task.id} className="mb-1 flex items-start gap-1.5">
            <span
              className={
                task.status === "working"
                  ? "text-gold"
                  : task.status === "completed"
                    ? "text-bullish"
                    : "text-bearish"
              }
            >
              [{task.status}]
            </span>
            <span className="truncate opacity-80">
              {AGENT_PROFILES[task.owner].name}: {task.description}
            </span>
          </div>
        ))}
      </Section>

      <Section title="Upcoming Events">
        {upcoming.length === 0 && <div className="opacity-50">Nothing scheduled.</div>}
        {upcoming.map((event) => (
          <div key={event.agentId} className="mb-1 opacity-80">
            {AGENT_PROFILES[event.agentId].name} → {event.location.replace("-", " ")} at {String(event.atHour).padStart(2, "0")}:00 ({event.task})
          </div>
        ))}
      </Section>

      <Section title="Market Status">
        <div className="mb-1 opacity-50">Placeholder — not connected to a live feed.</div>
        {marketHeadlines.length === 0 && <div className="opacity-50">No headlines yet.</div>}
        {marketHeadlines.map((n) => (
          <div key={n.id} className="mb-1 opacity-80">
            {n.headline}
          </div>
        ))}
      </Section>

      <Section title="Recent Discoveries">
        {discoveries.length === 0 && <div className="opacity-50">Nothing yet — check back soon.</div>}
        {discoveries.map((n) => (
          <div key={n.id} className="mb-1 opacity-80">
            {n.headline}
          </div>
        ))}
      </Section>
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  return (
    <div className="mt-0.5 h-1 w-full overflow-hidden rounded-full bg-ink/40">
      <div className="h-full rounded-full bg-[#60d1ff] transition-all duration-500 ease-out" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <div className="mb-1 border-b border-[#60d1ff]/30 pb-0.5 text-[#60d1ff]">{title}</div>
      {children}
    </div>
  );
}
