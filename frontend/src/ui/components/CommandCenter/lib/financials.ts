import type { PaperTrade, TimeState } from "@/types";

/**
 * TradeTown's company financial calendar — mirrors backend/app/analytics.py's
 * `_period_start_sim_minutes()` exactly (same day-boundary math, same
 * 30-day month convention) so the frontend's period boundaries always
 * agree with the periodic PerformanceSnapshots the backend itself
 * computes. Everything here operates on PaperTrade.closedSimMinutes
 * (added in v0.6.1 specifically so this arithmetic is possible — see that
 * field's own docstring in schemas.py) rather than the real wall-clock
 * openedAt/closedAt fields, because real time and simulated time run at
 * different rates (default ~150x) and mixing them would silently produce
 * wrong period boundaries.
 *
 * TradeTown's clock is a plain incrementing "Day N" counter with no real
 * calendar date attached (no month/year) — so periods are labeled
 * "Simulated Month N", not a real month name like "July 2026". Inventing
 * a fake real-world date here would be exactly the kind of misleading
 * display this feature exists to avoid.
 */

export const MIN_PER_DAY = 1440;
export const DAYS_PER_MONTH = 30;

export function currentSimMinutes(time: TimeState): number {
  return time.day * MIN_PER_DAY + time.hour * 60 + time.minute;
}

export function dayOfSimMinutes(simMinutes: number): number {
  return Math.floor(simMinutes / MIN_PER_DAY);
}

export function simMonthNumber(day: number): number {
  return Math.floor((day - 1) / DAYS_PER_MONTH) + 1;
}

function monthStartDay(day: number): number {
  return day - ((day - 1) % DAYS_PER_MONTH);
}

function weekStartDay(day: number): number {
  return day - ((day - 1) % 7);
}

/** Which week (1-4) of its month a day falls in — a 30-day month isn't evenly divisible by 7, so week 4 runs slightly long (days 22-30) rather than spilling into a partial week 5. */
export function weekOfMonth(day: number): number {
  const dayInMonth = ((day - 1) % DAYS_PER_MONTH) + 1;
  return Math.min(4, Math.ceil(dayInMonth / 7));
}

export type FinancialPeriod = "today" | "week" | "month" | "prevMonth" | "allTime";

export interface PeriodFinancials {
  period: FinancialPeriod;
  label: string;
  /** Inclusive [startDay, endDay] on TradeTown's Day-N calendar; endDay is "now" for the current period. */
  dayRange: [number, number];
  startingBalance: number;
  endingBalance: number;
  realizedPnl: number;
  /** Only nonzero for periods that include "now" (today/week/month) — a past period's unrealized swings aren't reconstructable without a historical price series. */
  unrealizedPnl: number;
  netPnl: number;
  returnPct: number;
  maxDrawdownPct: number;
  winRate: number;
  tradeCount: number;
  winCount: number;
  lossCount: number;
  profitFactor: number | null;
  /** Only populated for period === "month" | "prevMonth". */
  weeklyBreakdown: { week: number; pnl: number }[] | null;
}

function periodStartDay(period: FinancialPeriod, nowDay: number): number | null {
  switch (period) {
    case "today":
      return nowDay;
    case "week":
      return weekStartDay(nowDay);
    case "month":
      return monthStartDay(nowDay);
    case "prevMonth":
      return monthStartDay(nowDay) - DAYS_PER_MONTH;
    case "allTime":
      return null;
  }
}

function periodEndDay(period: FinancialPeriod, nowDay: number): number {
  if (period === "prevMonth") return monthStartDay(nowDay) - 1;
  return nowDay;
}

const PERIOD_LABEL: Record<FinancialPeriod, string> = {
  today: "Today",
  week: "This Week",
  month: "This Month",
  prevMonth: "Previous Month",
  allTime: "All Time",
};

/** Includes "now" — i.e. the period is still accumulating and should include open-position unrealized P&L. */
function isOngoingPeriod(period: FinancialPeriod): boolean {
  return period === "today" || period === "week" || period === "month" || period === "allTime";
}

export function computePeriodFinancials(
  period: FinancialPeriod,
  trades: PaperTrade[],
  startingBalanceGlobal: number,
  time: TimeState,
  openPositionsUnrealizedPnl: number,
): PeriodFinancials {
  const nowDay = time.day;
  const startDay = periodStartDay(period, nowDay);
  const endDay = periodEndDay(period, nowDay);
  const startMinutes = startDay === null ? null : startDay * MIN_PER_DAY;
  const endMinutes = period === "prevMonth" ? (endDay + 1) * MIN_PER_DAY - 1 : currentSimMinutes(time);

  const tradesBefore = startMinutes === null ? [] : trades.filter((t) => t.closedSimMinutes < startMinutes);
  const tradesInPeriod = trades.filter((t) => (startMinutes === null || t.closedSimMinutes >= startMinutes) && t.closedSimMinutes <= endMinutes);

  const startingBalance = startingBalanceGlobal + tradesBefore.reduce((s, t) => s + t.pnl, 0);
  const realizedPnl = tradesInPeriod.reduce((s, t) => s + t.pnl, 0);
  const unrealizedPnl = isOngoingPeriod(period) ? openPositionsUnrealizedPnl : 0;
  const netPnl = realizedPnl + unrealizedPnl;
  const endingBalance = startingBalance + netPnl;
  const returnPct = startingBalance ? (netPnl / startingBalance) * 100 : 0;

  const losingPcts = tradesInPeriod.filter((t) => t.pnl < 0).map((t) => t.pnlPct);
  const maxDrawdownPct = losingPcts.length ? Math.abs(Math.min(0, ...losingPcts)) : 0;

  const wins = tradesInPeriod.filter((t) => t.pnl > 0);
  const losses = tradesInPeriod.filter((t) => t.pnl < 0);
  const winRate = tradesInPeriod.length ? (wins.length / tradesInPeriod.length) * 100 : 0;
  const grossWin = wins.reduce((s, t) => s + t.pnl, 0);
  const grossLoss = Math.abs(losses.reduce((s, t) => s + t.pnl, 0));
  const profitFactor = grossLoss > 0 ? grossWin / grossLoss : null;

  const weeklyBreakdown =
    period === "month" || period === "prevMonth"
      ? [1, 2, 3, 4].map((week) => ({
          week,
          pnl: tradesInPeriod.filter((t) => weekOfMonth(dayOfSimMinutes(t.closedSimMinutes)) === week).reduce((s, t) => s + t.pnl, 0),
        }))
      : null;

  return {
    period,
    label: PERIOD_LABEL[period],
    dayRange: [startDay ?? 1, endDay],
    startingBalance,
    endingBalance,
    realizedPnl,
    unrealizedPnl,
    netPnl,
    returnPct,
    maxDrawdownPct,
    winRate,
    tradeCount: tradesInPeriod.length,
    winCount: wins.length,
    lossCount: losses.length,
    profitFactor,
    weeklyBreakdown,
  };
}
