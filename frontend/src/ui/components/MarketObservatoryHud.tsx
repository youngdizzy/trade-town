import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { CandlestickChart } from "@/ui/components/CommandCenter/CandlestickChart";
import { useCandles } from "@/ui/components/CommandCenter/lib/useCandles";
import { CONFIDENCE_TIER_LABEL } from "@/types";
import type { MarketEnvironmentRegime } from "@/types";
import { RISK_LEVEL_LABEL, confidenceTierTone, riskLevel, riskTextClass } from "@/ui/components/CommandCenter/lib/derive";
import { Glass, RiskDot, StatusPill, TerminalLabel } from "@/ui/components/CommandCenter/ui";

const MACRO_CATEGORIES = new Set(["economy", "gold", "bitcoin", "index"]);

const REGIME_TONE: Record<MarketEnvironmentRegime, "green" | "red" | "amber" | "cyan" | "neutral"> = {
  bull: "green",
  bear: "red",
  sideways: "neutral",
  high_volatility: "amber",
  low_volatility: "cyan",
};

/**
 * The Market Observatory's readouts — "deep immersive analysis," in
 * contrast to the Global Command Center's fast quick-access overlay (see
 * MarketObservatoryScene.ts's own docstring). Deliberately reuses the
 * exact same gameStore fields, derive.ts helpers, and CandlestickChart
 * component the Command Center already uses — the brief is explicit that
 * "Both must use the same underlying market data and analysis systems.
 * Do not create two disconnected fake systems."
 *
 * Ambient only (shows automatically while physically standing in the
 * room, same as BrainRoomHud's ambient mode) — no toolbar toggle, since
 * the whole point of a physical Observatory vs. the global Command Center
 * is that one requires actually walking there.
 */
export function MarketObservatoryHud() {
  const { currentScene, watchlist, decisions, research, news, riskWarnings, riskLimits, strategies, backtestSessions, time, marketEnvironment } = useGameStore();
  const [symbol, setSymbol] = useState(watchlist[0]?.symbol ?? "AAPL");
  const { candles, loading, error } = useCandles(symbol, "1h", 100);
  const dataStatus = candles[0]?.dataStatus ?? null;

  if (currentScene !== "MarketObservatoryScene") return null;

  const level = riskLevel(riskWarnings);
  const activeWatch = watchlist.find((w) => w.symbol === symbol);

  const latestDecisionForSymbol = [...decisions].reverse().find((d) => d.symbol === symbol) ?? null;
  const recentNews = [...news].filter((n) => n.category === "market" || n.category === "discovery").slice(-4).reverse();
  const macroResearch = research.filter((r) => MACRO_CATEGORIES.has(r.category)).slice(-4).reverse();
  const activeSimulations = backtestSessions.filter((s) => s.status !== "completed");

  return (
    <div className="pointer-events-none absolute inset-x-3 bottom-3 top-16 flex flex-col gap-2 font-cmdmono text-[10px] text-cmd-text">
      <Glass className="pointer-events-auto flex items-center justify-between px-3 py-1.5">
        <div className="flex items-center gap-3">
          <span className="tracking-[0.15em] text-cmd-cyan">MARKET OBSERVATORY</span>
          <span className="text-cmd-textDim">
            Day {time.day} · {String(time.hour).padStart(2, "0")}:{String(time.minute).padStart(2, "0")}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-cmd-textDim">
            {activeWatch ? `${activeWatch.symbol} — $${activeWatch.lastPrice.toFixed(2)} (${activeWatch.dailyChangePct >= 0 ? "+" : ""}${activeWatch.dailyChangePct.toFixed(2)}%)` : symbol}
          </span>
          {latestDecisionForSymbol?.confidenceEngine && (
            <StatusPill tone={confidenceTierTone(latestDecisionForSymbol.confidenceEngine.tier)}>
              {CONFIDENCE_TIER_LABEL[latestDecisionForSymbol.confidenceEngine.tier]} · {Math.round(latestDecisionForSymbol.confidenceEngine.score)}
            </StatusPill>
          )}
          <span className={`flex items-center gap-1 ${riskTextClass(level)}`}>
            <RiskDot level={level} /> {RISK_LEVEL_LABEL[level]}
          </span>
        </div>
      </Glass>

      <div className="grid min-h-0 flex-1 grid-cols-3 gap-2">
        <Glass className="pointer-events-auto col-span-2 flex flex-col p-3">
          <div className="mb-2 flex items-center justify-between">
            <TerminalLabel>Large Central Market Display</TerminalLabel>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="rounded-sm border border-cmd-border bg-cmd-bg px-1.5 py-0.5 text-[10px] text-cmd-text"
            >
              {watchlist.map((w) => (
                <option key={w.symbol} value={w.symbol}>
                  {w.symbol}
                </option>
              ))}
            </select>
          </div>
          <CandlestickChart candles={candles} loading={loading} error={error} dataStatus={dataStatus} height={200} />
          {latestDecisionForSymbol && (
            <div className="mt-2 border-t border-cmd-border/60 pt-2 text-[9px] text-cmd-textDim">
              Latest decision on {symbol}: <span className="text-cmd-text">{latestDecisionForSymbol.finalReasoning}</span>
            </div>
          )}
        </Glass>

        <div className="col-span-1 grid grid-rows-2 gap-2">
          <Glass className="pointer-events-auto overflow-y-auto p-2.5">
            <div className="mb-1 flex items-center justify-between">
              <TerminalLabel>Technical Station</TerminalLabel>
              <StatusPill tone={REGIME_TONE[marketEnvironment.current]}>{marketEnvironment.label}</StatusPill>
            </div>
            <div className="text-[9px] text-cmd-textDim">{marketEnvironment.detail}</div>
            {latestDecisionForSymbol && <div className="mt-1 text-[9px] text-cmd-textDim">{latestDecisionForSymbol.technicalSummary}</div>}
            {marketEnvironment.timeline.length > 0 && (
              <div className="mt-1.5 border-t border-cmd-border/50 pt-1.5">
                <div className="mb-0.5 text-[9px] uppercase tracking-wide text-cmd-textDim">Environment Timeline</div>
                {[...marketEnvironment.timeline]
                  .reverse()
                  .slice(0, 3)
                  .map((entry) => (
                    <div key={entry.id} className="truncate text-[9px] text-cmd-textDim">
                      t+{entry.simMinutes}m — {entry.label}
                    </div>
                  ))}
              </div>
            )}
          </Glass>
          <Glass className="pointer-events-auto overflow-y-auto p-2.5">
            <TerminalLabel>News/Events Station</TerminalLabel>
            {recentNews.length === 0 ? (
              <div className="text-cmd-textDim">No recent headlines.</div>
            ) : (
              <div className="space-y-1">
                {recentNews.map((n) => (
                  <div key={n.id} className="truncate text-[9px] text-cmd-textDim">
                    {n.headline}
                  </div>
                ))}
              </div>
            )}
          </Glass>
        </div>

        <Glass className="pointer-events-auto overflow-y-auto p-2.5">
          <TerminalLabel>Macro Station</TerminalLabel>
          {macroResearch.length === 0 ? (
            <div className="text-cmd-textDim">No macro/economy research yet.</div>
          ) : (
            <div className="space-y-1">
              {macroResearch.map((r) => (
                <div key={r.id} className="text-[9px]">
                  <span className="text-cmd-cyan">{r.symbol ?? r.category}</span> — <span className="text-cmd-textDim">{r.summary || "In progress."}</span>
                </div>
              ))}
            </div>
          )}
        </Glass>

        <Glass className="pointer-events-auto overflow-y-auto p-2.5">
          <div className="mb-1 flex items-center justify-between">
            <TerminalLabel>Risk Station</TerminalLabel>
            <StatusPill tone={level === "red" ? "red" : level === "yellow" ? "amber" : "green"}>{RISK_LEVEL_LABEL[level]}</StatusPill>
          </div>
          <div className="text-[9px] text-cmd-textDim">
            {riskWarnings.length} active warning{riskWarnings.length === 1 ? "" : "s"} · limit {riskLimits.maxDrawdownPct}% drawdown
          </div>
          {riskWarnings.slice(0, 3).map((w) => (
            <div key={w.id} className={`mt-1 text-[9px] ${w.severity === "critical" ? "text-cmd-red" : "text-cmd-amber"}`}>
              [{w.symbol}] {w.message}
            </div>
          ))}
        </Glass>

        <Glass className="pointer-events-auto overflow-y-auto p-2.5">
          <TerminalLabel>Strategy Station</TerminalLabel>
          <div className="text-[9px] text-cmd-textDim">
            {strategies.length} strategies tracked · {activeSimulations.length} simulation{activeSimulations.length === 1 ? "" : "s"} running
          </div>
          {strategies.slice(0, 3).map((s) => (
            <div key={s.id} className="mt-1 truncate text-[9px] text-cmd-text">
              {s.name} — {AGENT_PROFILES[s.createdBy].name}
            </div>
          ))}
        </Glass>
      </div>
    </div>
  );
}
