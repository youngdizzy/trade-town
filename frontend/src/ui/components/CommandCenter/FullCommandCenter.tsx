import { useEffect, useState } from "react";
import { gameStore } from "@/state/gameStore";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { EventBus } from "@/game/systems/EventBus";
import type { EducationTopic, TradeDecision } from "@/types";
import { aiStatus, riskLevel } from "./lib/derive";
import { AREA_ORDER, areaForTab, groupTabsBySection, tabsForArea, type Area } from "./lib/navigation";
import { RiskDot, StatusPill } from "./ui";
import { MarketChartPanel } from "./MarketChartPanel";
import { OverviewPanel } from "./panels/OverviewPanel";
import { OpportunitiesPanel } from "./panels/OpportunitiesPanel";
import { DecisionsPanel } from "./panels/DecisionsPanel";
import { ReplayPanel } from "./panels/ReplayPanel";
import { SandboxPanel } from "./panels/SandboxPanel";
import { ConstitutionPanel } from "./panels/ConstitutionPanel";
import { KnowledgeBasePanel } from "./panels/KnowledgeBasePanel";
import { ExecutivePanel } from "./panels/ExecutivePanel";
import { RiskPanel } from "./panels/RiskPanel";
import { AgentsPanel } from "./panels/AgentsPanel";
import { ResearchPanel } from "./panels/ResearchPanel";
import { PerformancePanel } from "./panels/PerformancePanel";
import { LogsPanel } from "./panels/LogsPanel";
import { CalibrationPanel } from "./panels/CalibrationPanel";
import { PlayerVsAiPanel } from "./panels/PlayerVsAiPanel";
import { EducationPanel } from "./panels/EducationPanel";
import { CompanyPanel } from "./panels/CompanyPanel";
import { ExecutiveIntelPanel } from "./panels/ExecutiveIntelPanel";
import { MarketIntelPanel } from "./panels/MarketIntelPanel";
import { AcademyPanel } from "./panels/AcademyPanel";
import { DisciplinePanel } from "./panels/DisciplinePanel";
import { DecisionVaultPanel } from "./panels/DecisionVaultPanel";
import { WarRoomPanel } from "./panels/WarRoomPanel";
import { PortfolioIntelPanel } from "./panels/PortfolioIntelPanel";
import { BlackSwanPanel } from "./panels/BlackSwanPanel";
import { EconomicIntelPanel } from "./panels/EconomicIntelPanel";
import { PanelErrorBoundary } from "./PanelErrorBoundary";
import { ReasoningLabPanel } from "./panels/ReasoningLabPanel";
import { ReflectionPanel } from "./panels/ReflectionPanel";
import { MentorPanel } from "./panels/MentorPanel";
import { MentorLibraryPanel } from "./panels/MentorLibraryPanel";
import { MentorLabPanel } from "./panels/MentorLabPanel";
import { TalentPanel } from "./panels/TalentPanel";
import { FoundersPanel } from "./panels/FoundersPanel";
import { TreasuryPanel } from "./panels/TreasuryPanel";
import { CalendarPanel } from "./panels/CalendarPanel";
import { BlackBoxPanel } from "./panels/BlackBoxPanel";
import { CompliancePanel } from "./panels/CompliancePanel";
import { TradingModesPanel } from "./panels/TradingModesPanel";
import { PsychologyDashboardPanel } from "./panels/PsychologyDashboardPanel";
import { EvolutionPanel } from "./panels/EvolutionPanel";
import { SituationRoomPanel } from "./panels/SituationRoomPanel";
import { TravelModePanel } from "./panels/TravelModePanel";
import { DecisionDetail } from "./DecisionDetail";

// Design Bible Chapter 67 (TradeTown Operating System) — Phase 1: the
// 34 tabs below now render grouped into TTOS's 7 permanent sections
// (see ./lib/navigation.ts for the section mapping and the reasoning
// behind each judgment call). This TABS array itself, and every tab's
// button text, are intentionally untouched by that change — the
// number-key 1-9 shortcut below indexes into this array positionally,
// and frontend/tests/helpers.ts's clickTab() looks buttons up by exact
// accessible name, so renaming or reordering anything here would ripple
// into the whole Playwright suite for zero real user benefit.
//
// Note: "ACADEMY" (below) is the pre-existing v0.6.2 Trading Academy tab
// (EducationPanel — lesson/quiz curriculum). v0.7 Feature 25's AI Academy
// & Knowledge Network is a different system entirely (per-agent
// Knowledge Points, research projects, the Company Knowledge Library —
// see AcademyPanel.tsx) and gets its own "KNOWLEDGE" tab rather than
// colliding with the existing name. v0.7 Feature 47's Company Operating
// System — the "Knowledge Base" — gets its own "OPS" tab for the same
// reason: it's a flat, filterable timeline over six real learning
// sources (see KnowledgeBasePanel.tsx), distinct from KNOWLEDGE's
// relational graph. "MENTOR" is Sage, the single always-available
// Socratic Q&A advisor (MentorPanel.tsx); v0.7 Feature 49's Foundational
// Mentor Program is a different system entirely — a roadmap of named-
// track lesson/quiz curricula (see MentorLibraryPanel.tsx) — and gets
// its own "MENTORLIB" tab rather than colliding with MENTOR. The Command
// Center UI Revision brief asked for this dashboard to be relabeled
// "ACADEMY", but that name is already the pre-existing Trading Academy
// tab above, so MENTORLIB keeps its name (it already functions as the
// employees'-progress dashboard the brief describes) and a new
// "MENTORLAB" tab is added alongside it for CEO custom-mentor/lesson
// authoring (see MentorLabPanel.tsx). The brief's third tab, "TRAINING",
// is also already a distinct pre-existing system (CalibrationPanel's
// Signal Calibration mini-game) and is left untouched — its content
// overlaps with the real backtesting/paper-trading pipeline already on
// the SANDBOX tab, so no changes were made there for this revision.
const TABS = [
  "OVERVIEW",
  "OPPORTUNITIES",
  "EXECUTIVE",
  "DECISIONS",
  "REPLAY",
  "RISK",
  "BLACKSWAN",
  "AGENTS",
  "RESEARCH",
  "COMPANY",
  "EXECINTEL",
  "MARKETCHART",
  "MARKETINTEL",
  "ECONINTEL",
  "KNOWLEDGE",
  "DISCIPLINE",
  "VAULT",
  "WARROOM",
  "PORTFOLIO",
  "REASONING",
  "REFLECTION",
  "MENTOR",
  "MENTORLIB",
  "MENTORLAB",
  "TALENT",
  "SANDBOX",
  "CONSTITUTION",
  "OPS",
  "FOUNDERS",
  "TREASURY",
  "CALENDAR",
  "BLACKBOX",
  "TRAINING",
  "PVAI",
  "ACADEMY",
  "PERFORMANCE",
  "LOGS",
  "COMPLIANCE",
  "TRADINGMODES",
  "SITUATIONROOM",
  "TRAVELMODE",
  "EVOLUTION",
  "PSYCHOLOGY",
] as const;
type Tab = (typeof TABS)[number];

export function FullCommandCenter({ onCollapse, onClose }: { onCollapse: () => void; onClose: () => void }) {
  const { time, riskWarnings, research, agents, decisions, pendingInspectDecision, pendingCommandCenterTab } = useGameStore();
  const [tab, setTab] = useState<Tab>("OVERVIEW");
  const [inspecting, setInspecting] = useState<TradeDecision | null>(null);
  const [helpLessonId, setHelpLessonId] = useState<EducationTopic | null>(null);

  // v0.7 Feature 19 — the trade outcome banner's View Trade/Analyze buttons
  // request a jump straight to a specific decision via gameStore.
  useEffect(() => {
    if (!pendingInspectDecision) return;
    setTab("DECISIONS");
    if (pendingInspectDecision.openDetail) {
      const match = decisions.find((d) => d.id === pendingInspectDecision.decisionId) ?? null;
      setInspecting(match);
    }
    gameStore.clearPendingInspectDecision();
  }, [pendingInspectDecision, decisions]);

  // Design Bible Chapter 67 (TTOS) Part 3 — the Quick Action Dock's
  // quick-jump buttons request a jump straight to a tab via gameStore,
  // same pattern as pendingInspectDecision above. Validated against the
  // real TABS list since the event payload is a bare string, not this
  // file's own Tab union (see EventBus.ts's own note on why).
  useEffect(() => {
    if (!pendingCommandCenterTab) return;
    if ((TABS as readonly string[]).includes(pendingCommandCenterTab)) {
      setTab(pendingCommandCenterTab as Tab);
    }
    gameStore.clearPendingCommandCenterTab();
  }, [pendingCommandCenterTab]);

  // v0.7 Feature 34, updated for the Phase 2 IA consolidation — number
  // keys 1-6 now jump straight to one of the six top-level areas'
  // default tab (AREA_ORDER's own order: 1=OVERVIEW, 2=MARKETS,
  // 3=AI DESK, 4=PORTFOLIO & RISK, 5=RESEARCH & INTELLIGENCE, 6=MORE),
  // the same real area-jump clicking one of the six primary buttons
  // already performs. Was 1-9 indexing the old flat 42-tab list
  // positionally; six real destinations is what the new IA actually
  // has. Ignored while typing in a form control so it never fights a
  // text/number input's own digits (Treasury's amount field, Company
  // Priority's fast-forward hours, ...).
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      const digit = Number(e.key);
      if (!Number.isInteger(digit) || digit < 1 || digit > AREA_ORDER.length) return;
      const area = AREA_ORDER[digit - 1];
      if (!area) return;
      const firstTab = tabsForArea(area, TABS)[0];
      if (firstTab) setTab(firstTab);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const needHelp = (lessonId: EducationTopic) => {
    setHelpLessonId(lessonId);
    setTab("ACADEMY");
  };

  const level = riskLevel(riskWarnings);
  const status = aiStatus(riskWarnings, research, agents);

  return (
    <div className="flex h-full flex-col">
      {/* Design Bible Chapter 73.5 — flex-wrap so a narrow/mobile viewport
          wraps the status/action cluster onto its own row instead of
          overflowing past the edge, which would push CLOSE (the one
          control that must always stay reachable to exit) off-screen.
          Buttons get a 44px minimum touch target below `sm`, unchanged
          on desktop. */}
      <header className="flex flex-wrap items-center justify-between gap-y-2 border-b border-cmd-border px-4 py-2.5">
        <div className="flex items-center gap-3">
          <span className="tracking-[0.2em] text-cmd-cyan">COMMAND CENTER</span>
          <span className="text-cmd-textDim">
            Day {time.day} · {String(time.hour).padStart(2, "0")}:{String(time.minute).padStart(2, "0")}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <StatusPill tone={status === "RISK LOCK" ? "red" : status === "ANALYZING" ? "cyan" : status === "ACTIVE" ? "green" : "neutral"}>{status}</StatusPill>
          <span className="flex items-center gap-1">
            <RiskDot level={level} />
          </span>
          <button
            type="button"
            onClick={() => EventBus.emit("ui:campusMap", { open: true })}
            className="hidden min-h-[44px] rounded-sm border border-cmd-border px-2.5 py-1 text-cmd-textDim transition-colors hover:border-cmd-cyan/50 hover:text-cmd-cyan sm:flex sm:min-h-0 sm:items-center"
            title="Company Campus Map (M)"
          >
            🗺 CAMPUS
          </button>
          <button
            type="button"
            onClick={onCollapse}
            className="flex min-h-[44px] items-center rounded-sm border border-cmd-border px-2.5 py-1 text-cmd-textDim transition-colors hover:border-cmd-cyan/50 hover:text-cmd-cyan sm:min-h-0"
          >
            QUICK VIEW
          </button>
          <button
            type="button"
            onClick={onClose}
            className="flex min-h-[44px] items-center rounded-sm border border-cmd-border px-2.5 py-1 text-cmd-textDim transition-colors hover:border-cmd-red/50 hover:text-cmd-red sm:min-h-0"
          >
            CLOSE ✕
          </button>
        </div>
      </header>

      <CommandCenterNav tab={tab} setTab={setTab} />

      <div className="flex-1 overflow-y-auto p-4">
        <PanelErrorBoundary key={tab} panelName={tab}>
        {tab === "OVERVIEW" && <OverviewPanel onInspect={setInspecting} onNavigate={setTab} />}
        {tab === "OPPORTUNITIES" && <OpportunitiesPanel onInspect={setInspecting} />}
        {tab === "EXECUTIVE" && <ExecutivePanel />}
        {tab === "DECISIONS" && <DecisionsPanel onInspect={setInspecting} />}
        {tab === "REPLAY" && <ReplayPanel />}
        {tab === "RISK" && <RiskPanel onNeedHelp={needHelp} />}
        {tab === "BLACKSWAN" && <BlackSwanPanel />}
        {tab === "AGENTS" && <AgentsPanel />}
        {tab === "RESEARCH" && <ResearchPanel />}
        {tab === "COMPANY" && <CompanyPanel />}
        {tab === "EXECINTEL" && <ExecutiveIntelPanel />}
        {tab === "MARKETCHART" && <MarketChartPanel />}
        {tab === "MARKETINTEL" && <MarketIntelPanel />}
        {tab === "ECONINTEL" && <EconomicIntelPanel />}
        {tab === "KNOWLEDGE" && <AcademyPanel />}
        {tab === "DISCIPLINE" && <DisciplinePanel />}
        {tab === "VAULT" && <DecisionVaultPanel />}
        {tab === "WARROOM" && <WarRoomPanel />}
        {tab === "PORTFOLIO" && <PortfolioIntelPanel />}
        {tab === "REASONING" && <ReasoningLabPanel />}
        {tab === "REFLECTION" && <ReflectionPanel />}
        {tab === "MENTOR" && <MentorPanel />}
        {tab === "MENTORLIB" && <MentorLibraryPanel />}
        {tab === "MENTORLAB" && <MentorLabPanel />}
        {tab === "TALENT" && <TalentPanel />}
        {tab === "SANDBOX" && <SandboxPanel />}
        {tab === "CONSTITUTION" && <ConstitutionPanel />}
        {tab === "OPS" && <KnowledgeBasePanel />}
        {tab === "FOUNDERS" && <FoundersPanel />}
        {tab === "TREASURY" && <TreasuryPanel />}
        {tab === "BLACKBOX" && <BlackBoxPanel />}
        {tab === "CALENDAR" && <CalendarPanel />}
        {tab === "TRAINING" && <CalibrationPanel onNeedHelp={needHelp} />}
        {tab === "PVAI" && <PlayerVsAiPanel />}
        {tab === "ACADEMY" && <EducationPanel openLessonId={helpLessonId} />}
        {tab === "PERFORMANCE" && <PerformancePanel />}
        {tab === "LOGS" && <LogsPanel />}
        {tab === "COMPLIANCE" && <CompliancePanel />}
        {tab === "TRADINGMODES" && <TradingModesPanel />}
        {tab === "SITUATIONROOM" && <SituationRoomPanel />}
        {tab === "TRAVELMODE" && <TravelModePanel />}
        {tab === "EVOLUTION" && <EvolutionPanel />}
        {tab === "PSYCHOLOGY" && <PsychologyDashboardPanel />}
        </PanelErrorBoundary>
      </div>

      {inspecting !== null && <DecisionDetail decision={inspecting} onClose={() => setInspecting(null)} />}
    </div>
  );
}

/**
 * CEO directive "TradeTown — Command Center + Professional Quant
 * Trading Firm Upgrade," Phase 2 — the two-tier navigation this
 * chapter's IA consolidation calls for: six primary destinations
 * (OVERVIEW / MARKETS / AI DESK / PORTFOLIO & RISK / RESEARCH &
 * INTELLIGENCE / MORE), each showing its own real member tabs below it
 * — see lib/navigation.ts's AREA_ORDER/tabsForArea/areaForTab for the
 * real, documented placement of every one of the 42 real tabs. No tab
 * was deleted or renamed; this is purely a new outer grouping layer.
 */
function CommandCenterNav({ tab, setTab }: { tab: Tab; setTab: (tab: Tab) => void }) {
  const activeArea = areaForTab(tab);
  const secondaryTabs = tabsForArea(activeArea, TABS);

  return (
    <nav className="flex max-h-[45vh] flex-col border-b border-cmd-border bg-cmd-panel/60">
      <div className="flex flex-wrap items-center gap-1 border-b border-cmd-border/60 px-3 py-1.5">
        {AREA_ORDER.map((area) => (
          <button
            key={area}
            type="button"
            onClick={() => {
              const firstTab = tabsForArea(area, TABS)[0];
              if (firstTab) setTab(firstTab);
            }}
            className={`min-h-[40px] whitespace-nowrap rounded-sm px-3 py-1.5 tracking-wide transition-colors sm:min-h-0 ${
              activeArea === area ? "border border-cmd-cyan/40 bg-cmd-cyan/10 text-cmd-cyan shadow-cmd-cyan" : "border border-transparent text-cmd-textDim hover:text-cmd-text"
            }`}
          >
            {area}
          </button>
        ))}
      </div>

      {activeArea === "MORE" ? (
        <div className="flex flex-col gap-1 overflow-y-auto px-3 py-1.5">
          {groupTabsBySection(secondaryTabs).map(({ section, tabs: sectionTabs }) => (
            <div key={section} className="flex flex-wrap items-center gap-1">
              <span className="mr-1 w-[104px] shrink-0 text-[10px] tracking-[0.15em] text-cmd-textDim/70">{section}</span>
              {sectionTabs.map((t) => (
                <TabButton key={t} label={t} active={tab === t} onClick={() => setTab(t)} />
              ))}
            </div>
          ))}
        </div>
      ) : (
        secondaryTabs.length > 1 && (
          <div className="flex flex-wrap items-center gap-1 overflow-y-auto px-3 py-1.5">
            {secondaryTabs.map((t) => (
              <TabButton key={t} label={t} active={tab === t} onClick={() => setTab(t)} />
            ))}
          </div>
        )
      )}
    </nav>
  );
}

function TabButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-[40px] whitespace-nowrap rounded-sm px-3 py-1.5 tracking-wide transition-colors sm:min-h-0 ${
        active ? "border border-cmd-cyan/40 bg-cmd-cyan/10 text-cmd-cyan shadow-cmd-cyan" : "border border-transparent text-cmd-textDim hover:text-cmd-text"
      }`}
    >
      {label}
    </button>
  );
}

export type { Tab };
export type { Area };
