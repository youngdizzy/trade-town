import { useEffect, useMemo, useState } from "react";
import { CandlestickChart, type ChartOverlays } from "@/ui/components/CommandCenter/CandlestickChart";
import { useCandles } from "@/ui/components/CommandCenter/lib/useCandles";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "@/ui/components/CommandCenter/ui";
import type { SniperCandidate, SniperPosition } from "@/types";

function fmtSol(v: number, digits = 3): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)} SOL`;
}

function fmtPct(v: number, digits = 1): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}%`;
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
  };
  const candles = useCandles(position.symbol, "1m", 120);

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
        <DataRow label="MFE / MAE" value={`+${position.maxFavorableExcursionPct.toFixed(1)}% / ${position.maxAdverseExcursionPct.toFixed(1)}%`} />
        <DataRow label="Hold time" value={`${Math.round(position.holdTimeSeconds)}s`} />
        <DataRow label="Opened" value={new Date(position.openedAt).toLocaleTimeString()} />
        <DataRow label="Data" value="SIMULATED" valueClassName="text-cmd-amber" />
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
export function SniperTerminal({ positions, candidates }: { positions: SniperPosition[]; candidates: SniperCandidate[] }) {
  const openPositions = useMemo(() => positions.filter((p) => p.status === "open"), [positions]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (selectedId !== null && !openPositions.some((p) => p.id === selectedId)) {
      setSelectedId(null);
    }
    if (selectedId === null && openPositions.length > 0) {
      setSelectedId(openPositions[0]?.id ?? null);
    }
  }, [openPositions, selectedId]);

  const selected = openPositions.find((p) => p.id === selectedId) ?? null;
  const matchingCandidate = selected ? candidates.find((c) => c.mint === selected.mint) : undefined;

  const totalExposureSol = openPositions.reduce((s, p) => s + p.sizeSol, 0);
  const totalUnrealizedSol = openPositions.reduce((s, p) => s + p.pnlSol, 0);

  return (
    <div className="space-y-3">
      <Glass className="grid grid-cols-2 gap-2 p-3 text-[9px] sm:grid-cols-4">
        <DataRow label="Active trades" value={openPositions.length} />
        <DataRow label="Total exposure" value={`${totalExposureSol.toFixed(3)} SOL`} />
        <DataRow label="Unrealized P&L" value={fmtSol(totalUnrealizedSol)} valueClassName={totalUnrealizedSol >= 0 ? "text-cmd-green" : "text-cmd-red"} />
        <DataRow label="Trailing" value={openPositions.filter((p) => p.trailingActive).length} />
      </Glass>

      {openPositions.length === 0 ? (
        <Glass className="p-3">
          <EmptyState>No open paper positions right now.</EmptyState>
        </Glass>
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          <div className="space-y-1.5 lg:col-span-1">
            <TerminalLabel>Active Trades ({openPositions.length})</TerminalLabel>
            {openPositions.map((p) => (
              <TradeRow key={p.id} position={p} selected={p.id === selectedId} onSelect={() => setSelectedId(p.id)} />
            ))}
          </div>
          <div className="lg:col-span-2">
            {selected ? (
              <TradeDetail position={selected} matchingCandidate={matchingCandidate} onClose={() => setSelectedId(null)} />
            ) : (
              <Glass className="p-3">
                <EmptyState>Select a trade to focus its chart.</EmptyState>
              </Glass>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
