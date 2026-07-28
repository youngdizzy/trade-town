import { useEffect, useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { PaperTrade } from "@/types";
import { api } from "@/net/api";
import { NexusManager } from "@/game/systems/NexusManager";
import { Glass, StatusPill } from "@/ui/components/CommandCenter/ui";

type Outcome = "win" | "loss" | "breakeven";

function classifyOutcome(pnl: number): Outcome {
  if (pnl > 0) return "win";
  if (pnl < 0) return "loss";
  return "breakeven";
}

const OUTCOME_LABEL: Record<Outcome, string> = { win: "WIN", loss: "LOSS", breakeven: "BREAKEVEN" };
const THESIS_LABEL: Record<Outcome, string> = {
  win: "Thesis confirmed — the reasoning behind this trade played out.",
  loss: "Thesis invalidated — the trade moved against the original reasoning.",
  breakeven: "Thesis neutral — the trade closed flat, no real confirmation either way.",
};

/**
 * Trade outcome popups (v0.6.2 Phase 10). Every field shown here is a
 * real value already on the closed PaperTrade (see app/journal.py) —
 * win/loss/breakeven and the thesis classification are both a direct,
 * honest read of the trade's own real pnl sign, not a second invented
 * signal. Acknowledgement persists via POST /api/trades/ack so a
 * refresh or Docker restart never re-shows a popup already seen.
 *
 * Only the single most recently closed trade ever gets a popup. If
 * several trades closed while the player was away (or on the very
 * first load of an existing save), the older ones are acknowledged
 * silently in the background instead of queuing up a stack of popups —
 * a backlog of 49 blocking modals to click through would make the
 * feature actively hostile rather than a celebration. Every trade still
 * has its full real analysis available any time in the Command Center's
 * Decisions/Performance tabs; this popup is a "here's what just
 * happened" moment, not the only record.
 */
export function TradeOutcomePopup() {
  const { paperPortfolio, viewedTradeNotificationIds, currentScene } = useGameStore();
  const [dismissing, setDismissing] = useState(false);

  const unviewed = useMemo(() => {
    return [...paperPortfolio.tradeHistory].filter((t) => !viewedTradeNotificationIds.includes(t.id)).sort((a, b) => a.closedSimMinutes - b.closedSimMinutes);
  }, [paperPortfolio.tradeHistory, viewedTradeNotificationIds]);

  const trade: PaperTrade | undefined = unviewed[unviewed.length - 1];
  const backlog = unviewed.slice(0, -1);

  useEffect(() => {
    if (backlog.length === 0) return;
    void Promise.all(backlog.map((t) => api.ackTradeNotification(t.id))).then((results) => {
      const last = results[results.length - 1];
      if (last) NexusManager.setViewedTradeNotificationIds(last.viewedTradeNotificationIds);
    });
    // Only re-run when the backlog's composition actually changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [backlog.map((t) => t.id).join(",")]);

  // The WebSocket connects at app boot (see GameCanvas.tsx), independent
  // of the title screen — so a real backlog of unviewed trades can already
  // exist by the time MainMenuScene is still showing. Never render a
  // full-screen popup over the title screen itself, or it swallows the
  // click meant for the canvas's own "Continue" button. Checked after the
  // hooks above (not as an early return before them) so every hook still
  // runs unconditionally on every render.
  if (currentScene === "MainMenuScene" || !trade) return null;

  const outcome = classifyOutcome(trade.pnl);

  const dismiss = async () => {
    if (dismissing) return;
    setDismissing(true);
    try {
      const res = await api.ackTradeNotification(trade.id);
      NexusManager.setViewedTradeNotificationIds(res.viewedTradeNotificationIds);
    } finally {
      setDismissing(false);
    }
  };

  const borderClass = outcome === "win" ? "border-cmd-green/60 animate-cmd-glow-pulse" : outcome === "loss" ? "border-cmd-red/60" : "border-cmd-border";
  const shakeClass = outcome === "loss" ? "motion-safe:animate-cmd-shake" : "";

  return (
    <div className="pointer-events-auto absolute inset-0 z-[60] flex items-center justify-center bg-cmd-bg/80 p-4 backdrop-blur-sm" data-testid="trade-outcome-popup">
      <div className={`relative w-full max-w-md overflow-hidden rounded-sm border bg-cmd-panel shadow-cmd-cyan ${borderClass} ${shakeClass}`}>
        {outcome === "win" && (
          <div className="pointer-events-none absolute inset-x-0 top-0 flex justify-around overflow-hidden" aria-hidden="true">
            {["#3ce28a", "#4fd8ff", "#ffb443", "#a78bfa"].flatMap((color, colorIdx) =>
              Array.from({ length: 3 }, (_, i) => (
                <span
                  key={`${colorIdx}-${i}`}
                  className="motion-safe:animate-cmd-confetti-fall block h-2 w-2 rounded-[1px]"
                  style={{ backgroundColor: color, animationDelay: `${(colorIdx * 3 + i) * 90}ms` }}
                />
              )),
            )}
          </div>
        )}

        <div className="relative space-y-3 p-5">
          <div className="flex items-center justify-between">
            <span className="font-cmdmono text-xl text-cmd-cyan">{trade.symbol}</span>
            <StatusPill tone={outcome === "win" ? "green" : outcome === "loss" ? "red" : "neutral"}>{OUTCOME_LABEL[outcome]}</StatusPill>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <Glass className="p-2">
              <div className="text-[9px] uppercase tracking-wide text-cmd-textDim">P&amp;L</div>
              <div className={`font-cmdmono ${outcome === "win" ? "text-cmd-green" : outcome === "loss" ? "text-cmd-red" : "text-cmd-text"}`}>
                {trade.pnl >= 0 ? "+" : ""}
                {trade.pnl.toFixed(2)} ({trade.pnl >= 0 ? "+" : ""}
                {trade.pnlPct.toFixed(1)}%)
              </div>
            </Glass>
            <Glass className="p-2">
              <div className="text-[9px] uppercase tracking-wide text-cmd-textDim">Entry → Exit</div>
              <div className="font-cmdmono text-cmd-text">
                {trade.entryPrice.toFixed(2)} → {trade.exitPrice.toFixed(2)}
              </div>
            </Glass>
          </div>

          <div className="text-cmd-textDim">{trade.reason}</div>

          <Glass className="p-2">
            <div className="text-[9px] uppercase tracking-wide text-cmd-textDim">Post-Trade Analysis</div>
            <div className="mt-1 text-cmd-text">{THESIS_LABEL[outcome]}</div>
            {trade.coachReview && <div className="mt-1 text-cmd-textDim">{trade.coachReview}</div>}
            {trade.lessonsLearned && <div className="mt-1 text-cmd-textDim">{trade.lessonsLearned}</div>}
          </Glass>

          <button
            type="button"
            onClick={() => void dismiss()}
            disabled={dismissing}
            className="w-full rounded-sm border border-cmd-border py-2 text-cmd-textDim hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
          >
            {dismissing ? "…" : "Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
