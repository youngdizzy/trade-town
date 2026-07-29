import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { NexusManager } from "@/game/systems/NexusManager";
import { api } from "@/net/api";
import type { StrategyStage, StrategyVerdict, TestScenario } from "@/types";
import { computeStrategyConsistency } from "../lib/derive";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

const STAGE_ORDER: StrategyStage[] = ["idea", "research", "historical_backtest", "market_simulation", "paper_trading", "limited_live_capital", "company_review", "approved"];

const STAGE_LABELS: Record<StrategyStage, string> = {
  idea: "Idea",
  research: "Research",
  historical_backtest: "Historical Backtest",
  market_simulation: "Market Simulation",
  paper_trading: "Paper Trading",
  limited_live_capital: "Limited Live Capital",
  company_review: "Company Review",
  approved: "Approved",
};

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

/**
 * v0.7 Feature 45 — the Research Sandbox. See backend/app/sandbox.py's
 * module docstring for the full scope: strategies cannot skip pipeline
 * stages, every stage transition traces to a real signal, and the last
 * three stages (Paper Trading/Limited Live Capital/Company Review) are
 * real CEO-authorized trust checkpoints rather than fabricated live P&L
 * attribution — this codebase's live trading loop has no mechanism to
 * attribute an executed trade back to a specific Strategy object.
 */
export function SandboxPanel() {
  const { strategies, backtestSessions, simulationResults, strategyReports, strategyReviews, watchlist } = useGameStore();
  const [selectedId, setSelectedId] = useState<string | null>(strategies[0]?.id ?? null);
  const [scenario, setScenario] = useState<TestScenario>("historical");
  const [customBias, setCustomBias] = useState(0);
  const [customVol, setCustomVol] = useState(1);
  const [liveAmount, setLiveAmount] = useState(500);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = strategies.find((s) => s.id === selectedId) ?? null;
  const ownResults = useMemo(() => (selected ? simulationResults.filter((r) => r.strategyId === selected.id) : []), [selected, simulationResults]);
  const ownReports = useMemo(() => (selected ? strategyReports.filter((r) => r.strategyId === selected.id) : []), [selected, strategyReports]);
  const ownReviews = useMemo(() => (selected ? strategyReviews.filter((r) => r.strategyId === selected.id) : []), [selected, strategyReviews]);
  const pendingReview = ownReviews.find((r) => r.ceoDecision === "pending");
  const activeSessions = useMemo(() => (selected ? backtestSessions.filter((s) => s.strategyId === selected.id && s.status !== "completed") : []), [selected, backtestSessions]);
  const consistency = selected ? computeStrategyConsistency(selected.id, simulationResults) : null;

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
      if (!selected) return;
      const res = await api.queueSandboxBacktest(selected.id, scenario, customBias, customVol);
      NexusManager.setBacktestSessions(res.backtestSessions);
    });

  const beginPaperTrial = () =>
    runAction(async () => {
      if (!selected) return;
      const res = await api.beginSandboxPaperTrial(selected.id);
      NexusManager.setSandboxState(res.strategies, res.strategyReviews);
    });

  const beginLimitedLive = () =>
    runAction(async () => {
      if (!selected) return;
      const res = await api.beginSandboxLimitedLive(selected.id, liveAmount);
      NexusManager.setSandboxState(res.strategies, res.strategyReviews);
    });

  const requestReview = () =>
    runAction(async () => {
      if (!selected) return;
      const res = await api.requestSandboxCompanyReview(selected.id);
      NexusManager.setSandboxState(res.strategies, res.strategyReviews);
    });

  const decide = (approve: boolean) =>
    runAction(async () => {
      if (!pendingReview) return;
      const res = await api.decideSandboxReview(pendingReview.id, approve);
      NexusManager.setSandboxState(res.strategies, res.strategyReviews);
    });

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <Glass className="p-3 lg:col-span-1">
        <TerminalLabel>Strategies — no strategy skips a stage</TerminalLabel>
        <p className="mb-2 text-[9px] text-cmd-textDim">
          Idea → Research → Historical Backtest → Market Simulation → Paper Trading → Limited Live Capital → Company Review → Approved. Each arrow only fires on a real signal — see
          the pipeline below.
        </p>
        <div className="space-y-1.5">
          {strategies.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setSelectedId(s.id)}
              className={`w-full rounded-sm border p-2 text-left text-[9px] ${selectedId === s.id ? "border-cmd-cyan/60 bg-cmd-cyan/10" : "border-cmd-border/60 bg-cmd-bg/40 hover:border-cmd-border"}`}
            >
              <div className="flex items-center justify-between">
                <span className="text-cmd-cyan">{s.name}</span>
                <StatusPill tone={s.stage === "approved" ? "green" : "cyan"}>{STAGE_LABELS[s.stage]}</StatusPill>
              </div>
              <div className="mt-0.5 text-cmd-textDim">{s.focusCategory} — {AGENT_PROFILES[s.createdBy].name}</div>
            </button>
          ))}
        </div>
      </Glass>

      {!selected ? (
        <Glass className="p-3 lg:col-span-2">
          <EmptyState>Select a strategy to open its Research Sandbox.</EmptyState>
        </Glass>
      ) : (
        <div className="space-y-3 lg:col-span-2">
          <Glass className="p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>{selected.name} — Pipeline</TerminalLabel>
              <StatusPill tone={selected.stage === "approved" ? "green" : "cyan"}>{STAGE_LABELS[selected.stage]}</StatusPill>
            </div>
            <div className="mb-2 flex flex-wrap gap-1">
              {STAGE_ORDER.map((stage, i) => {
                const reached = STAGE_ORDER.indexOf(selected.stage) >= i;
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
                      <span className="text-cmd-text">{SCENARIO_LABELS[s.scenario]} on {s.symbol}</span>
                      <span className="text-cmd-textDim">{s.status}</span>
                    </div>
                    <Meter value={s.progress} tone="cyan" />
                  </div>
                ))}
              </div>
            )}
            {error && <div className="mt-2 text-[9px] text-cmd-red">{error}</div>}
          </Glass>

          <Glass className="p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>Performance Metrics — real per-run history</TerminalLabel>
              {consistency && consistency.sampleSize > 0 && (
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
                        <td className={`px-1 py-1 tabular-nums ${r.totalReturnPct >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{r.totalReturnPct >= 0 ? "+" : ""}{r.totalReturnPct.toFixed(1)}%</td>
                        <td className="px-1 py-1 tabular-nums text-cmd-text">{r.winRate.toFixed(0)}%</td>
                        <td className="px-1 py-1 tabular-nums text-cmd-text">{r.expectedValuePct >= 0 ? "+" : ""}{r.expectedValuePct.toFixed(2)}%</td>
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
                    {report.strengths.length > 0 && (
                      <div className="text-cmd-green">
                        Strengths: {report.strengths.join(" ")}
                      </div>
                    )}
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
                      <span className="text-cmd-textDim">
                        {review.ceoDecision === "pending" ? "Awaiting CEO decision" : `${review.ceoDecision} (${review.resolvedBy})`}
                      </span>
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
        </div>
      )}
    </div>
  );
}
