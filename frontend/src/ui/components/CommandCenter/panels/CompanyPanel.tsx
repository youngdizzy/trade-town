import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { SettingsManager } from "@/game/systems/SettingsManager";
import { SaveManager } from "@/game/systems/SaveManager";
import { api } from "@/net/api";
import type { CompanyHealthTier, CompanyPriority, MarketEnvironmentRegime, OperatingMode, TimeAdvanceTarget } from "@/types";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

const MODE_LABEL: Record<OperatingMode, string> = { learning: "LEARNING", assisted: "ASSISTED", executive: "EXECUTIVE" };
const MODE_DESCRIPTION: Record<OperatingMode, string> = {
  learning: "Every trade proposal waits for your real buy/sell/wait call — the desk never acts on its own.",
  assisted:
    "Routine proposals (high confidence, no active risk warning, reasonable size) auto-resolve using the desk's own recommendation. A significant one still waits for you.",
  executive:
    "Every proposal auto-resolves using the desk's own recommendation. You review Decisions and Company Health rather than individual trades.",
};

// v0.7 Feature 34 — Company Priorities. Each option biases exactly one
// real, already-existing lever (see backend/app/nexus.py's tick()) —
// "Expansion"/"Efficiency"/"Innovation" from the brief have no real
// distinct lever to attach to and aren't offered (see schemas.py's
// CompanyPriority docstring).
const PRIORITY_LABEL: Record<CompanyPriority, string> = { balanced: "BALANCED", learning: "LEARNING", research: "RESEARCH", risk_reduction: "RISK REDUCTION" };
const PRIORITY_DESCRIPTION: Record<CompanyPriority, string> = {
  balanced: "No bias — every department runs at its normal, unmodified pace.",
  learning: "Academy knowledge points from research, projects, and meetings are earned 1.5x faster.",
  research: "Active research items gain confidence 1.5x faster toward completion.",
  risk_reduction: "New trade proposals are sized and vetted against tightened (80%) risk limits — your own configured limits are unchanged.",
};

const TIME_TARGETS: { target: TimeAdvanceTarget; label: string; description: string }[] = [
  { target: "workday_end", label: "END WORKDAY", description: "Jump to 20:00 — the moment every department's day genuinely ends." },
  { target: "week_end", label: "END WEEK", description: "Jump to next week's close — weekly reports fire along the way." },
  { target: "month_end", label: "END MONTH", description: "Jump to next month's close — monthly reports and Treasury rules fire along the way." },
];

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
  const [advancing, setAdvancing] = useState<TimeAdvanceTarget | null>(null);
  const [customHours, setCustomHours] = useState("6");
  const [timeError, setTimeError] = useState<string | null>(null);

  const runAdvance = async (target: TimeAdvanceTarget, hours?: number) => {
    if (advancing) return;
    setAdvancing(target);
    setTimeError(null);
    try {
      const state = await api.advanceTime(target, hours);
      SaveManager.applyState(state);
    } catch (err) {
      setTimeError(err instanceof Error ? err.message : String(err));
    } finally {
      setAdvancing(null);
    }
  };

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

      <Glass className="p-3 lg:col-span-3">
        <TerminalLabel>Company Priority</TerminalLabel>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-4">
          {(Object.keys(PRIORITY_LABEL) as CompanyPriority[]).map((priority) => {
            const active = settings.companyPriority === priority;
            return (
              <button
                key={priority}
                type="button"
                onClick={() => SettingsManager.update({ companyPriority: priority })}
                className={`rounded-sm border p-2.5 text-left transition-colors ${
                  active ? "border-cmd-purple/50 bg-cmd-purple/10" : "border-cmd-border/60 bg-cmd-bg/40 hover:border-cmd-purple/30"
                }`}
              >
                <div className="mb-1 flex items-center justify-between">
                  <span className={active ? "text-cmd-purple" : "text-cmd-text"}>{PRIORITY_LABEL[priority]}</span>
                  {active && <StatusPill tone="purple">ACTIVE</StatusPill>}
                </div>
                <div className="text-[9px] text-cmd-textDim">{PRIORITY_DESCRIPTION[priority]}</div>
              </button>
            );
          })}
        </div>
      </Glass>

      <Glass className="p-3 lg:col-span-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Work Mode</TerminalLabel>
          <StatusPill tone={settings.workMode === "work" ? "green" : "purple"}>{settings.workMode === "work" ? "🟢 WORK MODE ACTIVE" : "🌙 REST MODE ACTIVE"}</StatusPill>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => SettingsManager.update({ workMode: "work" })}
            className={`rounded-sm border p-2.5 text-left transition-colors ${
              settings.workMode === "work" ? "border-cmd-green/50 bg-cmd-green/10 shadow-cmd-green" : "border-cmd-border/60 bg-cmd-bg/40 hover:border-cmd-green/30"
            }`}
          >
            <div className={`mb-1 ${settings.workMode === "work" ? "text-cmd-green" : "text-cmd-text"}`}>WORK MODE</div>
            <div className="text-[9px] text-cmd-textDim">
              Employees work their real schedules indefinitely — research, meetings, and Academy training all continue. Trading runs on the
              selected Operating Mode above. No automatic stopping; stays active until you switch it.
            </div>
          </button>
          <button
            type="button"
            onClick={() => SettingsManager.update({ workMode: "rest" })}
            className={`rounded-sm border p-2.5 text-left transition-colors ${
              settings.workMode === "rest" ? "border-cmd-purple/50 bg-cmd-purple/10" : "border-cmd-border/60 bg-cmd-bg/40 hover:border-cmd-purple/30"
            }`}
          >
            <div className={`mb-1 ${settings.workMode === "rest" ? "text-cmd-purple" : "text-cmd-text"}`}>REST MODE</div>
            <div className="text-[9px] text-cmd-textDim">
              Employees finish what they're doing, stop starting new work, and head to the Break Room to eat, socialize, study, exercise, or
              sleep — real off-hours routines, on demand. Open trades keep being managed safely by Automation Mode and risk rules; they never
              get abandoned.
            </div>
          </button>
        </div>
      </Glass>

      <Glass className="p-3 lg:col-span-3">
        <TerminalLabel>Time Controls</TerminalLabel>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-4">
          {TIME_TARGETS.map(({ target, label, description }) => (
            <button
              key={target}
              type="button"
              onClick={() => void runAdvance(target)}
              disabled={advancing !== null}
              className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2.5 text-left transition-colors hover:border-cmd-cyan/30 disabled:opacity-40"
            >
              <div className="mb-1 text-cmd-cyan">{advancing === target ? "ADVANCING…" : label}</div>
              <div className="text-[9px] text-cmd-textDim">{description}</div>
            </button>
          ))}
          <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2.5">
            <div className="mb-1 text-cmd-cyan">FAST FORWARD</div>
            <div className="flex items-center gap-1.5">
              <input
                type="number"
                min={1}
                max={72}
                value={customHours}
                onChange={(e) => setCustomHours(e.target.value)}
                className="w-14 rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text focus:border-cmd-cyan/50 focus:outline-none"
              />
              <span className="text-[9px] text-cmd-textDim">hours</span>
              <button
                type="button"
                onClick={() => void runAdvance("hours", Number(customHours))}
                disabled={advancing !== null}
                className="ml-auto flex-none rounded-sm border border-cmd-cyan/50 px-2 py-1 text-[9px] uppercase tracking-wider text-cmd-cyan transition-colors hover:bg-cmd-cyan/10 disabled:opacity-40"
              >
                {advancing === "hours" ? "…" : "GO"}
              </button>
            </div>
          </div>
        </div>
        {timeError && <div className="mt-2 text-[9px] text-cmd-red">{timeError}</div>}
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
