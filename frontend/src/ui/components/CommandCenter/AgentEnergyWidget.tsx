import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { api } from "@/net/api";
import { NexusManager } from "@/game/systems/NexusManager";
import { Glass, Meter, TerminalLabel } from "./ui";

// Mirrors backend/app/agent_energy.py's ACTION_COSTS — kept in sync by hand
// since energy costs aren't part of any server-pushed schema (they're a
// fixed game-balance constant, not data).
const ACTION_COSTS: Record<string, number> = {
  research_boost: 15,
  extra_simulation: 20,
  watch_symbol: 10,
};

/**
 * Agent Energy (v0.6.2 Phase 6) — a company-wide spendable resource,
 * distinct from each individual agent's fatigue/rest level. Every spend has
 * a real, verifiable effect on real game state (see agent_energy.py /
 * nexus.py's apply_energy_action): it never just makes a number go up.
 */
export function AgentEnergyWidget() {
  const { agentEnergy, research } = useGameStore();
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [researchId, setResearchId] = useState<string>("");

  const inProgress = research.filter((r) => r.status === "in_progress");
  const selectedId = researchId || inProgress[0]?.id || "";

  const spend = async (action: string, researchIdArg?: string) => {
    if (pending) return;
    setPending(action);
    setError(null);
    try {
      const res = await api.spendEnergy(action, researchIdArg);
      NexusManager.setAgentEnergy(res.agentEnergy);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPending(null);
    }
  };

  const afford = (action: string) => agentEnergy.current >= ACTION_COSTS[action]!;

  return (
    <div data-testid="agent-energy-widget">
      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Agent Energy</TerminalLabel>
          <span className="font-cmdmono text-cmd-cyan">
            {Math.round(agentEnergy.current)} <span className="text-cmd-textDim">/ {Math.round(agentEnergy.cap)}</span>
          </span>
        </div>
        <Meter value={agentEnergy.current} max={agentEnergy.cap} tone={agentEnergy.current < agentEnergy.cap * 0.25 ? "amber" : "cyan"} />
        <div className="mt-1 text-[9px] text-cmd-textDim">Regenerates +20 at the start of each in-game day.</div>

        <div className="mt-3 space-y-2">
          <div className="flex items-center gap-2">
            <select
              value={selectedId}
              onChange={(e) => setResearchId(e.target.value)}
              disabled={inProgress.length === 0}
              className="min-w-0 flex-1 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-cmd-text disabled:opacity-40"
            >
              {inProgress.length === 0 ? (
                <option value="">No in-progress research</option>
              ) : (
                inProgress.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title} ({Math.round(r.confidence)}%)
                  </option>
                ))
              )}
            </select>
            <EnergyButton
              label={`Boost (${ACTION_COSTS.research_boost}⚡)`}
              disabled={inProgress.length === 0 || !afford("research_boost") || pending !== null}
              busy={pending === "research_boost"}
              onClick={() => void spend("research_boost", selectedId)}
            />
          </div>
          <EnergyButton
            full
            label={`Queue Extra Simulation (${ACTION_COSTS.extra_simulation}⚡)`}
            disabled={!afford("extra_simulation") || pending !== null}
            busy={pending === "extra_simulation"}
            onClick={() => void spend("extra_simulation")}
          />
          <EnergyButton
            full
            label={`Watch New Symbol (${ACTION_COSTS.watch_symbol}⚡)`}
            disabled={!afford("watch_symbol") || pending !== null}
            busy={pending === "watch_symbol"}
            onClick={() => void spend("watch_symbol")}
          />
        </div>

        {error && <div className="mt-2 text-[9px] text-cmd-red">{error}</div>}
      </Glass>
    </div>
  );
}

function EnergyButton({
  label,
  disabled,
  busy,
  full = false,
  onClick,
}: {
  label: string;
  disabled: boolean;
  busy: boolean;
  full?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`shrink-0 rounded-sm border border-cmd-border px-2 py-1 text-cmd-textDim hover:enabled:text-cmd-cyan hover:enabled:border-cmd-cyan/50 disabled:opacity-30 ${full ? "w-full" : ""}`}
    >
      {busy ? "…" : label}
    </button>
  );
}
