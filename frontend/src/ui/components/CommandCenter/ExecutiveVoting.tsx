import { useEffect, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { AnalystChoice, AnalystVote, DebateTurn, GatekeeperVerdict, ScenarioResult, ScenarioType, TradeProposal, WhatIfSimulation } from "@/types";
import { CONFIDENCE_TIER_LABEL, ROLE_TO_AGENT } from "@/types";
import { api } from "@/net/api";
import { NexusManager } from "@/game/systems/NexusManager";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { EventBus } from "@/game/systems/EventBus";
import { confidenceTierTone, formatMoney, formatPct, preTradeChecklist } from "./lib/derive";
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

const STANCE_LABEL: Record<DebateTurn["stance"], string> = { opening: "OPENING", challenge: "CHALLENGES", support: "AGREES" };
const STANCE_TONE: Record<DebateTurn["stance"], "cyan" | "red" | "green"> = { opening: "cyan", challenge: "red", support: "green" };

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
  const { tradeProposals, executiveVotingOpen, executiveVotingProposalId, riskWarnings, paperPortfolio, riskLimits, currentScene, debates } = useGameStore();
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [showDebate, setShowDebate] = useState(false);
  const [showWhatIf, setShowWhatIf] = useState(false);
  const [whatIf, setWhatIf] = useState<WhatIfSimulation | null>(null);
  const [whatIfLoading, setWhatIfLoading] = useState(false);
  const [whatIfError, setWhatIfError] = useState<string | null>(null);
  const [expandedScenario, setExpandedScenario] = useState<ScenarioType | null>(null);
  const [submitting, setSubmitting] = useState<AnalystChoice | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // v0.7 Feature 20 — set only when the Trade Gatekeeper vetoes the CEO's
  // real BUY/SELL call; holds the proposals list the backend already
  // returned so acknowledging can advance to the next one without a
  // second round-trip.
  const [gatekeeperRejection, setGatekeeperRejection] = useState<{
    symbol: string;
    choice: AnalystChoice;
    verdict: GatekeeperVerdict;
    nextProposals: TradeProposal[];
  } | null>(null);

  const proposal: TradeProposal | undefined =
    tradeProposals.find((p) => p.id === executiveVotingProposalId) ?? tradeProposals[0];

  // v0.7 Feature 16 — fetches fresh (never cached/persisted — see
  // backend/app/whatif.py) every time the lab is opened for a given
  // symbol, so switching between pending proposals always shows that
  // proposal's own real simulation, not a stale one from the last symbol.
  useEffect(() => {
    if (!showWhatIf || !proposal) return;
    let cancelled = false;
    setWhatIfLoading(true);
    setWhatIfError(null);
    api
      .getWhatIfSimulation(proposal.symbol)
      .then((res) => {
        if (!cancelled) setWhatIf(res);
      })
      .catch((err) => {
        if (!cancelled) setWhatIfError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setWhatIfLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // Deliberately keyed on the symbol, not the whole proposal object
    // (which is re-derived fresh every render) — refetches exactly when
    // the lab opens or the active proposal's symbol actually changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showWhatIf, proposal?.symbol]);

  // Same reasoning as TradeOutcomeBanner's own MainMenuScene guard: the
  // WebSocket connects independent of the title screen, so never render
  // a full-screen popup over it. A pending gatekeeperRejection keeps this
  // window open even though its proposal has already been resolved and
  // removed from tradeProposals (see decide() below).
  if (currentScene === "MainMenuScene" || !executiveVotingOpen) return null;
  if (!gatekeeperRejection && !proposal) return null;

  const close = () => {
    setExpandedAgent(null);
    setShowAnalysis(false);
    setShowWhatIf(false);
    setExpandedScenario(null);
    setError(null);
    EventBus.emit("ui:executiveVoting", { open: false });
  };

  const advanceOrClose = (proposals: TradeProposal[]) => {
    const next = proposals[0];
    if (next) {
      EventBus.emit("ui:executiveVoting", { open: true, proposalId: next.id });
    } else {
      EventBus.emit("ui:executiveVoting", { open: false });
    }
  };

  const decide = async (choice: AnalystChoice) => {
    if (submitting || !proposal) return;
    setSubmitting(choice);
    setError(null);
    try {
      const res = await api.submitCeoDecision(proposal.id, choice);
      NexusManager.setExecutiveDecisionResult(res.tradeProposals, res.ceoDecisions, res.decisions, res.paperPortfolio, res.gatekeeperRejections);
      setExpandedAgent(null);
      setShowAnalysis(false);
      setShowWhatIf(false);
      setExpandedScenario(null);
      // v0.7 Feature 20 — the CEO's own buy/sell can still be vetoed by
      // the Trade Gatekeeper; surface that instead of silently advancing
      // to the next proposal (per the brief's transparency requirement).
      const resolvedDecision = res.decisions.find((d) => d.id === `decision-${proposal.id}`);
      if (resolvedDecision?.gatekeeperVerdict && !resolvedDecision.gatekeeperVerdict.approved) {
        setGatekeeperRejection({ symbol: proposal.symbol, choice, verdict: resolvedDecision.gatekeeperVerdict, nextProposals: res.tradeProposals });
        return;
      }
      advanceOrClose(res.tradeProposals);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(null);
    }
  };

  const acknowledgeRejection = () => {
    if (!gatekeeperRejection) return;
    const nextProposals = gatekeeperRejection.nextProposals;
    setGatekeeperRejection(null);
    advanceOrClose(nextProposals);
  };

  if (gatekeeperRejection) {
    return <GatekeeperRejectionScreen rejection={gatekeeperRejection} onAcknowledge={acknowledgeRejection} />;
  }
  if (!proposal) return null;

  const confidence = proposal.confidenceEngine;
  const checklist = preTradeChecklist(proposal, riskWarnings, paperPortfolio, riskLimits);
  const unmetCount = checklist.filter((c) => !c.met).length;
  // v0.7 Feature 17 — the most recent debate over this proposal; nexus.py
  // generates one the moment the proposal itself is created, and
  // "request another debate" below appends a fresh one rather than
  // replacing it, so the newest is always the live transcript.
  const debate = [...debates].reverse().find((d) => d.proposalId === proposal.id);

  const requestAnotherDebate = async () => {
    if (regenerating) return;
    setRegenerating(true);
    setError(null);
    try {
      const res = await api.regenerateDebate(proposal.id);
      NexusManager.setDebates(res.debates);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRegenerating(false);
    }
  };

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
            onClick={() => setShowDebate(!showDebate)}
            className="w-full rounded-sm border border-cmd-border px-3 py-1.5 text-cmd-textDim transition-colors hover:border-cmd-cyan/50 hover:text-cmd-cyan"
          >
            {showDebate ? "HIDE DEBATE ROOM ▲" : "OPEN DEBATE ROOM ▼"}
          </button>

          {showDebate && (
            <Glass className="p-3">
              <div className="mb-1.5 flex items-center justify-between">
                <TerminalLabel>Investment Committee Debate</TerminalLabel>
                <button
                  type="button"
                  disabled={regenerating}
                  onClick={() => void requestAnotherDebate()}
                  className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
                >
                  {regenerating ? "…" : "Request Another Debate"}
                </button>
              </div>
              {!debate ? (
                <div className="text-[9px] text-cmd-textDim">No debate on record for this proposal yet.</div>
              ) : (
                <>
                  <div className="space-y-1.5">
                    {debate.turns.map((turn, i) => {
                      const speaker = AGENT_PROFILES[ROLE_TO_AGENT[turn.role]];
                      const respondingTo = turn.respondingTo ? AGENT_PROFILES[turn.respondingTo].name : null;
                      return (
                        <div key={i} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2 text-[9px]">
                          <div className="mb-1 flex items-center justify-between gap-2">
                            <span className="flex items-center gap-1.5">
                              <span className="text-cmd-text">{speaker.name}</span>
                              <span className="text-cmd-textDim">{ROLE_LABEL[turn.role]}</span>
                            </span>
                            <StatusPill tone={STANCE_TONE[turn.stance]}>
                              {STANCE_LABEL[turn.stance]}
                              {respondingTo ? ` ${respondingTo.toUpperCase()}` : ""}
                            </StatusPill>
                          </div>
                          <div className="text-cmd-textDim">{turn.text}</div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="mt-2 border-t border-cmd-border/40 pt-2 text-[9px] text-cmd-text">{debate.finalSummary}</div>
                  <div className="mt-1.5 text-[9px] text-cmd-textDim">
                    Click any seat in the Analyst Desk above to question that agent individually — its full reasoning and evidence are already there.
                  </div>
                </>
              )}
            </Glass>
          )}

          <button
            type="button"
            onClick={() => setShowWhatIf(!showWhatIf)}
            className="w-full rounded-sm border border-cmd-border px-3 py-1.5 text-cmd-textDim transition-colors hover:border-cmd-cyan/50 hover:text-cmd-cyan"
          >
            {showWhatIf ? "HIDE WHAT-IF SIMULATION LAB ▲" : "OPEN WHAT-IF SIMULATION LAB ▼"}
          </button>

          {showWhatIf && (
            <Glass className="p-3">
              <div className="mb-1.5 flex items-center justify-between">
                <TerminalLabel>Scenario Stress Test — {proposal.symbol}</TerminalLabel>
                <span className="text-[9px] text-cmd-textDim">Resilience test, not a prediction.</span>
              </div>
              {whatIfLoading && <div className="text-[9px] text-cmd-textDim">Simulating scenarios…</div>}
              {whatIfError && <div className="text-[9px] text-cmd-red">{whatIfError}</div>}
              {!whatIfLoading && whatIf && whatIf.symbol === proposal.symbol && (
                <WhatIfPanel whatIf={whatIf} expandedScenario={expandedScenario} onToggleScenario={(s) => setExpandedScenario(expandedScenario === s ? null : s)} />
              )}
            </Glass>
          )}

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

/**
 * v0.7 Feature 20 — shown in place of the normal voting panel whenever the
 * Trade Gatekeeper vetoes the CEO's real BUY/SELL call. Per the brief's
 * transparency requirement: which rule failed, why it matters (each
 * check's own real detail text — see backend/app/gatekeeper.py), and what
 * this rejection is tracked against (the self-evaluation described below).
 */
function GatekeeperRejectionScreen({
  rejection,
  onAcknowledge,
}: {
  rejection: { symbol: string; choice: AnalystChoice; verdict: GatekeeperVerdict };
  onAcknowledge: () => void;
}) {
  const failedChecks = rejection.verdict.checks.filter((c) => !c.passed);
  return (
    <div className="pointer-events-auto absolute inset-0 z-[55] flex items-center justify-center bg-cmd-bg/85 p-4 backdrop-blur-sm" data-testid="gatekeeper-rejection">
      <div className="motion-safe:animate-cmd-overlay-in relative max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-sm border border-cmd-red/50 bg-cmd-panel shadow-cmd-red">
        <AnimatedGrid />
        <header className="sticky top-0 flex items-center justify-between border-b border-cmd-border bg-cmd-panel/95 px-4 py-3 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <StatusPill tone="red">REJECTED BY GATEKEEPER</StatusPill>
            <span className="font-cmdmono text-lg text-cmd-text">{rejection.symbol}</span>
          </div>
        </header>

        <div className="space-y-3 p-4">
          <Glass className="p-3">
            <TerminalLabel>Verdict</TerminalLabel>
            <p className="text-cmd-text">
              The CEO chose <span className="text-cmd-amber">{rejection.choice.toUpperCase()}</span> on {rejection.symbol}, but the firm&apos;s
              final-approval layer blocked it before execution — no order was placed. &quot;The best trade is often the one you don&apos;t
              take.&quot;
            </p>
            <p className="mt-2 text-cmd-textDim">{rejection.verdict.summary}</p>
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Failed Checks — {failedChecks.length}</TerminalLabel>
            <div className="space-y-1.5">
              {failedChecks.map((c) => (
                <div key={c.id} className="rounded-sm border border-cmd-red/30 bg-cmd-bg/40 p-2 text-[9px]">
                  <div className="mb-1 flex items-center gap-2">
                    <StatusPill tone="red">FAILED</StatusPill>
                    <span className="text-cmd-text">{c.label}</span>
                  </div>
                  <div className="text-cmd-textDim">{c.detail}</div>
                </div>
              ))}
            </div>
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Full Checklist</TerminalLabel>
            <div className="space-y-1">
              {rejection.verdict.checks.map((c) => (
                <div key={c.id} className="flex items-start gap-2 text-[9px]">
                  <span className={c.passed ? "text-cmd-green" : "text-cmd-red"}>{c.passed ? "✓" : "✗"}</span>
                  <div>
                    <div className={c.passed ? "text-cmd-text" : "text-cmd-red"}>{c.label}</div>
                    <div className="text-cmd-textDim">{c.detail}</div>
                  </div>
                </div>
              ))}
            </div>
          </Glass>

          <div className="text-[9px] text-cmd-textDim">
            This rejection is tracked for the Gatekeeper&apos;s own self-evaluation (see the Executive tab&apos;s Trade Gatekeeper card) — once
            enough simulated time passes, TradeTown checks {rejection.symbol}&apos;s real subsequent price move to see whether this trade would
            actually have worked. Nothing here changes the firm&apos;s rules automatically; that stays a manual review.
          </div>

          <button
            type="button"
            onClick={onAcknowledge}
            className="w-full rounded-sm border border-cmd-red/50 py-2.5 font-cmdmono tracking-wide text-cmd-red transition-all duration-150 hover:bg-cmd-red/10"
          >
            ACKNOWLEDGE
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

/** A shared reward-range scale (min/max % across every scenario, padded
 * 10%) so all 12 bars in the lab are directly visually comparable rather
 * than each auto-scaling to its own range. */
function scenarioScale(whatIf: WhatIfSimulation): { min: number; max: number } {
  const all = [...whatIf.scenarios, whatIf.baseline];
  const min = Math.min(0, ...all.map((s) => s.rewardRangeLowPct));
  const max = Math.max(0, ...all.map((s) => s.rewardRangeHighPct));
  const pad = Math.max((max - min) * 0.1, 0.5);
  return { min: min - pad, max: max + pad };
}

function RewardRangeBar({ scenario, scale }: { scenario: ScenarioResult; scale: { min: number; max: number } }) {
  const span = scale.max - scale.min || 1;
  const toPct = (v: number) => ((v - scale.min) / span) * 100;
  const lowPct = toPct(scenario.rewardRangeLowPct);
  const highPct = toPct(scenario.rewardRangeHighPct);
  return (
    <div className="relative h-3 w-full rounded-sm bg-cmd-bg/60">
      <div className="absolute inset-y-0 w-px bg-cmd-border" style={{ left: `${toPct(0)}%` }} />
      <div
        className={`absolute inset-y-0.5 rounded-sm ${scenario.mostLikelyPct >= 0 ? "bg-cmd-green/50" : "bg-cmd-red/50"}`}
        style={{ left: `${Math.min(lowPct, highPct)}%`, width: `${Math.max(1, Math.abs(highPct - lowPct))}%` }}
      />
      <div className="absolute inset-y-0 w-0.5 bg-cmd-cyan" style={{ left: `${toPct(scenario.mostLikelyPct)}%` }} />
    </div>
  );
}

/**
 * v0.7 Feature 16 — the What-If Simulation Lab's results. Every number is
 * a real bootstrap-simulated outcome (see backend/app/whatif.py); best/
 * worst case are whichever real scenario produced the highest/lowest
 * reward-range edge, "most likely" is the unbiased baseline reading —
 * never a fabricated cross-scenario probability (see WhatIfSimulation's
 * own doc comment in types.ts for why).
 */
function WhatIfPanel({
  whatIf,
  expandedScenario,
  onToggleScenario,
}: {
  whatIf: WhatIfSimulation;
  expandedScenario: ScenarioType | null;
  onToggleScenario: (s: ScenarioType) => void;
}) {
  const scale = scenarioScale(whatIf);
  const bestCase = whatIf.scenarios.find((s) => s.scenarioType === whatIf.bestCaseScenario);
  const worstCase = whatIf.scenarios.find((s) => s.scenarioType === whatIf.worstCaseScenario);

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-3 gap-2 text-[9px]">
        <div className="rounded-sm border border-cmd-green/30 bg-cmd-bg/40 p-2">
          <div className="text-cmd-textDim">BEST CASE</div>
          <div className="truncate text-cmd-green">{bestCase?.label}</div>
          <div className="text-cmd-text">up to {bestCase ? formatPct(bestCase.rewardRangeHighPct) : "—"}</div>
        </div>
        <div className="rounded-sm border border-cmd-red/30 bg-cmd-bg/40 p-2">
          <div className="text-cmd-textDim">WORST CASE</div>
          <div className="truncate text-cmd-red">{worstCase?.label}</div>
          <div className="text-cmd-text">down to {worstCase ? formatPct(worstCase.rewardRangeLowPct) : "—"}</div>
        </div>
        <div className="rounded-sm border border-cmd-cyan/30 bg-cmd-bg/40 p-2">
          <div className="text-cmd-textDim">MOST LIKELY (unbiased)</div>
          <div className="text-cmd-cyan">{formatPct(whatIf.baseline.mostLikelyPct)}</div>
          <div className="text-cmd-text">{whatIf.baseline.probabilityOfProfitPct.toFixed(0)}% win rate</div>
        </div>
      </div>

      <div className="flex items-center gap-2 px-2 text-[8px] uppercase tracking-wide text-cmd-textDim">
        <span className="w-32 shrink-0">Scenario</span>
        <span className="flex-1">Reward range ({whatIf.holdBars}-bar hold)</span>
        <span className="w-14 shrink-0 text-right">Likely</span>
        <span className="w-10 shrink-0 text-right">Win%</span>
      </div>

      <div className="space-y-1">
        {whatIf.scenarios.map((s) => {
          const expanded = expandedScenario === s.scenarioType;
          return (
            <button
              key={s.scenarioType}
              type="button"
              onClick={() => onToggleScenario(s.scenarioType)}
              className="w-full rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-left transition-colors hover:border-cmd-cyan/40"
            >
              <div className="flex items-center gap-2 text-[9px]">
                <span className="w-32 shrink-0 truncate text-cmd-text">{s.label}</span>
                <span className="flex-1">
                  <RewardRangeBar scenario={s} scale={scale} />
                </span>
                <span className={`w-14 shrink-0 text-right ${s.mostLikelyPct >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{formatPct(s.mostLikelyPct)}</span>
                <span className="w-10 shrink-0 text-right text-cmd-textDim">{s.probabilityOfProfitPct.toFixed(0)}%</span>
              </div>
              {expanded && (
                <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 border-t border-cmd-border/50 pt-1.5 text-[9px] text-cmd-textDim">
                  <div>
                    Reward range: {formatPct(s.rewardRangeLowPct)} to {formatPct(s.rewardRangeHighPct)}
                  </div>
                  <div>Typical drawdown: {formatPct(s.typicalDrawdownPct)}</div>
                  <div>Max expected risk: {formatPct(s.maxRiskPct)}</div>
                  <div>Probability of profit: {s.probabilityOfProfitPct.toFixed(0)}%</div>
                  <div className="col-span-2 text-cmd-amber">Invalidated if: {s.invalidation}</div>
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
