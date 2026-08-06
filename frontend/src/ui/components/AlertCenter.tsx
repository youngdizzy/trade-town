import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { useCloseOnEscape } from "@/ui/hooks/useCloseOnEscape";
import { EventBus } from "@/game/systems/EventBus";
import type { NotificationTier } from "@/types";
import { EmptyState, Glass, StatusPill, TerminalLabel } from "./CommandCenter/ui";

const TIER_LABEL: Record<NotificationTier, string> = { critical: "Critical", high: "High", normal: "Normal" };
const TIER_TONE: Record<NotificationTier, "red" | "amber" | "neutral"> = { critical: "red", high: "amber", normal: "neutral" };
const TIER_ORDER: NotificationTier[] = ["critical", "high", "normal"];

/**
 * Design Bible Chapter 67 (TTOS) Part 3 — the Executive Alert Center.
 * The full, permanent view over gameStore's `alertHistory` — every
 * toast CyberNotifications.tsx has ever shown (see that component's own
 * doc comment for exactly which real source maps to which tier), so a
 * notification the CEO glimpsed and missed is never actually lost.
 * Styled with the Command Center's own terminal component library
 * (`Glass`/`StatusPill`/`TerminalLabel`) rather than the pixel-parchment
 * world-chrome overlays (Newspaper/CompanyMemory/etc.) use, since this
 * overlay is a direct extension of CyberNotifications' own terminal-
 * styled toasts, not a lore/social surface.
 */
export function AlertCenter() {
  const { alertCenterOpen, alertHistory } = useGameStore();
  const [tier, setTier] = useState<NotificationTier | null>(null);
  const close = () => EventBus.emit("ui:alertCenter", { open: false });
  useCloseOnEscape(alertCenterOpen, close);
  if (!alertCenterOpen) return null;

  const filtered = tier === null ? alertHistory : alertHistory.filter((a) => a.tier === tier);
  const counts: Record<NotificationTier, number> = { critical: 0, high: 0, normal: 0 };
  for (const a of alertHistory) counts[a.tier]++;

  return (
    <div className="pointer-events-auto absolute inset-0 z-50 flex items-center justify-center bg-black/70 p-[10vh] font-cmdmono text-[11px] text-cmd-text backdrop-blur-sm">
      <div className="flex h-full w-full max-w-2xl flex-col overflow-hidden rounded-md border border-cmd-cyan/30 bg-cmd-bg shadow-cmd-cyan">
        <header className="flex items-center justify-between border-b border-cmd-border px-4 py-2.5">
          <div className="flex items-center gap-3">
            <span className="tracking-[0.2em] text-cmd-cyan">EXECUTIVE ALERT CENTER</span>
            <span className="text-cmd-textDim">{alertHistory.length} recorded</span>
          </div>
          <button type="button" onClick={close} className="rounded-sm border border-cmd-border px-2.5 py-1 text-cmd-textDim transition-colors hover:border-cmd-cyan/50 hover:text-cmd-cyan">
            CLOSE
          </button>
        </header>

        <div className="flex items-center gap-2 border-b border-cmd-border/60 px-4 py-2">
          <TierChip label="All" active={tier === null} onClick={() => setTier(null)} />
          {TIER_ORDER.map((t) => (
            <TierChip key={t} label={`${TIER_LABEL[t]} (${counts[t]})`} active={tier === t} onClick={() => setTier(t)} />
          ))}
        </div>

        <div className="flex-1 space-y-2 overflow-y-auto p-4">
          {filtered.length === 0 ? (
            <EmptyState>No alerts recorded yet.</EmptyState>
          ) : (
            filtered.map((a) => (
              <Glass key={a.id} className="p-3">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <TerminalLabel>{a.title}</TerminalLabel>
                  <StatusPill tone={TIER_TONE[a.tier]}>{TIER_LABEL[a.tier].toUpperCase()}</StatusPill>
                </div>
                <div className="text-cmd-textDim">{a.body}</div>
                <div className="mt-1 text-[9px] text-cmd-textDim/70">{new Date(a.createdAt).toLocaleString()}</div>
              </Glass>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function TierChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-sm border px-2 py-1 text-[9px] uppercase tracking-wide transition-colors ${
        active ? "border-cmd-cyan/50 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
      }`}
    >
      {label}
    </button>
  );
}
