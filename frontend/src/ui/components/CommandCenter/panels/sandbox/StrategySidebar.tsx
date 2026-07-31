import type { Strategy, StrategyHealthAssessment } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { STAGE_LABELS, strategyHealthTone } from "../../lib/derive";
import { StatusPill, TerminalLabel } from "../../ui";

function latestHealth(strategyId: string, assessments: StrategyHealthAssessment[]): StrategyHealthAssessment | null {
  const own = assessments.filter((a) => a.strategyId === strategyId);
  return own.length > 0 ? own[own.length - 1]! : null;
}

/** Shared left-column strategy roster used by every strategy-scoped
 * Strategy Validation Laboratory sub-view (Pipeline/Certification/
 * Health/Evolution) so the CEO's current selection persists across
 * sub-tabs instead of resetting on every switch. */
export function StrategySidebar({
  strategies,
  healthAssessments,
  selectedId,
  onSelect,
}: {
  strategies: Strategy[];
  healthAssessments: StrategyHealthAssessment[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="space-y-1.5">
      {strategies.map((s) => {
        const health = latestHealth(s.id, healthAssessments);
        return (
          <button
            key={s.id}
            type="button"
            onClick={() => onSelect(s.id)}
            className={`w-full rounded-sm border p-2 text-left text-[9px] ${selectedId === s.id ? "border-cmd-cyan/60 bg-cmd-cyan/10" : "border-cmd-border/60 bg-cmd-bg/40 hover:border-cmd-border"} ${s.stage === "retired" ? "opacity-70" : ""}`}
          >
            <div className="flex items-center justify-between gap-1.5">
              <span className="truncate text-cmd-cyan">{s.name}</span>
              <StatusPill tone={s.stage === "retired" ? "neutral" : s.stage === "approved" ? "green" : "cyan"}>{STAGE_LABELS[s.stage]}</StatusPill>
            </div>
            <div className="mt-0.5 flex items-center justify-between text-cmd-textDim">
              <span>
                {s.focusCategory} — {AGENT_PROFILES[s.createdBy].name}
              </span>
              {health && <StatusPill tone={strategyHealthTone(health.status)}>{health.status.replace(/_/g, " ")}</StatusPill>}
            </div>
          </button>
        );
      })}
    </div>
  );
}

export function StrategySidebarPanel({
  strategies,
  healthAssessments,
  selectedId,
  onSelect,
}: {
  strategies: Strategy[];
  healthAssessments: StrategyHealthAssessment[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="rounded-sm border border-cmd-border bg-cmd-panel/80 p-3 backdrop-blur-sm lg:col-span-1">
      <TerminalLabel>Strategies — no strategy skips a stage</TerminalLabel>
      <p className="mb-2 text-[9px] text-cmd-textDim">
        Idea → Research → Historical Backtest → Market Simulation → Paper Trading → Limited Live Capital → Company Review → Approved. Retirement is a real, deliberate CEO call reachable
        from any stage.
      </p>
      <StrategySidebar strategies={strategies} healthAssessments={healthAssessments} selectedId={selectedId} onSelect={onSelect} />
    </div>
  );
}
