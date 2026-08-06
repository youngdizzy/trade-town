import { useGameStore } from "@/ui/hooks/useGameStore";
import { economicHealthTone, latestEconomicIntelligenceReport, marketQualityTone, newsRiskTone } from "../lib/derive";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

/**
 * Design Bible Chapter 71 — Economic Intelligence Center
 * (backend/app/economic_intelligence.py). This codebase has no real
 * macroeconomic data source anywhere (no API keys, no live feed) — every
 * number here traces to a real already-computed signal from Market
 * Environment (regime), Market Intelligence (quality/news risk), or
 * Portfolio Intelligence (correlation/category exposure), synthesized
 * into one Economic Health Score with five named, published factors —
 * never a black-box blend. The Confidence read and Daily Brief narrative
 * are real too: confidence/evidence quality are computed, and the
 * narrative only cites real, computed deltas, never invented causality
 * like "the Fed cut rates" (no real Fed data exists here).
 */
export function EconomicIntelPanel() {
  const { economicIntelligence: eic, economicIntelligenceReports } = useGameStore();
  const latestReport = latestEconomicIntelligenceReport(economicIntelligenceReports);
  const { health, confidence } = eic;

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Economic Health — {eic.regimeLabel}</TerminalLabel>
          <StatusPill tone={economicHealthTone(health.tier)}>{health.tier}</StatusPill>
        </div>
        <div className="mb-2 flex items-center gap-3">
          <span className="font-cmdmono text-cmd-cyan">{health.overall.toFixed(1)}/100</span>
          <div className="flex-1">
            <Meter value={health.overall} tone={economicHealthTone(health.tier)} />
          </div>
          <StatusPill tone={marketQualityTone(eic.marketQualityTier)}>market {eic.marketQualityTier.replace(/_/g, " ")}</StatusPill>
        </div>
        <p className="text-cmd-textDim">{health.reasoning}</p>
        <div className="mt-1.5 text-right text-[9px] text-cmd-textDim">Updated {new Date(eic.updatedAt).toLocaleTimeString()}</div>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Five Real Factors — never a black-box blend</TerminalLabel>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-5">
          {health.factors.map((factor) => (
            <div key={factor.name} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-cmd-cyan">{factor.name}</span>
                <span className="text-cmd-textDim">×{factor.weight.toFixed(2)}</span>
              </div>
              <div className="mb-1">
                <Meter value={factor.score} tone={factor.score >= 60 ? "green" : factor.score >= 35 ? "amber" : "red"} />
              </div>
              <div className="flex items-center justify-between text-cmd-textDim">
                <span>{factor.score.toFixed(0)}/100</span>
              </div>
              <div className="mt-1 text-cmd-textDim">{factor.detail}</div>
            </div>
          ))}
        </div>
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Economic Confidence Engine — never presented as fact</TerminalLabel>
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
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div>
            <div className="mb-1 text-cmd-green">Supporting</div>
            {confidence.supportingEvidence.length === 0 ? (
              <div className="text-[9px] text-cmd-textDim">None.</div>
            ) : (
              <ul className="list-inside list-disc space-y-0.5 text-[9px] text-cmd-text">
                {confidence.supportingEvidence.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <div className="mb-1 text-cmd-amber">Contradicting</div>
            {confidence.contradictingEvidence.length === 0 ? (
              <div className="text-[9px] text-cmd-textDim">None.</div>
            ) : (
              <ul className="list-inside list-disc space-y-0.5 text-[9px] text-cmd-text">
                {confidence.contradictingEvidence.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
        <div className="mt-2 border-t border-cmd-border/50 pt-1.5 text-[9px] text-cmd-text">{confidence.alternativeOutcome}</div>
        <div className="mt-1.5 text-[9px] text-cmd-textDim">
          <div className="mb-0.5 uppercase tracking-wider text-cmd-textDim">Key Assumptions</div>
          <ul className="list-inside list-disc space-y-0.5">
            {confidence.keyAssumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      </Glass>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <Glass className="p-2">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>News Risk</TerminalLabel>
            <span title="Named proxy: real count of market-category news items on file, not a real economic calendar">ⓘ</span>
          </div>
          <StatusPill tone={newsRiskTone(eic.newsRisk.riskLevel)}>{eic.newsRisk.riskLevel}</StatusPill>
          <div className="mt-1">
            <DataRow label="Active Market News" value={eic.newsRisk.activeMarketNewsCount} />
          </div>
          <div className="mt-1 text-[9px] text-cmd-textDim">{eic.newsRisk.detail}</div>
        </Glass>

        <Glass className="p-2">
          <TerminalLabel>Correlation Clustering — held symbols only</TerminalLabel>
          {eic.correlationPairs.length === 0 ? (
            <EmptyState>No currently-held symbols clear the correlation threshold.</EmptyState>
          ) : (
            <div className="space-y-1">
              {eic.correlationPairs.map((pair) => (
                <div key={`${pair.symbolA}-${pair.symbolB}`} className="flex items-center justify-between rounded-sm border border-cmd-border/40 bg-cmd-bg/60 p-1.5 text-[9px]">
                  <span className="text-cmd-text">
                    {pair.symbolA} ↔ {pair.symbolB}
                  </span>
                  <StatusPill tone={pair.direction === "positive" ? "amber" : "cyan"}>
                    {pair.direction} {pair.correlation.toFixed(2)}
                  </StatusPill>
                </div>
              ))}
            </div>
          )}
        </Glass>
      </div>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Daily Economic Intelligence Brief</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">One real snapshot per in-game evening ({economicIntelligenceReports.length} on record)</span>
        </div>
        {!latestReport ? (
          <EmptyState>No brief has been generated yet — the first one lands at the end of the current in-game day.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-cmd-textDim">Day {latestReport.simDay}</span>
              <span className="text-cmd-cyan">{latestReport.narrative.headline}</span>
            </div>
            <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px] text-cmd-text">{latestReport.narrative.body}</div>
            {latestReport.narrative.evidence.length > 0 && (
              <ul className="list-inside list-disc space-y-0.5 text-[9px] text-cmd-textDim">
                {latestReport.narrative.evidence.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </Glass>
    </div>
  );
}
