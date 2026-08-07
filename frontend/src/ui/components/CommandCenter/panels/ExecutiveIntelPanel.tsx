import { useEffect, useState } from "react";
import { api } from "@/net/api";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { EXECUTIVE_ACTION_LABEL, EXECUTIVE_STANCE_LABEL, type BoardReport, type BoardRoster } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { computeDepartmentHealth, computeExecutivePriorities, decisionGradeTone, executiveActionTone, executiveStanceTone, latestSelfEvaluationsByRole, recentMeetingLogEntries } from "../lib/derive";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

const CADENCE_TONE: Record<BoardReport["cadence"], "cyan" | "purple" | "red"> = {
  daily: "cyan",
  quarterly: "purple",
  emergency: "red",
};

/**
 * v0.7 Feature 43 — the Executive Intelligence Dashboard. Researched
 * first (see docs/Architecture.md's "Executive Intelligence Dashboard"
 * section): most of the brief's "Company Health" list already exists
 * under `CompanyHealth`/`CompanyScore`; "Performance Trends" already
 * exists as `PerformanceSnapshot` (see the PERFORMANCE tab); "CEO
 * Insights" is the same real recommendation text this tab's Executive
 * Priorities section already surfaces, just framed as alerts instead of
 * a ranked list. Two pieces are genuinely new here: Company DNA (a real
 * behavioral profile — see app/company_dna.py) and Department Health (a
 * real per-subsystem rollup — see lib/derive.ts's computeDepartmentHealth
 * for exactly which of the brief's five requested dimensions each real
 * subsystem actually supports).
 *
 * Design Bible Chapter 70 Part 1 — Executive Board & CEO Intelligence
 * System (backend/app/board.py). boardRoster has no WS-broadcast field
 * (computed fresh per request, since agent identity rarely changes) —
 * fetched here on mount instead. boardReports IS already live via the
 * WS tick broadcast (gameStore).
 */
export function ExecutiveIntelPanel() {
  const { companyDna, companyHealth, coachReports, executiveReviews, research, riskWarnings, paperPortfolio, blackBox, innovationState, founderState, academyState, executiveMeetingLog, departmentSelfEvaluations, boardReports } = useGameStore();
  const [expandedMeeting, setExpandedMeeting] = useState<string | null>(null);
  const [roster, setRoster] = useState<BoardRoster | null>(null);
  const [rosterError, setRosterError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getBoardRoster()
      .then(setRoster)
      .catch((err: unknown) => setRosterError(err instanceof Error ? err.message : "Failed to load the Board Roster."));
  }, []);

  const priorities = computeExecutivePriorities(companyHealth, coachReports, executiveReviews);
  const departments = computeDepartmentHealth({
    companyHealth,
    research,
    riskWarnings,
    portfolio: paperPortfolio,
    blackBox,
    innovationState,
    coachReports,
    founderState,
    academyState,
  });
  const recentMeetings = recentMeetingLogEntries(executiveMeetingLog, 20);
  const latestSelfEvaluations = latestSelfEvaluationsByRole(departmentSelfEvaluations);

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Company DNA</TerminalLabel>
          <StatusPill tone={companyDna.sampleSize > 0 ? "cyan" : "neutral"}>
            {companyDna.sampleSize > 0 ? `${companyDna.sampleSize} decision(s) analyzed` : "NOT ENOUGH HISTORY"}
          </StatusPill>
        </div>
        <div className="mb-2 flex items-center gap-2">
          <span data-testid="company-dna-identity" className="text-cmd-purple">
            {companyDna.identity}
          </span>
        </div>
        <p className="mb-2 text-cmd-text">{companyDna.summary}</p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-5">
          {companyDna.traits.map((trait) => (
            <div key={trait.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-[9px] uppercase tracking-wide text-cmd-textDim">{trait.name}</span>
                <span className="font-cmdmono text-cmd-cyan">{Math.round(trait.score)}</span>
              </div>
              <Meter value={trait.score} tone="cyan" />
              <div className="mt-1.5 text-[9px] text-cmd-textDim">{trait.detail}</div>
            </div>
          ))}
        </div>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Board Roster — 11 of the brief&apos;s 12 named seats (the 12th is never named in the source brief)</TerminalLabel>
        {roster === null ? (
          rosterError ? <div className="text-[9px] text-cmd-red">{rosterError}</div> : <EmptyState>Loading the Board Roster…</EmptyState>
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {roster.seats.map((seat) => (
              <div key={seat.title} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-cmd-cyan">{seat.title}</span>
                  <StatusPill tone={seat.agentId ? "green" : "neutral"}>{seat.agentId ? "FILLED" : "VACANT"}</StatusPill>
                </div>
                <div className="text-cmd-text">{seat.agentName ?? "No agent holds this seat."}</div>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Executive Priorities — What Deserves Attention First</TerminalLabel>
        {priorities.length === 0 ? (
          <EmptyState>Every real signal is holding strong — nothing urgent on record right now.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {priorities.map((p, i) => (
              <div key={`${p.label}-${i}`} className="flex items-start gap-2 rounded-sm border border-cmd-amber/30 bg-cmd-bg/40 p-2 text-[9px]">
                <span className="font-cmdmono text-cmd-amber">{i + 1}.</span>
                <span className="flex-1 text-cmd-text">{p.label}</span>
                <span className="uppercase tracking-wide text-cmd-textDim">{p.source}</span>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Department Health</TerminalLabel>
        <p className="mb-2 text-[9px] text-cmd-textDim">
          This codebase has no literal "department" concept — these are the real subsystems that stand in for the brief&apos;s named departments. Each shows whichever real
          Efficiency/Workload/Morale/Productivity/Bottleneck signal that subsystem actually tracks, never a uniform template. &quot;Brain Room&quot; is not shown here — it&apos;s
          the room housing this Overview HUD, not a distinct operational unit with its own state.
        </p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {departments.map((dept) => (
            <div key={dept.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2">
              <div className="mb-1 text-cmd-cyan">{dept.label}</div>
              {dept.metrics.map((m) => (
                <DataRow key={m.label} label={m.label} value={m.value} />
              ))}
            </div>
          ))}
        </div>
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Weekly Self-Evaluation</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">v0.7 Feature 50 (Part 2/3) — one real read per department per in-game week</span>
        </div>
        {latestSelfEvaluations.length === 0 ? (
          <EmptyState>No real decisions have reached the network yet — nothing to self-evaluate.</EmptyState>
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {latestSelfEvaluations.map((evaluation) => (
              <div key={evaluation.role} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-cmd-cyan">{evaluation.departmentLabel}</span>
                  <span className="text-cmd-text">{Math.round(evaluation.score)}/100</span>
                </div>
                <Meter value={evaluation.score} tone={evaluation.score >= 70 ? "green" : evaluation.score >= 45 ? "amber" : "red"} />
                <div className="mt-1.5 text-cmd-textDim">{evaluation.summary}</div>
                {evaluation.strengths.length > 0 && (
                  <div className="mt-1.5 text-cmd-green">{evaluation.strengths[0]}</div>
                )}
                {evaluation.improvementAreas.length > 0 && (
                  <div className="mt-1 text-cmd-amber">{evaluation.improvementAreas[0]}</div>
                )}
                <div className="mt-1.5 text-cmd-textDim">Week ending sim day {evaluation.weekEndingSimDay}</div>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Executive Meeting Log ({executiveMeetingLog.length})</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">v0.7 Feature 50 (Part 2/3) — one real entry per resolved decision</span>
        </div>
        {recentMeetings.length === 0 ? (
          <EmptyState>No real Executive decisions have been recorded yet.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {recentMeetings.map((entry) => {
              const expanded = expandedMeeting === entry.id;
              return (
                <button
                  key={entry.id}
                  type="button"
                  onClick={() => setExpandedMeeting(expanded ? null : entry.id)}
                  className="w-full rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-left transition-colors hover:border-cmd-cyan/40"
                >
                  <div className="flex flex-wrap items-center gap-2 text-[9px]">
                    <span className="font-cmdmono text-cmd-cyan">{entry.symbol}</span>
                    <StatusPill tone={executiveActionTone(entry.recommendedAction)}>{EXECUTIVE_ACTION_LABEL[entry.recommendedAction]}</StatusPill>
                    <StatusPill tone={decisionGradeTone(entry.decisionGrade)}>{entry.decisionGrade}</StatusPill>
                    <span className={entry.networkAgreed ? "text-cmd-green" : "text-cmd-amber"}>{entry.networkAgreed ? "CEO agreed" : "CEO diverged"}</span>
                    <span className="ml-auto text-cmd-textDim">Day {entry.simDay} — {entry.resolvedBy === "ceo" ? "CEO decision" : "auto-resolved"}</span>
                  </div>
                  {expanded && (
                    <div className="mt-1.5 space-y-1.5 border-t border-cmd-border/50 pt-1.5">
                      <div className="text-[9px] text-cmd-text">{entry.recommendationReason}</div>
                      <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
                        {entry.opinions.map((op) => (
                          <div key={op.role} className="flex items-center justify-between gap-2 rounded-sm border border-cmd-border/40 bg-cmd-bg/60 p-1.5 text-[9px]">
                            <span className="flex items-center gap-1.5">
                              <span className="text-cmd-textDim">{op.departmentLabel}</span>
                              {op.agentId && <span className="text-cmd-textDim">({AGENT_PROFILES[op.agentId].name})</span>}
                            </span>
                            <StatusPill tone={executiveStanceTone(op.stance)}>{EXECUTIVE_STANCE_LABEL[op.stance]}</StatusPill>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Board Reports ({boardReports.length})</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">Daily / Quarterly / Emergency — composed from already-real signals, never a duplicate computation</span>
        </div>
        {boardReports.length === 0 ? (
          <EmptyState>No Board Report has been filed yet.</EmptyState>
        ) : (
          <div className="max-h-96 space-y-1.5 overflow-y-auto">
            {[...boardReports].reverse().map((report) => (
              <div key={report.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <StatusPill tone={CADENCE_TONE[report.cadence]}>{report.cadence.toUpperCase()}</StatusPill>
                  {report.trigger && <span className="text-cmd-textDim">({report.trigger.replace("_", " ")})</span>}
                  <span className="ml-auto text-cmd-textDim">Day {report.simDay}</span>
                </div>
                <p className="mb-1.5 text-cmd-text">{report.summary}</p>
                <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 sm:grid-cols-4">
                  <DataRow label="Confidence" value={`${report.confidenceLevel.toFixed(0)}%`} />
                  <DataRow label="Decisions Pending" value={report.requiredCeoDecisions} />
                  <DataRow label="Problems" value={report.problems.length} />
                  <DataRow label="Recommendations" value={report.recommendations.length} />
                </div>
                {report.problems.length > 0 && (
                  <div className="mt-1.5 space-y-0.5">
                    {report.problems.map((p) => (
                      <div key={p} className="text-cmd-amber">{p}</div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}
