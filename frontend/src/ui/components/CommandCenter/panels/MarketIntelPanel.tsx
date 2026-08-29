import { useEffect, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { api } from "@/net/api";
import { EXECUTIVE_ACTION_LABEL } from "@/types";
import type { DataCategory, DataProvenanceReport, EvidenceConfluenceRead, MarketDebateSpecialist, SessionRegimeEvidence, SessionRegimeEvidenceState, SessionRegimeEvidenceSummary, TechnicalAnalysisRead } from "@/types";
import { EvidenceConfluenceCard } from "../EvidenceConfluenceCard";
import { executiveActionTone, latestMarketIntelligenceReport, marketQualityTone, momentumTone, newsRiskTone, recentMarketIntelligenceLearning } from "../lib/derive";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

function sessionEvidenceTone(state: SessionRegimeEvidenceState): "green" | "red" | "amber" | "cyan" {
  switch (state) {
    case "favorable":
      return "green";
    case "unfavorable":
      return "red";
    case "mixed":
      return "amber";
    case "not_enough_evidence":
      return "cyan";
  }
}

const SESSION_EVIDENCE_LABEL: Record<SessionRegimeEvidenceState, string> = {
  favorable: "Favorable",
  unfavorable: "Unfavorable",
  mixed: "Mixed",
  not_enough_evidence: "Not Enough Evidence",
};

function dataCategoryTone(category: DataCategory): "green" | "red" | "amber" | "cyan" {
  switch (category) {
    case "real":
      return "green";
    case "simulated":
      return "cyan";
    case "synthetic":
      return "amber";
    case "user_provided":
      return "cyan";
    case "unavailable":
      return "red";
  }
}

const DATA_CATEGORY_LABEL: Record<DataCategory, string> = {
  real: "Real",
  synthetic: "Synthetic",
  simulated: "Simulated",
  user_provided: "User-Provided",
  unavailable: "Unavailable",
};

const SPECIALIST_ICON: Record<MarketDebateSpecialist, string> = {
  liquidity: "💧",
  price_action: "📈",
  momentum: "⚡",
  quant: "📊",
  risk: "⚠",
};

/**
 * v0.7 Feature 51 — Market Intelligence Department, "the company's
 * eyes." Every number here traces to a real field on MarketIntelligenceState
 * (recomputed every tick from real mock OHLCV candle data or real
 * wall-clock time) or to the most recent MarketIntelligenceReport (one
 * real permanent snapshot per in-game evening). See
 * backend/app/market_intelligence.py's module docstring for the full
 * real/named-proxy/not-built honesty boundary — institutionalActivity and
 * newsRisk are explicitly labeled proxies below, never presented as real
 * order-flow or economic-calendar data.
 */
export function MarketIntelPanel() {
  const { marketIntelligence: mi, marketIntelligenceReports, marketIntelligenceLearning } = useGameStore();
  const latestReport = latestMarketIntelligenceReport(marketIntelligenceReports);
  const recentLearning = recentMarketIntelligenceLearning(marketIntelligenceLearning, 10);

  // CEO directive "Session Trading Education & Agent Training" — real,
  // on-demand SESSION x REGIME evidence (backend/app/session_evidence.py),
  // no WS-broadcast field backs it, the same on-demand pattern this
  // Command Center already uses for Regime Reconciliation.
  const [sessionEvidence, setSessionEvidence] = useState<SessionRegimeEvidenceSummary | null>(null);
  useEffect(() => {
    api.getSessionRegimeEvidence().then(setSessionEvidence).catch(() => undefined);
  }, []);
  const currentBucket: SessionRegimeEvidence | undefined = sessionEvidence?.buckets.find(
    (b) => b.session === mi.session.current && b.regime === mi.regime
  );

  // CEO directive "Next Professional Trading Firm Phase," Priority 5 —
  // real, on-demand data-provenance audit (backend/app/data_provenance.py).
  // CEO directive "Professional Trading Firm — Market-Analysis Knowledge
  // + Session Intelligence Expansion," Phases 1-3 — real technical
  // indicator/pattern reads for one symbol at a time, fetched on demand
  // (backend/app/technical_analysis.py). Never persisted, never wired
  // into any live trading decision.
  const [taSymbol, setTaSymbol] = useState<string | null>(null);
  const [technicalAnalysis, setTechnicalAnalysis] = useState<TechnicalAnalysisRead | null>(null);
  const [taLoading, setTaLoading] = useState(false);
  useEffect(() => {
    if (!taSymbol) return;
    let cancelled = false;
    setTaLoading(true);
    api
      .getTechnicalAnalysis(taSymbol)
      .then((res) => {
        if (!cancelled) setTechnicalAnalysis(res);
      })
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) setTaLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [taSymbol]);

  // CEO directive "Professional Quant Trading Firm — Quant Intelligence
  // + Market Analysis Completion Phase," Phase D — the evidence-family
  // confluence layer, fetched for the same selected symbol as the
  // Technical Analysis section above (backend/app/evidence_confluence.py).
  const [evidenceConfluence, setEvidenceConfluence] = useState<EvidenceConfluenceRead | null>(null);
  useEffect(() => {
    if (!taSymbol) return;
    let cancelled = false;
    api
      .getEvidenceConfluence(taSymbol)
      .then((res) => {
        if (!cancelled) setEvidenceConfluence(res);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [taSymbol]);

  const [dataProvenance, setDataProvenance] = useState<DataProvenanceReport | null>(null);
  useEffect(() => {
    api.getDataProvenance().then(setDataProvenance).catch(() => undefined);
  }, []);

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Market Regime — {mi.regimeLabel}</TerminalLabel>
          <StatusPill tone={marketQualityTone(mi.quality.tier)}>{mi.quality.tier.replace(/_/g, " ")}</StatusPill>
        </div>
        <p className="mb-2 text-cmd-text">{mi.regimeDetail}</p>
        <div className="mb-2 flex items-center gap-3">
          <span className="font-cmdmono text-cmd-cyan">{Math.round(mi.quality.score)}/100</span>
          <div className="flex-1">
            <Meter value={mi.quality.score} tone={marketQualityTone(mi.quality.tier)} />
          </div>
          <span className="text-[9px] text-cmd-textDim">{Math.round(mi.quality.confidencePct)}% confidence</span>
        </div>
        <p className="mb-1.5 text-cmd-textDim">{mi.quality.reasoning}</p>
        {mi.quality.evidence.length > 0 && (
          <ul className="mb-1.5 list-inside list-disc space-y-0.5 text-[9px] text-cmd-text">
            {mi.quality.evidence.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
        <div className="text-[9px] text-cmd-textDim">{mi.quality.historicalSimilarity}</div>
        <div className="mt-1.5 text-right text-[9px] text-cmd-textDim">Updated {new Date(mi.updatedAt).toLocaleTimeString()}</div>
      </Glass>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <Glass className="p-2">
          <TerminalLabel>Session</TerminalLabel>
          <div className="mb-1 text-cmd-cyan">{mi.session.label}</div>
          {mi.session.overlapsActive.length > 0 && (
            <div className="mb-1 flex flex-wrap gap-1">
              {mi.session.overlapsActive.map((o) => (
                <StatusPill key={o} tone="purple">
                  {o}
                </StatusPill>
              ))}
            </div>
          )}
          <div className="text-[9px] text-cmd-textDim">{mi.session.detail}</div>
        </Glass>

        <Glass className="p-2">
          <TerminalLabel>Volatility</TerminalLabel>
          <DataRow label="Current" value={`${mi.volatility.currentPct.toFixed(2)}%`} />
          <DataRow label="Historical Avg" value={`${mi.volatility.historicalAvgPct.toFixed(2)}%`} />
          <DataRow label="Percentile" value={`${Math.round(mi.volatility.percentile)}th`} />
          <div className="mt-1 text-[9px] text-cmd-textDim">{mi.volatility.detail}</div>
        </Glass>

        <Glass className="p-2">
          <TerminalLabel>Momentum</TerminalLabel>
          <StatusPill tone={momentumTone(mi.momentum.strength)}>{mi.momentum.strength}</StatusPill>
          <div className="mt-1">
            <DataRow label="Rate of Change" value={`${mi.momentum.rocPct >= 0 ? "+" : ""}${mi.momentum.rocPct.toFixed(2)}%`} />
          </div>
          <div className="mt-1 text-[9px] text-cmd-textDim">{mi.momentum.detail}</div>
        </Glass>

        <Glass className="p-2">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Institutional Activity</TerminalLabel>
            <span title="Named proxy: real volume/price-move divergence, not real order-flow data">ⓘ</span>
          </div>
          <DataRow label="Divergence Score" value={mi.institutionalActivity.volumePriceDivergenceScore.toFixed(1)} />
          <DataRow label="Absorption" value={mi.institutionalActivity.absorptionDetected ? "Detected" : "None"} valueClassName={mi.institutionalActivity.absorptionDetected ? "text-cmd-amber" : "text-cmd-text"} />
          <div className="mt-1 text-[9px] text-cmd-textDim">{mi.institutionalActivity.detail}</div>
        </Glass>

        <Glass className="p-2">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>News Risk</TerminalLabel>
            <span title="Named proxy: real count of market-category news items on file, not a real economic calendar">ⓘ</span>
          </div>
          <StatusPill tone={newsRiskTone(mi.newsRisk.riskLevel)}>{mi.newsRisk.riskLevel}</StatusPill>
          <div className="mt-1">
            <DataRow label="Active Market News" value={mi.newsRisk.activeMarketNewsCount} />
          </div>
          <div className="mt-1 text-[9px] text-cmd-textDim">{mi.newsRisk.detail}</div>
        </Glass>
      </div>

      <Glass className="p-3">
        <TerminalLabel>Liquidity &amp; Structure — By Symbol</TerminalLabel>
        {mi.liquidity.length === 0 ? (
          <EmptyState>No real candle data sampled yet.</EmptyState>
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {mi.liquidity.map((liq) => {
              const structure = mi.structure.find((s) => s.symbol === liq.symbol);
              return (
                <div key={liq.symbol} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="font-cmdmono text-cmd-cyan">{liq.symbol}</span>
                    {liq.sweepDetected && <StatusPill tone="amber">sweep {liq.sweepDirection.replace(/_/g, " ")}</StatusPill>}
                  </div>
                  <DataRow label="Liquidity Score" value={liq.liquidityScore.toFixed(1)} />
                  <div className="mt-1 text-cmd-textDim">{liq.detail}</div>
                  {liq.zones.length > 0 && (
                    <div className="mt-1.5 space-y-0.5">
                      {liq.zones.map((z, i) => (
                        <div key={i} className="flex items-center justify-between text-cmd-textDim">
                          <span>{z.kind.replace(/_/g, " ")}</span>
                          <span className="tabular-nums text-cmd-text">
                            {z.price.toFixed(2)} × {z.touches}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                  {structure && (
                    <div className="mt-1.5 border-t border-cmd-border/50 pt-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-cmd-textDim">Structure</span>
                        <span className="text-cmd-text">{structure.structureState.replace(/_/g, " ")}</span>
                      </div>
                      {structure.lastBreakOfStructure !== "none" && (
                        <div className={`mt-0.5 ${structure.lastBreakOfStructure === "bullish" ? "text-cmd-green" : "text-cmd-red"}`}>
                          Break of structure: {structure.lastBreakOfStructure}
                        </div>
                      )}
                      <div className="mt-1 text-cmd-textDim">{structure.detail}</div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Technical Analysis — Real Indicators &amp; Patterns</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">Computed fresh, never wired into any live decision</span>
        </div>
        {mi.liquidity.length === 0 ? (
          <EmptyState>No real candle data sampled yet.</EmptyState>
        ) : (
          <>
            <div className="mb-2 flex flex-wrap gap-1">
              {mi.liquidity.map((liq) => (
                <button
                  key={liq.symbol}
                  type="button"
                  onClick={() => setTaSymbol(liq.symbol === taSymbol ? null : liq.symbol)}
                  className={`rounded-sm border px-2 py-1 font-cmdmono text-[9px] transition-colors ${
                    taSymbol === liq.symbol ? "border-cmd-cyan text-cmd-cyan" : "border-cmd-border/60 text-cmd-textDim hover:border-cmd-cyan/40"
                  }`}
                >
                  {liq.symbol}
                </button>
              ))}
            </div>
            {!taSymbol && <EmptyState>Select a symbol above for its real indicator/pattern read.</EmptyState>}
            {taSymbol && taLoading && <div className="text-[9px] text-cmd-textDim">Computing…</div>}
            {taSymbol && !taLoading && technicalAnalysis && technicalAnalysis.symbol === taSymbol && (
              <div className="space-y-2 text-[9px]">
                <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 sm:grid-cols-3">
                  <DataRow label="SMA20" value={technicalAnalysis.indicators.sma20?.toFixed(2) ?? "—"} />
                  <DataRow label="EMA20" value={technicalAnalysis.indicators.ema20?.toFixed(2) ?? "—"} />
                  <DataRow label="RSI14" value={technicalAnalysis.indicators.rsi14?.toFixed(1) ?? "—"} />
                  <DataRow label="MACD" value={technicalAnalysis.indicators.macdLine?.toFixed(3) ?? "—"} />
                  <DataRow label="Stoch %K" value={technicalAnalysis.indicators.stochasticPercentK?.toFixed(1) ?? "—"} />
                  <DataRow label="ATR14" value={technicalAnalysis.indicators.atr14?.toFixed(2) ?? "—"} />
                  <DataRow label="VWAP" value={technicalAnalysis.indicators.vwap?.toFixed(2) ?? "—"} />
                  <DataRow
                    label="Parabolic SAR"
                    value={technicalAnalysis.indicators.parabolicSar !== null ? `${technicalAnalysis.indicators.parabolicSar.toFixed(2)} (${technicalAnalysis.indicators.parabolicSarTrend})` : "—"}
                    valueClassName={technicalAnalysis.indicators.parabolicSarTrend === "up" ? "text-cmd-green" : technicalAnalysis.indicators.parabolicSarTrend === "down" ? "text-cmd-red" : undefined}
                  />
                  <DataRow
                    label="SuperTrend"
                    value={technicalAnalysis.indicators.supertrend !== null ? `${technicalAnalysis.indicators.supertrend.toFixed(2)} (${technicalAnalysis.indicators.supertrendTrend})` : "—"}
                    valueClassName={technicalAnalysis.indicators.supertrendTrend === "up" ? "text-cmd-green" : technicalAnalysis.indicators.supertrendTrend === "down" ? "text-cmd-red" : undefined}
                  />
                </div>
                <div className="text-cmd-textDim">{technicalAnalysis.indicators.detail}</div>
                <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2">
                  <div className="text-cmd-textDim">Swing Structure</div>
                  <div className="text-cmd-text">{technicalAnalysis.swingStructure.labels.length > 0 ? technicalAnalysis.swingStructure.labels.join(" → ").replace(/_/g, " ") : "No real swing labels yet"}</div>
                </div>
                {technicalAnalysis.fairValueGaps.gaps.length > 0 && (
                  <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2">
                    <div className="mb-0.5 text-cmd-textDim">Fair Value Gaps</div>
                    {technicalAnalysis.fairValueGaps.gaps.map((g, i) => (
                      <div key={i} className="flex items-center justify-between">
                        <span className={g.direction === "bullish" ? "text-cmd-green" : "text-cmd-red"}>{g.direction}</span>
                        <span className="tabular-nums text-cmd-text">
                          {g.gapLow.toFixed(2)} – {g.gapHigh.toFixed(2)}
                        </span>
                        <StatusPill tone={g.filled ? "cyan" : "amber"}>{g.filled ? "filled" : "open"}</StatusPill>
                      </div>
                    ))}
                  </div>
                )}
                {technicalAnalysis.candlestickPatterns.patterns.length > 0 && (
                  <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2">
                    <div className="mb-0.5 text-cmd-textDim">Candlestick Patterns</div>
                    {technicalAnalysis.candlestickPatterns.patterns.map((p, i) => (
                      <div key={i} className="text-cmd-text">
                        {p.pattern.replace(/_/g, " ")} — <span className="text-cmd-textDim">{p.detail}</span>
                      </div>
                    ))}
                  </div>
                )}
                {technicalAnalysis.fibonacci.levels.length > 0 && (
                  <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2">
                    <div className="mb-0.5 text-cmd-textDim">Fibonacci Levels (swing {technicalAnalysis.fibonacci.swingLow.toFixed(2)} – {technicalAnalysis.fibonacci.swingHigh.toFixed(2)})</div>
                    <div className="flex flex-wrap gap-x-3 gap-y-0.5">
                      {technicalAnalysis.fibonacci.levels.map((lv, i) => (
                        <span key={i} className="tabular-nums text-cmd-text">
                          {lv.ratio} → {lv.price.toFixed(2)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {technicalAnalysis.supportResistance.levels.length > 0 && (
                  <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2">
                    <div className="mb-0.5 text-cmd-textDim">Support / Resistance</div>
                    <div className="space-y-0.5">
                      {technicalAnalysis.supportResistance.levels.map((lv, i) => (
                        <div key={i} className="flex items-center justify-between">
                          <span className={lv.role === "support" ? "text-cmd-green" : "text-cmd-red"}>{lv.role}</span>
                          <span className="tabular-nums text-cmd-text">{lv.price.toFixed(2)}</span>
                          <span className="text-cmd-textDim">{lv.touches}× touched</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2">
                  <div className="text-cmd-textDim">Order Block</div>
                  <div className="text-cmd-text">{technicalAnalysis.orderBlock.detail}</div>
                </div>
                {technicalAnalysis.chartPatterns.patterns.length > 0 && (
                  <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2">
                    <div className="mb-0.5 text-cmd-textDim">Chart Patterns (double top/bottom, trendline breaks)</div>
                    <div className="space-y-1">
                      {technicalAnalysis.chartPatterns.patterns.map((p) => (
                        <div key={p.patternId} className="flex items-center justify-between">
                          <span className={p.direction === "bullish" ? "text-cmd-green" : "text-cmd-red"}>{p.patternType.replace(/_/g, " ")}</span>
                          <span className="tabular-nums text-cmd-text">
                            {p.priceLow.toFixed(2)} – {p.priceHigh.toFixed(2)}
                          </span>
                          <span className="text-cmd-textDim">{p.confidencePct.toFixed(0)}% confidence</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </Glass>

      {taSymbol && evidenceConfluence && evidenceConfluence.symbol === taSymbol && (
        <EvidenceConfluenceCard confluence={evidenceConfluence} title={`Evidence Confluence — ${taSymbol}`} />
      )}

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Executive Market Brief — Today&apos;s Market Debate</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">One real snapshot per in-game evening ({marketIntelligenceReports.length} on record)</span>
        </div>
        {!latestReport ? (
          <EmptyState>No Executive Market Brief has been generated yet — the first one lands at the end of the current in-game day.</EmptyState>
        ) : (
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-cmd-textDim">Day {latestReport.simDay}</span>
              <StatusPill tone={executiveActionTone(latestReport.tradeRecommendation)}>{EXECUTIVE_ACTION_LABEL[latestReport.tradeRecommendation]}</StatusPill>
              <span className="text-cmd-textDim">{Math.round(latestReport.confidencePct)}% confidence</span>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {latestReport.debate.turns.map((turn) => (
                <div key={turn.specialist} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-cmd-purple">
                      {SPECIALIST_ICON[turn.specialist]} {turn.label}
                    </span>
                    <span className="text-cmd-textDim">{Math.round(turn.confidencePct)}%</span>
                  </div>
                  <div className="mb-1 text-cmd-text">{turn.observation}</div>
                  {turn.opportunities.length > 0 && <div className="text-cmd-green">+ {turn.opportunities[0]}</div>}
                  {turn.risks.length > 0 && <div className="mt-0.5 text-cmd-amber">− {turn.risks[0]}</div>}
                </div>
              ))}
            </div>
            <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px] text-cmd-text">{latestReport.debate.summary}</div>
            <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-cmd-cyan">Strategy Match</span>
                <StatusPill tone="purple">{latestReport.strategyMatch.recommendedRiskLevel} risk</StatusPill>
              </div>
              <div className="text-cmd-textDim">{latestReport.strategyMatch.detail}</div>
              {latestReport.strategyMatch.recommendedStrategyIds.length > 0 && (
                <div className="mt-1 text-cmd-green">Recommended: {latestReport.strategyMatch.recommendedStrategyIds.join(", ")}</div>
              )}
              {latestReport.strategyMatch.avoidedStrategyIds.length > 0 && (
                <div className="mt-0.5 text-cmd-red">Avoided: {latestReport.strategyMatch.avoidedStrategyIds.join(", ")}</div>
              )}
            </div>
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Learning Loop</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">Generated the day after each brief — real predicted vs. actual comparison ({marketIntelligenceLearning.length} on record)</span>
        </div>
        {recentLearning.length === 0 ? (
          <EmptyState>No prior brief has been graded against a real outcome yet.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {recentLearning.map((entry) => (
              <div key={entry.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-cmd-textDim">Day {entry.forSimDay}</span>
                  <span className="text-cmd-text">predicted {entry.predictedRegime.replace(/_/g, " ")}</span>
                  {entry.regimeConsistent === null ? (
                    <StatusPill tone="neutral">no comparison yet</StatusPill>
                  ) : (
                    <StatusPill tone={entry.regimeConsistent ? "green" : "amber"}>{entry.regimeConsistent ? "consistent" : "diverged"}</StatusPill>
                  )}
                  {entry.tradesClosedThatDay > 0 && (
                    <span className="ml-auto text-cmd-textDim">
                      {entry.tradesClosedThatDay} trade(s) closed{entry.tradesWinRatePct !== null && ` — ${Math.round(entry.tradesWinRatePct)}% win rate`}
                    </span>
                  )}
                </div>
                <div className="mt-1 text-cmd-text">{entry.lesson}</div>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Session × Regime Evidence</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">Session context is evidence, not a signal — real closed-trade outcomes only</span>
        </div>
        {sessionEvidence === null ? (
          <EmptyState>Loading…</EmptyState>
        ) : (
          <>
            <div className="mb-2 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2">
              <div className="mb-1 flex items-center gap-2">
                <span className="text-[9px] uppercase tracking-wide text-cmd-textDim">Current pairing — {mi.session.label}</span>
                {currentBucket && <StatusPill tone={sessionEvidenceTone(currentBucket.evidenceState)}>{SESSION_EVIDENCE_LABEL[currentBucket.evidenceState]}</StatusPill>}
              </div>
              {currentBucket ? (
                <div className="text-[9px] text-cmd-text">
                  {currentBucket.sampleSize} real observation{currentBucket.sampleSize === 1 ? "" : "s"} under this regime
                  {currentBucket.winRatePct !== null && ` — ${currentBucket.winRatePct.toFixed(0)}% favorable`}
                </div>
              ) : (
                <div className="text-[9px] text-cmd-textDim">
                  NOT ENOUGH EVIDENCE for this session/regime pairing yet (0 real observations, {sessionEvidence.minSampleSize} required).
                </div>
              )}
            </div>
            {sessionEvidence.buckets.length === 0 ? (
              <EmptyState>No closed trade has ever been recorded under any session/regime pairing yet.</EmptyState>
            ) : (
              <div className="max-h-48 space-y-1 overflow-y-auto">
                {sessionEvidence.buckets.map((b) => (
                  <div key={`${b.session}-${b.regime}`} className="flex items-center gap-2 rounded-sm border border-cmd-border/40 bg-cmd-bg/30 px-2 py-1 text-[9px]">
                    <StatusPill tone={sessionEvidenceTone(b.evidenceState)}>{SESSION_EVIDENCE_LABEL[b.evidenceState]}</StatusPill>
                    <span className="text-cmd-text">{b.session.replace(/_/g, " ")}</span>
                    <span className="text-cmd-textDim">× {b.regime.replace(/_/g, " ")}</span>
                    <span className="ml-auto text-cmd-textDim">
                      {b.sampleSize} obs{b.winRatePct !== null && ` — ${b.winRatePct.toFixed(0)}%`}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Data Integrity — What Backs This Company&apos;s Data</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">Real / Synthetic / Simulated / User-Provided / Unavailable, per subsystem</span>
        </div>
        {dataProvenance === null ? (
          <EmptyState>Loading…</EmptyState>
        ) : (
          <div className="space-y-1">
            {dataProvenance.sources.map((source) => (
              <div key={source.subsystem} className="rounded-sm border border-cmd-border/40 bg-cmd-bg/30 px-2 py-1.5 text-[9px]">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill tone={dataCategoryTone(source.category)}>{DATA_CATEGORY_LABEL[source.category]}</StatusPill>
                  <span className="text-cmd-text">{source.subsystem}</span>
                  {source.coveragePct !== null && <span className="ml-auto text-cmd-textDim">Coverage: {source.coveragePct.toFixed(0)}%</span>}
                  {source.reproducible !== null && (
                    <span className="text-cmd-textDim">{source.reproducible ? "Reproducible" : "Not reproducible run-to-run"}</span>
                  )}
                </div>
                <div className="mt-0.5 text-cmd-textDim">{source.detail}</div>
              </div>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}
