import { useEffect, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { SettingsManager } from "@/game/systems/SettingsManager";
import { SaveManager } from "@/game/systems/SaveManager";
import { NexusManager } from "@/game/systems/NexusManager";
import { api } from "@/net/api";
import { GOAL_CATEGORY_LABEL, GOAL_METRIC_LABEL } from "@/types";
import type { CompanyHealthTier, CompanyPriority, Goal, GoalAllocation, GoalCategory, GoalMetric, GoalPriority, MarketEnvironmentRegime, OperatingMode, RegimeAgreement, RegimePosture, RegimeReconciliation, TimeAdvanceTarget } from "@/types";
import { computeScoreBenchmark } from "../lib/derive";
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

// Design Bible Chapter 65 — real, transparent categories off
// MarketQualityScore.tier + confidencePct alone (see
// backend/app/regime_reconciliation.py) — never a numeric override of
// any CEO-configured RiskLimits field.
const POSTURE_TONE: Record<RegimePosture, "green" | "amber" | "cyan"> = { cautious: "amber", normal: "cyan", opportunistic: "green" };
const AGREEMENT_TONE: Record<RegimeAgreement, "green" | "amber"> = { aligned: "green", diverging: "amber" };

function metricTone(score: number): "green" | "amber" | "red" {
  return score >= 70 ? "green" : score >= 40 ? "amber" : "red";
}

// Design Bible Chapter 63 — Benchmarking period options. Real, retained
// ExecutiveReview history caps at 20 monthly reviews server-side, so
// "12 reviews ago" is the deepest honest comparison available.
const BENCHMARK_PERIODS: number[] = [1, 3, 6, 12];

// Design Bible Chapter 64 — every option here maps to a real, already-
// computed metric (see backend/app/goals.py's resolve_metric_value()).
const GOAL_METRIC_OPTIONS: GoalMetric[] = ["company_health_combined", "company_score_overall", "portfolio_return_pct", "academy_level"];
const GOAL_CATEGORY_OPTIONS: GoalCategory[] = ["growth", "risk", "research", "trading", "operations"];
const GOAL_STATUS_TONE: Record<string, "green" | "cyan" | "amber" | "red"> = { active: "cyan", completed: "green", cancelled: "amber", expired: "red" };

// Design Bible Chapter 64 (third pass) — the Executive Priority Engine's
// real 0-100 score (see backend/app/goals.py's compute_goal_priority()).
function priorityTone(score: number): "green" | "amber" | "red" {
  return score >= 70 ? "red" : score >= 35 ? "amber" : "green";
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
  const { settings, companyHealth, marketEnvironment, riskLimits, executiveReviews, goals, strategicReviews, time } = useGameStore();
  const [advancing, setAdvancing] = useState<TimeAdvanceTarget | null>(null);
  const [customHours, setCustomHours] = useState("6");
  const [timeError, setTimeError] = useState<string | null>(null);

  // Design Bible Chapter 63 — Company Health tier thresholds. Defaults
  // match the exact fixed constants they replace (85/70/50/30); the
  // server validates they stay strictly descending regardless of which
  // subset this call changes.
  const [excellentThreshold, setExcellentThreshold] = useState(String(riskLimits.companyHealthExcellentThreshold));
  const [goodThreshold, setGoodThreshold] = useState(String(riskLimits.companyHealthGoodThreshold));
  const [stableThreshold, setStableThreshold] = useState(String(riskLimits.companyHealthStableThreshold));
  const [needsAttentionThreshold, setNeedsAttentionThreshold] = useState(String(riskLimits.companyHealthNeedsAttentionThreshold));
  const [thresholdBusy, setThresholdBusy] = useState(false);
  const [thresholdError, setThresholdError] = useState<string | null>(null);

  const saveTierThresholds = async () => {
    if (thresholdBusy) return;
    setThresholdBusy(true);
    setThresholdError(null);
    try {
      const res = await api.updateRiskLimits({
        companyHealthExcellentThreshold: Number(excellentThreshold),
        companyHealthGoodThreshold: Number(goodThreshold),
        companyHealthStableThreshold: Number(stableThreshold),
        companyHealthNeedsAttentionThreshold: Number(needsAttentionThreshold),
      });
      NexusManager.setRiskLimits(res.riskLimits);
    } catch (err) {
      setThresholdError(err instanceof Error ? err.message : String(err));
    } finally {
      setThresholdBusy(false);
    }
  };

  // Design Bible Chapter 63 — Benchmarking. Real comparison against a
  // CEO-chosen prior monthly ExecutiveReview, not just the immediately-
  // previous one (see lib/derive.ts's computeScoreBenchmark).
  const [benchmarkPeriods, setBenchmarkPeriods] = useState(1);
  const benchmark = computeScoreBenchmark(executiveReviews, benchmarkPeriods);

  // Design Bible Chapter 64 — Goal creation form. Deliberately the
  // smallest real slice: title + category + one real metric + target +
  // optional deadline. Progress is never entered by the CEO — it's
  // computed server-side.
  const [goalTitle, setGoalTitle] = useState("");
  const [goalCategory, setGoalCategory] = useState<GoalCategory>("growth");
  const [goalMetric, setGoalMetric] = useState<GoalMetric>("company_score_overall");
  const [goalTarget, setGoalTarget] = useState("80");
  const [goalDeadline, setGoalDeadline] = useState("");
  const [goalBusy, setGoalBusy] = useState(false);
  const [goalError, setGoalError] = useState<string | null>(null);

  const createGoal = async () => {
    if (goalBusy) return;
    setGoalBusy(true);
    setGoalError(null);
    try {
      const deadlineSimDay = goalDeadline.trim() === "" ? null : Number(goalDeadline);
      const res = await api.createGoal({ title: goalTitle, category: goalCategory, targetMetric: goalMetric, targetValue: Number(goalTarget), deadlineSimDay });
      NexusManager.setGoals(res.goals);
      setGoalTitle("");
    } catch (err) {
      setGoalError(err instanceof Error ? err.message : String(err));
    } finally {
      setGoalBusy(false);
    }
  };

  const cancelGoal = async (goalId: string) => {
    try {
      const res = await api.cancelGoal(goalId);
      NexusManager.setGoals(res.goals);
    } catch {
      // A failed cancel leaves the goal exactly as it was — nothing to
      // reconcile client-side; the next real tick's WS update is the
      // source of truth either way.
    }
  };

  // Design Bible Chapter 64 (third pass) — the Executive Priority
  // Engine. Refetched whenever the real goals list changes (a create,
  // cancel, or tick-driven status/progress change all shift real
  // rankings), computed fresh server-side, never a client-computed
  // number.
  const [priorities, setPriorities] = useState<GoalPriority[]>([]);
  useEffect(() => {
    let cancelled = false;
    api
      .getGoalPriorities()
      .then((res) => {
        if (!cancelled) setPriorities(res);
      })
      .catch(() => {
        // An honest empty state (no ranking shown) beats a stale one.
        if (!cancelled) setPriorities([]);
      });
    return () => {
      cancelled = true;
    };
  }, [goals]);

  const priorityByGoalId = new Map(priorities.map((p) => [p.goalId, p]));
  const rankedGoals = orderGoalsByPriority(goals, priorityByGoalId);

  // Design Bible Chapter 64 (fourth pass) — Resource Allocation. A
  // recommend-only share of executive ATTENTION across active goals,
  // normalized from the same real Priority Engine scores above —
  // fetched the same way, refetched on the same real triggers, never a
  // claim about moving real capital (see backend/app/goals.py's
  // compute_resource_allocation()).
  const [allocations, setAllocations] = useState<GoalAllocation[]>([]);
  useEffect(() => {
    let cancelled = false;
    api
      .getGoalAllocations()
      .then((res) => {
        if (!cancelled) setAllocations(res);
      })
      .catch(() => {
        if (!cancelled) setAllocations([]);
      });
    return () => {
      cancelled = true;
    };
  }, [goals]);
  const allocationByGoalId = new Map(allocations.map((a) => [a.goalId, a]));

  // Design Bible Chapter 65 — Market Regime Detection & Adaptive
  // Strategy Engine. Reconciles the two real regime engines (this
  // panel's own Market Environment card below, and the MARKETINTEL
  // tab's richer 13-way read) into one CEO-facing answer, plus a
  // read-only posture recommendation — never an automatic change to
  // any real risk limit. Refetched whenever the live regime updates.
  const [regimeReconciliation, setRegimeReconciliation] = useState<RegimeReconciliation | null>(null);
  useEffect(() => {
    let cancelled = false;
    api
      .getRegimeReconciliation()
      .then((res) => {
        if (!cancelled) setRegimeReconciliation(res);
      })
      .catch(() => {
        if (!cancelled) setRegimeReconciliation(null);
      });
    return () => {
      cancelled = true;
    };
  }, [marketEnvironment]);

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
          <HealthCell label="Team Chemistry" value={companyHealth.teamChemistry} />
        </div>
      </Glass>

      <Glass className="p-3 lg:col-span-2">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Executive Health</TerminalLabel>
          <StatusPill tone={TIER_TONE[companyHealth.executiveTier]}>{TIER_LABEL[companyHealth.executiveTier]}</StatusPill>
        </div>
        <p className="mb-2 text-[9px] text-cmd-textDim">
          Ten dimensions computed from the Executive Intelligence Network&apos;s own real data — additive alongside Company Health above, never
          replacing it.
        </p>
        <div className="mb-2 flex items-baseline justify-between">
          <span className="font-cmdmono text-2xl text-cmd-cyan">{Math.round(companyHealth.executiveOverall)}</span>
          <span className="text-cmd-textDim">/ 100</span>
        </div>
        <Meter
          value={companyHealth.executiveOverall}
          tone={TIER_TONE[companyHealth.executiveTier] === "amber" || TIER_TONE[companyHealth.executiveTier] === "red" ? TIER_TONE[companyHealth.executiveTier] : "cyan"}
        />
        <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-3">
          <HealthCell label="Decision Quality" value={companyHealth.decisionQuality} />
          <HealthCell label="Exec Alignment" value={companyHealth.executiveAlignment} />
          <HealthCell label="Risk Governance" value={companyHealth.riskGovernance} />
          <HealthCell label="Sim Coverage" value={companyHealth.simulationCoverage} />
          <HealthCell label="Dept Consensus" value={companyHealth.departmentConsensus} />
          <HealthCell label="Self-Eval Health" value={companyHealth.selfEvaluationHealth} />
          <HealthCell label="Institutional Memory" value={companyHealth.institutionalMemory} />
          <HealthCell label="Innovation Velocity" value={companyHealth.innovationVelocity} />
          <HealthCell label="Talent Development" value={companyHealth.talentDevelopment} />
          <HealthCell label="Founder Oversight" value={companyHealth.founderOversight} />
        </div>
        <div className="mt-3 flex items-center justify-between border-t border-cmd-border/50 pt-2">
          <span className="text-[9px] uppercase tracking-wide text-cmd-textDim">Combined Overall</span>
          <span className="flex items-center gap-2">
            <StatusPill tone={TIER_TONE[companyHealth.combinedTier]}>{TIER_LABEL[companyHealth.combinedTier]}</StatusPill>
            <span className="font-cmdmono text-cmd-text">{Math.round(companyHealth.combinedOverall)}/100</span>
          </span>
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

      <Glass className="p-3 lg:col-span-2">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Company Health Tier Thresholds</TerminalLabel>
          <span className="text-[8px] uppercase tracking-wide text-cmd-textDim">Design Bible Chapter 63</span>
        </div>
        <div className="text-[9px] text-cmd-textDim">
          Where each real tier begins, for Company Health, Executive Health, and Combined alike. Must stay strictly descending — Excellent &gt; Good &gt; Stable &gt; Needs Attention.
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Excellent ≥
            <input
              type="number"
              min="0"
              max="100"
              step="1"
              value={excellentThreshold}
              onChange={(e) => setExcellentThreshold(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Good ≥
            <input
              type="number"
              min="0"
              max="100"
              step="1"
              value={goodThreshold}
              onChange={(e) => setGoodThreshold(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Stable ≥
            <input
              type="number"
              min="0"
              max="100"
              step="1"
              value={stableThreshold}
              onChange={(e) => setStableThreshold(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Needs Attention ≥
            <input
              type="number"
              min="0"
              max="100"
              step="1"
              value={needsAttentionThreshold}
              onChange={(e) => setNeedsAttentionThreshold(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
        </div>
        <button
          type="button"
          onClick={() => void saveTierThresholds()}
          disabled={thresholdBusy}
          className="mt-3 rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[9px] uppercase tracking-wider text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40"
        >
          {thresholdBusy ? "Saving…" : "Save Tier Thresholds"}
        </button>
        {thresholdError && <div className="mt-1.5 text-[9px] text-cmd-red">{thresholdError}</div>}
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Benchmarking</TerminalLabel>
          <span className="text-[8px] uppercase tracking-wide text-cmd-textDim">Design Bible Chapter 63</span>
        </div>
        <div className="mb-2 flex gap-1">
          {BENCHMARK_PERIODS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setBenchmarkPeriods(p)}
              className={`flex-1 rounded-sm border px-1.5 py-1 text-[9px] transition-colors ${
                benchmarkPeriods === p ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border/60 bg-cmd-bg/40 text-cmd-textDim hover:border-cmd-cyan/30"
              }`}
            >
              {p}x
            </button>
          ))}
        </div>
        {benchmark === null ? (
          <EmptyState>Not enough monthly Executive Review history yet — check back after a few more real months pass.</EmptyState>
        ) : (
          <>
            <div className="flex items-baseline justify-between">
              <span className="font-cmdmono text-lg text-cmd-cyan">{benchmark.currentScore.toFixed(1)}</span>
              <span className={`font-cmdmono text-[10px] ${benchmark.delta >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>
                {benchmark.delta >= 0 ? "+" : ""}
                {benchmark.delta.toFixed(1)}
              </span>
            </div>
            <div className="mt-1 text-[9px] text-cmd-textDim">
              vs. {benchmark.comparisonScore.toFixed(1)} ({benchmark.comparisonLabel})
            </div>
          </>
        )}
      </Glass>

      <Glass className="p-3 lg:col-span-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Company Goals</TerminalLabel>
          <span className="text-[8px] uppercase tracking-wide text-cmd-textDim">Design Bible Chapter 64</span>
        </div>
        <div className="mb-3 text-[9px] text-cmd-textDim">
          Name a real objective against one already-tracked company metric. Progress is computed fresh every tick — never entered by hand.
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-5">
          <input
            type="text"
            placeholder="Goal title"
            value={goalTitle}
            onChange={(e) => setGoalTitle(e.target.value)}
            className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50 sm:col-span-2"
          />
          <select
            value={goalCategory}
            onChange={(e) => setGoalCategory(e.target.value as GoalCategory)}
            className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          >
            {GOAL_CATEGORY_OPTIONS.map((c) => (
              <option key={c} value={c}>
                {GOAL_CATEGORY_LABEL[c]}
              </option>
            ))}
          </select>
          <select
            value={goalMetric}
            onChange={(e) => setGoalMetric(e.target.value as GoalMetric)}
            className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          >
            {GOAL_METRIC_OPTIONS.map((m) => (
              <option key={m} value={m}>
                {GOAL_METRIC_LABEL[m]}
              </option>
            ))}
          </select>
          <input
            type="number"
            placeholder="Target"
            value={goalTarget}
            onChange={(e) => setGoalTarget(e.target.value)}
            className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          />
        </div>
        <div className="mt-2 flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-[9px] text-cmd-textDim">
            Deadline (sim day, optional — currently day {time.day})
            <input
              type="number"
              min={time.day + 1}
              placeholder="none"
              value={goalDeadline}
              onChange={(e) => setGoalDeadline(e.target.value)}
              className="w-20 rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
          <button
            type="button"
            onClick={() => void createGoal()}
            disabled={goalBusy || goalTitle.trim() === ""}
            className="ml-auto flex-none rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[9px] uppercase tracking-wider text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40"
          >
            {goalBusy ? "Creating…" : "Create Goal"}
          </button>
        </div>
        {goalError && <div className="mt-1.5 text-[9px] text-cmd-red">{goalError}</div>}

        <div className="mt-3 space-y-1.5 border-t border-cmd-border/50 pt-2">
          {goals.length === 0 ? (
            <EmptyState>No company goals set yet.</EmptyState>
          ) : (
            rankedGoals.map((g) => {
              const priority = priorityByGoalId.get(g.id);
              const allocation = allocationByGoalId.get(g.id);
              return (
                <div key={g.id} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2 text-[9px]">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-cmd-text">{g.title}</span>
                    <div className="flex flex-none items-center gap-1.5">
                      {priority && <StatusPill tone={priorityTone(priority.score)}>PRIORITY {priority.score.toFixed(0)}</StatusPill>}
                      <StatusPill tone={GOAL_STATUS_TONE[g.status]}>{g.status.toUpperCase()}</StatusPill>
                      {g.status === "active" && (
                        <button type="button" onClick={() => void cancelGoal(g.id)} className="text-cmd-textDim hover:text-cmd-red">
                          ✕
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-cmd-textDim">
                    <span>
                      {GOAL_CATEGORY_LABEL[g.category]} · {GOAL_METRIC_LABEL[g.targetMetric]}
                      {priority?.daysRemaining !== undefined && priority?.daysRemaining !== null && ` · ${priority.daysRemaining}d left`}
                    </span>
                    <span className="tabular-nums">
                      {g.currentValue.toFixed(1)} / {g.targetValue.toFixed(1)}
                    </span>
                  </div>
                  <Meter value={g.progressPct} tone={g.status === "completed" ? "green" : "cyan"} />
                  {allocation && (
                    <div className="mt-1 flex items-center gap-1.5 text-cmd-textDim">
                      <span className="uppercase tracking-wide">Recommended attention</span>
                      <div className="h-1 flex-1 overflow-hidden rounded-full bg-cmd-bg/80">
                        <div className="h-full rounded-full bg-cmd-purple/70" style={{ width: `${allocation.allocationPct}%` }} />
                      </div>
                      <span className="tabular-nums text-cmd-text">{allocation.allocationPct.toFixed(0)}%</span>
                    </div>
                  )}
                  {g.milestones.length > 0 && (
                    <div className="mt-1 flex items-center gap-2">
                      {g.milestones.map((m) => (
                        <span key={m.id} title={`${m.thresholdPct.toFixed(0)}% milestone${m.reached ? " — reached" : ""}`} className={`flex items-center gap-0.5 ${m.reached ? "text-cmd-green" : "text-cmd-textDim"}`}>
                          {m.reached ? "●" : "○"} {m.thresholdPct.toFixed(0)}%
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </Glass>

      <Glass className="p-3 lg:col-span-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Strategic Review Cycle</TerminalLabel>
          <span className="text-[9px] uppercase tracking-wide text-cmd-textDim">Design Bible Chapter 64</span>
        </div>
        <div className="mb-3 text-[9px] text-cmd-textDim">
          Generated monthly alongside the Executive Review — a real, checkable snapshot of what changed for CEO-authored goals since the previous cycle.
        </div>
        {strategicReviews.length === 0 ? (
          <EmptyState>No strategic review yet — the first one generates at the end of this month.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {[...strategicReviews].reverse().map((review) => (
              <div key={review.id} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-2 text-[9px]">
                <div className="flex items-center justify-between gap-2 text-cmd-textDim">
                  <span className="uppercase tracking-wide">{review.activeGoalCount} active goal(s)</span>
                  <span className="tabular-nums">{new Date(review.createdAt).toLocaleDateString()}</span>
                </div>
                <div className="mt-1 text-cmd-text">{review.summary}</div>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3 lg:col-span-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Regime Reconciliation</TerminalLabel>
          <span className="text-[9px] uppercase tracking-wide text-cmd-textDim">Design Bible Chapter 65</span>
        </div>
        {regimeReconciliation === null ? (
          <EmptyState>Reconciling the two live regime reads…</EmptyState>
        ) : (
          <>
            <div className="mb-2 flex flex-wrap items-center gap-1.5">
              <StatusPill tone={REGIME_TONE[regimeReconciliation.environmentRegime]}>{regimeReconciliation.environmentLabel}</StatusPill>
              <span className="text-[9px] text-cmd-textDim">vs.</span>
              <StatusPill tone="cyan">{regimeReconciliation.intelligenceLabel}</StatusPill>
              <StatusPill tone={AGREEMENT_TONE[regimeReconciliation.agreement]}>{regimeReconciliation.agreement.toUpperCase()}</StatusPill>
              <StatusPill tone={POSTURE_TONE[regimeReconciliation.posture]}>{regimeReconciliation.posture.toUpperCase()}</StatusPill>
              <span className="text-[9px] text-cmd-textDim">{Math.round(regimeReconciliation.confidencePct)}% confidence</span>
            </div>
            <div className="text-[9px] text-cmd-textDim">{regimeReconciliation.rationale}</div>
          </>
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

// Design Bible Chapter 64 (third pass) — real Executive Priority order:
// active goals ranked by their real priority score (highest first, via
// GET /api/goals/priorities), followed by every non-active goal in
// most-recently-updated order — nothing left to prioritize once a goal
// is completed/expired/cancelled, so those simply keep the old
// most-recent-first ordering this card always used.
function orderGoalsByPriority(goals: Goal[], priorityByGoalId: Map<string, GoalPriority>): Goal[] {
  const active = goals.filter((g) => g.status === "active").sort((a, b) => (priorityByGoalId.get(b.id)?.score ?? 0) - (priorityByGoalId.get(a.id)?.score ?? 0));
  const inactive = goals.filter((g) => g.status !== "active").reverse();
  return [...active, ...inactive];
}

function HealthCell({ label, value }: { label: string; value: number }) {
  const tone = metricTone(value);
  const toneClass: Record<string, string> = { green: "text-cmd-green", amber: "text-cmd-amber", red: "text-cmd-red" };
  return <DataRow label={label} value={value.toFixed(0)} valueClassName={toneClass[tone]} />;
}
