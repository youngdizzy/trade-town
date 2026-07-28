import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { PaperTrade } from "@/types";
import { CONFIDENCE_TIER_LABEL } from "@/types";
import { api } from "@/net/api";
import { NexusManager } from "@/game/systems/NexusManager";
import { EventBus } from "@/game/systems/EventBus";
import { confidenceTierTone, formatMoney } from "@/ui/components/CommandCenter/lib/derive";
import { StatusPill } from "@/ui/components/CommandCenter/ui";

type Outcome = "win" | "loss" | "breakeven";

const AUTO_DISMISS_MS = 8000;
const LEAVE_ANIM_MS = 300;
const COUNT_UP_MS = 900;

function classifyOutcome(pnl: number): Outcome {
  if (pnl > 0) return "win";
  if (pnl < 0) return "loss";
  return "breakeven";
}

function formatHoldingTime(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)}m`;
  const hours = Math.floor(minutes / 60);
  const rest = Math.round(minutes % 60);
  return rest === 0 ? `${hours}h` : `${hours}h ${rest}m`;
}

/** Eases 0 -> target over durationMs, restarting whenever `key` changes. */
function useCountUp(target: number, durationMs: number, key: string): number {
  const [value, setValue] = useState(0);
  useEffect(() => {
    setValue(0);
    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      setValue(target * (1 - (1 - t) * (1 - t)));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
    // Restart only when a genuinely new trade takes over the banner.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return value;
}

/**
 * v0.7 Feature 19 — the premium, non-blocking trade outcome banner that
 * replaces TradeOutcomePopup's full-screen blocking modal. Every field
 * shown is a real value already on the closed PaperTrade (see
 * app/journal.py) or, for the confidence pill, the TradeDecision that
 * approved the order behind it (see app/confidence.py) — nothing here is
 * invented. The spec's "Strategy" and "Trade Quality Score" fields are
 * deliberately not shown: TradeTown's auto-traded orders aren't linked to
 * a named Strategy record (those only exist for Simulation Lab backtests),
 * and Trade Quality Score was formally replaced by the real Decision
 * Confidence Engine in v0.7 Feature 15 rather than kept as a second,
 * duplicate number.
 *
 * Unlike the old popup, every closed-but-unviewed trade gets its own turn
 * in a real queue instead of the backlog being silently acknowledged —
 * "queue banners, never overlap" is a spec requirement, not just a nicety.
 */
export function TradeOutcomeBanner() {
  const { paperPortfolio, viewedTradeNotificationIds, currentScene, decisions } = useGameStore();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [leaving, setLeaving] = useState(false);

  const timerHandle = useRef<number | null>(null);
  const timerStartedAt = useRef(0);
  const timerRemaining = useRef(AUTO_DISMISS_MS);

  const queue = useMemo(
    () =>
      [...paperPortfolio.tradeHistory]
        .filter((t) => !viewedTradeNotificationIds.includes(t.id))
        .sort((a, b) => a.closedSimMinutes - b.closedSimMinutes),
    [paperPortfolio.tradeHistory, viewedTradeNotificationIds],
  );

  // Looked up from the full trade history, not the viewed-filtered queue —
  // this trade must keep rendering through its own leave animation even
  // after the ack below has already dropped it out of `queue`.
  const trade: PaperTrade | undefined = activeId ? paperPortfolio.tradeHistory.find((t) => t.id === activeId) : undefined;

  const clearTimer = useCallback(() => {
    if (timerHandle.current !== null) {
      window.clearTimeout(timerHandle.current);
      timerHandle.current = null;
    }
  }, []);

  const ack = useCallback(async (id: string) => {
    const res = await api.ackTradeNotification(id);
    NexusManager.setViewedTradeNotificationIds(res.viewedTradeNotificationIds);
  }, []);

  const dismiss = useCallback(() => {
    if (!activeId || leaving) return;
    clearTimer();
    setLeaving(true);
    const id = activeId;
    window.setTimeout(() => {
      // Wait for the ack to land (so `queue` has already dropped this
      // trade) before freeing up activeId — otherwise the pull-next
      // effect below can race and re-select this same still-unviewed
      // trade instead of advancing the queue.
      void ack(id).finally(() => {
        setActiveId(null);
        setLeaving(false);
      });
    }, LEAVE_ANIM_MS);
  }, [activeId, leaving, ack, clearTimer]);

  const startTimer = useCallback(
    (ms: number) => {
      clearTimer();
      timerStartedAt.current = performance.now();
      timerRemaining.current = ms;
      timerHandle.current = window.setTimeout(dismiss, ms);
    },
    [clearTimer, dismiss],
  );

  // Pull the next queued trade in only once nothing is showing or leaving —
  // this is what makes banners queue instead of overlapping.
  useEffect(() => {
    if (activeId || leaving) return;
    const next = queue[0];
    if (next) setActiveId(next.id);
  }, [queue, activeId, leaving]);

  // Fresh 8s auto-dismiss timer every time a new trade takes the banner.
  useEffect(() => {
    if (!activeId) return;
    startTimer(AUTO_DISMISS_MS);
    return clearTimer;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

  const handleMouseEnter = () => {
    if (timerHandle.current === null) return;
    const elapsed = performance.now() - timerStartedAt.current;
    timerRemaining.current = Math.max(0, timerRemaining.current - elapsed);
    clearTimer();
  };

  const handleMouseLeave = () => {
    if (!activeId || leaving) return;
    startTimer(timerRemaining.current);
  };

  const inspect = (openDetail: boolean) => {
    if (trade?.decisionId) {
      EventBus.emit("trade:inspect", { decisionId: trade.decisionId, openDetail, nonce: Date.now() });
    }
    dismiss();
  };

  const countUpValue = useCountUp(trade?.pnl ?? 0, COUNT_UP_MS, trade?.id ?? "none");

  if (currentScene === "MainMenuScene" || !trade) return null;

  const outcome = classifyOutcome(trade.pnl);
  const decision = trade.decisionId ? (decisions.find((d) => d.id === trade.decisionId) ?? null) : null;
  const pnlDisplay = countUpValue >= 0 ? `+${formatMoney(countUpValue)}` : formatMoney(countUpValue);

  const borderClass = outcome === "win" ? "border-cmd-green/60" : outcome === "loss" ? "border-cmd-red/60" : "border-cmd-cyan/50";
  const glowClass = outcome === "win" ? "motion-safe:animate-cmd-glow-pulse" : outcome === "breakeven" ? "shadow-cmd-cyan" : "";
  const enterExitClass = leaving ? "motion-safe:animate-cmd-banner-out" : "motion-safe:animate-cmd-banner-in";
  const shakeClass = outcome === "loss" && !leaving ? "motion-safe:animate-cmd-shake" : "";

  return (
    <div className="pointer-events-none absolute inset-x-0 top-14 z-[65] flex justify-center px-3">
      <div
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        data-testid="trade-outcome-banner"
        className={`pointer-events-auto relative w-full max-w-md overflow-hidden rounded-lg border bg-cmd-panel/90 font-cmdmono text-[10px] text-cmd-text backdrop-blur-md ${borderClass} ${glowClass} ${enterExitClass} ${shakeClass}`}
      >
        {outcome === "win" && (
          <div className="pointer-events-none absolute inset-x-0 top-0 flex justify-around overflow-hidden" aria-hidden="true">
            {["#3ce28a", "#4fd8ff", "#ffb443", "#a78bfa"].flatMap((color, colorIdx) =>
              Array.from({ length: 2 }, (_, i) => (
                <span
                  key={`${colorIdx}-${i}`}
                  className="motion-safe:animate-cmd-confetti-fall block h-1.5 w-1.5 rounded-[1px]"
                  style={{ backgroundColor: color, animationDelay: `${(colorIdx * 2 + i) * 90}ms` }}
                />
              )),
            )}
          </div>
        )}

        <div className="relative space-y-2 p-3">
          <div className="flex items-center justify-between">
            <span
              className={`flex items-center gap-1.5 text-xs uppercase tracking-wide ${
                outcome === "win" ? "text-cmd-green" : outcome === "loss" ? "text-cmd-red motion-safe:animate-cmd-glitch" : "text-cmd-cyan"
              }`}
            >
              <span data-testid="trade-outcome-status">
                {outcome === "win" && "✓ TRADE WON"}
                {outcome === "loss" && "✕ TRADE LOST"}
                {outcome === "breakeven" && "TRADE CLOSED"}
              </span>
            </span>
            <span className="text-cmd-cyan" data-testid="trade-outcome-symbol">
              {trade.symbol}
            </span>
          </div>

          {outcome === "breakeven" ? (
            <div className="text-center text-base tracking-wide text-cmd-cyan">BREAK EVEN</div>
          ) : (
            <div className={`text-center text-2xl tabular-nums ${outcome === "win" ? "text-cmd-green" : "text-cmd-red"}`}>{pnlDisplay}</div>
          )}

          <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-cmd-textDim">
            <div>
              {trade.side === "buy" ? "LONG" : "SHORT"} · {trade.entryPrice.toFixed(2)} → {trade.exitPrice.toFixed(2)}
            </div>
            <div className="text-right">Held {formatHoldingTime(trade.durationMinutes)}</div>
          </div>

          {decision?.confidenceEngine && (
            <StatusPill tone={confidenceTierTone(decision.confidenceEngine.tier)}>
              {CONFIDENCE_TIER_LABEL[decision.confidenceEngine.tier]} · {Math.round(decision.confidenceEngine.score)} confidence
            </StatusPill>
          )}

          <div className="flex items-center gap-1.5 pt-0.5">
            {trade.decisionId && (
              <>
                <button
                  type="button"
                  onClick={() => inspect(false)}
                  className="rounded-sm border border-cmd-border px-2 py-1 text-cmd-textDim transition-colors hover:border-cmd-cyan/50 hover:text-cmd-cyan"
                >
                  View Trade
                </button>
                <button
                  type="button"
                  onClick={() => inspect(true)}
                  className="rounded-sm border border-cmd-border px-2 py-1 text-cmd-textDim transition-colors hover:border-cmd-cyan/50 hover:text-cmd-cyan"
                >
                  Analyze
                </button>
              </>
            )}
            <button
              type="button"
              onClick={dismiss}
              className="ml-auto rounded-sm border border-cmd-border px-2 py-1 text-cmd-textDim transition-colors hover:border-cmd-red/50 hover:text-cmd-red"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
