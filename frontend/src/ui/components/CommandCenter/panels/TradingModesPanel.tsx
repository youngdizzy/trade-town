import { useEffect, useState } from "react";
import { api } from "@/net/api";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { AdaptiveModeRecommendation, DailyCircuitBreakerTier, TradingMode, TradingModeHealthAssessment, TradingStylePerformance } from "@/types";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

/**
 * Design Bible Chapter 75 — Company Trading Modes & Institutional
 * Capital Protection (backend/app/trading_modes.py). Extends, never
 * duplicates, Chapter 65's real Regime Reconciliation and Chapter 66's
 * real daily/weekly/monthly loss halt and Trade Gatekeeper — a graduated
 * Circuit Breaker sits in front of the existing hard halt, and the
 * Adaptive Mode recommendation is read-only, exactly like Chapter 65's
 * own posture field. tradingModes/dailyCircuitBreaker/losingStreak/
 * recoveryBriefings are live via the WS tick broadcast (gameStore);
 * Performance Split, Trading Mode Health, and the Adaptive
 * recommendation have no WS-broadcast field and are fetched on demand,
 * the same pattern Chapter 73's CompliancePanel established.
 */

const MODE_LABEL: Record<TradingMode, string> = {
  day_trading: "Day Trading",
  swing_trading: "Swing Trading",
  hybrid: "Hybrid",
};

const TIER_LABEL: Record<DailyCircuitBreakerTier, string> = {
  none: "Normal",
  tier1: "Tier 1 — Reduced Size",
  tier2: "Tier 2 — Manual Review Only",
  tier3: "Tier 3 — New Trades Blocked",
  tier4: "Tier 4 — Emergency Stop",
};

function tierTone(tier: DailyCircuitBreakerTier): "green" | "cyan" | "amber" | "red" {
  if (tier === "none") return "green";
  if (tier === "tier1") return "cyan";
  if (tier === "tier2" || tier === "tier3") return "amber";
  return "red";
}

function healthTone(status: TradingModeHealthAssessment["status"]): "green" | "cyan" | "amber" | "red" {
  if (status === "excellent" || status === "healthy") return "green";
  if (status === "stable") return "cyan";
  if (status === "needs_review" || status === "declining") return "amber";
  return "red";
}

export function TradingModesPanel() {
  const { tradingModes, dailyCircuitBreaker, losingStreak, recoveryBriefings } = useGameStore();

  const [selectedMode, setSelectedMode] = useState<TradingMode>(tradingModes.mode);
  const [hybridPct, setHybridPct] = useState(tradingModes.hybridDayAllocationPct);
  const [saving, setSaving] = useState(false);
  const [acknowledging, setAcknowledging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [recommendation, setRecommendation] = useState<AdaptiveModeRecommendation | null>(null);
  const [performance, setPerformance] = useState<TradingStylePerformance[] | null>(null);
  const [health, setHealth] = useState<TradingModeHealthAssessment[] | null>(null);
  const [togglingRecommendations, setTogglingRecommendations] = useState(false);

  useEffect(() => {
    setSelectedMode(tradingModes.mode);
    setHybridPct(tradingModes.hybridDayAllocationPct);
  }, [tradingModes.mode, tradingModes.hybridDayAllocationPct]);

  useEffect(() => {
    api.getAdaptiveModeRecommendation().then(setRecommendation).catch(() => setRecommendation(null));
    api.getTradingStylePerformance().then(setPerformance).catch(() => setPerformance([]));
    api.getTradingModeHealth().then(setHealth).catch(() => setHealth([]));
  }, [tradingModes.mode, tradingModes.adaptiveRecommendationsEnabled, recoveryBriefings.length]);

  async function toggleAdaptiveRecommendations() {
    setError(null);
    setTogglingRecommendations(true);
    try {
      await api.setAdaptiveRecommendationsEnabled(!tradingModes.adaptiveRecommendationsEnabled);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setTogglingRecommendations(false);
    }
  }

  async function saveMode() {
    setError(null);
    setSaving(true);
    try {
      await api.setTradingMode(selectedMode, selectedMode === "hybrid" ? hybridPct : undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  async function acknowledgeStreak() {
    setError(null);
    setAcknowledging(true);
    try {
      await api.acknowledgeLosingStreak();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setAcknowledging(false);
    }
  }

  const hasPendingChange = selectedMode !== tradingModes.mode || (selectedMode === "hybrid" && hybridPct !== tradingModes.hybridDayAllocationPct);

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Trading Mode</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">Changed {new Date(tradingModes.changedAt).toLocaleString()}</span>
        </div>
        <div className="mb-2 flex flex-wrap gap-1.5">
          {(Object.keys(MODE_LABEL) as TradingMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setSelectedMode(mode)}
              className={`rounded-sm border px-2.5 py-1 text-[9px] uppercase tracking-wide ${
                selectedMode === mode ? "border-cmd-cyan/60 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
              }`}
            >
              {MODE_LABEL[mode]}
            </button>
          ))}
        </div>
        {selectedMode === "hybrid" && (
          <label className="mb-2 block text-[9px] text-cmd-textDim">
            Day-Trading Allocation: {hybridPct.toFixed(0)}% day / {(100 - hybridPct).toFixed(0)}% swing
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={hybridPct}
              onChange={(e) => setHybridPct(Number(e.target.value))}
              className="mt-1 w-full accent-cmd-cyan"
            />
            <span className="mt-0.5 block text-cmd-textDim">
              A disclosed deterministic rotation assigns each new proposal — never an independent capital pool per style (live execution isn&apos;t routed to
              separate accounts yet).
            </span>
          </label>
        )}
        {hasPendingChange && (
          <button
            type="button"
            onClick={saveMode}
            disabled={saving}
            className="rounded-sm border border-cmd-cyan/50 px-2.5 py-1 text-[9px] uppercase tracking-wide text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Apply Trading Mode"}
          </button>
        )}
        {error && <div className="mt-2 text-[9px] text-cmd-red">{error}</div>}

        <div className="mt-2 border-t border-cmd-border/50 pt-2">
          <div className="mb-1.5 flex items-center justify-between gap-2">
            <TerminalLabel>Adaptive Mode Recommendation — read-only, never applied automatically</TerminalLabel>
            <button
              type="button"
              onClick={toggleAdaptiveRecommendations}
              disabled={togglingRecommendations}
              className={`shrink-0 rounded-sm border px-2 py-0.5 text-[9px] uppercase tracking-wide disabled:opacity-50 ${
                tradingModes.adaptiveRecommendationsEnabled
                  ? "border-cmd-cyan/50 text-cmd-cyan hover:bg-cmd-cyan/10"
                  : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
              }`}
            >
              {tradingModes.adaptiveRecommendationsEnabled ? "On" : "Off"}
            </button>
          </div>
          {!tradingModes.adaptiveRecommendationsEnabled ? (
            <div className="text-[9px]">
              <p className="text-cmd-textDim">{recommendation?.reasoning ?? "Adaptive Recommendations are turned off."}</p>
              {recommendation?.note && <p className="mt-1 text-cmd-amber">{recommendation.note}</p>}
            </div>
          ) : recommendation === null ? (
            <EmptyState>Loading…</EmptyState>
          ) : recommendation.recommendedMode ? (
            <div className="text-[9px]">
              <div className="mb-1 flex items-center gap-1.5">
                <StatusPill tone="cyan">{MODE_LABEL[recommendation.recommendedMode]}</StatusPill>
                <span className="text-cmd-textDim">{recommendation.confidencePct.toFixed(0)}% confidence</span>
              </div>
              <p className="text-cmd-text">{recommendation.reasoning}</p>
            </div>
          ) : (
            <div className="text-[9px]">
              <p className="text-cmd-textDim">{recommendation.reasoning}</p>
              {recommendation.note && <p className="mt-1 text-cmd-amber">{recommendation.note}</p>}
            </div>
          )}
        </div>
      </Glass>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Daily Circuit Breaker</TerminalLabel>
            <StatusPill tone={tierTone(dailyCircuitBreaker.tier)}>{TIER_LABEL[dailyCircuitBreaker.tier]}</StatusPill>
          </div>
          <div className="mb-2 flex items-center gap-3">
            <span className={`font-cmdmono ${dailyCircuitBreaker.dailyPnlPct < 0 ? "text-cmd-red" : "text-cmd-green"}`}>{dailyCircuitBreaker.dailyPnlPct.toFixed(2)}%</span>
            <div className="flex-1">
              <Meter value={Math.min(100, Math.abs(dailyCircuitBreaker.dailyPnlPct) / dailyCircuitBreaker.tier4Pct * 100)} tone={tierTone(dailyCircuitBreaker.tier)} />
            </div>
          </div>
          <DataRow label="Tier 1" value={`-${dailyCircuitBreaker.tier1Pct.toFixed(1)}%`} />
          <DataRow label="Tier 2" value={`-${dailyCircuitBreaker.tier2Pct.toFixed(1)}%`} />
          <DataRow label="Tier 3" value={`-${dailyCircuitBreaker.tier3Pct.toFixed(1)}%`} />
          <DataRow label="Tier 4 (Emergency Stop)" value={`-${dailyCircuitBreaker.tier4Pct.toFixed(1)}%`} />
        </Glass>

        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Losing Streak Protection</TerminalLabel>
            {losingStreak.pauseActive && <StatusPill tone="amber">PAUSED</StatusPill>}
          </div>
          <DataRow label="Consecutive Losses" value={losingStreak.consecutiveLosses} valueClassName={losingStreak.consecutiveLosses > 0 ? "text-cmd-amber" : "text-cmd-text"} />
          <DataRow label="Pause Threshold" value={losingStreak.pauseThreshold} />
          <DataRow label="Emergency Stop Threshold" value={losingStreak.suspendThreshold} />
          {losingStreak.pauseActive ? (
            <button
              type="button"
              onClick={acknowledgeStreak}
              disabled={acknowledging}
              className="mt-2 rounded-sm border border-cmd-amber/50 px-2.5 py-1 text-[9px] uppercase tracking-wide text-cmd-amber hover:bg-cmd-amber/10 disabled:opacity-50"
            >
              {acknowledging ? "Acknowledging…" : "Acknowledge — Resume New Proposals"}
            </button>
          ) : (
            <p className="mt-2 text-[9px] text-cmd-textDim">New proposals continue normally.</p>
          )}
        </Glass>
      </div>

      <Glass className="p-3">
        <TerminalLabel>Trading Style Performance & Health — real, never a claimed separate capital pool</TerminalLabel>
        {performance === null || health === null ? (
          <EmptyState>Loading…</EmptyState>
        ) : performance.length === 0 ? (
          <EmptyState>No tagged trades closed yet.</EmptyState>
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {performance.map((p) => {
              const h = health.find((x) => x.style === p.style);
              return (
                <div key={p.style} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="uppercase text-cmd-cyan">{p.style}</span>
                    {h && <StatusPill tone={healthTone(h.status)}>{h.status.replace(/_/g, " ")}</StatusPill>}
                  </div>
                  <DataRow label="Trades" value={p.tradeCount} />
                  <DataRow label="Win Rate" value={`${p.winRate.toFixed(1)}%`} />
                  <DataRow label="Total P&L" value={`${p.totalPnl >= 0 ? "+" : ""}${p.totalPnl.toFixed(0)}`} valueClassName={p.totalPnl >= 0 ? "text-cmd-green" : "text-cmd-red"} />
                  <DataRow label="Avg P&L %" value={`${p.avgPnlPct >= 0 ? "+" : ""}${p.avgPnlPct.toFixed(1)}%`} />
                </div>
              );
            })}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Recovery Briefings — generated only for Circuit-Breaker/Losing-Streak-triggered stops</TerminalLabel>
        {recoveryBriefings.length === 0 ? (
          <EmptyState>No trading halts triggered by this chapter&apos;s own thresholds yet.</EmptyState>
        ) : (
          <div className="max-h-72 space-y-1.5 overflow-y-auto">
            {[...recoveryBriefings].reverse().map((b) => (
              <div key={b.id} className="border-b border-cmd-border/50 pb-1.5 last:border-0 text-[9px]">
                <div className="mb-0.5 flex items-center gap-1.5">
                  <StatusPill tone="red">{b.trigger === "circuit_breaker_tier4" ? "Circuit Breaker Tier 4" : "Losing Streak"}</StatusPill>
                  <span className="text-cmd-textDim">{new Date(b.createdAt).toLocaleString()}</span>
                </div>
                <p className="text-cmd-text">{b.summary}</p>
                {b.linkedDisciplineReviewIds.length > 0 && (
                  <div className="mt-0.5 text-cmd-textDim">{b.linkedDisciplineReviewIds.length} linked Discipline Chamber review(s).</div>
                )}
              </div>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}
