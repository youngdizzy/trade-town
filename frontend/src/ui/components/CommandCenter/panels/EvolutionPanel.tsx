import { useEffect, useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { NexusManager } from "@/game/systems/NexusManager";
import { api } from "@/net/api";
import { AGENT_IDS } from "@/types";
import type {
  AgentId,
  CaseStudyCategory,
  CompanyEvolutionScore,
  CompanyEvolutionWindow,
  DisciplineTier,
  ExecutiveLearningSummary,
  LossWinClassificationRead,
  SelfImprovementCategory,
  SelfImprovementProposal,
  VisionObjectiveCategory,
  VisionPriorityCategory,
  VisionSelfCorrectionNote,
} from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

/**
 * Design Bible Chapter 74 — Continuous Learning & Self-Improvement
 * System (CLSIS, Part 1; backend/app/self_improvement.py), the
 * Institutional Evolution Engine (Part 2; backend/app/evolution.py),
 * and Chapter 74.5's CEO Vision Board & Strategic Alignment Engine
 * (backend/app/vision_board.py) — three real, previously frontend-less
 * systems bundled under one tab, the same pattern TradingModesPanel
 * established for Chapter 75's own multi-part backend.
 * selfImprovementProposals/evolutionReports/visionBoard are live via
 * the WS tick broadcast (gameStore); Executive Learning Summary, the
 * Company Evolution Score, and the Vision Self-Correction Note have no
 * WS-broadcast field and are fetched on demand. Goal/constitution-
 * amendment Vision Alignment lookups exist at the API layer but have no
 * UI surface here — they belong on the Goals/Constitution panels
 * themselves, not this one.
 */

const CATEGORY_LABEL: Record<SelfImprovementCategory, string> = {
  risk_rule: "Risk Rule",
  dashboard: "Dashboard",
  research_workflow: "Research Workflow",
  position_sizing: "Position Sizing",
  new_executive: "New Executive",
  automation: "Automation",
  knowledge_organization: "Knowledge Organization",
  ui: "UI",
};

const PRIORITY_TONE: Record<SelfImprovementProposal["priority"], "green" | "amber" | "red"> = {
  low: "green",
  medium: "amber",
  high: "red",
};

const STATUS_TONE: Record<SelfImprovementProposal["status"], "neutral" | "cyan" | "green" | "red"> = {
  pending: "cyan",
  approved: "green",
  rejected: "red",
  implemented: "green",
};

// Trading Psychology & Discipline, Piece D — mirrors DisciplinePanel.tsx's
// own local TIER_TONE/CATEGORY_LABEL exactly (each Command Center panel
// stays self-contained rather than cross-importing another panel's
// module-local consts).
const TIER_TONE: Record<DisciplineTier, "green" | "cyan" | "amber" | "red"> = {
  exemplary: "green",
  sound: "cyan",
  adequate: "amber",
  weak: "amber",
  reckless: "red",
};

const CASE_STUDY_CATEGORY_LABEL: Record<CaseStudyCategory, string> = {
  overconfidence: "The Cost of Overconfidence",
  incomplete_research: "Incomplete Research",
  unchallenged_assumptions: "Failure to Challenge Assumptions",
  acted_too_quickly: "Acting Too Quickly",
  ignored_dissent: "Poor Communication",
  confirmation_bias: "Confirmation Bias",
  disciplined_process: "A Well-Disciplined Process",
  rigorous_cross_examination: "Rigorous Cross-Examination",
  patient_execution: "Patient Execution",
};

const VISION_PRIORITY_LABEL: Record<VisionPriorityCategory, string> = {
  growth: "Growth",
  risk: "Risk",
  research: "Research",
  trading: "Trading",
  operations: "Operations",
  governance: "Governance",
};

const ALL_VISION_PRIORITIES: VisionPriorityCategory[] = ["growth", "risk", "research", "trading", "operations", "governance"];

const OBJECTIVE_CATEGORY_LABEL: Record<VisionObjectiveCategory, string> = {
  trading_style: "Trading Style",
  expansion: "Expansion",
  research_priority: "Research Priority",
  technology: "Technology",
  lifestyle: "Lifestyle",
  other: "Other",
};

export function EvolutionPanel() {
  const { selfImprovementProposals, evolutionReports, visionBoard, disciplineReviews, caseStudies } = useGameStore();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [implementNoteByProposal, setImplementNoteByProposal] = useState<Record<string, string>>({});

  const [learningAgent, setLearningAgent] = useState<AgentId>(AGENT_IDS[0]!);
  const [learningSummary, setLearningSummary] = useState<ExecutiveLearningSummary | null>(null);

  const [evolutionWindow, setEvolutionWindow] = useState<CompanyEvolutionWindow>("monthly");
  const [evolutionScore, setEvolutionScore] = useState<CompanyEvolutionScore | null>(null);

  const [lossWinClassification, setLossWinClassification] = useState<LossWinClassificationRead | null>(null);

  const [missionDraft, setMissionDraft] = useState(visionBoard.mission ?? "");
  const [identityNoteDraft, setIdentityNoteDraft] = useState(visionBoard.identityNote ?? "");
  const [objectiveText, setObjectiveText] = useState("");
  const [objectiveCategory, setObjectiveCategory] = useState<VisionObjectiveCategory>("other");
  const [selfCorrection, setSelfCorrection] = useState<VisionSelfCorrectionNote | null>(null);

  useEffect(() => {
    setMissionDraft(visionBoard.mission ?? "");
  }, [visionBoard.mission]);

  useEffect(() => {
    setIdentityNoteDraft(visionBoard.identityNote ?? "");
  }, [visionBoard.identityNote]);

  useEffect(() => {
    api.getExecutiveLearningSummary(learningAgent).then(setLearningSummary).catch(() => setLearningSummary(null));
  }, [learningAgent]);

  useEffect(() => {
    api.getCompanyEvolutionScore(evolutionWindow).then(setEvolutionScore).catch(() => setEvolutionScore(null));
  }, [evolutionWindow, evolutionReports.length]);

  useEffect(() => {
    api.getLossWinClassification().then(setLossWinClassification).catch(() => setLossWinClassification(null));
  }, [disciplineReviews.length, caseStudies.length]);

  useEffect(() => {
    api.getVisionSelfCorrectionNote().then(setSelfCorrection).catch(() => setSelfCorrection(null));
  }, [visionBoard.priorities]);

  const pendingProposals = useMemo(() => selfImprovementProposals.filter((p) => p.status === "pending"), [selfImprovementProposals]);
  const otherProposals = useMemo(() => [...selfImprovementProposals.filter((p) => p.status !== "pending")].reverse(), [selfImprovementProposals]);
  const recentReports = useMemo(() => [...evolutionReports].reverse(), [evolutionReports]);

  const runAction = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const decide = (proposalId: string, approve: boolean) =>
    runAction(async () => {
      const proposals = await api.decideSelfImprovementProposal(proposalId, approve);
      NexusManager.setSelfImprovementProposals(proposals);
    });

  const implement = (proposalId: string) =>
    runAction(async () => {
      const note = implementNoteByProposal[proposalId]?.trim() || undefined;
      const proposals = await api.markSelfImprovementProposalImplemented(proposalId, note);
      NexusManager.setSelfImprovementProposals(proposals);
      setImplementNoteByProposal((prev) => ({ ...prev, [proposalId]: "" }));
    });

  const saveMission = () =>
    runAction(async () => {
      const board = await api.setVisionBoardMission(missionDraft.trim() || null);
      NexusManager.setVisionBoard(board);
    });

  const saveIdentityNote = () =>
    runAction(async () => {
      const board = await api.setVisionBoardIdentityNote(identityNoteDraft.trim() || null);
      NexusManager.setVisionBoard(board);
    });

  const movePriority = (category: VisionPriorityCategory, direction: -1 | 1) =>
    runAction(async () => {
      const current = visionBoard.priorities.length > 0 ? visionBoard.priorities : ALL_VISION_PRIORITIES;
      const index = current.indexOf(category);
      const targetIndex = index + direction;
      if (index < 0 || targetIndex < 0 || targetIndex >= current.length) return;
      const reordered = [...current];
      [reordered[index], reordered[targetIndex]] = [reordered[targetIndex]!, reordered[index]!];
      const board = await api.setVisionBoardPriorities(reordered);
      NexusManager.setVisionBoard(board);
    });

  const addObjective = () =>
    runAction(async () => {
      if (!objectiveText.trim()) return;
      const board = await api.addVisionBoardObjective(objectiveText.trim(), objectiveCategory);
      NexusManager.setVisionBoard(board);
      setObjectiveText("");
    });

  const removeObjective = (objectiveId: string) =>
    runAction(async () => {
      const board = await api.removeVisionBoardObjective(objectiveId);
      NexusManager.setVisionBoard(board);
    });

  const rankedPriorities = visionBoard.priorities.length > 0 ? visionBoard.priorities : [];

  return (
    <div className="space-y-3">
      {error && <div className="rounded-sm border border-cmd-red/50 bg-cmd-red/10 p-2 text-[9px] text-cmd-red">{error}</div>}

      <Glass className="p-3">
        <TerminalLabel>Self-Improvement Proposals — CEO-manual resolution only, never automation-eligible</TerminalLabel>
        {pendingProposals.length === 0 && otherProposals.length === 0 ? (
          <EmptyState>No self-improvement proposals filed yet — these fire when a real recurring pattern is detected.</EmptyState>
        ) : (
          <div className="space-y-2">
            {pendingProposals.map((proposal) => (
              <div key={proposal.id} className="rounded-sm border border-cmd-cyan/40 bg-cmd-bg/40 p-2 text-[9px]">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="text-cmd-cyan">{proposal.title}</span>
                  <div className="flex shrink-0 items-center gap-1.5">
                    <StatusPill tone={PRIORITY_TONE[proposal.priority]}>{proposal.priority}</StatusPill>
                    <StatusPill tone="neutral">{CATEGORY_LABEL[proposal.category]}</StatusPill>
                  </div>
                </div>
                <p className="mb-1 text-cmd-text">{proposal.reasoning}</p>
                <DataRow label="Evidence" value={`${proposal.evidence.length} real record(s) cited`} />
                <DataRow label="Confidence" value={`${proposal.confidence.toFixed(0)}%`} />
                {proposal.benefits.length > 0 && <div className="mt-1 text-cmd-textDim">Benefits: {proposal.benefits.join(" ")}</div>}
                {proposal.risks.length > 0 && <div className="mt-0.5 text-cmd-amber">Risks: {proposal.risks.join(" ")}</div>}
                <div className="mt-1.5 flex gap-2">
                  <button type="button" onClick={() => void decide(proposal.id, true)} disabled={busy} className="rounded-sm border border-cmd-green/50 px-2 py-0.5 text-[9px] uppercase text-cmd-green hover:bg-cmd-green/10 disabled:opacity-40">
                    Approve
                  </button>
                  <button type="button" onClick={() => void decide(proposal.id, false)} disabled={busy} className="rounded-sm border border-cmd-red/50 px-2 py-0.5 text-[9px] uppercase text-cmd-red hover:bg-cmd-red/10 disabled:opacity-40">
                    Reject
                  </button>
                </div>
              </div>
            ))}

            {otherProposals.length > 0 && (
              <div className="max-h-72 space-y-1.5 overflow-y-auto border-t border-cmd-border/50 pt-2">
                {otherProposals.map((proposal) => (
                  <div key={proposal.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                    <div className="mb-0.5 flex items-center justify-between gap-2">
                      <span className="text-cmd-text">{proposal.title}</span>
                      <StatusPill tone={STATUS_TONE[proposal.status]}>{proposal.status}</StatusPill>
                    </div>
                    {proposal.ceoNote && <div className="text-cmd-textDim">CEO note: {proposal.ceoNote}</div>}
                    {proposal.status === "implemented" && (
                      <div className="mt-0.5 text-cmd-green">
                        Implemented{proposal.implementationNote ? `: ${proposal.implementationNote}` : ""}
                      </div>
                    )}
                    {proposal.status === "approved" && (
                      <div className="mt-1.5 flex items-center gap-1.5">
                        <input
                          type="text"
                          value={implementNoteByProposal[proposal.id] ?? ""}
                          onChange={(e) => setImplementNoteByProposal((prev) => ({ ...prev, [proposal.id]: e.target.value }))}
                          placeholder="What did you actually change? (optional)"
                          className="flex-1 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text placeholder:text-cmd-textDim outline-none focus:border-cmd-cyan/50"
                        />
                        <button
                          type="button"
                          onClick={() => void implement(proposal.id)}
                          disabled={busy}
                          className="shrink-0 rounded-sm border border-cmd-cyan/50 px-2 py-1 text-[9px] uppercase text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40"
                        >
                          Mark Implemented
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Loss/Win Classification — formalized on top of the Discipline Chamber</TerminalLabel>
        {lossWinClassification === null ? (
          <EmptyState>Loading…</EmptyState>
        ) : lossWinClassification.totalReviewed === 0 ? (
          <EmptyState>No trades reviewed by the Discipline Chamber yet.</EmptyState>
        ) : (
          <div className="text-[9px]">
            <div className="mb-1.5 flex items-center gap-1.5">
              <StatusPill tone={lossWinClassification.winRatePct !== null && lossWinClassification.winRatePct >= 50 ? "green" : "amber"}>
                {lossWinClassification.winRatePct !== null ? `${lossWinClassification.winRatePct.toFixed(0)}% win rate` : "N/A"}
              </StatusPill>
              <span className="text-cmd-textDim">
                {lossWinClassification.winCount}W / {lossWinClassification.lossCount}L over {lossWinClassification.totalReviewed} reviewed
              </span>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <div className="mb-1 text-cmd-textDim">By Discipline tier</div>
                {lossWinClassification.byTier.map((row) => (
                  <div key={row.tier} className="mb-0.5 flex items-center justify-between gap-2">
                    <StatusPill tone={TIER_TONE[row.tier]}>{row.tier}</StatusPill>
                    <span className="text-cmd-text">
                      {row.winCount}W / {row.lossCount}L
                    </span>
                  </div>
                ))}
              </div>
              <div>
                <div className="mb-1 text-cmd-textDim">Process/outcome alignment</div>
                <DataRow label="Aligned (good process→win, weak→loss)" value={lossWinClassification.alignedCount} />
                <DataRow label="Unlucky loss (good process, still lost)" value={lossWinClassification.unluckyLossCount} />
                <DataRow label="Lucky win (weak process, still won)" value={lossWinClassification.luckyWinCount} />
              </div>
            </div>
            {(lossWinClassification.mostCommonMistakeCategory || lossWinClassification.mostCommonSuccessCategory) && (
              <div className="mt-1.5 border-t border-cmd-border/50 pt-1.5">
                {lossWinClassification.mostCommonMistakeCategory && (
                  <DataRow
                    label="Most common mistake"
                    value={`${CASE_STUDY_CATEGORY_LABEL[lossWinClassification.mostCommonMistakeCategory]} (${lossWinClassification.mostCommonMistakeCount}×)`}
                  />
                )}
                {lossWinClassification.mostCommonSuccessCategory && (
                  <DataRow
                    label="Most common success"
                    value={`${CASE_STUDY_CATEGORY_LABEL[lossWinClassification.mostCommonSuccessCategory]} (${lossWinClassification.mostCommonSuccessCount}×)`}
                  />
                )}
              </div>
            )}
          </div>
        )}
      </Glass>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Glass className="p-3">
          <TerminalLabel>Executive Learning Summary — pure composition of four already-real per-agent systems</TerminalLabel>
          <select
            value={learningAgent}
            onChange={(e) => setLearningAgent(e.target.value as AgentId)}
            className="mb-2 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          >
            {AGENT_IDS.map((id) => (
              <option key={id} value={id}>
                {AGENT_PROFILES[id].name}
              </option>
            ))}
          </select>
          {learningSummary === null ? (
            <EmptyState>Loading…</EmptyState>
          ) : (
            <div className="text-[9px]">
              <DataRow label="Research Accuracy" value={learningSummary.researchAccuracy !== null ? `${learningSummary.researchAccuracy.toFixed(0)}%` : "No data yet"} />
              <DataRow label="Confidence Calibration" value={learningSummary.confidenceCalibration !== null ? `${learningSummary.confidenceCalibration.toFixed(0)}%` : "No data yet"} />
              <DataRow label="Knowledge Tier" value={`${learningSummary.knowledgeTier} (${learningSummary.knowledgeLevel})`} />
              <DataRow label="Knowledge Points" value={learningSummary.knowledgePoints.toFixed(0)} />
              <DataRow label="Mentor Tracks" value={learningSummary.mentorTracks.length > 0 ? learningSummary.mentorTracks.join(", ") : "None started"} />
              <DataRow label="Graduated Tracks" value={learningSummary.graduatedTrackCount} />
            </div>
          )}
        </Glass>

        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Company Evolution Score — real, disclosed, unweighted mean of 5 factors</TerminalLabel>
            <select
              value={evolutionWindow}
              onChange={(e) => setEvolutionWindow(e.target.value as CompanyEvolutionWindow)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-0.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
            >
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
              <option value="yearly">Yearly</option>
            </select>
          </div>
          {evolutionScore === null ? (
            <EmptyState>Loading…</EmptyState>
          ) : (
            <div className="text-[9px]">
              <div className="mb-1 flex items-center gap-1.5">
                <StatusPill tone={evolutionScore.overall >= 60 ? "green" : evolutionScore.overall >= 30 ? "amber" : "neutral"}>{evolutionScore.overall.toFixed(0)} / 100</StatusPill>
                <span className="text-cmd-textDim">
                  Day {evolutionScore.periodStartSimDay}–{evolutionScore.periodEndSimDay}
                </span>
              </div>
              <DataRow label="Learning Volume" value={`${evolutionScore.learningVolume.toFixed(0)}%`} />
              <DataRow label="Proposal Execution" value={`${evolutionScore.proposalExecution.toFixed(0)}%`} />
              <DataRow label="Knowledge Growth" value={`${evolutionScore.knowledgeGrowth.toFixed(0)}%`} />
              <DataRow label="Strategy Maturation" value={`${evolutionScore.strategyMaturation.toFixed(0)}%`} />
              <DataRow label="Governance Evolution" value={`${evolutionScore.governanceEvolution.toFixed(0)}%`} />
            </div>
          )}
        </Glass>
      </div>

      <Glass className="p-3">
        <TerminalLabel>Institutional Evolution Reports — composes, never recomputes, this period&apos;s own real monthly reports</TerminalLabel>
        {recentReports.length === 0 ? (
          <EmptyState>No evolution reports generated yet.</EmptyState>
        ) : (
          <div className="max-h-72 space-y-1.5 overflow-y-auto">
            {recentReports.map((report) => (
              <div key={report.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                <div className="mb-0.5 flex items-center justify-between">
                  <span className="text-cmd-textDim">Day {report.simDay}</span>
                  <StatusPill tone="cyan">{report.evolutionScore.overall.toFixed(0)} / 100</StatusPill>
                </div>
                <p className="text-cmd-text">{report.summary}</p>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>CEO Vision Board — advisory only, never bypasses risk or governance</TerminalLabel>

        {selfCorrection?.triggered && (
          <div className="mb-2 rounded-sm border border-cmd-amber/50 bg-cmd-amber/10 p-2 text-[9px] text-cmd-amber">{selfCorrection.message}</div>
        )}

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <div>
            <label className="mb-1 block text-cmd-textDim">Mission</label>
            <textarea
              value={missionDraft}
              onChange={(e) => setMissionDraft(e.target.value)}
              placeholder="What is this company trying to become?"
              rows={2}
              className="mb-1 w-full resize-none rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text placeholder:text-cmd-textDim outline-none focus:border-cmd-cyan/50"
            />
            <button type="button" onClick={() => void saveMission()} disabled={busy || missionDraft === (visionBoard.mission ?? "")} className="rounded-sm border border-cmd-cyan/50 px-2 py-0.5 text-[9px] uppercase text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40">
              Save Mission
            </button>

            <label className="mb-1 mt-2 block text-cmd-textDim">Identity Note</label>
            <textarea
              value={identityNoteDraft}
              onChange={(e) => setIdentityNoteDraft(e.target.value)}
              placeholder="CEO annotation next to the company's derived identity classification"
              rows={2}
              className="mb-1 w-full resize-none rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text placeholder:text-cmd-textDim outline-none focus:border-cmd-cyan/50"
            />
            <button type="button" onClick={() => void saveIdentityNote()} disabled={busy || identityNoteDraft === (visionBoard.identityNote ?? "")} className="rounded-sm border border-cmd-cyan/50 px-2 py-0.5 text-[9px] uppercase text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40">
              Save Identity Note
            </button>
          </div>

          <div>
            <label className="mb-1 block text-cmd-textDim">Priorities (rank 1 = highest)</label>
            {rankedPriorities.length === 0 ? (
              <p className="mb-2 text-cmd-textDim">No ranking set yet — every category is treated equally.</p>
            ) : (
              <div className="mb-2 space-y-1">
                {rankedPriorities.map((category, index) => (
                  <div key={category} className="flex items-center justify-between gap-2 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 px-1.5 py-1">
                    <span className="text-cmd-text">
                      {index + 1}. {VISION_PRIORITY_LABEL[category]}
                    </span>
                    <div className="flex gap-1">
                      <button type="button" onClick={() => void movePriority(category, -1)} disabled={busy || index === 0} className="rounded-sm border border-cmd-border px-1.5 text-cmd-textDim hover:text-cmd-text disabled:opacity-30">
                        ↑
                      </button>
                      <button type="button" onClick={() => void movePriority(category, 1)} disabled={busy || index === rankedPriorities.length - 1} className="rounded-sm border border-cmd-border px-1.5 text-cmd-textDim hover:text-cmd-text disabled:opacity-30">
                        ↓
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {rankedPriorities.length === 0 && (
              <button
                type="button"
                onClick={() =>
                  void runAction(async () => {
                    const board = await api.setVisionBoardPriorities(ALL_VISION_PRIORITIES);
                    NexusManager.setVisionBoard(board);
                  })
                }
                disabled={busy}
                className="rounded-sm border border-cmd-cyan/50 px-2 py-0.5 text-[9px] uppercase text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40"
              >
                Set a Ranking
              </button>
            )}
          </div>
        </div>

        <div className="mt-3 border-t border-cmd-border/50 pt-2">
          <label className="mb-1 block text-cmd-textDim">Objectives</label>
          {visionBoard.objectives.length === 0 ? (
            <EmptyState>No objectives on the board yet.</EmptyState>
          ) : (
            <div className="mb-2 space-y-1">
              {visionBoard.objectives.map((objective) => (
                <div key={objective.id} className="flex items-center justify-between gap-2 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 px-1.5 py-1 text-[9px]">
                  <div>
                    <span className="text-cmd-text">{objective.text}</span>
                    <span className="ml-1.5 text-cmd-textDim">({OBJECTIVE_CATEGORY_LABEL[objective.category]})</span>
                  </div>
                  <button type="button" onClick={() => void removeObjective(objective.id)} disabled={busy} className="shrink-0 rounded-sm border border-cmd-red/50 px-1.5 py-0.5 text-cmd-red hover:bg-cmd-red/10 disabled:opacity-40">
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="flex items-center gap-1.5">
            <input
              type="text"
              value={objectiveText}
              onChange={(e) => setObjectiveText(e.target.value)}
              placeholder="New objective"
              className="flex-1 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text placeholder:text-cmd-textDim outline-none focus:border-cmd-cyan/50"
            />
            <select
              value={objectiveCategory}
              onChange={(e) => setObjectiveCategory(e.target.value as VisionObjectiveCategory)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
            >
              {(Object.keys(OBJECTIVE_CATEGORY_LABEL) as VisionObjectiveCategory[]).map((c) => (
                <option key={c} value={c}>
                  {OBJECTIVE_CATEGORY_LABEL[c]}
                </option>
              ))}
            </select>
            <button type="button" onClick={() => void addObjective()} disabled={busy || !objectiveText.trim()} className="shrink-0 rounded-sm border border-cmd-cyan/50 px-2 py-1 text-[9px] uppercase text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40">
              Add
            </button>
          </div>
        </div>
      </Glass>
    </div>
  );
}
