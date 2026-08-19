import { useEffect, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { api } from "@/net/api";
import type { SymbolPerformanceRead, SymbolPerformanceSummary } from "@/types";
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
  const { paperPortfolio, time } = useGameStore();
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
          Performance-by-agent and performance-by-strategy breakdowns aren&apos;t built yet — a trade&apos;s
          multiple supporting/opposing agents have no CEO-authorized credit-split rule, and closed trades
          aren&apos;t currently linked to a Strategy id. See CHANGELOG.md.
        </div>
      </Glass>

      <SymbolPerformanceSection summary={symbolPerformance} />

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
