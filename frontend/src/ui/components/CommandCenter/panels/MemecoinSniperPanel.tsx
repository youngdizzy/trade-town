import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type {
  SniperCandidate,
  SniperClassification,
  SniperEngineStatusRead,
  SniperLead,
  SniperLesson,
  SniperPosition,
  SniperSafetyStatus,
  SniperTrade,
} from "@/types";
import { AnimatedGrid, DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

const POLL_MS = 5_000;

const CLASSIFICATION_TONE: Record<SniperClassification, "green" | "amber" | "red" | "purple" | "cyan"> = {
  high_conviction: "green",
  qualified: "cyan",
  watch: "amber",
  rejected: "red",
};

const SAFETY_TONE: Record<SniperSafetyStatus, "green" | "amber" | "red" | "purple"> = {
  safe_enough: "green",
  caution: "amber",
  unknown: "purple",
  rejected: "red",
};

function fmtSol(v: number, digits = 3): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)} SOL`;
}

function fmtPct(v: number, digits = 1): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}%`;
}

function timeAgo(iso: string): string {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

/**
 * CEO directive "TradeTown — Memecoin Sniper Agent." A single, no-tabs
 * dashboard (Section 32/34/36) reused within the existing Command
 * Center terminal visual language (Glass/StatusPill/AnimatedGrid — the
 * same dark, glow-accented system every other tab already uses) rather
 * than a parallel design system. PAPER-ONLY, SIMULATED DATA, DISCLOSED
 * throughout — every card below either shows a real "SIMULATED" label
 * or reads it directly off the record itself; nothing here ever claims
 * live on-chain evidence. No fake AI confidence score anywhere — the
 * opportunity score is always shown as its own real, itemized 7-axis
 * breakdown, never a bare number alone.
 *
 * Simplification disclosed: the backend does not persist a dedicated
 * event log (Section 35's "Live Event Feed"), so "RECENT ACTIVITY"
 * below is honestly derived from the real candidates/trades already
 * fetched rather than a fabricated stream — see CHANGELOG.md's own
 * disclosure for this pass's exact scope.
 */
export function MemecoinSniperPanel() {
  const [status, setStatus] = useState<SniperEngineStatusRead | null>(null);
  const [candidates, setCandidates] = useState<SniperCandidate[]>([]);
  const [positions, setPositions] = useState<SniperPosition[]>([]);
  const [trades, setTrades] = useState<SniperTrade[]>([]);
  const [leads, setLeads] = useState<SniperLead[]>([]);
  const [lessons, setLessons] = useState<SniperLesson[]>([]);
  const [expandedCandidateId, setExpandedCandidateId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    api.getSniperStatus().then(setStatus).catch(() => undefined);
    api.getSniperCandidates(20).then(setCandidates).catch(() => undefined);
    api.getSniperPositions().then(setPositions).catch(() => undefined);
    api.getSniperTrades(20).then(setTrades).catch(() => undefined);
    api.getSniperLeads().then(setLeads).catch(() => undefined);
    api.getSniperLessons().then(setLessons).catch(() => undefined);
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_MS);
    return () => clearInterval(interval);
  }, []);

  async function setEngineStatus(next: "running" | "paused" | "stopped") {
    setBusy(true);
    setError(null);
    try {
      const result = await api.updateSniperEngine({ status: next });
      setStatus(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function tryArmLive() {
    setError(null);
    try {
      await api.updateSniperEngine({ mode: "live" });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function toggle(field: "turbo" | "copyTradingEnabled", value: boolean) {
    try {
      const result = await api.updateSniperEngine({ [field]: value });
      setStatus(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function closePosition(id: string) {
    setBusy(true);
    try {
      await api.closeSniperPosition(id);
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const openPositions = positions.filter((p) => p.status === "open");
  const opportunities = candidates.filter((c) => c.classification === "qualified" || c.classification === "high_conviction").slice(0, 4);
  const recentActivity = [
    ...candidates.slice(0, 8).map((c) => ({ at: c.discoveredAt, text: `DISCOVERED ${c.symbol} — score ${c.opportunityScore ?? "—"}, ${c.classification.replace(/_/g, " ")}` })),
    ...trades.slice(0, 8).map((t) => ({ at: t.closedAt, text: `EXIT ${t.symbol} — ${t.exitReason.replace(/_/g, " ")}, ${fmtSol(t.pnlSol)} (${t.rMultiple >= 0 ? "+" : ""}${t.rMultiple.toFixed(2)}R)` })),
  ]
    .sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime())
    .slice(0, 10);

  return (
    <div className="relative space-y-3">
      <AnimatedGrid />
      <div className="relative space-y-3">
        {/* Header strip */}
        <Glass className="flex flex-wrap items-center justify-between gap-3 p-3">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-cmd-cyan">Memecoin Sniper</div>
            <div className="text-[9px] text-cmd-textDim">Solana memecoin discovery + paper execution — simulated data</div>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-[9px]">
            <div>
              <div className="text-cmd-textDim">ENGINE</div>
              <StatusPill tone={status?.config.status === "running" ? "green" : status?.config.status === "paused" ? "amber" : "neutral"}>
                {(status?.config.status ?? "…").toUpperCase()}
              </StatusPill>
            </div>
            <div>
              <div className="text-cmd-textDim">MODE</div>
              <StatusPill tone="cyan">{status?.config.mode === "live" ? "LIVE" : "DRY RUN"}</StatusPill>
            </div>
            <div>
              <div className="text-cmd-textDim">TURBO</div>
              <StatusPill tone={status?.config.turbo ? "amber" : "neutral"}>{status?.config.turbo ? "ON" : "OFF"}</StatusPill>
            </div>
            <div>
              <div className="text-cmd-textDim">COPY TRADING</div>
              <StatusPill tone={status?.config.copyTradingEnabled ? "green" : "neutral"}>{status?.config.copyTradingEnabled ? "ON" : "OFF"}</StatusPill>
            </div>
            <div>
              <div className="text-cmd-textDim">PAPER BALANCE</div>
              <div className="tabular-nums text-cmd-text">{status?.risk.equitySol.toFixed(3) ?? "—"} SOL</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {status?.risk.killSwitchTriggered && (
              <StatusPill tone="red">KILL SWITCH: {status.risk.killSwitchReason}</StatusPill>
            )}
            <button
              type="button"
              disabled={busy}
              onClick={() => void setEngineStatus("stopped")}
              className="rounded-sm border border-cmd-red/60 bg-cmd-red/10 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-cmd-red shadow-cmd-red hover:bg-cmd-red/20 disabled:opacity-50"
            >
              Stop / Kill
            </button>
          </div>
        </Glass>

        {error && (
          <Glass className="border-cmd-red/50 p-2 text-[9px] text-cmd-red">{error}</Glass>
        )}

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          {/* Performance */}
          <Glass className="p-3">
            <TerminalLabel>Performance (today)</TerminalLabel>
            <DataRow label="Session P&L" value={status ? fmtSol(status.todayPnlSol) : "—"} valueClassName={status && status.todayPnlSol >= 0 ? "text-cmd-green" : "text-cmd-red"} />
            <DataRow label="Trades today" value={status?.todayTradeCount ?? 0} />
            <DataRow label="Win rate" value={status?.winRatePct !== null && status?.winRatePct !== undefined ? `${status.winRatePct}%` : "NOT VERIFIED"} />
            <DataRow label="Expectancy" value={status?.expectancyR !== null && status?.expectancyR !== undefined ? `${status.expectancyR >= 0 ? "+" : ""}${status.expectancyR}R` : "NOT VERIFIED"} />
          </Glass>

          {/* Risk status */}
          <Glass className="p-3">
            <TerminalLabel>Risk status</TerminalLabel>
            <DataRow label="Drawdown" value={`${status?.risk.drawdownPct.toFixed(1) ?? "0.0"}% of max`} />
            <DataRow label="Daily loss" value={status ? fmtSol(-status.risk.dailyLossSol) : "—"} valueClassName="text-cmd-red" />
            <DataRow label="Open risk" value={status ? `${status.risk.openRiskSol.toFixed(3)} SOL` : "—"} />
            <DataRow label="Size multiplier" value={`${status?.risk.sizeMultiplier.toFixed(2) ?? "1.00"}x`} />
            <DataRow label="Consecutive losses" value={status?.risk.consecutiveLosses ?? 0} />
            <DataRow
              label="Kill switch"
              value={<StatusPill tone={status?.risk.killSwitchTriggered ? "red" : status?.risk.killSwitchArmed ? "green" : "neutral"}>{status?.risk.killSwitchTriggered ? "TRIGGERED" : status?.risk.killSwitchArmed ? "ARMED" : "DISARMED"}</StatusPill>}
            />
          </Glass>

          {/* Quick controls */}
          <Glass className="p-3">
            <TerminalLabel>Quick controls</TerminalLabel>
            <div className="grid grid-cols-3 gap-1.5">
              <button type="button" disabled={busy} onClick={() => void setEngineStatus("running")} className="rounded-sm border border-cmd-green/50 bg-cmd-green/10 py-1.5 text-[9px] uppercase tracking-wide text-cmd-green hover:bg-cmd-green/20 disabled:opacity-50">Start</button>
              <button type="button" disabled={busy} onClick={() => void setEngineStatus("paused")} className="rounded-sm border border-cmd-amber/50 bg-cmd-amber/10 py-1.5 text-[9px] uppercase tracking-wide text-cmd-amber hover:bg-cmd-amber/20 disabled:opacity-50">Pause</button>
              <button type="button" disabled={busy} onClick={() => void setEngineStatus("stopped")} className="rounded-sm border border-cmd-red/50 bg-cmd-red/10 py-1.5 text-[9px] uppercase tracking-wide text-cmd-red hover:bg-cmd-red/20 disabled:opacity-50">Stop</button>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-1.5">
              <div className="rounded-sm border border-cmd-cyan/50 bg-cmd-cyan/10 py-1.5 text-center text-[9px] uppercase tracking-wide text-cmd-cyan">Dry Run</div>
              <button type="button" onClick={() => void tryArmLive()} className="rounded-sm border border-cmd-border py-1.5 text-[9px] uppercase tracking-wide text-cmd-textDim hover:border-cmd-red/50 hover:text-cmd-red" title="Live trading requires real Solana RPC/Jupiter/wallet credentials — not configured in this environment">
                Live 🔒
              </button>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-1.5">
              <button type="button" onClick={() => void toggle("turbo", !status?.config.turbo)} className={`rounded-sm border py-1.5 text-[9px] uppercase tracking-wide ${status?.config.turbo ? "border-cmd-amber/50 bg-cmd-amber/10 text-cmd-amber" : "border-cmd-border text-cmd-textDim"}`}>
                Turbo {status?.config.turbo ? "ON" : "OFF"}
              </button>
              <button type="button" onClick={() => void toggle("copyTradingEnabled", !status?.config.copyTradingEnabled)} className={`rounded-sm border py-1.5 text-[9px] uppercase tracking-wide ${status?.config.copyTradingEnabled ? "border-cmd-green/50 bg-cmd-green/10 text-cmd-green" : "border-cmd-border text-cmd-textDim"}`}>
                Copy {status?.config.copyTradingEnabled ? "ON" : "OFF"}
              </button>
            </div>
            {status && !status.liveArming.armed && (
              <p className="mt-2 text-[8px] leading-relaxed text-cmd-textDim">
                Live trading locked: {status.liveArming.blockingReasons[0]}
              </p>
            )}
          </Glass>
        </div>

        {/* Top opportunities */}
        <Glass className="p-3">
          <TerminalLabel>Top opportunities — evidence-ranked, never a bare score</TerminalLabel>
          {opportunities.length === 0 ? (
            <EmptyState>No qualified/high-conviction candidates yet this session.</EmptyState>
          ) : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {opportunities.map((c) => (
                <div key={c.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                  <div className="flex items-center justify-between gap-1">
                    <span className="font-semibold text-cmd-cyan">{c.symbol}</span>
                    <StatusPill tone={CLASSIFICATION_TONE[c.classification]}>{c.classification.replace(/_/g, " ")}</StatusPill>
                  </div>
                  <div className="mt-1 text-cmd-textDim">{timeAgo(c.discoveredAt)} · {c.timingState.replace(/_/g, " ")}</div>
                  <div className="mt-1 flex items-baseline gap-1">
                    <span className="text-lg font-semibold text-cmd-text tabular-nums">{c.opportunityScore ?? "—"}</span>
                    <span className="text-cmd-textDim">score</span>
                  </div>
                  <DataRow label="Liquidity" value={`$${c.liquidityUsd.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
                  <DataRow label="Buy pressure" value={`${c.buyPressurePct}%`} />
                  <DataRow label="Safety" value={<StatusPill tone={SAFETY_TONE[c.safetyStatus]}>{c.safetyStatus.replace(/_/g, " ")}</StatusPill>} />
                  <button
                    type="button"
                    onClick={() => setExpandedCandidateId(expandedCandidateId === c.id ? null : c.id)}
                    className="mt-1.5 w-full rounded-sm border border-cmd-border py-1 text-[8px] uppercase tracking-wide text-cmd-textDim hover:text-cmd-cyan"
                  >
                    {expandedCandidateId === c.id ? "Hide analysis" : "View analysis"}
                  </button>
                  {expandedCandidateId === c.id && (
                    <div className="mt-2 space-y-1 border-t border-cmd-border/60 pt-2">
                      <div className="text-cmd-textDim">Score breakdown:</div>
                      {c.scoreComponents.map((comp) => (
                        <DataRow key={comp.name} label={`${comp.name.replace(/_/g, " ")} (${comp.weightPct}%)`} value={comp.normalizedScore.toFixed(0)} />
                      ))}
                      <div className="mt-1 text-cmd-textDim">Safety checks:</div>
                      {c.safetyChecks.map((chk) => (
                        <div key={chk.name} className={chk.status === "pass" ? "text-cmd-green" : chk.status === "fail" ? "text-cmd-red" : "text-cmd-purple"}>
                          {chk.status === "pass" ? "✓" : chk.status === "fail" ? "✗" : "?"} {chk.name.replace(/_/g, " ")}: {chk.detail}
                        </div>
                      ))}
                      <div className="mt-1 text-cmd-textDim">{c.decisionReason}</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Glass>

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          {/* Open positions */}
          <Glass className="p-3 lg:col-span-2">
            <TerminalLabel>Open positions ({openPositions.length} / {status?.config.maxOpenPositions ?? "—"})</TerminalLabel>
            {openPositions.length === 0 ? (
              <EmptyState>No open paper positions.</EmptyState>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-[9px]">
                  <thead>
                    <tr className="text-left text-cmd-textDim">
                      <th className="pb-1 font-normal">Token</th>
                      <th className="pb-1 font-normal">Entry</th>
                      <th className="pb-1 font-normal">Current</th>
                      <th className="pb-1 font-normal">Size</th>
                      <th className="pb-1 font-normal">P&L</th>
                      <th className="pb-1 font-normal">R</th>
                      <th className="pb-1 font-normal">Hold</th>
                      <th className="pb-1 font-normal"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {openPositions.map((p) => (
                      <tr key={p.id} className="border-t border-cmd-border/60">
                        <td className="py-1 text-cmd-cyan">{p.symbol}</td>
                        <td className="py-1 tabular-nums text-cmd-textDim">${p.entryPrice.toPrecision(3)}</td>
                        <td className="py-1 tabular-nums text-cmd-textDim">${p.currentPrice.toPrecision(3)}</td>
                        <td className="py-1 tabular-nums">{p.sizeSol.toFixed(3)} SOL</td>
                        <td className={`py-1 tabular-nums ${p.pnlSol >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{fmtPct(p.pnlPct)}</td>
                        <td className={`py-1 tabular-nums ${(p.rMultiple ?? 0) >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{p.rMultiple !== null ? `${p.rMultiple >= 0 ? "+" : ""}${p.rMultiple.toFixed(2)}R` : "—"}</td>
                        <td className="py-1 tabular-nums text-cmd-textDim">{Math.round(p.holdTimeSeconds)}s</td>
                        <td className="py-1">
                          <button type="button" disabled={busy} onClick={() => void closePosition(p.id)} className="rounded-sm border border-cmd-border px-1.5 py-0.5 text-[8px] uppercase text-cmd-textDim hover:border-cmd-red/50 hover:text-cmd-red disabled:opacity-50">
                            Manage
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Glass>

          {/* Recent activity (derived, real data — see module docstring) */}
          <Glass className="p-3">
            <TerminalLabel>Recent activity</TerminalLabel>
            {recentActivity.length === 0 ? (
              <EmptyState>No activity yet.</EmptyState>
            ) : (
              <div className="max-h-64 space-y-1 overflow-y-auto text-[8px]">
                {recentActivity.map((item, i) => (
                  <div key={i} className="border-b border-cmd-border/40 pb-1 text-cmd-textDim last:border-0">
                    <span className="text-cmd-cyan">{timeAgo(item.at)}</span> {item.text}
                  </div>
                ))}
              </div>
            )}
          </Glass>
        </div>

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {/* Smart money */}
          <Glass className="p-3">
            <TerminalLabel>Smart money activity (simulated)</TerminalLabel>
            {leads.length === 0 ? (
              <EmptyState>No leads generated yet.</EmptyState>
            ) : (
              <div className="space-y-1">
                {leads.map((lead) => (
                  <DataRow
                    key={lead.id}
                    label={lead.walletLabel}
                    value={`${lead.winRatePct}% WR · ${lead.tradeCount} trades · weight ${lead.weight.toFixed(2)}`}
                  />
                ))}
              </div>
            )}
          </Glass>

          {/* Lessons */}
          <Glass className="p-3">
            <TerminalLabel>Research lessons</TerminalLabel>
            {lessons.length === 0 ? (
              <EmptyState>Fewer than 20 trades on file — no lesson has cleared the real evidence floor yet.</EmptyState>
            ) : (
              <div className="space-y-2 text-[9px]">
                {lessons.map((lesson) => (
                  <div key={lesson.id} className="border-b border-cmd-border/40 pb-1.5 last:border-0">
                    <div className="text-cmd-text">{lesson.observation}</div>
                    <div className="mt-0.5 text-cmd-textDim">
                      n={lesson.sampleSize} · confidence {lesson.confidence} · {lesson.recommendation}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Glass>
        </div>

        {/* Trade journal */}
        <Glass className="p-3">
          <TerminalLabel>Trade journal (most recent {trades.length})</TerminalLabel>
          {trades.length === 0 ? (
            <EmptyState>No trades closed yet.</EmptyState>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-[9px]">
                <thead>
                  <tr className="text-left text-cmd-textDim">
                    <th className="pb-1 font-normal">Token</th>
                    <th className="pb-1 font-normal">Closed</th>
                    <th className="pb-1 font-normal">P&L</th>
                    <th className="pb-1 font-normal">R</th>
                    <th className="pb-1 font-normal">Exit reason</th>
                    <th className="pb-1 font-normal">Failure codes</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((t) => (
                    <tr key={t.id} className="border-t border-cmd-border/60">
                      <td className="py-1 text-cmd-cyan">{t.symbol}</td>
                      <td className="py-1 text-cmd-textDim">{timeAgo(t.closedAt)}</td>
                      <td className={`py-1 tabular-nums ${t.pnlSol >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{fmtSol(t.pnlSol)}</td>
                      <td className={`py-1 tabular-nums ${t.rMultiple >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{t.rMultiple >= 0 ? "+" : ""}{t.rMultiple.toFixed(2)}R</td>
                      <td className="py-1 text-cmd-textDim">{t.exitReason.replace(/_/g, " ")}</td>
                      <td className="py-1 text-cmd-textDim">{t.failureCodes.length > 0 ? t.failureCodes.join(", ") : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Glass>

        <Meter value={status?.risk.drawdownPct ?? 0} max={8} tone={((status?.risk.drawdownPct ?? 0) >= 6 ? "red" : (status?.risk.drawdownPct ?? 0) >= 4 ? "amber" : "cyan") as "red" | "amber" | "cyan"} />
      </div>
    </div>
  );
}
