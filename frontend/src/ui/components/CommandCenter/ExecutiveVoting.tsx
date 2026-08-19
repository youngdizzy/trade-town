import { useEffect, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type {
  AnalystChoice,
  AnalystVote,
  ChallengeSeverity,
  DebateTurn,
  ExecutiveAccuracyScore,
  ExecutiveAction,
  ExecutiveDepartmentRole,
  ExecutiveRecommendation,
  GatekeeperVerdict,
  HoldReason,
  ScenarioResult,
  ScenarioType,
  TradeProposal,
  WeightedExecutiveRecommendation,
  WeightProfile,
  WhatIfSimulation,
} from "@/types";
import { CONFIDENCE_TIER_LABEL, EXECUTIVE_ACTION_LABEL, EXECUTIVE_DEPARTMENT_LABEL, EXECUTIVE_STANCE_LABEL, ROLE_TO_AGENT, WEIGHT_PROFILE_LABEL } from "@/types";
import { api } from "@/net/api";
import { NexusManager } from "@/game/systems/NexusManager";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { EventBus } from "@/game/systems/EventBus";
import { SettingsManager } from "@/game/systems/SettingsManager";
import { confidenceTierTone, executiveActionTone, executiveStanceTone, formatMoney, formatPct, preTradeChecklist } from "./lib/derive";
import { AnimatedGrid, DataRow, Glass, Meter, StatusPill, TerminalLabel } from "./ui";

const CHOICE_TONE: Record<AnalystChoice, "green" | "red" | "amber"> = { buy: "green", sell: "red", wait: "amber" };

// Design Bible Chapter 70 Part 2 — maps the Executive Intelligence
// Network's 6-value ExecutiveAction onto the real 3-way AnalystChoice a
// "Delegate to the Executive Board" click actually submits.
// trade_normally/reduce_risk both mean "the network is fine with a
// trade happening" — direction still comes from the analyst desk's own
// overallRecommendation (the network never invents a buy/sell direction
// of its own); every other action means "don't force a trade."
function delegatedChoice(action: ExecutiveAction, deskRecommendation: AnalystChoice): AnalystChoice {
  if (action === "trade_normally" || action === "reduce_risk") return deskRecommendation;
  return "wait";
}

// v0.7 Feature 40.5 — mirrors backend/app/executive.py's MAX_PROPOSAL_HOLDS.
const MAX_PROPOSAL_HOLDS = 2;

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

// v0.7 Feature 41 — the Intelligent Devil's Advocate System.
const SEVERITY_LABEL: Record<ChallengeSeverity, string> = { none_found: "NO WEAKNESSES FOUND", minor: "MINOR WEAKNESSES", major: "MAJOR WEAKNESSES" };
const SEVERITY_TONE: Record<ChallengeSeverity, "green" | "amber" | "red"> = { none_found: "green", minor: "amber", major: "red" };

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
  const {
    tradeProposals,
    executiveVotingOpen,
    executiveVotingProposalId,
    riskWarnings,
    paperPortfolio,
    riskLimits,
    riskBudgetStatus,
    currentScene,
    debates,
    challengeReports,
    constitution,
    settings,
  } = useGameStore();
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [showDebate, setShowDebate] = useState(false);
  const [showChallenge, setShowChallenge] = useState(false);
  const [showWhatIf, setShowWhatIf] = useState(false);
  const [whatIf, setWhatIf] = useState<WhatIfSimulation | null>(null);
  const [whatIfLoading, setWhatIfLoading] = useState(false);
  const [whatIfError, setWhatIfError] = useState<string | null>(null);
  const [showExecIntel, setShowExecIntel] = useState(false);
  const [execIntel, setExecIntel] = useState<ExecutiveRecommendation | null>(null);
  const [execIntelLoading, setExecIntelLoading] = useState(false);
  const [execIntelError, setExecIntelError] = useState<string | null>(null);
  const [expandedScenario, setExpandedScenario] = useState<ScenarioType | null>(null);
  const [submitting, setSubmitting] = useState<AnalystChoice | null>(null);
  const [holding, setHolding] = useState<HoldReason | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [regeneratingChallenge, setRegeneratingChallenge] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Design Bible Chapter 70 Part 2 — "Modify" as a real CEO decision
  // action (downsize-only, stays pending).
  const [modifyQuantity, setModifyQuantity] = useState("");
  const [modifying, setModifying] = useState(false);
  // Design Bible Chapter 70 Part 2 — "Delegate to the Executive Board":
  // asks the Executive Intelligence Network's own recommendation to
  // decide, mapped client-side (see delegatedChoice below) then
  // submitted through the same /executive/decide endpoint, tagged
  // resolved_by="delegated".
  const [delegating, setDelegating] = useState(false);
  // Design Bible Chapter 70 Part 2 — Executive Accuracy Score, real and
  // company-wide (not proposal-scoped), fetched fresh on open.
  const [showAccuracy, setShowAccuracy] = useState(false);
  const [accuracy, setAccuracy] = useState<ExecutiveAccuracyScore[] | null>(null);
  const [accuracyLoading, setAccuracyLoading] = useState(false);
  const [accuracyError, setAccuracyError] = useState<string | null>(null);
  // Design Bible Chapter 70 Part 3 — Weighted Executive Decision Engine.
  // previewProfile === null means "use the CEO's persisted active
  // profile"; picking a different profile in the panel below previews
  // it live without persisting — only "Set as Active Profile" does that.
  const [showWeighted, setShowWeighted] = useState(false);
  const [weighted, setWeighted] = useState<WeightedExecutiveRecommendation | null>(null);
  const [weightedLoading, setWeightedLoading] = useState(false);
  const [weightedError, setWeightedError] = useState<string | null>(null);
  const [previewProfile, setPreviewProfile] = useState<WeightProfile | null>(null);
  const [customWeightDraft, setCustomWeightDraft] = useState<Partial<Record<ExecutiveDepartmentRole, number>>>({});
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

  // v0.7 Feature 50 (Part 1) — the Executive Intelligence Network's
  // recommendation is computed fresh (never persisted — see
  // backend/app/routers/executive.py) every time this section is opened
  // for a given proposal, same reasoning as the What-If lab above.
  useEffect(() => {
    if (!showExecIntel || !proposal) return;
    let cancelled = false;
    setExecIntelLoading(true);
    setExecIntelError(null);
    api
      .getExecutiveIntelligence(proposal.id)
      .then((res) => {
        if (!cancelled) setExecIntel(res);
      })
      .catch((err) => {
        if (!cancelled) setExecIntelError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setExecIntelLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showExecIntel, proposal?.id]);

  // Design Bible Chapter 70 Part 2 — Executive Accuracy Score, fetched
  // fresh whenever the section is opened; company-wide, so not keyed on
  // the active proposal the way the two effects above are.
  useEffect(() => {
    if (!showAccuracy) return;
    let cancelled = false;
    setAccuracyLoading(true);
    setAccuracyError(null);
    api
      .getExecutiveAccuracy()
      .then((res) => {
        if (!cancelled) setAccuracy(res);
      })
      .catch((err) => {
        if (!cancelled) setAccuracyError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setAccuracyLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [showAccuracy]);

  // Design Bible Chapter 70 Part 3 — Weighted Executive Decision Engine,
  // fetched fresh (same convention as the two effects above) whenever
  // the section is open, the proposal changes, or the CEO previews a
  // different profile.
  useEffect(() => {
    if (!showWeighted || !proposal) return;
    let cancelled = false;
    setWeightedLoading(true);
    setWeightedError(null);
    api
      .getWeightedDecision(proposal.id, previewProfile ?? undefined)
      .then((res) => {
        if (!cancelled) setWeighted(res);
      })
      .catch((err) => {
        if (!cancelled) setWeightedError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setWeightedLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showWeighted, proposal?.id, previewProfile]);

  // Same reasoning as CyberNotifications' own MainMenuScene guard: the
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
    setShowExecIntel(false);
    setShowWeighted(false);
    setPreviewProfile(null);
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

  const decide = async (choice: AnalystChoice, delegated = false) => {
    if (submitting || !proposal) return;
    setSubmitting(choice);
    setError(null);
    try {
      const res = await api.submitCeoDecision(proposal.id, choice, delegated);
      NexusManager.setExecutiveDecisionResult(res.tradeProposals, res.ceoDecisions, res.decisions, res.paperPortfolio, res.gatekeeperRejections);
      setExpandedAgent(null);
      setShowAnalysis(false);
      setShowWhatIf(false);
      setShowExecIntel(false);
      setShowWeighted(false);
      setPreviewProfile(null);
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

  // Design Bible Chapter 70 Part 2 — "Delegate to the Executive Board."
  // Fetches the network's real recommendation (reusing the already-open
  // panel's data if it's for this proposal, otherwise a fresh fetch),
  // maps it to a real buy/sell/wait, then submits exactly like decide()
  // above but tagged delegated=true.
  const delegate = async () => {
    if (submitting || holding || delegating || !proposal) return;
    setDelegating(true);
    setError(null);
    try {
      const recommendation = execIntel && execIntel.proposalId === proposal.id ? execIntel : await api.getExecutiveIntelligence(proposal.id);
      const choice = delegatedChoice(recommendation.action, proposal.overallRecommendation);
      const res = await api.submitCeoDecision(proposal.id, choice, true);
      NexusManager.setExecutiveDecisionResult(res.tradeProposals, res.ceoDecisions, res.decisions, res.paperPortfolio, res.gatekeeperRejections);
      setExpandedAgent(null);
      setShowAnalysis(false);
      setShowWhatIf(false);
      setShowExecIntel(false);
      setShowWeighted(false);
      setPreviewProfile(null);
      setExpandedScenario(null);
      const resolvedDecision = res.decisions.find((d) => d.id === `decision-${proposal.id}`);
      if (resolvedDecision?.gatekeeperVerdict && !resolvedDecision.gatekeeperVerdict.approved) {
        setGatekeeperRejection({ symbol: proposal.symbol, choice, verdict: resolvedDecision.gatekeeperVerdict, nextProposals: res.tradeProposals });
        return;
      }
      advanceOrClose(res.tradeProposals);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setDelegating(false);
    }
  };

  // Design Bible Chapter 70 Part 2 — "Modify" as a real CEO decision
  // action. Downsize-only (see backend/app/executive.py's
  // modify_proposal()) — the proposal stays pending, so there's no
  // advanceOrClose() call here, same as hold() below.
  const modify = async () => {
    if (modifying || submitting || holding || !proposal) return;
    const quantity = Number(modifyQuantity);
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setError("Enter a valid resized quantity greater than 0.");
      return;
    }
    setModifying(true);
    setError(null);
    try {
      const res = await api.modifyProposal(proposal.id, quantity);
      NexusManager.setTradeProposals(res.tradeProposals);
      setModifyQuantity("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setModifying(false);
    }
  };

  // v0.7 Feature 40.5 — "Request More Research" / "Delay Decision". Unlike
  // decide(), this never resolves the proposal (see backend/app/executive.py's
  // hold_proposal()) — it stays pending and open, so there's no
  // advanceOrClose() call here.
  const hold = async (reason: HoldReason) => {
    if (holding || submitting || !proposal) return;
    setHolding(reason);
    setError(null);
    try {
      const res = await api.holdProposal(proposal.id, reason);
      NexusManager.setTradeProposals(res.tradeProposals);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setHolding(null);
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

  // v0.7 Feature 41 — the most recent Devil's Advocate Challenge Report
  // over this proposal; nexus.py generates one the moment the proposal
  // itself is created, and "request another review" below appends a
  // fresh one (with a newly rotated assignee) rather than replacing it.
  const challengeReport = [...challengeReports].reverse().find((c) => c.proposalId === proposal.id);

  const requestAnotherReview = async () => {
    if (regeneratingChallenge) return;
    setRegeneratingChallenge(true);
    setError(null);
    try {
      const res = await api.regenerateChallengeReport(proposal.id);
      NexusManager.setChallengeReports(res.challengeReports, res.innovationState);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRegeneratingChallenge(false);
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
            onClick={() => setShowChallenge(!showChallenge)}
            className="w-full rounded-sm border border-cmd-border px-3 py-1.5 text-cmd-textDim transition-colors hover:border-cmd-amber/50 hover:text-cmd-amber"
          >
            {showChallenge ? "HIDE DEVIL'S ADVOCATE REVIEW ▲" : "OPEN DEVIL'S ADVOCATE REVIEW ▼"}
          </button>

          {showChallenge && (
            <Glass className="p-3">
              <div className="mb-1.5 flex items-center justify-between">
                <TerminalLabel>Challenge Report — {proposal.symbol}</TerminalLabel>
                <button
                  type="button"
                  disabled={regeneratingChallenge}
                  onClick={() => void requestAnotherReview()}
                  className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] text-cmd-textDim transition-colors hover:enabled:border-cmd-amber/50 hover:enabled:text-cmd-amber disabled:opacity-40"
                >
                  {regeneratingChallenge ? "…" : "Request Another Review"}
                </button>
              </div>
              {!challengeReport ? (
                <div className="text-[9px] text-cmd-textDim">No Devil&apos;s Advocate review on record for this proposal yet.</div>
              ) : (
                <>
                  <div className="mb-1.5 flex items-center gap-2 text-[9px]">
                    <span data-testid="challenge-report-assignee" className="text-cmd-text">
                      {AGENT_PROFILES[challengeReport.assignedAgent].name}
                    </span>
                    <span className="text-cmd-textDim">assigned Devil&apos;s Advocate</span>
                    <StatusPill tone={SEVERITY_TONE[challengeReport.severity]}>{SEVERITY_LABEL[challengeReport.severity]}</StatusPill>
                  </div>
                  <div className="space-y-2 text-[9px]">
                    <div>
                      <div className="text-cmd-textDim">Bull Case</div>
                      <div className="text-cmd-text">{challengeReport.bullCase}</div>
                    </div>
                    <div>
                      <div className="text-cmd-textDim">Bear Case</div>
                      <div className="text-cmd-text">{challengeReport.bearCase}</div>
                    </div>
                    {challengeReport.hiddenRisks.length > 0 && (
                      <div>
                        <div className="text-cmd-amber">Hidden Risks</div>
                        <ul className="list-disc space-y-0.5 pl-3 text-cmd-textDim">
                          {challengeReport.hiddenRisks.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {challengeReport.weakAssumptions.length > 0 && (
                      <div>
                        <div className="text-cmd-amber">Weak Assumptions</div>
                        <ul className="list-disc space-y-0.5 pl-3 text-cmd-textDim">
                          {challengeReport.weakAssumptions.map((a, i) => (
                            <li key={i}>{a}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {challengeReport.missingEvidence.length > 0 && (
                      <div>
                        <div className="text-cmd-amber">Missing Evidence</div>
                        <ul className="list-disc space-y-0.5 pl-3 text-cmd-textDim">
                          {challengeReport.missingEvidence.map((m, i) => (
                            <li key={i}>{m}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {challengeReport.historicalComparisons.length > 0 && (
                      <div>
                        <div className="text-cmd-textDim">Historical Comparisons</div>
                        <ul className="list-disc space-y-0.5 pl-3 text-cmd-textDim">
                          {challengeReport.historicalComparisons.map((h, i) => (
                            <li key={i}>{h}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <div>
                      <div className="text-cmd-textDim">Worst Case Scenario</div>
                      <div className="text-cmd-text">{challengeReport.worstCaseScenario}</div>
                    </div>
                    {challengeReport.suggestedImprovements.length > 0 && (
                      <div>
                        <div className="text-cmd-cyan">Suggested Improvements</div>
                        <ul className="list-disc space-y-0.5 pl-3 text-cmd-textDim">
                          {challengeReport.suggestedImprovements.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                  {challengeReport.citedArticleIds.length > 0 && (
                    <div data-testid="challenge-cited-articles" className="mt-2 border-t border-cmd-border/40 pt-2 text-[9px]">
                      <div className="text-cmd-cyan">Constitution Citations</div>
                      <ul className="list-disc space-y-0.5 pl-3 text-cmd-textDim">
                        {challengeReport.citedArticleIds.map((articleId) => {
                          const article = constitution.articles.find((a) => a.id === articleId);
                          return <li key={articleId}>{article ? `Article ${article.id} — ${article.title}` : `Article ${articleId}`}</li>;
                        })}
                      </ul>
                    </div>
                  )}
                  <div className="mt-2 border-t border-cmd-border/40 pt-2 text-[9px] text-cmd-text">{challengeReport.finalRecommendation}</div>
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
            onClick={() => setShowExecIntel(!showExecIntel)}
            className="w-full rounded-sm border border-cmd-border px-3 py-1.5 text-cmd-textDim transition-colors hover:border-cmd-purple/50 hover:text-cmd-purple"
          >
            {showExecIntel ? "HIDE EXECUTIVE INTELLIGENCE NETWORK ▲" : "OPEN EXECUTIVE INTELLIGENCE NETWORK ▼"}
          </button>

          {showExecIntel && (
            <Glass className="p-3">
              <div className="mb-1.5 flex items-center justify-between">
                <TerminalLabel>Executive Recommendation — {proposal.symbol}</TerminalLabel>
                <span className="text-[9px] text-cmd-textDim">Synthesized live, not a 9th vote.</span>
              </div>
              {execIntelLoading && <div className="text-[9px] text-cmd-textDim">Convening the network…</div>}
              {execIntelError && <div className="text-[9px] text-cmd-red">{execIntelError}</div>}
              {!execIntelLoading && execIntel && execIntel.proposalId === proposal.id && <ExecutiveIntelligencePanel recommendation={execIntel} />}
            </Glass>
          )}

          <button
            type="button"
            onClick={() => setShowAccuracy(!showAccuracy)}
            className="w-full rounded-sm border border-cmd-border px-3 py-1.5 text-cmd-textDim transition-colors hover:border-cmd-purple/50 hover:text-cmd-purple"
          >
            {showAccuracy ? "HIDE EXECUTIVE ACCURACY SCORE ▲" : "OPEN EXECUTIVE ACCURACY SCORE ▼"}
          </button>

          {showAccuracy && (
            <Glass className="p-3">
              <div className="mb-1.5 flex items-center justify-between">
                <TerminalLabel>Executive Accuracy Score</TerminalLabel>
                <span className="text-[9px] text-cmd-textDim">Company-wide, not just {proposal.symbol}.</span>
              </div>
              {accuracyLoading && <div className="text-[9px] text-cmd-textDim">Reviewing closed trades…</div>}
              {accuracyError && <div className="text-[9px] text-cmd-red">{accuracyError}</div>}
              {!accuracyLoading && accuracy && <ExecutiveAccuracyPanel scores={accuracy} />}
            </Glass>
          )}

          <button
            type="button"
            onClick={() => setShowWeighted(!showWeighted)}
            className="w-full rounded-sm border border-cmd-border px-3 py-1.5 text-cmd-textDim transition-colors hover:border-cmd-purple/50 hover:text-cmd-purple"
          >
            {showWeighted ? "HIDE WEIGHTED EXECUTIVE DECISION ENGINE ▲" : "OPEN WEIGHTED EXECUTIVE DECISION ENGINE ▼"}
          </button>

          {showWeighted && (
            <Glass className="p-3">
              <div className="mb-1.5 flex items-center justify-between">
                <TerminalLabel>Weighted Executive Decision Engine — {proposal.symbol}</TerminalLabel>
                <span className="text-[9px] text-cmd-textDim">Advisory only — never overrides the Gatekeeper.</span>
              </div>
              <div className="mb-2 flex items-center gap-2 text-[9px]">
                <span className="text-cmd-textDim">Weight Profile:</span>
                <select
                  value={previewProfile ?? settings.activeWeightProfile}
                  onChange={(e) => setPreviewProfile(e.target.value as WeightProfile)}
                  className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-0.5 text-cmd-text"
                >
                  {(Object.keys(WEIGHT_PROFILE_LABEL) as WeightProfile[]).map((p) => (
                    <option key={p} value={p}>
                      {WEIGHT_PROFILE_LABEL[p]}
                    </option>
                  ))}
                </select>
                {previewProfile && previewProfile !== settings.activeWeightProfile && (
                  <button
                    type="button"
                    onClick={() => {
                      SettingsManager.update({ activeWeightProfile: previewProfile });
                      setPreviewProfile(null);
                    }}
                    className="rounded-sm border border-cmd-cyan/50 px-1.5 py-0.5 text-cmd-cyan transition-colors hover:bg-cmd-cyan/10"
                  >
                    SET AS ACTIVE PROFILE
                  </button>
                )}
              </div>

              {(previewProfile ?? settings.activeWeightProfile) === "custom" && (
                <div className="mb-2 rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2">
                  <div className="mb-1.5 text-[9px] text-cmd-textDim">
                    Custom CEO Profile — set each department&apos;s multiplier (1.00 = neutral). Saved weights apply on the next settings sync,
                    same as every other CEO preference.
                  </div>
                  <div className="grid grid-cols-3 gap-1.5">
                    {(Object.keys(EXECUTIVE_DEPARTMENT_LABEL) as ExecutiveDepartmentRole[]).map((role) => (
                      <label key={role} className="flex items-center justify-between gap-1 text-[8px] text-cmd-textDim">
                        {EXECUTIVE_DEPARTMENT_LABEL[role]}
                        <input
                          type="number"
                          min={0}
                          step={0.1}
                          value={customWeightDraft[role] ?? settings.customDepartmentWeights[role] ?? 1.0}
                          onChange={(e) => setCustomWeightDraft((prev) => ({ ...prev, [role]: Number(e.target.value) }))}
                          className="w-12 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1 py-0.5 text-right text-cmd-text"
                        />
                      </label>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      SettingsManager.update({ customDepartmentWeights: { ...settings.customDepartmentWeights, ...customWeightDraft } });
                      setCustomWeightDraft({});
                    }}
                    disabled={Object.keys(customWeightDraft).length === 0}
                    className="mt-1.5 rounded-sm border border-cmd-cyan/50 px-1.5 py-0.5 text-[9px] text-cmd-cyan transition-colors hover:bg-cmd-cyan/10 disabled:opacity-40"
                  >
                    SAVE CUSTOM WEIGHTS
                  </button>
                </div>
              )}
              {weightedLoading && <div className="text-[9px] text-cmd-textDim">Reweighing the board…</div>}
              {weightedError && <div className="text-[9px] text-cmd-red">{weightedError}</div>}
              {!weightedLoading && weighted && weighted.proposalId === proposal.id && <WeightedDecisionPanel recommendation={weighted} />}
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
                  <TerminalLabel>Risk Budget Remaining</TerminalLabel>
                  {riskBudgetStatus.tradingHalted && <StatusPill tone="red">HALTED</StatusPill>}
                </div>
                <DataRow
                  label="Lifetime drawdown budget"
                  value={`${riskBudgetStatus.remainingDrawdownBudgetPct.toFixed(1)}% of ${riskBudgetStatus.maxDrawdownPct}% left`}
                  valueClassName={riskBudgetStatus.remainingDrawdownBudgetPct <= riskBudgetStatus.maxDrawdownPct * 0.25 ? "text-cmd-red" : undefined}
                />
                <DataRow
                  label="Today's loss budget"
                  value={`${riskBudgetStatus.remainingDailyLossBudgetPct.toFixed(1)}% of ${riskBudgetStatus.maxDailyLossPct}% left`}
                  valueClassName={riskBudgetStatus.remainingDailyLossBudgetPct <= riskBudgetStatus.maxDailyLossPct * 0.25 ? "text-cmd-red" : undefined}
                />
                <DataRow label="Distance to today's profit target" value={`${riskBudgetStatus.remainingToDailyProfitTargetPct.toFixed(1)}%`} />
                <DataRow label="Trading days so far" value={riskBudgetStatus.tradingDaysCount} />
                {riskBudgetStatus.haltReason && <div className="mt-1.5 text-[9px] text-cmd-amber">{riskBudgetStatus.haltReason}</div>}
                <div className="mt-1.5 text-[9px] text-cmd-textDim">
                  Remaining permissible loss budget before this trade — not a new limit, just what&apos;s left of the existing ones above.
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

          {/* Design Bible Chapter 70 Part 2 — "Modify": resize the pending
              proposal downward before deciding. Never sizes up (see
              backend/app/executive.py's modify_proposal for why). */}
          <div className="flex items-center gap-2 text-[9px]">
            <input
              type="number"
              min={0}
              max={proposal.quantity}
              step="0.01"
              value={modifyQuantity}
              onChange={(e) => setModifyQuantity(e.target.value)}
              placeholder={`Resize (currently ${proposal.quantity.toFixed(2)})`}
              className="flex-1 rounded-sm border border-cmd-border bg-cmd-bg/40 px-2 py-1.5 text-cmd-text placeholder:text-cmd-textDim/60 focus:border-cmd-cyan/50 focus:outline-none"
            />
            <button
              type="button"
              disabled={modifying || submitting !== null || holding !== null || !modifyQuantity}
              onClick={() => void modify()}
              className="rounded-sm border border-cmd-border px-3 py-1.5 text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
            >
              {modifying ? "…" : "MODIFY"}
            </button>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <ActionButton
              label="BUY"
              tone="green"
              disabled={submitting !== null || holding !== null}
              loading={submitting === "buy"}
              onClick={() => void decide("buy")}
            />
            <ActionButton
              label="SELL"
              tone="red"
              disabled={submitting !== null || holding !== null}
              loading={submitting === "sell"}
              onClick={() => void decide("sell")}
            />
            <ActionButton
              label="WAIT"
              tone="amber"
              disabled={submitting !== null || holding !== null}
              loading={submitting === "wait"}
              onClick={() => void decide("wait")}
            />
          </div>
          <div className="grid grid-cols-2 gap-2 text-[9px]">
            <button
              type="button"
              disabled={submitting !== null || holding !== null}
              onClick={() => void decide(proposal.overallRecommendation)}
              className="rounded-sm border border-cmd-border py-1.5 text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
            >
              APPROVE (follow desk: {proposal.overallRecommendation.toUpperCase()})
            </button>
            <button
              type="button"
              disabled={submitting !== null || holding !== null}
              onClick={() => void decide("wait")}
              className="rounded-sm border border-cmd-border py-1.5 text-cmd-textDim transition-colors hover:enabled:border-cmd-red/50 hover:enabled:text-cmd-red disabled:opacity-40"
            >
              REJECT (no trade)
            </button>
          </div>
          {/* Design Bible Chapter 70 Part 2 — "Delegate to the Executive
              Board": distinct from APPROVE above, which follows the
              6-analyst desk's own pick — this follows the 9-department
              Executive Intelligence Network's real recommendation
              instead, which can (and does) disagree with the desk. */}
          <button
            type="button"
            disabled={submitting !== null || holding !== null || delegating}
            onClick={() => void delegate()}
            className="w-full rounded-sm border border-cmd-purple/50 py-1.5 text-[9px] text-cmd-purple transition-colors hover:enabled:bg-cmd-purple/10 disabled:opacity-40"
          >
            {delegating ? "…" : "DELEGATE TO EXECUTIVE BOARD"}
          </button>
          {/* v0.7 Feature 40.5 — Expert Consultation System's two real CEO
              actions beyond buy/sell/wait: both just reset the proposal's own
              expiry clock (see hold() above), capped at MAX_PROPOSAL_HOLDS so
              a proposal can't be deferred forever. */}
          <div className="grid grid-cols-2 gap-2 text-[9px]">
            <button
              type="button"
              disabled={submitting !== null || holding !== null || proposal.holdCount >= MAX_PROPOSAL_HOLDS}
              onClick={() => void hold("more_research")}
              className="rounded-sm border border-cmd-border py-1.5 text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
            >
              {holding === "more_research" ? "…" : `REQUEST MORE RESEARCH (${proposal.holdCount}/${MAX_PROPOSAL_HOLDS})`}
            </button>
            <button
              type="button"
              disabled={submitting !== null || holding !== null || proposal.holdCount >= MAX_PROPOSAL_HOLDS}
              onClick={() => void hold("delay")}
              className="rounded-sm border border-cmd-border py-1.5 text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
            >
              {holding === "delay" ? "…" : `DELAY DECISION (${proposal.holdCount}/${MAX_PROPOSAL_HOLDS})`}
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

/**
 * v0.7 Feature 50 (Part 1) — the Executive Intelligence Network's
 * recommendation panel. All 8 department opinions are real stances
 * derived from already-computed systems (see
 * backend/app/executive_intelligence.py); the recommended action is a
 * rule-based synthesis of those opinions, never a fabricated score.
 */
function ExecutiveIntelligencePanel({ recommendation }: { recommendation: ExecutiveRecommendation }) {
  const [expandedRole, setExpandedRole] = useState<string | null>(null);
  const hasWhatIf = recommendation.probabilityOfSuccessPct !== null || recommendation.estimatedReturnPct !== null || recommendation.estimatedRiskPct !== null;
  return (
    <div className="space-y-2">
      <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2">
        <div className="mb-1 flex items-center justify-between gap-2">
          <StatusPill tone={executiveActionTone(recommendation.action)}>{EXECUTIVE_ACTION_LABEL[recommendation.action]}</StatusPill>
          <span className="text-[9px] text-cmd-textDim">{Math.round(recommendation.confidencePct)}% network confidence</span>
        </div>
        <div className="text-[9px] text-cmd-text">{recommendation.reason}</div>
        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[8px] text-cmd-textDim">
          <span>
            Supporting: {recommendation.supporting.length > 0 ? recommendation.supporting.map((r) => EXECUTIVE_DEPARTMENT_LABEL[r]).join(", ") : "none"}
          </span>
          <span>Opposing: {recommendation.opposing.length > 0 ? recommendation.opposing.map((r) => EXECUTIVE_DEPARTMENT_LABEL[r]).join(", ") : "none"}</span>
        </div>
      </div>

      {/* Design Bible Chapter 70 Part 2 — Executive Consensus Meter's
          headline row. Consensus % (share of departments that plainly
          agree) is deliberately shown apart from Confidence % above
          (their average conviction) — two real, different numbers. */}
      <div className="grid grid-cols-2 gap-2 text-[9px]">
        <div className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2">
          <div className="text-cmd-textDim">CONSENSUS</div>
          <div className="text-cmd-cyan">{Math.round(recommendation.consensusPct)}%</div>
        </div>
        <div className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2">
          <div className="text-cmd-textDim">CONFIDENCE</div>
          <div className="text-cmd-cyan">{Math.round(recommendation.confidencePct)}%</div>
        </div>
      </div>

      {hasWhatIf && (
        <div className="grid grid-cols-3 gap-2 text-[9px]">
          <div className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2">
            <div className="text-cmd-textDim">PROB. OF SUCCESS</div>
            <div className="text-cmd-text">{recommendation.probabilityOfSuccessPct !== null ? `${recommendation.probabilityOfSuccessPct.toFixed(0)}%` : "—"}</div>
          </div>
          <div className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2">
            <div className="text-cmd-textDim">EST. RETURN</div>
            <div className="text-cmd-text">{recommendation.estimatedReturnPct !== null ? formatPct(recommendation.estimatedReturnPct) : "—"}</div>
          </div>
          <div className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2">
            <div className="text-cmd-textDim">EST. RISK</div>
            <div className="text-cmd-text">{recommendation.estimatedRiskPct !== null ? formatPct(recommendation.estimatedRiskPct) : "—"}</div>
          </div>
        </div>
      )}
      {hasWhatIf && <div className="text-[8px] text-cmd-textDim">Probability/Return/Risk sourced live from the What-If Simulation Lab — never a fabricated composite.</div>}

      {/* Disagreement Analysis — a real, generated paragraph over the
          same opinions shown card-by-card below, not a separate claim. */}
      <div className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2 text-[9px]">
        <div className="mb-1 text-cmd-textDim">DISAGREEMENT ANALYSIS</div>
        <div className="text-cmd-text">{recommendation.disagreementSummary}</div>
      </div>

      <div className="space-y-1">
        {recommendation.opinions.map((op) => {
          const expanded = expandedRole === op.role;
          const hasDetail = op.evidence.length > 0 || op.concerns.length > 0 || op.benefits.length > 0 || op.alternative;
          return (
            <button
              key={op.role}
              type="button"
              onClick={() => hasDetail && setExpandedRole(expanded ? null : op.role)}
              className="w-full rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2 text-left text-[9px] transition-colors hover:border-cmd-cyan/40"
            >
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="flex items-center gap-1.5">
                  <span className="text-cmd-text">{op.departmentLabel}</span>
                  {op.agentId && <span className="text-cmd-textDim">{AGENT_PROFILES[op.agentId].name}</span>}
                </span>
                <StatusPill tone={executiveStanceTone(op.stance)}>{EXECUTIVE_STANCE_LABEL[op.stance]}</StatusPill>
              </div>
              <div className="text-cmd-textDim">{op.summary}</div>
              <div className="mt-1 text-[8px] text-cmd-textDim">{Math.round(op.confidencePct)}% confidence</div>
              {expanded && (
                <div className="mt-1.5 space-y-1.5 border-t border-cmd-border/50 pt-1.5 text-[8px]">
                  {op.evidence.length > 0 && (
                    <div>
                      <div className="text-cmd-cyan">Supporting Evidence</div>
                      <ul className="list-disc space-y-0.5 pl-3 text-cmd-textDim">
                        {op.evidence.map((e, i) => (
                          <li key={i}>{e}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {op.benefits.length > 0 && (
                    <div>
                      <div className="text-cmd-green">Expected Benefits</div>
                      <ul className="list-disc space-y-0.5 pl-3 text-cmd-textDim">
                        {op.benefits.map((b, i) => (
                          <li key={i}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {op.concerns.length > 0 && (
                    <div>
                      <div className="text-cmd-amber">Primary Concerns</div>
                      <ul className="list-disc space-y-0.5 pl-3 text-cmd-textDim">
                        {op.concerns.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {op.alternative && (
                    <div>
                      <div className="text-cmd-purple">Alternative Recommendation</div>
                      <div className="text-cmd-textDim">{op.alternative}</div>
                    </div>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>
      <div className="text-[8px] text-cmd-textDim">
        Generated {new Date(recommendation.generatedAt).toLocaleTimeString()} — recomputed fresh each time this panel opens, not stored.
      </div>
    </div>
  );
}

/**
 * Design Bible Chapter 70 Part 2 — Executive Accuracy Score. Scored only
 * over trades the CEO actually took and that have since closed with a
 * real outcome (see backend/app/executive_intelligence.py's
 * compute_executive_accuracy_scores). CEO directive "Features 31-35,"
 * Feature 33 — `evaluationState` (not a hand-rolled threshold check
 * here) is the one real source of truth for "does this department have
 * enough evidence yet," including the backend's disclosed minimum
 * sample floor (MIN_ACCURACY_SAMPLE_FOR_VERDICT) — a department can
 * have 1-2 real tracked decisions and still honestly read
 * NOT_ENOUGH_EVIDENCE, not just 0.
 */
function ExecutiveAccuracyPanel({ scores }: { scores: ExecutiveAccuracyScore[] }) {
  const evaluated = scores.filter((s) => s.evaluationState !== "not_enough_evidence" && s.accuracyPct !== null);
  const notEnoughEvidence = scores.filter((s) => s.evaluationState === "not_enough_evidence");
  return (
    <div className="space-y-1.5">
      {evaluated.length === 0 && (
        <div className="text-[9px] text-cmd-textDim">No closed, tracked trades yet — every department's accuracy is still unscored.</div>
      )}
      {evaluated
        .slice()
        .sort((a, b) => (b.accuracyPct ?? 0) - (a.accuracyPct ?? 0))
        .map((s) => {
          const pct = s.accuracyPct as number;
          const tone = s.evaluationState === "pass" ? "green" : s.evaluationState === "fail" ? "red" : "amber";
          return (
            <div key={s.role} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2 text-[9px]">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="text-cmd-text">{s.departmentLabel}</span>
                <span className={tone === "green" ? "text-cmd-green" : tone === "red" ? "text-cmd-red" : "text-cmd-amber"}>{pct.toFixed(0)}%</span>
              </div>
              <Meter value={pct} tone={tone} />
              <div className="mt-1 text-[8px] text-cmd-textDim">
                {s.correctCount}/{s.decisionsTracked} closed, real trades called correctly — {s.evaluationState.toUpperCase()}.
              </div>
            </div>
          );
        })}
      {notEnoughEvidence.length > 0 && (
        <div className="text-[8px] text-cmd-textDim">
          NOT ENOUGH EVIDENCE yet: {notEnoughEvidence.map((s) => `${s.departmentLabel} (${s.decisionsTracked})`).join(", ")}.
        </div>
      )}
    </div>
  );
}

/**
 * Design Bible Chapter 70 Part 3 — Weighted Executive Decision Engine.
 * Always shown alongside the Raw Vote (Executive Intelligence Network
 * panel above), never replacing it — a department's weight is the
 * product of small, published multipliers, each shown in its own
 * reasoning line, never a hidden blend. Purely advisory: nothing here
 * gates or resolves the trade.
 */
function WeightedDecisionPanel({ recommendation }: { recommendation: WeightedExecutiveRecommendation }) {
  const sortedInfluences = [...recommendation.departmentInfluences].sort((a, b) => b.finalWeight - a.finalWeight);
  const sortedActions = Object.entries(recommendation.scoreByAction).sort((a, b) => b[1] - a[1]);
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-2 text-[9px]">
        <div className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2">
          <div className="mb-1 text-cmd-textDim">RAW VOTE</div>
          <StatusPill tone={executiveActionTone(recommendation.rawAction)}>{EXECUTIVE_ACTION_LABEL[recommendation.rawAction]}</StatusPill>
        </div>
        <div className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2">
          <div className="mb-1 text-cmd-textDim">WEIGHTED VOTE</div>
          <StatusPill tone={executiveActionTone(recommendation.weightedAction)}>{EXECUTIVE_ACTION_LABEL[recommendation.weightedAction]}</StatusPill>
        </div>
      </div>
      <div className="text-[9px] text-cmd-textDim">
        {recommendation.agreesWithRaw
          ? "Weighted and Raw votes agree — reweighting didn't change the call."
          : "Weighted and Raw votes disagree — the CEO decides which one to trust."}{" "}
        Market regime: <span className="text-cmd-text">{recommendation.marketRegime.replace(/_/g, " ")}</span>.
      </div>

      <div className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2 text-[9px]">
        <div className="mb-1 text-cmd-textDim">SCORE BY ACTION (published, 0-100)</div>
        <div className="space-y-1">
          {sortedActions.map(([action, score]) => (
            <div key={action} className="flex items-center justify-between gap-2">
              <span className="text-cmd-text">{EXECUTIVE_ACTION_LABEL[action as ExecutiveAction] ?? action}</span>
              <span className="text-cmd-cyan">{score.toFixed(0)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-1">
        {sortedInfluences.map((di) => (
          <div key={di.role} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2 text-[9px]">
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="text-cmd-text">{di.departmentLabel}</span>
              <span className="text-cmd-cyan">{di.finalWeight.toFixed(2)}×</span>
            </div>
            <div className="text-cmd-textDim">{di.reasoning}</div>
          </div>
        ))}
      </div>
      <div className="text-[8px] text-cmd-textDim">
        Historical Accuracy and Market Conditions are the only two of the brief&apos;s eight named weighting inputs with a real, computable
        source today — see the Design Bible chapter for the honest boundary on the rest.
      </div>
    </div>
  );
}
