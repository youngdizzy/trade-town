import { useEffect, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { api } from "@/net/api";
import { EventBus } from "@/game/systems/EventBus";
import type {
  RegimePerformanceRead,
  RegimePerformanceSummary,
  SessionPerformanceRead,
  SessionPerformanceSummary,
  Strategy,
  StrategyCapitalAllocationRead,
  StrategyCapitalAllocationSummary,
  StrategyPerformanceRead,
  StrategyPerformanceSummary,
  StrategySessionPerformanceSummary,
  SymbolPerformanceRead,
  SymbolPerformanceSummary,
  TradeAttributionRecord,
  TradeAttributionSummary,
} from "@/types";
import type { FinancialPeriod } from "../lib/financials";
import { computePeriodFinancials, simMonthNumber } from "../lib/financials";
import { computeTradeStats, formatMoney, formatPct } from "../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

const PERIODS: FinancialPeriod[] = ["today", "week", "month", "prevMonth", "allTime"];

/**
 * Company financial reporting — monthly P&L is the primary view (per the
 * brief), not raw real-time trading fluctuation. See lib/financials.ts
 * for why periods are computed against TradeTown's simulated clock
 * (PaperTrade.closedSimMinutes) rather than real wall-clock time, and why
 * months are labeled "Simulated Month N" rather than a real calendar
 * month — there is no real-world date anywhere in this game's state.
 */
export function PerformancePanel() {
  const { paperPortfolio, time, strategies } = useGameStore();
  const [period, setPeriod] = useState<FinancialPeriod>("month");

  const openUnrealized = paperPortfolio.positions.reduce((s, p) => s + p.unrealizedPnl, 0);
  const financials = computePeriodFinancials(period, paperPortfolio.tradeHistory, paperPortfolio.startingBalance, time, openUnrealized);
  const prevMonth = computePeriodFinancials("prevMonth", paperPortfolio.tradeHistory, paperPortfolio.startingBalance, time, openUnrealized);
  const allTimeStats = computeTradeStats(paperPortfolio.tradeHistory);

  // CEO directive "Next Professional Trading Firm Phase," Priority 2 —
  // real, on-demand symbol-level P&L attribution
  // (backend/app/performance_attribution.py), no WS-broadcast field
  // backs it, the same on-demand pattern this Command Center already
  // uses for Exit Efficiency in the Discipline panel.
  const [symbolPerformance, setSymbolPerformance] = useState<SymbolPerformanceSummary | null>(null);
  useEffect(() => {
    api.getPerformanceBySymbol().then(setSymbolPerformance).catch(() => undefined);
  }, []);

  // CEO directive "Next Phase: Professional Trading Firm Intelligence,"
  // Phase 1 — real per-trade agent-contribution evidence
  // (backend/app/trade_attribution.py), same on-demand pattern.
  const [tradeAttribution, setTradeAttribution] = useState<TradeAttributionSummary | null>(null);
  useEffect(() => {
    api.getTradeAttribution().then(setTradeAttribution).catch(() => undefined);
  }, []);

  // CEO directive "Next Phase: Professional Trading Firm Intelligence,"
  // Phase 3 — real session/regime P&L via the real Decision Vault join.
  const [sessionPerformance, setSessionPerformance] = useState<SessionPerformanceSummary | null>(null);
  useEffect(() => {
    api.getPerformanceBySession().then(setSessionPerformance).catch(() => undefined);
  }, []);
  const [regimePerformance, setRegimePerformance] = useState<RegimePerformanceSummary | null>(null);
  useEffect(() => {
    api.getPerformanceByRegime().then(setRegimePerformance).catch(() => undefined);
  }, []);

  // CEO directive "Live Trade → Strategy Provenance," Phase 4 — real
  // strategy-grouped P&L, same real Decision Vault join, only ever
  // grouping trades where the CEO explicitly selected a strategy.
  const [strategyPerformance, setStrategyPerformance] = useState<StrategyPerformanceSummary | null>(null);
  useEffect(() => {
    api.getPerformanceByStrategy().then(setStrategyPerformance).catch(() => undefined);
  }, []);

  // CEO directive "Live Trade → Strategy Provenance," Phase 6 — the
  // real strategy×session axis, same real Decision Vault join.
  const [strategySessionPerformance, setStrategySessionPerformance] = useState<StrategySessionPerformanceSummary | null>(null);
  useEffect(() => {
    api.getPerformanceByStrategySession().then(setStrategySessionPerformance).catch(() => undefined);
  }, []);

  // CEO directive "Portfolio Construction, Capital Allocation & Execution
  // Realism," Phase 5 — an informational evidence roster for the CEO's
  // own manual allocatedCapital decision, never a system-generated
  // ranking or auto-allocation.
  const [capitalAllocation, setCapitalAllocation] = useState<StrategyCapitalAllocationSummary | null>(null);
  useEffect(() => {
    api.getStrategyCapitalAllocation().then(setCapitalAllocation).catch(() => undefined);
  }, []);

  const netPositive = financials.netPnl >= 0;
  const monthLabel =
    period === "month"
      ? `Simulated Month ${simMonthNumber(financials.dayRange[0])}`
      : period === "prevMonth"
        ? `Simulated Month ${simMonthNumber(financials.dayRange[0])}`
        : financials.label;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5">
        {PERIODS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setPeriod(p)}
            className={`rounded-sm border px-3 py-1.5 uppercase tracking-wide transition-colors ${
              period === p ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan shadow-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
            }`}
          >
            {p === "prevMonth" ? "Previous Month" : p === "allTime" ? "All Time" : p === "today" ? "Today" : p === "week" ? "This Week" : "This Month"}
          </button>
        ))}
      </div>

      <Glass className={`border p-4 ${netPositive ? "border-cmd-green/40" : "border-cmd-red/40"}`}>
        <div className="flex items-center justify-between">
          <TerminalLabel>{monthLabel}</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">
            Sim Day {financials.dayRange[0]}
            {financials.dayRange[1] !== financials.dayRange[0] ? `–${financials.dayRange[1]}` : ""}
          </span>
        </div>
        <div className="mb-1 text-[9px] uppercase tracking-widest text-cmd-textDim">Net P&amp;L</div>
        <div className={`font-cmdmono text-4xl ${netPositive ? "text-cmd-green" : "text-cmd-red"}`}>{formatMoney(financials.netPnl)}</div>
        <div className={`text-[11px] ${netPositive ? "text-cmd-green" : "text-cmd-red"}`}>{formatPct(financials.returnPct)} of starting balance</div>
      </Glass>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Glass className="p-3">
          <TerminalLabel>Realized P&amp;L</TerminalLabel>
          <div className={`font-cmdmono ${financials.realizedPnl >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{formatMoney(financials.realizedPnl)}</div>
          <div className="mt-0.5 text-[9px] text-cmd-textDim">From closed trades</div>
        </Glass>
        <Glass className="p-3">
          <TerminalLabel>Unrealized P&amp;L</TerminalLabel>
          <div className={`font-cmdmono ${financials.unrealizedPnl >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{formatMoney(financials.unrealizedPnl)}</div>
          <div className="mt-0.5 text-[9px] text-cmd-textDim">Open positions, right now</div>
        </Glass>
        <Glass className="p-3">
          <TerminalLabel>Max Drawdown</TerminalLabel>
          <div className="font-cmdmono text-cmd-amber">{financials.maxDrawdownPct.toFixed(1)}%</div>
          <div className="mt-0.5 text-[9px] text-cmd-textDim">Worst single trade this period</div>
        </Glass>
        <Glass className="p-3">
          <TerminalLabel>Win Rate</TerminalLabel>
          <div className="font-cmdmono text-cmd-text">{financials.tradeCount ? `${Math.round(financials.winRate)}%` : "N/A"}</div>
          <div className="mt-0.5 text-[9px] text-cmd-textDim">
            {financials.winCount}W / {financials.lossCount}L of {financials.tradeCount}
          </div>
        </Glass>
        <Glass className="p-3">
          <TerminalLabel>Profit Factor</TerminalLabel>
          <div className="font-cmdmono text-cmd-text">{financials.profitFactor === null ? "N/A" : financials.profitFactor.toFixed(2)}</div>
          <div className="mt-0.5 text-[9px] text-cmd-textDim">Gross win ÷ gross loss</div>
        </Glass>
        <Glass className="p-3">
          <TerminalLabel>Starting → Ending</TerminalLabel>
          <div className="font-cmdmono text-cmd-text">
            {formatMoney(financials.startingBalance)} → {formatMoney(financials.endingBalance)}
          </div>
        </Glass>
      </div>

      {financials.weeklyBreakdown !== null && (
        <Glass className="p-3">
          <TerminalLabel>Weekly Breakdown</TerminalLabel>
          <div className="grid grid-cols-4 gap-2">
            {financials.weeklyBreakdown.map((w) => (
              <div key={w.week} className="rounded-sm border border-cmd-border p-2 text-center">
                <div className="text-[9px] uppercase text-cmd-textDim">Week {w.week}</div>
                <div className={`font-cmdmono ${w.pnl >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{formatMoney(w.pnl)}</div>
              </div>
            ))}
          </div>
        </Glass>
      )}

      {period === "month" && (
        <Glass className="p-3">
          <TerminalLabel>Previous Month Comparison</TerminalLabel>
          <DataRow label={`Simulated Month ${simMonthNumber(prevMonth.dayRange[0])} — Net P&L`} value={formatMoney(prevMonth.netPnl)} valueClassName={prevMonth.netPnl >= 0 ? "text-cmd-green" : "text-cmd-red"} />
          <DataRow label="Change vs. previous month" value={formatMoney(financials.netPnl - prevMonth.netPnl)} valueClassName={financials.netPnl - prevMonth.netPnl >= 0 ? "text-cmd-green" : "text-cmd-red"} />
        </Glass>
      )}

      <Glass className="p-3">
        <TerminalLabel>All-Time Trade Journal</TerminalLabel>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-4">
          <DataRow label="Trades" value={allTimeStats.count} />
          <DataRow label="Win rate" value={`${Math.round(allTimeStats.winRate)}%`} />
          <DataRow label="Avg win" value={formatMoney(allTimeStats.avgWin)} valueClassName="text-cmd-green" />
          <DataRow label="Avg loss" value={formatMoney(-allTimeStats.avgLoss)} valueClassName="text-cmd-red" />
        </div>
        <div className="mt-2 text-[9px] text-cmd-textDim">
          A numeric performance-by-agent P&amp;L split isn&apos;t built — a trade&apos;s multiple supporting/opposing
          agents have no CEO-authorized credit-split rule (see Trade Attribution below for the real evidence
          instead). See CHANGELOG.md.
        </div>
      </Glass>

      <SymbolPerformanceSection summary={symbolPerformance} />

      <SessionRegimePerformanceSection sessionSummary={sessionPerformance} regimeSummary={regimePerformance} />

      <StrategyPerformanceSection summary={strategyPerformance} strategies={strategies} />

      <StrategySessionPerformanceSection summary={strategySessionPerformance} strategies={strategies} />

      <StrategyCapitalAllocationSection summary={capitalAllocation} />

      <TradeAttributionSection summary={tradeAttribution} />

      <Glass className="p-3">
        <TerminalLabel>Recent Trades — Post-Trade Learning</TerminalLabel>
        {paperPortfolio.tradeHistory.length === 0 ? (
          <EmptyState>No trades closed yet.</EmptyState>
        ) : (
          <div className="space-y-2">
            {[...paperPortfolio.tradeHistory].reverse().slice(0, 8).map((t) => (
              <div key={t.id} className="border-b border-cmd-border/60 pb-2 last:border-0">
                <div className="flex items-center justify-between">
                  <span className="font-cmdmono text-cmd-cyan">{t.symbol}</span>
                  <span className={t.pnl >= 0 ? "text-cmd-green" : "text-cmd-red"}>
                    {formatMoney(t.pnl)} ({formatPct(t.pnlPct)})
                  </span>
                </div>
                {t.transactionCostUsd > 0 && (
                  <div className="mt-0.5 text-[9px] text-cmd-textDim">Transaction cost: {formatMoney(t.transactionCostUsd)} (real, already netted above)</div>
                )}
                {(t.entrySlippageBps > 0 || t.exitSlippageBps > 0) && (
                  <div className="mt-0.5 text-[9px] text-cmd-textDim">
                    Slippage: {t.entrySlippageBps.toFixed(1)}bps in / {t.exitSlippageBps.toFixed(1)}bps out (real, already reflected in entry/exit price)
                  </div>
                )}
                {t.distanceToDrawdownCeilingBeforePct !== null && t.distanceToDrawdownCeilingAfterPct !== null && (
                  <div className="mt-0.5 text-[9px] text-cmd-textDim">
                    Distance to drawdown ceiling: {t.distanceToDrawdownCeilingBeforePct.toFixed(1)}% → {t.distanceToDrawdownCeilingAfterPct.toFixed(1)}%
                  </div>
                )}
                {(t.maePct !== 0 || t.mfePct !== 0) && (
                  <div className="mt-0.5 text-[9px] text-cmd-textDim">
                    MAE: <span className="text-cmd-red">{formatPct(t.maePct)}</span> · MFE: <span className="text-cmd-green">{formatPct(t.mfePct)}</span>
                  </div>
                )}
                {(t.lessonsLearned ?? t.coachReview) && <div className="mt-0.5 text-[9px] text-cmd-textDim">{t.lessonsLearned ?? t.coachReview}</div>}
              </div>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}

/** CEO directive "Next Professional Trading Firm Phase," Priority 2 —
 * "What is making money? Where is the edge strongest?" answered with
 * real, computed-fresh symbol-level attribution. */
function SymbolPerformanceSection({ summary }: { summary: SymbolPerformanceSummary | null }) {
  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Performance by Symbol</TerminalLabel>
        <span className="text-[9px] text-cmd-textDim">Most profitable symbol first — real, computed fresh from closed trades</span>
      </div>
      {summary === null ? (
        <EmptyState>Loading…</EmptyState>
      ) : summary.reads.length === 0 ? (
        <EmptyState>No trade has closed yet.</EmptyState>
      ) : (
        <div className="space-y-1">
          {summary.reads.map((r) => (
            <SymbolPerformanceRow key={r.symbol} read={r} />
          ))}
        </div>
      )}
    </Glass>
  );
}

function SymbolPerformanceRow({ read }: { read: SymbolPerformanceRead }) {
  return (
    <div className="rounded-sm border border-cmd-border/40 bg-cmd-bg/30 px-2 py-1.5 text-[9px]">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-cmdmono text-cmd-cyan">{read.symbol}</span>
        <span className={read.totalPnl >= 0 ? "text-cmd-green" : "text-cmd-red"}>{formatMoney(read.totalPnl)}</span>
        <span className="text-cmd-textDim">
          {read.tradeCount} trade{read.tradeCount === 1 ? "" : "s"} · {read.winRatePct.toFixed(0)}% win rate
        </span>
        {read.evidenceState === "not_enough_data" ? (
          <StatusPill tone="amber">NOT ENOUGH DATA</StatusPill>
        ) : (
          <>
            <span className="text-cmd-textDim">
              Expectancy: <span className={read.expectancyPct !== null && read.expectancyPct >= 0 ? "text-cmd-green" : "text-cmd-red"}>{formatPct(read.expectancyPct ?? 0)}</span>
            </span>
            <span className="text-cmd-textDim">Profit factor: {read.profitFactor === null ? "N/A (no losses yet)" : read.profitFactor.toFixed(2)}</span>
          </>
        )}
      </div>
      <div className="mt-0.5 text-cmd-textDim">
        Avg winner: <span className="text-cmd-green">{read.avgWinnerPct === null ? "—" : formatPct(read.avgWinnerPct)}</span> · Avg loser:{" "}
        <span className="text-cmd-red">{read.avgLoserPct === null ? "—" : formatPct(read.avgLoserPct)}</span> · Best: {formatPct(read.bestTradePnlPct)} · Worst:{" "}
        {formatPct(read.worstTradePnlPct)}
      </div>
    </div>
  );
}

/** CEO directive "Next Phase: Professional Trading Firm Intelligence,"
 * Phase 3 — real session/regime P&L via the real Decision Vault join.
 * "Which strategies/agents work during London?" isn't answerable yet
 * (strategy id and agent credit-split are both real, disclosed gaps —
 * see Trade Attribution below and CHANGELOG.md), but "which sessions/
 * regimes produce the highest expectancy?" now is. */
function SessionRegimePerformanceSection({ sessionSummary, regimeSummary }: { sessionSummary: SessionPerformanceSummary | null; regimeSummary: RegimePerformanceSummary | null }) {
  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Performance by Session &amp; Market Regime</TerminalLabel>
        <span className="text-[9px] text-cmd-textDim">Real Decision Vault join — most profitable first</span>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Session</div>
          {sessionSummary === null ? (
            <EmptyState>Loading…</EmptyState>
          ) : sessionSummary.reads.length === 0 ? (
            <EmptyState>No trade has closed with a real vault entry yet.</EmptyState>
          ) : (
            <div className="space-y-1">
              {sessionSummary.reads.map((r) => (
                <GroupPerformanceRow key={r.session} label={r.session.replace(/_/g, " ")} read={r} />
              ))}
              {sessionSummary.tradesExcludedNoVaultEntry > 0 && (
                <div className="text-[9px] text-cmd-textDim">
                  {sessionSummary.tradesExcludedNoVaultEntry} closed trade{sessionSummary.tradesExcludedNoVaultEntry === 1 ? "" : "s"} excluded — no matching Decision Vault entry.
                </div>
              )}
            </div>
          )}
        </div>
        <div>
          <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Market Regime</div>
          {regimeSummary === null ? (
            <EmptyState>Loading…</EmptyState>
          ) : regimeSummary.reads.length === 0 ? (
            <EmptyState>No trade has closed with a real vault entry yet.</EmptyState>
          ) : (
            <div className="space-y-1">
              {regimeSummary.reads.map((r) => (
                <GroupPerformanceRow key={r.regime} label={r.regime.replace(/_/g, " ")} read={r} />
              ))}
              {regimeSummary.tradesExcludedNoVaultEntry > 0 && (
                <div className="text-[9px] text-cmd-textDim">
                  {regimeSummary.tradesExcludedNoVaultEntry} closed trade{regimeSummary.tradesExcludedNoVaultEntry === 1 ? "" : "s"} excluded — no matching Decision Vault entry.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </Glass>
  );
}

function GroupPerformanceRow({ label, read }: { label: string; read: SessionPerformanceRead | RegimePerformanceRead }) {
  return (
    <div className="rounded-sm border border-cmd-border/40 bg-cmd-bg/30 px-2 py-1 text-[9px]">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-cmdmono text-cmd-cyan">{label}</span>
        <span className={read.totalPnl >= 0 ? "text-cmd-green" : "text-cmd-red"}>{formatMoney(read.totalPnl)}</span>
        <span className="text-cmd-textDim">
          {read.tradeCount} · {read.winRatePct.toFixed(0)}% win
        </span>
        {read.evidenceState === "not_enough_data" ? (
          <StatusPill tone="amber">THIN</StatusPill>
        ) : (
          <span className="text-cmd-textDim">Exp: {formatPct(read.expectancyPct ?? 0)}</span>
        )}
      </div>
    </div>
  );
}

/** CEO directive "Live Trade → Strategy Provenance," Phase 4 — the
 * Strategy Exposure view. Only ever groups trades where the CEO
 * explicitly selected a real strategy at decision time
 * (strategyProvenanceState === "known"); the two exclusion counts below
 * are the honest majority on almost every save today, since the
 * strategy selector only just shipped (see ExecutiveVoting.tsx). */
function StrategyPerformanceSection({ summary, strategies }: { summary: StrategyPerformanceSummary | null; strategies: Strategy[] }) {
  const nameFor = (strategyId: string) => strategies.find((s) => s.id === strategyId)?.name ?? strategyId;
  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Performance by Strategy</TerminalLabel>
        <button
          type="button"
          onClick={() => EventBus.emit("ui:commandCenterJump", { tab: "SANDBOX" })}
          className="text-[9px] text-cmd-cyan underline decoration-dotted hover:text-cmd-text"
        >
          → Strategy Library (backtest evidence, certification, health)
        </button>
      </div>
      <div className="mb-1.5 text-[9px] text-cmd-textDim">Only trades with a CEO-selected strategy — real Decision Vault join</div>
      {summary === null ? (
        <EmptyState>Loading…</EmptyState>
      ) : summary.reads.length === 0 ? (
        <EmptyState>No closed trade has a CEO-selected strategy yet.</EmptyState>
      ) : (
        <div className="space-y-1">
          {summary.reads.map((r) => (
            <StrategyPerformanceRow key={r.strategyId} read={r} label={nameFor(r.strategyId)} />
          ))}
        </div>
      )}
      {summary !== null && (summary.tradesExcludedNoStrategySelected > 0 || summary.tradesExcludedNoVaultEntry > 0) && (
        <div className="mt-1 space-y-0.5 text-[9px] text-cmd-textDim">
          {summary.tradesExcludedNoStrategySelected > 0 && (
            <div>
              {summary.tradesExcludedNoStrategySelected} closed trade{summary.tradesExcludedNoStrategySelected === 1 ? "" : "s"} excluded — CEO didn&apos;t select a
              strategy at decision time.
            </div>
          )}
          {summary.tradesExcludedNoVaultEntry > 0 && (
            <div>
              {summary.tradesExcludedNoVaultEntry} closed trade{summary.tradesExcludedNoVaultEntry === 1 ? "" : "s"} excluded — no matching Decision Vault entry.
            </div>
          )}
        </div>
      )}
    </Glass>
  );
}

function StrategyPerformanceRow({ read, label }: { read: StrategyPerformanceRead; label: string }) {
  return (
    <div className="rounded-sm border border-cmd-border/40 bg-cmd-bg/30 px-2 py-1.5 text-[9px]">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-cmdmono text-cmd-cyan">{label}</span>
        <span className={read.totalPnl >= 0 ? "text-cmd-green" : "text-cmd-red"}>{formatMoney(read.totalPnl)}</span>
        <span className="text-cmd-textDim">
          {read.tradeCount} trade{read.tradeCount === 1 ? "" : "s"} · {read.winRatePct.toFixed(0)}% win rate
        </span>
        {read.evidenceState === "not_enough_data" ? (
          <StatusPill tone="amber">NOT ENOUGH DATA</StatusPill>
        ) : (
          <>
            <span className="text-cmd-textDim">
              Expectancy: <span className={read.expectancyPct !== null && read.expectancyPct >= 0 ? "text-cmd-green" : "text-cmd-red"}>{formatPct(read.expectancyPct ?? 0)}</span>
            </span>
            <span className="text-cmd-textDim">Profit factor: {read.profitFactor === null ? "N/A (no losses yet)" : read.profitFactor.toFixed(2)}</span>
          </>
        )}
      </div>
    </div>
  );
}

/** CEO directive "Live Trade → Strategy Provenance," Phase 6 — the real
 * strategy×session axis. Compact by design: only strategy/session pairs
 * that actually have a real closed trade appear at all — no cross-
 * product of every strategy against every session. */
function StrategySessionPerformanceSection({ summary, strategies }: { summary: StrategySessionPerformanceSummary | null; strategies: Strategy[] }) {
  const nameFor = (strategyId: string) => strategies.find((s) => s.id === strategyId)?.name ?? strategyId;
  if (summary === null || summary.reads.length === 0) return null;
  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Strategy Performance by Session</TerminalLabel>
        <span className="text-[9px] text-cmd-textDim">Real Decision Vault join, cross-cut by session</span>
      </div>
      <div className="space-y-1">
        {summary.reads.map((r) => (
          <div key={`${r.strategyId}-${r.session}`} className="rounded-sm border border-cmd-border/40 bg-cmd-bg/30 px-2 py-1 text-[9px]">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-cmdmono text-cmd-cyan">{nameFor(r.strategyId)}</span>
              <span className="text-cmd-purple">{r.session.replace(/_/g, " ")}</span>
              <span className={r.totalPnl >= 0 ? "text-cmd-green" : "text-cmd-red"}>{formatMoney(r.totalPnl)}</span>
              <span className="text-cmd-textDim">
                {r.tradeCount} · {r.winRatePct.toFixed(0)}% win
              </span>
            </div>
          </div>
        ))}
      </div>
    </Glass>
  );
}

/** CEO directive "Portfolio Construction, Capital Allocation & Execution
 * Realism," Phase 5 — an informational evidence roster for the CEO's
 * own manual allocatedCapital decision. Rows are sorted by allocated
 * capital (the CEO's own existing real commitment), never re-sorted
 * here by any performance metric — that would silently turn a neutral
 * evidence view into an implied ranking. */
function StrategyCapitalAllocationSection({ summary }: { summary: StrategyCapitalAllocationSummary | null }) {
  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Strategy Capital Allocation — Evidence, Not a Ranking</TerminalLabel>
        <span className="text-[9px] text-cmd-textDim">Sorted by allocated capital — never by performance</span>
      </div>
      <div className="mb-1.5 text-[9px] text-cmd-textDim">
        Informational only. Real, evidence-gated reads for the CEO&apos;s own manual allocation decisions — never a system ranking, never auto-allocated capital.
      </div>
      {summary === null ? (
        <EmptyState>Loading…</EmptyState>
      ) : summary.reads.length === 0 ? (
        <EmptyState>No strategies on file yet.</EmptyState>
      ) : (
        <div className="space-y-1.5">
          {summary.reads.map((r) => (
            <StrategyCapitalAllocationRow key={r.strategyId} read={r} />
          ))}
        </div>
      )}
    </Glass>
  );
}

function StrategyCapitalAllocationRow({ read }: { read: StrategyCapitalAllocationRead }) {
  return (
    <div className="rounded-sm border border-cmd-border/40 bg-cmd-bg/30 px-2 py-1.5 text-[9px]">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-cmdmono text-cmd-cyan">{read.strategyName}</span>
        <span className="text-cmd-textDim">{read.stage.replace(/_/g, " ")}</span>
        <span className="text-cmd-text">Allocated: {formatMoney(read.allocatedCapital)}</span>
        {read.evidenceState === "no_live_trades_yet" ? (
          <StatusPill tone="neutral">NO LIVE TRADES YET</StatusPill>
        ) : read.evidenceState === "not_enough_data" ? (
          <StatusPill tone="amber">NOT ENOUGH DATA ({read.tradeCount} trade{read.tradeCount === 1 ? "" : "s"})</StatusPill>
        ) : (
          <StatusPill tone="cyan">{read.tradeCount} TRADES</StatusPill>
        )}
      </div>
      {read.evidenceState === "sufficient_evidence" && (
        <div className="mt-1 flex flex-wrap items-center gap-2 text-cmd-textDim">
          <span>Win rate: <span className="text-cmd-text">{read.winRatePct?.toFixed(0)}%</span></span>
          <span>
            Expectancy: <span className={(read.expectancyPct ?? 0) >= 0 ? "text-cmd-green" : "text-cmd-red"}>{formatPct(read.expectancyPct ?? 0)}</span>
          </span>
          <span>Profit factor: {read.profitFactor === null ? "N/A (no losses yet)" : read.profitFactor.toFixed(2)}</span>
          <span>Live drawdown: {read.liveDrawdownUsd === null ? "—" : formatMoney(-read.liveDrawdownUsd)}</span>
          <span>Return volatility: {read.liveReturnVolatilityPct === null ? "—" : `${read.liveReturnVolatilityPct.toFixed(2)}%`}</span>
          <span>
            Avg slippage: {read.avgEntrySlippageBps === null ? "—" : `${read.avgEntrySlippageBps.toFixed(1)} bps in / ${read.avgExitSlippageBps?.toFixed(1)} bps out`}
          </span>
        </div>
      )}
      <div className="mt-1 text-cmd-textDim">
        Exposure: {formatMoney(read.currentExposureValue)} ({read.currentExposurePctOfEquity.toFixed(1)}% of equity)
      </div>
      <div className="mt-1 italic text-cmd-textDim/80">{read.robustnessNote}</div>
      <div className="mt-0.5 italic text-cmd-textDim/80">{read.correlationNote}</div>
    </div>
  );
}

/** CEO directive "Next Phase: Professional Trading Firm Intelligence,"
 * Phase 1 — real per-trade agent-contribution evidence. Deliberately
 * never shows a dollar/percent split per agent — see each record's own
 * creditSplitNote for why. */
function TradeAttributionSection({ summary }: { summary: TradeAttributionSummary | null }) {
  const recent = summary ? [...summary.records].reverse().slice(0, 8) : [];
  return (
    <Glass className="max-h-96 overflow-y-auto p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Trade Attribution — Who Advised What</TerminalLabel>
        <span className="text-[9px] text-cmd-textDim">Real evidence, not a P&amp;L credit split</span>
      </div>
      {summary === null ? (
        <EmptyState>Loading…</EmptyState>
      ) : summary.records.length === 0 ? (
        <EmptyState>No trade has closed yet.</EmptyState>
      ) : (
        <>
          <div className="mb-2 text-[9px] text-cmd-textDim">{recent[0]?.creditSplitNote}</div>
          <div className="space-y-1.5">
            {recent.map((r) => (
              <TradeAttributionRow key={r.tradeId} record={r} />
            ))}
          </div>
        </>
      )}
    </Glass>
  );
}

function TradeAttributionRow({ record }: { record: TradeAttributionRecord }) {
  if (record.evidenceState === "no_decision_on_record") {
    return (
      <div className="rounded-sm border border-cmd-border/40 bg-cmd-bg/30 px-2 py-1.5 text-[9px]">
        <div className="flex items-center gap-2">
          <span className="font-cmdmono text-cmd-cyan">{record.symbol}</span>
          <span className={record.pnl >= 0 ? "text-cmd-green" : "text-cmd-red"}>{formatMoney(record.pnl)}</span>
          <StatusPill tone="amber">NO DECISION ON RECORD</StatusPill>
        </div>
      </div>
    );
  }
  return (
    <div className="rounded-sm border border-cmd-border/40 bg-cmd-bg/30 px-2 py-1.5 text-[9px]">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-cmdmono text-cmd-cyan">{record.symbol}</span>
        <span className={record.pnl >= 0 ? "text-cmd-green" : "text-cmd-red"}>{formatMoney(record.pnl)}</span>
        {record.ceoOverrodeTheDesk && <StatusPill tone="purple">CEO OVERRODE THE DESK</StatusPill>}
        {record.gatekeeperApproved !== null && (
          <StatusPill tone={record.gatekeeperApproved ? "green" : "red"}>{record.gatekeeperApproved ? "GATEKEEPER APPROVED" : "GATEKEEPER REJECTED"}</StatusPill>
        )}
      </div>
      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
        {record.contributions.map((c) => (
          <span key={c.agentId} className="text-cmd-textDim">
            <span className="text-cmd-text">{c.role}</span> ({c.agentId}): {c.choice}{" "}
            <span className={c.agreedWithSideTraded ? "text-cmd-green" : "text-cmd-textDim"}>{c.agreedWithSideTraded ? "✓ agreed" : "did not agree"}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
