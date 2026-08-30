import { useEffect, useState } from "react";
import { api } from "@/net/api";
import { AGENT_IDS } from "@/types";
import type { AgentId, CandidacyBinning, CandidateLifecycleStage, FactoryRunRecord, FactoryStatsRead, ResearchLoopIterationRecord, StrategyScorecard } from "@/types";
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
  compile_rejected: "red",
  backtested: "purple",
  candidate: "amber",
  rejected: "red",
  survivor: "green",
  challenger_eligible: "green",
};

const FACTORY_PIPELINE_LABELS = ["OBSERVE", "GENERATE", "MUTATE", "COMPILE", "BACKTEST", "VALIDATE", "STRESS", "COMPARE", "ACCEPT / BIN"];

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
                {candidate.mutationCandidate && (
                  <p className="mt-1 text-[9px] text-cmd-text">
                    <span className="text-cmd-cyan">Mutation ({candidate.mutationCandidate.mutationType.replace(/_/g, " ")}):</span> {candidate.mutationCandidate.rationale}
                    {candidate.mutationCandidate.mutatedSourceText === null && <span className="text-cmd-textDim italic"> — no bounded automatic operator; {candidate.mutationCandidate.constraints}</span>}
                  </p>
                )}
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
