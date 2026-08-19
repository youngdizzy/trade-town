import { useEffect, useMemo, useState } from "react";
import { api } from "@/net/api";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import {
  AGENT_IDS,
  type AgentId,
  type AlertSeverity,
  type AuditEntry,
  type AuditEventCategory,
  type CeoOverrideEvaluation,
  type CeoOverrideGovernanceSummary,
  type CeoOverrideRecord,
  type ComplianceIncident,
  type ComplianceIncidentSummary,
  type ComplianceOverview,
  type ContinuousImprovementSummary,
  type ControlEffectivenessRecord,
  type ControlEffectivenessSummary,
  type GatekeeperControlEffectivenessState,
  type GovernanceLayer,
  type IncidentRootCause,
  type IncidentStatus,
  type OverrideProcessQuality,
  type RemediationEffectivenessRecord,
  type RemediationEffectivenessState,
  type RootCauseRecurrence,
} from "@/types";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

/**
 * Design Bible Chapter 73 — Compliance, Audit & Governance System (CAGS)
 * (backend/app/audit_log.py). Unlike every other Command Center panel,
 * CAGS has no WS-broadcast fields and is not part of gameStore — every
 * section below is a genuine on-demand fetch via app/net/api.ts against
 * GET /api/audit/*. Nothing here is client-side derived: the Audit Log,
 * Incidents, Governance chain, Compliance Score, and CEO Override list
 * are all computed server-side from real, already-persisted records
 * (CEO decisions, Gatekeeper/Opportunity rejections, critical risk
 * warnings, weak/reckless discipline reviews, Emergency Stop / Crisis
 * Briefing memory records, Black Swan defensive-mode events, and a live
 * read of the Institutional Rule Engine). There is still no per-event
 * Broker/User/Software-Version field and no Institutional Time Machine
 * state-replay (see the Design Bible chapter's own Implementation Notes
 * for the full cut list).
 *
 * CEO directive "Features 31-35," Feature 31 adds the one real exception
 * to "no mutable Incident workflow" above: the Incident Cases tab is
 * backed by GET/POST /api/audit/incidents/* (backend/app/compliance_incidents.py)
 * — a genuinely persisted, mutable lifecycle (open -> investigating ->
 * remediation -> awaiting_verification -> resolved -> reopened), still
 * fetched on demand rather than riding the WS tick broadcast. The
 * original Incidents tab above it is untouched: a different, still
 * fully ephemeral view of the same underlying Audit Log.
 *
 * Feature 32 adds the Override Governance tab — real, persisted
 * CeoOverrideEvaluations (backend/app/override_governance.py), still
 * fetched on demand. Distinct from the original CEO Overrides tab above
 * (still the ephemeral CeoOverrideRecord list): this tab adds real
 * PROCESS QUALITY evidence (was the override justified given evidence
 * at decision time) alongside — never merged with — the real OUTCOME
 * (mirrored from CeoDecisionRecord.outcome, never re-derived), per the
 * directive's explicit "no hindsight-only evaluation" rule.
 *
 * Feature 34 adds the Control Effectiveness tab — a genuinely new
 * question CAGS never answered before: did each real Gatekeeper check
 * (backend/app/gatekeeper.py) actually prevent or detect what it was
 * designed to address, not just how often it exists/fires. Read-only,
 * computed fresh per request (backend/app/control_effectiveness.py) —
 * no new persisted state, same on-demand pattern as every CAGS tab
 * above it.
 *
 * Feature 35 adds the Continuous Improvement tab — closes the loop:
 * did a real remediation (Feature 31's own recorded correctiveAction)
 * actually hold, and is any real root cause recurring across the
 * incident backlog (backend/app/continuous_improvement.py). Also
 * connects real evidence into Company Health's own existing
 * architecture as a new complianceHealth Executive-tier dimension —
 * never a rewrite of the separate Compliance Score above, which stays
 * untouched pending explicit CEO authorization to change it.
 */

const TABS = ["log", "incidents", "cases", "governance", "overrides", "overrideGovernance", "controlEffectiveness", "continuousImprovement"] as const;
type Tab = (typeof TABS)[number];

const TAB_LABEL: Record<Tab, string> = {
  log: "Audit Log",
  incidents: "Incidents",
  cases: "Incident Cases",
  governance: "Governance",
  overrides: "CEO Overrides",
  overrideGovernance: "Override Governance",
  controlEffectiveness: "Control Effectiveness",
  continuousImprovement: "Continuous Improvement",
};

const PROCESS_QUALITY_LABEL: Record<OverrideProcessQuality, string> = {
  justified: "Justified",
  unjustified: "Unjustified",
  mixed: "Mixed Evidence",
  not_enough_evidence: "Not Enough Evidence",
};

function processQualityTone(quality: OverrideProcessQuality): "red" | "amber" | "cyan" | "green" {
  if (quality === "justified") return "green";
  if (quality === "unjustified") return "red";
  if (quality === "mixed") return "amber";
  return "cyan";
}

const INCIDENT_STATUS_LABEL: Record<IncidentStatus, string> = {
  open: "Open",
  investigating: "Investigating",
  remediation: "Remediation",
  awaiting_verification: "Awaiting Verification",
  resolved: "Resolved",
  reopened: "Reopened",
};

const ROOT_CAUSE_LABEL: Record<IncidentRootCause, string> = {
  process_failure: "Process Failure",
  control_failure: "Control Failure",
  data_failure: "Data Failure",
  model_failure: "Model Failure",
  human_error: "Human Error",
  governance_failure: "Governance Failure",
  communication_failure: "Communication Failure",
  unknown: "Unknown (Root Cause Not Established)",
};

function incidentStatusTone(status: IncidentStatus): "red" | "amber" | "cyan" | "green" {
  if (status === "resolved") return "green";
  if (status === "reopened") return "red";
  if (status === "open") return "amber";
  if (status === "awaiting_verification") return "amber";
  return "cyan";
}

const CATEGORY_OPTIONS: { value: AuditEventCategory | "all"; label: string }[] = [
  { value: "all", label: "All Categories" },
  { value: "ceo_decision", label: "CEO Decision" },
  { value: "gatekeeper_rejection", label: "Gatekeeper Rejection" },
  { value: "opportunity_rejection", label: "Opportunity Rejection" },
  { value: "risk_warning", label: "Risk Warning" },
  { value: "discipline_review", label: "Discipline Review" },
  { value: "emergency_stop", label: "Emergency Stop" },
  { value: "defensive_mode", label: "Defensive Mode" },
  { value: "crisis_briefing", label: "Crisis Briefing" },
  { value: "rule_violation", label: "Rule Violation" },
];

const SEVERITY_OPTIONS: { value: AlertSeverity | "all"; label: string }[] = [
  { value: "all", label: "Any Severity" },
  { value: "critical", label: "Critical" },
  { value: "warning", label: "Warning" },
  { value: "info", label: "Info" },
];

function severityTone(severity: AlertSeverity): "red" | "amber" | "cyan" {
  if (severity === "critical") return "red";
  if (severity === "warning") return "amber";
  return "cyan";
}

function severityTextClass(severity: AlertSeverity): string {
  if (severity === "critical") return "text-cmd-red";
  if (severity === "warning") return "text-cmd-amber";
  return "text-cmd-textDim";
}

function outcomeTone(outcome: CeoOverrideRecord["outcome"]): "green" | "red" | "amber" | "neutral" {
  if (outcome === "correct") return "green";
  if (outcome === "incorrect") return "red";
  if (outcome === "pending") return "amber";
  return "neutral";
}

export function CompliancePanel() {
  const [tab, setTab] = useState<Tab>("log");
  const [overview, setOverview] = useState<ComplianceOverview | null>(null);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getComplianceOverview()
      .then((res) => {
        if (!cancelled) setOverview(res);
      })
      .catch((err: unknown) => {
        if (!cancelled) setOverviewError(err instanceof Error ? err.message : "Failed to load compliance overview.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-3">
      <OverviewCard overview={overview} error={overviewError} />

      <Glass className="p-3">
        <div className="mb-2 flex flex-wrap gap-1.5">
          {TABS.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`rounded-sm border px-2.5 py-1 text-[9px] uppercase tracking-wide ${
                tab === t ? "border-cmd-cyan/60 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
              }`}
            >
              {TAB_LABEL[t]}
            </button>
          ))}
        </div>

        {tab === "log" && <AuditLogTab />}
        {tab === "incidents" && <IncidentsTab />}
        {tab === "cases" && <CasesTab />}
        {tab === "governance" && <GovernanceTab />}
        {tab === "overrides" && <OverridesTab />}
        {tab === "overrideGovernance" && <OverrideGovernanceTab />}
        {tab === "controlEffectiveness" && <ControlEffectivenessTab />}
        {tab === "continuousImprovement" && <ContinuousImprovementTab />}
      </Glass>
    </div>
  );
}

function OverviewCard({ overview, error }: { overview: ComplianceOverview | null; error: string | null }) {
  if (error) {
    return (
      <Glass className="p-3">
        <TerminalLabel>Compliance Overview</TerminalLabel>
        <EmptyState>{error}</EmptyState>
      </Glass>
    );
  }
  if (!overview) {
    return (
      <Glass className="p-3">
        <TerminalLabel>Compliance Overview</TerminalLabel>
        <EmptyState>Loading…</EmptyState>
      </Glass>
    );
  }
  const scoreTone = overview.complianceScore >= 80 ? "green" : overview.complianceScore >= 60 ? "amber" : "red";
  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Compliance Overview</TerminalLabel>
        <div className="flex items-center gap-1.5">
          {overview.emergencyStopActive && <StatusPill tone="red">Emergency Stop Active</StatusPill>}
          {overview.defensiveModeActive && <StatusPill tone="amber">Defensive Mode Active</StatusPill>}
        </div>
      </div>
      <div className="mb-2 flex items-center gap-3">
        <span className="font-cmdmono text-cmd-cyan">{overview.complianceScore.toFixed(1)}/100</span>
        <div className="flex-1">
          <Meter value={overview.complianceScore} tone={scoreTone} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-4">
        <DataRow label="Open Incidents" value={overview.openIncidentCount} valueClassName={overview.openIncidentCount > 0 ? "text-cmd-amber" : "text-cmd-text"} />
        <DataRow label="Critical" value={overview.criticalIncidentCount} valueClassName={overview.criticalIncidentCount > 0 ? "text-cmd-red" : "text-cmd-text"} />
        <DataRow label="Audit Entries" value={overview.totalAuditEntries} />
        <DataRow label="CEO Overrides" value={`${overview.ceoOverrideCount} (${overview.ceoOverrideRatePct.toFixed(1)}%)`} />
      </div>
      {overview.executiveAccuracy.length > 0 && (
        <div className="mt-2 border-t border-cmd-border/50 pt-2">
          <TerminalLabel>Executive Accuracy — reused from Chapter 70 Part 2, evidence states from Feature 33</TerminalLabel>
          <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
            {overview.executiveAccuracy.map((a) => (
              <div key={a.role} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="text-cmd-textDim">{a.departmentLabel}</div>
                <div className={a.evaluationState === "not_enough_evidence" ? "text-cmd-textDim tabular-nums" : "text-cmd-text tabular-nums"}>
                  {a.accuracyPct === null ? "NOT ENOUGH EVIDENCE" : `${a.accuracyPct.toFixed(0)}%`} <span className="text-cmd-textDim">({a.decisionsTracked})</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="mt-1.5 text-right text-[9px] text-cmd-textDim">Updated {new Date(overview.updatedAt).toLocaleTimeString()}</div>
    </Glass>
  );
}

function AuditLogTab() {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState<AuditEventCategory | "all">("all");
  const [severity, setSeverity] = useState<AlertSeverity | "all">("all");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");

  useEffect(() => {
    const handle = setTimeout(() => setSearch(searchInput.trim()), 300);
    return () => clearTimeout(handle);
  }, [searchInput]);

  useEffect(() => {
    let cancelled = false;
    api
      .getAuditLog({
        category: category === "all" ? undefined : category,
        severity: severity === "all" ? undefined : severity,
        search: search || undefined,
        limit: 200,
      })
      .then((res) => {
        if (!cancelled) setEntries(res);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load audit log.");
      });
    return () => {
      cancelled = true;
    };
  }, [category, severity, search]);

  return (
    <div>
      <div className="mb-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as AuditEventCategory | "all")}
          className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
        >
          {CATEGORY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value as AlertSeverity | "all")}
          className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
        >
          {SEVERITY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search summary, detail, department…"
          className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
        />
      </div>
      <AuditEntryTable entries={entries} error={error} emptyText="No audit entries match these filters." />
    </div>
  );
}

function IncidentsTab() {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getAuditIncidents()
      .then((res) => {
        if (!cancelled) setEntries(res);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load incidents.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <p className="mb-2 text-[9px] text-cmd-textDim">
        Every Audit Log entry with `warning` or `critical` severity — a pure filter over the same list, never a separately-tracked incident record. There is no
        open/acknowledged/resolved workflow: incident *resolution* is not a real mechanic anywhere in this codebase today.
      </p>
      <AuditEntryTable entries={entries} error={error} emptyText="No open incidents." />
    </div>
  );
}

function CasesTab() {
  const [cases, setCases] = useState<ComplianceIncident[] | null>(null);
  const [summary, setSummary] = useState<ComplianceIncidentSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = () => {
    api
      .getComplianceIncidentCases()
      .then((res) => setCases(res))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load incident cases."));
    api.getComplianceIncidentSummary().then((res) => setSummary(res)).catch(() => undefined);
  };

  useEffect(() => {
    load();
  }, []);

  const sorted = useMemo(() => {
    if (!cases) return null;
    const order: Record<IncidentStatus, number> = { open: 0, reopened: 1, investigating: 2, remediation: 3, awaiting_verification: 4, resolved: 5 };
    return [...cases].sort((a, b) => order[a.status] - order[b.status] || b.simDay - a.simDay);
  }, [cases]);

  const handleUpdated = (updated: ComplianceIncident) => {
    setCases((prev) => (prev ? prev.map((c) => (c.id === updated.id ? updated : c)) : prev));
    api.getComplianceIncidentSummary().then((res) => setSummary(res)).catch(() => undefined);
  };

  return (
    <div>
      <p className="mb-2 text-[9px] text-cmd-textDim">
        The real, persisted incident lifecycle — every case here is opened from a real Audit Log entry (never a second detection mechanism) and only advances through the enforced
        stages below. There is no way to mark an incident RESOLVED without first passing through investigation, remediation, and verification.
      </p>
      <SummaryStrip summary={summary} />
      {error && <EmptyState>{error}</EmptyState>}
      {!error && !sorted && <EmptyState>Loading…</EmptyState>}
      {!error && sorted && sorted.length === 0 && <EmptyState>No incident cases yet.</EmptyState>}
      {!error && sorted && sorted.length > 0 && (
        <div className="max-h-[28rem] space-y-1 overflow-y-auto">
          {sorted.map((c) => (
            <CaseRow key={c.id} incident={c} expanded={expandedId === c.id} onToggle={() => setExpandedId((v) => (v === c.id ? null : c.id))} onUpdated={handleUpdated} />
          ))}
        </div>
      )}
    </div>
  );
}

function SummaryStrip({ summary }: { summary: ComplianceIncidentSummary | null }) {
  if (!summary) return null;
  return (
    <div className="mb-2 grid grid-cols-2 gap-x-4 gap-y-1 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 sm:grid-cols-4">
      <DataRow label="Total Cases" value={summary.totalCount} />
      <DataRow label="Open" value={summary.openCount} valueClassName={summary.openCount > 0 ? "text-cmd-amber" : "text-cmd-text"} />
      <DataRow label="Resolved" value={summary.resolvedCount} valueClassName="text-cmd-green" />
      <DataRow label="Overdue" value={summary.overdueCount} valueClassName={summary.overdueCount > 0 ? "text-cmd-red" : "text-cmd-text"} />
      <DataRow label="Reopened" value={summary.reopenedIncidentCount} />
      <DataRow label="Severity-Weighted Backlog" value={summary.severityWeightedBacklog} />
      <DataRow
        label="Avg Resolution (sim days)"
        value={summary.averageResolutionSimDays === null ? "NOT ENOUGH EVIDENCE" : summary.averageResolutionSimDays.toFixed(1)}
        valueClassName={summary.averageResolutionSimDays === null ? "text-cmd-textDim" : "text-cmd-text"}
      />
    </div>
  );
}

function CaseRow({
  incident,
  expanded,
  onToggle,
  onUpdated,
}: {
  incident: ComplianceIncident;
  expanded: boolean;
  onToggle: () => void;
  onUpdated: (updated: ComplianceIncident) => void;
}) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40">
      <div onClick={onToggle} className="flex cursor-pointer items-center gap-2 px-2 py-1.5 hover:bg-cmd-panelLight/60">
        <StatusPill tone={incidentStatusTone(incident.status)}>{INCIDENT_STATUS_LABEL[incident.status]}</StatusPill>
        <StatusPill tone={severityTone(incident.severity)}>{incident.severity}</StatusPill>
        <span className="text-cmd-cyan text-[9px]">{incident.department}</span>
        <span className={`flex-1 truncate text-[9px] ${severityTextClass(incident.severity)}`}>{incident.summary}</span>
        {incident.reopenedCount > 0 && <span className="text-[9px] text-cmd-red">reopened ×{incident.reopenedCount}</span>}
        <span className="text-[9px] text-cmd-textDim">Day {incident.simDay}</span>
      </div>
      {expanded && (
        <div className="border-t border-cmd-border/40 px-2 py-2 text-[9px]">
          <div className="mb-1.5 text-cmd-textDim">{incident.detail}</div>
          <div className="mb-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 sm:grid-cols-3">
            <DataRow label="Owner" value={incident.owner ? AGENT_PROFILES[incident.owner].name : "Unassigned"} />
            <DataRow label="Deadline" value={incident.deadlineSimDay === null ? "Not set" : `Day ${incident.deadlineSimDay}`} />
            <DataRow label="Verification" value={incident.verificationStatus.replace("_", " ")} />
            <DataRow label="Root Cause" value={incident.rootCause ? ROOT_CAUSE_LABEL[incident.rootCause] : "Not yet determined"} />
            <DataRow label="Verifier" value={incident.verifier ? AGENT_PROFILES[incident.verifier].name : "—"} />
            <DataRow label="Resolved" value={incident.resolvedAt ? new Date(incident.resolvedAt).toLocaleString() : "Not resolved"} />
          </div>
          {incident.remediationPlan && (
            <div className="mb-1.5">
              <span className="text-cmd-textDim">Remediation plan: </span>
              <span className="text-cmd-text">{incident.remediationPlan}</span>
            </div>
          )}
          {incident.correctiveAction && (
            <div className="mb-1.5">
              <span className="text-cmd-textDim">Corrective action: </span>
              <span className="text-cmd-text">{incident.correctiveAction}</span>
            </div>
          )}
          {incident.evidence.length > 0 && (
            <div className="mb-1.5">
              <div className="text-cmd-textDim">Evidence trail:</div>
              <ul className="list-inside list-disc text-cmd-text">
                {incident.evidence.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}
          <CaseActions incident={incident} onUpdated={onUpdated} />
        </div>
      )}
    </div>
  );
}

function CaseActions({ incident, onUpdated }: { incident: ComplianceIncident; onUpdated: (updated: ComplianceIncident) => void }) {
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [owner, setOwner] = useState<AgentId>("scout");
  const [remediationPlan, setRemediationPlan] = useState("");
  const [deadlineSimDay, setDeadlineSimDay] = useState(incident.simDay + 5);
  const [failNote, setFailNote] = useState("");
  const [reopenNote, setReopenNote] = useState("");
  const [evidenceNote, setEvidenceNote] = useState("");
  const [verifier, setVerifier] = useState<AgentId>("sentinel");
  const [rootCause, setRootCause] = useState<IncidentRootCause>("unknown");
  const [correctiveAction, setCorrectiveAction] = useState("");

  const run = (fn: () => Promise<ComplianceIncident>) => {
    setBusy(true);
    setActionError(null);
    fn()
      .then((updated) => onUpdated(updated))
      .catch((err: unknown) => setActionError(err instanceof Error ? err.message : "Action failed."))
      .finally(() => setBusy(false));
  };

  const selectClass = "rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50";
  const inputClass = selectClass;
  const buttonClass = "rounded-sm border border-cmd-cyan/50 bg-cmd-cyan/10 px-2 py-1 text-[9px] uppercase tracking-wide text-cmd-cyan hover:bg-cmd-cyan/20 disabled:opacity-40";

  return (
    <div className="mt-1.5 space-y-1.5 border-t border-cmd-border/40 pt-1.5">
      {actionError && <div className="text-cmd-red">{actionError}</div>}

      {incident.status === "open" && (
        <div className="flex flex-wrap items-center gap-1.5">
          <select value={owner} onChange={(e) => setOwner(e.target.value as AgentId)} className={selectClass}>
            {AGENT_IDS.map((id) => (
              <option key={id} value={id}>
                {AGENT_PROFILES[id].name}
              </option>
            ))}
          </select>
          <button type="button" disabled={busy} className={buttonClass} onClick={() => run(() => api.startInvestigatingIncident(incident.id, owner))}>
            Start Investigating
          </button>
        </div>
      )}

      {incident.status === "reopened" && (
        <div className="flex flex-wrap items-center gap-1.5">
          <select value={owner} onChange={(e) => setOwner(e.target.value as AgentId)} className={selectClass}>
            {AGENT_IDS.map((id) => (
              <option key={id} value={id}>
                {AGENT_PROFILES[id].name}
              </option>
            ))}
          </select>
          <button type="button" disabled={busy} className={buttonClass} onClick={() => run(() => api.startInvestigatingIncident(incident.id, owner))}>
            Resume Investigating
          </button>
        </div>
      )}

      {incident.status === "investigating" && (
        <div className="space-y-1">
          <textarea
            value={remediationPlan}
            onChange={(e) => setRemediationPlan(e.target.value)}
            placeholder="Real remediation plan…"
            rows={2}
            className={`${inputClass} w-full`}
          />
          <div className="flex flex-wrap items-center gap-1.5">
            <label className="text-cmd-textDim">Deadline (sim day):</label>
            <input
              type="number"
              value={deadlineSimDay}
              onChange={(e) => setDeadlineSimDay(Number(e.target.value))}
              className={`${inputClass} w-20`}
            />
            <button
              type="button"
              disabled={busy || remediationPlan.trim().length === 0}
              className={buttonClass}
              onClick={() => run(() => api.beginIncidentRemediation(incident.id, remediationPlan.trim(), deadlineSimDay))}
            >
              Begin Remediation
            </button>
          </div>
        </div>
      )}

      {incident.status === "remediation" && (
        <div>
          <button type="button" disabled={busy} className={buttonClass} onClick={() => run(() => api.submitIncidentForVerification(incident.id))}>
            Submit For Verification
          </button>
        </div>
      )}

      {incident.status === "awaiting_verification" && (
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <select value={verifier} onChange={(e) => setVerifier(e.target.value as AgentId)} className={selectClass}>
              {AGENT_IDS.map((id) => (
                <option key={id} value={id}>
                  {AGENT_PROFILES[id].name}
                </option>
              ))}
            </select>
            <select value={rootCause} onChange={(e) => setRootCause(e.target.value as IncidentRootCause)} className={selectClass}>
              {(Object.keys(ROOT_CAUSE_LABEL) as IncidentRootCause[]).map((rc) => (
                <option key={rc} value={rc}>
                  {ROOT_CAUSE_LABEL[rc]}
                </option>
              ))}
            </select>
          </div>
          <textarea
            value={correctiveAction}
            onChange={(e) => setCorrectiveAction(e.target.value)}
            placeholder="Real corrective action taken…"
            rows={2}
            className={`${inputClass} w-full`}
          />
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              disabled={busy || correctiveAction.trim().length === 0}
              className={buttonClass}
              onClick={() => run(() => api.verifyAndResolveIncident(incident.id, verifier, rootCause, correctiveAction.trim()))}
            >
              Verify &amp; Resolve
            </button>
            <input
              type="text"
              value={failNote}
              onChange={(e) => setFailNote(e.target.value)}
              placeholder="Why the fix did not hold…"
              className={`${inputClass} flex-1`}
            />
            <button
              type="button"
              disabled={busy || failNote.trim().length === 0}
              className="rounded-sm border border-cmd-red/50 bg-cmd-red/10 px-2 py-1 text-[9px] uppercase tracking-wide text-cmd-red hover:bg-cmd-red/20 disabled:opacity-40"
              onClick={() => run(() => api.failIncidentVerification(incident.id, failNote.trim()))}
            >
              Fail Verification
            </button>
          </div>
        </div>
      )}

      {incident.status === "resolved" && (
        <div className="flex flex-wrap items-center gap-1.5">
          <input
            type="text"
            value={reopenNote}
            onChange={(e) => setReopenNote(e.target.value)}
            placeholder="Same underlying issue recurred…"
            className={`${inputClass} flex-1`}
          />
          <button
            type="button"
            disabled={busy || reopenNote.trim().length === 0}
            className="rounded-sm border border-cmd-red/50 bg-cmd-red/10 px-2 py-1 text-[9px] uppercase tracking-wide text-cmd-red hover:bg-cmd-red/20 disabled:opacity-40"
            onClick={() => run(() => api.reopenIncident(incident.id, reopenNote.trim()))}
          >
            Reopen
          </button>
        </div>
      )}

      <div className="flex items-center gap-1.5">
        <input
          type="text"
          value={evidenceNote}
          onChange={(e) => setEvidenceNote(e.target.value)}
          placeholder="Log real evidence…"
          className={`${inputClass} flex-1`}
        />
        <button
          type="button"
          disabled={busy || evidenceNote.trim().length === 0}
          className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] uppercase tracking-wide text-cmd-textDim hover:text-cmd-text disabled:opacity-40"
          onClick={() => run(() => api.addIncidentEvidence(incident.id, evidenceNote.trim()))}
        >
          Add Evidence
        </button>
      </div>
    </div>
  );
}

function AuditEntryTable({ entries, error, emptyText }: { entries: AuditEntry[] | null; error: string | null; emptyText: string }) {
  if (error) return <EmptyState>{error}</EmptyState>;
  if (!entries) return <EmptyState>Loading…</EmptyState>;
  if (entries.length === 0) return <EmptyState>{emptyText}</EmptyState>;
  return (
    <div className="max-h-96 overflow-y-auto">
      <table className="w-full">
        <thead>
          <tr className="sticky top-0 border-b border-cmd-border bg-cmd-panel text-[9px] uppercase tracking-wide text-cmd-textDim">
            <th className="px-2 py-1.5 text-left">Time</th>
            <th className="px-2 py-1.5 text-left">Severity</th>
            <th className="px-2 py-1.5 text-left">Department</th>
            <th className="px-2 py-1.5 text-left">Summary</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <AuditEntryRow key={e.id} entry={e} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AuditEntryRow({ entry }: { entry: AuditEntry }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <>
      <tr onClick={() => setExpanded((v) => !v)} className="cursor-pointer border-b border-cmd-border/40 last:border-0 hover:bg-cmd-panelLight/60">
        <td className="whitespace-nowrap px-2 py-1.5 text-[9px] text-cmd-textDim">{new Date(entry.timestamp).toLocaleString()}</td>
        <td className="px-2 py-1.5">
          <StatusPill tone={severityTone(entry.severity)}>{entry.severity}</StatusPill>
        </td>
        <td className="px-2 py-1.5 text-cmd-cyan">{entry.department}</td>
        <td className={`px-2 py-1.5 ${severityTextClass(entry.severity)}`}>{entry.summary}</td>
      </tr>
      {expanded && (
        <tr className="border-b border-cmd-border/40 bg-cmd-bg/40 last:border-0">
          <td colSpan={4} className="px-2 py-1.5 text-[9px] text-cmd-textDim">
            {entry.detail}
            {entry.relatedId && <div className="mt-0.5">Related record: {entry.relatedId}</div>}
          </td>
        </tr>
      )}
    </>
  );
}

function GovernanceTab() {
  const [layers, setLayers] = useState<GovernanceLayer[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getGovernance()
      .then((res) => {
        if (!cancelled) setLayers(res);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load governance chain.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <EmptyState>{error}</EmptyState>;
  if (!layers) return <EmptyState>Loading…</EmptyState>;

  return (
    <div>
      <p className="mb-2 text-[9px] text-cmd-textDim">
        The real, disclosed order app/gatekeeper.py::evaluate_gatekeeper() checks every live trade proposal in — not a new authority chain. `Unwired` marks the one honest gap: the
        Institutional Rule Engine is real but not yet routed into live trade execution for non-primary accounts.
      </p>
      <div className="space-y-1.5">
        {layers.map((layer) => (
          <div key={layer.order} className="flex items-start gap-2 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
            <span className="mt-0.5 font-cmdmono text-cmd-cyan">{String(layer.order).padStart(2, "0")}</span>
            <div className="flex-1">
              <div className="flex items-center gap-1.5">
                <span className="text-cmd-text">{layer.name}</span>
                <StatusPill tone={layer.wired ? "green" : "amber"}>{layer.wired ? "WIRED" : "UNWIRED"}</StatusPill>
              </div>
              <div className="text-cmd-textDim">{layer.module}</div>
              <div className="mt-0.5 text-cmd-textDim">{layer.description}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function OverridesTab() {
  const [overrides, setOverrides] = useState<CeoOverrideRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getCeoOverrides()
      .then((res) => {
        if (!cancelled) setOverrides(res);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load CEO overrides.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const sorted = useMemo(() => (overrides ? [...overrides].reverse() : null), [overrides]);

  if (error) return <EmptyState>{error}</EmptyState>;
  if (!sorted) return <EmptyState>Loading…</EmptyState>;
  if (sorted.length === 0) return <EmptyState>No CEO decisions have disagreed with the AI&apos;s recommendation yet.</EmptyState>;

  return (
    <div className="max-h-96 overflow-y-auto">
      <table className="w-full">
        <thead>
          <tr className="sticky top-0 border-b border-cmd-border bg-cmd-panel text-[9px] uppercase tracking-wide text-cmd-textDim">
            <th className="px-2 py-1.5 text-left">Time</th>
            <th className="px-2 py-1.5 text-left">Symbol</th>
            <th className="px-2 py-1.5 text-left">AI Said</th>
            <th className="px-2 py-1.5 text-left">CEO Chose</th>
            <th className="px-2 py-1.5 text-left">Outcome</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((o) => (
            <tr key={o.id} className="border-b border-cmd-border/40 last:border-0">
              <td className="whitespace-nowrap px-2 py-1.5 text-[9px] text-cmd-textDim">{new Date(o.createdAt).toLocaleString()}</td>
              <td className="px-2 py-1.5 font-cmdmono text-cmd-cyan">{o.symbol}</td>
              <td className="px-2 py-1.5 text-[9px] uppercase text-cmd-textDim">{o.aiRecommendation}</td>
              <td className="px-2 py-1.5 text-[9px] uppercase text-cmd-text">{o.ceoDecision}</td>
              <td className="px-2 py-1.5">
                <StatusPill tone={outcomeTone(o.outcome)}>{o.outcome}</StatusPill>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OverrideGovernanceTab() {
  const [evaluations, setEvaluations] = useState<CeoOverrideEvaluation[] | null>(null);
  const [summary, setSummary] = useState<CeoOverrideGovernanceSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = () => {
    api
      .getCeoOverrideEvaluations()
      .then((res) => setEvaluations(res))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load override evaluations."));
    api.getCeoOverrideGovernanceSummary().then((res) => setSummary(res)).catch(() => undefined);
  };

  useEffect(() => {
    load();
  }, []);

  const sorted = useMemo(() => (evaluations ? [...evaluations].reverse() : null), [evaluations]);

  const handleUpdated = (updated: CeoOverrideEvaluation) => {
    setEvaluations((prev) => (prev ? prev.map((e) => (e.id === updated.id ? updated : e)) : prev));
  };

  return (
    <div>
      <p className="mb-2 text-[9px] text-cmd-textDim">
        Every real CEO override, evaluated on two separate axes never collapsed into one score: PROCESS QUALITY (was the override justified by the evidence available at the moment
        the CEO decided) and OUTCOME (mirrored from the underlying trade&apos;s real P&amp;L, never re-derived here). A correct decision can still lose; a bad decision can still win.
      </p>
      <OverrideSummaryStrip summary={summary} />
      {error && <EmptyState>{error}</EmptyState>}
      {!error && !sorted && <EmptyState>Loading…</EmptyState>}
      {!error && sorted && sorted.length === 0 && <EmptyState>No CEO decisions have disagreed with the AI&apos;s recommendation yet.</EmptyState>}
      {!error && sorted && sorted.length > 0 && (
        <div className="max-h-[28rem] space-y-1 overflow-y-auto">
          {sorted.map((e) => (
            <OverrideEvaluationRow key={e.id} evaluation={e} expanded={expandedId === e.id} onToggle={() => setExpandedId((v) => (v === e.id ? null : e.id))} onUpdated={handleUpdated} />
          ))}
        </div>
      )}
    </div>
  );
}

function OverrideSummaryStrip({ summary }: { summary: CeoOverrideGovernanceSummary | null }) {
  if (!summary) return null;
  return (
    <div className="mb-2 grid grid-cols-2 gap-x-4 gap-y-1 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 sm:grid-cols-4">
      <DataRow label="Total Overrides" value={summary.totalOverrideCount} />
      <DataRow
        label="Override Rate"
        value={summary.overrideRatePct === null ? "NOT ENOUGH EVIDENCE" : `${summary.overrideRatePct.toFixed(1)}%`}
        valueClassName={summary.overrideRatePct === null ? "text-cmd-textDim" : "text-cmd-text"}
      />
      <DataRow label="Justified" value={summary.justifiedCount} valueClassName="text-cmd-green" />
      <DataRow label="Unjustified" value={summary.unjustifiedCount} valueClassName={summary.unjustifiedCount > 0 ? "text-cmd-red" : "text-cmd-text"} />
      <DataRow label="Mixed Evidence" value={summary.mixedCount} />
      <DataRow label="Not Enough Evidence" value={summary.notEnoughEvidenceCount} />
      <DataRow label="Outcome Correct / Incorrect" value={`${summary.outcomeCorrectCount} / ${summary.outcomeIncorrectCount}`} />
      <DataRow
        label="Sample Size"
        value={summary.sampleSizeSufficient ? "Sufficient for trends" : "Too small for trends"}
        valueClassName={summary.sampleSizeSufficient ? "text-cmd-text" : "text-cmd-textDim"}
      />
    </div>
  );
}

function OverrideEvaluationRow({
  evaluation,
  expanded,
  onToggle,
  onUpdated,
}: {
  evaluation: CeoOverrideEvaluation;
  expanded: boolean;
  onToggle: () => void;
  onUpdated: (updated: CeoOverrideEvaluation) => void;
}) {
  const [reviewer, setReviewer] = useState<AgentId>("cio");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const submitReview = () => {
    setBusy(true);
    setActionError(null);
    api
      .addCeoOverrideReview(evaluation.id, reviewer, note.trim())
      .then((updated) => {
        onUpdated(updated);
        setNote("");
      })
      .catch((err: unknown) => setActionError(err instanceof Error ? err.message : "Failed to record review."))
      .finally(() => setBusy(false));
  };

  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40">
      <div onClick={onToggle} className="flex cursor-pointer items-center gap-2 px-2 py-1.5 hover:bg-cmd-panelLight/60">
        <StatusPill tone={processQualityTone(evaluation.processQuality)}>{PROCESS_QUALITY_LABEL[evaluation.processQuality]}</StatusPill>
        <StatusPill tone={outcomeTone(evaluation.outcome)}>{evaluation.outcome}</StatusPill>
        <span className="font-cmdmono text-cmd-cyan text-[9px]">{evaluation.symbol}</span>
        <span className="flex-1 truncate text-[9px] text-cmd-textDim">
          AI said <span className="uppercase text-cmd-text">{evaluation.originalRecommendation}</span> — CEO chose <span className="uppercase text-cmd-text">{evaluation.ceoDecision}</span>
        </span>
        <span className="text-[9px] text-cmd-textDim">Day {evaluation.simDay}</span>
      </div>
      {expanded && (
        <div className="border-t border-cmd-border/40 px-2 py-2 text-[9px]">
          <div className="mb-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 sm:grid-cols-3">
            <DataRow label="Original Confidence" value={evaluation.originalConfidencePct === null ? "NOT ENOUGH EVIDENCE" : `${evaluation.originalConfidencePct.toFixed(0)}%`} />
            <DataRow label="Decision Grade" value={evaluation.originalDecisionGrade ?? "—"} />
            <DataRow label="Risk Dept. Stance" value={evaluation.riskDepartmentStance ?? "—"} />
            <DataRow label="Department Agreement" value={evaluation.departmentAgreementPct === null ? "—" : `${evaluation.departmentAgreementPct.toFixed(0)}%`} />
            <DataRow label="Recommendation Source" value="Executive Network" />
          </div>
          {evaluation.overrideReason && (
            <div className="mb-1.5">
              <span className="text-cmd-textDim">CEO&apos;s stated reason: </span>
              <span className="text-cmd-text">{evaluation.overrideReason}</span>
            </div>
          )}
          {evaluation.evidenceAtDecisionTime.length > 0 && (
            <div className="mb-1.5">
              <div className="text-cmd-textDim">Real dissenting evidence on file at decision time:</div>
              <ul className="list-inside list-disc text-cmd-text">
                {evaluation.evidenceAtDecisionTime.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {evaluation.reviewer && (
            <div className="mb-1.5">
              <span className="text-cmd-textDim">Reviewed by {AGENT_PROFILES[evaluation.reviewer].name}: </span>
              <span className="text-cmd-text">{evaluation.reviewNote}</span>
            </div>
          )}
          {actionError && <div className="mb-1.5 text-cmd-red">{actionError}</div>}
          <div className="flex flex-wrap items-center gap-1.5 border-t border-cmd-border/40 pt-1.5">
            <select
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value as AgentId)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
            >
              {AGENT_IDS.map((id) => (
                <option key={id} value={id}>
                  {AGENT_PROFILES[id].name}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add a real review note…"
              className="flex-1 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
            <button
              type="button"
              disabled={busy || note.trim().length === 0}
              className="rounded-sm border border-cmd-cyan/50 bg-cmd-cyan/10 px-2 py-1 text-[9px] uppercase tracking-wide text-cmd-cyan hover:bg-cmd-cyan/20 disabled:opacity-40"
              onClick={submitReview}
            >
              Record Review
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function controlEffectivenessTone(state: GatekeeperControlEffectivenessState): "green" | "red" | "amber" | "cyan" | "neutral" {
  switch (state) {
    case "effective":
      return "green";
    case "ineffective":
      return "red";
    case "mixed":
      return "amber";
    case "insufficient_data":
      return "cyan";
    case "not_yet_tested":
      return "neutral";
  }
}

const CONTROL_EFFECTIVENESS_LABEL: Record<GatekeeperControlEffectivenessState, string> = {
  effective: "Effective",
  ineffective: "Ineffective",
  mixed: "Mixed Evidence",
  insufficient_data: "Insufficient Data",
  not_yet_tested: "Not Yet Tested",
};

function ControlEffectivenessTab() {
  const [summary, setSummary] = useState<ControlEffectivenessSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    api
      .getControlEffectiveness()
      .then((res) => setSummary(res))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load control effectiveness."));
  }, []);

  return (
    <div>
      <p className="mb-2 text-[9px] text-cmd-textDim">
        Did each real Gatekeeper check actually prevent or detect what it was designed to address — not just how often it exists or fires. A control that has never once failed a
        decision reads NOT YET TESTED, never a fabricated &quot;effective&quot;. An outcome is only credited to a control when it was the sole reason a trade was blocked; when
        several checks failed together, the outcome cannot be honestly attributed to any one of them.
      </p>
      {error && <EmptyState>{error}</EmptyState>}
      {!error && !summary && <EmptyState>Loading…</EmptyState>}
      {!error && summary && (
        <>
          <div className="mb-2 grid grid-cols-2 gap-x-4 gap-y-1 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 sm:grid-cols-5">
            <DataRow label="Effective" value={summary.effectiveCount} valueClassName="text-cmd-green" />
            <DataRow label="Ineffective" value={summary.ineffectiveCount} valueClassName={summary.ineffectiveCount > 0 ? "text-cmd-red" : "text-cmd-text"} />
            <DataRow label="Mixed Evidence" value={summary.mixedCount} />
            <DataRow label="Insufficient Data" value={summary.insufficientDataCount} />
            <DataRow label="Not Yet Tested" value={summary.notYetTestedCount} />
            {summary.regressedControlCount > 0 && (
              <DataRow label="Control Regression" value={summary.regressedControlCount} valueClassName="text-cmd-red" />
            )}
          </div>
          <div className="max-h-[28rem] space-y-1 overflow-y-auto">
            {summary.controls.map((c) => (
              <ControlEffectivenessRow
                key={c.controlId}
                control={c}
                expanded={expandedId === c.controlId}
                onToggle={() => setExpandedId((v) => (v === c.controlId ? null : c.controlId))}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function ControlEffectivenessRow({ control, expanded, onToggle }: { control: ControlEffectivenessRecord; expanded: boolean; onToggle: () => void }) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/30">
      <button type="button" onClick={onToggle} className="flex w-full items-center gap-2 px-2 py-1.5 text-left">
        <StatusPill tone={controlEffectivenessTone(control.effectivenessState)}>{CONTROL_EFFECTIVENESS_LABEL[control.effectivenessState]}</StatusPill>
        {control.controlRegression && <StatusPill tone="red">Regression</StatusPill>}
        <span className="flex-1 font-cmdmono text-[10px] text-cmd-text">{control.controlLabel}</span>
        <span className="text-[9px] text-cmd-textDim">{control.triggeredCount} evaluated</span>
      </button>
      {expanded && (
        <div className="border-t border-cmd-border/40 px-2 py-1.5 text-[9px] leading-relaxed">
          <div className="mb-1.5 text-cmd-textDim">{control.purpose}</div>
          <div className="mb-1.5">
            <span className="text-cmd-textDim">Owner: </span>
            <span className="text-cmd-text">{control.owner}</span>
          </div>
          <div className="mb-1.5 grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
            <DataRow label="Triggered / Passed" value={`${control.triggeredCount} / ${control.passedCount}`} />
            <DataRow label="Failed (Blocked)" value={control.failedCount} />
            <DataRow label="Sole-Reason Rejections" value={control.soleReasonRejectionCount} />
            <DataRow label="Confirmed Prevented" value={control.confirmedPreventedCount} valueClassName="text-cmd-green" />
            <DataRow label="Confirmed False Positive" value={control.confirmedFalsePositiveCount} valueClassName={control.confirmedFalsePositiveCount > 0 ? "text-cmd-red" : "text-cmd-text"} />
            <DataRow label="Pending Evaluation" value={control.pendingEvaluationCount} />
            <DataRow label="Ambiguous Attribution" value={control.ambiguousAttributionCount} />
            <DataRow label="Last Triggered" value={control.lastTriggeredAt ? new Date(control.lastTriggeredAt).toLocaleString() : "—"} />
            <DataRow label="Last Evaluated" value={control.lastEvaluatedAt ? new Date(control.lastEvaluatedAt).toLocaleString() : "—"} />
          </div>
        </div>
      )}
    </div>
  );
}

function remediationEffectivenessTone(state: RemediationEffectivenessState): "green" | "red" | "amber" | "cyan" {
  switch (state) {
    case "effective":
      return "green";
    case "ineffective":
      return "red";
    case "partially_effective":
      return "amber";
    case "not_enough_evidence":
      return "cyan";
  }
}

const REMEDIATION_EFFECTIVENESS_LABEL: Record<RemediationEffectivenessState, string> = {
  effective: "Effective",
  partially_effective: "Partially Effective",
  ineffective: "Ineffective",
  not_enough_evidence: "Not Enough Evidence",
};

function ContinuousImprovementTab() {
  const [summary, setSummary] = useState<ContinuousImprovementSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getContinuousImprovement()
      .then((res) => setSummary(res))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load the continuous improvement loop."));
  }, []);

  return (
    <div>
      <p className="mb-2 text-[9px] text-cmd-textDim">
        The loop this closes: INCIDENT → ROOT CAUSE → REMEDIATION → MONITORING → OUTCOME → EFFECTIVENESS REVIEW → COMPANY HEALTH. A real
        reopened incident is the strongest evidence a fix failed and always reads INEFFECTIVE. Short of that, a real observation window must
        elapse before &quot;no recurrence yet&quot; honestly reads EFFECTIVE rather than NOT ENOUGH EVIDENCE.
      </p>
      {error && <EmptyState>{error}</EmptyState>}
      {!error && !summary && <EmptyState>Loading…</EmptyState>}
      {!error && summary && (
        <>
          <div className="mb-2 grid grid-cols-2 gap-x-4 gap-y-1 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 sm:grid-cols-5">
            <DataRow label="Effective" value={summary.effectiveCount} valueClassName="text-cmd-green" />
            <DataRow label="Partially Effective" value={summary.partiallyEffectiveCount} />
            <DataRow label="Ineffective" value={summary.ineffectiveCount} valueClassName={summary.ineffectiveCount > 0 ? "text-cmd-red" : "text-cmd-text"} />
            <DataRow label="Not Enough Evidence" value={summary.notEnoughEvidenceCount} />
            <DataRow label="Recurring Failures" value={summary.recurringFailureCount} valueClassName={summary.recurringFailureCount > 0 ? "text-cmd-red" : "text-cmd-text"} />
          </div>

          <TerminalLabel>Root Cause Recurrence</TerminalLabel>
          {summary.rootCauseRecurrences.length === 0 && <EmptyState>No incident has ever been resolved with a real root cause yet.</EmptyState>}
          {summary.rootCauseRecurrences.length > 0 && (
            <div className="mb-3 space-y-1">
              {summary.rootCauseRecurrences.map((r) => (
                <RootCauseRecurrenceRow key={r.rootCause} recurrence={r} />
              ))}
            </div>
          )}

          <TerminalLabel>Remediation Effectiveness</TerminalLabel>
          {summary.remediations.length === 0 && <EmptyState>No incident has ever been resolved yet — nothing to review.</EmptyState>}
          {summary.remediations.length > 0 && (
            <div className="max-h-[24rem] space-y-1 overflow-y-auto">
              {summary.remediations.map((r) => (
                <RemediationRow key={r.incidentId} remediation={r} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function RootCauseRecurrenceRow({ recurrence }: { recurrence: RootCauseRecurrence }) {
  return (
    <div className="flex items-center gap-2 rounded-sm border border-cmd-border/60 bg-cmd-bg/30 px-2 py-1.5 text-[9px]">
      {recurrence.recurringFailure && <StatusPill tone="red">Recurring</StatusPill>}
      <span className="flex-1 font-cmdmono text-cmd-text">{ROOT_CAUSE_LABEL[recurrence.rootCause]}</span>
      <span className="text-cmd-textDim">{recurrence.incidentCount} incident{recurrence.incidentCount === 1 ? "" : "s"}</span>
    </div>
  );
}

function RemediationRow({ remediation }: { remediation: RemediationEffectivenessRecord }) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/30 px-2 py-1.5 text-[9px]">
      <div className="flex items-center gap-2">
        <StatusPill tone={remediationEffectivenessTone(remediation.effectivenessState)}>
          {REMEDIATION_EFFECTIVENESS_LABEL[remediation.effectivenessState]}
        </StatusPill>
        <span className="flex-1 font-cmdmono text-cmd-text">{ROOT_CAUSE_LABEL[remediation.rootCause]}</span>
        <span className="text-cmd-textDim">{remediation.department}</span>
      </div>
      <div className="mt-1 text-cmd-textDim">{remediation.correctiveAction}</div>
      <div className="mt-1 flex gap-4 text-cmd-textDim">
        <span>Reopened: {remediation.reopenedCount}</span>
        <span>Recurrence: {remediation.recurrenceCount}</span>
      </div>
    </div>
  );
}
