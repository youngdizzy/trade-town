import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { computeKnowledgeBase, KNOWLEDGE_BASE_SOURCE_LABEL, type KnowledgeBaseSource } from "../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

const SOURCE_TONE: Record<KnowledgeBaseSource, "cyan" | "green" | "amber" | "purple" | "red"> = {
  case_study: "amber",
  strategy_report: "cyan",
  constitution_citation: "purple",
  coach_recommendation: "green",
  academy_project: "cyan",
  reflection_insight: "purple",
};

/**
 * v0.7 Feature 47 — the Company Operating System's "Knowledge
 * Absorption." A pure, zero-new-backend-data aggregation (see
 * lib/derive.ts's computeKnowledgeBase) of six already-real, already-
 * persisted learning records into one chronological, filterable feed —
 * the single place the brief asks for where "everything the company
 * learns" is visible. Distinct from the existing Knowledge Graph tab's
 * relational node/edge view.
 */
export function KnowledgeBasePanel() {
  const { caseStudies, strategyReports, constitution, coachReports, academyProjects, reflectionSessions } = useGameStore();
  const [sourceFilter, setSourceFilter] = useState<KnowledgeBaseSource | "all">("all");

  const entries = useMemo(
    () =>
      computeKnowledgeBase({
        caseStudies,
        strategyReports,
        constitutionCitations: constitution.citations,
        coachReports,
        academyProjects,
        reflectionSessions,
      }),
    [caseStudies, strategyReports, constitution.citations, coachReports, academyProjects, reflectionSessions],
  );

  const filtered = useMemo(() => entries.filter((e) => sourceFilter === "all" || e.source === sourceFilter), [entries, sourceFilter]);

  const sourceCounts = useMemo(() => {
    const counts: Record<KnowledgeBaseSource, number> = {
      case_study: 0,
      strategy_report: 0,
      constitution_citation: 0,
      coach_recommendation: 0,
      academy_project: 0,
      reflection_insight: 0,
    };
    for (const e of entries) counts[e.source] += 1;
    return counts;
  }, [entries]);

  return (
    <div className="grid grid-cols-1 gap-3">
      <Glass className="p-3">
        <TerminalLabel>Knowledge Base — everything the company has learned</TerminalLabel>
        <p className="mb-2 text-[9px] text-cmd-textDim">
          Six real sources feeding one timeline: the Library of Mistakes, Research Sandbox reports, Constitution citations, Coach recommendations, completed Academy projects, and
          Reflection Chamber insights. Nothing here is generated — every row links back to a real, already-persisted record.
        </p>
        <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3 lg:grid-cols-6">
          {(Object.keys(KNOWLEDGE_BASE_SOURCE_LABEL) as KnowledgeBaseSource[]).map((source) => (
            <DataRow key={source} label={KNOWLEDGE_BASE_SOURCE_LABEL[source]} value={sourceCounts[source]} />
          ))}
        </div>
      </Glass>

      <Glass className="max-h-[36rem] overflow-y-auto p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Timeline</TerminalLabel>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value as KnowledgeBaseSource | "all")}
            className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-0.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          >
            <option value="all">Every source</option>
            {(Object.keys(KNOWLEDGE_BASE_SOURCE_LABEL) as KnowledgeBaseSource[]).map((source) => (
              <option key={source} value={source}>
                {KNOWLEDGE_BASE_SOURCE_LABEL[source]}
              </option>
            ))}
          </select>
        </div>
        {filtered.length === 0 ? (
          <EmptyState>Nothing filed yet — entries appear as real company events happen.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {filtered.map((entry) => (
              <div key={entry.id} data-testid="knowledge-base-entry" className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                <div className="mb-0.5 flex items-center justify-between gap-2">
                  <span className="text-cmd-text">{entry.title}</span>
                  <StatusPill tone={SOURCE_TONE[entry.source]}>{KNOWLEDGE_BASE_SOURCE_LABEL[entry.source]}</StatusPill>
                </div>
                <div className="text-cmd-textDim">{entry.detail}</div>
                <div className="mt-1 text-cmd-textDim/70">
                  {entry.agentId ? `${AGENT_PROFILES[entry.agentId].name} — ` : ""}
                  {new Date(entry.createdAt).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}
