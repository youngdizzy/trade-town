import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import type { SimulationResult, Strategy, StrategyHealthAssessment } from "@/types";
import { STAGE_LABELS, strategyHealthTone } from "../../lib/derive";
import { EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";

function aggregate(strategyId: string, results: SimulationResult[]): { runs: number; avgReturnPct: number; avgWinRate: number } {
  const own = results.filter((r) => r.strategyId === strategyId);
  if (own.length === 0) return { runs: 0, avgReturnPct: 0, avgWinRate: 0 };
  return {
    runs: own.length,
    avgReturnPct: own.reduce((sum, r) => sum + r.totalReturnPct, 0) / own.length,
    avgWinRate: own.reduce((sum, r) => sum + r.winRate, 0) / own.length,
  };
}

/**
 * v0.7 Feature 52 (Part 2) — "Strategy Library." Every real field the
 * brief's Library section asks for (creator/status/stage/description/
 * risk profile/historical performance) already lives on the real
 * Strategy object plus its own SimulationResult/StrategyHealthAssessment
 * history — see docs/Architecture.md's Part 2 section for why no new
 * backend artifact was needed here. Nothing is ever deleted: every
 * strategy this company has ever created, including retired ones,
 * stays in this roster permanently.
 */
export function StrategyLibraryView({
  strategies,
  simulationResults,
  healthAssessments,
  onOpen,
  onOpenCompiledRules,
}: {
  strategies: Strategy[];
  simulationResults: SimulationResult[];
  healthAssessments: StrategyHealthAssessment[];
  onOpen: (id: string) => void;
  onOpenCompiledRules: (strategy: Strategy) => void;
}) {
  return (
    <Glass className="p-3">
      <TerminalLabel>Strategy Library — every strategy this company has ever created, nothing ever deleted</TerminalLabel>
      {strategies.length === 0 ? (
        <EmptyState>No strategies on file yet.</EmptyState>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[9px]">
            <thead>
              <tr className="border-b border-cmd-border text-cmd-textDim">
                <th className="px-1.5 py-1.5 text-left">Strategy</th>
                <th className="px-1.5 py-1.5 text-left">Creator</th>
                <th className="px-1.5 py-1.5 text-left">Focus</th>
                <th className="px-1.5 py-1.5 text-left">Stage</th>
                <th className="px-1.5 py-1.5 text-left">Rules</th>
                <th className="px-1.5 py-1.5 text-left">Health</th>
                <th className="px-1.5 py-1.5 text-left">Runs</th>
                <th className="px-1.5 py-1.5 text-left">Avg Return</th>
                <th className="px-1.5 py-1.5 text-left">Avg Win Rate</th>
                <th className="px-1.5 py-1.5" />
              </tr>
            </thead>
            <tbody>
              {strategies.map((s) => {
                const stats = aggregate(s.id, simulationResults);
                const own = healthAssessments.filter((h) => h.strategyId === s.id);
                const health = own[own.length - 1] ?? null;
                return (
                  <tr key={s.id} className={`border-b border-cmd-border/40 ${s.stage === "retired" ? "opacity-70" : ""}`}>
                    <td className="px-1.5 py-1.5">
                      <div className="text-cmd-cyan">{s.name}</div>
                      <div className="text-cmd-textDim">{s.description}</div>
                    </td>
                    <td className="px-1.5 py-1.5 text-cmd-text">{AGENT_PROFILES[s.createdBy].name}</td>
                    <td className="px-1.5 py-1.5 text-cmd-textDim">{s.focusCategory}</td>
                    <td className="px-1.5 py-1.5">
                      <StatusPill tone={s.stage === "retired" ? "neutral" : s.stage === "approved" ? "green" : "cyan"}>{STAGE_LABELS[s.stage]}</StatusPill>
                    </td>
                    <td className="px-1.5 py-1.5">
                      {s.compiledDefinitionId ? (
                        <button
                          type="button"
                          onClick={() => onOpenCompiledRules(s)}
                          className="rounded-sm border border-cmd-purple/50 px-2 py-0.5 text-[9px] uppercase text-cmd-purple hover:bg-cmd-purple/10"
                          title="Real, compiled trigger/entry/stop/target rules exist for this strategy — open in the Strategy Compiler."
                        >
                          View Rules
                        </button>
                      ) : (
                        <span className="text-cmd-textDim" title="No represented trading logic yet — a tracked idea only.">
                          —
                        </span>
                      )}
                    </td>
                    <td className="px-1.5 py-1.5">{health ? <StatusPill tone={strategyHealthTone(health.status)}>{health.status.replace(/_/g, " ")}</StatusPill> : <span className="text-cmd-textDim">—</span>}</td>
                    <td className="px-1.5 py-1.5 tabular-nums text-cmd-textDim">{stats.runs}</td>
                    <td className={`px-1.5 py-1.5 tabular-nums ${stats.avgReturnPct >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>
                      {stats.runs > 0 ? `${stats.avgReturnPct >= 0 ? "+" : ""}${stats.avgReturnPct.toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-1.5 py-1.5 tabular-nums text-cmd-text">{stats.runs > 0 ? `${stats.avgWinRate.toFixed(0)}%` : "—"}</td>
                    <td className="px-1.5 py-1.5">
                      <button type="button" onClick={() => onOpen(s.id)} className="rounded-sm border border-cmd-cyan/50 px-2 py-0.5 text-[9px] uppercase text-cmd-cyan hover:bg-cmd-cyan/10">
                        Open
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Glass>
  );
}
