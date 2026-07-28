import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { AnalystChoice, AnalystVote, TradeProposal } from "@/types";
import { CONFIDENCE_TIER_LABEL, ROLE_TO_AGENT } from "@/types";
import { api } from "@/net/api";
import { NexusManager } from "@/game/systems/NexusManager";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { EventBus } from "@/game/systems/EventBus";
import { confidenceTierTone, formatMoney, preTradeChecklist } from "./lib/derive";
import { AnimatedGrid, DataRow, Glass, Meter, StatusPill, TerminalLabel } from "./ui";

const CHOICE_TONE: Record<AnalystChoice, "green" | "red" | "amber"> = { buy: "green", sell: "red", wait: "amber" };

const ROLE_LABEL: Record<AnalystVote["role"], string> = {
  technical: "Technical Analyst",
  news: "News Analyst",
  macro: "Macro Analyst",
  risk: "Risk Manager",
  sentiment: "Sentiment Agent",
  execution: "Execution Agent",
};

/**
 * Feature 12 — the Executive Voting window. The player is TradeTown's CEO;
 * every trade candidate that crosses the confidence threshold arrives here
 * as a real TradeProposal (see backend/app/executive.py) instead of
 * executing automatically. Six analyst seats each cast a real, evidence-
 * backed vote; the CEO's own BUY/SELL/WAIT call is what actually happens —
 * "Approve"/"Reject" are convenience shortcuts for the desk's own
 * recommendation, not separate outcomes.
 */
export function ExecutiveVoting() {
  const { tradeProposals, executiveVotingOpen, executiveVotingProposalId, riskWarnings, paperPortfolio, riskLimits, currentScene } = useGameStore();
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [submitting, setSubmitting] = useState<AnalystChoice | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Same reasoning as TradeOutcomePopup's own MainMenuScene guard: the
  // WebSocket connects independent of the title screen, so never render
  // a full-screen popup over it.
  if (currentScene === "MainMenuScene" || !executiveVotingOpen) return null;

  const proposal: TradeProposal | undefined =
    tradeProposals.find((p) => p.id === executiveVotingProposalId) ?? tradeProposals[0];

  if (!proposal) return null;

  const close = () => {
    setExpandedAgent(null);
    setShowAnalysis(false);
    setError(null);
    EventBus.emit("ui:executiveVoting", { open: false });
  };

  const decide = async (choice: AnalystChoice) => {
    if (submitting) return;
    setSubmitting(choice);
    setError(null);
    try {
      const res = await api.submitCeoDecision(proposal.id, choice);
      NexusManager.setExecutiveDecisionResult(res.tradeProposals, res.ceoDecisions, res.decisions, res.paperPortfolio);
      setExpandedAgent(null);
      setShowAnalysis(false);
      const next = res.tradeProposals[0];
      if (next) {
        EventBus.emit("ui:executiveVoting", { open: true, proposalId: next.id });
      } else {
        EventBus.emit("ui:executiveVoting", { open: false });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(null);
    }
  };

  const confidence = proposal.confidenceEngine;
  const checklist = preTradeChecklist(proposal, riskWarnings, paperPortfolio, riskLimits);
  const unmetCount = checklist.filter((c) => !c.met).length;

  return (
    <div className="pointer-events-auto absolute inset-0 z-[55] flex items-center justify-center bg-cmd-bg/85 p-4 backdrop-blur-sm" data-testid="executive-voting">
      <div className="motion-safe:animate-cmd-overlay-in relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-sm border border-cmd-cyan/40 bg-cmd-panel shadow-cmd-cyan">
        <AnimatedGrid />
        <header className="sticky top-0 flex items-center justify-between border-b border-cmd-border bg-cmd-panel/95 px-4 py-3 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <span className="tracking-[0.2em] text-cmd-cyan">EXECUTIVE VOTING</span>
            <span className="font-cmdmono text-lg text-cmd-text">{proposal.symbol}</span>
            <StatusPill tone={CHOICE_TONE[proposal.overallRecommendation]}>DESK: {proposal.overallRecommendation.toUpperCase()}</StatusPill>
            <StatusPill tone={confidenceTierTone(confidence.tier)}>
              {CONFIDENCE_TIER_LABEL[confidence.tier]} · {Math.round(confidence.score)}
            </StatusPill>
          </div>
          {tradeProposals.length > 1 && <span className="text-[9px] text-cmd-textDim">+{tradeProposals.length - 1} more pending</span>}
        </header>

        <div className="space-y-3 p-4">
          <Glass className="p-3">
            <TerminalLabel>Research Summary</TerminalLabel>
            <p className="text-cmd-text">{proposal.researchSummary}</p>
          </Glass>

          <Glass className="p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>Analyst Desk — {proposal.analystVotes.length} votes</TerminalLabel>
            </div>
            <div className="space-y-1.5">
              {proposal.analystVotes.map((vote) => {
                const agent = AGENT_PROFILES[ROLE_TO_AGENT[vote.role]];
                const key = vote.role;
                const expanded = expandedAgent === key;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setExpandedAgent(expanded ? null : key)}
                    className="w-full rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-left transition-colors hover:border-cmd-cyan/40"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="flex items-center gap-2">
                        <span className="text-cmd-text">{agent.name}</span>
                        <span className="text-[9px] text-cmd-textDim">{ROLE_LABEL[vote.role]}</span>
                      </span>
                      <StatusPill tone={CHOICE_TONE[vote.choice]}>{vote.choice.toUpperCase()}</StatusPill>
                    </div>
                    {expanded && (
                      <div className="mt-1.5 space-y-1 border-t border-cmd-border/50 pt-1.5 text-[9px]">
                        <div className="text-cmd-text">{vote.reasoning}</div>
                        {vote.evidence.length > 0 && (
                          <ul className="list-disc space-y-0.5 pl-3 text-cmd-textDim">
                            {vote.evidence.map((e, i) => (
                              <li key={i}>{e}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </Glass>

          <button
            type="button"
            onClick={() => setShowAnalysis(!showAnalysis)}
            className="w-full rounded-sm border border-cmd-border px-3 py-1.5 text-cmd-textDim transition-colors hover:border-cmd-purple/50 hover:text-cmd-purple"
          >
            {showAnalysis ? "HIDE FULL ANALYSIS ▲" : "REVIEW ANALYSIS ▼"}
          </button>

          {showAnalysis && (
            <div className="space-y-3">
              <Glass className="p-3">
                <TerminalLabel>Decision Confidence Engine</TerminalLabel>
                <div className="mb-1 flex items-center justify-between">
                  <span className="font-cmdmono text-xl text-cmd-text">
                    {Math.round(confidence.score)}/100 <span className="text-[11px] text-cmd-textDim">{CONFIDENCE_TIER_LABEL[confidence.tier]}</span>
                  </span>
                  <span className="text-[9px] text-cmd-textDim">Scores setup quality, not a guaranteed outcome.</span>
                </div>
                <Meter value={confidence.score} tone={confidence.score >= 70 ? "green" : confidence.score >= 45 ? "amber" : "red"} />
                <div className="mt-2 text-[9px] text-cmd-textDim">{confidence.summary}</div>
                <div className="mt-2 space-y-1">
                  {confidence.factors.map((f) => (
                    <div key={f.name} className="flex items-center justify-between gap-2 border-t border-cmd-border/40 pt-1 text-[9px]">
                      <span className="text-cmd-textDim">{f.name}</span>
                      <span className={f.score >= 60 ? "text-cmd-green" : f.score >= 40 ? "text-cmd-amber" : "text-cmd-red"}>{f.score.toFixed(0)}</span>
                    </div>
                  ))}
                </div>
              </Glass>

              <Glass className="p-3">
                <TerminalLabel>Risk Snapshot</TerminalLabel>
                <DataRow label="Confidence" value={`${Math.round(proposal.confidence)}%`} />
                <DataRow label="Position size" value={`${proposal.quantity.toFixed(2)} @ ${formatMoney(proposal.price)}`} />
                <DataRow label="Notional" value={formatMoney(proposal.quantity * proposal.price)} />
                <DataRow label="Open positions" value={`${paperPortfolio.positions.length}/${riskLimits.maxOpenPositions}`} />
                <div className="mt-1.5 text-[9px] text-cmd-textDim">{proposal.riskSummary}</div>
                <div className="mt-1.5 text-[9px] text-cmd-textDim">
                  Stop-loss / take-profit distance and reward-to-risk ratio aren&apos;t shown — TradeTown&apos;s paper broker doesn&apos;t place exit
                  orders yet, so there&apos;s no real number to report.
                </div>
              </Glass>

              <Glass className="p-3">
                <div className="mb-1.5 flex items-center justify-between">
                  <TerminalLabel>Pre-Trade Checklist</TerminalLabel>
                  {unmetCount > 0 && <StatusPill tone="amber">{unmetCount} UNMET</StatusPill>}
                </div>
                <div className="space-y-1">
                  {checklist.map((item) => (
                    <div key={item.label} className="flex items-start gap-2 text-[9px]">
                      <span className={item.met ? "text-cmd-green" : "text-cmd-amber"}>{item.met ? "✓" : "✗"}</span>
                      <div>
                        <div className={item.met ? "text-cmd-text" : "text-cmd-amber"}>{item.label}</div>
                        <div className="text-cmd-textDim">{item.detail}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </Glass>
            </div>
          )}

          {error && <div className="text-[9px] text-cmd-red">{error}</div>}

          <div className="grid grid-cols-3 gap-2">
            <ActionButton label="BUY" tone="green" disabled={submitting !== null} loading={submitting === "buy"} onClick={() => void decide("buy")} />
            <ActionButton label="SELL" tone="red" disabled={submitting !== null} loading={submitting === "sell"} onClick={() => void decide("sell")} />
            <ActionButton label="WAIT" tone="amber" disabled={submitting !== null} loading={submitting === "wait"} onClick={() => void decide("wait")} />
          </div>
          <div className="grid grid-cols-2 gap-2 text-[9px]">
            <button
              type="button"
              disabled={submitting !== null}
              onClick={() => void decide(proposal.overallRecommendation)}
              className="rounded-sm border border-cmd-border py-1.5 text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
            >
              APPROVE (follow desk: {proposal.overallRecommendation.toUpperCase()})
            </button>
            <button
              type="button"
              disabled={submitting !== null}
              onClick={() => void decide("wait")}
              className="rounded-sm border border-cmd-border py-1.5 text-cmd-textDim transition-colors hover:enabled:border-cmd-red/50 hover:enabled:text-cmd-red disabled:opacity-40"
            >
              REJECT (no trade)
            </button>
          </div>
          <button type="button" onClick={close} className="w-full py-1 text-[9px] text-cmd-textDim hover:text-cmd-text">
            Decide later — this proposal stays pending
          </button>
        </div>
      </div>
    </div>
  );
}

function ActionButton({
  label,
  tone,
  disabled,
  loading,
  onClick,
}: {
  label: string;
  tone: "green" | "red" | "amber";
  disabled: boolean;
  loading: boolean;
  onClick: () => void;
}) {
  const toneClass: Record<string, string> = {
    green: "border-cmd-green/50 text-cmd-green hover:enabled:bg-cmd-green/10",
    red: "border-cmd-red/50 text-cmd-red hover:enabled:bg-cmd-red/10",
    amber: "border-cmd-amber/50 text-cmd-amber hover:enabled:bg-cmd-amber/10",
  };
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`rounded-sm border py-2.5 font-cmdmono tracking-wide transition-all duration-150 disabled:opacity-40 hover:enabled:-translate-y-0.5 ${toneClass[tone]}`}
    >
      {loading ? "…" : label}
    </button>
  );
}
