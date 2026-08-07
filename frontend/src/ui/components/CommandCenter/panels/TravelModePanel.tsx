import { useEffect, useState } from "react";
import { api } from "@/net/api";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { NotificationSensitivity, TravelModeBriefing } from "@/types";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

/**
 * Design Bible Chapter 73.5 — Mobile Command Center & Remote Operations
 * (backend/app/travel_mode.py). A real CEO-configurable conservative
 * posture that composes with Company Priority's and Chapter 75's
 * Circuit Breaker's own derived-override seam — confirmed to be one of
 * exactly three tightening patterns in this codebase, never a fourth.
 * travelMode/travelModeBriefings are live via the WS tick broadcast
 * (gameStore); activate/deactivate/settings below are the real CEO
 * actions.
 */

const SENSITIVITY_LABEL: Record<NotificationSensitivity, string> = {
  all: "All Notifications",
  high_and_above: "High & Above",
  critical_only: "Critical Only",
};

export function TravelModePanel() {
  const { travelMode, travelModeBriefings } = useGameStore();

  const [positionCap, setPositionCap] = useState(travelMode.settings.positionSizeCapPct);
  const [riskCap, setRiskCap] = useState(travelMode.settings.dailyRiskCapPct);
  const [sensitivity, setSensitivity] = useState<NotificationSensitivity>(travelMode.settings.notificationSensitivity);
  const [autoEnabled, setAutoEnabled] = useState(travelMode.settings.autoActivateEnabled);
  const [autoMinutes, setAutoMinutes] = useState(travelMode.settings.autoActivateAfterMinutes);

  const [toggling, setToggling] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastBriefing, setLastBriefing] = useState<TravelModeBriefing | null>(null);

  useEffect(() => {
    setPositionCap(travelMode.settings.positionSizeCapPct);
    setRiskCap(travelMode.settings.dailyRiskCapPct);
    setSensitivity(travelMode.settings.notificationSensitivity);
    setAutoEnabled(travelMode.settings.autoActivateEnabled);
    setAutoMinutes(travelMode.settings.autoActivateAfterMinutes);
  }, [travelMode.settings]);

  const hasPendingChange =
    positionCap !== travelMode.settings.positionSizeCapPct ||
    riskCap !== travelMode.settings.dailyRiskCapPct ||
    sensitivity !== travelMode.settings.notificationSensitivity ||
    autoEnabled !== travelMode.settings.autoActivateEnabled ||
    autoMinutes !== travelMode.settings.autoActivateAfterMinutes;

  async function toggle() {
    setError(null);
    setToggling(true);
    try {
      if (travelMode.active) {
        const briefing = await api.deactivateTravelMode();
        setLastBriefing(briefing);
      } else {
        await api.activateTravelMode();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setToggling(false);
    }
  }

  async function saveSettings() {
    setError(null);
    setSaving(true);
    try {
      await api.updateTravelModeSettings({
        positionSizeCapPct: positionCap,
        dailyRiskCapPct: riskCap,
        notificationSensitivity: sensitivity,
        autoActivateEnabled: autoEnabled,
        autoActivateAfterMinutes: autoMinutes,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Travel Mode — reduce capital exposure while the CEO is away</TerminalLabel>
          {travelMode.active && (
            <StatusPill tone="amber">{travelMode.activationSource === "auto_inactivity" ? "AUTO-ACTIVATED" : "ACTIVE"}</StatusPill>
          )}
        </div>
        {travelMode.active && travelMode.activatedAt && (
          <div className="mb-2 text-[9px] text-cmd-textDim">Active since {new Date(travelMode.activatedAt).toLocaleString()}.</div>
        )}
        <button
          type="button"
          onClick={toggle}
          disabled={toggling}
          className={`rounded-sm border px-2.5 py-1 text-[9px] uppercase tracking-wide disabled:opacity-50 ${
            travelMode.active
              ? "border-cmd-green/50 text-cmd-green hover:bg-cmd-green/10"
              : "border-cmd-amber/50 text-cmd-amber hover:bg-cmd-amber/10"
          }`}
        >
          {toggling ? "Working…" : travelMode.active ? "Return to Full Operations" : "Activate Travel Mode"}
        </button>
        {error && <div className="mt-2 text-[9px] text-cmd-red">{error}</div>}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Posture Settings — composes with the Daily Circuit Breaker, never a duplicate override</TerminalLabel>
        <label className="mb-2 block text-[9px] text-cmd-textDim">
          Position Size Cap: {positionCap.toFixed(0)}% of normal
          <input
            type="range"
            min={25}
            max={75}
            step={5}
            value={positionCap}
            onChange={(e) => setPositionCap(Number(e.target.value))}
            className="mt-1 w-full accent-cmd-amber"
          />
        </label>
        <label className="mb-2 block text-[9px] text-cmd-textDim">
          Daily Risk Cap: {riskCap.toFixed(0)}% of normal
          <input
            type="range"
            min={25}
            max={75}
            step={5}
            value={riskCap}
            onChange={(e) => setRiskCap(Number(e.target.value))}
            className="mt-1 w-full accent-cmd-amber"
          />
        </label>
        <label className="mb-2 block text-[9px] text-cmd-textDim">
          Notification Sensitivity
          <div className="mt-1 flex flex-wrap gap-1.5">
            {(Object.keys(SENSITIVITY_LABEL) as NotificationSensitivity[]).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setSensitivity(s)}
                className={`rounded-sm border px-2.5 py-1 text-[9px] uppercase tracking-wide ${
                  sensitivity === s ? "border-cmd-cyan/60 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
                }`}
              >
                {SENSITIVITY_LABEL[s]}
              </button>
            ))}
          </div>
          <span className="mt-0.5 block text-cmd-textDim">Critical alerts always interrupt, regardless of this setting.</span>
        </label>
        <label className="mb-2 flex items-center gap-2 text-[9px] text-cmd-textDim">
          <input type="checkbox" checked={autoEnabled} onChange={(e) => setAutoEnabled(e.target.checked)} className="accent-cmd-cyan" />
          Auto-activate after inactivity — a real, measured signal (this codebase has no calendar/wall-clock concept), not a fabricated schedule
        </label>
        {autoEnabled && (
          <label className="mb-2 block text-[9px] text-cmd-textDim">
            Inactivity Threshold: {autoMinutes} simulated minute(s)
            <input
              type="range"
              min={15}
              max={240}
              step={15}
              value={autoMinutes}
              onChange={(e) => setAutoMinutes(Number(e.target.value))}
              className="mt-1 w-full accent-cmd-cyan"
            />
          </label>
        )}
        {hasPendingChange && (
          <button
            type="button"
            onClick={saveSettings}
            disabled={saving}
            className="rounded-sm border border-cmd-cyan/50 px-2.5 py-1 text-[9px] uppercase tracking-wide text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Apply Settings"}
          </button>
        )}
      </Glass>

      {(lastBriefing || travelModeBriefings.length > 0) && (
        <Glass className="p-3">
          <TerminalLabel>Return-to-Operations Briefings — built from real records in the exact activation window</TerminalLabel>
          <div className="max-h-72 space-y-1.5 overflow-y-auto">
            {[...(lastBriefing && !travelModeBriefings.some((b) => b.id === lastBriefing.id) ? [lastBriefing] : []), ...travelModeBriefings]
              .reverse()
              .map((b) => (
                <div key={b.id} className="border-b border-cmd-border/50 pb-1.5 last:border-0 text-[9px]">
                  <div className="mb-0.5 flex items-center gap-1.5">
                    <StatusPill tone={b.activationSource === "auto_inactivity" ? "amber" : "cyan"}>
                      {b.activationSource === "auto_inactivity" ? "Auto-Activated" : "Manual"}
                    </StatusPill>
                    <span className="text-cmd-textDim">{new Date(b.deactivatedAt).toLocaleString()}</span>
                  </div>
                  <p className="text-cmd-text">{b.summary}</p>
                  <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5 sm:grid-cols-4">
                    <DataRow label="Decisions" value={b.decisionsResolved} />
                    <DataRow label="Rejections" value={b.gatekeeperRejections} />
                    <DataRow label="Critical Warnings" value={b.criticalRiskWarnings} />
                    <DataRow label="Realized P&L" value={`${b.realizedPnl >= 0 ? "+" : ""}${b.realizedPnl.toFixed(0)}`} valueClassName={b.realizedPnl >= 0 ? "text-cmd-green" : "text-cmd-red"} />
                  </div>
                </div>
              ))}
          </div>
        </Glass>
      )}
      {!lastBriefing && travelModeBriefings.length === 0 && (
        <Glass className="p-3">
          <TerminalLabel>Return-to-Operations Briefings</TerminalLabel>
          <EmptyState>No Travel Mode activation has ended yet.</EmptyState>
        </Glass>
      )}
    </div>
  );
}
