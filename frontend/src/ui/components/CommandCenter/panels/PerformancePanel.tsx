import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { FinancialPeriod } from "../lib/financials";
import { computePeriodFinancials, simMonthNumber } from "../lib/financials";
import { computeTradeStats, formatMoney, formatPct } from "../lib/derive";
import { DataRow, EmptyState, Glass, TerminalLabel } from "../ui";

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
          Performance-by-strategy and performance-by-market-regime breakdowns aren&apos;t tracked yet — closed trades aren&apos;t currently linked to a Strategy id. See CHANGELOG.md.
        </div>
      </Glass>

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
