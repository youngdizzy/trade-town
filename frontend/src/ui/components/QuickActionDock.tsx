import { useGameStore } from "@/ui/hooks/useGameStore";
import { EventBus } from "@/game/systems/EventBus";
import { SettingsManager } from "@/game/systems/SettingsManager";
import { useIsTouchDevice } from "@/ui/hooks/useIsTouchDevice";
import type { OperatingMode } from "@/types";

/**
 * Design Bible Chapter 67 (TTOS) Part 3 — the Quick Action Dock. The
 * brief asked for one surface consolidating Pause/Resume (Work Mode),
 * Automation Mode, Emergency Stop, and quick-jumps to Risk/Company
 * Health/Portfolio/Executive. Pause/Resume+Work Mode
 * (`BottomToolbar.tsx`) and Emergency Stop (`TopStatusBar.tsx`,
 * Chapter 67 Part 3's own earlier slice) are already real, global,
 * always-visible controls — this dock deliberately does not duplicate
 * their buttons a second time (this codebase's own "reuse, don't
 * duplicate" convention; physically merging three already-shipped,
 * independently-tested components into one for a cosmetic-only change
 * risks exactly the layout regressions this session already hit twice
 * with TopStatusBar). What genuinely was not global before this dock:
 * Automation Mode (Operating Mode), previously reachable only by
 * opening the Full Command Center and clicking into COMPANY, and
 * quick-jump buttons that open the Command Center directly on a real
 * tab instead of always defaulting to OVERVIEW.
 *
 * Visible labels below are deliberately prefixed ("→ Risk", not bare
 * "Risk") and this control's own accessible name is set via `aria-label`
 * distinct from its visible mode text. Both exist for the same reason:
 * "Risk", "Company Health", "Portfolio", "Executive", "LEARNING",
 * "ASSISTED", and "EXECUTIVE" are all real headings/labels/values that
 * legitimately already appear elsewhere in this 34-tab Command Center
 * (RiskPanel's own heading, CompanyPanel's own Operating Mode buttons,
 * GlobalStatusBar's own Automation pill, etc.) — since this dock, unlike
 * those, is *always* mounted (never conditionally rendered per tab), a
 * bare label here would create a real strict-mode collision the moment
 * any of those other real, correct instances is also on screen. Confirmed
 * by three real regressions this caused in the existing test suite
 * before this fix (commandCenter.spec.ts's Company tab / Operating Mode
 * tests, globalStatusBar.spec.ts's own AUTOMATION/LEARNING checks) —
 * fixed at the source here rather than patching every colliding
 * pre-existing test, since the underlying labels are genuinely reused
 * this many places across the app.
 */
const MODE_ORDER: OperatingMode[] = ["learning", "assisted", "executive"];
const MODE_LABEL: Record<OperatingMode, string> = { learning: "LEARNING", assisted: "ASSISTED", executive: "EXECUTIVE" };

const JUMPS: { label: string; tab: string }[] = [
  { label: "→ Risk", tab: "RISK" },
  { label: "→ Company Health", tab: "COMPANY" },
  { label: "→ Portfolio", tab: "PORTFOLIO" },
  { label: "→ Executive", tab: "EXECUTIVE" },
];

export function QuickActionDock() {
  const { settings, currentScene } = useGameStore();
  const isTouch = useIsTouchDevice();
  const inGame = currentScene !== "MainMenuScene";
  // Design Bible Chapter 73.5 — this dock's fixed bottom-right pixel
  // offset was never designed for a narrow viewport, and on touch
  // devices it now shares that screen region with the mobile joystick/
  // interact controls (MobileTouchControls.tsx) and BottomToolbar's
  // wrapped rows — every function here (mode cycle, tab quick-jumps) is
  // still one tap away inside the Command Center, the CEO's primary
  // mobile surface, so this convenience layer steps aside on touch
  // rather than risk covering a real control.
  if (!inGame || isTouch) return null;

  const cycleMode = () => {
    const next = MODE_ORDER[(MODE_ORDER.indexOf(settings.operatingMode) + 1) % MODE_ORDER.length];
    SettingsManager.update({ operatingMode: next });
  };

  return (
    <div className="pointer-events-none absolute bottom-16 right-3 flex flex-col items-end gap-1.5 font-pixel text-[10px] text-parchment">
      <div className="pointer-events-auto flex items-center gap-1.5 rounded bg-panel/90 px-2.5 py-1.5 shadow-pixel">
        <span className="opacity-60">MODE</span>
        <button
          type="button"
          onClick={cycleMode}
          aria-label={`Cycle Automation Mode (currently ${MODE_LABEL[settings.operatingMode]})`}
          title="Cycle Operating Mode — also changeable in the Command Center's COMPANY tab"
          className="rounded bg-panelLight px-2 py-1 text-gold shadow-pixel transition-colors hover:bg-gold hover:text-ink active:translate-y-px"
        >
          {MODE_LABEL[settings.operatingMode]}
        </button>
      </div>
      <div className="pointer-events-auto flex items-center gap-1.5 rounded bg-panel/90 px-2.5 py-1.5 shadow-pixel">
        <span className="opacity-60">JUMP</span>
        {JUMPS.map((j) => (
          <button
            key={j.tab}
            type="button"
            onClick={() => EventBus.emit("ui:commandCenterJump", { tab: j.tab })}
            className="rounded bg-panelLight px-2 py-1 text-parchment shadow-pixel transition-colors hover:bg-gold hover:text-ink active:translate-y-px"
          >
            {j.label}
          </button>
        ))}
      </div>
    </div>
  );
}
