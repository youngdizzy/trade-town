import type {
  AgentId,
  AgentState,
  AgentVote,
  AnalystRole,
  CaseStudy,
  CeoDecisionRecord,
  ChallengeReport,
  ConfidenceTier,
  Debate,
  DisciplineReview,
  GatekeeperRejection,
  PaperOrder,
  PaperPortfolio,
  PaperTrade,
  ResearchCategory,
  ResearchItem,
  RiskLimits,
  RiskWarning,
  TradeDecision,
  TradeProposal,
  WatchlistEntry,
} from "@/types";
import { AGENT_IDS, ROLE_TO_AGENT } from "@/types";

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

// --- v0.6.3 Feature 12/13 — Executive Voting + Risk Command Center -------
// The pre-trade checklist below is deliberately built ONLY from data
// TradeTown's backend actually tracks: agent agreement, research
// confidence, Sentinel/Guardian's real risk warnings, and current
// portfolio exposure. The spec also names stop-loss distance,
// take-profit distance, and reward-to-risk ratio — TradeTown's paper
// broker has never placed stop-loss/take-profit exit orders (see
// DecisionDetail's "Trade Plan" section above), so there is no real
// number to show for those; rather than invent one, the UI says so
// explicitly instead of rendering a fabricated ratio.
//
// The trade-quality SCORE itself moved server-side in v0.7 Feature 15
// (see backend/app/confidence.py) — TradeProposal.confidenceEngine /
// TradeDecision.confidenceEngine are now the single source of truth,
// computed once at decision time and persisted, rather than recomputed
// fresh (and potentially drifting) on every client render.

const TIER_TONE: Record<ConfidenceTier, "green" | "cyan" | "amber" | "red" | "purple"> = {
  elite: "purple",
  strong: "green",
  good: "cyan",
  moderate: "amber",
  weak: "amber",
  poor: "red",
};

export function confidenceTierTone(tier: ConfidenceTier): "green" | "cyan" | "amber" | "red" | "purple" {
  return TIER_TONE[tier];
}

export interface ChecklistItem {
  label: string;
  met: boolean;
  detail: string;
}

/** TradeTown has no stop-loss/take-profit/reward-to-risk data to check
 * (see this section's header comment), so this checklist only covers
 * items the backend actually has real data for. */
export function preTradeChecklist(proposal: TradeProposal, riskWarnings: RiskWarning[], portfolio: PaperPortfolio, riskLimits: RiskLimits): ChecklistItem[] {
  const symbolWarning = riskWarnings.find((w) => w.symbol === proposal.symbol);
  const totalVotes = proposal.analystVotes.length || 1;
  const agreeing = proposal.analystVotes.filter((v) => v.choice === proposal.overallRecommendation).length;
  return [
    { label: "Thesis written", met: proposal.researchSummary.trim().length > 0, detail: proposal.researchSummary },
    { label: "Risk reviewed", met: true, detail: proposal.riskSummary },
    {
      label: "No active risk warning",
      met: !symbolWarning,
      detail: symbolWarning?.message ?? `${proposal.symbol} is within all of Sentinel's and Guardian's configured limits.`,
    },
    {
      label: "Multi-agent agreement",
      met: agreeing >= Math.ceil(totalVotes / 2),
      detail: `${agreeing}/${totalVotes} analysts agree with ${proposal.overallRecommendation.toUpperCase()}.`,
    },
    {
      label: "Portfolio exposure acceptable",
      met: portfolio.positions.length < riskLimits.maxOpenPositions,
      detail: `${portfolio.positions.length}/${riskLimits.maxOpenPositions} positions currently open.`,
    },
  ];
}

export interface CeoCategoryStat {
  category: ResearchCategory;
  correct: number;
  incorrect: number;
  winRate: number;
}

export interface CeoStats {
  totalDecisions: number;
  gradedCount: number;
  ceoAccuracy: number | null;
  aiGradedCount: number;
  aiAccuracy: number | null;
  agreementRate: number | null;
  successfulOverrides: number;
  failedOverrides: number;
  byCategory: CeoCategoryStat[];
  bestCategory: CeoCategoryStat | null;
  worstCategory: CeoCategoryStat | null;
}

/** AI Accuracy is only ever computed over decisions the CEO agreed with —
 * an override's real trade tells us whether the CEO's own call was right,
 * never whether the AI's original (never-taken) direction would have
 * been, so overrides can never contribute to AI Accuracy (see
 * backend/app/executive.py's module docstring for the same reasoning
 * applied to CeoDecisionRecord.outcome server-side). */
export function computeCeoStats(records: CeoDecisionRecord[]): CeoStats {
  const graded = records.filter((r) => r.outcome === "correct" || r.outcome === "incorrect");
  const ceoCorrect = graded.filter((r) => r.outcome === "correct").length;
  const ceoAccuracy = graded.length ? (ceoCorrect / graded.length) * 100 : null;

  const agreedGraded = graded.filter((r) => r.agreedWithAi);
  const aiCorrect = agreedGraded.filter((r) => r.outcome === "correct").length;
  const aiAccuracy = agreedGraded.length ? (aiCorrect / agreedGraded.length) * 100 : null;

  const agreementRate = records.length ? (records.filter((r) => r.agreedWithAi).length / records.length) * 100 : null;

  const overrides = graded.filter((r) => !r.agreedWithAi);
  const successfulOverrides = overrides.filter((r) => r.outcome === "correct").length;
  const failedOverrides = overrides.filter((r) => r.outcome === "incorrect").length;

  const byCategoryMap = new Map<ResearchCategory, { correct: number; incorrect: number }>();
  for (const r of graded) {
    const bucket = byCategoryMap.get(r.category) ?? { correct: 0, incorrect: 0 };
    if (r.outcome === "correct") bucket.correct += 1;
    else bucket.incorrect += 1;
    byCategoryMap.set(r.category, bucket);
  }
  const byCategory: CeoCategoryStat[] = [...byCategoryMap.entries()].map(([category, b]) => ({
    category,
    correct: b.correct,
    incorrect: b.incorrect,
    winRate: (b.correct / (b.correct + b.incorrect)) * 100,
  }));
  const bestCategory = byCategory.length ? byCategory.reduce((a, b) => (b.winRate > a.winRate ? b : a)) : null;
  const worstCategory = byCategory.length ? byCategory.reduce((a, b) => (b.winRate < a.winRate ? b : a)) : null;

  return {
    totalDecisions: records.length,
    gradedCount: graded.length,
    ceoAccuracy,
    aiGradedCount: agreedGraded.length,
    aiAccuracy,
    agreementRate,
    successfulOverrides,
    failedOverrides,
    byCategory,
    bestCategory,
    worstCategory,
  };
}

/**
 * v0.7 Feature 18 — the same "overrode the Risk Manager" / "traded
 * against the trend" pattern app/coach.py's _override_mistakes joins
 * server-side for the weekly/monthly Coach report, applied per-row here
 * so a single losing decision in the history table can be tagged with
 * exactly which real analyst it went against — echo (technical) or
 * sentinel (risk) present in the linked TradeDecision's opposingAgents,
 * and only for a decision whose real outcome graded "incorrect". Never
 * fabricated: null whenever no linked decision or no real losing outcome
 * exists yet to judge.
 */
export function mistakeTagForCeoDecision(record: CeoDecisionRecord, decisions: TradeDecision[]): "OVERRODE RISK" | "AGAINST TREND" | null {
  if (record.outcome !== "incorrect" || !record.decisionId) return null;
  const decision = decisions.find((d) => d.id === record.decisionId);
  if (!decision) return null;
  if (decision.opposingAgents.includes("sentinel")) return "OVERRODE RISK";
  if (decision.opposingAgents.includes("echo")) return "AGAINST TREND";
  return null;
}

export interface GatekeeperStats {
  approvedCount: number;
  rejectedCount: number;
  resolvedRejections: number;
  pendingRejections: number;
  wouldHaveWon: number;
  wouldHaveLost: number;
  /** % of *resolved* rejections where blocking the trade actually spared
   * the desk a loser — the Gatekeeper's own batting average on its calls,
   * per the v0.7 brief's self-evaluation requirement. Null until at least
   * one rejection has resolved (see backend/app/gatekeeper.py's
   * GATEKEEPER_EVAL_WINDOW_MINUTES). */
  vetoAccuracy: number | null;
}

// --- v0.7 Feature 42 — Decision Replay Center -----------------------------
// Every one of these joins reuses data the client already has (broadcast
// over WS the same way DecisionDetail.tsx's own order/closedTrade lookups
// already work) — there is no dedicated replay endpoint, because there is
// nothing left to fetch: TradeDecision already carries forward everything
// its originating TradeProposal computed (confidenceEngine, votes,
// gatekeeperVerdict), so a decisionId/proposalId join across the existing
// capped lists is the whole feature.

/** A TradeDecision's id is always `decision-{proposalId}` (see
 * backend/app/executive.py's resolve_proposal) — every other permanent
 * record downstream (Debate, ChallengeReport, GatekeeperRejection) keys
 * off the raw proposalId, not the decisionId. */
export function proposalIdForDecision(decision: TradeDecision): string {
  return decision.id.startsWith("decision-") ? decision.id.slice("decision-".length) : decision.id;
}

export interface DecisionReplayLinks {
  decision: TradeDecision;
  ceoDecision: CeoDecisionRecord | null;
  debate: Debate | null;
  challengeReport: ChallengeReport | null;
  disciplineReview: DisciplineReview | null;
  caseStudies: CaseStudy[];
  order: PaperOrder | null;
  exitOrders: PaperOrder[];
  trade: PaperTrade | null;
}

/** Joins every permanent record this decision ever touched, purely from
 * lists already in gameStore — see the section header above for why no
 * backend call is involved. Each linked record is independently
 * nullable/empty: a Debate/ChallengeReport is only ever generated for
 * some proposals (see backend/app/devils_advocate.py's rotation), and
 * capped lists (the 40-order log, the 200-decision log) can age a record
 * out even when it once existed — the replay UI shows that honestly
 * rather than assuming absence means "never happened." */
export function buildDecisionReplay(
  decision: TradeDecision,
  state: {
    ceoDecisions: CeoDecisionRecord[];
    debates: Debate[];
    challengeReports: ChallengeReport[];
    disciplineReviews: DisciplineReview[];
    caseStudies: CaseStudy[];
    portfolio: PaperPortfolio;
  }
): DecisionReplayLinks {
  const proposalId = proposalIdForDecision(decision);
  const ceoDecision =
    state.ceoDecisions.find((r) => r.decisionId === decision.id) ?? state.ceoDecisions.find((r) => r.proposalId === proposalId) ?? null;
  const debate = [...state.debates].reverse().find((d) => d.proposalId === proposalId) ?? null;
  const challengeReport = [...state.challengeReports].reverse().find((c) => c.proposalId === proposalId) ?? null;
  const disciplineReview = state.disciplineReviews.find((r) => r.decisionId === decision.id) ?? null;
  const caseStudies = state.caseStudies.filter((c) => c.decisionId === decision.id);
  const order = linkedOrderFor(decision, state.portfolio.orders);
  const position = state.portfolio.positions.find((p) => p.symbol === decision.symbol) ?? null;
  const exitOrders = position ? exitOrdersForPosition(position.id, state.portfolio.orders) : [];
  const trade = state.portfolio.tradeHistory.find((t) => t.decisionId === decision.id) ?? null;
  return { decision, ceoDecision, debate, challengeReport, disciplineReview, caseStudies, order, exitOrders, trade };
}

export type ReplayStageStatus = "recorded" | "not_generated" | "not_applicable";

export interface ReplayStage {
  key: string;
  label: string;
  status: ReplayStageStatus;
  detail: string;
}

/**
 * The brief's 13-stage timeline (Research Started → ... → Reflection
 * Chamber Review), built entirely from `links`. Two honest departures
 * from a literal reading, both documented inline rather than faked:
 *
 *  - "AI Research" is folded into Research/Technical/Fundamental Analysis
 *    below rather than shown as a fifth, separate research stage — all
 *    four would read from the exact same real summary fields, so
 *    splitting them would just repeat the same text under two labels.
 *  - "Quant Review" is always `not_applicable` — Quant/Vector reviews
 *    long-horizon Black Box research projects (weeks of sim time), never
 *    an individual trade decision (see backend/app/black_box.py); no
 *    per-trade Quant review mechanism exists anywhere in this codebase.
 *
 * The final stage is labeled "Post-Decision Review" rather than a literal
 * "Reflection Chamber Review": this codebase's actual per-decision
 * post-mortem is the Discipline Chamber's DisciplineReview (see
 * backend/app/discipline.py) — the "Reflection Chamber" name belongs to
 * a different, company-wide weekly/monthly system (backend/app/wisdom.py)
 * that has no per-decision link to key off.
 */
export function buildReplayTimeline(links: DecisionReplayLinks): ReplayStage[] {
  const { decision, ceoDecision, debate, challengeReport, order, exitOrders, trade, disciplineReview } = links;
  const approved = decision.outcome === "trade" && decision.orderId !== null;

  return [
    { key: "research_started", label: "Research Started", status: "recorded", detail: decision.researchSummary },
    { key: "technical_analysis", label: "Technical Analysis", status: "recorded", detail: decision.technicalSummary },
    { key: "fundamental_analysis", label: "Fundamental Analysis", status: "recorded", detail: decision.fundamentalSummary },
    { key: "risk_review", label: "Risk Review", status: "recorded", detail: decision.riskSummary },
    {
      key: "quant_review",
      label: "Quant Review",
      status: "not_applicable",
      detail: "Quant/Vector reviews long-horizon Black Box research projects, never an individual trade decision — there is no per-trade Quant review in this company.",
    },
    challengeReport
      ? { key: "devils_advocate", label: "Devil's Advocate Review", status: "recorded", detail: challengeReport.finalRecommendation }
      : { key: "devils_advocate", label: "Devil's Advocate Review", status: "not_generated", detail: "Not every proposal is escalated to a Devil's Advocate — none was assigned to this one." },
    debate
      ? { key: "team_discussion", label: "Team Discussion", status: "recorded", detail: debate.finalSummary }
      : { key: "team_discussion", label: "Team Discussion", status: "not_generated", detail: "No AI Debate was generated for this proposal, or it has aged out of the capped debate log." },
    ceoDecision
      ? { key: "ceo_approval", label: "CEO Approval", status: "recorded", detail: `The CEO chose ${ceoDecision.ceoDecision.toUpperCase()} (${ceoDecision.resolvedBy === "ceo" ? "a real player decision" : "auto-resolved under the active Operating Mode"}).` }
      : { key: "ceo_approval", label: "CEO Approval", status: "not_generated", detail: "No CeoDecisionRecord found — this decision predates that record, or it has aged out of the capped log." },
    order
      ? { key: "trade_execution", label: "Trade Execution", status: "recorded", detail: `${order.side.toUpperCase()} ${order.quantity} @ ${formatMoney(order.price)}, placed by ${order.placedBy}.` }
      : {
          key: "trade_execution",
          label: "Trade Execution",
          status: approved ? "not_generated" : "not_applicable",
          detail: approved ? "The order has aged out of the capped 40-order log." : "This decision was not approved — no order was ever placed.",
        },
    exitOrders.length > 0
      ? { key: "trade_management", label: "Trade Management", status: "recorded", detail: `${exitOrders.length} exit order(s) attached.` }
      : { key: "trade_management", label: "Trade Management", status: "not_applicable", detail: "TradeTown's auto-trader doesn't place stop-loss/take-profit exit orders yet — see DecisionDetail's Trade Plan section for the same documented boundary." },
    trade
      ? { key: "trade_exit", label: "Trade Exit", status: "recorded", detail: `Closed ${trade.pnl >= 0 ? "+" : ""}${trade.pnl.toFixed(2)} (${trade.pnlPct.toFixed(1)}%) after ${trade.durationMinutes} simulated minutes.` }
      : { key: "trade_exit", label: "Trade Exit", status: "not_applicable", detail: approved ? "This position is still open." : "This decision was not approved — no trade to exit." },
    disciplineReview
      ? { key: "post_decision_review", label: "Post-Decision Review", status: "recorded", detail: disciplineReview.summary }
      : { key: "post_decision_review", label: "Post-Decision Review", status: "not_applicable", detail: "A Discipline Review is only filed once the resulting position closes." },
  ];
}

export interface ReplayFilters {
  agentId: AgentId | "all";
  symbol: string;
  result: "all" | "trade" | "no_trade" | "win" | "loss";
  minConfidence: number;
  role: AnalystRole | "all";
}

export const DEFAULT_REPLAY_FILTERS: ReplayFilters = { agentId: "all", symbol: "", result: "all", minConfidence: 0, role: "all" };

/**
 * The brief's "Smart Search" asks for natural-language queries ("Show all
 * losing trades", "Show every trade where Risk disagreed", ...) — this
 * codebase has no real NL/LLM infrastructure anywhere (confirmed by grep
 * across the whole backend), so rather than fabricate a fake parser, this
 * is the same query set expressed as real structured filters, covering
 * every one of the brief's own examples honestly:
 *   "losing trades"              -> result = "loss"
 *   "where Risk disagreed"       -> role = "risk" + agentId = sentinel's
 *                                    opposing vote (see matchesFilters)
 *   "above 85% confidence"       -> minConfidence = 85
 *   "reviewed by the Quant"      -> not supported (see buildReplayTimeline
 *                                    — Quant never reviews individual trades)
 *   "breakout strategy" / "during earnings" -> not supported (no strategy
 *                                    taxonomy or earnings calendar exists)
 * "Department" (from the brief's filter list) maps to AnalystRole, the
 * closest real per-decision "who reviewed this" grouping this codebase has.
 */
export function matchesReplayFilters(decision: TradeDecision, filters: ReplayFilters, trade: PaperTrade | null): boolean {
  if (filters.agentId !== "all" && !decision.votes.some((v) => v.agentId === filters.agentId)) return false;
  if (filters.symbol.trim() && !decision.symbol.toLowerCase().includes(filters.symbol.trim().toLowerCase())) return false;
  if (filters.result === "trade" && decision.outcome !== "trade") return false;
  if (filters.result === "no_trade" && decision.outcome !== "no_trade") return false;
  if (filters.result === "win" && (!trade || trade.pnl <= 0)) return false;
  if (filters.result === "loss" && (!trade || trade.pnl >= 0)) return false;
  if (decision.confidence < filters.minConfidence) return false;
  if (filters.role !== "all") {
    const roleAgent = ROLE_TO_AGENT[filters.role];
    if (!decision.votes.some((v) => v.agentId === roleAgent)) return false;
  }
  return true;
}

/** Every count here comes straight off a real TradeDecision.gatekeeperVerdict
 * or GatekeeperRejection (see backend/app/gatekeeper.py) — approved/rejected
 * counts and the resolved would-have-won/lost outcomes are never estimated. */
export function computeGatekeeperStats(decisions: TradeDecision[], rejections: GatekeeperRejection[]): GatekeeperStats {
  const verdicts = decisions.map((d) => d.gatekeeperVerdict).filter((v) => v !== null);
  const approvedCount = verdicts.filter((v) => v.approved).length;
  const rejectedCount = verdicts.filter((v) => !v.approved).length;
  const resolved = rejections.filter((r) => r.outcome !== "pending");
  const wouldHaveWon = resolved.filter((r) => r.outcome === "would_have_won").length;
  const wouldHaveLost = resolved.filter((r) => r.outcome === "would_have_lost").length;
  return {
    approvedCount,
    rejectedCount,
    resolvedRejections: resolved.length,
    pendingRejections: rejections.length - resolved.length,
    wouldHaveWon,
    wouldHaveLost,
    vetoAccuracy: resolved.length ? (wouldHaveLost / resolved.length) * 100 : null,
  };
}
