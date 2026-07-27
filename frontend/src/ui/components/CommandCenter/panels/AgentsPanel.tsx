import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_IDS } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { EmptyState, Glass, Meter } from "../ui";

/** The nine-agent roster as a real status board — only fields TradeTown's backend actually tracks per agent (see AgentState in types.ts); no fabricated activity feed. */
export function AgentsPanel() {
  const { agents, tasks, research } = useGameStore();

  if (!agents) return <EmptyState>Agent state hasn&apos;t loaded yet.</EmptyState>;

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
      {AGENT_IDS.map((id) => {
        const profile = AGENT_PROFILES[id];
        const state = agents[id];
        const latestTask = [...tasks].reverse().find((t) => t.owner === id) ?? null;
        const activeResearch = research.find((r) => r.assignedAgent === id && r.status === "in_progress") ?? null;
        const idle = state.location === "lobby" || state.location === "break-room";

        return (
          <Glass key={id} className="p-3">
            <div className="mb-1 flex items-center justify-between">
              <div>
                <span className="font-cmdmono text-cmd-cyan">{profile.name}</span>
                <span className="ml-2 text-[9px] uppercase tracking-wide text-cmd-textDim">{profile.occupation}</span>
              </div>
              <span className={`text-[9px] uppercase ${idle ? "text-cmd-textDim" : "text-cmd-green"}`}>{idle ? "IDLE" : "WORKING"}</span>
            </div>

            <div className="mb-1.5 text-[9px] text-cmd-textDim">{state.location.replace("-", " ")}</div>

            <div className="mb-1.5">
              <div className="text-[9px] uppercase tracking-wide text-cmd-textDim">Current Task</div>
              <div className="truncate text-cmd-text">{state.currentTask}</div>
            </div>

            <div className="mb-1.5 grid grid-cols-2 gap-2">
              <div>
                <div className="mb-0.5 flex items-center justify-between text-[9px] text-cmd-textDim">
                  <span>Mood</span>
                  <span>{Math.round(state.mood)}</span>
                </div>
                <Meter value={state.mood} tone={state.mood < 35 ? "red" : state.mood < 65 ? "amber" : "green"} />
              </div>
              <div>
                <div className="mb-0.5 flex items-center justify-between text-[9px] text-cmd-textDim">
                  <span>Energy</span>
                  <span>{Math.round(state.energy)}</span>
                </div>
                <Meter value={state.energy} tone={state.energy < 35 ? "red" : state.energy < 65 ? "amber" : "cyan"} />
              </div>
            </div>

            <div className="border-t border-cmd-border/60 pt-1.5 text-[9px] text-cmd-textDim">
              {activeResearch !== null && (
                <div className="mb-0.5">
                  Researching <span className="text-cmd-text">{activeResearch.title}</span> — {Math.round(activeResearch.confidence)}% confidence
                </div>
              )}
              {latestTask !== null && (
                <div className="truncate">
                  Latest: {latestTask.description} <span className="opacity-70">[{latestTask.status}]</span>
                </div>
              )}
              {activeResearch === null && latestTask === null && <div>No recent activity logged.</div>}
            </div>
          </Glass>
        );
      })}
    </div>
  );
}
