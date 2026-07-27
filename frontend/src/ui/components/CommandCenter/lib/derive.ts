import type { AgentId, AgentState, AgentVote, PaperOrder, PaperTrade, ResearchItem, RiskWarning, TradeDecision, WatchlistEntry } from "@/types";
import { AGENT_IDS } from "@/types";

/**
 * Every number here is either a real field read straight off the wire, or
 * a standard, honestly-labeled derivation computed from real records
 * (profit factor, expectancy, a risk-severity bucket, a market-regime
 * heuristic). Nothing in this file invents data the backend doesn't have —
 * see CHANGELOG.md's v0.6.1 entry for exactly which Command Center fields
 * are direct reuse vs. derived vs. "not tracked yet" (and why).
 */

export type RiskLevel = "green" | "yellow" | "red";

/** Sentinel/Guardian only ever emit "warning"/"critical" (see risk_engine.py) — "info" exists in the type but nothing currently produces it. */
export function riskLevel(warnings: RiskWarning[]): RiskLevel {
  if (warnings.some((w) => w.severity === "critical")) return "red";
  if (warnings.some((w) => w.severity === "warning")) return "yellow";
  return "green";
}

export const RISK_LEVEL_LABEL: Record<RiskLevel, string> = {
  green: "NORMAL",
  yellow: "ELEVATED",
  red: "RESTRICTED",
};

const RISK_TEXT: Record<RiskLevel, string> = {
  green: "text-cmd-green",
  yellow: "text-cmd-amber",
  red: "text-cmd-red",
};

export function riskTextClass(level: RiskLevel): string {
  return RISK_TEXT[level];
}

export function formatPct(value: number, digits = 1): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}%`;
}

export function formatMoney(value: number): string {
  return `${value < 0 ? "-" : ""}$${Math.abs(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export type AiStatus = "RISK LOCK" | "ANALYZING" | "ACTIVE" | "WAITING";

/**
 * There is no single backend "AI status" field — this reads the same
 * underlying signals a player could otherwise only see by checking three
 * different screens (risk warnings, research queue, agent locations) and
 * folds them into one glanceable state, in priority order: a hard risk
 * veto always wins, then active research, then whether the team is
 * actually staffed anywhere but Lobby/Break Room right now.
 */
export function aiStatus(riskWarnings: RiskWarning[], research: ResearchItem[], agents: Record<AgentId, AgentState> | null): AiStatus {
  if (riskLevel(riskWarnings) === "red") return "RISK LOCK";
  if (research.some((r) => r.status === "in_progress")) return "ANALYZING";
  if (!agents) return "WAITING";
  const working = AGENT_IDS.filter((id) => !["lobby", "break-room"].includes(agents[id].location)).length;
  return working > 0 ? "ACTIVE" : "WAITING";
}

export interface MarketRegime {
  label: string;
  detail: string;
}

/**
 * TradeTown's backend keeps no rolling price history (scanner.py's own
 * docstring notes this) so there is no real regime *model* to reuse — this
 * is a transparent, clearly-labeled heuristic over the watchlist's live
 * `dailyChangePct` figures (real numbers), not a fabricated classification.
 * See CHANGELOG.md for why a proper regime model is a v0.7+ backend item.
 */
export function marketRegimeHeuristic(watchlist: WatchlistEntry[]): MarketRegime {
  if (watchlist.length === 0) {
    return { label: "UNKNOWN", detail: "No symbols on the watchlist yet." };
  }
  const changes = watchlist.map((w) => w.dailyChangePct);
  const avg = changes.reduce((s, c) => s + c, 0) / changes.length;
  const avgAbs = changes.reduce((s, c) => s + Math.abs(c), 0) / changes.length;
  const spread = Math.max(...changes) - Math.min(...changes);
  let label: string;
  if (avgAbs >= 3) label = "HIGH VOLATILITY";
  else if (Math.abs(avg) >= 1.2 && spread < avgAbs * 3 + 1) label = avg > 0 ? "TRENDING UP" : "TRENDING DOWN";
  else label = "CHOPPY";
  return {
    label,
    detail: `Heuristic over ${watchlist.length} tracked symbol${watchlist.length === 1 ? "" : "s"} — avg move ${avg >= 0 ? "+" : ""}${avg.toFixed(2)}%, avg |move| ${avgAbs.toFixed(2)}%.`,
  };
}

export type VoteDirection = "LONG" | "SHORT" | "NEUTRAL";

/** VoteChoice has no explicit "short" — "sell"/"hold"/the two hard-reject choices all read as non-bullish here, only "buy" counts as bullish. */
export function voteDirection(votes: AgentVote[]): VoteDirection {
  const buys = votes.filter((v) => v.choice === "buy").length;
  const sells = votes.filter((v) => v.choice === "sell").length;
  if (buys > sells) return "LONG";
  if (sells > buys) return "SHORT";
  return "NEUTRAL";
}

/** The votes that pushed toward taking the trade — this IS `TradeDecision.supportingAgents`' underlying vote data, just resolved to full vote objects. */
export function bullCaseVotes(decision: TradeDecision): AgentVote[] {
  return decision.votes.filter((v) => decision.supportingAgents.includes(v.agentId));
}

/** The votes that pushed back — includes both soft disagreement ("sell"/"hold") and the two hard-reject choices ("risk_too_high"/"position_too_large"). */
export function bearCaseVotes(decision: TradeDecision): AgentVote[] {
  return decision.votes.filter((v) => decision.opposingAgents.includes(v.agentId));
}

export function linkedOrderFor(decision: TradeDecision, orders: PaperOrder[]): PaperOrder | null {
  if (!decision.orderId) return null;
  return orders.find((o) => o.id === decision.orderId) ?? null;
}

/** Exit orders (stop-loss/take-profit) attached to an already-open position — see PaperOrder.linkedPositionId. TradeTown's auto-trader never places these today (see CHANGELOG), so this is almost always empty; shown when present rather than assumed absent. */
export function exitOrdersForPosition(positionId: string, orders: PaperOrder[]): PaperOrder[] {
  return orders.filter((o) => o.linkedPositionId === positionId);
}

export interface TradeStats {
  count: number;
  winCount: number;
  lossCount: number;
  winRate: number;
  avgWin: number;
  avgLoss: number;
  /** null = no losing trades yet, so the ratio is undefined rather than a real number. */
  profitFactor: number | null;
  expectancy: number;
}

/** Standard trading-journal arithmetic over real closed trades — not a backend field, but not a fabricated one either. */
export function computeTradeStats(trades: PaperTrade[]): TradeStats {
  const wins = trades.filter((t) => t.pnl > 0);
  const losses = trades.filter((t) => t.pnl < 0);
  const count = trades.length;
  const winRate = count ? (wins.length / count) * 100 : 0;
  const lossRate = count ? (losses.length / count) * 100 : 0;
  const avgWin = wins.length ? wins.reduce((s, t) => s + t.pnl, 0) / wins.length : 0;
  const avgLoss = losses.length ? Math.abs(losses.reduce((s, t) => s + t.pnl, 0) / losses.length) : 0;
  const grossWin = wins.reduce((s, t) => s + t.pnl, 0);
  const grossLoss = Math.abs(losses.reduce((s, t) => s + t.pnl, 0));
  const profitFactor = grossLoss > 0 ? grossWin / grossLoss : null;
  const expectancy = (winRate / 100) * avgWin - (lossRate / 100) * avgLoss;
  return { count, winCount: wins.length, lossCount: losses.length, winRate, avgWin, avgLoss, profitFactor, expectancy };
}

export function topOpportunity(research: ResearchItem[]): ResearchItem | null {
  const candidates = research.filter((r) => r.status !== "completed");
  if (candidates.length === 0) return null;
  return candidates.reduce((best, r) => (r.confidence > best.confidence ? r : best), candidates[0]!);
}

export function latestDecision(decisions: TradeDecision[]): TradeDecision | null {
  return decisions.length ? decisions[decisions.length - 1]! : null;
}

export interface NoTradeStats {
  total: number;
  tradedCount: number;
  noTradeCount: number;
  recentNoTrade: TradeDecision[];
}

export function computeNoTradeStats(decisions: TradeDecision[]): NoTradeStats {
  const noTrade = decisions.filter((d) => d.outcome === "no_trade");
  return {
    total: decisions.length,
    tradedCount: decisions.length - noTrade.length,
    noTradeCount: noTrade.length,
    recentNoTrade: noTrade.slice(-8).reverse(),
  };
}
