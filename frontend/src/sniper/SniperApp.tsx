import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { SniperAiReasoningResult, SniperCandidate, SniperClassification, SniperEngineStatusRead, SniperEquitySnapshot, SniperEvent, SniperLead, SniperLesson, SniperPnlHistoryPoint, SniperPosition, SniperSafetyStatus, SniperTrade, SniperWallet } from "@/types";
import { EquityCurveChart } from "@/ui/components/CommandCenter/panels/EquityCurveChart";
import { AnimatedGrid, DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "@/ui/components/CommandCenter/ui";
import { SniperTerminal } from "./SniperTerminal";

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

function fmtSol(v: number, digits = 3): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)} SOL`;
}

function timeAgo(iso: string): string {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

/**
 * CEO directive "TradeTown — Memecoin Sniper + Professional Trading
 * Terminal, UI Correction / Visualization Rebuild." Root component of
 * the Sniper's own DEDICATED application surface (served at `/sniper`,
 * a completely separate React root from the main TradeTown app — see
 * `src/main.tsx`'s own docstring for why). This is deliberately NOT a
 * Command Center tab: no Phaser canvas, no gameStore, no EventBus — the
 * only shared dependency with the main app is the plain REST client
 * (`@/net/api`) and this same terminal design-language's UI primitives
 * (`Glass`/`StatusPill`/`TerminalLabel`/etc.), reused because they're
 * genuinely the right visual language, not because this is secretly
 * still the same app.
 *
 * One flat command surface, not a tab maze — the directive's own
 * explicit instruction ("no tabs inside the Sniper"). PAPER-ONLY,
 * SIMULATED DATA, disclosed throughout exactly as the previous
 * (now-retired) MemecoinSniperPanel.tsx already established — every
 * card either shows a real "SIMULATED" label or reads it directly off
 * the record. No fake AI confidence anywhere — the opportunity score is
 * always its own real, itemized breakdown.
 *
 * "Recent Activity" reads the backend's own real, persisted event log
 * (`GET /api/sniper/events` — see SniperEvent's own docstring for the
 * real bug this pass found and fixed: these events used to be generated
 * every tick and then silently discarded, never actually kept anywhere).
 *
 * "Terminal 2.1" directive, Phase 5 — Wallet management now has a real,
 * persisted backend (add/remove/activate real METADATA — label, public
 * address, network). What still does NOT exist, and is stated as such
 * rather than faked: secure secret storage for a real signing key. No
 * field for one exists anywhere on `SniperWallet`, and adding a wallet
 * never arms live trading — `evaluate_live_arming()` still names the
 * other three real unmet prerequisites (RPC/Jupiter/validation).
 */
export function SniperApp() {
  const [status, setStatus] = useState<SniperEngineStatusRead | null>(null);
  const [candidates, setCandidates] = useState<SniperCandidate[]>([]);
  const [positions, setPositions] = useState<SniperPosition[]>([]);
  const [trades, setTrades] = useState<SniperTrade[]>([]);
  const [leads, setLeads] = useState<SniperLead[]>([]);
  const [lessons, setLessons] = useState<SniperLesson[]>([]);
  const [events, setEvents] = useState<SniperEvent[]>([]);
  const [wallets, setWallets] = useState<SniperWallet[]>([]);
  // "Terminal 2.2" directive — the real, full, oldest-first cumulative
  // realized-P&L history (never the 20-trade-capped `trades` list above,
  // which would misrepresent the true cumulative total).
  const [pnlHistory, setPnlHistory] = useState<SniperPnlHistoryPoint[]>([]);
  // "Equity Snapshot Telemetry 1.0" directive — real, periodic
  // mark-to-market readings, distinct from pnlHistory above (realized-
  // only). Never merged into one chart/line with it (Part XIX).
  const [equityHistory, setEquityHistory] = useState<SniperEquitySnapshot[]>([]);
  const [walletLabel, setWalletLabel] = useState("");
  const [walletAddress, setWalletAddress] = useState("");
  const [expandedCandidateId, setExpandedCandidateId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [walletError, setWalletError] = useState<string | null>(null);
  // CEO directive "TradeTown — Memecoin Sniper AI 1.0" — real, human-
  // triggered shadow reasoning, keyed by the candidate's own real
  // `mint` (this domain's own real join key; see
  // app/sniper_ai_context.py's own module docstring). Never polled
  // automatically — only ever populated by an explicit "Ask AI" click.
  const [aiResultsByMint, setAiResultsByMint] = useState<Record<string, SniperAiReasoningResult[]>>({});
  const [aiLoadingMint, setAiLoadingMint] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  const refresh = () => {
    api.getSniperStatus().then(setStatus).catch(() => undefined);
    api.getSniperCandidates(20).then(setCandidates).catch(() => undefined);
    api.getSniperPositions().then(setPositions).catch(() => undefined);
    api.getSniperTrades(20).then(setTrades).catch(() => undefined);
    api.getSniperLeads().then(setLeads).catch(() => undefined);
    api.getSniperLessons().then(setLessons).catch(() => undefined);
    api.getSniperEvents({ limit: 15 }).then(setEvents).catch(() => undefined);
    api.getSniperWallets().then(setWallets).catch(() => undefined);
    api.getSniperPnlHistory().then(setPnlHistory).catch(() => undefined);
    api.getSniperEquityHistory().then(setEquityHistory).catch(() => undefined);
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

  async function addWallet() {
    setWalletError(null);
    try {
      const wallet = await api.addSniperWallet({ label: walletLabel, publicAddress: walletAddress });
      setWallets((prev) => [...prev, wallet]);
      setWalletLabel("");
      setWalletAddress("");
      api.getSniperStatus().then(setStatus).catch(() => undefined);
    } catch (e) {
      setWalletError(e instanceof Error ? e.message : String(e));
    }
  }

  async function runAiAnalysis(candidate: SniperCandidate) {
    setAiLoadingMint(candidate.mint);
    setAiError(null);
    try {
      const result = await api.runSniperAiReasoning(candidate.id);
      setAiResultsByMint((prev) => ({ ...prev, [candidate.mint]: [...(prev[candidate.mint] ?? []), result] }));
    } catch (e) {
      setAiError(e instanceof Error ? e.message : String(e));
    } finally {
      setAiLoadingMint(null);
    }
  }

  async function removeWallet(walletId: string) {
    if (!window.confirm("Remove this wallet? This only deletes its saved label/address — it never touches any real funds (this environment has none).")) return;
    setWalletError(null);
    try {
      await api.removeSniperWallet(walletId);
      setWallets((prev) => prev.filter((w) => w.id !== walletId));
      api.getSniperStatus().then(setStatus).catch(() => undefined);
    } catch (e) {
      setWalletError(e instanceof Error ? e.message : String(e));
    }
  }

  async function activateWallet(walletId: string) {
    setWalletError(null);
    try {
      const result = await api.activateSniperWallet(walletId);
      setWallets(result);
    } catch (e) {
      setWalletError(e instanceof Error ? e.message : String(e));
    }
  }

  const opportunities = candidates.filter((c) => c.classification === "qualified" || c.classification === "high_conviction").slice(0, 4);
  // "Terminal 2.1" directive, Phase 3 — rejected/blocked candidates are
  // real evidence, not noise; the directive's own words: "This is much
  // more useful than simply hiding the candidate." Real classification
  // already on the candidate — no backend change needed for this view.
  const recentlyRejected = candidates.filter((c) => c.classification === "rejected").slice(0, 4);
  const enteredMints = new Set(positions.map((p) => p.mint));

  return (
    <div className="relative min-h-screen w-screen overflow-x-hidden bg-cmd-bg text-[10px] text-cmd-text">
      <AnimatedGrid className="fixed" />
      <div className="relative mx-auto max-w-[1600px] space-y-3 p-3">
        {/* Header strip */}
        <Glass className="flex flex-wrap items-center justify-between gap-3 p-3">
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-[13px] font-semibold uppercase tracking-[0.2em] text-cmd-cyan">Memecoin Sniper</span>
              <span className="text-[8px] uppercase tracking-wide text-cmd-textDim">Specialist Terminal — not part of the main TradeTown app</span>
            </div>
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
            {status?.risk.killSwitchTriggered && <StatusPill tone="red">KILL SWITCH: {status.risk.killSwitchReason}</StatusPill>}
            <button
              type="button"
              disabled={busy}
              onClick={() => void setEngineStatus("stopped")}
              className="rounded-sm border border-cmd-red/60 bg-cmd-red/10 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-cmd-red shadow-cmd-red hover:bg-cmd-red/20 disabled:opacity-50"
            >
              Stop / Kill
            </button>
            <a href="/" className="rounded-sm border border-cmd-border px-3 py-1.5 text-[9px] uppercase tracking-wide text-cmd-textDim hover:text-cmd-cyan">
              ← Back to TradeTown
            </a>
          </div>
        </Glass>

        {error && <Glass className="border-cmd-red/50 p-2 text-[9px] text-cmd-red">{error}</Glass>}

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          <Glass className="p-3">
            <TerminalLabel>Performance (today)</TerminalLabel>
            <DataRow label="Session P&L" value={status ? fmtSol(status.todayPnlSol) : "—"} valueClassName={status && status.todayPnlSol >= 0 ? "text-cmd-green" : "text-cmd-red"} />
            <DataRow label="Trades today" value={status?.todayTradeCount ?? 0} />
            <DataRow label="Win rate" value={status?.winRatePct !== null && status?.winRatePct !== undefined ? `${status.winRatePct}%` : "NOT VERIFIED"} />
            <DataRow label="Expectancy" value={status?.expectancyR !== null && status?.expectancyR !== undefined ? `${status.expectancyR >= 0 ? "+" : ""}${status.expectancyR}R` : "NOT VERIFIED"} />
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Risk status</TerminalLabel>
            <DataRow label="Drawdown" value={`${status?.risk.drawdownPct.toFixed(1) ?? "0.0"}% of max`} />
            <DataRow label="Daily loss" value={status ? `${fmtSol(-status.risk.dailyLossSol)} of max ${status.config.maxDailyLossPct}%` : "—"} valueClassName="text-cmd-red" />
            {status && (
              <DataRow
                label="Open risk"
                value={`${status.risk.openRiskSol.toFixed(4)} SOL — max ${((status.risk.equitySol * status.config.maxOpenRiskPct) / 100).toFixed(3)} SOL (${status.risk.equitySol > 0 ? ((status.risk.openRiskSol / (status.risk.equitySol * (status.config.maxOpenRiskPct / 100))) * 100).toFixed(0) : "0"}% utilized)`}
              />
            )}
            <DataRow label="Risk per trade (base)" value={`${status?.config.riskPerTradePct ?? "—"}%`} />
            <DataRow label="Size multiplier (dynamic)" value={`${status?.risk.sizeMultiplier.toFixed(2) ?? "1.00"}x`} />
            <DataRow label="Consecutive losses" value={status?.risk.consecutiveLosses ?? 0} />
            <DataRow
              label="Kill switch"
              value={<StatusPill tone={status?.risk.killSwitchTriggered ? "red" : status?.risk.killSwitchArmed ? "green" : "neutral"}>{status?.risk.killSwitchTriggered ? "TRIGGERED" : status?.risk.killSwitchArmed ? "ARMED" : "DISARMED"}</StatusPill>}
            />
          </Glass>

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
            {status && !status.liveArming.armed && <p className="mt-2 text-[8px] leading-relaxed text-cmd-textDim">Live trading locked: {status.liveArming.blockingReasons[0]}</p>}
          </Glass>
        </div>

        {/* "Terminal 2.2" directive, Part X/XI — real cumulative realized
            P&L, built server-side from the exact same trade journal the
            Performance (today) card above reads (see
            build_sniper_pnl_history's own docstring for why this is
            realized-only, not a mark-to-market equity curve, and for the
            disclosed future gap that would be needed for one). */}
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <Glass className="p-3">
            <TerminalLabel>Realized P&L — cumulative, all-time (not a mark-to-market equity curve)</TerminalLabel>
            <EquityCurveChart
              startingBalance={0}
              pnls={pnlHistory.map((p) => p.realizedPnlSol)}
              formatValue={(v) => fmtSol(v)}
              emptyLabel="No P&L history yet — no Sniper trades have closed this session."
              height={120}
            />
          </Glass>

          {/* "Equity Snapshot Telemetry 1.0" directive, Part XIX — a
              SEPARATE, clearly labeled chart, never merged into the
              realized-P&L line above. Each point is a real, periodic
              mark-to-market reading (realized equity + live unrealized
              P&L from open positions) — see
              build_sniper_equity_snapshot's own docstring. The series fed
              to EquityCurveChart is the real snapshot-to-snapshot delta,
              so walking forward from the first real snapshot's own
              totalEquitySol reproduces every later real value exactly —
              no interpolation, no invented points. Rolling recent window
              (see MAX_SNIPER_EQUITY_SNAPSHOTS, app/nexus.py) — never the
              full permanent lifetime, disclosed via the "history begins"
              note below rather than implied to be complete. */}
          <Glass className="p-3">
            <TerminalLabel>Account equity — mark-to-market (realized + live unrealized, rolling recent window)</TerminalLabel>
            <EquityCurveChart
              startingBalance={equityHistory[0]?.totalEquitySol ?? 0}
              pnls={equityHistory.slice(1).map((s, i) => s.totalEquitySol - (equityHistory[i]?.totalEquitySol ?? 0))}
              formatValue={(v) => fmtSol(v)}
              emptyLabel="No equity history yet — telemetry begins once the Sniper engine starts running or paused."
              height={120}
            />
            {equityHistory.length > 0 && (
              <p className="mt-1 text-[8px] text-cmd-textDim">
                History begins {new Date(equityHistory[0]?.timestamp ?? "").toLocaleTimeString()} — a rolling recent window, not permanent lifetime history.
              </p>
            )}
          </Glass>
        </div>

        {/* Discovery */}
        <Glass className="p-3">
          <TerminalLabel>Discovery — evidence-ranked opportunities, never a bare score</TerminalLabel>
          {opportunities.length === 0 ? (
            <EmptyState>No qualified/high-conviction candidates yet this session.</EmptyState>
          ) : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {opportunities.map((c) => (
                <div key={c.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                  <div className="flex items-center justify-between gap-1">
                    <span className="font-semibold text-cmd-cyan">{c.symbol}</span>
                    <div className="flex items-center gap-1">
                      {enteredMints.has(c.mint) && <StatusPill tone="green">ENTERED</StatusPill>}
                      <StatusPill tone={CLASSIFICATION_TONE[c.classification]}>{c.classification.replace(/_/g, " ")}</StatusPill>
                    </div>
                  </div>
                  <div className="mt-1 text-cmd-textDim">{timeAgo(c.discoveredAt)} · {c.timingState.replace(/_/g, " ")}</div>
                  <div className="mt-1 flex items-baseline gap-1">
                    <span className="text-lg font-semibold text-cmd-text tabular-nums">{c.opportunityScore ?? "—"}</span>
                    <span className="text-cmd-textDim">score</span>
                  </div>
                  <DataRow label="Liquidity" value={`$${c.liquidityUsd.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
                  <DataRow label="Buy pressure" value={`${c.buyPressurePct}%`} />
                  <DataRow label="Safety" value={<StatusPill tone={SAFETY_TONE[c.safetyStatus]}>{c.safetyStatus.replace(/_/g, " ")}</StatusPill>} />
                  <button type="button" onClick={() => setExpandedCandidateId(expandedCandidateId === c.id ? null : c.id)} className="mt-1.5 w-full rounded-sm border border-cmd-border py-1 text-[8px] uppercase tracking-wide text-cmd-textDim hover:text-cmd-cyan">
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

                      {/* CEO directive "TradeTown — Memecoin Sniper AI 1.0" —
                          real, human-triggered shadow reasoning. Never
                          auto-fired; the CEO decides when to spend a real
                          provider call. */}
                      <div className="mt-2 border-t border-cmd-border/60 pt-2">
                        <div className="flex items-center justify-between gap-1">
                          <span className="text-cmd-purple">AI shadow reasoning</span>
                          <button
                            type="button"
                            disabled={aiLoadingMint === c.mint}
                            onClick={() => void runAiAnalysis(c)}
                            className="rounded-sm border border-cmd-purple/50 px-1.5 py-0.5 text-[8px] uppercase tracking-wide text-cmd-purple hover:bg-cmd-purple/10 disabled:opacity-50"
                          >
                            {aiLoadingMint === c.mint ? "Asking…" : "Ask AI"}
                          </button>
                        </div>
                        {(aiResultsByMint[c.mint] ?? []).slice(-1).map((result) => (
                          <div key={result.id} className="mt-1 space-y-1">
                            {result.status !== "completed" ? (
                              <div className="text-cmd-textDim">
                                {result.status === "provider_unavailable" ? "AI provider not configured in this environment." : `AI reasoning: ${result.status.replace(/_/g, " ")}.`}
                                {result.failureDetail && <span className="block text-cmd-textDim/70">{result.failureDetail}</span>}
                              </div>
                            ) : (
                              <>
                                <DataRow
                                  label="AI recommendation"
                                  value={
                                    <StatusPill tone={result.recommendation === "buy" ? "green" : result.recommendation === "reject_thesis" ? "red" : "amber"}>
                                      {(result.recommendation ?? "unclear").replace(/_/g, " ")}
                                    </StatusPill>
                                  }
                                />
                                <DataRow
                                  label="vs. deterministic engine"
                                  value={
                                    result.recommendation && result.deterministicRecommendation
                                      ? (result.recommendation === "buy") === (result.deterministicRecommendation === "buy")
                                        ? "AGREE"
                                        : "DISAGREE"
                                      : "—"
                                  }
                                />
                                {result.confidence !== null && <DataRow label="AI confidence (reasoning quality, not win probability)" value={`${result.confidence.toFixed(0)}/100`} />}
                                {result.thesis && <div className="mt-1 text-cmd-text">{result.thesis}</div>}
                                {result.riskFlags.length > 0 && <div className="text-cmd-red">Risk flags: {result.riskFlags.join("; ")}</div>}
                                {result.unknowns.length > 0 && <div className="text-cmd-textDim">Unknowns: {result.unknowns.join("; ")}</div>}
                              </>
                            )}
                          </div>
                        ))}
                        {aiError && <div className="mt-1 text-cmd-red">{aiError}</div>}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Glass>

        {/* "Terminal 2.1" directive, Phase 3 — a rejected candidate is
            real evidence, not something to hide. Real classification +
            real safety-check breakdown already on the candidate; no
            backend change needed for this section. */}
        {recentlyRejected.length > 0 && (
          <Glass className="p-3">
            <TerminalLabel>Recently rejected — real reasons, never hidden</TerminalLabel>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {recentlyRejected.map((c) => (
                <div key={c.id} className="rounded-sm border border-cmd-red/30 bg-cmd-bg/40 p-2 text-[9px]">
                  <div className="flex items-center justify-between gap-1">
                    <span className="font-semibold text-cmd-text">{c.symbol}</span>
                    <StatusPill tone="red">REJECTED</StatusPill>
                  </div>
                  <div className="mt-1 text-cmd-textDim">{timeAgo(c.discoveredAt)} · score {c.opportunityScore ?? "—"}</div>
                  <div className="mt-1 text-cmd-red">{c.decisionReason}</div>
                </div>
              ))}
            </div>
          </Glass>
        )}

        {/* Professional trading terminal — the directive's own headline correction */}
        <SniperTerminal positions={positions} candidates={candidates} trades={trades} />

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          <Glass className="p-3 lg:col-span-2">
            <TerminalLabel>Recent activity — real, persisted event log</TerminalLabel>
            {events.length === 0 ? (
              <EmptyState>No events yet.</EmptyState>
            ) : (
              <div className="max-h-64 space-y-1 overflow-y-auto text-[8px]">
                {events.map((e) => (
                  <div key={e.id} className="border-b border-cmd-border/40 pb-1 text-cmd-textDim last:border-0">
                    <span className="text-cmd-cyan">{timeAgo(e.timestamp)}</span> <span className={`font-semibold ${EVENT_TONE[e.type]}`}>{e.type.toUpperCase().replace(/_/g, " ")}</span>
                    {e.symbol && <span className="text-cmd-text"> {e.symbol}</span>} — {e.detail}
                  </div>
                ))}
              </div>
            )}
          </Glass>

          {/* "Terminal 2.1" directive, Phase 5 — real wallet METADATA
              management. No field for a private key/seed phrase exists
              anywhere on SniperWallet, and adding a wallet never arms
              live trading — see this file's own module docstring. */}
          <Glass className="p-3">
            <TerminalLabel>Wallet management — public metadata only, no secrets</TerminalLabel>
            {walletError && <div className="mb-1.5 rounded-sm border border-cmd-red/50 bg-cmd-red/10 p-1.5 text-cmd-red">{walletError}</div>}
            {wallets.length === 0 ? (
              <EmptyState>No wallets added yet. Public address only — this environment has no secure credential storage for a real signing key, so adding a wallet never arms live trading.</EmptyState>
            ) : (
              <div className="space-y-1">
                {wallets.map((w) => (
                  <div key={w.id} data-testid={`sniper-wallet-${w.id}`} className="flex items-center gap-2 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="truncate font-semibold text-cmd-text">{w.label}</span>
                        {w.isActive && <StatusPill tone="green">ACTIVE</StatusPill>}
                      </div>
                      <div className="truncate text-cmd-textDim">{w.publicAddress} · {w.network}</div>
                    </div>
                    {!w.isActive && (
                      <button type="button" onClick={() => void activateWallet(w.id)} className="shrink-0 rounded-sm border border-cmd-cyan/50 px-2 py-1 text-cmd-cyan hover:bg-cmd-cyan/10">
                        Set active
                      </button>
                    )}
                    <button type="button" onClick={() => void removeWallet(w.id)} className="shrink-0 rounded-sm border border-cmd-red/50 px-2 py-1 text-cmd-red hover:bg-cmd-red/10">
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-2 flex flex-wrap gap-1.5 border-t border-cmd-border/50 pt-2">
              <input
                type="text"
                placeholder="Label (e.g. Ops wallet)"
                value={walletLabel}
                onChange={(e) => setWalletLabel(e.target.value)}
                className="min-w-0 flex-1 rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text placeholder:text-cmd-textDim"
              />
              <input
                type="text"
                placeholder="Public address"
                value={walletAddress}
                onChange={(e) => setWalletAddress(e.target.value)}
                className="min-w-0 flex-[2] rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-cmd-text placeholder:text-cmd-textDim"
              />
              <button
                type="button"
                disabled={!walletLabel.trim() || !walletAddress.trim()}
                onClick={() => void addWallet()}
                className="shrink-0 rounded-sm border border-cmd-green/50 bg-cmd-green/10 px-3 py-1 uppercase tracking-wide text-cmd-green hover:bg-cmd-green/20 disabled:opacity-40"
              >
                Add wallet
              </button>
            </div>
            {status && !status.liveArming.armed && <p className="mt-2 text-[8px] leading-relaxed text-cmd-textDim">Live trading locked regardless of wallet state: {status.liveArming.blockingReasons.join(" ")}</p>}
          </Glass>
        </div>

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <Glass className="p-3">
            <TerminalLabel>Smart money activity (simulated)</TerminalLabel>
            {leads.length === 0 ? (
              <EmptyState>No leads generated yet.</EmptyState>
            ) : (
              <div className="space-y-1">
                {leads.map((lead) => (
                  <DataRow key={lead.id} label={lead.walletLabel} value={`${lead.winRatePct}% WR · ${lead.tradeCount} trades · weight ${lead.weight.toFixed(2)}`} />
                ))}
              </div>
            )}
          </Glass>

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
