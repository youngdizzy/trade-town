import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { EmaPullbackResearchResult, EmaPullbackStatsBucket } from "@/types";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";

const VERDICT_TONE: Record<string, "green" | "amber"> = {
  enough_evidence: "green",
  not_enough_evidence: "amber",
};

function BucketRow({ bucket }: { bucket: EmaPullbackStatsBucket }) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="text-cmd-cyan">{bucket.label}</span>
        {bucket.verdict && <StatusPill tone={VERDICT_TONE[bucket.verdict]}>{bucket.verdict.replace(/_/g, " ")}</StatusPill>}
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 sm:grid-cols-4">
        <DataRow label="Trades" value={`${bucket.tradeCount} (${bucket.winCount}W/${bucket.lossCount}L/${bucket.openCount}O)`} />
        <DataRow label="Win Rate" value={bucket.winRatePct !== null ? `${bucket.winRatePct}%` : "—"} />
        <DataRow label="Expectancy" value={bucket.expectancyR !== null ? `${bucket.expectancyR >= 0 ? "+" : ""}${bucket.expectancyR}R` : "—"} valueClassName={bucket.expectancyR !== null ? (bucket.expectancyR >= 0 ? "text-cmd-green" : "text-cmd-red") : undefined} />
        <DataRow label="Profit Factor" value={bucket.profitFactor ?? "—"} />
      </div>
      <div className="mt-1 text-cmd-textDim">{bucket.detail}</div>
    </div>
  );
}

function BucketGroup({ title, buckets }: { title: string; buckets: EmaPullbackStatsBucket[] }) {
  if (buckets.length === 0) return null;
  return (
    <Glass className="p-3">
      <TerminalLabel>{title}</TerminalLabel>
      <div className="mt-1.5 space-y-1.5">
        {buckets.map((b, i) => (
          <BucketRow key={i} bucket={b} />
        ))}
      </div>
    </Glass>
  );
}

/**
 * CEO directive "Professional Trading Firm — Market-Analysis Knowledge +
 * Session Intelligence Expansion," Phase 15 — the 50 EMA breakout +
 * pullback strategy's research result. Read-only, computed fresh on
 * open (GET /api/sandbox/ema-pullback-research) — nothing here is
 * persisted, and this view never claims the strategy is validated or
 * profitable; it only ever displays this run's own real numbers next to
 * the CEO-supplied source material's own claim, kept explicitly
 * separate. See backend/app/ema_pullback_research.py's module docstring
 * for the full rule definitions this backtest replays.
 */
export function EmaPullbackResearchView() {
  const [result, setResult] = useState<EmaPullbackResearchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRules, setShowRules] = useState(false);

  const refresh = () => {
    setLoading(true);
    setError(null);
    api
      .getEmaPullbackResearch()
      .then(setResult)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
  }, []);

  if (loading && !result) {
    return (
      <Glass className="p-3">
        <EmptyState>Quant Research is replaying the real rule set against real (mock) candle history…</EmptyState>
      </Glass>
    );
  }
  if (error) {
    return (
      <Glass className="p-3">
        <div className="text-[9px] text-cmd-red">{error}</div>
      </Glass>
    );
  }
  if (!result) return null;

  const sc = result.sourceClaimComparison;

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>50 EMA Breakout + Pullback — Research Hypothesis</TerminalLabel>
          <button type="button" onClick={refresh} className="rounded-sm border border-cmd-border px-2 py-0.5 text-[9px] uppercase text-cmd-textDim hover:border-cmd-cyan/50 hover:text-cmd-cyan">
            Re-run
          </button>
        </div>
        <p className="text-[9px] text-cmd-text">{result.hypothesis}</p>
        <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 sm:grid-cols-4">
          <DataRow label="Symbols Tested" value={result.symbolsTested.length} />
          <DataRow label="Timeframe" value={result.timeframe} />
          <DataRow label="Candles / Symbol" value={result.candlesPerSymbol.toLocaleString()} />
          <DataRow label="Reference Target" value={`${result.referenceRMultiple}R`} />
        </div>
        <button type="button" onClick={() => setShowRules(!showRules)} className="mt-1.5 text-[9px] uppercase text-cmd-textDim hover:text-cmd-cyan">
          {showRules ? "Hide full rule disclosure ▲" : "Show full rule disclosure ▼"}
        </button>
        {showRules && <pre className="mt-1.5 max-h-64 overflow-y-auto whitespace-pre-wrap rounded-sm border border-cmd-border/50 bg-cmd-bg/60 p-2 text-[8px] text-cmd-textDim">{result.rulesDisclosure}</pre>}
      </Glass>

      <Glass className="border-cmd-amber/40 p-3">
        <TerminalLabel>Source Claim vs. TradeTown Evidence</TerminalLabel>
        <div className="mt-1.5 grid grid-cols-2 gap-3">
          <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
            <div className="mb-1 uppercase tracking-wide text-cmd-textDim">Source Claim (external, unvalidated)</div>
            <div className="text-cmd-text">
              {sc.sourceClaimWinners} / {sc.sourceClaimTradeCount} trades — {sc.sourceClaimWinRatePct}% win rate
            </div>
          </div>
          <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
            <div className="mb-1 uppercase tracking-wide text-cmd-textDim">TradeTown Evidence (real, computed)</div>
            <div className="text-cmd-text">
              {sc.tradetownTradeCount} trades — {sc.tradetownWinRatePct !== null ? `${sc.tradetownWinRatePct}%` : "not enough evidence"} win rate
            </div>
          </div>
        </div>
        <p className="mt-1.5 text-[8px] italic text-cmd-textDim">{sc.detail}</p>
      </Glass>

      <BucketGroup title="R-Multiple Sweep (1R – 3R)" buckets={result.rMultipleSweep} />
      <BucketGroup title="Confirmed (Pullback + Breakout) vs. Naive EMA Cross Baseline" buckets={result.confirmedVsNaiveBaseline} />
      <BucketGroup title="Session Breakdown (at reference R)" buckets={result.sessionBreakdown} />
      <BucketGroup title="Regime Trend Breakdown (at reference R)" buckets={result.regimeTrendBreakdown} />
      <BucketGroup title="Regime Volatility Breakdown (at reference R)" buckets={result.regimeVolatilityBreakdown} />
      <BucketGroup title="Instrument Breakdown (at reference R)" buckets={result.instrumentBreakdown} />
      <BucketGroup title="Breakout Candle Size (at reference R)" buckets={result.breakoutSizeBreakdown} />

      {result.modelValidation && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Model Validation — Meridian's Independent Challenge</TerminalLabel>
            <StatusPill tone={result.modelValidation.verdict === "approved" ? "green" : result.modelValidation.verdict === "rejected" ? "red" : "amber"}>{result.modelValidation.verdict.replace(/_/g, " ")}</StatusPill>
          </div>
          <div className="text-[9px] text-cmd-text">{result.modelValidation.evidenceSummary}</div>
          <div className="mt-1.5 grid grid-cols-2 gap-1.5 sm:grid-cols-3">
            {result.modelValidation.checks.map((c) => (
              <div key={c.id} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[8px]">
                <div className={c.passed === true ? "text-cmd-green" : c.passed === false ? "text-cmd-red" : "text-cmd-textDim"}>{c.label}</div>
              </div>
            ))}
          </div>
        </Glass>
      )}

      {result.monteCarlo && (
        <Glass className="p-3">
          <TerminalLabel>Monte Carlo Bootstrap</TerminalLabel>
          <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 sm:grid-cols-4">
            <DataRow label="Probability Of Profit" value={`${result.monteCarlo.probabilityOfProfitPct}%`} />
            <DataRow label="Probability Of Ruin" value={`${result.monteCarlo.probabilityOfRuinPct}%`} />
            <DataRow label="Median Return" value={`${result.monteCarlo.medianReturnPct}%`} />
            <DataRow label="Worst-Case Drawdown" value={`${result.monteCarlo.worstCaseDrawdownPct}%`} />
          </div>
        </Glass>
      )}

      <Glass className="p-3">
        <p className="text-[8px] italic text-cmd-textDim">{result.dataHonestyNote}</p>
      </Glass>
    </div>
  );
}
