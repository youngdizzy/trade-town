import { useEffect, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { api } from "@/net/api";
import type { CompiledStrategyDefinition, Strategy, StrategyPerformanceSummary } from "@/types";
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
import { EmaPullbackResearchView } from "./sandbox/EmaPullbackResearchView";
import { StrategyCompilerView } from "./sandbox/StrategyCompilerView";
import { QuantResearchLabView } from "./sandbox/QuantResearchLabView";
import { LiveStrategyEligibilityCard } from "./sandbox/LiveStrategyEligibilityCard";
import { StrategyTradingDiagnosticsView } from "./sandbox/StrategyTradingDiagnosticsView";
import { ChampionChallengerView } from "./sandbox/ChampionChallengerView";
import { ResearchFactoryView } from "./sandbox/ResearchFactoryView";

const SUB_TABS = [
  "PIPELINE",
  "LIBRARY",
  "CERTIFICATION",
  "HEALTH",
  "EVOLUTION",
  "HALL OF FAME",
  "FAILED ARCHIVE",
  "DASHBOARD",
  "50 EMA RESEARCH",
  "STRATEGY COMPILER",
  "QUANT RESEARCH LAB",
  "CHAMPION/CHALLENGER",
  "RESEARCH FACTORY",
] as const;
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
 * (the two permanent real outcomes of a retirement), DASHBOARD (a
 * real, computed-on-request company-wide aggregate), and 50 EMA RESEARCH
 * (CEO directive "Market-Analysis Knowledge + Session Intelligence
 * Expansion," Phase 15 — a real, on-demand bar-by-bar backtest of the
 * 50 EMA breakout + pullback strategy against real (mock) candle
 * history, kept explicitly separate from the CEO-supplied source
 * material's own claimed win rate — see
 * backend/app/ema_pullback_research.py), and STRATEGY COMPILER (CEO
 * directive "Professional Quant Trading Firm — Quant Intelligence +
 * Market Analysis Completion Phase," Phase F — a real, deterministic
 * English-language strategy compiler and generic backtest engine, never
 * an LLM guess; ambiguous phrasing is refused, not silently converted
 * into an invented threshold — see backend/app/strategy_compiler.py /
 * backend/app/strategy_engine.py), and QUANT RESEARCH LAB (CEO directive
 * "Professional Quant Firm Phase," Features 36/37/40 — files a real,
 * hypothesis-driven experiment into a permanent, searchable archive,
 * registers real persisted strategy version history, and runs a
 * multi-strategy tournament across every real validation axis via
 * named-slot superlatives and staged elimination rounds, never a
 * fabricated composite score — see backend/app/quant_research_lab.py /
 * backend/app/strategy_registry.py / backend/app/strategy_tournament.py).
 * See docs/Architecture.md's Feature 52 sections for the full honesty
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
  const [compilerSeed, setCompilerSeed] = useState<CompiledStrategyDefinition | null>(null);
  const [compilerSeedError, setCompilerSeedError] = useState<string | null>(null);
  // CEO directive "Live Trade → Strategy Provenance," Phase 11 — the
  // Strategy Library's real live-P&L column (backend/app/
  // performance_attribution.py's compute_strategy_performance(), the
  // same Phase 4 data already rendered in the Performance panel — never
  // a second, independently-computed reading).
  const [strategyPerformance, setStrategyPerformance] = useState<StrategyPerformanceSummary | null>(null);
  useEffect(() => {
    api.getPerformanceByStrategy().then(setStrategyPerformance).catch(() => undefined);
  }, []);

  const selected = strategies.find((s) => s.id === selectedId) ?? null;
  const openStrategy = (id: string) => {
    setSelectedId(id);
    setSubTab("CERTIFICATION");
  };
  // CEO directive "Strategy Intelligence + Live Strategy Attribution,"
  // Phase 1 — a real Strategy's own already-registered compiled rules
  // (see app/strategy_registry.py's register_researchable_strategy()),
  // opened directly in the Strategy Compiler rather than making the CEO
  // retype the English text from scratch.
  const openCompiledRules = (strategy: Strategy) => {
    setCompilerSeedError(null);
    api
      .getStrategyVersions(strategy.name)
      .then((versions) => {
        const latest = versions[versions.length - 1];
        if (!latest) {
          setCompilerSeedError(`No registered compiled definition found for "${strategy.name}" — it may have been registered under a different name.`);
          return;
        }
        setCompilerSeed(latest);
        setSubTab("STRATEGY COMPILER");
      })
      .catch((err) => setCompilerSeedError(err instanceof Error ? err.message : String(err)));
  };

  return (
    <div className="space-y-3">
      <LiveStrategyEligibilityCard strategies={strategies} />

      <StrategyTradingDiagnosticsView />
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
        <>
          {compilerSeedError && (
            <Glass className="p-3">
              <div className="text-[9px] text-cmd-red">{compilerSeedError}</div>
            </Glass>
          )}
          <StrategyLibraryView
            strategies={strategies}
            simulationResults={simulationResults}
            healthAssessments={strategyHealthAssessments}
            livePerformance={strategyPerformance}
            onOpen={openStrategy}
            onOpenCompiledRules={openCompiledRules}
          />
        </>
      )}
      {subTab === "HALL OF FAME" && <StrategyHallOfFameView entries={strategyHallOfFame} />}
      {subTab === "FAILED ARCHIVE" && <StrategyFailedArchiveView entries={strategyFailedArchive} />}
      {subTab === "DASHBOARD" && <StrategyExecutiveDashboardView />}
      {subTab === "50 EMA RESEARCH" && <EmaPullbackResearchView />}
      {subTab === "STRATEGY COMPILER" && <StrategyCompilerView seed={compilerSeed} />}
      {subTab === "QUANT RESEARCH LAB" && <QuantResearchLabView />}
      {subTab === "CHAMPION/CHALLENGER" && <ChampionChallengerView />}
      {subTab === "RESEARCH FACTORY" && <ResearchFactoryView />}

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
