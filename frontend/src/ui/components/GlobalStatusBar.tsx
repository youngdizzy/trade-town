import { useGameStore } from "@/ui/hooks/useGameStore";
import type { CompanyHealthTier, MarketEnvironmentRegime, OperatingMode } from "@/types";
import { EventBus } from "@/game/systems/EventBus";
import { RISK_LEVEL_LABEL, riskLevel } from "./CommandCenter/lib/derive";

/**
 * Design Bible Chapter 67 (TTOS) Part 3 — the "always-visible broker-
 * status/risk-status/capital-status/company-health strip" the chapter's
 * own Safety Systems section named as genuinely missing (Risk Status,
 * Company Health, and Market Environment were previously real but only
 * shown inside OverviewPanel/QuickView, not persistent from every
 * scene). A second row below TopStatusBar.tsx. Every value here is read
 * straight off gameStore — nothing here computes a new number; risk
 * level reuses lib/derive.ts's own riskLevel() rather than
 * re-implementing the Sentinel/Guardian severity bucket. Connection
 * status is deliberately left in TopStatusBar's own dot, not duplicated
 * here. Broker Status is honestly static — "SIMULATED" — since no live
 * broker integration exists anywhere in this codebase (see
 * app/broker.py's own module docstring); it does not read a real field
 * because there is no real field, and inventing one would violate this
 * project's no-fabrication rule. "Portfolio Health" is this codebase's
 * real Portfolio Heat reading (cool/warm/hot/overheated) — the closest
 * existing signal to that name; it is intentionally NOT relabeled to
 * "Health" in the pill itself, to stay honest about what it actually
 * measures (see PortfolioIntelPanel.tsx's own "a reading, never an
 * automatic action" framing).
 *
 * CEO directive "Command Center + Professional Quant Trading Firm
 * Upgrade," Phase 2 (Top Command Center Bar) — added P&L
 * (paperPortfolio.totalPnlPct, the same real field PerformancePanel/
 * OverviewPanel already read) and EMERGENCY STOP (emergencyStop.active,
 * the same real GameSaveState.emergency_stop field RiskPanel's own
 * activation control reads). The Emergency Stop pill is clickable — it
 * jumps straight to the RISK tab via the same real ui:commandCenterJump
 * event QuickActionDock/CommandPalette already use, never a second,
 * parallel activation control (the only real activate/resume flow
 * stays RiskPanel's own EmergencyStopControl/EmergencyStopConfirm).
 */
const RISK_TONE: Record<"green" | "yellow" | "red", string> = {
  green: "text-bullish",
  yellow: "text-gold",
  red: "text-bearish",
};

const HEALTH_TONE: Record<CompanyHealthTier, string> = {
  excellent: "text-bullish",
  good: "text-bullish",
  stable: "text-parchment",
  needs_attention: "text-gold",
  critical: "text-bearish",
};

const HEAT_TONE: Record<"cool" | "warm" | "hot" | "overheated", string> = {
  cool: "text-parchment",
  warm: "text-bullish",
  hot: "text-gold",
  overheated: "text-bearish",
};

const REGIME_TONE: Record<MarketEnvironmentRegime, string> = {
  bull: "text-bullish",
  bear: "text-bearish",
  sideways: "text-parchment",
  high_volatility: "text-gold",
  low_volatility: "text-parchment",
};

const MODE_LABEL: Record<OperatingMode, string> = { learning: "LEARNING", assisted: "ASSISTED", executive: "EXECUTIVE" };

function StatusItem({
  label,
  value,
  tone,
  title,
  hideOnMobile = false,
  onClick,
}: {
  label: string;
  value: string;
  tone: string;
  title: string;
  /** Design Bible Chapter 73.5 — this row wraps into extra lines once
   * enough items exceed a narrow viewport's width, which pushed the row
   * tall enough to collide with CyberNotifications' toast stack below
   * it. RISK/COMPANY HEALTH/PORTFOLIO stay visible everywhere (the
   * user's own mobile-priority ordering); the remaining four are one tap
   * away in the Command Center's OVERVIEW tab. */
  hideOnMobile?: boolean;
  /** Phase 2 Top Bar — when present, the item becomes a real button
   * (e.g. Emergency Stop jumping straight to the RISK tab) rather than
   * a passive readout. */
  onClick?: () => void;
}) {
  const content = (
    <>
      <span className="opacity-60">{label}</span>
      <span className={`font-bold ${tone}`}>{value}</span>
    </>
  );
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={`items-center gap-1.5 ${hideOnMobile ? "hidden sm:flex" : "flex"}`}
        title={title}
      >
        {content}
      </button>
    );
  }
  return (
    <div className={`items-center gap-1.5 ${hideOnMobile ? "hidden sm:flex" : "flex"}`} title={title}>
      {content}
    </div>
  );
}

export function GlobalStatusBar() {
  const { riskWarnings, companyHealth, marketEnvironment, portfolioIntelligence, settings, currentScene, paperPortfolio, emergencyStop } =
    useGameStore();
  const inGame = currentScene !== "MainMenuScene";
  if (!inGame) return null;

  const level = riskLevel(riskWarnings);
  const pnlPositive = paperPortfolio.totalPnlPct >= 0;

  return (
    <div className="pointer-events-none absolute left-0 right-0 top-11 flex justify-center px-4">
      <div className="pointer-events-auto flex flex-wrap items-center gap-x-4 gap-y-1 rounded bg-panel/80 px-3 py-1 font-pixel text-[9px] text-parchment shadow-pixel">
        <StatusItem label="RISK" value={RISK_LEVEL_LABEL[level]} tone={RISK_TONE[level]} title="Real-time Sentinel/Guardian risk severity" />
        <StatusItem
          label="P&L"
          value={`${pnlPositive ? "+" : ""}${paperPortfolio.totalPnlPct.toFixed(1)}%`}
          tone={pnlPositive ? "text-bullish" : "text-bearish"}
          title={`Total real P&L — $${paperPortfolio.totalPnl.toFixed(2)} on $${paperPortfolio.startingBalance.toFixed(2)} starting capital`}
        />
        {emergencyStop.active && (
          <StatusItem
            label="EMERGENCY STOP"
            value="ACTIVE"
            tone="text-bearish"
            title="Emergency Stop is active — click to open Risk Controls"
            onClick={() => EventBus.emit("ui:commandCenterJump", { tab: "RISK" })}
          />
        )}
        <StatusItem
          label="COMPANY HEALTH"
          value={`${Math.round(companyHealth.overall)}`}
          tone={HEALTH_TONE[companyHealth.tier]}
          title={`Company Health tier: ${companyHealth.tier.replace("_", " ")}`}
        />
        <StatusItem
          label="PORTFOLIO"
          value={portfolioIntelligence.heat.tier.toUpperCase()}
          tone={HEAT_TONE[portfolioIntelligence.heat.tier]}
          title="Portfolio Heat — total capital at risk reading, never an automatic action"
        />
        <StatusItem
          label="MARKET"
          value={marketEnvironment.label}
          tone={REGIME_TONE[marketEnvironment.current]}
          title={marketEnvironment.detail}
          hideOnMobile
        />
        <StatusItem
          label="AUTOMATION"
          value={MODE_LABEL[settings.operatingMode]}
          tone="text-parchment"
          title="Company Operating Mode (COMPANY tab)"
          hideOnMobile
        />
        <StatusItem
          label="DEPLOYED"
          value={`${Math.round(portfolioIntelligence.deployedPctOfEquity)}%`}
          tone="text-parchment"
          title="Capital deployed as % of equity"
          hideOnMobile
        />
        <StatusItem
          label="BROKER"
          value="SIMULATED"
          tone="text-parchment/70"
          title="Paper trading only — no live broker integration exists (app/broker.py)"
          hideOnMobile
        />
      </div>
    </div>
  );
}
