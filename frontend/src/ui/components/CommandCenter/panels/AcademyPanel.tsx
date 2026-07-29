import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { careerLevelLabel, companyMajor } from "@/game/systems/careerLevels";
import type { AgentKnowledgeState } from "@/types";
import { KnowledgeGraphView } from "../KnowledgeGraphView";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

function tierTone(tier: number): "cyan" | "green" {
  return tier >= 3 ? "green" : "cyan";
}

/**
 * v0.7 Feature 25 — the AI Academy & Knowledge Network. Every number here
 * is real: agentKnowledge/academyState are recomputed server-side every
 * tick from actually-completed work (see backend/app/academy.py's module
 * docstring for exactly which real signal feeds which number, including
 * its honest scope note on why "mentorship" here is grounded in real
 * knowledge points rather than a fabricated seniority system).
 * academyProjects/academyCompletedProjects together are the Company
 * Knowledge Library — the active project plus its permanent, growing
 * archive (see backend/app/academy_research.py).
 */
export function AcademyPanel() {
  const { academyState, agentKnowledge, academyProjects, academyCompletedProjects, memory, executiveReviews } = useGameStore();
  const activeProject = academyProjects[0];
  const knowledgeStates = Object.values(agentKnowledge) as AgentKnowledgeState[];
  const rankedKnowledge = [...knowledgeStates].sort((a, b) => b.points - a.points);
  const mentorshipMemories = [...memory].filter((m) => m.category === "mentorship").reverse().slice(0, 5);
  const [showGraph, setShowGraph] = useState(false);
  const latestReview = executiveReviews[executiveReviews.length - 1];
  const knowledgeConnections = latestReview?.knowledgeConnections ?? [];

  return (
    <div className="relative grid grid-cols-1 gap-3 lg:grid-cols-3">
      <Glass className="p-3 lg:col-span-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Academy Progression</TerminalLabel>
          <StatusPill tone="cyan">
            LEVEL {academyState.level} — {academyState.levelLabel.toUpperCase()}
          </StatusPill>
        </div>
        <Meter value={(academyState.level / 5) * 100} tone="cyan" />
        <div className="mt-2 flex justify-between text-[9px] text-cmd-textDim">
          <span>{academyState.totalPoints.toFixed(0)} total knowledge points across the team</span>
          <span>{academyState.completedProjectCount} projects completed</span>
        </div>
      </Glass>

      <Glass className="p-3 lg:col-span-3">
        <div className="flex items-center justify-between">
          <div>
            <TerminalLabel>Company Knowledge Graph</TerminalLabel>
            <div className="text-[9px] text-cmd-textDim">Explore every discovery, project, and report as one connected network.</div>
          </div>
          <button
            type="button"
            onClick={() => setShowGraph(true)}
            className="flex-none rounded-sm border border-cmd-cyan/50 px-3 py-1.5 text-[10px] uppercase tracking-wider text-cmd-cyan shadow-cmd-cyan transition-colors hover:bg-cmd-cyan/10"
          >
            Open Knowledge Graph ▸
          </button>
        </div>
        {knowledgeConnections.length > 0 && (
          <div className="mt-2 space-y-1 border-t border-cmd-border/50 pt-2">
            {knowledgeConnections.slice(0, 3).map((line, i) => (
              <div key={i} className="text-[9px] italic text-cmd-textDim">
                “{line}”
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3 lg:col-span-2">
        <TerminalLabel>Knowledge Trees</TerminalLabel>
        <div className="mt-1.5 space-y-1.5">
          {rankedKnowledge.map((state) => {
            const major = companyMajor(state);
            return (
              <div key={state.agentId} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="flex items-center gap-2">
                  <span className="w-16 flex-none truncate text-cmd-cyan">{AGENT_PROFILES[state.agentId].name}</span>
                  <span className="w-28 flex-none truncate text-cmd-textDim">{state.branch}</span>
                  <div className="flex-1">
                    <Meter value={Math.min(100, (state.points / 30) * 100)} tone={tierTone(state.tier)} />
                  </div>
                  <span className="w-10 flex-none text-right tabular-nums text-cmd-textDim">{state.points.toFixed(0)}p</span>
                  <StatusPill tone={tierTone(state.tier)}>{state.level}</StatusPill>
                </div>
                {/* v0.7 Feature 40 — Career Level relabels the same real
                    tier academy.py already tracks; Company Major only
                    appears once that tier has actually sustained a real
                    specialization (see careerLevels.ts), an honest empty
                    state rather than a fabricated major from day one. */}
                <div className="mt-1 pl-[4.75rem] text-cmd-textDim">
                  Career Level: <span className="text-cmd-text">{careerLevelLabel(state.level)}</span>
                  {major && (
                    <>
                      {" · "}
                      {major}
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Active Research Project</TerminalLabel>
        {!activeProject ? (
          <EmptyState>No project currently active.</EmptyState>
        ) : (
          <>
            <div className="mb-1 text-cmd-cyan">{activeProject.title}</div>
            <div className="mb-2 text-[9px] text-cmd-textDim">{activeProject.summary}</div>
            <Meter value={activeProject.progress} tone="cyan" />
            <div className="mt-1 flex justify-between text-[9px] text-cmd-textDim">
              <span>{AGENT_PROFILES[activeProject.assignedAgent].name}</span>
              <span>{activeProject.progress.toFixed(0)}%</span>
            </div>
          </>
        )}
      </Glass>

      <Glass className="p-3 lg:col-span-2">
        <TerminalLabel>Company Knowledge Library</TerminalLabel>
        {academyCompletedProjects.length === 0 ? (
          <EmptyState>No completed projects yet — the library grows as the Academy finishes its research.</EmptyState>
        ) : (
          <div className="max-h-56 space-y-1 overflow-y-auto">
            {[...academyCompletedProjects].reverse().map((project) => (
              <div key={project.id} className="flex items-center justify-between gap-2 border-b border-cmd-border/40 py-1 text-[9px] last:border-0">
                <span className="flex-1 truncate text-cmd-text">{project.title}</span>
                <span className="flex-none text-cmd-textDim">{AGENT_PROFILES[project.assignedAgent].name}</span>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Recent Mentorship</TerminalLabel>
        {mentorshipMemories.length === 0 ? (
          <EmptyState>No mentorship sessions recorded yet — they start once a real knowledge gap opens between two agents.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {mentorshipMemories.map((m) => (
              <div key={m.id} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="mb-0.5 text-cmd-cyan">{m.title}</div>
                <div className="text-cmd-textDim">{m.body}</div>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3 lg:col-span-3">
        <TerminalLabel>Company Objectives</TerminalLabel>
        <DataRow label="Current Academy Level" value={`${academyState.level} / 5`} />
        <DataRow label="Next Milestone" value={academyState.level < 5 ? "Advance the Academy toward its next tier" : "Executive Institute reached"} />
      </Glass>

      {showGraph && <KnowledgeGraphView onClose={() => setShowGraph(false)} />}
    </div>
  );
}
