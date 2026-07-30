import { useGameStore } from "@/ui/hooks/useGameStore";
import { computeDepartmentHealth, computeExecutivePriorities } from "../lib/derive";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

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
 */
export function ExecutiveIntelPanel() {
  const { companyDna, companyHealth, coachReports, executiveReviews, research, riskWarnings, paperPortfolio, blackBox, innovationState, founderState, academyState } = useGameStore();

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
    </div>
  );
}
