import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import type { AgentId } from "@/types";

const AGENT_ORDER: AgentId[] = ["scout", "atlas", "echo", "nova"];

/**
 * The Brain Room's "Mission Control" readouts — Company Status, Agent
 * Status, Current Tasks, a placeholder Market Status, and Recent
 * Discoveries. Rendered as a React overlay (not in-world Phaser text) so
 * it stays legible regardless of the room's camera zoom; the holographic
 * core and monitor props in BrainRoomScene are the "physical" centerpiece,
 * this panel is the actual readable dashboard.
 */
export function BrainRoomHud() {
  const { currentScene, agents, tasks, news } = useGameStore();
  if (currentScene !== "BrainRoomScene" || !agents) return null;

  const working = AGENT_ORDER.filter((id) => !["lobby", "break-room"].includes(agents[id].location)).length;
  const avgMood = Math.round(AGENT_ORDER.reduce((sum, id) => sum + agents[id].mood, 0) / AGENT_ORDER.length);
  const avgEnergy = Math.round(AGENT_ORDER.reduce((sum, id) => sum + agents[id].energy, 0) / AGENT_ORDER.length);

  const recentTasks = [...tasks].reverse().slice(0, 6);
  const discoveries = news.filter((n) => n.category === "discovery").slice(-4).reverse();
  const marketHeadlines = news.filter((n) => n.category === "market").slice(-3).reverse();

  return (
    <div className="pointer-events-none absolute right-3 top-16 bottom-24 w-72 overflow-y-auto rounded border border-[#60d1ff]/40 bg-panel/90 p-3 font-pixel text-[10px] text-parchment shadow-pixel">
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

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <div className="mb-1 border-b border-[#60d1ff]/30 pb-0.5 text-[#60d1ff]">{title}</div>
      {children}
    </div>
  );
}
