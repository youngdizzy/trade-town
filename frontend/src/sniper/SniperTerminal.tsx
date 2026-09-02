import { useEffect, useMemo, useState } from "react";
import { api } from "@/net/api";
import { CandlestickChart, type ChartOverlayMarker, type ChartOverlays } from "@/ui/components/CommandCenter/CandlestickChart";
import { useCandles } from "@/ui/components/CommandCenter/lib/useCandles";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "@/ui/components/CommandCenter/ui";
import type { SniperCandidate, SniperEvent, SniperPosition, SniperTrade } from "@/types";

function fmtSol(v: number, digits = 3): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)} SOL`;
}

function fmtPct(v: number, digits = 1): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}%`;
}

const EVENT_TONE: Record<SniperEvent["type"], string> = {
  discovered: "text-cmd-cyan",
  safety_reject: "text-cmd-red",
  qualified: "text-cmd-amber",
  sniped: "text-cmd-green",
  no_trade: "text-cmd-textDim",
  exit: "text-cmd-text",
  manual_exit: "text-cmd-text",
  lesson: "text-cmd-purple",
};

const EXIT_LABEL: Record<SniperTrade["exitReason"], string> = {
  stop_loss: "STOP",
  take_profit: "TP",
  trailing_stop: "TRAIL STOP",
  momentum_failure: "EXIT",
  liquidity_collapse: "EXIT",
  whale_exit: "EXIT",
  max_hold: "EXIT (MAX HOLD)",
  risk_kill: "EXIT (RISK KILL)",
  manual_exit: "MANUAL EXIT",
};

/** "Terminal 2.1" directive, Phase 2 — real chart trade markers, never
 * a fabricated one. Every marker below comes from a real (timestamp,
 * price) pair the backend actually persisted:
 *  - ENTRY: the position/trade's own real entryPrice at openedAt.
 *  - TRAIL ACTIVATION: only rendered once trailingActivatedAt/Price are
 *    both real (non-null) — the exact tick trailing genuinely activated.
 *  - EXIT (labeled by the trade's own real exitReason — STOP/TP/TRAIL
 *    STOP/MANUAL EXIT/etc.): only for a CLOSED trade, at its own real
 *    exitPrice/closedAt.
 * No PARTIAL EXIT marker — this domain has no partial-fill concept
 * anywhere (SniperPosition/SniperTrade confirmed to have no such field);
 * every trade here is all-or-nothing. No FAILED ENTRY marker on this
 * chart either — that's a candidate-level event with no position/trade
 * of its own to chart against; see the Discovery section's own event
 * feed for those instead. */
function buildTradeMarkers(entry: { openedAt: string; entryPrice: number; trailingActivatedAt: string | null; trailingActivatedPrice: number | null }, closedTrade?: SniperTrade): ChartOverlayMarker[] {
  // Colors match CandlestickChart's own internal COLORS palette
  // (bull/bear/entry) for visual consistency with the chart's own lines.
  const markers: ChartOverlayMarker[] = [{ timestamp: entry.openedAt, price: entry.entryPrice, label: "ENTRY", color: "#4fd8ff", shape: "up" }];
  if (entry.trailingActivatedAt !== null && entry.trailingActivatedPrice !== null) {
    markers.push({ timestamp: entry.trailingActivatedAt, price: entry.trailingActivatedPrice, label: "TRAIL ON", color: "#a78bfa", shape: "dot" });
  }
  if (closedTrade) {
    markers.push({ timestamp: closedTrade.closedAt, price: closedTrade.exitPrice, label: EXIT_LABEL[closedTrade.exitReason], color: closedTrade.pnlSol >= 0 ? "#3ce28a" : "#ff4d5e", shape: "down" });
  }
  return markers;
}

function timeAgo(iso: string): string {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

/** Professional Trading Terminal directive, Part VII — this trade's own
 * real, persisted event timeline (`GET /api/sniper/events?mint=...`),
 * polled at the same 5s cadence as the rest of this terminal. Never
 * manufactured — every row is a real event the backend actually recorded
 * (see SniperEvent's own docstring for the discarded-every-tick bug this
 * replaced). */
function useSniperEvents(mint: string): SniperEvent[] {
  const [events, setEvents] = useState<SniperEvent[]>([]);
  useEffect(() => {
    let cancelled = false;
    const load = () => {
      api
        .getSniperEvents({ mint, limit: 15 })
        .then((result) => {
          if (!cancelled) setEvents(result);
        })
        .catch(() => undefined);
    };
    load();
    const interval = setInterval(load, 5_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [mint]);
  return events;
}

/** CEO directive "Memecoin Sniper + Professional Trading Terminal, UI
 * Correction" — real trade state, never a fabricated backend enum. The
 * only lifecycle fields this codebase's own SniperPosition actually
 * carries are `status` (open|closed) and `trailingActive`; every other
 * suggested state in the directive's own list (PENDING/OPENING/
 * CLOSING/etc.) has no real backend signal to derive it from honestly
 * — a paper fill is instant, there is no order-book queueing stage —
 * so this reduces to the two real, disclosed states plus a P&L-derived
 * label (never invented, always computed from the position's own real
 * pnlSol). */
function deriveTradeState(p: SniperPosition): { label: string; tone: "green" | "red" | "cyan" | "amber" | "neutral" } {
  if (p.trailingActive) return { label: "TRAILING", tone: "cyan" };
  if (p.pnlSol > 0) return { label: "PROFITABLE", tone: "green" };
  if (p.pnlSol < 0) return { label: "LOSING", tone: "red" };
  return { label: "OPEN", tone: "neutral" };
}

/** One row in the multi-trade overview — every field here is real,
 * already-fetched SniperPosition data, never re-derived or guessed. */
function TradeRow({ position, selected, onSelect }: { position: SniperPosition; selected: boolean; onSelect: () => void }) {
  const state = deriveTradeState(position);
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`block w-full rounded-sm border p-2 text-left text-[9px] transition-colors ${selected ? "border-cmd-cyan bg-cmd-cyan/5" : "border-cmd-border/60 bg-cmd-bg/30 hover:border-cmd-cyan/40"}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-cmd-cyan">{position.symbol}</span>
        <StatusPill tone={state.tone}>{state.label}</StatusPill>
        <span className={`ml-auto tabular-nums ${position.pnlSol >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{fmtSol(position.pnlSol)}</span>
      </div>
      <div className="mt-1 flex flex-wrap gap-x-3 text-cmd-textDim">
        <span>Entry ${position.entryPrice.toPrecision(3)}</span>
        <span>SL ${(position.trailingActive ? (position.trailingStopPrice ?? position.stopPrice) : position.stopPrice).toPrecision(3)}</span>
        <span>TP ${position.targetPrice.toPrecision(3)}</span>
        {position.rMultiple !== null && <span className={position.rMultiple >= 0 ? "text-cmd-green" : "text-cmd-red"}>{position.rMultiple >= 0 ? "+" : ""}{position.rMultiple.toFixed(2)}R</span>}
      </div>
    </button>
  );
}

/** The focused-trade detail card — answers, from real persisted state
 * only: what trade is this, why did we enter, where's the stop/target,
 * where's price now, how much are we making/losing, what state is it
 * in. `matchingCandidate` (by mint, if the candidate is still in the
 * recently-fetched window) supplies the real entry-evidence breakdown;
 * when it's rolled off, this honestly falls back to just the numeric
 * `entryScore` already stored on the position itself, never a
 * fabricated re-derivation. */
function TradeDetail({ position, matchingCandidate, onClose }: { position: SniperPosition; matchingCandidate: SniperCandidate | undefined; onClose: () => void }) {
  const state = deriveTradeState(position);
  const overlays: ChartOverlays = {
    entry: position.entryPrice,
    currentPrice: position.currentPrice,
    stopPrice: position.trailingActive ? (position.trailingStopPrice ?? position.stopPrice) : position.stopPrice,
    stopLabel: position.trailingActive ? "TRAILING SL" : "SL",
    targetPrice: position.targetPrice,
    markers: buildTradeMarkers(position),
  };
  const candles = useCandles(position.symbol, "1m", 120);
  const events = useSniperEvents(position.mint);

  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-cmdmono text-lg text-cmd-cyan">{position.symbol}</span>
          <StatusPill tone={state.tone}>{state.label}</StatusPill>
          <span className="text-[9px] text-cmd-textDim">Engine: Memecoin Sniper — Liquidity/Momentum Discovery (paper-only, simulated)</span>
        </div>
        <button type="button" onClick={onClose} className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] uppercase text-cmd-textDim hover:text-cmd-text">
          Close focus
        </button>
      </div>

      <CandlestickChart candles={candles.candles} loading={candles.loading} error={candles.error} dataStatus={candles.candles[0]?.dataStatus ?? null} overlays={overlays} height={260} />

      <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[9px] sm:grid-cols-4">
        <DataRow label="Entry" value={`$${position.entryPrice.toPrecision(4)}`} />
        <DataRow label="Current" value={`$${position.currentPrice.toPrecision(4)}`} />
        <DataRow label="P&L" value={fmtSol(position.pnlSol)} valueClassName={position.pnlSol >= 0 ? "text-cmd-green" : "text-cmd-red"} />
        <DataRow label="P&L %" value={fmtPct(position.pnlPct)} valueClassName={position.pnlPct >= 0 ? "text-cmd-green" : "text-cmd-red"} />
        <DataRow label="Stop" value={`$${(position.trailingActive ? (position.trailingStopPrice ?? position.stopPrice) : position.stopPrice).toPrecision(4)}`} valueClassName="text-cmd-red" />
        <DataRow label="Target" value={`$${position.targetPrice.toPrecision(4)}`} valueClassName="text-cmd-green" />
        <DataRow label="R multiple" value={position.rMultiple !== null ? `${position.rMultiple >= 0 ? "+" : ""}${position.rMultiple.toFixed(2)}R` : "—"} />
        <DataRow label="Size" value={`${position.sizeSol.toFixed(3)} SOL`} />
        <DataRow label="Risk (SOL)" value={`${position.riskSol.toFixed(4)} SOL`} valueClassName="text-cmd-amber" />
        <DataRow label="MFE / MAE" value={`+${position.maxFavorableExcursionPct.toFixed(1)}% / ${position.maxAdverseExcursionPct.toFixed(1)}%`} />
        <DataRow label="Hold time" value={`${Math.round(position.holdTimeSeconds)}s`} />
        <DataRow label="Opened" value={new Date(position.openedAt).toLocaleTimeString()} />
        <DataRow label="Data" value="SIMULATED" valueClassName="text-cmd-amber" />
      </div>

      <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 border-t border-cmd-border/50 pt-2 text-[9px] sm:grid-cols-4">
        <DataRow label="Strategy" value={position.strategyName} />
        <DataRow
          label="Version"
          value={position.strategyVersionStatus === "versioned" ? (position.strategyVersionId ?? "—") : "Not versioned"}
          valueClassName={position.strategyVersionStatus === "versioned" ? undefined : "text-cmd-textDim"}
        />
      </div>

      <div className="mt-2 border-t border-cmd-border/50 pt-2">
        <TerminalLabel>Entry Evidence — why this trade was taken</TerminalLabel>
        {matchingCandidate ? (
          <div className="space-y-1 text-[9px]">
            {matchingCandidate.scoreComponents.map((comp) => (
              <DataRow key={comp.name} label={`${comp.name.replace(/_/g, " ")} (${comp.weightPct}%)`} value={comp.normalizedScore.toFixed(0)} />
            ))}
            <div className="mt-1 text-cmd-textDim">{matchingCandidate.decisionReason}</div>
          </div>
        ) : (
          <div className="text-[9px] text-cmd-textDim">
            Entry score {position.entryScore ?? "—"}. The full evidence breakdown for this specific entry has rolled off the recent-candidates window — only the numeric score survives on the position itself
            (not fabricated to fill the gap).
          </div>
        )}
      </div>

      <div className="mt-2 border-t border-cmd-border/50 pt-2">
        <TerminalLabel>Trade Event Timeline — this token's own real events</TerminalLabel>
        {events.length === 0 ? (
          <div className="text-[9px] text-cmd-textDim">No events recorded for this token yet.</div>
        ) : (
          <div className="max-h-40 space-y-1 overflow-y-auto text-[9px]">
            {events.map((e) => (
              <div key={e.id} className="border-b border-cmd-border/30 pb-1 text-cmd-textDim last:border-0">
                <span className="text-cmd-cyan">{timeAgo(e.timestamp)}</span> <span className={`font-semibold ${EVENT_TONE[e.type]}`}>{e.type.toUpperCase().replace(/_/g, " ")}</span> — {e.detail}
              </div>
            ))}
          </div>
        )}
      </div>
    </Glass>
  );
}

/** One row in the closed-trades list — mirrors TradeRow's shape, real
 * final values only (no live current price to show — the trade is
 * over). */
function ClosedTradeRow({ trade, selected, onSelect }: { trade: SniperTrade; selected: boolean; onSelect: () => void }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`block w-full rounded-sm border p-2 text-left text-[9px] transition-colors ${selected ? "border-cmd-cyan bg-cmd-cyan/5" : "border-cmd-border/60 bg-cmd-bg/30 hover:border-cmd-cyan/40"}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-cmd-cyan">{trade.symbol}</span>
        <StatusPill tone={trade.pnlSol >= 0 ? "green" : "red"}>{EXIT_LABEL[trade.exitReason]}</StatusPill>
        <span className={`ml-auto tabular-nums ${trade.pnlSol >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{fmtSol(trade.pnlSol)}</span>
      </div>
      <div className="mt-1 flex flex-wrap gap-x-3 text-cmd-textDim">
        <span>Entry ${trade.entryPrice.toPrecision(3)}</span>
        <span>Exit ${trade.exitPrice.toPrecision(3)}</span>
        <span className={trade.rMultiple >= 0 ? "text-cmd-green" : "text-cmd-red"}>{trade.rMultiple >= 0 ? "+" : ""}{trade.rMultiple.toFixed(2)}R</span>
      </div>
    </button>
  );
}

/** The closed-trade detail card — same real chart + marker treatment as
 * TradeDetail, but for a finished trade: shows the full ENTRY→EXIT
 * story (including the real STOP/TP/TRAIL STOP/MANUAL EXIT marker at
 * this trade's own real closedAt/exitPrice), never a live-updating
 * current price (there isn't one — the position closed). */
function ClosedTradeDetail({ trade, matchingCandidate, onClose }: { trade: SniperTrade; matchingCandidate: SniperCandidate | undefined; onClose: () => void }) {
  const overlays: ChartOverlays = {
    entry: trade.entryPrice,
    currentPrice: trade.exitPrice,
    stopPrice: trade.stopPrice ?? undefined,
    targetPrice: trade.targetPrice ?? undefined,
    markers: buildTradeMarkers(trade, trade),
  };
  const candles = useCandles(trade.symbol, "1m", 120);
  const events = useSniperEvents(trade.mint);

  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-cmdmono text-lg text-cmd-cyan">{trade.symbol}</span>
          <StatusPill tone={trade.pnlSol >= 0 ? "green" : "red"}>CLOSED — {EXIT_LABEL[trade.exitReason]}</StatusPill>
          <span className="text-[9px] text-cmd-textDim">Engine: Memecoin Sniper — Liquidity/Momentum Discovery (paper-only, simulated)</span>
        </div>
        <button type="button" onClick={onClose} className="rounded-sm border border-cmd-border px-2 py-1 text-[9px] uppercase text-cmd-textDim hover:text-cmd-text">
          Close focus
        </button>
      </div>

      <CandlestickChart candles={candles.candles} loading={candles.loading} error={candles.error} dataStatus={candles.candles[0]?.dataStatus ?? null} overlays={overlays} height={260} />

      <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[9px] sm:grid-cols-4">
        <DataRow label="Entry" value={`$${trade.entryPrice.toPrecision(4)}`} />
        <DataRow label="Exit" value={`$${trade.exitPrice.toPrecision(4)}`} />
        <DataRow label="P&L" value={fmtSol(trade.pnlSol)} valueClassName={trade.pnlSol >= 0 ? "text-cmd-green" : "text-cmd-red"} />
        <DataRow label="R multiple" value={`${trade.rMultiple >= 0 ? "+" : ""}${trade.rMultiple.toFixed(2)}R`} valueClassName={trade.rMultiple >= 0 ? "text-cmd-green" : "text-cmd-red"} />
        <DataRow label="Stop" value={trade.stopPrice !== null ? `$${trade.stopPrice.toPrecision(4)}` : "N/A (pre-dates this field)"} valueClassName="text-cmd-red" />
        <DataRow label="Target" value={trade.targetPrice !== null ? `$${trade.targetPrice.toPrecision(4)}` : "N/A (pre-dates this field)"} valueClassName="text-cmd-green" />
        <DataRow label="Exit reason" value={trade.exitReason.replace(/_/g, " ")} />
        <DataRow label="Size" value={`${trade.sizeSol.toFixed(3)} SOL`} />
        <DataRow label="Risk (SOL)" value={`${trade.riskSol.toFixed(4)} SOL`} valueClassName="text-cmd-amber" />
        <DataRow label="MFE / MAE" value={`+${trade.maxFavorableExcursionPct.toFixed(1)}% / ${trade.maxAdverseExcursionPct.toFixed(1)}%`} />
        <DataRow label="Hold time" value={`${Math.round(trade.holdTimeSeconds)}s`} />
        <DataRow label="Closed" value={new Date(trade.closedAt).toLocaleTimeString()} />
      </div>

      <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 border-t border-cmd-border/50 pt-2 text-[9px] sm:grid-cols-4">
        <DataRow label="Strategy" value={trade.strategyName} />
        <DataRow
          label="Version"
          value={trade.strategyVersionStatus === "versioned" ? (trade.strategyVersionId ?? "—") : "Not versioned"}
          valueClassName={trade.strategyVersionStatus === "versioned" ? undefined : "text-cmd-textDim"}
        />
      </div>

      <div className="mt-2 border-t border-cmd-border/50 pt-2">
        <TerminalLabel>Entry Evidence — why this trade was taken</TerminalLabel>
        {matchingCandidate ? (
          <div className="space-y-1 text-[9px]">
            {matchingCandidate.scoreComponents.map((comp) => (
              <DataRow key={comp.name} label={`${comp.name.replace(/_/g, " ")} (${comp.weightPct}%)`} value={comp.normalizedScore.toFixed(0)} />
            ))}
            <div className="mt-1 text-cmd-textDim">{matchingCandidate.decisionReason}</div>
          </div>
        ) : (
          <div className="text-[9px] text-cmd-textDim">
            Entry score {trade.entryScore ?? "—"}. The full evidence breakdown for this specific entry has rolled off the recent-candidates window.
          </div>
        )}
        {trade.failureCodes.length > 0 && <div className="mt-1 text-cmd-red">Failure codes: {trade.failureCodes.join(", ")}</div>}
        <div className="mt-1 text-cmd-textDim">{trade.thesis}</div>
      </div>

      <div className="mt-2 border-t border-cmd-border/50 pt-2">
        <TerminalLabel>Trade Event Timeline — this token's own real events</TerminalLabel>
        {events.length === 0 ? (
          <div className="text-[9px] text-cmd-textDim">No events recorded for this token yet.</div>
        ) : (
          <div className="max-h-40 space-y-1 overflow-y-auto text-[9px]">
            {events.map((e) => (
              <div key={e.id} className="border-b border-cmd-border/30 pb-1 text-cmd-textDim last:border-0">
                <span className="text-cmd-cyan">{timeAgo(e.timestamp)}</span> <span className={`font-semibold ${EVENT_TONE[e.type]}`}>{e.type.toUpperCase().replace(/_/g, " ")}</span> — {e.detail}
              </div>
            ))}
          </div>
        )}
      </div>
    </Glass>
  );
}

/** The Trading Terminal — multi-trade overview (left) + focused chart/
 * detail (right) for the selected position. Replaces the previous
 * plain-text open-positions table with a real operational visualization:
 * every active trade's entry/SL/TP/current price/P&L is drawn on an
 * actual candlestick chart, not just listed as numbers. Selecting a
 * trade never mutates it — pure UI focus, same convention as this
 * codebase's own ActiveTradesPanel/MarketChartPanel pairing in the main
 * TradeTown app. */
type Focus = { kind: "open"; id: string } | { kind: "closed"; id: string };

/** "Terminal 2.1" directive, Phase 2 — closed trades (up to the 5 most
 * recent) are now also focusable, not just open positions, so the real
 * EXIT/STOP/TP/TRAIL markers this directive asks for have somewhere to
 * actually render — a closed trade's own chart. `trades` should be the
 * already-fetched recent SniperTrade[] (newest first). */
export function SniperTerminal({ positions, candidates, trades }: { positions: SniperPosition[]; candidates: SniperCandidate[]; trades: SniperTrade[] }) {
  const openPositions = useMemo(() => positions.filter((p) => p.status === "open"), [positions]);
  const recentClosed = useMemo(() => trades.slice(0, 5), [trades]);
  const [focus, setFocus] = useState<Focus | null>(null);

  useEffect(() => {
    const stillValid = focus !== null && (focus.kind === "open" ? openPositions.some((p) => p.id === focus.id) : recentClosed.some((t) => t.id === focus.id));
    if (focus !== null && !stillValid) {
      setFocus(null);
    }
    if (focus === null && openPositions.length > 0) {
      setFocus({ kind: "open", id: openPositions[0]?.id ?? "" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openPositions, recentClosed]);

  const selectedPosition = focus?.kind === "open" ? (openPositions.find((p) => p.id === focus.id) ?? null) : null;
  const selectedTrade = focus?.kind === "closed" ? (recentClosed.find((t) => t.id === focus.id) ?? null) : null;
  const matchingCandidate = candidates.find((c) => c.mint === (selectedPosition?.mint ?? selectedTrade?.mint));

  const totalExposureSol = openPositions.reduce((s, p) => s + p.sizeSol, 0);
  const totalUnrealizedSol = openPositions.reduce((s, p) => s + p.pnlSol, 0);
  const totalOpenRiskSol = openPositions.reduce((s, p) => s + p.riskSol, 0);

  return (
    <div className="space-y-3">
      <Glass className="grid grid-cols-2 gap-2 p-3 text-[9px] sm:grid-cols-5">
        <DataRow label="Active trades" value={openPositions.length} />
        <DataRow label="Total exposure" value={`${totalExposureSol.toFixed(3)} SOL`} />
        <DataRow label="Total open risk" value={`${totalOpenRiskSol.toFixed(4)} SOL`} valueClassName="text-cmd-amber" />
        <DataRow label="Unrealized P&L" value={fmtSol(totalUnrealizedSol)} valueClassName={totalUnrealizedSol >= 0 ? "text-cmd-green" : "text-cmd-red"} />
        <DataRow label="Trailing" value={openPositions.filter((p) => p.trailingActive).length} />
      </Glass>
      {openPositions.length > 1 && (
        <p className="px-1 text-[8px] text-cmd-textDim">
          Correlated exposure across these {openPositions.length} positions: NOT AVAILABLE — Sniper positions aren&apos;t part of the main portfolio&apos;s correlation engine
          (app/portfolio_intelligence.py::count_correlated_positions), and this pass did not build a second one.
        </p>
      )}

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-1">
          <div className="space-y-1.5">
            <TerminalLabel>Active Trades ({openPositions.length})</TerminalLabel>
            {openPositions.length === 0 ? (
              <Glass className="p-2">
                <EmptyState>No open paper positions right now.</EmptyState>
              </Glass>
            ) : (
              openPositions.map((p) => <TradeRow key={p.id} position={p} selected={focus?.kind === "open" && focus.id === p.id} onSelect={() => setFocus({ kind: "open", id: p.id })} />)
            )}
          </div>
          <div className="space-y-1.5">
            <TerminalLabel>Recently Closed ({recentClosed.length})</TerminalLabel>
            {recentClosed.length === 0 ? (
              <Glass className="p-2">
                <EmptyState>No trades closed yet.</EmptyState>
              </Glass>
            ) : (
              recentClosed.map((t) => <ClosedTradeRow key={t.id} trade={t} selected={focus?.kind === "closed" && focus.id === t.id} onSelect={() => setFocus({ kind: "closed", id: t.id })} />)
            )}
          </div>
        </div>
        <div className="lg:col-span-2">
          {selectedPosition ? (
            <TradeDetail position={selectedPosition} matchingCandidate={matchingCandidate} onClose={() => setFocus(null)} />
          ) : selectedTrade ? (
            <ClosedTradeDetail trade={selectedTrade} matchingCandidate={matchingCandidate} onClose={() => setFocus(null)} />
          ) : (
            <Glass className="p-3">
              <EmptyState>Select a trade to focus its chart.</EmptyState>
            </Glass>
          )}
        </div>
      </div>
    </div>
  );
}
