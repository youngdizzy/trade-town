import { useEffect, useState } from "react";
import { gameStore } from "@/state/gameStore";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { EventBus } from "@/game/systems/EventBus";
import type { EducationTopic, TradeDecision } from "@/types";
import { aiStatus, riskLevel } from "./lib/derive";
import { RiskDot, StatusPill } from "./ui";
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
import { DecisionDetail } from "./DecisionDetail";

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
  "AGENTS",
  "RESEARCH",
  "COMPANY",
  "EXECINTEL",
  "MARKETINTEL",
  "KNOWLEDGE",
  "DISCIPLINE",
  "VAULT",
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
] as const;
type Tab = (typeof TABS)[number];

export function FullCommandCenter({ onCollapse, onClose }: { onCollapse: () => void; onClose: () => void }) {
  const { time, riskWarnings, research, agents, decisions, pendingInspectDecision } = useGameStore();
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

  // v0.7 Feature 34 — number keys 1-9 jump straight to the first nine
  // tabs, the same real switch-tab action clicking one already performs.
  // Ignored while typing in a form control so it never fights a text/
  // number input's own digits (Treasury's amount field, Company
  // Priority's fast-forward hours, ...).
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      const digit = Number(e.key);
      if (!Number.isInteger(digit) || digit < 1 || digit > 9) return;
      const nextTab = TABS[digit - 1];
      if (nextTab) setTab(nextTab);
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
      <header className="flex items-center justify-between border-b border-cmd-border px-4 py-2.5">
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
            className="rounded-sm border border-cmd-border px-2.5 py-1 text-cmd-textDim transition-colors hover:border-cmd-cyan/50 hover:text-cmd-cyan"
            title="Company Campus Map (M)"
          >
            🗺 CAMPUS
          </button>
          <button
            type="button"
            onClick={onCollapse}
            className="rounded-sm border border-cmd-border px-2.5 py-1 text-cmd-textDim transition-colors hover:border-cmd-cyan/50 hover:text-cmd-cyan"
          >
            QUICK VIEW
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-sm border border-cmd-border px-2.5 py-1 text-cmd-textDim transition-colors hover:border-cmd-red/50 hover:text-cmd-red"
          >
            CLOSE ✕
          </button>
        </div>
      </header>

      <nav className="flex gap-1 overflow-x-auto border-b border-cmd-border bg-cmd-panel/60 px-3 py-1.5">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`whitespace-nowrap rounded-sm px-3 py-1.5 tracking-wide transition-colors ${
              tab === t ? "border border-cmd-cyan/40 bg-cmd-cyan/10 text-cmd-cyan shadow-cmd-cyan" : "border border-transparent text-cmd-textDim hover:text-cmd-text"
            }`}
          >
            {t}
          </button>
        ))}
      </nav>

      <div className="flex-1 overflow-y-auto p-4">
        {tab === "OVERVIEW" && <OverviewPanel onInspect={setInspecting} onNavigate={setTab} />}
        {tab === "OPPORTUNITIES" && <OpportunitiesPanel onInspect={setInspecting} />}
        {tab === "EXECUTIVE" && <ExecutivePanel />}
        {tab === "DECISIONS" && <DecisionsPanel onInspect={setInspecting} />}
        {tab === "REPLAY" && <ReplayPanel />}
        {tab === "RISK" && <RiskPanel onNeedHelp={needHelp} />}
        {tab === "AGENTS" && <AgentsPanel />}
        {tab === "RESEARCH" && <ResearchPanel />}
        {tab === "COMPANY" && <CompanyPanel />}
        {tab === "EXECINTEL" && <ExecutiveIntelPanel />}
        {tab === "MARKETINTEL" && <MarketIntelPanel />}
        {tab === "KNOWLEDGE" && <AcademyPanel />}
        {tab === "DISCIPLINE" && <DisciplinePanel />}
        {tab === "VAULT" && <DecisionVaultPanel />}
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
      </div>

      {inspecting !== null && <DecisionDetail decision={inspecting} onClose={() => setInspecting(null)} />}
    </div>
  );
}

export type { Tab };
