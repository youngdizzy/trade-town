import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { EducationTopic } from "@/types";
import { api } from "@/net/api";
import { NexusManager } from "@/game/systems/NexusManager";
import { EventBus } from "@/game/systems/EventBus";
import { RISK_LEVEL_LABEL, formatPct, riskLevel, riskTextClass } from "../lib/derive";
import { DataRow, EmptyState, Glass, RiskDot, StatusPill, TerminalLabel } from "../ui";
import { PortfolioRiskSnapshotCard } from "./PortfolioRiskSnapshotCard";
import { TradePipelineHealthCard } from "./TradePipelineHealthCard";
import { TradingRestrictionsCard } from "./TradingRestrictionsCard";

const RISK_BANNER = {
  green: "border-cmd-green/50 bg-cmd-green/5",
  yellow: "border-cmd-amber/50 bg-cmd-amber/5",
  red: "border-cmd-red/50 bg-cmd-red/5",
};

/**
 * Sentinel (position/drawdown limits) and Guardian (per-symbol
 * concentration) are the only two sources of RiskWarning in TradeTown's
 * backend — see risk_engine.py. A `warning`/`critical` severity from
 * either becomes a hard-reject vote that unconditionally blocks a trade
 * (decision.py's HARD_REJECT_CHOICES), so "RED" here always means the
 * system really is refusing new trades right now, not just a cosmetic
 * label.
 */
export function RiskPanel({ onNeedHelp }: { onNeedHelp?: (lessonId: EducationTopic) => void } = {}) {
  const { riskWarnings, riskLimits, paperPortfolio, companyScore, dailyObjectiveStatus, companyHealth, emergencyStop } = useGameStore();
  const level = riskLevel(riskWarnings);

  const equity = paperPortfolio.cashBalance + paperPortfolio.positions.reduce((s, p) => s + p.quantity * p.currentPrice, 0);
  const largestPosition = [...paperPortfolio.positions].sort((a, b) => b.quantity * b.currentPrice - a.quantity * a.currentPrice)[0] ?? null;
  const largestPositionPct = largestPosition && equity ? ((largestPosition.quantity * largestPosition.currentPrice) / equity) * 100 : 0;

  const [dailyProfitTargetPct, setDailyProfitTargetPct] = useState(String(riskLimits.dailyProfitTargetPct));
  const [maxDailyLossPct, setMaxDailyLossPct] = useState(String(riskLimits.maxDailyLossPct));
  const [maxTradesPerDay, setMaxTradesPerDay] = useState(String(riskLimits.maxTradesPerDay));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const saveObjectives = async () => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.updateRiskLimits({
        dailyProfitTargetPct: Number(dailyProfitTargetPct),
        maxDailyLossPct: Number(maxDailyLossPct),
        maxTradesPerDay: Number(maxTradesPerDay),
      });
      NexusManager.setRiskLimits(res.riskLimits);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  // v0.7 Chapter 57 — the Position Sizing engine's four writable CEO
  // controls (scalingAggressivenessPct/emergencyReductionHeatPct are
  // deliberately not exposed here — see backend/app/routers/risk.py's
  // own note on why: they have no real consumer until Position Scaling/
  // Reduction on already-open positions is built).
  const [maxWeeklyDeploymentPct, setMaxWeeklyDeploymentPct] = useState(String(riskLimits.maxWeeklyDeploymentPct));
  const [heatCapEnabled, setHeatCapEnabled] = useState(riskLimits.portfolioHeatCapPct !== null);
  const [portfolioHeatCapPct, setPortfolioHeatCapPct] = useState(String(riskLimits.portfolioHeatCapPct ?? 40));
  const [cashReservePct, setCashReservePct] = useState(String(riskLimits.cashReservePct));
  const [tier1Pct, setTier1Pct] = useState(String(riskLimits.tierAllocation.tier1Pct));
  const [tier2Pct, setTier2Pct] = useState(String(riskLimits.tierAllocation.tier2Pct));
  const [tier3Pct, setTier3Pct] = useState(String(riskLimits.tierAllocation.tier3Pct));
  const [tier4Pct, setTier4Pct] = useState(String(riskLimits.tierAllocation.tier4Pct));
  const [sizingBusy, setSizingBusy] = useState(false);
  const [sizingError, setSizingError] = useState<string | null>(null);

  const savePositionSizing = async () => {
    if (sizingBusy) return;
    setSizingBusy(true);
    setSizingError(null);
    try {
      const res = await api.updateRiskLimits({
        maxWeeklyDeploymentPct: Number(maxWeeklyDeploymentPct),
        cashReservePct: Number(cashReservePct),
        tierAllocation: { tier1Pct: Number(tier1Pct), tier2Pct: Number(tier2Pct), tier3Pct: Number(tier3Pct), tier4Pct: Number(tier4Pct) },
        ...(heatCapEnabled ? { portfolioHeatCapPct: Number(portfolioHeatCapPct) } : { clearPortfolioHeatCap: true }),
      });
      NexusManager.setRiskLimits(res.riskLimits);
    } catch (err) {
      setSizingError(err instanceof Error ? err.message : String(err));
    } finally {
      setSizingBusy(false);
    }
  };

  // v0.7 Chapter 58 — the Opportunity Gatekeeper's two CEO controls.
  const [minTradeQualityScore, setMinTradeQualityScore] = useState(String(riskLimits.minTradeQualityScore));
  const [minExpectedValuePct, setMinExpectedValuePct] = useState(String(riskLimits.minExpectedValuePct));
  // CEO directive "Portfolio Construction, Capital Allocation &
  // Execution Realism," Phase 4 — a third real control the Opportunity
  // Gatekeeper reads (see app/opportunity_gatekeeper.py's new
  // correlated_position_count check) alongside app/gatekeeper.py's
  // later-stage category-co-occurrence check. Default 2 preserves the
  // limit that was previously a hardcoded constant.
  const [maxCorrelatedPositions, setMaxCorrelatedPositions] = useState(String(riskLimits.maxCorrelatedPositions));
  const [gateBusy, setGateBusy] = useState(false);
  const [gateError, setGateError] = useState<string | null>(null);

  const saveOpportunityGate = async () => {
    if (gateBusy) return;
    setGateBusy(true);
    setGateError(null);
    try {
      const res = await api.updateRiskLimits({
        minTradeQualityScore: Number(minTradeQualityScore),
        minExpectedValuePct: Number(minExpectedValuePct),
        maxCorrelatedPositions: Number(maxCorrelatedPositions),
      });
      NexusManager.setRiskLimits(res.riskLimits);
    } catch (err) {
      setGateError(err instanceof Error ? err.message : String(err));
    } finally {
      setGateBusy(false);
    }
  };

  // v0.7 Chapter 59 — the Capital Priority & Opportunity Cost Engine's
  // two new CEO controls. Both default to 0 (no-op) — see
  // backend/app/capital_priority.py.
  const [minPriorityScore, setMinPriorityScore] = useState(String(riskLimits.minPriorityScore));
  const [capitalReservePct, setCapitalReservePct] = useState(String(riskLimits.capitalReservePct));
  const [priorityBusy, setPriorityBusy] = useState(false);
  const [priorityError, setPriorityError] = useState<string | null>(null);

  const saveCapitalPriority = async () => {
    if (priorityBusy) return;
    setPriorityBusy(true);
    setPriorityError(null);
    try {
      const res = await api.updateRiskLimits({
        minPriorityScore: Number(minPriorityScore),
        capitalReservePct: Number(capitalReservePct),
      });
      NexusManager.setRiskLimits(res.riskLimits);
    } catch (err) {
      setPriorityError(err instanceof Error ? err.message : String(err));
    } finally {
      setPriorityBusy(false);
    }
  };

  // Design Bible Chapter 67 (TTOS) Safety Settings — the second and
  // third real circuit breakers, config-only (no live weekly/monthly
  // P&L is tracked as displayable state anywhere in the backend today;
  // when one trips, it surfaces exactly like any other Sentinel warning
  // in the Active Warnings list below, not as a separate fabricated
  // gauge here).
  const [maxWeeklyLossPct, setMaxWeeklyLossPct] = useState(String(riskLimits.maxWeeklyLossPct));
  const [maxMonthlyLossPct, setMaxMonthlyLossPct] = useState(String(riskLimits.maxMonthlyLossPct));
  const [safetyBusy, setSafetyBusy] = useState(false);
  const [safetyError, setSafetyError] = useState<string | null>(null);

  const saveSafetyLimits = async () => {
    if (safetyBusy) return;
    setSafetyBusy(true);
    setSafetyError(null);
    try {
      const res = await api.updateRiskLimits({
        maxWeeklyLossPct: Number(maxWeeklyLossPct),
        maxMonthlyLossPct: Number(maxMonthlyLossPct),
      });
      NexusManager.setRiskLimits(res.riskLimits);
    } catch (err) {
      setSafetyError(err instanceof Error ? err.message : String(err));
    } finally {
      setSafetyBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      <Glass className={`border p-4 ${RISK_BANNER[level]}`}>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <RiskDot level={level} className="h-3 w-3" />
            <span className={`font-cmdmono text-xl tracking-wider ${riskTextClass(level)}`}>{RISK_LEVEL_LABEL[level]}</span>
          </div>
          {onNeedHelp && (
            <button
              type="button"
              onClick={() => onNeedHelp("risk_reward")}
              className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] uppercase tracking-wide text-cmd-textDim hover:border-cmd-cyan/50 hover:text-cmd-cyan"
            >
              Need Help?
            </button>
          )}
        </div>
        <div className="mt-1 text-cmd-textDim">
          {level === "red" && "A hard-reject condition is active — new trade candidates are being blocked (see decision.py's veto rule)."}
          {level === "yellow" && "Elevated risk — one or more warnings are active, but nothing is currently blocking new trades."}
          {level === "green" && "No active risk warnings. Sentinel and Guardian have no open concerns."}
        </div>
      </Glass>

      <PortfolioRiskSnapshotCard />

      <TradingRestrictionsCard />

      <Glass className={`p-3 ${dailyObjectiveStatus.tradingHalted ? "border border-cmd-amber/50 bg-cmd-amber/5" : ""}`}>
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Daily Trading Objectives — Day {dailyObjectiveStatus.simDay}</TerminalLabel>
          <StatusPill tone={dailyObjectiveStatus.tradingHalted ? "amber" : "green"}>{dailyObjectiveStatus.tradingHalted ? "TRADING HALTED FOR TODAY" : "ACTIVE"}</StatusPill>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <DataRow label="Trades today" value={`${dailyObjectiveStatus.tradesToday} / ${riskLimits.maxTradesPerDay}`} />
          <DataRow
            label="Realized P&L today"
            value={formatPct(dailyObjectiveStatus.realizedPnlPctToday)}
            valueClassName={dailyObjectiveStatus.realizedPnlPctToday >= 0 ? "text-cmd-green" : "text-cmd-red"}
          />
          <DataRow label="Profit target" value={`${riskLimits.dailyProfitTargetPct}%`} />
        </div>
        {dailyObjectiveStatus.haltReason && <div className="mt-2 border-t border-cmd-border/50 pt-2 text-cmd-amber">{dailyObjectiveStatus.haltReason}</div>}
        {!dailyObjectiveStatus.haltReason && (
          <div className="mt-2 text-[9px] text-cmd-textDim">
            Missing a trade is better than forcing one — once today&apos;s target or max loss is reached, new trades stop automatically until tomorrow.
          </div>
        )}
        <div className="mt-3 grid grid-cols-1 gap-2 border-t border-cmd-border/50 pt-3 sm:grid-cols-3">
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Daily profit target (%)
            <input
              type="number"
              min="0.1"
              step="0.1"
              value={dailyProfitTargetPct}
              onChange={(e) => setDailyProfitTargetPct(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Daily max loss (%)
            <input
              type="number"
              min="0.1"
              step="0.1"
              value={maxDailyLossPct}
              onChange={(e) => setMaxDailyLossPct(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Max trades per day
            <input
              type="number"
              min="1"
              step="1"
              value={maxTradesPerDay}
              onChange={(e) => setMaxTradesPerDay(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
        </div>
        <button
          type="button"
          onClick={() => void saveObjectives()}
          disabled={busy}
          className="mt-2 rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[9px] uppercase tracking-wider text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40"
        >
          {busy ? "Saving…" : "Save Objectives"}
        </button>
        {error && <div className="mt-1.5 text-cmd-red">{error}</div>}
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Position Sizing — Capital Deployment</TerminalLabel>
          <span className="text-[8px] uppercase tracking-wide text-cmd-textDim">v0.7 Chapter 57</span>
        </div>
        <div className="text-[9px] text-cmd-textDim">
          These only ever narrow the existing risk ceiling, never widen it — see the WARROOM tab for how each proposal was actually sized.
        </div>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Max weekly deployment (%)
            <input
              type="number"
              min="0.1"
              step="0.1"
              value={maxWeeklyDeploymentPct}
              onChange={(e) => setMaxWeeklyDeploymentPct(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Cash reserve (%)
            <input
              type="number"
              min="0"
              max="99.9"
              step="0.1"
              value={cashReservePct}
              onChange={(e) => setCashReservePct(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            <span className="flex items-center justify-between">
              Portfolio Heat cap (%)
              <span className="flex items-center gap-1 normal-case tracking-normal">
                <input type="checkbox" checked={heatCapEnabled} onChange={(e) => setHeatCapEnabled(e.target.checked)} className="accent-cmd-cyan" />
                Enabled
              </span>
            </span>
            <input
              type="number"
              min="0.1"
              step="0.1"
              value={portfolioHeatCapPct}
              disabled={!heatCapEnabled}
              onChange={(e) => setPortfolioHeatCapPct(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50 disabled:opacity-40"
            />
          </label>
        </div>
        <div className="mt-2 text-[9px] text-cmd-textDim">
          Disabled = no hard cap; Portfolio Heat stays a pure reading (Chapter 56). Enabled = a real ceiling the engine treats as a pass/fail gate — the CEO's own choice, never system-triggered.
        </div>
        <div className="mt-3 border-t border-cmd-border/50 pt-3">
          <TerminalLabel>Position Tier allocation caps (% of equity)</TerminalLabel>
          <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
              Exploratory
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={tier1Pct}
                onChange={(e) => setTier1Pct(e.target.value)}
                className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
              />
            </label>
            <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
              Standard
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={tier2Pct}
                onChange={(e) => setTier2Pct(e.target.value)}
                className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
              />
            </label>
            <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
              High Conviction
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={tier3Pct}
                onChange={(e) => setTier3Pct(e.target.value)}
                className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
              />
            </label>
            <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
              Institutional
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={tier4Pct}
                onChange={(e) => setTier4Pct(e.target.value)}
                className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
              />
            </label>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void savePositionSizing()}
          disabled={sizingBusy}
          className="mt-3 rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[9px] uppercase tracking-wider text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40"
        >
          {sizingBusy ? "Saving…" : "Save Position Sizing Controls"}
        </button>
        {sizingError && <div className="mt-1.5 text-cmd-red">{sizingError}</div>}
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Opportunity Gatekeeper</TerminalLabel>
          <span className="text-[8px] uppercase tracking-wide text-cmd-textDim">v0.7 Chapter 58</span>
        </div>
        <div className="text-[9px] text-cmd-textDim">
          A candidate must clear both minimums before it ever becomes a trade proposal — see EXECUTIVE for real rejections. Market Quality is also checked but has no separate CEO threshold.
        </div>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Minimum Trade Quality Score (0-100)
            <input
              type="number"
              min="0"
              max="100"
              step="1"
              value={minTradeQualityScore}
              onChange={(e) => setMinTradeQualityScore(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Minimum Expected Value (%)
            <input
              type="number"
              step="0.1"
              value={minExpectedValuePct}
              onChange={(e) => setMinExpectedValuePct(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Max Correlated Positions (statistical, pre-proposal)
            <input
              type="number"
              min="0"
              step="1"
              value={maxCorrelatedPositions}
              onChange={(e) => setMaxCorrelatedPositions(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
        </div>
        <div className="mt-2 text-[9px] text-cmd-textDim">
          A negative Expected Value minimum relaxes the gate below &quot;merely positive&quot; — real, but rarely what a disciplined desk wants. Correlated Positions counts real |Pearson r| ≥ 0.6 clusters against currently-held symbols, not category labels.
        </div>
        <button
          type="button"
          onClick={() => void saveOpportunityGate()}
          disabled={gateBusy}
          className="mt-3 rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[9px] uppercase tracking-wider text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40"
        >
          {gateBusy ? "Saving…" : "Save Opportunity Gatekeeper Controls"}
        </button>
        {gateError && <div className="mt-1.5 text-cmd-red">{gateError}</div>}
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Capital Priority — Opportunity Cost</TerminalLabel>
          <span className="text-[8px] uppercase tracking-wide text-cmd-textDim">v0.7 Chapter 59</span>
        </div>
        <div className="text-[9px] text-cmd-textDim">
          Good trades deserve consideration. Great trades deserve capital. Both controls default to off — see EXECUTIVE for the real, ranked Pending Proposals queue.
        </div>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Minimum Priority Score (0-100)
            <input
              type="number"
              min="0"
              max="100"
              step="1"
              value={minPriorityScore}
              onChange={(e) => setMinPriorityScore(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Capital Reserve (%)
            <input
              type="number"
              min="0"
              max="99.9"
              step="0.1"
              value={capitalReservePct}
              onChange={(e) => setCapitalReservePct(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
        </div>
        <div className="mt-2 text-[9px] text-cmd-textDim">
          Minimum Priority Score (0 = off) keeps a below-floor proposal pending for you in Assisted Mode, the same way low confidence already does. Capital Reserve (0 = off) is additive to the Position Sizing tab&apos;s hard Cash Reserve floor above — a voluntary target that halts further auto-approved BUYs in every mode once cash falls to it.
        </div>
        <button
          type="button"
          onClick={() => void saveCapitalPriority()}
          disabled={priorityBusy}
          className="mt-3 rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[9px] uppercase tracking-wider text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40"
        >
          {priorityBusy ? "Saving…" : "Save Capital Priority Controls"}
        </button>
        {priorityError && <div className="mt-1.5 text-cmd-red">{priorityError}</div>}
      </Glass>

      <Glass className={`p-3 ${emergencyStop.active ? "border border-cmd-red/50 bg-cmd-red/5" : ""}`}>
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Safety &amp; Capital Protection</TerminalLabel>
          <span className="text-[8px] uppercase tracking-wide text-cmd-textDim">Design Bible Ch. 67</span>
        </div>
        <div className="text-[9px] text-cmd-textDim">
          Two more real circuit breakers, enforced the same way as Daily Max Loss above (see Daily Trading Objectives) — just scoped to this sim week and this sim month instead of today. A breach blocks new trades and shows up in Active Warnings below, exactly like every other Sentinel warning.
        </div>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Max weekly loss (%)
            <input
              type="number"
              min="0.1"
              step="0.1"
              value={maxWeeklyLossPct}
              onChange={(e) => setMaxWeeklyLossPct(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-[9px] text-cmd-textDim">
            Max monthly loss (%)
            <input
              type="number"
              min="0.1"
              step="0.1"
              value={maxMonthlyLossPct}
              onChange={(e) => setMaxMonthlyLossPct(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
        </div>
        <button
          type="button"
          onClick={() => void saveSafetyLimits()}
          disabled={safetyBusy}
          className="mt-3 rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[9px] uppercase tracking-wider text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-40"
        >
          {safetyBusy ? "Saving…" : "Save Safety Limits"}
        </button>
        {safetyError && <div className="mt-1.5 text-cmd-red">{safetyError}</div>}

        <div className="mt-3 flex items-center justify-between gap-2 border-t border-cmd-border/50 pt-3">
          <div>
            <TerminalLabel>Global Emergency Stop</TerminalLabel>
            <div className={`font-cmdmono text-xs ${emergencyStop.active ? "text-cmd-red" : "text-cmd-green"}`}>
              {emergencyStop.active ? `HALTED since ${new Date(emergencyStop.activatedAt ?? "").toLocaleString()}` : "Not active"}
            </div>
          </div>
          <button
            type="button"
            onClick={() => EventBus.emit("ui:emergencyStopConfirm", { pending: emergencyStop.active ? "resume" : "activate" })}
            className={
              emergencyStop.active
                ? "rounded-sm border border-cmd-red/60 px-3 py-1.5 text-[9px] uppercase tracking-wider text-cmd-red hover:bg-cmd-red/10"
                : "rounded-sm border border-cmd-red/40 px-3 py-1.5 text-[9px] uppercase tracking-wider text-cmd-textDim hover:border-cmd-red/60 hover:text-cmd-red"
            }
          >
            {emergencyStop.active ? "Resume Trading" : "Emergency Stop"}
          </button>
        </div>

        <div className="mt-3 border-t border-cmd-border/50 pt-3 text-[9px] text-cmd-textDim">
          Not built — no real mechanism exists in this codebase for any of these: Black Swan Protection (no external market-crash data feed), Broker Failover (no live broker integration to fail over from — see PaperBroker in broker.py), or Emergency Contacts (no contact/notification-delivery system). Documented here rather than faked.
        </div>
      </Glass>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Glass className="p-3">
          <TerminalLabel>Open Positions</TerminalLabel>
          <div className="font-cmdmono text-cmd-text">
            {paperPortfolio.positions.length} / {riskLimits.maxOpenPositions}
          </div>
        </Glass>
        <Glass className="p-3">
          <TerminalLabel>Largest Position</TerminalLabel>
          <div className="font-cmdmono text-cmd-text">{largestPosition ? `${largestPosition.symbol} — ${largestPositionPct.toFixed(1)}%` : "None"}</div>
          <div className="mt-0.5 text-[9px] text-cmd-textDim">Limit {riskLimits.maxPositionPct}% per position</div>
        </Glass>
        <Glass className="p-3">
          <TerminalLabel>Total P&amp;L</TerminalLabel>
          <div className={`font-cmdmono ${paperPortfolio.totalPnlPct >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{formatPct(paperPortfolio.totalPnlPct)}</div>
          <div className="mt-0.5 text-[9px] text-cmd-textDim">Limit −{riskLimits.maxDrawdownPct}% max drawdown</div>
        </Glass>
        <Glass className="p-3">
          <TerminalLabel>Risk Management Score</TerminalLabel>
          <div className="font-cmdmono text-cmd-text">{Math.round(companyScore.riskManagement)}/100</div>
        </Glass>
        <Glass className="p-3">
          <div className="flex items-center justify-between">
            <TerminalLabel>Risk Governance</TerminalLabel>
            <span className="text-[8px] uppercase tracking-wide text-cmd-textDim">v0.7 Feature 50</span>
          </div>
          <div className="font-cmdmono text-cmd-text">{Math.round(companyHealth.riskGovernance)}/100</div>
          <div className="mt-0.5 text-[9px] text-cmd-textDim">Real Trade Gatekeeper approval rate — closed trades vs. real rejections.</div>
        </Glass>
      </div>

      <Glass className="p-3">
        <TerminalLabel>Configured Risk Limits</TerminalLabel>
        <DataRow label="Max position size" value={`${riskLimits.maxPositionPct}%`} />
        <DataRow label="Risk per trade" value={`${riskLimits.riskPerTradePct}%`} />
        <DataRow label="Daily profit target" value={`${riskLimits.dailyProfitTargetPct}%`} />
        <DataRow label="Max daily loss" value={`${riskLimits.maxDailyLossPct}%`} />
        <DataRow label="Max weekly loss" value={`${riskLimits.maxWeeklyLossPct}%`} />
        <DataRow label="Max monthly loss" value={`${riskLimits.maxMonthlyLossPct}%`} />
        <DataRow label="Max trades per day" value={riskLimits.maxTradesPerDay} />
        <DataRow label="Max drawdown" value={`${riskLimits.maxDrawdownPct}%`} />
        <DataRow label="Max open positions" value={riskLimits.maxOpenPositions} />
        <DataRow label="Max per-symbol concentration" value={`${riskLimits.maxSectorConcentrationPct}%`} />
        <DataRow label="Max correlated positions" value={riskLimits.maxCorrelatedPositions} />
        <div className="mt-1.5 text-[9px] text-cmd-textDim">
          Concentration is measured per-symbol, not per real market sector — TradeTown doesn&apos;t track a sector taxonomy (see risk_engine.py).
        </div>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Active Warnings ({riskWarnings.length})</TerminalLabel>
        {riskWarnings.length === 0 ? (
          <EmptyState>No active risk warnings.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {riskWarnings.map((w) => (
              <div key={w.id} className={`flex items-center justify-between gap-2 border-b border-cmd-border/60 py-1 last:border-0 ${w.severity === "critical" ? "text-cmd-red" : "text-cmd-amber"}`}>
                <span className="font-cmdmono">{w.symbol}</span>
                <span className="flex-1 text-left">{w.message}</span>
                {w.code && <span className="text-[8px] text-cmd-textDim">{w.code}</span>}
                <span className="text-[9px] uppercase">{w.severity}</span>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <TradePipelineHealthCard />
    </div>
  );
}
