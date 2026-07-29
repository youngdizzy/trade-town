import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { NexusManager } from "@/game/systems/NexusManager";
import { api } from "@/net/api";
import { AGENT_IDS } from "@/types";
import type { AgentId, ThinkingProfile } from "@/types";
import { computeBestCollaborators, computeGrowthHistory } from "../lib/derive";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

/**
 * v0.7 Feature 44 — the Talent Discovery System (see
 * backend/app/talent.py's module docstring for the full research
 * rationale). Four of the brief's six sections are real here:
 *
 * - Performance Analysis reuses the exact ThinkingProfile/AgentScore data
 *   already computed for the Mentor tab — no new computation.
 * - Discovery Events are real Talent Reports: each only ever fires when a
 *   specific agent's own best ThinkingProfile trait clears a real
 *   threshold AND their last three CoachReport scores are all
 *   consistently strong (see app/talent.py) — never a fabricated pattern.
 * - Growth History is a real per-agent timeline built from every existing
 *   record that already names that agent (see lib/derive.ts's
 *   computeGrowthHistory).
 * - "Best Collaborators" is the one real signal salvageable from the
 *   brief's "Team Optimization": who actually supports vs. challenges
 *   whom across every real AI Debate (see computeBestCollaborators).
 *
 * "Career Development" and most of "CEO Decision"/"Team Optimization" are
 * deliberately not built: this codebase's roster is fixed at game start
 * (agents.py's AgentProfile is a frozen dataclass; founders.py's own
 * docstring states plainly that no employee ever joins or changes role) —
 * so no occupation ever changes, no promotion mechanic exists, and no
 * roster recomposition is possible. A Talent Report's "Suggested Focus" is
 * a real coaching note, not a career-path promise.
 */
export function TalentPanel() {
  const { talent, thinkingProfiles, coachReports, disciplineReviews, reasoningChallenges, reflectionSessions, challengeReports, blackBox, debates } = useGameStore();
  const [selectedAgent, setSelectedAgent] = useState<AgentId>(AGENT_IDS[0]!);
  const [acking, setAcking] = useState<string | null>(null);

  const profiles = useMemo(() => Object.values(thinkingProfiles) as ThinkingProfile[], [thinkingProfiles]);
  const reports = useMemo(() => [...talent.reports].reverse(), [talent.reports]);
  const growthHistory = useMemo(
    () => computeGrowthHistory(selectedAgent, { disciplineReviews, reasoningChallenges, reflectionSessions, challengeReports, blackBox, coachReports }),
    [selectedAgent, disciplineReviews, reasoningChallenges, reflectionSessions, challengeReports, blackBox, coachReports],
  );
  const collaborators = useMemo(() => computeBestCollaborators(debates).slice(0, 8), [debates]);

  const ackReport = async (reportId: string) => {
    if (acking) return;
    setAcking(reportId);
    try {
      const res = await api.ackTalentReport(reportId);
      NexusManager.setViewedTalentReportIds(res.viewedReportIds);
    } finally {
      setAcking(null);
    }
  };

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Discovery Events — Talent Reports</TerminalLabel>
          <StatusPill tone={reports.length > 0 ? "cyan" : "neutral"}>{reports.length}</StatusPill>
        </div>
        <p className="mb-2 text-[9px] text-cmd-textDim">
          A report only ever files when one employee&apos;s own best real thinking trait clears a high bar and their last three Coach Report scores are all consistently strong —
          never a fabricated pattern.
        </p>
        {reports.length === 0 ? (
          <EmptyState>No Discovery Events filed yet — these take real, sustained strong performance to earn.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {reports.map((report) => {
              const seen = talent.viewedReportIds.includes(report.id);
              return (
                <div key={report.id} className={`rounded-sm border p-2 text-[9px] ${seen ? "border-cmd-border/60 bg-cmd-bg/40" : "border-cmd-cyan/50 bg-cmd-cyan/5"}`}>
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      {!seen && <StatusPill tone="cyan">NEW</StatusPill>}
                      <span className="text-cmd-cyan">{report.title}</span>
                    </div>
                    <span className="text-cmd-textDim">Day {report.simDay}</span>
                  </div>
                  <div className="mb-1 text-cmd-text">{report.narrative}</div>
                  <DataRow label="Employee" value={AGENT_PROFILES[report.agentId].name} />
                  <DataRow label="Trait" value={`${report.traitName} — ${report.currentScore.toFixed(0)}/100 (${report.sampleSize} data point${report.sampleSize === 1 ? "" : "s"})`} />
                  {report.evidence.length > 0 && (
                    <ul className="mt-1 list-inside list-disc text-cmd-textDim">
                      {report.evidence.map((e, i) => (
                        <li key={i}>{e}</li>
                      ))}
                    </ul>
                  )}
                  <div className="mt-1 border-t border-cmd-border/50 pt-1">
                    <DataRow label="Suggested Focus" value={report.suggestedFocus} />
                    <DataRow label="Expected Benefit" value={report.expectedBenefits} />
                  </div>
                  {!seen && (
                    <button
                      type="button"
                      onClick={() => void ackReport(report.id)}
                      disabled={acking === report.id}
                      className="mt-1.5 rounded-sm border border-cmd-cyan/50 px-2 py-0.5 text-[9px] uppercase tracking-wider text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40"
                    >
                      {acking === report.id ? "Acknowledging…" : "Acknowledge"}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Glass>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Glass className="p-3">
          <TerminalLabel>Growth History</TerminalLabel>
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value as AgentId)}
            className="mt-1.5 mb-2 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          >
            {AGENT_IDS.map((id) => (
              <option key={id} value={id}>
                {AGENT_PROFILES[id].name}
              </option>
            ))}
          </select>
          {growthHistory.length === 0 ? (
            <EmptyState>No real participation records for this employee yet.</EmptyState>
          ) : (
            <div className="max-h-72 space-y-1.5 overflow-y-auto">
              {growthHistory.map((entry, i) => (
                <div key={i} className="border-b border-cmd-border/40 pb-1 text-[9px] last:border-0">
                  <div className="flex items-center justify-between">
                    <span className="text-cmd-cyan">{entry.label}</span>
                    {entry.simDay !== null && <span className="text-cmd-textDim">Day {entry.simDay}</span>}
                  </div>
                  <div className="text-cmd-textDim">{entry.detail}</div>
                </div>
              ))}
            </div>
          )}
        </Glass>

        <Glass className="p-3">
          <TerminalLabel>Best Collaborators</TerminalLabel>
          <p className="mb-2 text-[9px] text-cmd-textDim">
            The roster is fixed — nothing about team composition can be optimized. This is the one real signal left: who actually supports vs. challenges whom across every AI
            Debate on record.
          </p>
          {collaborators.length === 0 ? (
            <EmptyState>No debates on record yet.</EmptyState>
          ) : (
            <div className="space-y-1.5">
              {collaborators.map((pair) => (
                <div key={`${pair.agentA}-${pair.agentB}`} className="flex items-center justify-between rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                  <span className="text-cmd-text">
                    {AGENT_PROFILES[pair.agentA].name} &amp; {AGENT_PROFILES[pair.agentB].name}
                  </span>
                  <span className="flex gap-2 tabular-nums">
                    <span className="text-cmd-green">{pair.supportCount} support</span>
                    <span className="text-cmd-red">{pair.challengeCount} challenge</span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </Glass>
      </div>

      <Glass className="p-3">
        <TerminalLabel>Performance Analysis — Thinking Profiles</TerminalLabel>
        <p className="mb-2 text-[9px] text-cmd-textDim">
          Reused directly from the Mentor tab&apos;s real ThinkingProfile computation — nothing new here, just surfaced where the talent brief expects it.
        </p>
        {profiles.length === 0 ? (
          <EmptyState>No profiles computed yet.</EmptyState>
        ) : (
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {profiles.map((profile) => (
              <div key={profile.agentId} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                <div className="mb-1.5 text-cmd-cyan">{AGENT_PROFILES[profile.agentId].name}</div>
                <div className="space-y-1">
                  {profile.traits.map((trait) => (
                    <div key={trait.id}>
                      <div className="flex items-center justify-between">
                        <span className="text-cmd-text">{trait.name}</span>
                        <span className="tabular-nums text-cmd-textDim">{trait.score.toFixed(0)}</span>
                      </div>
                      <Meter value={trait.score} tone={trait.score >= 70 ? "green" : trait.score >= 40 ? "amber" : "red"} />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}
