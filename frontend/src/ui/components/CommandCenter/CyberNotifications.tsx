import { useCallback, useEffect, useRef, useState } from "react";
import { EventBus } from "@/game/systems/EventBus";
import type { ResearchItem, ScannerAlert, TradeProposal } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";

type ToastKind = "trade" | "research" | "volatility" | "alert" | "save";

interface Toast {
  id: string;
  kind: ToastKind;
  title: string;
  body: string;
  leaving: boolean;
}

const KIND_STYLE: Record<ToastKind, { border: string; label: string; dot: string }> = {
  trade: { border: "border-cmd-cyan/50 shadow-cmd-cyan", label: "text-cmd-cyan", dot: "bg-cmd-cyan" },
  research: { border: "border-cmd-green/50 shadow-cmd-green", label: "text-cmd-green", dot: "bg-cmd-green" },
  volatility: { border: "border-cmd-amber/50 shadow-cmd-amber", label: "text-cmd-amber", dot: "bg-cmd-amber" },
  alert: { border: "border-cmd-purple/50", label: "text-cmd-purple", dot: "bg-cmd-purple" },
  save: { border: "border-cmd-red/50", label: "text-cmd-red", dot: "bg-cmd-red" },
};

const AUTO_DISMISS_MS = 6000;

/**
 * Feature 14 — futuristic corner toasts for events that don't already
 * have a dedicated modal. TRADE WON / TRADE LOST from the spec's example
 * list are deliberately NOT duplicated here — TradeOutcomeBanner.tsx
 * already gives a closed trade its own full-treatment celebration/shake
 * moment, and a second toast for the same event would just be noise on
 * top of it. AGENT LEVEL UP is also not implemented: TradeTown agents
 * have no leveling mechanic to report on, and inventing one here would
 * fabricate a signal the backend doesn't produce. Everything else below
 * is a real EventBus event already emitted elsewhere in the app.
 */
export function CyberNotifications() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef<Map<string, number>>(new Map());

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, leaving: true } : t)));
    window.setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 250);
    const handle = timers.current.get(id);
    if (handle) window.clearTimeout(handle);
    timers.current.delete(id);
  }, []);

  const push = useCallback(
    (kind: ToastKind, title: string, body: string) => {
      const id = `${kind}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setToasts((prev) => [...prev.slice(-3), { id, kind, title, body, leaving: false }]);
      const handle = window.setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
      timers.current.set(id, handle);
    },
    [dismiss],
  );

  useEffect(() => {
    const onProposal = (proposal: TradeProposal) => push("trade", "NEW TRADE AVAILABLE", `${proposal.symbol} — desk recommends ${proposal.overallRecommendation.toUpperCase()}.`);
    const onResearch = (item: ResearchItem) => push("research", "RESEARCH COMPLETE", `${AGENT_PROFILES[item.assignedAgent].name} finished ${item.symbol ?? item.title}.`);
    const onAlert = (alert: ScannerAlert) => {
      if (alert.alertType === "high_volatility") {
        push("volatility", "HIGH VOLATILITY WARNING", alert.message);
      } else if (alert.alertType === "gap_up" || alert.alertType === "gap_down" || alert.alertType === "breakout") {
        push("alert", "NEWS ALERT", alert.message);
      }
    };
    // v0.7 — Save Architecture Redesign Phase 3: the one real error case
    // worth interrupting the player for — a successful save produces no
    // toast (autosave fires every 30-60s; a toast on every one would just
    // be noise, same reasoning as AGENT LEVEL UP not existing above).
    const onSaveFailed = ({ error }: { error: string }) => push("save", "SAVE FAILED", error);
    EventBus.on("tradeProposal:new", onProposal);
    EventBus.on("research:completed", onResearch);
    EventBus.on("scanner:alertDetected", onAlert);
    EventBus.on("save:failed", onSaveFailed);
    return () => {
      EventBus.off("tradeProposal:new", onProposal);
      EventBus.off("research:completed", onResearch);
      EventBus.off("scanner:alertDetected", onAlert);
      EventBus.off("save:failed", onSaveFailed);
    };
  }, [push]);

  if (toasts.length === 0) return null;

  return (
    <div className="pointer-events-none absolute right-3 top-14 z-[70] flex w-72 flex-col gap-2">
      {toasts.map((t) => {
        const style = KIND_STYLE[t.kind];
        return (
          <div
            key={t.id}
            className={`pointer-events-auto rounded-sm border bg-cmd-panel/90 p-2.5 font-cmdmono text-[10px] text-cmd-text backdrop-blur-md ${style.border} ${
              t.leaving ? "motion-safe:animate-cmd-toast-out" : "motion-safe:animate-cmd-toast-in"
            }`}
          >
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className={`flex items-center gap-1.5 uppercase tracking-wider ${style.label}`}>
                <span className={`inline-block h-1.5 w-1.5 rounded-full ${style.dot}`} />
                {t.title}
              </span>
              <button type="button" onClick={() => dismiss(t.id)} className="text-cmd-textDim hover:text-cmd-text">
                ✕
              </button>
            </div>
            <div className="text-cmd-textDim">{t.body}</div>
          </div>
        );
      })}
    </div>
  );
}
