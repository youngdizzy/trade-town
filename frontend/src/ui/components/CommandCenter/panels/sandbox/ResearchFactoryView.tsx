import { useEffect, useState } from "react";
import { api } from "@/net/api";
import { AGENT_IDS } from "@/types";
import type {
  AgentId,
  CandidacyBinning,
  CandidateLifecycleStage,
  FactoryCandidateRecord,
  FactoryRunRecord,
  FactoryStatsRead,
  FamilyResearchStats,
  ParetoStatus,
  ResearchDiscoveryCycleRecord,
  ResearchExperimentRecord,
  ResearchLoopIterationRecord,
  ResearchScorecardClassification,
  StrategyScorecard,
} from "@/types";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";

const CANDIDACY_TONE: Record<CandidacyBinning, "green" | "amber" | "red" | "purple"> = {
  accepted: "green",
  promising: "green",
  fragile: "amber",
  rejected: "red",
  duplicate: "purple",
  insufficient_evidence: "purple",
  overfit: "red",
  benchmark_failed: "amber",
  risk_failed: "red",
};

const LIFECYCLE_TONE: Record<CandidateLifecycleStage, "green" | "amber" | "red" | "purple"> = {
  generated: "purple",
  duplicate_pruned: "purple",
  compile_rejected: "red",
  backtested: "purple",
  candidate: "amber",
  adversarial_tested: "amber",
  rejected: "red",
  survivor: "green",
  challenger_eligible: "green",
};

const SCORECARD_TONE: Record<ResearchScorecardClassification, "green" | "amber" | "red" | "purple"> = {
  rejected: "red",
  fragile: "amber",
  promising: "amber",
  robust: "green",
  champion_candidate: "green",
};

const FACTORY_PIPELINE_LABELS = ["OBSERVE", "GENERATE", "MUTATE", "COMPILE", "BACKTEST", "VALIDATE", "STRESS", "COMPARE", "ACCEPT / BIN"];

const PARETO_TONE: Record<ParetoStatus, "green" | "amber" | "red" | "purple"> = {
  non_dominated: "green",
  dominated: "amber",
};

const VERDICT_TONE: Record<string, "green" | "amber" | "red" | "purple"> = {
  clean: "green",
  stable: "green",
  cost_resilient: "green",
  robust: "green",
  sufficient_evidence: "green",
  fragile: "amber",
  unstable: "red",
  cost_sensitive: "red",
  weak: "red",
  violations_found: "red",
  insufficient_evidence: "purple",
  not_validatable: "purple",
};

function FunnelStage({ label, verdict }: { label: string; verdict: string | null }) {
  const tone = verdict !== null ? (VERDICT_TONE[verdict] ?? "neutral") : "neutral";
  return (
    <div className="flex flex-col items-center gap-0.5 text-center">
      <span className="text-[8px] uppercase tracking-wide text-cmd-textDim">{label}</span>
      <StatusPill tone={tone}>{verdict !== null ? verdict.replace(/_/g, " ") : "NOT VERIFIED"}</StatusPill>
    </div>
  );
}

function ScorecardRow({ label, value }: { label: string; value: string | number | boolean | null }) {
  return <DataRow label={label} value={value === null ? "NOT VERIFIED" : String(value)} />;
}

// CEO directive "Phase 9: Real Market Data + Evidence Integrity
// Foundation," Section 24 — surfaces dataset provenance/quality/feature
// version disclosure alongside a candidate's other real evidence.
// Never claims "REAL HISTORICAL DATA" — this codebase's mock provider
// is the only real implementation, so dataCategory is always
// "simulated" today; that is stated plainly, not hidden.
function DataProvenanceLine({ experiment }: { experiment: ResearchExperimentRecord }) {
  const meta = experiment.datasetMetadata;
  return (
    <p className="mt-1 text-[8px] text-cmd-textDim">
      <span className="uppercase tracking-wide">
        {meta ? `${meta.dataCategory === "simulated" ? "SIMULATED DATA" : meta.dataCategory.toUpperCase()} · v${meta.datasetVersion} · coverage ${meta.coveragePct.toFixed(0)}%` : "DATASET METADATA NOT VERIFIED"}
      </span>
      {" · "}
      point-in-time {experiment.pointInTimeVerified === null ? "NOT VERIFIED" : experiment.pointInTimeVerified ? "verified clean" : "VIOLATIONS FOUND"}
      {" · "}
      {experiment.featureVersions.length > 0 ? `${experiment.featureVersions.length} feature version(s)` : "no indicators referenced"}
    </p>
  );
}

// CEO directive "Phase 9: Full Autonomous Quant Research Factory,"
// Phases 15/16 — real sibling ranking + Research Council disclosure.
// `siblingRank`/`fitnessRationale` are null for every single-child
// generation (never a vacuous "rank 1 of 1"); `researchCouncil` is null
// for a candidate that never reached a real backtest.
function CouncilAndSiblingLine({ candidate }: { candidate: FactoryCandidateRecord }) {
  if (candidate.siblingRank === null && candidate.researchCouncil === null) return null;
  return (
    <div className="mt-1 text-[8px] text-cmd-textDim">
      {candidate.siblingRank !== null && candidate.fitnessRationale && (
        <p>
          <span className="uppercase tracking-wide text-cmd-cyan">Fitness rank:</span> {candidate.fitnessRationale}
        </p>
      )}
      {candidate.researchCouncil && (
        <p className="mt-0.5">
          <span className="uppercase tracking-wide text-cmd-cyan">Research Council →</span> {candidate.researchCouncil.recommendation.replace(/_/g, " ")}: {candidate.researchCouncil.recommendationReason}
        </p>
      )}
    </div>
  );
}

// CEO directive "TradeTown — Autonomous Mutation Application + Pareto
// Survivor Engine" — real, disclosed multi-dimensional Pareto dominance
// (backend/app/research_pareto.py), never a single opaque score.
// `null` for any candidate with no real backtest to compare
// (compile_rejected/duplicate_pruned).
function ParetoStatusLine({ candidate }: { candidate: FactoryCandidateRecord }) {
  if (candidate.paretoStatus === null) return null;
  return (
    <div className="mt-1 flex items-start gap-2 text-[8px] text-cmd-textDim">
      <StatusPill tone={PARETO_TONE[candidate.paretoStatus]}>{candidate.paretoStatus.replace(/_/g, " ")}</StatusPill>
      <p>{candidate.paretoReason}</p>
    </div>
  );
}

function renderScorecard(scorecard: StrategyScorecard) {
  return (
    <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
      <div>
        <ScorecardRow label="Trade count" value={scorecard.tradeCount} />
        <ScorecardRow label="Win rate" value={scorecard.winRatePct !== null ? `${scorecard.winRatePct.toFixed(1)}%` : null} />
        <ScorecardRow label="Avg win / loss (R)" value={scorecard.avgWinR !== null && scorecard.avgLossR !== null ? `${scorecard.avgWinR.toFixed(2)} / ${scorecard.avgLossR.toFixed(2)}` : null} />
        <ScorecardRow label="Expectancy (R)" value={scorecard.expectancyR !== null ? scorecard.expectancyR.toFixed(3) : null} />
        <ScorecardRow label="Profit factor" value={scorecard.profitFactor !== null ? scorecard.profitFactor.toFixed(2) : null} />
        <ScorecardRow label="Max drawdown (R)" value={scorecard.maxDrawdownR !== null ? scorecard.maxDrawdownR.toFixed(2) : null} />
        <ScorecardRow label="Total return (R)" value={scorecard.totalReturnR !== null ? scorecard.totalReturnR.toFixed(2) : null} />
      </div>
      <div>
        <ScorecardRow label="Benchmark return" value={scorecard.benchmarkReturnPct !== null ? `${scorecard.benchmarkReturnPct.toFixed(1)}%` : null} />
        <ScorecardRow label="Excess return (approx.)" value={scorecard.excessReturnApproxPct !== null ? `${scorecard.excessReturnApproxPct >= 0 ? "+" : ""}${scorecard.excessReturnApproxPct.toFixed(1)}%` : null} />
        <ScorecardRow label="Outlier dependent" value={scorecard.outlierDependent} />
        <ScorecardRow label="Largest win share of return" value={scorecard.largestWinShareOfReturnPct !== null ? `${scorecard.largestWinShareOfReturnPct.toFixed(0)}%` : null} />
        <ScorecardRow label="Tuning exposure (version)" value={scorecard.tuningExposureVersion} />
        <ScorecardRow label="Research family experiment count" value={scorecard.researchFamilyExperimentCount} />
        <ScorecardRow label="Statistical evidence" value={scorecard.statisticalEvidenceState} />
      </div>
    </div>
  );
}

/**
 * CEO directive "TradeTown — Next Major Implementation Pass, Phase 4-6:
 * Self-Improving Strategy Factory + Validation Funnel," Section 19 — a
 * transparent Research Factory view. Every number here comes from the
 * real backend evidence backend/app/research_loop.py computes (see that
 * module's own docstring) — no black-box "AI quality score" anywhere:
 * the scorecard shows individual dimensions, each traceable to real
 * evidence or explicitly "NOT VERIFIED" when this codebase genuinely
 * has none yet.
 */
export function ResearchFactoryView() {
  const [name, setName] = useState("");
  const [sourceText, setSourceText] = useState(
    "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
  );
  const [hypothesis, setHypothesis] = useState("");
  const [marketMechanism, setMarketMechanism] = useState("");
  const [expectedEdge, setExpectedEdge] = useState("");
  const [invalidationConditions, setInvalidationConditions] = useState("");
  const [proposedBy, setProposedBy] = useState<AgentId>("quant");
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [result, setResult] = useState<ResearchLoopIterationRecord | null>(null);
  const [history, setHistory] = useState<ResearchLoopIterationRecord[]>([]);
  const [factoryRunning, setFactoryRunning] = useState(false);
  const [factoryError, setFactoryError] = useState<string | null>(null);
  const [factoryRun, setFactoryRun] = useState<FactoryRunRecord | null>(null);
  const [factoryRuns, setFactoryRuns] = useState<FactoryRunRecord[]>([]);
  const [factoryStats, setFactoryStats] = useState<FactoryStatsRead | null>(null);

  useEffect(() => {
    api
      .getResearchLoopIterations()
      .then(setHistory)
      .catch(() => undefined);
  }, [result?.id]);

  useEffect(() => {
    api
      .getResearchFactoryRuns()
      .then(setFactoryRuns)
      .catch(() => undefined);
    api
      .getResearchFactoryStats()
      .then(setFactoryStats)
      .catch(() => undefined);
  }, [factoryRun?.id]);

  function buildHypothesis(timeframe: string): Parameters<typeof api.runResearchLoopIteration>[0] {
    return {
      id: `hyp-${Date.now()}`,
      hypothesis: hypothesis || "No stated hypothesis.",
      marketMechanism: marketMechanism || "Not stated.",
      expectedEdge: expectedEdge || "Not stated.",
      invalidationConditions: invalidationConditions || "Not stated.",
      symbolUniverse: ["AAPL"],
      timeframe,
      entryConditions: "See compiled definition.",
      exitConditions: "See compiled definition.",
      stopLossLogic: "See compiled definition.",
      takeProfitLogic: "See compiled definition.",
      positionSizingLogic: "Fixed risk per trade (CEO-configured RiskLimits.riskPerTradePct).",
      riskConstraints: "Standard.",
      indicatorsFeatures: [],
      regimeAssumptions: "",
      researchRationale: "",
      parentStrategyFamily: null,
      parentDefinitionId: null,
      parentDefinitionVersion: null,
      proposedBy,
      createdAt: new Date().toISOString(),
      generation: 0,
      lineageId: null,
      reasonForGeneration: null,
      lessonsUsed: [],
      failureCodesAddressed: [],
      mutationOperatorUsed: null,
      expectedImprovement: null,
      expectedRisk: null,
      reproducibilitySeed: null,
      sourceEvidenceIds: [],
    };
  }

  async function runFunnel() {
    setRunning(true);
    setRunError(null);
    try {
      const definition = await api.compileStrategy(name, sourceText);
      if (definition.status !== "compiled") {
        setRunError(definition.detail ?? "Compilation did not succeed — see ambiguities.");
        return;
      }
      const iteration = await api.runResearchLoopIteration(buildHypothesis(definition.timeframe), definition);
      setResult(iteration);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  }

  async function runFactory() {
    setFactoryRunning(true);
    setFactoryError(null);
    try {
      const definition = await api.compileStrategy(name, sourceText);
      if (definition.status !== "compiled") {
        setFactoryError(definition.detail ?? "Compilation did not succeed — see ambiguities.");
        return;
      }
      const run = await api.runResearchFactoryRun(buildHypothesis(definition.timeframe), definition);
      setFactoryRun(run);
    } catch (err) {
      setFactoryError(err instanceof Error ? err.message : String(err));
    } finally {
      setFactoryRunning(false);
    }
  }

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <TerminalLabel>Research Factory — hypothesis to funnel decision, never a black-box score</TerminalLabel>
        <p className="mt-1 text-[9px] text-cmd-textDim">
          Runs the real backtest/cost/walk-forward/parameter-sensitivity/look-ahead pipeline, a real benchmark comparison, and a real, transparent candidacy
          decision — every number below traces to real evidence or reads &quot;NOT VERIFIED.&quot; This candidate layer is separate from, and never
          weaker than, Certification/Hall of Fame/Champion-Challenger, which stay the sole authoritative promotion path.
        </p>
        <div className="mt-2 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Strategy name"
            className="w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          />
          <select
            value={proposedBy}
            onChange={(e) => setProposedBy(e.target.value as AgentId)}
            className="w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          >
            {AGENT_IDS.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </div>
        <textarea
          value={sourceText}
          onChange={(e) => setSourceText(e.target.value)}
          rows={2}
          placeholder="Describe the strategy's rules in plain English…"
          className="mt-1.5 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
        />
        <textarea
          value={hypothesis}
          onChange={(e) => setHypothesis(e.target.value)}
          rows={2}
          placeholder='Hypothesis — what market behavior are you attempting to exploit? (e.g. "trend continuation after a confirmed breakout")'
          className="mt-1.5 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
        />
        <textarea
          value={marketMechanism}
          onChange={(e) => setMarketMechanism(e.target.value)}
          rows={1}
          placeholder="Market mechanism — why would this work?"
          className="mt-1.5 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
        />
        <textarea
          value={expectedEdge}
          onChange={(e) => setExpectedEdge(e.target.value)}
          rows={1}
          placeholder="Expected edge"
          className="mt-1.5 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
        />
        <textarea
          value={invalidationConditions}
          onChange={(e) => setInvalidationConditions(e.target.value)}
          rows={1}
          placeholder="Invalidation conditions — what would prove this wrong?"
          className="mt-1.5 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
        />
        <div className="mt-2 flex flex-wrap gap-1.5">
          <button
            type="button"
            disabled={running || !name.trim() || !sourceText.trim()}
            onClick={runFunnel}
            className="rounded-sm border border-cmd-border px-3 py-1.5 text-[9px] uppercase text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
          >
            {running ? "Running full funnel…" : "Run Research Funnel (single pass)"}
          </button>
          <button
            type="button"
            disabled={factoryRunning || !name.trim() || !sourceText.trim()}
            onClick={runFactory}
            title="Automatically generates, mutates, compiles, and re-tests successive real strategy versions — bounded, deterministic, never LLM-driven. See app/research_factory.py."
            className="rounded-sm border border-cmd-purple/60 px-3 py-1.5 text-[9px] uppercase text-cmd-purple transition-colors hover:enabled:border-cmd-purple hover:enabled:text-cmd-text disabled:opacity-40"
          >
            {factoryRunning ? "Running autonomous factory cycle…" : "Run Autonomous Factory Cycle"}
          </button>
        </div>
        {runError && <div className="mt-1.5 text-[9px] text-cmd-red">{runError}</div>}
        {factoryError && <div className="mt-1.5 text-[9px] text-cmd-red">{factoryError}</div>}
      </Glass>

      {factoryRun && (
        <>
          <Glass className="p-3">
            <TerminalLabel>Factory Status — Run {factoryRun.id}</TerminalLabel>
            <p className="mt-1 text-[9px] text-cmd-textDim">
              Automatic OBSERVE→GENERATE→MUTATE→COMPILE→BACKTEST→VALIDATE→STRESS→COMPARE→ACCEPT/BIN loop. Every generation reuses the same real funnel above —
              never a second backtest engine. No candidate is ever auto-submitted to Champion/Challenger or given live/paper execution authority.
            </p>
            <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-0.5 sm:grid-cols-3">
              <DataRow label="Generations completed" value={factoryRun.generationsCompleted} />
              <DataRow label="Candidates generated" value={factoryRun.candidatesGenerated} />
              <DataRow label="Candidates compiled" value={factoryRun.candidatesCompiled} />
              <DataRow label="Candidates backtested" value={factoryRun.candidatesBacktested} />
              <DataRow label="Candidates rejected" value={factoryRun.candidatesRejected} />
              <DataRow label="Survivors" value={factoryRun.survivorCandidateIds.length} />
              <DataRow
                label="Current champion"
                value={factoryRun.currentChampionDefinitionId ? `${factoryRun.currentChampionDefinitionId} v${factoryRun.currentChampionDefinitionVersion}` : "none yet"}
              />
              <DataRow label="Budget (family)" value={`${factoryRun.config.maxIterationsPerFamily} iterations / ${factoryRun.config.maxMutationsPerParent} mutations/parent`} />
              <DataRow label="Run budget" value={`${factoryRun.config.maxGenerations} generations / ${factoryRun.config.maxTotalBacktests} backtests`} />
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-1 border-t border-cmd-border/40 pt-2 text-[8px] uppercase tracking-wide text-cmd-textDim">
              {FACTORY_PIPELINE_LABELS.map((label, i) => (
                <span key={label} className="flex items-center gap-1">
                  <span className="rounded-sm border border-cmd-border/60 px-1.5 py-0.5">{label}</span>
                  {i < FACTORY_PIPELINE_LABELS.length - 1 && <span className="text-cmd-textDim/50">→</span>}
                </span>
              ))}
            </div>
            <p className="mt-2 border-t border-cmd-border/40 pt-2 text-[9px] text-cmd-text">
              <span className="text-cmd-cyan">Stop reason:</span> {factoryRun.stopReason}
            </p>
            {factoryRun.topRejectionReasons.length > 0 && (
              <p className="mt-1 text-[9px] text-cmd-textDim">
                <span className="text-cmd-cyan">Top rejection reasons:</span> {factoryRun.topRejectionReasons.join(", ")}
              </p>
            )}
            {factoryRun.topLessons.length > 0 && (
              <div className="mt-1 text-[9px] text-cmd-textDim">
                <span className="text-cmd-cyan">Lessons filed this run:</span>
                <ul className="ml-3 mt-0.5 list-disc space-y-0.5">
                  {factoryRun.topLessons.map((lesson, i) => (
                    <li key={i}>{lesson}</li>
                  ))}
                </ul>
              </div>
            )}
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Candidate Lineage — every generation, real evidence, never deleted</TerminalLabel>
            {factoryRun.candidates.map((candidate) => (
              <div key={candidate.id} className="mt-2 border-t border-cmd-border/40 pt-2 first:mt-0 first:border-0 first:pt-0">
                <div className="flex flex-wrap items-center justify-between gap-1">
                  <span className="text-[9px] text-cmd-text">
                    Gen {candidate.generation} — v{candidate.definitionVersion}
                    {candidate.parentCandidateId && <span className="text-cmd-textDim"> (child of {candidate.parentCandidateId})</span>}
                  </span>
                  <StatusPill tone={LIFECYCLE_TONE[candidate.lifecycleStage]}>{candidate.lifecycleStage.replace(/_/g, " ")}</StatusPill>
                </div>
                <p className="mt-0.5 text-[9px] text-cmd-textDim">{candidate.hypothesis.hypothesis}</p>
                {candidate.iteration && (
                  <div className="mt-1 grid grid-cols-2 gap-x-4 sm:grid-cols-4">
                    <DataRow label="Trades" value={candidate.iteration.scorecard.tradeCount ?? "NOT VERIFIED"} />
                    <DataRow label="PF" value={candidate.iteration.scorecard.profitFactor?.toFixed(2) ?? "NOT VERIFIED"} />
                    <DataRow label="Max DD (R)" value={candidate.iteration.scorecard.maxDrawdownR?.toFixed(2) ?? "NOT VERIFIED"} />
                    <DataRow label="Expectancy (R)" value={candidate.iteration.scorecard.expectancyR?.toFixed(3) ?? "NOT VERIFIED"} />
                    <DataRow label="Excess return (approx.)" value={candidate.iteration.scorecard.excessReturnApproxPct !== null ? `${candidate.iteration.scorecard.excessReturnApproxPct.toFixed(1)}%` : "NOT VERIFIED"} />
                    <DataRow label="Walk-forward" value={candidate.iteration.scorecard.walkForwardVerdict ?? "NOT VERIFIED"} />
                    <DataRow label="Cost sensitivity" value={candidate.iteration.scorecard.costSensitivityVerdict ?? "NOT VERIFIED"} />
                    <DataRow label="Regime" value={candidate.iteration.scorecard.regimeRobustnessVerdict ?? "NOT VERIFIED"} />
                  </div>
                )}
                {candidate.iteration && <DataProvenanceLine experiment={candidate.iteration.experiment} />}
                {candidate.mutationCandidate && (
                  <p className="mt-1 text-[9px] text-cmd-text">
                    <span className="text-cmd-cyan">Mutation ({candidate.mutationCandidate.mutationType.replace(/_/g, " ")}):</span> {candidate.mutationCandidate.rationale}
                    {candidate.mutationCandidate.mutatedSourceText === null && <span className="text-cmd-textDim italic"> — no bounded automatic operator; {candidate.mutationCandidate.constraints}</span>}
                  </p>
                )}
                <CouncilAndSiblingLine candidate={candidate} />
                <ParetoStatusLine candidate={candidate} />
                <p className="mt-0.5 text-[9px] text-cmd-textDim">{candidate.decisionReason}</p>
              </div>
            ))}
          </Glass>
        </>
      )}

      {factoryRuns.length > 0 && (
        <Glass className="p-3">
          <div className="flex items-center justify-between">
            <TerminalLabel>Factory Run History — permanent, never overwritten</TerminalLabel>
            {factoryStats && (
              <span className="text-[8px] text-cmd-textDim">
                {factoryStats.totalRuns} runs · {factoryStats.totalCandidates} candidates · {factoryStats.totalSurvivors} survivors · {factoryStats.totalRejected} rejected
              </span>
            )}
          </div>
          {[...factoryRuns].reverse().slice(0, 10).map((r) => (
            <div key={r.id} className="mt-1 flex items-center justify-between border-t border-cmd-border/40 pt-1 text-[9px] first:mt-0 first:border-0 first:pt-0">
              <span className="text-cmd-text">
                {r.strategyFamily} — {r.generationsCompleted} gen(s)
              </span>
              <StatusPill tone={r.survivorCandidateIds.length > 0 ? "green" : "red"}>{r.survivorCandidateIds.length > 0 ? "survivor found" : "no survivor"}</StatusPill>
            </div>
          ))}
        </Glass>
      )}

      <DiscoveryCyclePanel />

      {result && (
        <>
          <Glass className="p-3">
            <TerminalLabel>Funnel — Hypothesis → Backtest → Cost → Walk-Forward → Regime → Robustness → Statistics → Benchmark → Decision</TerminalLabel>
            <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
              <FunnelStage label="Look-Ahead" verdict={result.scorecard.lookAheadVerdict} />
              <FunnelStage label="Cost" verdict={result.scorecard.costSensitivityVerdict} />
              <FunnelStage label="Walk-Forward" verdict={result.scorecard.walkForwardVerdict} />
              <FunnelStage label="Regime" verdict={result.scorecard.regimeRobustnessVerdict} />
              <FunnelStage label="Parameters" verdict={result.scorecard.parameterRobustnessVerdict} />
              <FunnelStage label="Statistics" verdict={result.scorecard.statisticalEvidenceState} />
              <FunnelStage label="Benchmark" verdict={result.benchmarkComparisons.length > 0 ? (result.benchmarkComparisons.every((b) => b.beatsBenchmark) ? "beats" : "trails") : null} />
            </div>
            <div className="mt-2 flex items-center justify-between border-t border-cmd-border/40 pt-2">
              <TerminalLabel>Candidacy Decision</TerminalLabel>
              <StatusPill tone={CANDIDACY_TONE[result.candidacy]}>{result.candidacy.replace(/_/g, " ")}</StatusPill>
            </div>
            <p className="mt-1 text-[9px] text-cmd-text">{result.candidacyReason}</p>
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Strategy Scorecard — every dimension traceable to real evidence, never a black-box score</TerminalLabel>
            <div className="mt-2">{renderScorecard(result.scorecard)}</div>
          </Glass>

          {result.benchmarkComparisons.length > 0 && (
            <Glass className="p-3">
              <TerminalLabel>Benchmark Comparison — approximate, never blended units</TerminalLabel>
              {result.benchmarkComparisons.map((bc) => (
                <div key={bc.symbol} className="mt-1 border-t border-cmd-border/40 pt-1 first:mt-0 first:border-0 first:pt-0">
                  <div className="flex items-center justify-between text-[9px]">
                    <span className="text-cmd-text">{bc.symbol}</span>
                    <StatusPill tone={bc.beatsBenchmark ? "green" : "red"}>{bc.beatsBenchmark ? "beats benchmark" : "trails benchmark"}</StatusPill>
                  </div>
                  <DataRow label="Benchmark (buy & hold)" value={`${bc.benchmarkReturnPct.toFixed(1)}%`} />
                  <DataRow label="Strategy (approx. equity return)" value={`${bc.strategyEquityReturnApproxPct.toFixed(1)}%`} />
                  <DataRow label="Excess (approx.)" value={`${bc.excessReturnApproxPct >= 0 ? "+" : ""}${bc.excessReturnApproxPct.toFixed(1)}%`} />
                  <p className="mt-0.5 text-[8px] italic text-cmd-textDim">{bc.approximationNote}</p>
                </div>
              ))}
            </Glass>
          )}

          {result.failureCodes.length > 0 && (
            <Glass className="p-3">
              <TerminalLabel>Failure Diagnosis</TerminalLabel>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {result.failureCodes.map((f, i) => (
                  <div key={i} className="flex items-center gap-1 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 px-1.5 py-0.5 text-[8px]" title={f.evidence}>
                    <StatusPill tone={f.severity === "critical" || f.severity === "high" ? "red" : f.severity === "medium" ? "amber" : "neutral"}>{f.severity}</StatusPill>
                    <span className="text-cmd-text">{f.code.replace(/_/g, " ")}</span>
                  </div>
                ))}
              </div>
            </Glass>
          )}

          {result.mutation && (
            <Glass className="p-3">
              <TerminalLabel>Proposed Mutation — a real recommendation, never auto-applied</TerminalLabel>
              <DataRow label="Observed failure" value={result.mutation.observedFailureCodes.join(", ").replace(/_/g, " ")} />
              <p className="mt-1 text-[9px] text-cmd-text">
                <span className="text-cmd-cyan">Change:</span> {result.mutation.proposedChange}
              </p>
              <p className="mt-0.5 text-[9px] text-cmd-textDim">
                <span className="text-cmd-cyan">Reason:</span> {result.mutation.reason}
              </p>
              <p className="mt-0.5 text-[9px] text-cmd-textDim">
                <span className="text-cmd-cyan">Expected effect:</span> {result.mutation.expectedEffect}
              </p>
              <p className="mt-1 text-[8px] italic text-cmd-textDim">
                Not auto-applied — re-testing this idea still goes through the existing Strategy Compiler, exactly like any other new version.
              </p>
            </Glass>
          )}

          {(result.similarFailedStrategies.length > 0 || result.researchRelationship !== "novel") && (
            <Glass className="p-3">
              <div className="flex items-center justify-between">
                <TerminalLabel>Research Memory</TerminalLabel>
                <StatusPill tone={result.researchRelationship === "similar_failure" || result.researchRelationship === "contradictory_evidence" ? "red" : result.researchRelationship === "near_duplicate" ? "amber" : "green"}>
                  {result.researchRelationship.replace(/_/g, " ")}
                </StatusPill>
              </div>
              {result.similarFailedStrategies.map((m) => (
                <div key={m.strategyArchiveId} className="mt-1 border-t border-cmd-border/40 pt-1 text-[9px] first:mt-0 first:border-0 first:pt-0">
                  <span className="text-cmd-text">
                    Similar to retired &quot;{m.strategyName}&quot; ({(m.overlapScore * 100).toFixed(0)}% overlap) — failed at {m.failedAtStage.replace(/_/g, " ")}
                  </span>
                </div>
              ))}
            </Glass>
          )}

          <Glass className="p-3">
            <TerminalLabel>Research Budget</TerminalLabel>
            <DataRow label="Experiments attempted (this family)" value={`${result.budget.experimentsAttempted} / ${result.budget.maxIterationsPerFamily}`} />
            <DataRow label="Mutations for this parent" value={`${result.budget.mutationsForThisParent} / ${result.budget.maxMutationsPerParent}`} />
            {result.budget.stopped && <div className="mt-1 text-[9px] text-cmd-red">⚠ {result.budget.stopReason}</div>}
          </Glass>
        </>
      )}

      {history.length > 0 && (
        <Glass className="p-3">
          <TerminalLabel>Research Iteration History — permanent, never overwritten</TerminalLabel>
          {[...history].reverse().slice(0, 15).map((h) => (
            <div key={h.id} className="mt-1 flex items-center justify-between border-t border-cmd-border/40 pt-1 text-[9px] first:mt-0 first:border-0 first:pt-0">
              <span className="text-cmd-text">{h.strategyFamily}</span>
              <StatusPill tone={CANDIDACY_TONE[h.candidacy]}>{h.candidacy.replace(/_/g, " ")}</StatusPill>
            </div>
          ))}
        </Glass>
      )}

      {!result && history.length === 0 && (
        <Glass className="p-3">
          <EmptyState>No research-loop iteration has been run yet.</EmptyState>
        </Glass>
      )}
    </div>
  );
}

/**
 * CEO directive "TradeTown — Phase 8: Autonomous Strategy Discovery +
 * Adversarial Research Engine." Generates a controlled, deterministic
 * candidate POPULATION across multiple real, compiler-supported
 * strategy families, prunes real near-duplicates, and attacks every
 * real survivor via app/adversarial_research.py's real attack suite —
 * see backend/app/research_discovery.py's own module docstring for the
 * full real architecture and its disclosed scope boundary (one real
 * generation per population member).
 */
function DiscoveryCyclePanel() {
  const [conceptName, setConceptName] = useState("Discovery Cycle");
  const [populationSize, setPopulationSize] = useState(6);
  const [seed, setSeed] = useState(() => `seed-${Date.now()}`);
  const [proposedBy, setProposedBy] = useState<AgentId>("quant");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cycle, setCycle] = useState<ResearchDiscoveryCycleRecord | null>(null);
  const [cycles, setCycles] = useState<ResearchDiscoveryCycleRecord[]>([]);
  const [familyStats, setFamilyStats] = useState<FamilyResearchStats[]>([]);
  const [unsupported, setUnsupported] = useState<Record<string, string>>({});

  useEffect(() => {
    api
      .getResearchDiscoveryCycles()
      .then(setCycles)
      .catch(() => undefined);
    api
      .getResearchDiscoveryFamilyStats()
      .then(setFamilyStats)
      .catch(() => undefined);
    api
      .getResearchDiscoverySupportedFamilies()
      .then((r) => setUnsupported(r.unsupported))
      .catch(() => undefined);
  }, [cycle?.id]);

  async function runCycle() {
    setRunning(true);
    setError(null);
    try {
      const record = await api.runResearchDiscoveryCycle(conceptName, populationSize, seed, proposedBy, { symbols: ["AAPL"] });
      setCycle(record);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <TerminalLabel>Strategy Discovery Cycle — a diverse population, real near-duplicate pruning, real adversarial attacks</TerminalLabel>
        <p className="mt-1 text-[9px] text-cmd-textDim">
          Generates a controlled, deterministic candidate population across multiple real, compiler-supported strategy families (never 30 mutations of one parent), prunes
          real near-duplicates before spending research budget, and attacks every real survivor (outlier removal, worst-period, sequence reshuffle, extended cost, regime).
          Each real candidate runs the SAME unmodified research funnel — this never bypasses a hard gate. Runtime scales with population size (each candidate re-runs a full
          real backtest plus adversarial suite) — a population of 6 typically takes several minutes.
        </p>
        {Object.keys(unsupported).length > 0 && (
          <p className="mt-1 text-[8px] italic text-cmd-textDim">Not generated (real, disclosed compiler limitations): {Object.keys(unsupported).join(", ")}.</p>
        )}
        <div className="mt-2 grid grid-cols-2 gap-1.5 sm:grid-cols-4">
          <input
            type="text"
            value={conceptName}
            onChange={(e) => setConceptName(e.target.value)}
            placeholder="Concept name"
            className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          />
          <input
            type="number"
            min={1}
            max={30}
            value={populationSize}
            onChange={(e) => setPopulationSize(Math.max(1, Math.min(30, Number(e.target.value) || 1)))}
            placeholder="Population size"
            className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          />
          <input
            type="text"
            value={seed}
            onChange={(e) => setSeed(e.target.value)}
            placeholder="Deterministic seed"
            className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          />
          <select
            value={proposedBy}
            onChange={(e) => setProposedBy(e.target.value as AgentId)}
            className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          >
            {AGENT_IDS.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          disabled={running || !conceptName.trim()}
          onClick={runCycle}
          className="mt-2 rounded-sm border border-cmd-purple/60 px-3 py-1.5 text-[9px] uppercase text-cmd-purple transition-colors hover:enabled:border-cmd-purple hover:enabled:text-cmd-text disabled:opacity-40"
        >
          {running ? "Generating population and attacking survivors…" : "Run Discovery Cycle"}
        </button>
        {error && <div className="mt-1.5 text-[9px] text-cmd-red">{error}</div>}
      </Glass>

      {cycle && (
        <>
          <Glass className="p-3">
            <TerminalLabel>Discovery Cycle {cycle.id} — Status</TerminalLabel>
            <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-0.5 sm:grid-cols-3">
              <DataRow label="Population size" value={cycle.populationSize} />
              <DataRow label="Duplicates pruned" value={cycle.duplicatesPruned} />
              <DataRow label="Survivors" value={cycle.survivorCandidateIds.length} />
              <DataRow label="Champion candidates" value={cycle.championCandidateIds.length} />
              <DataRow label="Holdout" value={cycle.holdout.status === "available" ? "available" : "NOT AVAILABLE"} />
            </div>
            <p className="mt-1.5 text-[8px] italic text-cmd-textDim">{cycle.holdout.reason}</p>
            <p className="mt-1.5 border-t border-cmd-border/40 pt-1.5 text-[9px] text-cmd-text">{cycle.stopReason}</p>
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Family Research Statistics — real, decomposable, never a black-box score</TerminalLabel>
            <div className="mt-1.5 overflow-x-auto">
              <table className="w-full text-[8px]">
                <thead>
                  <tr className="text-left text-cmd-textDim">
                    <th className="pr-2">Family</th>
                    <th className="pr-2">Gen</th>
                    <th className="pr-2">BT</th>
                    <th className="pr-2">Avg Exp (R)</th>
                    <th className="pr-2">Cost Surv %</th>
                    <th>Allocation</th>
                  </tr>
                </thead>
                <tbody>
                  {cycle.familyStats.map((fs) => {
                    const allocation = cycle.allocationDecisions.find((a) => a.family === fs.family);
                    return (
                      <tr key={fs.family} className="border-t border-cmd-border/30">
                        <td className="py-0.5 pr-2 text-cmd-text">{fs.family.replace(/_/g, " ")}</td>
                        <td className="pr-2">{fs.numberGenerated}</td>
                        <td className="pr-2">{fs.numberBacktested}</td>
                        <td className="pr-2">{fs.averageExpectancyR !== null ? fs.averageExpectancyR.toFixed(3) : "NOT VERIFIED"}</td>
                        <td className="pr-2">{fs.costSurvivalRatePct !== null ? `${fs.costSurvivalRatePct.toFixed(0)}%` : "NOT VERIFIED"}</td>
                        <td>{allocation ? `${allocation.allocationWeightPct.toFixed(1)}%` : "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Population — every candidate, real evidence, never deleted</TerminalLabel>
            {cycle.candidates.map((candidate) => (
              <div key={candidate.id} className="mt-2 border-t border-cmd-border/40 pt-2 first:mt-0 first:border-0 first:pt-0">
                <div className="flex flex-wrap items-center justify-between gap-1">
                  <span className="text-[9px] text-cmd-text">
                    {candidate.researchFamily?.replace(/_/g, " ") ?? "—"}
                    {candidate.discoveryReason && <span className="text-cmd-textDim"> · {candidate.discoveryReason.replace(/_/g, " ")}</span>}
                  </span>
                  <div className="flex items-center gap-1">
                    <StatusPill tone={LIFECYCLE_TONE[candidate.lifecycleStage]}>{candidate.lifecycleStage.replace(/_/g, " ")}</StatusPill>
                    {candidate.scorecardClassification && (
                      <StatusPill tone={SCORECARD_TONE[candidate.scorecardClassification]}>{candidate.scorecardClassification.replace(/_/g, " ")}</StatusPill>
                    )}
                  </div>
                </div>
                {candidate.duplicateOfCandidateId && <p className="mt-0.5 text-[8px] italic text-cmd-textDim">Duplicate of {candidate.duplicateOfCandidateId} — never backtested.</p>}
                {candidate.iteration && (
                  <div className="mt-1 grid grid-cols-2 gap-x-4 sm:grid-cols-4">
                    <DataRow label="Trades" value={candidate.iteration.scorecard.tradeCount ?? "NOT VERIFIED"} />
                    <DataRow label="Expectancy (R)" value={candidate.iteration.scorecard.expectancyR?.toFixed(3) ?? "NOT VERIFIED"} />
                    <DataRow label="PF" value={candidate.iteration.scorecard.profitFactor?.toFixed(2) ?? "NOT VERIFIED"} />
                    <DataRow label="Max DD (R)" value={candidate.iteration.scorecard.maxDrawdownR?.toFixed(2) ?? "NOT VERIFIED"} />
                  </div>
                )}
                {candidate.iteration && <DataProvenanceLine experiment={candidate.iteration.experiment} />}
                {candidate.adversarialResult && (
                  <div className="mt-1 grid grid-cols-2 gap-x-4 sm:grid-cols-3">
                    <DataRow label="Outlier resilience" value={candidate.adversarialResult.outlierResilience.classification.replace(/_/g, " ")} />
                    <DataRow label="Regime" value={candidate.adversarialResult.regimeRobustness.classification.replace(/_/g, " ")} />
                    <DataRow
                      label="Survives beyond stress"
                      value={candidate.adversarialResult.extendedCostAttack.survivesBeyondStress === null ? "NOT VERIFIED" : candidate.adversarialResult.extendedCostAttack.survivesBeyondStress}
                    />
                  </div>
                )}
                {candidate.adversarialResult && candidate.adversarialResult.failureBoundaries.length > 0 && (
                  <div className="mt-1 text-[8px] text-cmd-textDim">
                    {candidate.adversarialResult.failureBoundaries.map((fb) => (
                      <div key={fb.id}>
                        {fb.failureBoundaryMetric}: survives until{" "}
                        {fb.failureBoundaryValue !== null ? fb.failureBoundaryValue.toFixed(1) : "not observed to fail within the tested range"} (confidence: {fb.confidence})
                      </div>
                    ))}
                  </div>
                )}
                <CouncilAndSiblingLine candidate={candidate} />
                <ParetoStatusLine candidate={candidate} />
                <p className="mt-0.5 text-[9px] text-cmd-textDim">{candidate.decisionReason}</p>
              </div>
            ))}
          </Glass>
        </>
      )}

      {cycles.length > 0 && (
        <Glass className="p-3">
          <TerminalLabel>Discovery Cycle History — permanent, never overwritten</TerminalLabel>
          {[...cycles].reverse().slice(0, 10).map((c) => (
            <div key={c.id} className="mt-1 flex items-center justify-between border-t border-cmd-border/40 pt-1 text-[9px] first:mt-0 first:border-0 first:pt-0">
              <span className="text-cmd-text">
                {c.conceptName} — {c.populationSize} candidates
              </span>
              <StatusPill tone={c.survivorCandidateIds.length > 0 ? "green" : "red"}>{c.survivorCandidateIds.length} survivor(s)</StatusPill>
            </div>
          ))}
        </Glass>
      )}

      {familyStats.length > 0 && !cycle && (
        <Glass className="p-3">
          <TerminalLabel>Family Research Statistics — across every real discovery cycle ever run</TerminalLabel>
          {familyStats.map((fs) => (
            <div key={fs.family} className="mt-1 flex items-center justify-between border-t border-cmd-border/40 pt-1 text-[9px] first:mt-0 first:border-0 first:pt-0">
              <span className="text-cmd-text">{fs.family.replace(/_/g, " ")}</span>
              <span className="text-cmd-textDim">
                {fs.numberGenerated} generated · avg exp {fs.averageExpectancyR !== null ? fs.averageExpectancyR.toFixed(3) : "N/A"}
              </span>
            </div>
          ))}
        </Glass>
      )}
    </div>
  );
}
