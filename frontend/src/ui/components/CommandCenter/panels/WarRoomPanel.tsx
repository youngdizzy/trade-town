import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { EXECUTIVE_ACTION_LABEL, EXECUTIVE_STANCE_LABEL, type PositionTier, type WarRoomSession } from "@/types";
import { EvidenceConfluenceCard } from "../EvidenceConfluenceCard";
import { executiveActionTone, executiveStanceTone, formatMoney } from "../lib/derive";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

const UNAVAILABLE = "text-cmd-textDim italic";

const TIER_TONE: Record<PositionTier, "neutral" | "cyan" | "purple" | "green"> = {
  exploratory: "neutral",
  standard: "cyan",
  high_conviction: "purple",
  institutional: "green",
};

/**
 * v0.7 Feature 55 (the brief self-numbered it "Feature 54," already used
 * elsewhere in this codebase for the Decision Memory System) — the
 * Executive Decision Simulator's Digital War Room
 * (backend/app/war_room.py). Every WarRoomSession is built eagerly the
 * instant a TradeProposal is created, joining department opinions, the
 * What-If Simulation Lab's 12 real scenarios, the Decision Vault's
 * similarity engine, a real Expected Value read, a composite Decision
 * Score, and a signal-grounded Contingency Plan — never computed on
 * request in this panel.
 */
export function WarRoomPanel() {
  const { warRoomSessions } = useGameStore();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const recentSessions = useMemo(() => [...warRoomSessions].reverse(), [warRoomSessions]);
  const selected = useMemo(() => warRoomSessions.find((s) => s.id === selectedId) ?? recentSessions[0] ?? null, [warRoomSessions, selectedId, recentSessions]);

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <Glass className="max-h-[32rem] overflow-y-auto p-3 lg:col-span-1">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>War Room</TerminalLabel>
          <StatusPill tone="purple">{warRoomSessions.length} session{warRoomSessions.length === 1 ? "" : "s"}</StatusPill>
        </div>
        {recentSessions.length === 0 ? (
          <EmptyState>No proposal has entered the War Room yet — every new Trading Floor proposal is stress-tested here the instant Executive Voting opens.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {recentSessions.map((session) => (
              <SessionRow key={session.id} session={session} selected={session.id === (selected?.id ?? null)} onSelect={() => setSelectedId(session.id)} />
            ))}
          </div>
        )}
      </Glass>

      <div className="space-y-3 lg:col-span-2">
        {selected ? <SessionDetail session={selected} /> : <Glass className="p-3"><EmptyState>Select a session to see its full War Room read.</EmptyState></Glass>}
      </div>
    </div>
  );
}

function SessionRow({ session, selected, onSelect }: { session: WarRoomSession; selected: boolean; onSelect: () => void }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-sm border p-1.5 text-left text-[9px] ${selected ? "border-cmd-cyan/60 bg-cmd-cyan/10" : "border-cmd-border/60 bg-cmd-bg/40 hover:border-cmd-border"}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5">
          <span className="text-cmd-cyan">{session.symbol}</span>
          <StatusPill tone={session.decisionScore.passed ? "green" : "amber"}>{session.decisionScore.overall.toFixed(0)}/100</StatusPill>
        </span>
        <span className={`tabular-nums ${session.expectedValue.positiveExpectancy ? "text-cmd-green" : "text-cmd-red"}`}>
          EV {session.expectedValue.expectedValuePct >= 0 ? "+" : ""}
          {session.expectedValue.expectedValuePct.toFixed(1)}%
        </span>
      </div>
      <div className="mt-0.5 flex items-center justify-between text-cmd-textDim">
        <StatusPill tone={executiveActionTone(session.recommendation.action)}>{EXECUTIVE_ACTION_LABEL[session.recommendation.action]}</StatusPill>
        {session.outcomeComparison && <span className={session.outcomeComparison.withinPredictedRange ? "text-cmd-green" : "text-cmd-amber"}>outcome in</span>}
      </div>
    </button>
  );
}

/**
 * CEO directive "Portfolio Construction, Capital Allocation & Execution
 * Realism," Phase 9 — a consolidated "WHY THIS TRADE?" summary. Every
 * value here is a real, already-computed read joined from state already
 * on the store (WarRoomSession + the matching TradeProposal) — nothing
 * new is computed. Genuine gaps this codebase cannot honestly fill for
 * a still-pending proposal are named explicitly ("Unavailable — ...")
 * rather than guessed or left silently blank; see docs/Architecture.md's
 * Phase 9 section for the full research behind each one.
 */
function WhyThisTradeCard({ session }: { session: WarRoomSession }) {
  const { tradeProposals } = useGameStore();
  const proposal = tradeProposals.find((p) => p.id === session.proposalId) ?? null;
  const vol = session.positionSizing?.volatilitySizing;

  return (
    <Glass className="border border-cmd-cyan/30 p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Why This Trade? — {session.symbol}</TerminalLabel>
        <StatusPill tone={executiveActionTone(session.recommendation.action)}>{EXECUTIVE_ACTION_LABEL[session.recommendation.action]}</StatusPill>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
        <DataRow label="Strategy" value={<span className={UNAVAILABLE}>Unavailable — not selected until the CEO decides (see Strategy below War Room)</span>} />
        <DataRow label="Entry (signal price)" value={proposal ? formatMoney(proposal.price) : <span className={UNAVAILABLE}>Unavailable — proposal no longer pending</span>} />
        <DataRow
          label="Stop distance (ATR-based)"
          value={vol?.available ? `${vol.stopDistance?.toFixed(2) ?? "—"}` : <span className={UNAVAILABLE}>Unavailable — {vol?.detail ?? "not computed"}</span>}
        />
        <DataRow label="Target price" value={<span className={UNAVAILABLE}>Unavailable — no live target-price mechanism exists for a live trade</span>} />
        <DataRow
          label="Expected Value"
          value={`${session.expectedValue.expectedValuePct >= 0 ? "+" : ""}${session.expectedValue.expectedValuePct.toFixed(2)}%`}
          valueClassName={session.expectedValue.expectedValuePct >= 0 ? "text-cmd-green" : "text-cmd-red"}
        />
        <DataRow label="Expected R-multiple" value={<span className={UNAVAILABLE}>Unavailable — no live stop-loss order exists to compute a real R against</span>} />
        <DataRow label="Risk budget" value={vol?.available ? formatMoney(vol.riskBudgetUsd ?? 0) : <span className={UNAVAILABLE}>Unavailable</span>} />
        <DataRow label="Position size" value={session.positionSizing ? session.positionSizing.finalQuantity.toFixed(4) : <span className={UNAVAILABLE}>Not yet sized</span>} />
        <DataRow label="Regime / Session" value={<span className={UNAVAILABLE}>Unavailable — only stamped once this trade closes (see Decision Vault)</span>} />
        <DataRow label="Portfolio Fit (category)" value={`${session.decisionScore.portfolioCompatibilityScore.toFixed(0)}/100`} />
        <DataRow
          label="Statistical correlation (Pearson)"
          value={session.statisticalCorrelatedPositions !== null ? `${session.statisticalCorrelatedPositions} correlated position(s)` : <span className={UNAVAILABLE}>Not computed for this session</span>}
        />
        <DataRow label="Agent evidence" value={`${session.recommendation.supporting.length} supporting / ${session.recommendation.opposing.length} opposing`} />
        <DataRow label="Risk checks (Gatekeeper)" value={<span className={UNAVAILABLE}>Unavailable — only run at CEO-decision time, not yet for a pending proposal</span>} />
        <DataRow label="Execution constraints" value={<span className={UNAVAILABLE}>Unavailable — slippage is only realized at fill time</span>} />
        <DataRow label="Final decision" value={<span className="text-cmd-amber">Pending — CEO has not decided yet</span>} />
      </div>
    </Glass>
  );
}

function SessionDetail({ session }: { session: WarRoomSession }) {
  return (
    <>
      <WhyThisTradeCard session={session} />

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>{session.symbol} — Decision Score</TerminalLabel>
          <StatusPill tone={session.decisionScore.passed ? "green" : "amber"}>
            {session.decisionScore.overall.toFixed(0)} / {session.decisionScore.threshold.toFixed(0)} {session.decisionScore.passed ? "PASSED" : "BELOW BAR"}
          </StatusPill>
        </div>
        <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
          <ScoreCell label="Evidence" value={session.decisionScore.evidenceScore} />
          <ScoreCell label="Confidence" value={session.decisionScore.confidenceScore} />
          <ScoreCell label="Risk" value={session.decisionScore.riskScore} />
          <ScoreCell label="Expected Value" value={session.decisionScore.expectedValueScore} />
          <ScoreCell label="Market Quality" value={session.decisionScore.marketQualityScore} />
          <ScoreCell label="Liquidity Quality" value={session.decisionScore.liquidityQualityScore} />
          <ScoreCell label="Portfolio Fit" value={session.decisionScore.portfolioCompatibilityScore} />
          <ScoreCell label="Strategy Health" value={session.decisionScore.strategyHealthScore} placeholder="n/a — not a tested strategy" />
          <ScoreCell label="Evidence Confluence" value={session.decisionScore.evidenceConfluenceScore} placeholder="n/a — no candle history" />
        </div>
        {!session.confidenceValidated && (
          <div className="mt-2 rounded-sm border border-cmd-red/50 bg-cmd-red/10 p-1.5 text-[9px] text-cmd-red">
            ⚠ Confidence exceeds evidence — this should never happen; flag for review.
          </div>
        )}
      </Glass>

      {session.evidenceConfluence && <EvidenceConfluenceCard confluence={session.evidenceConfluence} title={`Evidence Confluence — ${session.symbol}`} />}

      {session.confluenceClassification && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Confluence Classification — {session.confluenceClassification.targetDirection}</TerminalLabel>
            <span className="text-[9px] text-cmd-textDim">Evidence families vs. this trade's own direction</span>
          </div>
          <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
            {(
              [
                ["Supporting", session.confluenceClassification.supporting, "text-cmd-green"],
                ["Conflicting", session.confluenceClassification.conflicting, "text-cmd-red"],
                ["Neutral", session.confluenceClassification.neutral, "text-cmd-textDim"],
                ["Missing", session.confluenceClassification.missing, "text-cmd-amber"],
              ] as const
            ).map(([label, families, tone]) => (
              <div key={label} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className={tone}>{label} ({families.length})</div>
                <div className="mt-0.5 text-cmd-textDim">{families.length > 0 ? families.map((f) => f.replace(/_/g, " ")).join(", ") : "—"}</div>
              </div>
            ))}
          </div>
          <p className="mt-1.5 text-[8px] italic text-cmd-textDim">{session.confluenceClassification.detail}</p>
        </Glass>
      )}

      <Glass className="p-3">
        <TerminalLabel>Expected Value — real read over the 12 real simulated scenarios</TerminalLabel>
        <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
          <DataRow
            label="Expected Value"
            value={`${session.expectedValue.expectedValuePct >= 0 ? "+" : ""}${session.expectedValue.expectedValuePct.toFixed(2)}%`}
            valueClassName={session.expectedValue.expectedValuePct >= 0 ? "text-cmd-green" : "text-cmd-red"}
          />
          <DataRow label="Edge vs. Baseline" value={`${session.expectedValue.edgePct >= 0 ? "+" : ""}${session.expectedValue.edgePct.toFixed(2)}%`} />
          <DataRow label="Risk-to-Reward" value={session.expectedValue.riskToReward.toFixed(2)} />
        </div>
        <p className="mt-1.5 text-[9px] text-cmd-textDim">{session.expectedValue.detail}</p>
      </Glass>

      {session.positionSizing && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Position Sizing — Capital Deployment Engine</TerminalLabel>
            <StatusPill tone={TIER_TONE[session.positionSizing.tier]}>{session.positionSizing.tierLabel}</StatusPill>
          </div>
          <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
            <DataRow label="Sizing Score" value={`${session.positionSizing.sizingScore.toFixed(0)}/100`} />
            <DataRow label="Risk Ceiling" value={session.positionSizing.ceilingQuantity.toFixed(4)} />
            <DataRow label="Final Quantity" value={session.positionSizing.finalQuantity.toFixed(4)} valueClassName={session.positionSizing.reducedFromCeiling ? "text-cmd-amber" : "text-cmd-green"} />
          </div>
          <div className="mt-2">
            <div className="mb-0.5 flex items-center justify-between text-[9px] text-cmd-textDim">
              <span>Final vs. risk ceiling — this engine only ever narrows it, never widens it</span>
              <span className="tabular-nums">{session.positionSizing.ceilingQuantity > 0 ? ((session.positionSizing.finalQuantity / session.positionSizing.ceilingQuantity) * 100).toFixed(0) : "0"}%</span>
            </div>
            <Meter value={session.positionSizing.finalQuantity} max={Math.max(session.positionSizing.ceilingQuantity, session.positionSizing.finalQuantity, 1e-9)} tone={session.positionSizing.reducedFromCeiling ? "amber" : "green"} />
          </div>
          <div className="mt-2">
            <div className="mb-0.5 flex items-center justify-between text-[9px] text-cmd-textDim">
              <span>Weekly capital deployment budget used</span>
              <span className="tabular-nums">
                {session.positionSizing.weeklyDeploymentPct.toFixed(1)}% / {session.positionSizing.weeklyDeploymentCapPct.toFixed(1)}%
              </span>
            </div>
            <Meter value={session.positionSizing.weeklyDeploymentPct} max={session.positionSizing.weeklyDeploymentCapPct} tone={session.positionSizing.weeklyDeploymentPct >= session.positionSizing.weeklyDeploymentCapPct ? "red" : "cyan"} />
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <StatusPill tone={session.positionSizing.cashReserveOk ? "green" : "red"}>Cash reserve {session.positionSizing.cashReserveOk ? "OK" : "BINDING"}</StatusPill>
            <StatusPill tone={session.positionSizing.portfolioHeatCapOk ? "green" : "red"}>Heat cap {session.positionSizing.portfolioHeatCapOk ? "OK" : "BINDING"}</StatusPill>
            {session.positionSizing.institutionalGatesPassed && <StatusPill tone="green">All 3 Institutional gates passed</StatusPill>}
          </div>
          <p className="mt-1.5 text-[9px] text-cmd-textDim">{session.positionSizing.detail}</p>

          {/* CEO directive "Portfolio Construction, Capital Allocation &
              Execution Realism," Phase 3 — real ATR-based risk-per-unit
              sizing. available: false is its own honest state (never a
              fabricated stop distance) — no candle history yet. */}
          <div className="mt-2 border-t border-cmd-border/50 pt-2">
            <div className="mb-1 flex items-center justify-between">
              <TerminalLabel>Volatility-Based Risk Sizing — real ATR, risk budget ÷ stop distance</TerminalLabel>
              <StatusPill tone={session.positionSizing.volatilitySizing.available ? "cyan" : "neutral"}>
                {session.positionSizing.volatilitySizing.available ? "AVAILABLE" : "UNAVAILABLE"}
              </StatusPill>
            </div>
            {session.positionSizing.volatilitySizing.available ? (
              <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-4">
                <DataRow label={`ATR (${session.positionSizing.volatilitySizing.atrPeriod}-period)`} value={session.positionSizing.volatilitySizing.atrValue?.toFixed(2) ?? "—"} />
                <DataRow label="Stop Distance" value={session.positionSizing.volatilitySizing.stopDistance?.toFixed(2) ?? "—"} />
                <DataRow label="Risk Budget" value={`$${session.positionSizing.volatilitySizing.riskBudgetUsd?.toFixed(0) ?? "—"}`} />
                <DataRow label="Volatility Cap" value={session.positionSizing.volatilitySizing.volatilityCapQuantity?.toFixed(4) ?? "—"} />
              </div>
            ) : (
              <p className="text-[9px] text-cmd-textDim">{session.positionSizing.volatilitySizing.detail}</p>
            )}
          </div>

          {/* AHL directive follow-up — promotes the real, previously
              research-only inverse-volatility exposure calculator into
              this live, advisory-only narrowing cap. A SINGLE-position
              scaler — see the cross-portfolio section below for the
              real, naive risk-parity read across every open position. */}
          <div className="mt-2 border-t border-cmd-border/50 pt-2">
            <div className="mb-1 flex items-center justify-between">
              <TerminalLabel>Inverse-Volatility Sizing — AHL-inspired research cap</TerminalLabel>
              <StatusPill tone={session.positionSizing.inverseVolSizing ? "cyan" : "neutral"}>
                {session.positionSizing.inverseVolSizing ? "AVAILABLE" : "UNAVAILABLE"}
              </StatusPill>
            </div>
            {session.positionSizing.inverseVolSizing ? (
              <>
                <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-4">
                  <DataRow label="Volatility Estimate" value={`${session.positionSizing.inverseVolSizing.volatilityEstimatePct.toFixed(2)}%`} />
                  <DataRow label="Target Risk" value={`${session.positionSizing.inverseVolSizing.targetRiskPct.toFixed(2)}%`} />
                  <DataRow label="Raw Exposure" value={`${session.positionSizing.inverseVolSizing.rawExposurePct.toFixed(2)}%`} />
                  <DataRow label="Capped Exposure" value={`${session.positionSizing.inverseVolSizing.cappedExposurePct.toFixed(2)}%`} valueClassName={session.positionSizing.inverseVolSizing.wasCapped ? "text-cmd-amber" : undefined} />
                </div>
                <p className="mt-1 text-[9px] text-cmd-textDim">{session.positionSizing.inverseVolSizing.detail}</p>
              </>
            ) : (
              <p className="text-[9px] text-cmd-textDim">Not enough real candle history yet for a volatility estimate.</p>
            )}
          </div>

          {/* AHL directive follow-up — closes the honesty gap the
              section above discloses: this candidate's own exposure now
              also depends on every OTHER real currently-open position's
              own real volatility, a naive (uncorrelated) risk-parity
              read across the whole real portfolio. STILL NOT full
              covariance-based Equal Risk Contribution — real
              correlation between held symbols is not incorporated. */}
          <div className="mt-2 border-t border-cmd-border/50 pt-2">
            <div className="mb-1 flex items-center justify-between">
              <TerminalLabel>Cross-Portfolio Risk Parity — naive inverse-vol across all open positions</TerminalLabel>
              <StatusPill tone={session.positionSizing.crossPortfolioRiskSizing ? "cyan" : "neutral"}>
                {session.positionSizing.crossPortfolioRiskSizing ? "AVAILABLE" : "UNAVAILABLE"}
              </StatusPill>
            </div>
            {session.positionSizing.crossPortfolioRiskSizing ? (
              <>
                <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-4">
                  <DataRow label="Real Positions" value={`${session.positionSizing.crossPortfolioRiskSizing.positionCount}`} />
                  <DataRow label="Fair Share" value={`${session.positionSizing.crossPortfolioRiskSizing.candidateWeightPct.toFixed(1)}%`} />
                  <DataRow label="Fair-Share Risk" value={`${session.positionSizing.crossPortfolioRiskSizing.fairShareRiskPct.toFixed(3)}%`} />
                  <DataRow
                    label="Capped Exposure"
                    value={`${session.positionSizing.crossPortfolioRiskSizing.finalExposure.cappedExposurePct.toFixed(2)}%`}
                    valueClassName={session.positionSizing.crossPortfolioRiskSizing.finalExposure.wasCapped ? "text-cmd-amber" : undefined}
                  />
                </div>
                <p className="mt-1 text-[9px] text-cmd-textDim">{session.positionSizing.crossPortfolioRiskSizing.detail}</p>
              </>
            ) : (
              <p className="text-[9px] text-cmd-textDim">Not enough real candle history yet for a volatility estimate.</p>
            )}
          </div>

          {/* CEO directive "Portfolio Risk Engine, 11/10 Professional
              Quant-Firm Implementation" — the real correlation/
              concentration-cluster reduction, now actually wired into
              this narrowing-only cap chain (not just shown as advisory
              evidence elsewhere). Deliberately never shows a "vetoed"
              state here caused by a Sentinel/emergency-stop violation —
              see backend/app/portfolio_risk.py::
              compute_correlation_concentration_cap()'s own docstring for
              why that stays exclusively the Gatekeeper's job. */}
          <div className="mt-2 border-t border-cmd-border/50 pt-2">
            <div className="mb-1 flex items-center justify-between">
              <TerminalLabel>Marginal Risk Test — real correlation/concentration cluster cap</TerminalLabel>
              <StatusPill tone={session.positionSizing.marginalRiskDecision ? "cyan" : "neutral"}>
                {session.positionSizing.marginalRiskDecision ? "AVAILABLE" : "UNAVAILABLE"}
              </StatusPill>
            </div>
            {session.positionSizing.marginalRiskDecision ? (
              <>
                <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-4">
                  <DataRow label="Requested" value={`$${session.positionSizing.marginalRiskDecision.requestedValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
                  <DataRow
                    label="Allowed"
                    value={`$${session.positionSizing.marginalRiskDecision.allowedValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
                    valueClassName={session.positionSizing.marginalRiskDecision.allowedValue < session.positionSizing.marginalRiskDecision.requestedValue ? "text-cmd-amber" : undefined}
                  />
                  <DataRow label="Its Own Cluster" value={`${session.positionSizing.marginalRiskDecision.largestClusterPctAfter.toFixed(1)}%`} />
                  <DataRow label="Correlation Impact" value={session.positionSizing.marginalRiskDecision.correlationImpact.toUpperCase()} />
                </div>
                {session.positionSizing.marginalRiskDecision.warnings.map((w) => (
                  <p key={w} className="mt-1 text-[9px] text-cmd-amber">
                    ⚠ {w}
                  </p>
                ))}
                {session.positionSizing.marginalRiskDecision.decision === "data_blocked" && (
                  <p className="mt-1 text-[9px] text-cmd-textDim">{session.positionSizing.marginalRiskDecision.vetoReasons[0]}</p>
                )}
              </>
            ) : (
              <p className="text-[9px] text-cmd-textDim">Not enough real candle history yet for a portfolio-impact read.</p>
            )}
          </div>

          {/* CEO directive "Portfolio Risk Engine, 11/10 Professional
              Quant-Firm Implementation," Phase 2 — promotes backend/app/
              trend_engine.py's own real, previously-unconsumed regime-
              conditional hit-rate evidence into a real, narrowing-only
              cap: a strategy should not receive capital simply because
              it passed a backtest, only when THIS regime specifically
              has historically been favorable for its own signal. */}
          <div className="mt-2 border-t border-cmd-border/50 pt-2">
            <div className="mb-1 flex items-center justify-between">
              <TerminalLabel>Regime Suitability — real hit rate in the current regime</TerminalLabel>
              <StatusPill tone={session.positionSizing.regimeSuitabilitySizing.available ? "cyan" : "neutral"}>
                {session.positionSizing.regimeSuitabilitySizing.available ? "AVAILABLE" : "UNAVAILABLE"}
              </StatusPill>
            </div>
            {session.positionSizing.regimeSuitabilitySizing.available ? (
              <>
                <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-4">
                  <DataRow label="Current Regime" value={session.positionSizing.regimeSuitabilitySizing.currentRegime.replace(/_/g, " ")} />
                  <DataRow label="Bars Observed" value={`${session.positionSizing.regimeSuitabilitySizing.barsObserved}`} />
                  <DataRow label="Hit Rate" value={`${session.positionSizing.regimeSuitabilitySizing.hitRatePct?.toFixed(1) ?? "—"}%`} />
                  <DataRow
                    label="Suitability Scale"
                    value={`${(session.positionSizing.regimeSuitabilitySizing.suitabilityScale * 100).toFixed(0)}%`}
                    valueClassName={session.positionSizing.regimeSuitabilitySizing.suitabilityScale < 1.0 ? "text-cmd-amber" : undefined}
                  />
                </div>
                <p className="mt-1 text-[9px] text-cmd-textDim">{session.positionSizing.regimeSuitabilitySizing.detail}</p>
              </>
            ) : (
              <p className="text-[9px] text-cmd-textDim">{session.positionSizing.regimeSuitabilitySizing.detail}</p>
            )}
          </div>
        </Glass>
      )}

      <Glass className="p-3">
        <TerminalLabel>Contingency Plan — real IF/THEN, tied to live signals</TerminalLabel>
        <div className="space-y-1">
          {session.contingencyPlan.map((step, i) => (
            <div key={i} className={`rounded-sm border p-1.5 text-[9px] ${step.triggered ? "border-cmd-amber/50 bg-cmd-amber/10" : "border-cmd-border/50 bg-cmd-bg/40"}`}>
              <div className="flex items-center justify-between gap-2">
                <span className={step.triggered ? "text-cmd-amber" : "text-cmd-text"}>IF {step.condition}</span>
                {step.triggered && <StatusPill tone="amber">LIVE NOW</StatusPill>}
              </div>
              <div className="mt-0.5 text-cmd-textDim">THEN {step.action}</div>
            </div>
          ))}
        </div>
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Institutional Knowledge Graph — real similar-trade matches</TerminalLabel>
          <StatusPill tone="cyan">{session.similarTrades.matchCount} match{session.similarTrades.matchCount === 1 ? "" : "es"}</StatusPill>
        </div>
        {session.similarTrades.matchCount === 0 ? (
          <EmptyState>No comparable historical decisions yet.</EmptyState>
        ) : (
          <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
            <DataRow label="Win Rate" value={`${session.similarTrades.winRatePct.toFixed(0)}%`} />
            <DataRow label="Avg P&L" value={`${session.similarTrades.avgPnlPct >= 0 ? "+" : ""}${session.similarTrades.avgPnlPct.toFixed(1)}%`} valueClassName={session.similarTrades.avgPnlPct >= 0 ? "text-cmd-green" : "text-cmd-red"} />
            <DataRow label="Worst P&L" value={`${session.similarTrades.worstPnlPct.toFixed(1)}%`} valueClassName="text-cmd-red" />
          </div>
        )}
        {session.similarTrades.warning && (
          <div className="mt-2 rounded-sm border border-cmd-amber/50 bg-cmd-amber/10 p-1.5 text-[9px] text-cmd-amber">⚠ {session.similarTrades.warning}</div>
        )}
      </Glass>

      {session.outcomeComparison && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Predicted vs. Actual — filled in once the trade closed</TerminalLabel>
            <StatusPill tone={session.outcomeComparison.withinPredictedRange ? "green" : "amber"}>
              {session.outcomeComparison.withinPredictedRange ? "WITHIN RANGE" : "OUTSIDE RANGE"}
            </StatusPill>
          </div>
          <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
            <DataRow label="Matched Scenario" value={session.outcomeComparison.matchedLabel} />
            <DataRow label="Predicted Range" value={`${session.outcomeComparison.predictedRangeLowPct.toFixed(1)}% to ${session.outcomeComparison.predictedRangeHighPct.toFixed(1)}%`} />
            <DataRow label="Actual P&L" value={`${session.outcomeComparison.actualPnlPct >= 0 ? "+" : ""}${session.outcomeComparison.actualPnlPct.toFixed(1)}%`} valueClassName={session.outcomeComparison.actualPnlPct >= 0 ? "text-cmd-green" : "text-cmd-red"} />
          </div>
          <p className="mt-1.5 text-[9px] text-cmd-textDim">{session.outcomeComparison.detail}</p>
        </Glass>
      )}

      <Glass className="p-3">
        <TerminalLabel>Department Opinions</TerminalLabel>
        <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
          {session.departmentOpinions.map((op) => (
            <div key={op.role} className="flex items-center justify-between gap-2 rounded-sm border border-cmd-border/40 bg-cmd-bg/60 p-1.5 text-[9px]">
              <span className="flex items-center gap-1.5">
                <span className="text-cmd-textDim">{op.departmentLabel}</span>
                {op.agentId && <span className="text-cmd-textDim">({AGENT_PROFILES[op.agentId].name})</span>}
              </span>
              <StatusPill tone={executiveStanceTone(op.stance)}>{EXECUTIVE_STANCE_LABEL[op.stance]}</StatusPill>
            </div>
          ))}
        </div>
      </Glass>
    </>
  );
}

function ScoreCell({ label, value, placeholder }: { label: string; value: number | null; placeholder?: string }) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
      <div className="text-cmd-textDim">{label}</div>
      <div className="tabular-nums text-cmd-text">{value === null ? placeholder ?? "n/a" : `${value.toFixed(0)}/100`}</div>
    </div>
  );
}
