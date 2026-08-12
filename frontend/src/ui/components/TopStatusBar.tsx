import { useGameStore } from "@/ui/hooks/useGameStore";
import { TimeManager } from "@/game/systems/TimeManager";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { AGENT_IDS } from "@/types";
import { EmergencyStopControl } from "./EmergencyStopControl";

export function TopStatusBar() {
  const { time, agents, meeting, netConnected, currentScene } = useGameStore();
  const inGame = currentScene !== "MainMenuScene";
  if (!inGame) return null;

  return (
    <div className="pointer-events-none absolute left-0 right-0 top-0 flex items-center justify-between gap-4 bg-gradient-to-b from-black/70 to-transparent px-4 py-2 font-pixel text-[11px] text-parchment">
      <div className="pointer-events-auto flex items-center gap-3 rounded bg-panel/80 px-3 py-1.5 shadow-pixel">
        <span className="text-gold">TradeTown HQ</span>
        <span className="opacity-70">{TimeManager.formatClock(time)}</span>
        {meeting.active && <span className="rounded bg-gold/20 px-1.5 py-0.5 text-gold">Meeting in progress</span>}
      </div>

      {/* Design Bible Chapter 73.5 — hidden below `sm` so this row's 3
          justify-between blocks never squeeze Emergency Stop (the
          highest-priority mobile control per the Design Bible's own
          desktop-vs-mobile interface priority rule) off a narrow phone
          viewport. Agent status stays one tap away via the Command
          Center's AGENTS tab. */}
      {agents && (
        <div className="pointer-events-auto hidden items-center gap-3 rounded bg-panel/80 px-3 py-1.5 shadow-pixel sm:flex">
          {AGENT_IDS.map((id) => {
            const profile = AGENT_PROFILES[id];
            const agent = agents[id];
            return (
              <div
                key={id}
                className="flex items-center gap-1.5"
                title={`${profile.name} (${profile.occupation}) — ${agent.currentTask}\nMood ${Math.round(agent.mood)} · Energy ${Math.round(agent.energy)}`}
              >
                <span className="h-2.5 w-2.5 rounded-full border border-black/40" style={{ backgroundColor: `#${profile.tint.toString(16).padStart(6, "0")}` }} />
                <span className="hidden opacity-80 sm:inline">{profile.name}</span>
              </div>
            );
          })}
        </div>
      )}

      <div className="flex items-center gap-2">
        <div className="pointer-events-auto flex items-center gap-2 rounded bg-panel/80 px-3 py-1.5 shadow-pixel">
          <span
            className={`h-2 w-2 rounded-full ${netConnected ? "bg-bullish" : "bg-bearish"}`}
            title={netConnected ? "Connected to backend" : "Offline (local simulation)"}
          />
          <span className="opacity-70">{netConnected ? "Live" : "Offline"}</span>
        </div>

        <EmergencyStopControl />
      </div>
    </div>
  );
}
