import { useGameStore } from "@/ui/hooks/useGameStore";
import { CONFIDENCE_TIER_LABEL } from "@/types";
import { EventBus } from "@/game/systems/EventBus";
import { computeCeoStats, confidenceTierTone, mistakeTagForCeoDecision } from "../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

const CHOICE_TONE: Record<string, "green" | "red" | "amber"> = { buy: "green", sell: "red", wait: "amber" };
const OUTCOME_TONE: Record<string, "green" | "red" | "cyan" | "neutral"> = {
  correct: "green",
  incorrect: "red",
  pending: "cyan",
  undecidable: "neutral",
};

/**
 * Feature 12's history/stats view — every number here comes straight off
 * CeoDecisionRecord (see backend/app/executive.py); nothing is computed
 * against a trade that never actually happened. AI Accuracy only ever
 * covers decisions the CEO agreed with, since an override's real trade
 * only tells us whether the CEO's own call worked — see computeCeoStats'
 * own doc comment for why overrides can't grade the AI itself.
 */
export function ExecutivePanel() {
  const { tradeProposals, ceoDecisions, decisions } = useGameStore();
  const stats = computeCeoStats(ceoDecisions);
  const recent = [...ceoDecisions].reverse().slice(0, 12);

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <Glass className="p-3 lg:col-span-1">
        <TerminalLabel>CEO Track Record</TerminalLabel>
        <DataRow label="Decisions made" value={stats.totalDecisions} />
        <DataRow label="Graded (real trades)" value={stats.gradedCount} />
        <DataRow label="CEO accuracy" value={stats.ceoAccuracy === null ? "N/A" : `${Math.round(stats.ceoAccuracy)}%`} />
        <DataRow label="AI accuracy (agreed)" value={stats.aiAccuracy === null ? "N/A" : `${Math.round(stats.aiAccuracy)}%`} />
        <DataRow label="Agreement rate" value={stats.agreementRate === null ? "N/A" : `${Math.round(stats.agreementRate)}%`} />
        <DataRow label="Successful overrides" value={stats.successfulOverrides} valueClassName="text-cmd-green" />
        <DataRow label="Failed overrides" value={stats.failedOverrides} valueClassName="text-cmd-red" />

        <div className="mt-3">
          <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Best / Worst Setup</div>
          {stats.bestCategory ? (
            <DataRow label={`Best: ${stats.bestCategory.category}`} value={`${Math.round(stats.bestCategory.winRate)}%`} valueClassName="text-cmd-green" />
          ) : (
            <div className="text-cmd-textDim">No graded decisions yet.</div>
          )}
          {stats.worstCategory && stats.worstCategory !== stats.bestCategory && (
            <DataRow label={`Worst: ${stats.worstCategory.category}`} value={`${Math.round(stats.worstCategory.winRate)}%`} valueClassName="text-cmd-red" />
          )}
        </div>
      </Glass>

      <div className="space-y-3 lg:col-span-2">
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Pending Proposals ({tradeProposals.length})</TerminalLabel>
          </div>
          {tradeProposals.length === 0 ? (
            <EmptyState>No trade proposals awaiting a decision.</EmptyState>
          ) : (
            <div className="space-y-1.5">
              {tradeProposals.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => EventBus.emit("ui:executiveVoting", { open: true, proposalId: p.id })}
                  className="flex w-full items-center justify-between gap-2 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-left transition-colors hover:border-cmd-cyan/40"
                >
                  <span className="font-cmdmono text-cmd-cyan">{p.symbol}</span>
                  <span className="text-[9px] text-cmd-textDim">{Math.round(p.confidence)}% confidence</span>
                  <StatusPill tone={confidenceTierTone(p.confidenceEngine.tier)}>
                    {CONFIDENCE_TIER_LABEL[p.confidenceEngine.tier]} · {Math.round(p.confidenceEngine.score)}
                  </StatusPill>
                  <StatusPill tone={CHOICE_TONE[p.overallRecommendation]}>{p.overallRecommendation.toUpperCase()}</StatusPill>
                </button>
              ))}
            </div>
          )}
        </Glass>

        <Glass className="p-3">
          <TerminalLabel>Decision History</TerminalLabel>
          {recent.length === 0 ? (
            <EmptyState>No CEO decisions recorded yet.</EmptyState>
          ) : (
            <div className="divide-y divide-cmd-border/60">
              {recent.map((r) => {
                const mistakeTag = mistakeTagForCeoDecision(r, decisions);
                return (
                  <div key={r.id} className="flex items-center justify-between gap-2 py-1.5">
                    <span className="font-cmdmono text-cmd-cyan">{r.symbol}</span>
                    <span className="text-[9px] text-cmd-textDim">
                      you {r.ceoDecision.toUpperCase()} · desk {r.aiRecommendation.toUpperCase()}
                    </span>
                    {!r.agreedWithAi && <StatusPill tone="purple">OVERRIDE</StatusPill>}
                    {mistakeTag && <StatusPill tone="red">{mistakeTag}</StatusPill>}
                    <StatusPill tone={OUTCOME_TONE[r.outcome]}>{r.outcome.toUpperCase()}</StatusPill>
                  </div>
                );
              })}
            </div>
          )}
        </Glass>
      </div>
    </div>
  );
}
