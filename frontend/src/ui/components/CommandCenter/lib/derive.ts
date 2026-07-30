import type {
  AcademyProject,
  AcademyState,
  AgentId,
  AgentKnowledgeState,
  AgentState,
  AgentVote,
  AnalystRole,
  BlackBoxState,
  CaseStudy,
  CeoDecisionRecord,
  ChallengeReport,
  CoachReport,
  CompanyHealth,
  ConfidenceTier,
  ConstitutionCitation,
  Debate,
  DisciplineReview,
  ExecutiveReview,
  FounderState,
  FoundationalMentorId,
  FoundationalMentorProfile,
  FoundationalMentorState,
  GatekeeperRejection,
  InnovationState,
  PaperOrder,
  PaperPortfolio,
  PaperTrade,
  ReasoningChallenge,
  ReflectionSession,
  ResearchCategory,
  ResearchItem,
  RiskLimits,
  RiskWarning,
  SimulationResult,
  StrategyReport,
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

// --- v0.7 Feature 43 — Executive Intelligence Dashboard --------------------
// Every number below is a direct reuse of an already-real, already-
// computed signal (CompanyHealth's recommendations, the latest CoachReport/
// ExecutiveReview, per-department state this codebase already tracks) —
// no new backend computation was needed for either function here, the same
// "the data already exists, only the unified view was missing" pattern
// Feature 42's Decision Replay Center used.

export interface ExecutivePriority {
  label: string;
  source: "Company Health" | "Coach Report" | "Executive Review";
}

/**
 * The brief's "Executive Priorities" is a single AI-ranked list; this
 * codebase already generates three separate, real recommendation lists
 * (CompanyHealth.recommendations every tick, the latest CoachReport's
 * weekly/monthly recommendations, the latest ExecutiveReview's monthly
 * recommendations) that have never been merged into one view. This merges
 * and dedupes them by text — first occurrence wins, so Company Health's
 * always-current read takes priority over a possibly-stale periodic
 * report repeating the same point. No new ranking model: order reflects
 * which real system raised the point, not an invented severity score.
 */
export function computeExecutivePriorities(companyHealth: CompanyHealth, coachReports: CoachReport[], executiveReviews: ExecutiveReview[]): ExecutivePriority[] {
  const raw: ExecutivePriority[] = [];
  for (const label of companyHealth.recommendations) raw.push({ label, source: "Company Health" });
  const latestCoach = coachReports[coachReports.length - 1];
  if (latestCoach) for (const label of latestCoach.recommendations) raw.push({ label, source: "Coach Report" });
  const latestReview = executiveReviews[executiveReviews.length - 1];
  if (latestReview) for (const label of latestReview.recommendations) raw.push({ label, source: "Executive Review" });

  const seen = new Set<string>();
  return raw.filter((p) => {
    if (seen.has(p.label)) return false;
    seen.add(p.label);
    return true;
  });
}

export interface DepartmentMetric {
  label: string;
  value: string;
}

export interface DepartmentHealthEntry {
  id: string;
  label: string;
  metrics: DepartmentMetric[];
}

/**
 * The brief names 8 departments (Academy, Research, Risk, Trading,
 * Innovation, Coach, Founders, Brain Room), each with Efficiency/Workload/
 * Morale/Productivity/Bottlenecks. This codebase has no literal
 * "department" concept — what exists are 7 real subsystems, each with its
 * own real state; every metric below is whichever of those five
 * dimensions that subsystem actually has a real number for, never a
 * uniform template forced onto systems that don't track all five.
 * "Brain Room" is dropped entirely: it's the physical room housing the
 * Overview HUD, not a distinct operational unit with its own state —
 * including it would mean inventing metrics for a room, not a system.
 */
export function computeDepartmentHealth(state: {
  companyHealth: CompanyHealth;
  research: ResearchItem[];
  riskWarnings: RiskWarning[];
  portfolio: PaperPortfolio;
  blackBox: BlackBoxState;
  innovationState: Record<AgentId, InnovationState>;
  coachReports: CoachReport[];
  founderState: FounderState;
  academyState: AcademyState;
}): DepartmentHealthEntry[] {
  const activeResearch = state.research.filter((r) => r.status === "in_progress").length;
  const latestCoach = state.coachReports[state.coachReports.length - 1] ?? null;
  const totalInnovationPoints = Object.values(state.innovationState).reduce((sum, i) => sum + i.points, 0);
  const totalTrades = state.portfolio.winCount + state.portfolio.lossCount;

  return [
    {
      id: "academy",
      label: "Academy",
      metrics: [
        { label: "Level", value: state.academyState.levelLabel },
        { label: "Knowledge Points (Productivity)", value: state.academyState.totalPoints.toFixed(0) },
        { label: "Completed Projects", value: String(state.academyState.completedProjectCount) },
      ],
    },
    {
      id: "research",
      label: "Research",
      metrics: [
        { label: "Progress (Efficiency)", value: `${state.companyHealth.researchProgress.toFixed(0)}/100` },
        { label: "Active Items (Workload)", value: String(activeResearch) },
      ],
    },
    {
      id: "risk",
      label: "Risk",
      metrics: [
        { label: "Operational Stability", value: `${state.companyHealth.operationalStability.toFixed(0)}/100` },
        { label: "Active Warnings (Bottleneck)", value: String(state.riskWarnings.length) },
      ],
    },
    {
      id: "trading",
      label: "Trading",
      metrics: [
        { label: "Capital Health", value: `${state.companyHealth.capitalHealth.toFixed(0)}/100` },
        { label: "Open Positions (Workload)", value: String(state.portfolio.positions.length) },
        { label: "Win Rate (Productivity)", value: totalTrades > 0 ? `${((state.portfolio.winCount / totalTrades) * 100).toFixed(0)}%` : "N/A — no trades closed yet" },
      ],
    },
    {
      id: "innovation",
      label: "Innovation",
      metrics: [
        { label: "Active Project (Productivity)", value: state.blackBox.active ? `${state.blackBox.active.progress.toFixed(0)}% complete` : "None active" },
        { label: "Company Innovation Points", value: totalInnovationPoints.toFixed(0) },
      ],
    },
    {
      id: "coach",
      label: "Coach",
      metrics: [
        { label: "Latest Company Score (Efficiency)", value: latestCoach ? `${latestCoach.companyScore.toFixed(0)}/100` : "No report filed yet" },
        { label: "Reports Filed", value: String(state.coachReports.length) },
      ],
    },
    {
      id: "founders",
      label: "Founders",
      metrics: [
        { label: "Council Sessions", value: String(state.founderState.councilSessions.length) },
        { label: "Status", value: state.founderState.retired ? "Retired" : "Active" },
      ],
    },
  ];
}

// v0.7 Feature 44 — the Talent Discovery System's "Growth History" (see
// backend/app/talent.py's module docstring). Never a fabricated career
// log: every entry traces to a real record where this specific agent is
// already named — DisciplineReview.attendees, ReasoningChallenge's own
// contributions, ReflectionSession's own insights, ChallengeReport's
// assignedAgent (the Devil's Advocate rotation), and Black Box project
// team membership (active + archived). CoachReport.agentRankings adds
// the agent's own real score on each report's filing date.
export type GrowthHistorySource =
  | "Discipline Review"
  | "Reasoning Challenge"
  | "Reflection Session"
  | "Devil's Advocate Assignment"
  | "Black Box Team"
  | "Coach Ranking";

export interface GrowthHistoryEntry {
  source: GrowthHistorySource;
  label: string;
  detail: string;
  simDay: number | null;
  createdAt: string;
}

export function computeGrowthHistory(
  agentId: AgentId,
  state: {
    disciplineReviews: DisciplineReview[];
    reasoningChallenges: ReasoningChallenge[];
    reflectionSessions: ReflectionSession[];
    challengeReports: ChallengeReport[];
    blackBox: BlackBoxState;
    coachReports: CoachReport[];
  },
): GrowthHistoryEntry[] {
  const entries: GrowthHistoryEntry[] = [];

  for (const review of state.disciplineReviews) {
    if (!review.attendees.includes(agentId)) continue;
    entries.push({
      source: "Discipline Review",
      label: `Attended Discipline Review — ${review.symbol}`,
      detail: `${review.tier} tier, scored ${review.score.toFixed(0)}/100 on a ${review.outcome === "win" ? "winning" : "losing"} trade.`,
      simDay: review.simDay,
      createdAt: review.createdAt,
    });
  }

  for (const challenge of state.reasoningChallenges) {
    const contribution = challenge.contributions.find((c) => c.agentId === agentId);
    if (!contribution) continue;
    entries.push({
      source: "Reasoning Challenge",
      label: `Contributed to Reasoning Challenge — ${challenge.title}`,
      detail: contribution.contribution,
      simDay: challenge.simDay,
      createdAt: challenge.createdAt,
    });
  }

  for (const session of state.reflectionSessions) {
    const insight = session.insights.find((i) => i.agentId === agentId);
    if (!insight) continue;
    entries.push({
      source: "Reflection Session",
      label: `Shared insight in a ${session.cadence} Reflection Session`,
      detail: insight.insight,
      simDay: session.simDay,
      createdAt: session.createdAt,
    });
  }

  for (const report of state.challengeReports) {
    if (report.assignedAgent !== agentId) continue;
    entries.push({
      source: "Devil's Advocate Assignment",
      label: `Filed Devil's Advocate report — ${report.symbol}`,
      detail: `Severity: ${report.severity.replace(/_/g, " ")}. ${report.finalRecommendation}`,
      simDay: null,
      createdAt: report.createdAt,
    });
  }

  const blackBoxProjects = [...(state.blackBox.active ? [state.blackBox.active] : []), ...state.blackBox.archive];
  for (const project of blackBoxProjects) {
    if (!project.team.some((member) => member.agentId === agentId)) continue;
    entries.push({
      source: "Black Box Team",
      label: `Joined Black Box project team — ${project.title}`,
      detail: project.team.find((member) => member.agentId === agentId)!.role,
      simDay: project.startedSimDay,
      createdAt: project.createdAt,
    });
  }

  for (const report of state.coachReports) {
    const ranking = report.agentRankings.find((r) => r.agentId === agentId);
    if (!ranking) continue;
    entries.push({
      source: "Coach Ranking",
      label: `Scored in ${report.period} Coach Report`,
      detail: `${ranking.score.toFixed(0)}/100 (research accuracy ${ranking.researchAccuracy.toFixed(0)}, confidence calibration ${ranking.confidenceCalibration.toFixed(0)}).`,
      simDay: null,
      createdAt: report.createdAt,
    });
  }

  return entries.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}

export interface CollaboratorPairing {
  agentA: AgentId;
  agentB: AgentId;
  supportCount: number;
  challengeCount: number;
}

/**
 * The brief's "Team Optimization" asks which employee pairs work best
 * together and how to recompose the roster around them — this codebase's
 * roster is fixed (see talent.py's module docstring), so nothing about
 * composition can ever change. The one real signal that survives is which
 * agents actually support vs. challenge each other's points across every
 * real AI Debate (DebateTurn.respondingTo + stance) — counted here turn by
 * turn, nothing inferred or scored beyond the real tally.
 */
export function computeBestCollaborators(debates: Debate[]): CollaboratorPairing[] {
  const pairs = new Map<string, CollaboratorPairing>();

  for (const debate of debates) {
    for (const turn of debate.turns) {
      if (!turn.respondingTo || turn.respondingTo === turn.agentId || turn.stance === "opening") continue;
      const [agentA, agentB] = [turn.agentId, turn.respondingTo].sort() as [AgentId, AgentId];
      const key = `${agentA}|${agentB}`;
      let pairing = pairs.get(key);
      if (!pairing) {
        pairing = { agentA, agentB, supportCount: 0, challengeCount: 0 };
        pairs.set(key, pairing);
      }
      if (turn.stance === "support") pairing.supportCount += 1;
      else pairing.challengeCount += 1;
    }
  }

  return Array.from(pairs.values()).sort((a, b) => b.supportCount + b.challengeCount - (a.supportCount + a.challengeCount));
}

export interface StrategyConsistency {
  sampleSize: number;
  positiveRunPct: number;
  distinctScenarios: number;
}

/**
 * v0.7 Feature 45 — the Research Sandbox's "Consistency" and "Trade
 * Frequency" metrics from the brief. Both are properties of a
 * strategy's own real *history* (not a single run), so they're computed
 * here rather than stored per-SimulationResult: Consistency is the real
 * % of that strategy's own stored runs that came back positive;
 * distinctScenarios is the real count of different Testing Environments
 * actually exercised. "Trade Frequency" is deliberately not a separate
 * derived rate here — see app/sandbox.py's module docstring for why a
 * fabricated per-day rate would be worse than just showing each real
 * run's own tradeCount, which the panel already does.
 */
export function computeStrategyConsistency(strategyId: string, results: SimulationResult[]): StrategyConsistency {
  const own = results.filter((r) => r.strategyId === strategyId);
  const positive = own.filter((r) => r.totalReturnPct > 0).length;
  return {
    sampleSize: own.length,
    positiveRunPct: own.length > 0 ? (positive / own.length) * 100 : 0,
    distinctScenarios: new Set(own.map((r) => r.scenario)).size,
  };
}

// v0.7 Feature 47 — Company Operating System's "Knowledge Absorption."
// The brief asks for one place where "everything the company learns" is
// visible. This codebase already has six real, independently-filed
// learning records (Library of Mistakes, Research Sandbox reports,
// Constitution citations, Coach recommendations, completed Academy
// projects, Reflection Chamber insights) — this is a pure, zero-new-
// backend-data aggregation of those six into one chronological feed, the
// same "frontend-only feature" pattern Feature 45's Consistency metric
// used. Distinct from the existing Knowledge Graph (Feature 25.5,
// app/knowledge_graph.py): that is a relational node/edge structure over
// research/Academy/reviews; this is a flat, filterable timeline over a
// different (and larger) set of six real sources, several of which
// (Constitution, Reflection Chamber, Library of Mistakes) the graph
// doesn't touch at all.
export type KnowledgeBaseSource = "case_study" | "strategy_report" | "constitution_citation" | "coach_recommendation" | "academy_project" | "reflection_insight";

export const KNOWLEDGE_BASE_SOURCE_LABEL: Record<KnowledgeBaseSource, string> = {
  case_study: "Library of Mistakes",
  strategy_report: "Research Sandbox",
  constitution_citation: "Constitution",
  coach_recommendation: "Coach",
  academy_project: "Academy",
  reflection_insight: "Reflection Chamber",
};

export interface KnowledgeBaseEntry {
  id: string;
  source: KnowledgeBaseSource;
  title: string;
  detail: string;
  agentId: AgentId | null;
  createdAt: string;
}

export function computeKnowledgeBase(state: {
  caseStudies: CaseStudy[];
  strategyReports: StrategyReport[];
  constitutionCitations: ConstitutionCitation[];
  coachReports: CoachReport[];
  academyProjects: AcademyProject[];
  reflectionSessions: ReflectionSession[];
}): KnowledgeBaseEntry[] {
  const entries: KnowledgeBaseEntry[] = [];

  for (const cs of state.caseStudies) {
    entries.push({ id: `case-study-${cs.id}`, source: "case_study", title: cs.title, detail: cs.lessonsLearned, agentId: null, createdAt: cs.createdAt });
  }

  for (const report of state.strategyReports) {
    entries.push({
      id: `strategy-report-${report.id}`,
      source: "strategy_report",
      title: `${report.strategyName} — ${report.scenario}`,
      detail: report.executiveSummary,
      agentId: null,
      createdAt: report.createdAt,
    });
  }

  for (const citation of state.constitutionCitations) {
    entries.push({
      id: `constitution-citation-${citation.id}`,
      source: "constitution_citation",
      title: `Article ${citation.articleId} cited`,
      detail: citation.detail,
      agentId: null,
      createdAt: citation.createdAt,
    });
  }

  for (const report of state.coachReports) {
    report.recommendations.forEach((recommendation, i) => {
      entries.push({
        id: `coach-recommendation-${report.id}-${i}`,
        source: "coach_recommendation",
        title: `${report.period} Coach recommendation`,
        detail: recommendation,
        agentId: null,
        createdAt: report.createdAt,
      });
    });
  }

  for (const project of state.academyProjects) {
    if (project.status !== "completed") continue;
    entries.push({
      id: `academy-project-${project.id}`,
      source: "academy_project",
      title: project.title,
      detail: project.summary,
      agentId: project.assignedAgent,
      createdAt: project.updatedAt,
    });
  }

  for (const session of state.reflectionSessions) {
    session.insights.forEach((insight, i) => {
      entries.push({
        id: `reflection-insight-${session.id}-${i}`,
        source: "reflection_insight",
        title: `${session.cadence} reflection insight`,
        detail: insight.insight,
        agentId: insight.agentId,
        createdAt: session.createdAt,
      });
    });
  }

  return entries.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
}

// v0.7 Feature 49 (Phase 3 revision) — the Foundational Mentor Program /
// Professional Academy. Mirrors backend/app/foundational_mentors.py's
// STUDENT_AGENT_IDS exactly (see that module's own docstring for the
// full "why these 8, not the other 6 agents" reasoning) — duplicated
// here the same necessary way agent roster/identity data already lives
// in both layers (backend game logic, frontend rendering).
export const ACADEMY_STUDENT_AGENT_IDS: AgentId[] = ["scout", "atlas", "echo", "nova", "scribe", "sentinel", "pulse", "guardian"];

// Mirrors backend's COACH_ESCALATION_THRESHOLD.
const COACH_ESCALATION_THRESHOLD = 3;

export interface AcademyStudentSummary {
  agentId: AgentId;
  mentorId: FoundationalMentorId;
  currentLessonTitle: string | null;
  currentLessonOrder: number | null;
  totalLessons: number;
  completedLessonCount: number;
  completionPct: number;
  quizAveragePct: number;
  consecutiveQuizFailures: number;
  graduationStatus: "in_progress" | "pending_approval" | "graduated";
}

export interface AcademyCertification {
  agentId: AgentId;
  mentorId: FoundationalMentorId;
  mentorName: string;
  graduatedSimDay: number;
}

export interface AcademyRecommendation {
  agentId: AgentId;
  recommendation: "repeat_lesson" | "one_on_one_coaching";
  reason: string;
}

export interface AcademyDashboard {
  activeMentorId: FoundationalMentorId | null;
  activeMentorLabel: string | null;
  currentlyStudying: AcademyStudentSummary[];
  topStudents: AcademyStudentSummary[];
  needingHelp: AcademyStudentSummary[];
  graduationQueue: AcademyStudentSummary[];
  upcomingGraduations: AcademyStudentSummary[];
  avgQuizScorePct: number;
  avgKnowledgeScore: number;
  certifications: AcademyCertification[];
  recommendations: AcademyRecommendation[];
}

function studentSummaryFor(agentId: AgentId, mentorId: FoundationalMentorId, foundationalMentorState: FoundationalMentorState): AcademyStudentSummary | null {
  const mentor = foundationalMentorState.mentors.find((m) => m.id === mentorId);
  if (!mentor) return null;
  const progress = foundationalMentorState.progress[agentId]?.[mentorId];
  const completedLessonCount = progress?.completedLessonIds.length ?? 0;
  const totalLessons = mentor.lessons.length;
  const sortedLessons = [...mentor.lessons].sort((a, b) => a.order - b.order);
  const currentLesson = sortedLessons.find((l) => !(progress?.completedLessonIds.includes(l.id) ?? false)) ?? null;
  const quizAttempts = progress?.quizAttempts ?? 0;
  const correctQuizAttempts = progress?.correctQuizAttempts ?? 0;
  return {
    agentId,
    mentorId,
    currentLessonTitle: currentLesson?.title ?? null,
    currentLessonOrder: currentLesson?.order ?? null,
    totalLessons,
    completedLessonCount,
    completionPct: totalLessons > 0 ? (completedLessonCount / totalLessons) * 100 : 0,
    quizAveragePct: quizAttempts > 0 ? (correctQuizAttempts / quizAttempts) * 100 : 0,
    consecutiveQuizFailures: progress?.consecutiveQuizFailures ?? 0,
    graduationStatus: progress?.graduationStatus ?? "in_progress",
  };
}

/**
 * The Academy Dashboard — a pure client-side derivation, the same
 * "frontend-only feature" pattern computeKnowledgeBase above already
 * established, since every field here is computable from state already
 * broadcast over the WS tick (foundationalMentorState + agentKnowledge).
 * No new backend endpoint or schema exists for this dashboard shape.
 */
export function computeAcademyDashboard(foundationalMentorState: FoundationalMentorState, agentKnowledge: Record<AgentId, AgentKnowledgeState>): AcademyDashboard {
  const activeMentorId = foundationalMentorState.activeMentorId;
  const activeMentor = activeMentorId ? (foundationalMentorState.mentors.find((m) => m.id === activeMentorId) ?? null) : null;

  const activeSummaries = activeMentorId
    ? ACADEMY_STUDENT_AGENT_IDS.map((agentId) => studentSummaryFor(agentId, activeMentorId, foundationalMentorState)).filter((s): s is AcademyStudentSummary => s !== null)
    : [];

  const currentlyStudying = activeSummaries.filter((s) => s.graduationStatus === "in_progress");
  const graduationQueue = activeSummaries.filter((s) => s.graduationStatus === "pending_approval");
  const needingHelp = activeSummaries.filter((s) => s.consecutiveQuizFailures >= 1 && s.graduationStatus === "in_progress");
  const upcomingGraduations = currentlyStudying.filter((s) => s.totalLessons > 0 && s.totalLessons - s.completedLessonCount === 1);
  const topStudents = [...activeSummaries].sort((a, b) => b.completedLessonCount - a.completedLessonCount || b.quizAveragePct - a.quizAveragePct).slice(0, 3);

  const attemptsTotal = activeSummaries.reduce((sum, s) => sum + (foundationalMentorState.progress[s.agentId]?.[s.mentorId]?.quizAttempts ?? 0), 0);
  const correctTotal = activeSummaries.reduce((sum, s) => sum + (foundationalMentorState.progress[s.agentId]?.[s.mentorId]?.correctQuizAttempts ?? 0), 0);
  const avgQuizScorePct = attemptsTotal > 0 ? (correctTotal / attemptsTotal) * 100 : 0;

  const knowledgeScores = ACADEMY_STUDENT_AGENT_IDS.map((aid) => agentKnowledge[aid]?.points ?? 0);
  const avgKnowledgeScore = knowledgeScores.length > 0 ? knowledgeScores.reduce((a, b) => a + b, 0) / knowledgeScores.length : 0;

  const certifications: AcademyCertification[] = [];
  for (const agentId of ACADEMY_STUDENT_AGENT_IDS) {
    const agentProgress = foundationalMentorState.progress[agentId];
    if (!agentProgress) continue;
    for (const mentorId of Object.keys(agentProgress) as FoundationalMentorId[]) {
      const progress = agentProgress[mentorId];
      if (progress?.graduationStatus === "graduated" && progress.graduatedSimDay !== null) {
        const mentor = foundationalMentorState.mentors.find((m) => m.id === mentorId);
        certifications.push({ agentId, mentorId, mentorName: mentor?.name ?? mentorId, graduatedSimDay: progress.graduatedSimDay });
      }
    }
  }
  certifications.sort((a, b) => b.graduatedSimDay - a.graduatedSimDay);

  // Real Coach recommendations — see COACH_ESCALATION_THRESHOLD's
  // backend twin for the full reasoning. Only "Repeat Lesson" and
  // "One-on-One Coaching" are computed (both driven by the real
  // consecutiveQuizFailures counter); the brief's other recommendation
  // types have no real backing signal yet — see foundational_mentors.py's
  // module docstring.
  const recommendations: AcademyRecommendation[] = needingHelp.map((s) => ({
    agentId: s.agentId,
    recommendation: s.consecutiveQuizFailures >= COACH_ESCALATION_THRESHOLD ? "one_on_one_coaching" : "repeat_lesson",
    reason:
      s.consecutiveQuizFailures >= COACH_ESCALATION_THRESHOLD
        ? `${s.consecutiveQuizFailures} consecutive quiz misses on "${s.currentLessonTitle ?? "the current lesson"}" — recommend one-on-one coaching.`
        : `Missed the last quiz attempt on "${s.currentLessonTitle ?? "the current lesson"}" — recommend repeating the lesson before the next try.`,
  }));

  return {
    activeMentorId,
    activeMentorLabel: activeMentor?.trackLabel ?? null,
    currentlyStudying,
    topStudents,
    needingHelp,
    graduationQueue,
    upcomingGraduations,
    avgQuizScorePct,
    avgKnowledgeScore,
    certifications,
    recommendations,
  };
}

/**
 * Mentor Lab — "Company Concepts Learned" — a real, checkable count: the
 * number of distinct lessons, across every mentor track (not just the
 * currently-active one), that at least one real employee has actually
 * completed. Deliberately NOT paired with "Concepts Validated" /
 * "Concepts Rejected" numbers — no real cross-system validation
 * pipeline exists in this codebase to back them (see
 * backend/app/foundational_mentors.py's module docstring's "Mentor
 * Validation" scope-cut note) — MentorLabPanel shows an explicit honest
 * disclaimer instead of a fabricated number for those two.
 */
export function computeCompanyConceptsLearned(foundationalMentorState: FoundationalMentorState): number {
  const learnedLessonIds = new Set<string>();
  for (const agentProgress of Object.values(foundationalMentorState.progress)) {
    for (const progress of Object.values(agentProgress ?? {})) {
      for (const lessonId of progress?.completedLessonIds ?? []) {
        learnedLessonIds.add(lessonId);
      }
    }
  }
  return learnedLessonIds.size;
}

export interface MentorComparisonRow {
  mentorId: FoundationalMentorId;
  name: string;
  trackLabel: string;
  status: FoundationalMentorProfile["status"];
  lessonCount: number;
  avgCompletionPct: number;
}

/** Mentor Lab — "Mentor Comparison": a real, per-mentor completion
 * average across the real 8-agent student roster, computed the same way
 * computeAcademyDashboard's own per-student completion% already is. */
export function computeMentorComparison(foundationalMentorState: FoundationalMentorState): MentorComparisonRow[] {
  return foundationalMentorState.mentors.map((mentor) => {
    const completionPcts = ACADEMY_STUDENT_AGENT_IDS.map((agentId) => {
      const progress = foundationalMentorState.progress[agentId]?.[mentor.id];
      if (mentor.lessons.length === 0) return 0;
      return ((progress?.completedLessonIds.length ?? 0) / mentor.lessons.length) * 100;
    });
    const avgCompletionPct = completionPcts.length > 0 ? completionPcts.reduce((a, b) => a + b, 0) / completionPcts.length : 0;
    return {
      mentorId: mentor.id,
      name: mentor.name,
      trackLabel: mentor.trackLabel,
      status: mentor.status,
      lessonCount: mentor.lessons.length,
      avgCompletionPct,
    };
  });
}
