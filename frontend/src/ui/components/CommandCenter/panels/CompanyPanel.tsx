import { useGameStore } from "@/ui/hooks/useGameStore";
import { SettingsManager } from "@/game/systems/SettingsManager";
import type { CompanyHealthTier, MarketEnvironmentRegime, OperatingMode } from "@/types";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

const MODE_LABEL: Record<OperatingMode, string> = { learning: "LEARNING", assisted: "ASSISTED", executive: "EXECUTIVE" };
const MODE_DESCRIPTION: Record<OperatingMode, string> = {
  learning: "Every trade proposal waits for your real buy/sell/wait call — the desk never acts on its own.",
  assisted:
    "Routine proposals (high confidence, no active risk warning, reasonable size) auto-resolve using the desk's own recommendation. A significant one still waits for you.",
  executive:
    "Every proposal auto-resolves using the desk's own recommendation. You review Decisions and Company Health rather than individual trades.",
};

const TIER_TONE: Record<CompanyHealthTier, "green" | "cyan" | "amber" | "red"> = {
  excellent: "green",
  good: "green",
  stable: "cyan",
  needs_attention: "amber",
  critical: "red",
};
const TIER_LABEL: Record<CompanyHealthTier, string> = {
  excellent: "EXCELLENT",
  good: "GOOD",
  stable: "STABLE",
  needs_attention: "NEEDS ATTENTION",
  critical: "CRITICAL",
};

const REGIME_TONE: Record<MarketEnvironmentRegime, "green" | "red" | "amber" | "cyan" | "neutral"> = {
  bull: "green",
  bear: "red",
  sideways: "neutral",
  high_volatility: "amber",
  low_volatility: "cyan",
};

function metricTone(score: number): "green" | "amber" | "red" {
  return score >= 70 ? "green" : score >= 40 ? "amber" : "red";
}

/**
 * v0.7 Features 21-23 — Company Operating Modes, Market Environment
 * Simulation, and the Company Health & Stability System, co-located in
 * one tab since all three are "how is the company being run" concerns.
 * Every number here is a real field off gameStore — companyHealth and
 * marketEnvironment are recomputed server-side every tick (see
 * backend/app/company_health.py / app/market_environment.py); the
 * operating mode toggle writes through SettingsManager, the same real
 * path every other player preference (music/SFX/showFps) already uses.
 */
export function CompanyPanel() {
  const { settings, companyHealth, marketEnvironment } = useGameStore();

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <Glass className="p-3 lg:col-span-3">
        <TerminalLabel>Company Operating Mode</TerminalLabel>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {(Object.keys(MODE_LABEL) as OperatingMode[]).map((mode) => {
            const active = settings.operatingMode === mode;
            return (
              <button
                key={mode}
                type="button"
                onClick={() => SettingsManager.update({ operatingMode: mode })}
                className={`rounded-sm border p-2.5 text-left transition-colors ${
                  active ? "border-cmd-cyan/50 bg-cmd-cyan/10 shadow-cmd-cyan" : "border-cmd-border/60 bg-cmd-bg/40 hover:border-cmd-cyan/30"
                }`}
              >
                <div className="mb-1 flex items-center justify-between">
                  <span className={active ? "text-cmd-cyan" : "text-cmd-text"}>{MODE_LABEL[mode]}</span>
                  {active && <StatusPill tone="cyan">ACTIVE</StatusPill>}
                </div>
                <div className="text-[9px] text-cmd-textDim">{MODE_DESCRIPTION[mode]}</div>
              </button>
            );
          })}
        </div>
      </Glass>

      <Glass className="p-3 lg:col-span-2">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Company Health</TerminalLabel>
          <StatusPill tone={TIER_TONE[companyHealth.tier]}>{TIER_LABEL[companyHealth.tier]}</StatusPill>
        </div>
        <div className="mb-2 flex items-baseline justify-between">
          <span className="font-cmdmono text-2xl text-cmd-cyan">{Math.round(companyHealth.overall)}</span>
          <span className="text-cmd-textDim">/ 100</span>
        </div>
        <Meter value={companyHealth.overall} tone={TIER_TONE[companyHealth.tier] === "amber" || TIER_TONE[companyHealth.tier] === "red" ? TIER_TONE[companyHealth.tier] : "cyan"} />
        <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-3">
          <HealthCell label="Stability" value={companyHealth.operationalStability} />
          <HealthCell label="Efficiency" value={companyHealth.departmentEfficiency} />
          <HealthCell label="Morale" value={companyHealth.employeeMorale} />
          <HealthCell label="Research" value={companyHealth.researchProgress} />
          <HealthCell label="Capital" value={companyHealth.capitalHealth} />
          <HealthCell label="Resources" value={companyHealth.resourceUsage} />
          <HealthCell label="Reputation" value={companyHealth.reputation} />
          <HealthCell label="Technology" value={companyHealth.technologyLevel} />
          <HealthCell label="Office" value={companyHealth.officeExpansion} />
          <HealthCell label="Education" value={companyHealth.educationProgress} />
        </div>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Recommendations</TerminalLabel>
        {companyHealth.recommendations.length === 0 ? (
          <EmptyState>Every metric is holding strong.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {companyHealth.recommendations.map((r) => (
              <div key={r} className="rounded-sm border border-cmd-amber/30 bg-cmd-bg/40 p-2 text-[9px] text-cmd-amber">
                {r}
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3 lg:col-span-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Market Environment</TerminalLabel>
          <StatusPill tone={REGIME_TONE[marketEnvironment.current]}>{marketEnvironment.label}</StatusPill>
        </div>
        <div className="mb-3 text-[9px] text-cmd-textDim">{marketEnvironment.detail}</div>
        <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Historical Timeline</div>
        {marketEnvironment.timeline.length === 0 ? (
          <EmptyState>No regime changes recorded yet — conditions have stayed {marketEnvironment.label.toLowerCase()}.</EmptyState>
        ) : (
          <div className="space-y-1">
            {[...marketEnvironment.timeline].reverse().map((entry) => (
              <div key={entry.id} className="flex items-center justify-between gap-2 border-b border-cmd-border/40 py-1 text-[9px] last:border-0">
                <StatusPill tone={REGIME_TONE[entry.regime]}>{entry.label}</StatusPill>
                <span className="flex-1 truncate text-cmd-textDim">{entry.detail}</span>
                <span className="tabular-nums text-cmd-textDim">t+{entry.simMinutes}m</span>
              </div>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}

function HealthCell({ label, value }: { label: string; value: number }) {
  const tone = metricTone(value);
  const toneClass: Record<string, string> = { green: "text-cmd-green", amber: "text-cmd-amber", red: "text-cmd-red" };
  return <DataRow label={label} value={value.toFixed(0)} valueClassName={toneClass[tone]} />;
}
