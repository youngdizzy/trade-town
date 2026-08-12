import { useMemo, useState } from "react";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { NexusManager } from "@/game/systems/NexusManager";
import { api } from "@/net/api";
import type { BacktestSession, ModelValidationReport, Strategy, StrategyReport, StrategyReview, StrategyStage, StrategyVerdict, SimulationResult, TestScenario, WatchlistEntry } from "@/types";
import { STAGE_LABELS, computeStrategyConsistency } from "../../lib/derive";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../../ui";

const STAGE_ORDER: StrategyStage[] = ["idea", "research", "historical_backtest", "market_simulation", "paper_trading", "limited_live_capital", "company_review", "approved"];

const SCENARIO_LABELS: Record<TestScenario, string> = {
  historical: "Historical",
  bull: "Bull Market",
  bear: "Bear Market",
  sideways: "Sideways",
  high_volatility: "High Volatility",
  low_volatility: "Low Volatility",
  custom: "Custom",
};

const VERDICT_TONE: Record<StrategyVerdict, "green" | "amber" | "red"> = { pass: "green", concern: "amber", fail: "red" };

// v0.7 Quantitative Research & Intelligence System, Piece 4.
const MODEL_VALIDATION_TONE: Record<ModelValidationReport["verdict"], "green" | "amber" | "red" | "neutral"> = {
  approved: "green",
  rejected: "red",
  needs_more_evidence: "amber",
  not_validatable: "neutral",
};

// Trading Psychology & Discipline, Piece B — mirrors backend/app/strategy_lab.py's
// real MIN_RETIREMENT_TRADE_COUNT exactly (the Statistical Evidence Gate
// on Strategy Retirement). A strategy still at "idea"/"research" has no
// real evidence bar to clear — see evaluate_retirement_readiness()'s own
// docstring.
const MIN_RETIREMENT_TRADE_COUNT = 10;

/**
 * v0.7 Feature 45/52 — the Research Sandbox pipeline: queue real
 * backtests, review per-run metrics, and walk a strategy through its
 * real CEO-authorized trust checkpoints (Paper Trading/Limited Live
 * Capital/Company Review/Approved), ending in either full deployment or
 * a real, deliberate Retire decision (v0.7 Feature 52 Part 2) — never
 * fabricated live P&L attribution, see backend/app/sandbox.py's module
 * docstring.
 */
export function StrategyPipelineView({
  selected,
  backtestSessions,
  simulationResults,
  strategyReports,
  strategyReviews,
  strategyModelValidations,
  watchlist,
}: {
  selected: Strategy;
  backtestSessions: BacktestSession[];
  simulationResults: SimulationResult[];
  strategyReports: StrategyReport[];
  strategyReviews: StrategyReview[];
  strategyModelValidations: ModelValidationReport[];
  watchlist: WatchlistEntry[];
}) {
  const [scenario, setScenario] = useState<TestScenario>("historical");
  const [customBias, setCustomBias] = useState(0);
  const [customVol, setCustomVol] = useState(1);
  const [liveAmount, setLiveAmount] = useState(500);
  const [retireReason, setRetireReason] = useState("");
  const [showRetireForm, setShowRetireForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ownResults = useMemo(() => simulationResults.filter((r) => r.strategyId === selected.id), [selected, simulationResults]);
  const ownReports = useMemo(() => strategyReports.filter((r) => r.strategyId === selected.id), [selected, strategyReports]);
  const ownReviews = useMemo(() => strategyReviews.filter((r) => r.strategyId === selected.id), [selected, strategyReviews]);
  const pendingReview = ownReviews.find((r) => r.ceoDecision === "pending");
  const latestModelValidation = useMemo(() => {
    const own = strategyModelValidations.filter((r) => r.strategyId === selected.id);
    return own.length > 0 ? own[own.length - 1] : null;
  }, [selected, strategyModelValidations]);
  const activeSessions = useMemo(() => backtestSessions.filter((s) => s.strategyId === selected.id && s.status !== "completed"), [selected, backtestSessions]);
  const consistency = computeStrategyConsistency(selected.id, simulationResults);
  const totalTradeCount = useMemo(() => ownResults.reduce((sum, r) => sum + r.tradeCount, 0), [ownResults]);
  const enteredRealTesting = STAGE_ORDER.indexOf(selected.stage) >= STAGE_ORDER.indexOf("historical_backtest");
  const evidenceReady = !enteredRealTesting || totalTradeCount >= MIN_RETIREMENT_TRADE_COUNT;

  const runAction = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const queueBacktest = () =>
    runAction(async () => {
      const res = await api.queueSandboxBacktest(selected.id, scenario, customBias, customVol);
      NexusManager.setBacktestSessions(res.backtestSessions);
    });

  const beginPaperTrial = () =>
    runAction(async () => {
      const res = await api.beginSandboxPaperTrial(selected.id);
      NexusManager.setSandboxState(res.strategies, res.strategyReviews);
    });

  const beginLimitedLive = () =>
    runAction(async () => {
      const res = await api.beginSandboxLimitedLive(selected.id, liveAmount);
      NexusManager.setSandboxState(res.strategies, res.strategyReviews);
    });

  const requestReview = () =>
    runAction(async () => {
      const res = await api.requestSandboxCompanyReview(selected.id);
      NexusManager.setStrategyExecutiveOutcome(res.strategies, res.strategyReviews, res.strategyExecutiveReviews[0] ?? null, res.strategyFounderApprovals[0] ?? null, res.strategyModelValidation);
    });

  const decide = (approve: boolean) =>
    runAction(async () => {
      if (!pendingReview) return;
      const res = await api.decideSandboxReview(pendingReview.id, approve);
      NexusManager.setSandboxState(res.strategies, res.strategyReviews);
    });

  const retire = () =>
    runAction(async () => {
      if (!retireReason.trim()) return;
      const res = await api.retireSandboxStrategy(selected.id, retireReason.trim());
      NexusManager.setStrategyRetirementOutcome(res.strategies, res.strategyHallOfFameEntry, res.strategyFailedArchiveEntry);
      setShowRetireForm(false);
      setRetireReason("");
    });

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>{selected.name} — Pipeline</TerminalLabel>
          <StatusPill tone={selected.stage === "retired" ? "neutral" : selected.stage === "approved" ? "green" : "cyan"}>{STAGE_LABELS[selected.stage]}</StatusPill>
        </div>
        <div className="mb-2 flex flex-wrap gap-1">
          {STAGE_ORDER.map((stage, i) => {
            const reached = selected.stage !== "retired" && STAGE_ORDER.indexOf(selected.stage) >= i;
            return (
              <span key={stage} className={`rounded-sm border px-1.5 py-0.5 text-[8px] uppercase tracking-wide ${reached ? "border-cmd-cyan/50 text-cmd-cyan" : "border-cmd-border/50 text-cmd-textDim"}`}>
                {STAGE_LABELS[stage]}
              </span>
            );
          })}
        </div>
        {selected.allocatedCapital > 0 && <DataRow label="Allocated Capital (authorization ceiling, not live P&L)" value={`$${selected.allocatedCapital.toLocaleString()}`} />}
        <div className="mt-1.5 space-y-1 border-t border-cmd-border/50 pt-1.5">
          {selected.stageHistory.map((event) => (
            <div key={event.id} className="text-[9px]">
              <span className="text-cmd-cyan">Day {event.simDay}</span> <span className="text-cmd-text">{event.detail}</span>
            </div>
          ))}
        </div>
      </Glass>

      {selected.stage !== "retired" && (
        <Glass className="p-3">
          <TerminalLabel>Testing Environments — queue a real backtest run</TerminalLabel>
          <p className="mb-2 text-[9px] text-cmd-textDim">
            7 real scenarios (Historical + the 5 live market regimes + Custom). No Earnings Weeks / Economic News — no real data source for either exists in this codebase.
          </p>
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-[9px] text-cmd-textDim">
              Scenario
              <select
                value={scenario}
                onChange={(e) => setScenario(e.target.value as TestScenario)}
                className="mt-1 block w-40 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
              >
                {(Object.keys(SCENARIO_LABELS) as TestScenario[]).map((s) => (
                  <option key={s} value={s}>
                    {SCENARIO_LABELS[s]}
                  </option>
                ))}
              </select>
            </label>
            {scenario === "custom" && (
              <>
                <label className="text-[9px] text-cmd-textDim">
                  Return Bias %
                  <input type="number" value={customBias} onChange={(e) => setCustomBias(Number(e.target.value))} className="mt-1 block w-20 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50" />
                </label>
                <label className="text-[9px] text-cmd-textDim">
                  Volatility ×
                  <input type="number" step="0.1" value={customVol} onChange={(e) => setCustomVol(Number(e.target.value))} className="mt-1 block w-20 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50" />
                </label>
              </>
            )}
            <button
              type="button"
              onClick={() => void queueBacktest()}
              disabled={busy || watchlist.length === 0}
              className="rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-cyan shadow-cmd-cyan transition-colors hover:bg-cmd-cyan/10 disabled:opacity-40"
            >
              Run Backtest
            </button>
          </div>
          {activeSessions.length > 0 && (
            <div className="mt-2 space-y-1.5 border-t border-cmd-border/50 pt-2">
              {activeSessions.map((s) => (
                <div key={s.id} className="text-[9px]">
                  <div className="flex items-center justify-between">
                    <span className="text-cmd-text">
                      {SCENARIO_LABELS[s.scenario]} on {s.symbol}
                    </span>
                    <span className="text-cmd-textDim">{s.status}</span>
                  </div>
                  <Meter value={s.progress} tone="cyan" />
                </div>
              ))}
            </div>
          )}
          {error && <div className="mt-2 text-[9px] text-cmd-red">{error}</div>}
        </Glass>
      )}

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Performance Metrics — real per-run history</TerminalLabel>
          {consistency.sampleSize > 0 && (
            <StatusPill tone="cyan">
              Consistency {consistency.positiveRunPct.toFixed(0)}% ({consistency.sampleSize} runs, {consistency.distinctScenarios} scenario{consistency.distinctScenarios === 1 ? "" : "s"})
            </StatusPill>
          )}
        </div>
        {ownResults.length === 0 ? (
          <EmptyState>No completed backtests yet.</EmptyState>
        ) : (
          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-[9px]">
              <thead>
                <tr className="border-b border-cmd-border text-cmd-textDim">
                  <th className="px-1 py-1 text-left">Scenario</th>
                  <th className="px-1 py-1 text-left">Return</th>
                  <th className="px-1 py-1 text-left">Win Rate</th>
                  <th className="px-1 py-1 text-left">EV/Trade</th>
                  <th className="px-1 py-1 text-left">Profit Factor</th>
                  <th className="px-1 py-1 text-left">Max DD</th>
                  <th className="px-1 py-1 text-left">Sharpe</th>
                  <th className="px-1 py-1 text-left">R:R</th>
                  <th className="px-1 py-1 text-left">Trades</th>
                </tr>
              </thead>
              <tbody>
                {[...ownResults].reverse().map((r) => (
                  <tr key={r.id} className="border-b border-cmd-border/40">
                    <td className="px-1 py-1 text-cmd-cyan">{SCENARIO_LABELS[r.scenario]}</td>
                    <td className={`px-1 py-1 tabular-nums ${r.totalReturnPct >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>
                      {r.totalReturnPct >= 0 ? "+" : ""}
                      {r.totalReturnPct.toFixed(1)}%
                    </td>
                    <td className="px-1 py-1 tabular-nums text-cmd-text">{r.winRate.toFixed(0)}%</td>
                    <td className="px-1 py-1 tabular-nums text-cmd-text">
                      {r.expectedValuePct >= 0 ? "+" : ""}
                      {r.expectedValuePct.toFixed(2)}%
                    </td>
                    <td className="px-1 py-1 tabular-nums text-cmd-text">{r.profitFactor.toFixed(2)}</td>
                    <td className="px-1 py-1 tabular-nums text-cmd-amber">{r.maxDrawdownPct.toFixed(1)}%</td>
                    <td className="px-1 py-1 tabular-nums text-cmd-text">{r.sharpeRatio.toFixed(2)}</td>
                    <td className="px-1 py-1 tabular-nums text-cmd-text">{r.riskRewardRatio.toFixed(2)}</td>
                    <td className="px-1 py-1 tabular-nums text-cmd-textDim">{r.tradeCount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Glass>

      {ownReports.length > 0 && (
        <Glass className="p-3">
          <TerminalLabel>Strategy Reports — auto-generated per run</TerminalLabel>
          <div className="space-y-2">
            {[...ownReports].reverse().map((report) => (
              <div key={report.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                <div className="mb-1 text-cmd-text">{report.executiveSummary}</div>
                {report.strengths.length > 0 && <div className="text-cmd-green">Strengths: {report.strengths.join(" ")}</div>}
                {report.weaknesses.length > 0 && <div className="text-cmd-amber">Weaknesses: {report.weaknesses.join(" ")}</div>}
                {report.failureConditions.length > 0 && <div className="text-cmd-red">Failure Conditions: {report.failureConditions.join(" ")}</div>}
                <DataRow label="Best Market Environment" value={report.bestMarketEnvironment} />
                {report.recommendedImprovements.length > 0 && <DataRow label="Recommended" value={report.recommendedImprovements.join(" ")} />}
              </div>
            ))}
          </div>
        </Glass>
      )}

      <Glass className="p-3">
        <TerminalLabel>Approval Process — advance the pipeline</TerminalLabel>
        <div className="flex flex-wrap items-center gap-2">
          {selected.stage === "market_simulation" && (
            <button type="button" onClick={() => void beginPaperTrial()} disabled={busy} className="rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40">
              Begin Paper Trading Trial
            </button>
          )}
          {selected.stage === "paper_trading" && (
            <>
              <label className="text-[9px] text-cmd-textDim">
                Capital ($)
                <input type="number" value={liveAmount} onChange={(e) => setLiveAmount(Number(e.target.value))} className="mt-1 block w-24 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50" />
              </label>
              <button type="button" onClick={() => void beginLimitedLive()} disabled={busy} className="rounded-sm border border-cmd-amber/50 px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-amber hover:bg-cmd-amber/10 disabled:opacity-40">
                Begin Limited Live Capital
              </button>
            </>
          )}
          {selected.stage === "limited_live_capital" && (
            <button type="button" onClick={() => void requestReview()} disabled={busy} className="rounded-sm border border-cmd-purple/50 px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-purple hover:bg-cmd-purple/10 disabled:opacity-40">
              Request Company Review
            </button>
          )}
          {selected.stage === "approved" && <StatusPill tone="green">APPROVED FOR FULL DEPLOYMENT</StatusPill>}
          {selected.stage === "retired" && <StatusPill tone="neutral">RETIRED — see Evolution tab for the real outcome</StatusPill>}
          {(selected.stage === "idea" || selected.stage === "research" || selected.stage === "historical_backtest") && (
            <span className="text-[9px] text-cmd-textDim">No CEO action available yet — this strategy still needs real evidence from earlier stages.</span>
          )}
        </div>

        {ownReviews.length > 0 && (
          <div className="mt-2 space-y-2 border-t border-cmd-border/50 pt-2">
            {[...ownReviews].reverse().map((review) => (
              <div key={review.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                <div className="mb-1 flex items-center justify-between">
                  <StatusPill tone={VERDICT_TONE[review.overallVerdict]}>{review.overallVerdict.toUpperCase()}</StatusPill>
                  <span className="text-cmd-textDim">{review.ceoDecision === "pending" ? "Awaiting CEO decision" : `${review.ceoDecision} (${review.resolvedBy})`}</span>
                </div>
                <div className="space-y-1">
                  {review.verdicts.map((v) => (
                    <div key={v.reviewerRole} className="flex items-start gap-1.5">
                      <StatusPill tone={VERDICT_TONE[v.verdict]}>{v.reviewerRole.replace(/_/g, " ")}</StatusPill>
                      <span className="text-cmd-textDim">({AGENT_PROFILES[v.reviewerAgent].name})</span>
                      <span className="flex-1 text-cmd-text">{v.summary}</span>
                    </div>
                  ))}
                </div>
                {review.ceoDecision === "pending" && (
                  <div className="mt-1.5 flex gap-2">
                    <button type="button" onClick={() => void decide(true)} disabled={busy} className="rounded-sm border border-cmd-green/50 px-2 py-0.5 text-[9px] uppercase text-cmd-green hover:bg-cmd-green/10 disabled:opacity-40">
                      Approve
                    </button>
                    <button type="button" onClick={() => void decide(false)} disabled={busy} className="rounded-sm border border-cmd-red/50 px-2 py-0.5 text-[9px] uppercase text-cmd-red hover:bg-cmd-red/10 disabled:opacity-40">
                      Reject
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Glass>

      {latestModelValidation && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Model Validation — Meridian (independent, advisory-only)</TerminalLabel>
            <StatusPill tone={MODEL_VALIDATION_TONE[latestModelValidation.verdict]}>{latestModelValidation.verdict.replace(/_/g, " ").toUpperCase()}</StatusPill>
          </div>
          <p className="mb-2 text-[9px] text-cmd-textDim">
            {latestModelValidation.evidenceSummary} This verdict is advisory only — it does not override or bypass Company Review, the Gatekeeper, Risk Authority, or any Circuit Breaker, and a
            rejection does not automatically change this strategy's stage.
          </p>
          <div className="space-y-1">
            {latestModelValidation.checks.map((check) => (
              <div key={check.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="mb-0.5 flex items-start gap-1.5">
                  <StatusPill tone={check.passed === true ? "green" : check.passed === false ? "red" : "neutral"}>{check.passed === true ? "pass" : check.passed === false ? "fail" : "n/a"}</StatusPill>
                  <span className="flex-1 text-cmd-text">{check.label}</span>
                </div>
                <p className="text-cmd-textDim">{check.evidence}</p>
                <p className="text-cmd-textDim">{check.reasoning}</p>
                <p className="text-cmd-textDim">Threshold: {check.thresholdSource}</p>
              </div>
            ))}
          </div>
          {latestModelValidation.dataSourcesAndAssumptions.length > 0 && (
            <div className="mt-2 space-y-0.5 border-t border-cmd-border/50 pt-2 text-[9px] text-cmd-textDim">
              {latestModelValidation.dataSourcesAndAssumptions.map((line, i) => (
                <p key={i}>{line}</p>
              ))}
            </div>
          )}
        </Glass>
      )}

      {selected.stage !== "retired" && (
        <Glass className="p-3">
          <TerminalLabel>Retirement — a real, deliberate CEO call, never automatic</TerminalLabel>
          <p className="mb-2 text-[9px] text-cmd-textDim">
            Reachable from any stage. Files exactly one real permanent record: a Strategy Hall of Fame induction if this strategy clears a strict real bar, or a Failed Strategy Archive
            entry citing its own real concerns otherwise — see the Hall of Fame / Failed Archive / Evolution tabs.
          </p>
          {enteredRealTesting && (
            <p className={`mb-2 text-[9px] ${evidenceReady ? "text-cmd-textDim" : "text-cmd-amber"}`}>
              Statistical Evidence Gate: {totalTradeCount} real trade(s) on file (needs ≥{MIN_RETIREMENT_TRADE_COUNT} before this strategy can be retired — a single bad run does not invalidate
              a strategy).
            </p>
          )}
          {!showRetireForm ? (
            <button type="button" onClick={() => setShowRetireForm(true)} className="rounded-sm border border-cmd-red/50 px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-red hover:bg-cmd-red/10">
              Retire This Strategy
            </button>
          ) : (
            <div className="flex flex-wrap items-end gap-2">
              <label className="flex-1 text-[9px] text-cmd-textDim">
                Real reason (cite this strategy's own Health read)
                <input
                  type="text"
                  value={retireReason}
                  onChange={(e) => setRetireReason(e.target.value)}
                  placeholder="e.g. Recent win rate has fallen below a comfortable bar."
                  className="mt-1 block w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-cmd-text outline-none focus:border-cmd-red/50"
                />
              </label>
              <button type="button" onClick={() => void retire()} disabled={busy || !retireReason.trim()} className="rounded-sm border border-cmd-red/50 px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-red hover:bg-cmd-red/10 disabled:opacity-40">
                Confirm Retire
              </button>
              <button type="button" onClick={() => setShowRetireForm(false)} className="rounded-sm border border-cmd-border px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-textDim hover:text-cmd-text">
                Cancel
              </button>
            </div>
          )}
          {error && <div className="mt-2 text-[9px] text-cmd-red">{error}</div>}
        </Glass>
      )}
    </div>
  );
}
