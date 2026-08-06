import { useEffect, useMemo, useState } from "react";
import { api } from "@/net/api";
import type { AlertSeverity, AuditEntry, AuditEventCategory, CeoOverrideRecord, ComplianceOverview, GovernanceLayer } from "@/types";
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
 * read of the Institutional Rule Engine). There is no mutable Incident
 * workflow, no per-event Broker/User/Software-Version field, and no
 * Institutional Time Machine state-replay — the chronologically-sorted
 * Audit Log itself is that addendum's honest scope (see the Design
 * Bible chapter's own Implementation Notes for the full cut list).
 */

const TABS = ["log", "incidents", "governance", "overrides"] as const;
type Tab = (typeof TABS)[number];

const TAB_LABEL: Record<Tab, string> = {
  log: "Audit Log",
  incidents: "Incidents",
  governance: "Governance",
  overrides: "CEO Overrides",
};

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
        {tab === "governance" && <GovernanceTab />}
        {tab === "overrides" && <OverridesTab />}
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
          <TerminalLabel>Executive Accuracy — reused from Chapter 70 Part 2</TerminalLabel>
          <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
            {overview.executiveAccuracy.map((a) => (
              <div key={a.role} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="text-cmd-textDim">{a.departmentLabel}</div>
                <div className="text-cmd-text tabular-nums">
                  {a.decisionsTracked > 0 ? `${a.accuracyPct.toFixed(0)}%` : "—"} <span className="text-cmd-textDim">({a.decisionsTracked})</span>
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
