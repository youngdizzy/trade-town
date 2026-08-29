import { useEffect, useMemo, useState } from "react";
import { api } from "@/net/api";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { EvidenceConfluenceRead, ProcessAdherenceRead, TradeDecision, VolumeConfirmationRead } from "@/types";
import { CONFIDENCE_TIER_LABEL } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { CandlestickChart } from "./CandlestickChart";
import { DecisionTimelineList } from "./DecisionTimelineList";
import { EvidenceConfluenceCard } from "./EvidenceConfluenceCard";
import { bearCaseVotes, buildDecisionReplay, buildReplayTimeline, bullCaseVotes, confidenceTierTone, exitOrdersForPosition, formatMoney, linkedOrderFor, marketRegimeHeuristic, voteDirection } from "./lib/derive";
import { useCandles } from "./lib/useCandles";
import { StrategyCertificationChecklist } from "./panels/sandbox/StrategyCertificationChecklist";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "./ui";

const TIMEFRAMES = ["15m", "1h", "4h", "1d"];

/**
 * The "why does the AI want this trade?" drill-down. Every section below
 * maps onto a real TradeDecision field — see types.ts — rather than a
 * fabricated structure: Trade Thesis is `finalReasoning`, Bull/Bear Case are
 * the real per-agent votes split by `supportingAgents`/`opposingAgents`,
 * Market Context is `technicalSummary`/`fundamentalSummary` plus the same
 * regime heuristic used elsewhere, and Invalidation reuses `riskSummary`
 * (TradeTown has no separate "what would disprove this" field, but
 * riskSummary is Guardian/Sentinel's honest answer to "what could go
 * wrong"). Final Decision only ever renders APPROVED or REJECTED — a
 * "REDUCED" state is not implemented because nothing in the backend
 * distinguishes a reduced-size trade from a normal one.
 */
export function DecisionDetail({ decision, onClose }: { decision: TradeDecision; onClose: () => void }) {
  const { watchlist, paperPortfolio, ceoDecisions, debates, challengeReports, disciplineReviews, caseStudies, marketIntelligence } = useGameStore();
  const regime = marketRegimeHeuristic(watchlist);
  // CEO directive "Live Desk + Trade Observability," Phase 9 — the same
  // real research -> signal -> debate -> risk -> CEO -> execution ->
  // management -> exit chain the Replay tab already builds (see
  // ReplayPanel.tsx), reused here rather than reimplemented so a trade's
  // inspector panel can show its own full decision timeline.
  const replayLinks = useMemo(
    () => buildDecisionReplay(decision, { ceoDecisions, debates, challengeReports, disciplineReviews, caseStudies, portfolio: paperPortfolio }),
    [decision, ceoDecisions, debates, challengeReports, disciplineReviews, caseStudies, paperPortfolio]
  );
  const timeline = useMemo(() => buildReplayTimeline(replayLinks), [replayLinks]);
  const bulls = bullCaseVotes(decision);
  const bears = bearCaseVotes(decision);
  const order = linkedOrderFor(decision, paperPortfolio.orders);
  // Professional Quant Live Trading Desk — prefer the real, deterministic
  // link (PaperPosition.proposalId, set at open_position() time; a
  // TradeDecision.id is always `decision-{proposalId}`, the same
  // convention app/executive.py's resolve_proposal() mints it with) over
  // the old symbol-based guess, which silently picked the wrong position
  // whenever two agents held simultaneous positions on the same symbol.
  // Falls back to the symbol match only for a position opened before
  // proposalId existed (never guessed further than that).
  const proposalId = decision.id.replace(/^decision-/, "");
  const position = paperPortfolio.positions.find((p) => p.proposalId === proposalId) ?? paperPortfolio.positions.find((p) => p.symbol === decision.symbol) ?? null;
  const exitOrders = position ? exitOrdersForPosition(position.id, paperPortfolio.orders) : [];
  const approved = decision.outcome === "trade" && decision.orderId !== null;
  const closedTrade = paperPortfolio.tradeHistory.find((t) => t.decisionId === decision.id) ?? null;

  const [timeframe, setTimeframe] = useState("1h");
  const { candles, loading, error } = useCandles(decision.symbol, timeframe, 80);
  const dataStatus = candles[0]?.dataStatus ?? null;

  const [processAdherence, setProcessAdherence] = useState<ProcessAdherenceRead | null>(null);
  useEffect(() => {
    let cancelled = false;
    api
      .getProcessAdherence(decision.id)
      .then((res) => {
        if (!cancelled) setProcessAdherence(res);
      })
      .catch(() => {
        // Real, honest silence — this section simply doesn't render if the read fails.
      });
    return () => {
      cancelled = true;
    };
  }, [decision.id]);

  // CEO directive "TradeTown — 11/10 Market Intelligence + Quant
  // Research Engine" — Trade Inspection Panel. Volume Confirmation and
  // Evidence Confluence were both real, already-tested backend reads
  // (app/volume_analysis.py, app/evidence_confluence.py) with zero
  // consumers anywhere in the frontend — a repo-wide grep confirmed
  // VolumeConfirmationRead/getVolumeConfirmation were entirely unwired.
  // Fetched for the symbol/timeframe already selected in the Chart
  // section below, so all market-microstructure reads on this panel
  // describe the same window.
  const [volumeConfirmation, setVolumeConfirmation] = useState<VolumeConfirmationRead | null>(null);
  useEffect(() => {
    let cancelled = false;
    api
      .getVolumeConfirmation(decision.symbol, timeframe)
      .then((res) => !cancelled && setVolumeConfirmation(res))
      .catch(() => !cancelled && setVolumeConfirmation(null));
    return () => {
      cancelled = true;
    };
  }, [decision.symbol, timeframe]);

  const [evidenceConfluence, setEvidenceConfluence] = useState<EvidenceConfluenceRead | null>(null);
  useEffect(() => {
    let cancelled = false;
    api
      .getEvidenceConfluence(decision.symbol, timeframe)
      .then((res) => !cancelled && setEvidenceConfluence(res))
      .catch(() => !cancelled && setEvidenceConfluence(null));
    return () => {
      cancelled = true;
    };
  }, [decision.symbol, timeframe]);

  // Liquidity/Market Structure are already real, already-broadcast state
  // (MarketIntelligenceState.liquidity[]/structure[] — the same reads
  // MarketChartPanel's new sweep/BOS/CHoCH markers use), so no separate
  // fetch is needed here.
  const liquidity = marketIntelligence.liquidity.find((l) => l.symbol === decision.symbol) ?? null;
  const structure = marketIntelligence.structure.find((s) => s.symbol === decision.symbol) ?? null;

  return (
    <div className="absolute inset-0 z-10 flex items-center justify-center bg-cmd-bg/80 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-sm border border-cmd-border bg-cmd-panel shadow-cmd-cyan"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="sticky top-0 flex items-center justify-between border-b border-cmd-border bg-cmd-panel/95 px-4 py-3 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <span className="font-cmdmono text-xl text-cmd-cyan">{decision.symbol}</span>
            <span className="text-cmd-textDim">{voteDirection(decision.votes)}</span>
            <StatusPill tone={approved ? "green" : "amber"}>{approved ? "APPROVED" : "REJECTED"}</StatusPill>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-sm border border-cmd-border px-2.5 py-1 text-cmd-textDim transition-colors hover:border-cmd-red/50 hover:text-cmd-red"
          >
            CLOSE ✕
          </button>
        </header>

        <div className="space-y-3 p-4">
          <Glass className="p-3">
            <TerminalLabel>Trade Thesis</TerminalLabel>
            <p className="text-cmd-text">{decision.finalReasoning}</p>
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Decision Timeline — research through exit, real records only</TerminalLabel>
            <DecisionTimelineList stages={timeline} />
          </Glass>

          {position?.strategyId && <StrategyCertificationChecklist strategyId={position.strategyId} />}

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Glass className="border-cmd-green/30 p-3">
              <TerminalLabel>Bull Case ({bulls.length})</TerminalLabel>
              {bulls.length === 0 ? (
                <EmptyState>No supporting votes.</EmptyState>
              ) : (
                <div className="space-y-1.5">
                  {bulls.map((v) => (
                    <div key={v.agentId} className="border-b border-cmd-border/50 pb-1 last:border-0">
                      <div className="text-cmd-green">{AGENT_PROFILES[v.agentId].name}</div>
                      <div className="text-[9px] text-cmd-textDim">{v.reason}</div>
                    </div>
                  ))}
                </div>
              )}
            </Glass>

            <Glass className="border-cmd-red/30 p-3">
              <TerminalLabel>Bear Case ({bears.length})</TerminalLabel>
              {bears.length === 0 ? (
                <EmptyState>No opposing votes.</EmptyState>
              ) : (
                <div className="space-y-1.5">
                  {bears.map((v) => (
                    <div key={v.agentId} className="border-b border-cmd-border/50 pb-1 last:border-0">
                      <div className="text-cmd-red">{AGENT_PROFILES[v.agentId].name}</div>
                      <div className="text-[9px] text-cmd-textDim">{v.reason}</div>
                    </div>
                  ))}
                </div>
              )}
            </Glass>
          </div>

          <Glass className="p-3">
            <TerminalLabel>Market Context</TerminalLabel>
            <DataRow label="Regime" value={regime.label} />
            <div className="mt-1.5 space-y-1 text-[9px] text-cmd-textDim">
              <div>{regime.detail}</div>
              <div className="text-cmd-text">{decision.technicalSummary}</div>
              <div className="text-cmd-text">{decision.fundamentalSummary}</div>
            </div>
          </Glass>

          {(volumeConfirmation ?? liquidity ?? structure) && (
            <Glass className="p-3">
              <TerminalLabel>Volume & Liquidity — {decision.symbol}</TerminalLabel>
              <div className="mt-1 grid grid-cols-2 gap-x-4 sm:grid-cols-3">
                {volumeConfirmation && (
                  <>
                    <DataRow label="Relative Volume" value={`${volumeConfirmation.relativeVolume.toFixed(2)}x`} />
                    <DataRow label="Volume State" value={volumeConfirmation.volumeState} />
                    <DataRow label="Confirmation" value={volumeConfirmation.confirmationState.replace(/_/g, " ")} />
                  </>
                )}
                {liquidity && (
                  <>
                    <DataRow label="Liquidity Score" value={liquidity.liquidityScore.toFixed(0)} />
                    <DataRow
                      label="Liquidity Sweep"
                      value={liquidity.sweepDetected ? liquidity.sweepDirection.replace(/_/g, " ") : "none detected"}
                      valueClassName={liquidity.sweepDetected ? "text-cmd-amber" : "text-cmd-textDim"}
                    />
                  </>
                )}
                {structure && (
                  <>
                    <DataRow label="Structure State" value={structure.structureState.replace(/_/g, " ")} />
                    <DataRow label="Last Break of Structure" value={structure.lastBreakOfStructure} />
                    {structure.changeOfCharacter !== "none" && (
                      <DataRow label="Change of Character" value={structure.changeOfCharacter} valueClassName="text-cmd-amber" />
                    )}
                  </>
                )}
              </div>
              {!volumeConfirmation && <div className="mt-1.5 text-[9px] text-cmd-textDim">No real volume confirmation read yet — not enough {timeframe} history for {decision.symbol}.</div>}
            </Glass>
          )}

          {evidenceConfluence && evidenceConfluence.symbol === decision.symbol && (
            <EvidenceConfluenceCard confluence={evidenceConfluence} title={`Evidence Confluence — ${decision.symbol}`} />
          )}

          <Glass className="p-3">
            <div className="mb-2 flex items-center justify-between">
              <TerminalLabel>Chart — {decision.symbol}</TerminalLabel>
              <div className="flex gap-0.5">
                {TIMEFRAMES.map((tf) => (
                  <button
                    key={tf}
                    type="button"
                    onClick={() => setTimeframe(tf)}
                    className={`rounded-sm border px-1.5 py-0.5 text-[9px] uppercase transition-colors ${
                      timeframe === tf ? "border-cmd-cyan/50 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
                    }`}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </div>
            <CandlestickChart
              candles={candles}
              loading={loading}
              error={error}
              dataStatus={dataStatus}
              height={200}
              overlays={{ entry: order?.price, currentPrice: position?.currentPrice }}
            />
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Confidence</TerminalLabel>
            <div className="mb-1 flex items-center justify-between">
              <span className="font-cmdmono text-cmd-text">{Math.round(decision.confidence)}%</span>
              <span className="text-[9px] text-cmd-textDim">
                {decision.supportingAgents.length} supporting · {decision.opposingAgents.length} opposing
              </span>
            </div>
            <Meter value={decision.confidence} tone={decision.confidence >= 70 ? "green" : decision.confidence >= 50 ? "amber" : "red"} />
          </Glass>

          {decision.confidenceEngine && (
            <Glass className="p-3">
              <div className="mb-1 flex items-center justify-between">
                <TerminalLabel>Decision Confidence Engine</TerminalLabel>
                <StatusPill tone={confidenceTierTone(decision.confidenceEngine.tier)}>{CONFIDENCE_TIER_LABEL[decision.confidenceEngine.tier]}</StatusPill>
              </div>
              <div className="mb-1 font-cmdmono text-cmd-text">{Math.round(decision.confidenceEngine.score)}/100</div>
              <Meter
                value={decision.confidenceEngine.score}
                tone={decision.confidenceEngine.score >= 70 ? "green" : decision.confidenceEngine.score >= 45 ? "amber" : "red"}
              />
              <div className="mt-1.5 text-[9px] text-cmd-textDim">{decision.confidenceEngine.summary}</div>
            </Glass>
          )}

          {closedTrade && decision.confidenceEngine && (
            <Glass className={`p-3 ${closedTrade.pnl > 0 ? "border-cmd-green/30" : "border-cmd-red/30"}`}>
              <TerminalLabel>Post-Trade Review</TerminalLabel>
              <DataRow
                label="Setup quality at decision time"
                value={`${Math.round(decision.confidenceEngine.score)}/100 (${CONFIDENCE_TIER_LABEL[decision.confidenceEngine.tier]})`}
              />
              <DataRow label="Actual result" value={`${closedTrade.pnl >= 0 ? "+" : ""}${closedTrade.pnl.toFixed(2)} (${closedTrade.pnlPct.toFixed(1)}%)`} valueClassName={closedTrade.pnl > 0 ? "text-cmd-green" : "text-cmd-red"} />
              <div className="mt-1.5 text-cmd-text">
                {decision.confidenceEngine.score >= 70 && closedTrade.pnl <= 0
                  ? "A losing trade with an excellent setup — still a good decision. Process beats any single outcome."
                  : decision.confidenceEngine.score < 55 && closedTrade.pnl > 0
                    ? "A winning trade with a weak setup — this reads as luck, not skill. Don't mistake this one for validation of the process."
                    : decision.confidenceEngine.score >= 70 && closedTrade.pnl > 0
                      ? "A strong setup that also won — the process and the outcome agree."
                      : "A weak setup that also lost — the process correctly flagged the risk here."}
              </div>
            </Glass>
          )}

          <Glass className="p-3">
            <TerminalLabel>Trade Plan</TerminalLabel>
            {order ? (
              <>
                <DataRow label="Side" value={order.side.toUpperCase()} />
                <DataRow label="Order type" value={order.orderType} />
                <DataRow label="Quantity" value={order.quantity} />
                <DataRow label="Price" value={formatMoney(order.price)} />
                <DataRow label="Placed by" value={AGENT_PROFILES[order.placedBy].name} />
                {exitOrders.length > 0 ? (
                  exitOrders.map((eo) => <DataRow key={eo.id} label={`Exit (${eo.orderType})`} value={`${eo.quantity} @ ${formatMoney(eo.price)}`} />)
                ) : (
                  <div className="mt-1 text-[9px] text-cmd-textDim">No stop-loss or take-profit order attached — TradeTown&apos;s auto-trader doesn&apos;t place exit orders yet.</div>
                )}
              </>
            ) : approved ? (
              <EmptyState>
                Order not found — TradeTown&apos;s order log only keeps the most recent 40 resolved orders (see broker.py&apos;s
                MAX_ORDER_LOG), so an older approved decision&apos;s order may have aged out.
              </EmptyState>
            ) : (
              <EmptyState>No order was placed — this decision was not approved.</EmptyState>
            )}
          </Glass>

          {processAdherence && (
            <Glass className="p-3">
              <div className="mb-1.5 flex items-center justify-between">
                <TerminalLabel>Process Adherence</TerminalLabel>
                <span className="font-cmdmono text-cmd-text">
                  {processAdherence.scorePct !== null ? `${processAdherence.scorePct.toFixed(0)}%` : "N/A"}
                </span>
              </div>
              <div className="mb-2 text-[9px] text-cmd-textDim">
                Verified checks: {processAdherence.passedCount}/{processAdherence.verifiedCount} · Not trackable yet: {processAdherence.notTrackableCount} · Failed:{" "}
                {processAdherence.failedCount}
              </div>
              <div className="space-y-1">
                {processAdherence.checks.map((c) => (
                  <div key={c.id} className="flex items-start justify-between gap-2 border-b border-cmd-border/50 py-0.5 text-[9px] last:border-0">
                    <span className="text-cmd-textDim">{c.label}</span>
                    <span
                      className={
                        c.status === "passed" ? "shrink-0 text-cmd-green" : c.status === "failed" ? "shrink-0 text-cmd-red" : "shrink-0 text-cmd-textDim"
                      }
                    >
                      {c.status === "passed" ? "PASSED" : c.status === "failed" ? "FAILED" : "NOT TRACKABLE YET"}
                    </span>
                  </div>
                ))}
              </div>
              <p className="mt-2 text-[8px] text-cmd-textDim/70">
                Full plan adherence requires future execution/order-plan infrastructure this paper-trading engine does not have yet — stop-loss/take-profit/entry/exit/confluence checks
                above are honestly reported as not trackable, never scored as pass or fail.
              </p>
            </Glass>
          )}

          <Glass className="p-3">
            <TerminalLabel>Invalidation — What Would Prove This Thesis Wrong?</TerminalLabel>
            <p className="text-cmd-text">{decision.riskSummary}</p>
          </Glass>

          <Glass className={`p-3 ${approved ? "border-cmd-green/40" : "border-cmd-amber/40"}`}>
            <TerminalLabel>Final Decision</TerminalLabel>
            <div className={`font-cmdmono text-lg ${approved ? "text-cmd-green" : "text-cmd-amber"}`}>{approved ? "APPROVED" : "REJECTED"}</div>
            {!approved && <div className="mt-1 text-cmd-textDim">{decision.finalReasoning}</div>}
          </Glass>
        </div>
      </div>
    </div>
  );
}
