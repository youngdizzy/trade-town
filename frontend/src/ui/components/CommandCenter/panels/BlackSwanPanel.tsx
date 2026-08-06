import { useState } from "react";
import { api } from "@/net/api";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { BlackSwanScenarioType, PortfolioScenarioResult, PortfolioStressTestResult } from "@/types";
import { blackSwanRiskTone, latestBlackSwanReport, survivalGradeLabel, survivalGradeTone } from "../lib/derive";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

const SCENARIO_LABEL: Record<BlackSwanScenarioType, string> = {
  flash_crash: "Flash Crash",
  severe_selloff: "Severe Selloff",
  liquidity_freeze: "Liquidity Freeze",
  correlation_breakdown: "Correlation Breakdown",
};

function formatMoney(value: number): string {
  return value.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

/**
 * Design Bible Chapter 72 — Black Swan Intelligence & Resilience System
 * (backend/app/black_swan.py). This codebase has no historical
 * black-swan dataset, no real broker connection, and no macro/sector/
 * credit data — every number here traces to a real already-computed
 * signal (Risk Engine's live warnings, Market Intelligence's quality/
 * volatility/liquidity/news reads, Portfolio Intelligence's correlation/
 * heat reads, Regime Reconciliation, Economic Intelligence) or a real,
 * disclosed formula. No "Black Swan probability" or "Estimated Survival
 * Probability" is ever fabricated — the Risk Level and Survival Score
 * are real-time readings, never forecasts of a specific future event.
 */
export function BlackSwanPanel() {
  const { blackSwanIntelligence: bsi, blackSwanReports, defensiveMode, blackSwanEvents, institutionalSurvivalScore: survival } = useGameStore();
  const { warning, confidence } = bsi;
  const latestReport = latestBlackSwanReport(blackSwanReports);

  const [busy, setBusy] = useState<"activate" | "deactivate" | "stress" | BlackSwanScenarioType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stressResult, setStressResult] = useState<PortfolioStressTestResult | null>(null);
  const [scenarioResult, setScenarioResult] = useState<PortfolioScenarioResult | null>(null);

  // Meter only supports 4 tones (no "purple"); CRITICAL reads as "red" here.
  const warningMeterTone = warning.tier === "critical" || warning.tier === "red" ? "red" : warning.tier === "orange" ? "amber" : warning.tier === "yellow" ? "cyan" : "green";

  async function toggleDefensiveMode() {
    setError(null);
    setBusy(defensiveMode.active ? "deactivate" : "activate");
    try {
      if (defensiveMode.active) await api.deactivateDefensiveMode();
      else await api.activateDefensiveMode();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function toggleAutoTrigger() {
    setError(null);
    try {
      await api.configureDefensiveMode(null, !defensiveMode.autoTriggerEnabled);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function runStressTest() {
    setError(null);
    setBusy("stress");
    try {
      setStressResult(await api.runBlackSwanStressTest());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function runScenario(scenarioType: BlackSwanScenarioType) {
    setError(null);
    setBusy(scenarioType);
    try {
      setScenarioResult(await api.runBlackSwanScenario(scenarioType));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Early Warning Score — Black Swan Risk Level</TerminalLabel>
          <StatusPill tone={blackSwanRiskTone(warning.tier)}>{warning.tier}</StatusPill>
        </div>
        <div className="mb-2 flex items-center gap-3">
          <span className="font-cmdmono text-cmd-cyan">{warning.overall.toFixed(1)}/100</span>
          <div className="flex-1">
            <Meter value={warning.overall} tone={warningMeterTone} />
          </div>
        </div>
        <p className="text-cmd-textDim">{warning.reasoning}</p>
        <div className="mt-1.5 text-right text-[9px] text-cmd-textDim">Updated {new Date(bsi.updatedAt).toLocaleTimeString()}</div>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Eight Real Factors — never a black-box blend</TerminalLabel>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {warning.factors.map((factor) => (
            <div key={factor.name} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-cmd-cyan">{factor.name}</span>
                <span className="text-cmd-textDim">×{factor.weight.toFixed(2)}</span>
              </div>
              <div className="mb-1">
                <Meter value={factor.score} tone={factor.score <= 35 ? "green" : factor.score <= 60 ? "amber" : "red"} />
              </div>
              <div className="text-cmd-textDim">{factor.score.toFixed(0)}/100</div>
              <div className="mt-1 text-cmd-textDim">{factor.detail}</div>
            </div>
          ))}
        </div>
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Black Swan Confidence — never presented as fact</TerminalLabel>
          <StatusPill tone={confidence.evidenceQuality === "strong" ? "green" : confidence.evidenceQuality === "moderate" ? "cyan" : "amber"}>
            {confidence.evidenceQuality} evidence
          </StatusPill>
        </div>
        <div className="mb-2 flex items-center gap-3">
          <span className="font-cmdmono text-cmd-cyan">{confidence.confidencePct.toFixed(0)}%</span>
          <div className="flex-1">
            <Meter value={confidence.confidencePct} tone="cyan" />
          </div>
        </div>
        <div className="text-[9px] text-cmd-text">{confidence.alternativeOutcome}</div>
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Institutional Survival Score</TerminalLabel>
          <StatusPill tone={survivalGradeTone(survival.grade)}>{survivalGradeLabel(survival.grade)}</StatusPill>
        </div>
        <div className="mb-2 flex items-center gap-3">
          <span className="font-cmdmono text-cmd-cyan">{survival.overall.toFixed(1)}/100</span>
          <div className="flex-1">
            <Meter value={survival.overall} tone={survivalGradeTone(survival.grade)} />
          </div>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 mb-2">
          {survival.factors.map((factor) => (
            <div key={factor.name} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-cmd-cyan">{factor.name}</span>
                <span className="text-cmd-textDim">×{factor.weight.toFixed(2)}</span>
              </div>
              <Meter value={factor.score} tone={factor.score >= 60 ? "green" : factor.score >= 35 ? "amber" : "red"} />
              <div className="mt-1 text-cmd-textDim">{factor.detail}</div>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div>
            <div className="mb-1 text-cmd-green">Primary Strengths</div>
            <ul className="list-inside list-disc space-y-0.5 text-[9px] text-cmd-text">
              {survival.primaryStrengths.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
          <div>
            <div className="mb-1 text-cmd-amber">Primary Weaknesses</div>
            <ul className="list-inside list-disc space-y-0.5 text-[9px] text-cmd-text">
              {survival.primaryWeaknesses.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        </div>
        <div className="mt-2 border-t border-cmd-border/50 pt-1.5">
          <div className="mb-0.5 text-[9px] uppercase tracking-wider text-cmd-textDim">Top 5 Improvements</div>
          <ul className="list-inside list-disc space-y-0.5 text-[9px] text-cmd-text">
            {survival.topImprovements.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Defensive Mode — never auto-closes a position</TerminalLabel>
          <StatusPill tone={defensiveMode.active ? "red" : "neutral"}>{defensiveMode.active ? "ACTIVE" : "INACTIVE"}</StatusPill>
        </div>
        {error && <div className="mb-2 rounded-sm border border-cmd-red/50 bg-cmd-red/10 p-1.5 text-[9px] text-cmd-red">{error}</div>}
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={toggleDefensiveMode}
            disabled={busy !== null}
            className="rounded-sm border border-cmd-cyan/50 px-3 py-1.5 text-[10px] uppercase tracking-wider text-cmd-cyan transition-colors hover:bg-cmd-cyan/10 disabled:opacity-50"
          >
            {defensiveMode.active ? "Deactivate" : "Activate"} Defensive Mode
          </button>
          <label className="flex items-center gap-1.5 text-[9px] text-cmd-textDim">
            <input type="checkbox" checked={defensiveMode.autoTriggerEnabled} onChange={() => void toggleAutoTrigger()} />
            Auto-trigger at {defensiveMode.triggerTier.toUpperCase()}
          </label>
        </div>
        {defensiveMode.active && defensiveMode.activationReason && <div className="mb-2 text-[9px] text-cmd-textDim">{defensiveMode.activationReason}</div>}
        <div className="space-y-1">
          {(defensiveMode.active ? defensiveMode.recommendations : []).map((rec) => (
            <div key={rec.action} className="flex items-start justify-between gap-2 rounded-sm border border-cmd-border/40 bg-cmd-bg/60 p-1.5 text-[9px]">
              <div>
                <span className="text-cmd-text">{rec.action}</span>
                <div className="text-cmd-textDim">{rec.detail}</div>
              </div>
              <StatusPill tone={rec.automatic ? "green" : "neutral"}>{rec.automatic ? "auto" : "manual"}</StatusPill>
            </div>
          ))}
          {!defensiveMode.active && <EmptyState>Defensive Mode is inactive — no real RiskLimits are currently tightened.</EmptyState>}
        </div>
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Portfolio Stress Test — real ladder, honest recovery estimate</TerminalLabel>
          <button
            type="button"
            onClick={() => void runStressTest()}
            disabled={busy !== null}
            className="rounded-sm border border-cmd-cyan/50 px-2 py-1 text-[9px] uppercase tracking-wider text-cmd-cyan transition-colors hover:bg-cmd-cyan/10 disabled:opacity-50"
          >
            {busy === "stress" ? "Running…" : "Run Stress Test"}
          </button>
        </div>
        {!stressResult ? (
          <EmptyState>Run the -10/-20/-35/-50/-70% shock ladder against the primary portfolio's real current positions.</EmptyState>
        ) : (
          <div className="space-y-1">
            <div className="text-[9px] text-cmd-textDim">
              {stressResult.accountLabel} — starting equity {formatMoney(stressResult.startingEquity)}
            </div>
            {stressResult.levels.map((level) => (
              <div key={level.shockPct} className="grid grid-cols-5 gap-2 rounded-sm border border-cmd-border/40 bg-cmd-bg/60 p-1.5 text-[9px]">
                <span className="text-cmd-text">{level.shockPct.toFixed(0)}%</span>
                <span className="tabular-nums text-cmd-text">{formatMoney(level.resultingEquity)}</span>
                <span className="tabular-nums text-cmd-textDim">-{level.resultingDrawdownPct.toFixed(1)}% dd</span>
                <StatusPill tone={level.breachesMaxDrawdown ? "red" : "green"}>{level.breachesMaxDrawdown ? "breach" : "within limit"}</StatusPill>
                <span className="text-cmd-textDim">{level.recoveryDaysEstimate === null ? level.recoveryNote : `${level.recoveryDaysEstimate.toFixed(0)}d recovery`}</span>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Scenario Simulator — named for real mechanism, never a real historical event</TerminalLabel>
        <div className="mb-2 flex flex-wrap gap-2">
          {(Object.keys(SCENARIO_LABEL) as BlackSwanScenarioType[]).map((scenarioType) => (
            <button
              key={scenarioType}
              type="button"
              onClick={() => void runScenario(scenarioType)}
              disabled={busy !== null}
              className="rounded-sm border border-cmd-amber/50 px-2 py-1 text-[9px] uppercase tracking-wider text-cmd-amber transition-colors hover:bg-cmd-amber/10 disabled:opacity-50"
            >
              {busy === scenarioType ? "Running…" : SCENARIO_LABEL[scenarioType]}
            </button>
          ))}
        </div>
        {!scenarioResult ? (
          <EmptyState>Select a scenario to see its real, volatility-scaled impact on the primary portfolio right now.</EmptyState>
        ) : (
          <div className="space-y-1 text-[9px]">
            <div className="text-cmd-cyan">{scenarioResult.label}</div>
            <DataRow label="Starting Equity" value={formatMoney(scenarioResult.startingEquity)} />
            <DataRow label="Shocked Equity" value={formatMoney(scenarioResult.shockedEquity)} />
            <DataRow label="Impact" value={`${scenarioResult.impactPct.toFixed(2)}% (${formatMoney(scenarioResult.impactAmount)})`} valueClassName={scenarioResult.impactPct < 0 ? "text-cmd-red" : "text-cmd-green"} />
            <DataRow label="Max Drawdown Breach" value={scenarioResult.breachesMaxDrawdown ? "Yes" : "No"} />
            <DataRow label="Capital Survives" value={scenarioResult.capitalSurvives ? "Yes" : "No"} />
            <div className="mt-1 text-cmd-textDim">{scenarioResult.detail}</div>
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Post-Event Analysis — permanent record per completed episode</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">{blackSwanEvents.length} on record</span>
        </div>
        {blackSwanEvents.length === 0 ? (
          <EmptyState>No Defensive Mode episode has completed yet.</EmptyState>
        ) : (
          <div className="space-y-1">
            {[...blackSwanEvents]
              .reverse()
              .slice(0, 10)
              .map((event) => (
                <div key={event.id} className="rounded-sm border border-cmd-border/40 bg-cmd-bg/60 p-1.5 text-[9px]">
                  <div className="flex items-center justify-between">
                    <StatusPill tone={blackSwanRiskTone(event.peakTier)}>{event.peakTier}</StatusPill>
                    <span className={`tabular-nums ${event.equityChangePct >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{event.equityChangePct.toFixed(2)}%</span>
                  </div>
                  <div className="mt-1 text-cmd-textDim">{event.lesson}</div>
                </div>
              ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Daily Black Swan Situation Report</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">One real snapshot per in-game evening ({blackSwanReports.length} on record)</span>
        </div>
        {!latestReport ? (
          <EmptyState>No report has been generated yet — the first one lands at the end of the current in-game day.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-cmd-textDim">Day {latestReport.simDay}</span>
              <span className="text-cmd-cyan">{latestReport.narrative.headline}</span>
            </div>
            <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px] text-cmd-text">{latestReport.narrative.body}</div>
          </div>
        )}
      </Glass>
    </div>
  );
}
