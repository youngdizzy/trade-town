import { useGameStore } from "@/ui/hooks/useGameStore";
import type { PeriodFinancials } from "./financials";
import { computePeriodFinancials } from "./financials";
import type { AiStatus, MarketRegime, NoTradeStats, RiskLevel } from "./derive";
import { aiStatus, computeNoTradeStats, latestDecision, marketRegimeHeuristic, riskLevel, topOpportunity } from "./derive";
import type { ResearchItem, TradeDecision } from "@/types";

export interface DashboardData {
  equity: number;
  openUnrealized: number;
  month: PeriodFinancials;
  level: RiskLevel;
  status: AiStatus;
  regime: MarketRegime;
  opportunity: ResearchItem | null;
  latest: TradeDecision | null;
  noTrade: NoTradeStats;
  recentDecisions: TradeDecision[];
  workingCount: number;
}

/**
 * Design Bible Chapter 67 (TTOS) Part 3 — Executive Dashboard
 * consolidation. `QuickView.tsx` (the collapsed glance view) and
 * `OverviewPanel.tsx` (the OVERVIEW tab in the expanded Command Center)
 * independently recomputed `riskLevel()`, `latestDecision()`, and
 * `computeNoTradeStats()` from the same gameStore fields — real,
 * non-cosmetic duplication, not merely two components that happened to
 * look similar. This hook is the one canonical place those shared
 * derivations run; both components consume it instead of repeating the
 * calls. It does not merge the two components' actual layouts — a
 * compact always-visible glance and a full landing tab serve genuinely
 * different real contexts, the same "reuse the data, don't force-merge
 * different UI contexts" call this chapter's own Quick Action Dock
 * slice already made for Pause/Resume/Emergency Stop — so every real
 * data point either currently shows (Account Value/Month P&L/Top
 * Opportunity from QuickView; Team Status' working-agent count from
 * OverviewPanel) is included here rather than dropped.
 */
export function useDashboardData(): DashboardData {
  const { paperPortfolio, riskWarnings, watchlist, research, agents, decisions, time } = useGameStore();

  const equity = paperPortfolio.cashBalance + paperPortfolio.positions.reduce((s, p) => s + p.quantity * p.currentPrice, 0);
  const openUnrealized = paperPortfolio.positions.reduce((s, p) => s + p.unrealizedPnl, 0);
  // Monthly, not live/raw cumulative — a large single trade's notional
  // value shouldn't make the company dashboard read as an instant
  // windfall; see PerformancePanel's own docstring and CHANGELOG.md.
  const month = computePeriodFinancials("month", paperPortfolio.tradeHistory, paperPortfolio.startingBalance, time, openUnrealized);

  const level = riskLevel(riskWarnings);
  const status = aiStatus(riskWarnings, research, agents);
  const regime = marketRegimeHeuristic(watchlist);
  const opportunity = topOpportunity(research);
  const latest = latestDecision(decisions);
  const noTrade = computeNoTradeStats(decisions);
  const recentDecisions = [...decisions].slice(-5).reverse();

  const workingCount = agents ? Object.values(agents).filter((a) => !["lobby", "break-room"].includes(a.location)).length : 0;

  return { equity, openUnrealized, month, level, status, regime, opportunity, latest, noTrade, recentDecisions, workingCount };
}
