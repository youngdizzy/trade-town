import { useGameStore } from "@/ui/hooks/useGameStore";
import { CONFIDENCE_TIER_LABEL } from "@/types";
import { EventBus } from "@/game/systems/EventBus";
import {
  computeCeoStats,
  computeGatekeeperStats,
  computeOpportunityGatekeeperStats,
  computePredictionStats,
  confidenceTierTone,
  mistakeTagForCeoDecision,
  priorityScoreFor,
} from "../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";
import { BrierCalibrationCard } from "./BrierCalibrationCard";

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
const PREDICTION_OUTCOME_TONE: Record<string, "green" | "red" | "cyan"> = {
  correct: "green",
  incorrect: "red",
  pending: "cyan",
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
  const { tradeProposals, ceoDecisions, decisions, gatekeeperRejections, opportunityRejections, warRoomSessions, predictionRecords } = useGameStore();
  const stats = computeCeoStats(ceoDecisions);
  const recent = [...ceoDecisions].reverse().slice(0, 12);
  const gkStats = computeGatekeeperStats(decisions, gatekeeperRejections);
  const recentRejections = [...gatekeeperRejections].reverse().slice(0, 8);
  const oppStats = computeOpportunityGatekeeperStats(opportunityRejections);
  const recentOppRejections = [...opportunityRejections].reverse().slice(0, 8);
  const predictionStats = computePredictionStats(predictionRecords);
  const recentPredictions = [...predictionRecords].reverse().slice(0, 8);

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
                    {r.reasonCodes.length > 0 && (
                      <div className="mt-0.5 flex flex-wrap gap-1">
                        {r.reasonCodes.map((code) => (
                          <span key={code} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/60 px-1 py-0.5 text-[8px] text-cmd-textDim">
                            {code}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </Glass>

        <Glass className="p-3">
          <TerminalLabel>Opportunity Gatekeeper</TerminalLabel>
          <div className="mb-1.5 text-[9px] text-cmd-textDim">
            &quot;What deserves to be traded today?&quot; Every candidate is scored on real Decision Score and Expected Value before it ever reaches the CEO — a rejected one never becomes a trade proposal at all.
          </div>
          <DataRow label="Total rejected" value={oppStats.totalRejected} valueClassName="text-cmd-red" />
          <DataRow label="Rejection accuracy" value={oppStats.rejectionAccuracy === null ? "N/A" : `${Math.round(oppStats.rejectionAccuracy)}%`} />
          <DataRow label="Would have won" value={oppStats.wouldHaveWon} valueClassName="text-cmd-amber" />
          <DataRow label="Would have lost" value={oppStats.wouldHaveLost} valueClassName="text-cmd-green" />
          <DataRow label="Awaiting resolution" value={oppStats.pendingRejections} />

          <div className="mt-3">
            <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Recent Rejections</div>
            {recentOppRejections.length === 0 ? (
              <div className="text-cmd-textDim">No opportunities rejected yet.</div>
            ) : (
              <div className="space-y-1.5">
                {recentOppRejections.map((r) => (
                  <div key={r.id} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                    <div className="mb-0.5 flex items-center justify-between gap-2">
                      <span className="font-cmdmono text-cmd-cyan">
                        {r.symbol} · would have {r.wouldHaveRecommended.toUpperCase()}
                      </span>
                      <StatusPill tone={GK_OUTCOME_TONE[r.outcome]}>{GK_OUTCOME_LABEL[r.outcome]}</StatusPill>
                    </div>
                    <div className="text-cmd-textDim">
                      Score {r.decisionScoreAtRejection.toFixed(0)}/100 · EV {r.expectedValueAtRejectionPct >= 0 ? "+" : ""}
                      {r.expectedValueAtRejectionPct.toFixed(1)}%
                    </div>
                    {r.reasons[0] && <div className="text-cmd-textDim">{r.reasons[0]}</div>}
                    {r.reasonCodes.length > 0 && (
                      <div className="mt-0.5 flex flex-wrap gap-1">
                        {r.reasonCodes.map((code) => (
                          <span key={code} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/60 px-1 py-0.5 text-[8px] text-cmd-textDim">
                            {code}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </Glass>

        <Glass className="p-3">
          <TerminalLabel>Prediction Ledger</TerminalLabel>
          <div className="mb-1.5 text-[9px] text-cmd-textDim">
            CEO directive Feature 29 — every real trade-direction claim is staked before its outcome is known, then resolved purely from the trade&apos;s
            own real closed P&amp;L. Never regraded, never resolved early.
          </div>
          <DataRow label="Total predictions" value={predictionStats.totalPredictions} />
          <DataRow label="Resolved" value={predictionStats.resolvedPredictions} />
          <DataRow label="Accuracy" value={predictionStats.accuracyPct === null ? "N/A" : `${Math.round(predictionStats.accuracyPct)}%`} />
          <DataRow label="Awaiting resolution" value={predictionStats.pendingPredictions} />

          <div className="mt-3">
            <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Recent Predictions</div>
            {recentPredictions.length === 0 ? (
              <div className="text-cmd-textDim">No predictions staked yet.</div>
            ) : (
              <div className="space-y-1.5">
                {recentPredictions.map((p) => (
                  <div key={p.id} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                    <div className="mb-0.5 flex items-center justify-between gap-2">
                      <span className="font-cmdmono text-cmd-cyan">
                        {p.symbol} · {p.predictedDirection.toUpperCase()}
                      </span>
                      <StatusPill tone={PREDICTION_OUTCOME_TONE[p.outcome]}>{p.outcome.toUpperCase()}</StatusPill>
                    </div>
                    <div className="text-cmd-textDim">
                      {Math.round(p.confidencePct)}% confidence{p.resolvedPnlPct !== null ? ` · real P&L ${p.resolvedPnlPct >= 0 ? "+" : ""}${p.resolvedPnlPct.toFixed(1)}%` : ""}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Glass>

        <BrierCalibrationCard />
      </div>

      <div className="space-y-3 lg:col-span-2">
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Pending Proposals ({tradeProposals.length})</TerminalLabel>
            <span className="text-[8px] uppercase tracking-wide text-cmd-textDim">Ranked by Priority Score · v0.7 Chapter 59</span>
          </div>
          {tradeProposals.length === 0 ? (
            <EmptyState>No trade proposals awaiting a decision.</EmptyState>
          ) : (
            <div className="space-y-1.5">
              {tradeProposals.map((p, i) => {
                const score = priorityScoreFor(p, warRoomSessions);
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => EventBus.emit("ui:executiveVoting", { open: true, proposalId: p.id })}
                    className="flex w-full items-center justify-between gap-2 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-left transition-colors hover:border-cmd-cyan/40"
                  >
                    <span className="font-cmdmono text-cmd-textDim">#{i + 1}</span>
                    <span className="font-cmdmono text-cmd-cyan">{p.symbol}</span>
                    <span className="text-[9px] text-cmd-textDim">{score === null ? "Priority N/A" : `Priority ${Math.round(score)}/100`}</span>
                    <span className="text-[9px] text-cmd-textDim">{Math.round(p.confidence)}% confidence</span>
                    <StatusPill tone={confidenceTierTone(p.confidenceEngine.tier)}>
                      {CONFIDENCE_TIER_LABEL[p.confidenceEngine.tier]} · {Math.round(p.confidenceEngine.score)}
                    </StatusPill>
                    <StatusPill tone={CHOICE_TONE[p.overallRecommendation]}>{p.overallRecommendation.toUpperCase()}</StatusPill>
                  </button>
                );
              })}
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
                      {r.resolvedBy === "auto" ? "desk auto-decided" : "you"} {r.ceoDecision.toUpperCase()} · desk {r.aiRecommendation.toUpperCase()}
                    </span>
                    {/* v0.7 Feature 21 — resolvedBy is honest provenance: "auto" covers a
                        Company Operating Mode auto-resolution or a stale-proposal expiry,
                        never a real player click (see backend/app/executive.py). */}
                    {r.resolvedBy === "auto" && <StatusPill tone="cyan">AUTO</StatusPill>}
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
