import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { StrategyTradingDiagnosticRead, StrategyTradingDiagnosticSummary } from "@/types";
import { EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";

const REASON_LABEL: Record<StrategyTradingDiagnosticRead["reason"], string> = {
  trading_live: "TRADING LIVE",
  blocked_by_regime_today: "BLOCKED — TODAY'S REGIME",
  eligible_but_never_selected: "ELIGIBLE — NEVER SELECTED",
  no_backtest_evidence_yet: "NO BACKTEST EVIDENCE YET",
};

const REASON_TONE: Record<StrategyTradingDiagnosticRead["reason"], "green" | "red" | "amber" | "cyan"> = {
  trading_live: "green",
  blocked_by_regime_today: "red",
  eligible_but_never_selected: "amber",
  no_backtest_evidence_yet: "cyan",
};

/**
 * CEO directive "Live Trade → Strategy Provenance," Phase 9 — "why
 * isn't this strategy trading live?" per real strategy. Closes the one
 * gap `backend/app/trade_pipeline_health.py`'s existing funnel
 * diagnostic never covered (confirmed by audit: zero references to
 * "strategy" anywhere in that module before this). Built entirely from
 * two already-real, already-computed sources — never a new eligibility
 * rule or a new performance computation. Diagnostic only: feeds no
 * score, gates nothing, changes no CEO decision.
 */
export function StrategyTradingDiagnosticsView() {
  const [summary, setSummary] = useState<StrategyTradingDiagnosticSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getStrategyTradingDiagnostics()
      .then((result) => {
        if (!cancelled) setSummary(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return null;

  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Why Isn&apos;t This Strategy Trading? — Real Diagnostic</TerminalLabel>
        <span className="text-[9px] text-cmd-textDim">Diagnostic only — never gates a decision</span>
      </div>
      {summary === null ? (
        <EmptyState>Loading…</EmptyState>
      ) : (
        <div className="space-y-1">
          {summary.reads.map((r) => (
            <div key={r.strategyId} className="rounded-sm border border-cmd-border/40 bg-cmd-bg/30 px-2 py-1.5 text-[9px]">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-cmdmono text-cmd-cyan">{r.strategyName}</span>
                <span className="text-cmd-textDim">{r.stage.replace(/_/g, " ")}</span>
                <StatusPill tone={REASON_TONE[r.reason]}>{REASON_LABEL[r.reason]}</StatusPill>
              </div>
              <div className="mt-0.5 text-cmd-textDim">{r.detail}</div>
            </div>
          ))}
        </div>
      )}
    </Glass>
  );
}
