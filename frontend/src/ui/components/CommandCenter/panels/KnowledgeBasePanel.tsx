import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import type { InstitutionalMemorySource, InstitutionalMemoryStatus } from "@/types";
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

const MEMORY_SOURCE_LABEL: Record<InstitutionalMemorySource, string> = {
  behavioral_mistake: "Behavioral Mistake",
  behavioral_success: "Behavioral Success",
  strategy_failure: "Strategy Failure",
  strategy_success: "Strategy Success",
  model_validation: "Model Validation",
  risk_event: "Risk Event",
  market_regime_shift: "Regime Shift",
  prediction: "Prediction Outcome",
  failure_classification: "Failure Classification",
  // "TradeTown — Learning Organization 1.0" — bridged from a real ResearchLessonRecord.
  research_lesson: "Research Lesson",
};

const MEMORY_SOURCE_TONE: Record<InstitutionalMemorySource, "cyan" | "green" | "amber" | "purple" | "red"> = {
  behavioral_mistake: "red",
  behavioral_success: "green",
  strategy_failure: "amber",
  strategy_success: "cyan",
  model_validation: "purple",
  risk_event: "red",
  market_regime_shift: "cyan",
  prediction: "amber",
  failure_classification: "red",
  research_lesson: "purple",
};

const MEMORY_STATUS_TONE: Record<InstitutionalMemoryStatus, "neutral" | "cyan" | "amber" | "red"> = {
  active: "cyan",
  superseded: "amber",
  contradicted: "red",
  stale: "neutral",
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
  const { caseStudies, strategyReports, constitution, coachReports, academyProjects, reflectionSessions, institutionalMemory, knowledgeEvents } = useGameStore();
  const [sourceFilter, setSourceFilter] = useState<KnowledgeBaseSource | "all">("all");
  const [memorySourceFilter, setMemorySourceFilter] = useState<InstitutionalMemorySource | "all">("all");

  // "TradeTown — Knowledge Application Loop 1.0" — real per-memory
  // application counts, grouped once from the same real knowledgeEvents
  // list already broadcast in full (never a second fetch/derivation
  // pipeline). Only "knowledge_applied" events carry a graded outcome;
  // every other event type is irrelevant here.
  const applicationsByMemoryId = useMemo(() => {
    const byId = new Map<string, { supported: number; contradicted: number; pending: number }>();
    for (const event of knowledgeEvents) {
      if (event.type !== "knowledge_applied") continue;
      const counts = byId.get(event.lessonId) ?? { supported: 0, contradicted: 0, pending: 0 };
      if (event.applicationStatus === "evaluated" && event.outcome === "supported") counts.supported += 1;
      else if (event.applicationStatus === "evaluated" && event.outcome === "contradicted") counts.contradicted += 1;
      else counts.pending += 1;
      byId.set(event.lessonId, counts);
    }
    return byId;
  }, [knowledgeEvents]);

  const sortedMemory = useMemo(
    () => [...institutionalMemory].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()),
    [institutionalMemory],
  );
  const filteredMemory = useMemo(
    () => sortedMemory.filter((m) => memorySourceFilter === "all" || m.source === memorySourceFilter),
    [sortedMemory, memorySourceFilter],
  );

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

      <Glass className="max-h-[30rem] overflow-y-auto p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Institutional Memory — promoted lessons</TerminalLabel>
          <select
            value={memorySourceFilter}
            onChange={(e) => setMemorySourceFilter(e.target.value as InstitutionalMemorySource | "all")}
            className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-0.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          >
            <option value="all">Every source</option>
            {(Object.keys(MEMORY_SOURCE_LABEL) as InstitutionalMemorySource[]).map((source) => (
              <option key={source} value={source}>
                {MEMORY_SOURCE_LABEL[source]}
              </option>
            ))}
          </select>
        </div>
        <p className="mb-2 text-[9px] text-cmd-textDim">
          Real observation/interpretation/lesson promoted from a filed case study, strategy retirement, Model Validation finding, critical risk
          warning, or market regime shift — never a raw copy of the event log. Confidence and relevance are recomputed fresh, never trusted stale.
          A superseded/contradicted entry is kept, not deleted — see its link to what replaced it.
        </p>
        {filteredMemory.length === 0 ? (
          <EmptyState>No institutional memory filed yet — lessons appear as real company events happen.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {filteredMemory.map((entry) => (
              <div
                key={entry.id}
                data-testid="institutional-memory-entry"
                className={`rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px] ${entry.status !== "active" ? "opacity-60" : ""}`}
              >
                <div className="mb-0.5 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <StatusPill tone={MEMORY_SOURCE_TONE[entry.source]}>{MEMORY_SOURCE_LABEL[entry.source]}</StatusPill>
                    {entry.status !== "active" && <StatusPill tone={MEMORY_STATUS_TONE[entry.status]}>{entry.status}</StatusPill>}
                  </div>
                  <span className="text-cmd-textDim/70">
                    confidence {entry.confidence.toFixed(0)}% · relevance {entry.relevancePct.toFixed(0)}%
                  </span>
                </div>
                <div className="text-cmd-text">{entry.observation}</div>
                {entry.interpretation && <div className="mt-0.5 text-cmd-textDim">Interpretation: {entry.interpretation}</div>}
                {entry.lesson && <div className="mt-0.5 text-cmd-cyan">Lesson: {entry.lesson}</div>}
                {applicationsByMemoryId.has(entry.id) && (
                  <div className="mt-0.5 text-cmd-textDim/80">
                    Applied {(() => {
                      const c = applicationsByMemoryId.get(entry.id)!;
                      const parts: string[] = [];
                      if (c.supported) parts.push(`${c.supported} supported`);
                      if (c.contradicted) parts.push(`${c.contradicted} contradicted`);
                      if (c.pending) parts.push(`${c.pending} pending`);
                      return parts.join(" · ");
                    })()}
                  </div>
                )}
                <div className="mt-1 text-cmd-textDim/70">
                  {entry.originatingAgent ? `${AGENT_PROFILES[entry.originatingAgent].name} — ` : ""}
                  {new Date(entry.createdAt).toLocaleString()}
                </div>
                <div className="mt-0.5 text-cmd-textDim/60 italic">{entry.provenance}</div>
              </div>
            ))}
          </div>
        )}
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
