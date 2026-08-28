import { useEffect, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_IDS } from "@/types";
import type { AgentTradingStatus, AgentTradingStatusRead, AgentVoteAccuracyScore } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { api } from "@/net/api";
import { EmptyState, Glass, Meter, StatusPill } from "../ui";

const TRADING_STATUS_TONE: Record<AgentTradingStatus, "neutral" | "cyan" | "green" | "amber" | "red" | "purple"> = {
  waiting: "amber",
  scanning: "cyan",
  idle: "neutral",
  risk_blocked: "red",
  not_trading_role: "purple",
};

// CEO directive "Professional Quant Trading Core," Phase B's per-agent
// learning follow-up — real vote-accuracy evidence exists for at most
// the six agents who ever actually cast an AnalystVote (see
// backend/app/executive.py's generate_analyst_votes). "pass"/"fail" use
// the same green/red convention as TRADING_STATUS_TONE above.
const ACCURACY_TONE: Record<AgentVoteAccuracyScore["evaluationState"], "green" | "amber" | "red" | "neutral"> = {
  pass: "green",
  inconclusive: "amber",
  fail: "red",
  not_enough_evidence: "neutral",
};

/** The nine-agent roster as a real status board — only fields TradeTown's backend actually tracks per agent (see AgentState in types.ts); no fabricated activity feed. */
export function AgentsPanel() {
  const { agents, tasks, research } = useGameStore();
  const [tradingStatus, setTradingStatus] = useState<Record<string, AgentTradingStatusRead>>({});
  const [voteAccuracy, setVoteAccuracy] = useState<Record<string, AgentVoteAccuracyScore>>({});

  // CEO directive "Command Center + Professional Quant Trading Firm
  // Upgrade," Phase 2 — real per-agent trading-status explainability
  // (backend/app/agent_trading_status.py). On-demand, not WS-broadcast,
  // same pattern this Command Center already uses elsewhere.
  useEffect(() => {
    api
      .getAgentTradingStatus()
      .then((reads) => setTradingStatus(Object.fromEntries(reads.map((r) => [r.agentId, r]))))
      .catch(() => undefined);
  }, []);

  // CEO directive "Professional Quant Trading Core," Phase B's per-agent
  // learning follow-up (backend/app/executive_intelligence.py's
  // compute_agent_vote_accuracy()). On-demand, same convention as above.
  useEffect(() => {
    api
      .getAgentVoteAccuracy()
      .then((reads) => setVoteAccuracy(Object.fromEntries(reads.map((r) => [r.agentId, r]))))
      .catch(() => undefined);
  }, []);

  if (!agents) return <EmptyState>Agent state hasn&apos;t loaded yet.</EmptyState>;

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
      {AGENT_IDS.map((id) => {
        const profile = AGENT_PROFILES[id];
        const state = agents[id];
        const latestTask = [...tasks].reverse().find((t) => t.owner === id) ?? null;
        const activeResearch = research.find((r) => r.assignedAgent === id && r.status === "in_progress") ?? null;
        const idle = state.location === "lobby" || state.location === "break-room";
        const trading = tradingStatus[id];
        const accuracy = voteAccuracy[id];

        return (
          <Glass key={id} className="p-3">
            <div className="mb-1 flex items-center justify-between">
              <div>
                <span className="font-cmdmono text-cmd-cyan">{profile.name}</span>
                <span className="ml-2 text-[9px] uppercase tracking-wide text-cmd-textDim">{profile.occupation}</span>
              </div>
              <span className={`text-[9px] uppercase ${idle ? "text-cmd-textDim" : "text-cmd-green"}`}>{idle ? "IDLE" : "WORKING"}</span>
            </div>

            {trading && (
              <div className="mb-1.5 rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="mb-0.5 flex items-center justify-between gap-2">
                  <StatusPill tone={TRADING_STATUS_TONE[trading.status]}>{trading.status.replace(/_/g, " ")}</StatusPill>
                  {trading.symbol && <span className="font-cmdmono text-cmd-cyan">{trading.symbol}</span>}
                </div>
                <div className="text-cmd-text">{trading.headline}</div>
                <div className="mt-0.5 text-cmd-textDim">{trading.detail}</div>
              </div>
            )}

            {accuracy && accuracy.decisionsTracked > 0 && (
              <div className="mb-1.5 flex items-center justify-between gap-2 rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                <span className="text-cmd-textDim">
                  Vote Accuracy ({accuracy.correctCount}/{accuracy.decisionsTracked})
                </span>
                <StatusPill tone={ACCURACY_TONE[accuracy.evaluationState]}>{accuracy.accuracyPct?.toFixed(0)}%</StatusPill>
              </div>
            )}

            <div className="mb-1.5 text-[9px] text-cmd-textDim">{state.location.replace("-", " ")}</div>

            <div className="mb-1.5">
              <div className="text-[9px] uppercase tracking-wide text-cmd-textDim">Current Task</div>
              <div className="truncate text-cmd-text">{state.currentTask}</div>
            </div>

            <div className="mb-1.5 grid grid-cols-2 gap-2">
              <div>
                <div className="mb-0.5 flex items-center justify-between text-[9px] text-cmd-textDim">
                  <span>Mood</span>
                  <span>{Math.round(state.mood)}</span>
                </div>
                <Meter value={state.mood} tone={state.mood < 35 ? "red" : state.mood < 65 ? "amber" : "green"} />
              </div>
              <div>
                <div className="mb-0.5 flex items-center justify-between text-[9px] text-cmd-textDim">
                  <span>Energy</span>
                  <span>{Math.round(state.energy)}</span>
                </div>
                <Meter value={state.energy} tone={state.energy < 35 ? "red" : state.energy < 65 ? "amber" : "cyan"} />
              </div>
            </div>

            <div className="border-t border-cmd-border/60 pt-1.5 text-[9px] text-cmd-textDim">
              {activeResearch !== null && (
                <div className="mb-0.5">
                  Researching <span className="text-cmd-text">{activeResearch.title}</span> — {Math.round(activeResearch.confidence)}% confidence
                </div>
              )}
              {latestTask !== null && (
                <div className="truncate">
                  Latest: {latestTask.description} <span className="opacity-70">[{latestTask.status}]</span>
                </div>
              )}
              {activeResearch === null && latestTask === null && <div>No recent activity logged.</div>}
            </div>
          </Glass>
        );
      })}
    </div>
  );
}
