import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { TradeDecision } from "@/types";
import { aiStatus, riskLevel } from "./lib/derive";
import { RiskDot, StatusPill } from "./ui";
import { OverviewPanel } from "./panels/OverviewPanel";
import { OpportunitiesPanel } from "./panels/OpportunitiesPanel";
import { DecisionsPanel } from "./panels/DecisionsPanel";
import { RiskPanel } from "./panels/RiskPanel";
import { AgentsPanel } from "./panels/AgentsPanel";
import { ResearchPanel } from "./panels/ResearchPanel";
import { PerformancePanel } from "./panels/PerformancePanel";
import { LogsPanel } from "./panels/LogsPanel";
import { CalibrationPanel } from "./panels/CalibrationPanel";
import { PlayerVsAiPanel } from "./panels/PlayerVsAiPanel";
import { DecisionDetail } from "./DecisionDetail";

const TABS = ["OVERVIEW", "OPPORTUNITIES", "DECISIONS", "RISK", "AGENTS", "RESEARCH", "TRAINING", "PVAI", "PERFORMANCE", "LOGS"] as const;
type Tab = (typeof TABS)[number];

export function FullCommandCenter({ onCollapse, onClose }: { onCollapse: () => void; onClose: () => void }) {
  const { time, riskWarnings, research, agents } = useGameStore();
  const [tab, setTab] = useState<Tab>("OVERVIEW");
  const [inspecting, setInspecting] = useState<TradeDecision | null>(null);

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
        {tab === "DECISIONS" && <DecisionsPanel onInspect={setInspecting} />}
        {tab === "RISK" && <RiskPanel />}
        {tab === "AGENTS" && <AgentsPanel />}
        {tab === "RESEARCH" && <ResearchPanel />}
        {tab === "TRAINING" && <CalibrationPanel />}
        {tab === "PVAI" && <PlayerVsAiPanel />}
        {tab === "PERFORMANCE" && <PerformancePanel />}
        {tab === "LOGS" && <LogsPanel />}
      </div>

      {inspecting !== null && <DecisionDetail decision={inspecting} onClose={() => setInspecting(null)} />}
    </div>
  );
}

export type { Tab };
