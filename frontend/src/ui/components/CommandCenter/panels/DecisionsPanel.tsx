import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { TradeDecision } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { voteDirection } from "../lib/derive";
import { EmptyState, TerminalLabel } from "../ui";

type Filter = "all" | "trade" | "no_trade";

/** The full, exhaustive decision log — every TradeDecision TradeTown has ever recorded, filterable, newest first. */
export function DecisionsPanel({ onInspect }: { onInspect: (d: TradeDecision) => void }) {
  const { decisions } = useGameStore();
  const [filter, setFilter] = useState<Filter>("all");

  const filtered = [...decisions].reverse().filter((d) => filter === "all" || d.outcome === filter);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <TerminalLabel>Decision Log ({filtered.length} of {decisions.length})</TerminalLabel>
        <div className="flex gap-1.5">
          <FilterButton label="All" active={filter === "all"} onClick={() => setFilter("all")} />
          <FilterButton label="Trade" active={filter === "trade"} onClick={() => setFilter("trade")} />
          <FilterButton label="No Trade" active={filter === "no_trade"} onClick={() => setFilter("no_trade")} />
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState>No decisions match this filter.</EmptyState>
      ) : (
        <div className="overflow-x-auto rounded-sm border border-cmd-border">
          <table className="w-full">
            <thead>
              <tr className="border-b border-cmd-border bg-cmd-panel/60 text-[9px] uppercase tracking-wide text-cmd-textDim">
                <th className="px-2 py-1.5 text-left">Symbol</th>
                <th className="px-2 py-1.5 text-left">Direction</th>
                <th className="px-2 py-1.5 text-left">Confidence</th>
                <th className="px-2 py-1.5 text-left">Outcome</th>
                <th className="px-2 py-1.5 text-left">Led By</th>
                <th className="px-2 py-1.5 text-left">Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d) => (
                <tr key={d.id} onClick={() => onInspect(d)} className="cursor-pointer border-b border-cmd-border/40 last:border-0 hover:bg-cmd-panelLight/60">
                  <td className="px-2 py-1.5 font-cmdmono text-cmd-cyan">{d.symbol}</td>
                  <td className="px-2 py-1.5 text-cmd-textDim">{voteDirection(d.votes)}</td>
                  <td className="px-2 py-1.5 text-cmd-text">{Math.round(d.confidence)}%</td>
                  <td className={`px-2 py-1.5 ${d.outcome === "trade" ? "text-cmd-green" : "text-cmd-amber"}`}>{d.outcome === "trade" ? "TRADE" : "NO TRADE"}</td>
                  <td className="px-2 py-1.5 text-cmd-textDim">{d.supportingAgents.length ? AGENT_PROFILES[d.supportingAgents[0]!].name : "—"}</td>
                  <td className="max-w-[280px] truncate px-2 py-1.5 text-cmd-textDim">{d.finalReasoning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function FilterButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-sm border px-2.5 py-1 text-[9px] uppercase tracking-wide transition-colors ${
        active ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
      }`}
    >
      {label}
    </button>
  );
}
