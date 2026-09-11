import { useEffect, useState } from "react";
import { api } from "@/net/api";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "@/ui/components/CommandCenter/ui";
import type { SniperStrategyPerformanceRead, SniperStrategyPerformanceSummary } from "@/types";

const POLL_MS = 5_000;

function fmtSol(v: number, digits = 4): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)} SOL`;
}

/**
 * CEO directive "TradeTown — Sniper Per-Strategy Performance
 * Observability UI 1.0." Surfaces the already-built, already-
 * authoritative `GET /api/sniper/strategy-performance` endpoint
 * (`backend/app/sniper_strategy_performance.py`) inside the existing
 * Sniper Terminal. This component is a pure renderer — it never
 * recomputes win rate, P&L, or expectancy itself, never reorders
 * `reads` (API order is preserved verbatim — this is observability,
 * never a leaderboard), and never labels a strategy "best"/"worst"/
 * "recommended". See this file's own docstrings below for the exact
 * nullable-metric handling this directive requires.
 */

/** One strategy's row. `read.closedTradeCount` is shown first and most
 * prominently — sample size must never be an afterthought (Section
 * 7/18/30 of the directive this implements). Every nullable metric
 * renders as "—", never a fabricated 0/0%/$0 — only a genuine `0.0`
 * `totalRealizedPnlSol` renders as an actual zero. */
function StrategyPerformanceRow({ read }: { read: SniperStrategyPerformanceRead }) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/30 p-2 text-[9px]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-1.5">
          <span className="truncate font-semibold text-cmd-cyan">{read.name}</span>
          <span className="truncate font-mono text-[8px] text-cmd-textDim">{read.strategyId}</span>
          {!read.isRegistered && <StatusPill tone="neutral">No longer registered</StatusPill>}
          {read.status !== null && <StatusPill tone={read.status === "enabled" ? "green" : "neutral"}>{read.status}</StatusPill>}
        </div>
        <span className="shrink-0 text-cmd-textDim">
          {read.closedTradeCount} closed trade{read.closedTradeCount === 1 ? "" : "s"}
        </span>
      </div>

      {read.closedTradeCount === 0 ? (
        <div className="mt-1 text-cmd-textDim">No closed trades yet — no historical observation exists for this strategy.</div>
      ) : (
        <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5 sm:grid-cols-4">
          <DataRow label="Win rate" value={read.winRatePct !== null ? `${read.winRatePct.toFixed(1)}%` : "—"} />
          <DataRow label="Realized P&L" value={fmtSol(read.totalRealizedPnlSol)} valueClassName={read.totalRealizedPnlSol >= 0 ? "text-cmd-green" : "text-cmd-red"} />
          <DataRow label="Avg P&L / trade" value={read.averageRealizedPnlSol !== null ? fmtSol(read.averageRealizedPnlSol) : "—"} />
          <DataRow label="Observed expectancy" value={read.observedExpectancyPerClosedTradeSol !== null ? fmtSol(read.observedExpectancyPerClosedTradeSol) : "—"} />
        </div>
      )}

      <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5 border-t border-cmd-border/40 pt-1 sm:grid-cols-4">
        <DataRow label="Wins / losses" value={`${read.winCount} / ${read.lossCount}`} />
        <DataRow label="Avg winner" value={read.averageWinningTradeSol !== null ? fmtSol(read.averageWinningTradeSol) : "—"} />
        <DataRow label="Avg loser" value={read.averageLosingTradeSol !== null ? fmtSol(read.averageLosingTradeSol) : "—"} />
        {/* Section 9/20 of the directive this implements — historical
            versions are shown exactly as the API reports them, never
            replaced with whichever version the strategy is registered
            at today. */}
        <DataRow label="Historical versions" value={read.distinctStrategyVersionsObserved.length > 0 ? read.distinctStrategyVersionsObserved.join(", ") : "—"} />
      </div>
    </div>
  );
}

/** Root panel — one flat Glass card, matching every other Sniper
 * Terminal section (no new top-level tab). Loading/error/empty are
 * three distinct, honest states: `summary === null && error === null`
 * is loading; `error !== null` is a real fetch failure (never silently
 * swapped for stale or fixture data); `summary.reads.length === 0` is
 * a real, empty backend response. */
export function SniperStrategyPerformance() {
  const [summary, setSummary] = useState<SniperStrategyPerformanceSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      api
        .getSniperStrategyPerformance()
        .then((result) => {
          if (!cancelled) {
            setSummary(result);
            setError(null);
          }
        })
        .catch((e) => {
          if (!cancelled) setError(e instanceof Error ? e.message : String(e));
        });
    };
    load();
    const interval = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <Glass className="p-3">
      <div data-testid="sniper-strategy-performance-panel">
        <TerminalLabel>Strategy performance</TerminalLabel>
        <p className="mb-2 text-[8px] leading-relaxed text-cmd-textDim">
          Historical observed performance from real closed paper trades only. Not a validation score, ranking, or trading recommendation — this list is never reordered or labeled by performance.
        </p>
        {error !== null ? (
          <div className="rounded-sm border border-cmd-red/50 bg-cmd-red/10 p-2 text-[9px] text-cmd-red">Could not load strategy performance: {error}</div>
        ) : summary === null ? (
          <EmptyState>Loading strategy performance…</EmptyState>
        ) : summary.reads.length === 0 ? (
          <EmptyState>No strategy performance observations yet.</EmptyState>
        ) : (
          <>
            <div className="space-y-1.5">
              {summary.reads.map((read) => (
                <StrategyPerformanceRow key={read.strategyId} read={read} />
              ))}
            </div>
            <p className="mt-2 text-[8px] text-cmd-textDim">
              {summary.closedTradesConsidered} simulated closed paper trade{summary.closedTradesConsidered === 1 ? "" : "s"} considered as of {new Date(summary.generatedAt).toLocaleTimeString()}.
            </p>
          </>
        )}
      </div>
    </Glass>
  );
}
