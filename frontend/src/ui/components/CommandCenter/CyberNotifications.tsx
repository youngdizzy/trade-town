import { useCallback, useEffect, useRef, useState } from "react";
import { EventBus } from "@/game/systems/EventBus";
import { gameStore } from "@/state/gameStore";
import type { EmergencyStopState, NotificationTier, ResearchItem, RiskWarning, ScannerAlert, TradeProposal } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";

type ToastKind = "trade" | "research" | "volatility" | "alert" | "save" | "risk";

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
  risk: { border: "border-cmd-red/60 shadow-cmd-red animate-pulse", label: "text-cmd-red", dot: "bg-cmd-red" },
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
 *
 * Design Bible Chapter 67 (TTOS) Part 3 — Smart Notification priority
 * tiers. Every toast is also recorded into gameStore's `alertHistory`
 * (viewable in the Executive Alert Center, AlertCenter.tsx) at a real
 * tier derived from the same fields already driving the toast itself —
 * never a separate, second-guessed severity. Only two sources genuinely
 * carry a real backend-tagged severity: RiskWarning.severity (a critical
 * risk warning previously produced no proactive notification at all,
 * only passive visibility in RiskPanel/GlobalStatusBar — this is a real
 * gap this slice closes) and Emergency Stop activation. Both are
 * "critical" tier and, unlike every other toast here, do not
 * auto-dismiss — the CEO must close them, the one real behavioral
 * difference "interrupts" means for a non-blocking corner toast (a true
 * modal interrupt already exists for trade proposals via
 * ExecutiveVoting.tsx and stays that component's own territory, not
 * duplicated here). ScannerAlert carries no real severity field of its
 * own; `high_volatility` is treated as "high" tier (its own distinct
 * "volatility" toast style already implied this), everything else
 * "normal" — the same tier split this component's own kind-routing
 * already made, just made explicit.
 */
export function CyberNotifications() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef<Map<string, number>>(new Map());
  const priorRiskWarningIds = useRef<Set<string> | null>(null);
  const notifiedEmergencyStopAt = useRef<string | null | undefined>(undefined);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, leaving: true } : t)));
    window.setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 250);
    const handle = timers.current.get(id);
    if (handle) window.clearTimeout(handle);
    timers.current.delete(id);
  }, []);

  const push = useCallback(
    (kind: ToastKind, title: string, body: string, tier: NotificationTier, sticky = false) => {
      const id = `${kind}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setToasts((prev) => [...prev.slice(-3), { id, kind, title, body, leaving: false }]);
      gameStore.pushAlert(tier, title, body);
      if (!sticky) {
        const handle = window.setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
        timers.current.set(id, handle);
      }
    },
    [dismiss],
  );

  useEffect(() => {
    const onProposal = (proposal: TradeProposal) =>
      push("trade", "NEW TRADE AVAILABLE", `${proposal.symbol} — desk recommends ${proposal.overallRecommendation.toUpperCase()}.`, "normal");
    const onResearch = (item: ResearchItem) =>
      push("research", "RESEARCH COMPLETE", `${AGENT_PROFILES[item.assignedAgent].name} finished ${item.symbol ?? item.title}.`, "normal");
    const onAlert = (alert: ScannerAlert) => {
      if (alert.alertType === "high_volatility") {
        push("volatility", "HIGH VOLATILITY WARNING", alert.message, "high");
      } else if (alert.alertType === "gap_up" || alert.alertType === "gap_down" || alert.alertType === "breakout") {
        push("alert", "NEWS ALERT", alert.message, "normal");
      }
    };
    // v0.7 — Save Architecture Redesign Phase 3: the one real error case
    // worth interrupting the player for — a successful save produces no
    // toast (autosave fires every 30-60s; a toast on every one would just
    // be noise, same reasoning as AGENT LEVEL UP not existing above).
    // Now sticky, matching its already-real "critical" severity (a save
    // failure is a real data-loss risk) — the same interrupt behavior
    // the two new listeners below use.
    const onSaveFailed = ({ error }: { error: string }) => push("save", "SAVE FAILED", error, "critical", true);
    // New — previously a critical RiskWarning produced zero proactive
    // notification anywhere in this codebase, only passive visibility in
    // RiskPanel/GlobalStatusBar. Diffed by id against the previous tick's
    // warnings so only newly-appeared ones interrupt, never the same
    // still-active warning on every re-render.
    const onRiskWarnings = (warnings: RiskWarning[]) => {
      const priorIds = priorRiskWarningIds.current;
      priorRiskWarningIds.current = new Set(warnings.map((w) => w.id));
      if (priorIds === null) return; // first snapshot — nothing "new" yet
      for (const w of warnings) {
        if (priorIds.has(w.id)) continue;
        if (w.severity === "critical") push("risk", "CRITICAL RISK ALERT", `${w.symbol}: ${w.message}`, "critical", true);
      }
    };
    // New — Emergency Stop activation previously had no toast at all,
    // only the button's own visual state change and a Company Memory
    // entry. NexusManager.setEmergencyStop applies the activate/resume
    // response immediately, ahead of the next real WS broadcast tick
    // (same "don't wait for the next tick" pattern as riskLimits) — so a
    // stale, already-in-flight `active: false` broadcast sent by the
    // server just *before* activation can arrive and get processed just
    // *after* the immediate apply. A plain boolean false->true diff would
    // treat that stale tick as "resumed", then the next real tick would
    // look like a brand-new activation and double-push. Keying off the
    // real `activatedAt` identity instead (unique per real activation,
    // untouched by a stale `active: false` tick, since that branch never
    // runs when state.active is false) makes this immune to that race.
    const onEmergencyStop = (state: EmergencyStopState) => {
      if (notifiedEmergencyStopAt.current === undefined) {
        // First snapshot — record without pushing, whatever it is (never
        // notify about state that already existed before this mount).
        notifiedEmergencyStopAt.current = state.active ? state.activatedAt : null;
        return;
      }
      if (state.active && state.activatedAt !== notifiedEmergencyStopAt.current) {
        notifiedEmergencyStopAt.current = state.activatedAt;
        push("risk", "EMERGENCY STOP ACTIVATED", "All new trading is halted until the CEO resumes.", "critical", true);
      }
    };
    EventBus.on("tradeProposal:new", onProposal);
    EventBus.on("research:completed", onResearch);
    EventBus.on("scanner:alertDetected", onAlert);
    EventBus.on("save:failed", onSaveFailed);
    EventBus.on("riskWarnings:updated", onRiskWarnings);
    EventBus.on("emergencyStop:updated", onEmergencyStop);
    return () => {
      EventBus.off("tradeProposal:new", onProposal);
      EventBus.off("research:completed", onResearch);
      EventBus.off("scanner:alertDetected", onAlert);
      EventBus.off("save:failed", onSaveFailed);
      EventBus.off("riskWarnings:updated", onRiskWarnings);
      EventBus.off("emergencyStop:updated", onEmergencyStop);
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
