import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { EmptyState, Glass } from "../ui";
import { StrategySidebarPanel } from "./sandbox/StrategySidebar";
import { StrategyPipelineView } from "./sandbox/StrategyPipelineView";
import { StrategyCertificationView } from "./sandbox/StrategyCertificationView";
import { StrategyHealthView } from "./sandbox/StrategyHealthView";
import { StrategyEvolutionView } from "./sandbox/StrategyEvolutionView";
import { StrategyLibraryView } from "./sandbox/StrategyLibraryView";
import { StrategyHallOfFameView } from "./sandbox/StrategyHallOfFameView";
import { StrategyFailedArchiveView } from "./sandbox/StrategyFailedArchiveView";
import { StrategyExecutiveDashboardView } from "./sandbox/StrategyExecutiveDashboardView";

const SUB_TABS = ["PIPELINE", "LIBRARY", "CERTIFICATION", "HEALTH", "EVOLUTION", "HALL OF FAME", "FAILED ARCHIVE", "DASHBOARD"] as const;
type SubTab = (typeof SUB_TABS)[number];

const STRATEGY_SCOPED: ReadonlySet<SubTab> = new Set(["PIPELINE", "CERTIFICATION", "HEALTH", "EVOLUTION"]);

/**
 * v0.7 Feature 45/52 — the Strategy Validation Laboratory. One Command
 * Center tab, split into real sub-views rather than eight more top-level
 * tabs (this Command Center already carries 31 — see FullCommandCenter.tsx's
 * own TABS array): PIPELINE (the original Research Sandbox — queue
 * backtests, walk the real CEO-authorized stage checkpoints, retire),
 * LIBRARY (every strategy this company has ever created, nothing ever
 * deleted), CERTIFICATION (the full real validation dossier — Monte
 * Carlo/Regime Test/Liquidity/9-department Executive Review/Founder
 * Approval/Confidence Score), HEALTH (a real recent-vs-lifetime
 * performance trend — an honest reframe of the brief's "Live Performance
 * Monitor," since this codebase has no live-trade-to-Strategy
 * attribution to monitor), EVOLUTION (this strategy's own real stage
 * history plus its retirement outcome — an honest reframe of the
 * brief's "Strategy Evolution," since this codebase has no strategy
 * versioning mechanism to show instead), HALL OF FAME / FAILED ARCHIVE
 * (the two permanent real outcomes of a retirement), and DASHBOARD (a
 * real, computed-on-request company-wide aggregate). See
 * docs/Architecture.md's Feature 52 sections for the full honesty
 * boundary each sub-view observes.
 */
export function SandboxPanel() {
  const {
    strategies,
    backtestSessions,
    simulationResults,
    strategyReports,
    strategyReviews,
    strategyModelValidations,
    strategyHealthAssessments,
    strategyHallOfFame,
    strategyFailedArchive,
    watchlist,
  } = useGameStore();
  const [subTab, setSubTab] = useState<SubTab>("PIPELINE");
  const [selectedId, setSelectedId] = useState<string | null>(strategies[0]?.id ?? null);

  const selected = strategies.find((s) => s.id === selectedId) ?? null;
  const openStrategy = (id: string) => {
    setSelectedId(id);
    setSubTab("CERTIFICATION");
  };

  return (
    <div className="space-y-3">
      <nav className="flex flex-wrap gap-1 rounded-sm border border-cmd-border bg-cmd-panel/60 p-1.5">
        {SUB_TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setSubTab(t)}
            className={`whitespace-nowrap rounded-sm px-2.5 py-1 text-[9px] uppercase tracking-wide transition-colors ${
              subTab === t ? "border border-cmd-cyan/40 bg-cmd-cyan/10 text-cmd-cyan shadow-cmd-cyan" : "border border-transparent text-cmd-textDim hover:text-cmd-text"
            }`}
          >
            {t}
          </button>
        ))}
      </nav>

      {subTab === "LIBRARY" && (
        <StrategyLibraryView strategies={strategies} simulationResults={simulationResults} healthAssessments={strategyHealthAssessments} onOpen={openStrategy} />
      )}
      {subTab === "HALL OF FAME" && <StrategyHallOfFameView entries={strategyHallOfFame} />}
      {subTab === "FAILED ARCHIVE" && <StrategyFailedArchiveView entries={strategyFailedArchive} />}
      {subTab === "DASHBOARD" && <StrategyExecutiveDashboardView />}

      {STRATEGY_SCOPED.has(subTab) && (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          <StrategySidebarPanel strategies={strategies} healthAssessments={strategyHealthAssessments} selectedId={selectedId} onSelect={setSelectedId} />
          {!selected ? (
            <Glass className="p-3 lg:col-span-2">
              <EmptyState>Select a strategy to open its Research Sandbox.</EmptyState>
            </Glass>
          ) : (
            <div className="lg:col-span-2">
              {subTab === "PIPELINE" && (
                <StrategyPipelineView
                  selected={selected}
                  backtestSessions={backtestSessions}
                  simulationResults={simulationResults}
                  strategyReports={strategyReports}
                  strategyReviews={strategyReviews}
                  strategyModelValidations={strategyModelValidations}
                  watchlist={watchlist}
                />
              )}
              {subTab === "CERTIFICATION" && <StrategyCertificationView selected={selected} />}
              {subTab === "HEALTH" && <StrategyHealthView selected={selected} healthAssessments={strategyHealthAssessments} />}
              {subTab === "EVOLUTION" && (
                <StrategyEvolutionView
                  selected={selected}
                  hallOfFameEntry={strategyHallOfFame.find((e) => e.strategyId === selected.id) ?? null}
                  failedArchiveEntry={strategyFailedArchive.find((e) => e.strategyId === selected.id) ?? null}
                />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
