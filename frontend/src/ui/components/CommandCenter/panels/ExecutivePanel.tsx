import { useGameStore } from "@/ui/hooks/useGameStore";
import { CONFIDENCE_TIER_LABEL } from "@/types";
import { EventBus } from "@/game/systems/EventBus";
import { computeCeoStats, computeGatekeeperStats, confidenceTierTone, mistakeTagForCeoDecision } from "../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

const CHOICE_TONE: Record<string, "green" | "red" | "amber"> = { buy: "green", sell: "red", wait: "amber" };
const OUTCOME_TONE: Record<string, "green" | "red" | "cyan" | "neutral"> = {
  correct: "green",
  incorrect: "red",
  pending: "cyan",
  undecidable: "neutral",
};
const GK_OUTCOME_TONE: Record<string, "green" | "red" | "cyan"> = {
  would_have_won: "red", // the Gatekeeper blocked a winner
  would_have_lost: "green", // the veto was correct
  pending: "cyan",
};
const GK_OUTCOME_LABEL: Record<string, string> = {
  would_have_won: "WOULD HAVE WON",
  would_have_lost: "WOULD HAVE LOST",
  pending: "PENDING",
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
  const { tradeProposals, ceoDecisions, decisions, gatekeeperRejections } = useGameStore();
  const stats = computeCeoStats(ceoDecisions);
  const recent = [...ceoDecisions].reverse().slice(0, 12);
  const gkStats = computeGatekeeperStats(decisions, gatekeeperRejections);
  const recentRejections = [...gatekeeperRejections].reverse().slice(0, 8);

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <div className="space-y-3 lg:col-span-1">
        <Glass className="p-3">
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

        <Glass className="p-3">
          <TerminalLabel>Trade Gatekeeper</TerminalLabel>
          <div className="mb-1.5 text-[9px] text-cmd-textDim">
            &quot;The best trade is often the one you don&apos;t take.&quot; Every BUY/SELL passes final approval before it executes.
          </div>
          <DataRow label="Approved" value={gkStats.approvedCount} valueClassName="text-cmd-green" />
          <DataRow label="Rejected" value={gkStats.rejectedCount} valueClassName="text-cmd-red" />
          <DataRow label="Veto accuracy" value={gkStats.vetoAccuracy === null ? "N/A" : `${Math.round(gkStats.vetoAccuracy)}%`} />
          <DataRow label="Would have won" value={gkStats.wouldHaveWon} valueClassName="text-cmd-amber" />
          <DataRow label="Would have lost" value={gkStats.wouldHaveLost} valueClassName="text-cmd-green" />
          <DataRow label="Awaiting resolution" value={gkStats.pendingRejections} />

          <div className="mt-3">
            <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Recent Rejections</div>
            {recentRejections.length === 0 ? (
              <div className="text-cmd-textDim">No trades rejected yet.</div>
            ) : (
              <div className="space-y-1.5">
                {recentRejections.map((r) => (
                  <div key={r.id} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                    <div className="mb-0.5 flex items-center justify-between gap-2">
                      <span className="font-cmdmono text-cmd-cyan">
                        {r.symbol} · {r.ceoChoice.toUpperCase()}
                      </span>
                      <StatusPill tone={GK_OUTCOME_TONE[r.outcome]}>{GK_OUTCOME_LABEL[r.outcome]}</StatusPill>
                    </div>
                    {r.reasons[0] && <div className="text-cmd-textDim">{r.reasons[0]}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </Glass>
      </div>

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
