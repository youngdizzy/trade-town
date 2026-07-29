import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { AnalystRole, CaseStudy, CeoDecisionRecord, ChallengeReport, Debate, DisciplineReview, PaperPortfolio, TradeDecision } from "@/types";
import { AGENT_IDS, SUCCESS_CASE_STUDY_CATEGORIES } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import {
  DEFAULT_REPLAY_FILTERS,
  buildDecisionReplay,
  buildReplayTimeline,
  formatMoney,
  matchesReplayFilters,
  voteDirection,
  type ReplayFilters,
  type ReplayStage,
} from "../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

const RESULT_OPTIONS: { value: ReplayFilters["result"]; label: string }[] = [
  { value: "all", label: "All" },
  { value: "trade", label: "Traded" },
  { value: "no_trade", label: "No Trade" },
  { value: "win", label: "Winners" },
  { value: "loss", label: "Losers" },
];

const ROLE_OPTIONS: { value: AnalystRole | "all"; label: string }[] = [
  { value: "all", label: "Any Department" },
  { value: "technical", label: "Technical" },
  { value: "news", label: "News" },
  { value: "macro", label: "Macro" },
  { value: "risk", label: "Risk" },
  { value: "sentiment", label: "Sentiment" },
  { value: "execution", label: "Execution" },
];

const STAGE_STATUS_TONE: Record<ReplayStage["status"], "green" | "amber" | "neutral"> = {
  recorded: "green",
  not_generated: "amber",
  not_applicable: "neutral",
};

const STAGE_STATUS_LABEL: Record<ReplayStage["status"], string> = {
  recorded: "RECORDED",
  not_generated: "NOT GENERATED",
  not_applicable: "N/A",
};

/**
 * v0.7 Feature 42 — the Decision Replay Center. A dedicated, deeply-joined
 * companion to the existing Decisions tab / DecisionDetail modal: those
 * stay focused on "what did the AI want and why"; this tab is "walk the
 * whole real process end to end, search/filter across every decision on
 * record, and see what the process itself taught the company" — see
 * lib/derive.ts's buildDecisionReplay/buildReplayTimeline for exactly
 * which real records back each stage, and what's honestly cut (no
 * natural-language search, no per-trade Quant review, no stop-loss/
 * profit-target/expected-value fields — none have a real data source in
 * this codebase; see CHANGELOG.md for the full scope-cut list).
 */
export function ReplayPanel() {
  const { decisions, ceoDecisions, debates, challengeReports, disciplineReviews, caseStudies, paperPortfolio } = useGameStore();
  const [filters, setFilters] = useState<ReplayFilters>(DEFAULT_REPLAY_FILTERS);
  const [replayingId, setReplayingId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return [...decisions]
      .reverse()
      .filter((d) => matchesReplayFilters(d, filters, paperPortfolio.tradeHistory.find((t) => t.decisionId === d.id) ?? null));
  }, [decisions, filters, paperPortfolio.tradeHistory]);

  const replaying = replayingId ? decisions.find((d) => d.id === replayingId) ?? null : null;

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <TerminalLabel>Smart Search — Structured Filters</TerminalLabel>
        <p className="mb-2 text-[9px] text-cmd-textDim">
          No natural-language search here — TradeTown has no real language-understanding infrastructure anywhere in its backend, and a fake parser would be worse than an honest filter grid.
          Every example the brief names ("show all losing trades," "show trades above 85% confidence," "show every trade where Risk disagreed") is covered by the filters below.
        </p>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          <label className="text-[9px] text-cmd-textDim">
            Symbol
            <input
              type="text"
              value={filters.symbol}
              onChange={(e) => setFilters((f) => ({ ...f, symbol: e.target.value }))}
              placeholder="e.g. NEXA"
              className="mt-1 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </label>
          <label className="text-[9px] text-cmd-textDim">
            Employee
            <select
              value={filters.agentId}
              onChange={(e) => setFilters((f) => ({ ...f, agentId: e.target.value as ReplayFilters["agentId"] }))}
              className="mt-1 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            >
              <option value="all">Anyone</option>
              {AGENT_IDS.map((id) => (
                <option key={id} value={id}>
                  {AGENT_PROFILES[id].name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-[9px] text-cmd-textDim">
            Department
            <select
              value={filters.role}
              onChange={(e) => setFilters((f) => ({ ...f, role: e.target.value as ReplayFilters["role"] }))}
              className="mt-1 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            >
              {ROLE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-[9px] text-cmd-textDim">
            Result
            <select
              value={filters.result}
              onChange={(e) => setFilters((f) => ({ ...f, result: e.target.value as ReplayFilters["result"] }))}
              className="mt-1 w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-cmd-text outline-none focus:border-cmd-cyan/50"
            >
              {RESULT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="mt-2 block text-[9px] text-cmd-textDim">
          Min. Confidence: {filters.minConfidence}%
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={filters.minConfidence}
            onChange={(e) => setFilters((f) => ({ ...f, minConfidence: Number(e.target.value) }))}
            className="mt-1 w-full accent-cmd-cyan"
          />
        </label>
        {(filters.agentId !== "all" || filters.symbol !== "" || filters.result !== "all" || filters.minConfidence !== 0 || filters.role !== "all") && (
          <button
            type="button"
            onClick={() => setFilters(DEFAULT_REPLAY_FILTERS)}
            className="mt-2 rounded-sm border border-cmd-border px-2 py-0.5 text-[9px] uppercase tracking-wide text-cmd-textDim hover:text-cmd-text"
          >
            Reset Filters
          </button>
        )}
      </Glass>

      <Glass className="p-3">
        <div className="mb-2 flex items-center justify-between">
          <TerminalLabel>Decision Archive ({filtered.length} of {decisions.length})</TerminalLabel>
        </div>
        {filtered.length === 0 ? (
          <EmptyState>No decisions match these filters.</EmptyState>
        ) : (
          <div className="max-h-96 overflow-y-auto">
            <table className="w-full">
              <thead>
                <tr className="sticky top-0 border-b border-cmd-border bg-cmd-panel text-[9px] uppercase tracking-wide text-cmd-textDim">
                  <th className="px-2 py-1.5 text-left">Symbol</th>
                  <th className="px-2 py-1.5 text-left">Direction</th>
                  <th className="px-2 py-1.5 text-left">Confidence</th>
                  <th className="px-2 py-1.5 text-left">Outcome</th>
                  <th className="px-2 py-1.5 text-left">Result</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d) => {
                  const trade = paperPortfolio.tradeHistory.find((t) => t.decisionId === d.id) ?? null;
                  return (
                    <tr key={d.id} onClick={() => setReplayingId(d.id)} className="cursor-pointer border-b border-cmd-border/40 last:border-0 hover:bg-cmd-panelLight/60">
                      <td className="px-2 py-1.5 font-cmdmono text-cmd-cyan">{d.symbol}</td>
                      <td className="px-2 py-1.5 text-cmd-textDim">{voteDirection(d.votes)}</td>
                      <td className="px-2 py-1.5 text-cmd-text">{Math.round(d.confidence)}%</td>
                      <td className={`px-2 py-1.5 ${d.outcome === "trade" ? "text-cmd-green" : "text-cmd-amber"}`}>{d.outcome === "trade" ? "TRADE" : "NO TRADE"}</td>
                      <td className={`px-2 py-1.5 tabular-nums ${trade ? (trade.pnl >= 0 ? "text-cmd-green" : "text-cmd-red") : "text-cmd-textDim"}`}>
                        {trade ? `${trade.pnl >= 0 ? "+" : ""}${trade.pnlPct.toFixed(1)}%` : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Glass>

      {replaying && (
        <ReplayDetail
          decision={replaying}
          ceoDecisions={ceoDecisions}
          debates={debates}
          challengeReports={challengeReports}
          disciplineReviews={disciplineReviews}
          caseStudies={caseStudies}
          portfolio={paperPortfolio}
          onClose={() => setReplayingId(null)}
        />
      )}
    </div>
  );
}

function ReplayDetail({
  decision,
  ceoDecisions,
  debates,
  challengeReports,
  disciplineReviews,
  caseStudies,
  portfolio,
  onClose,
}: {
  decision: TradeDecision;
  ceoDecisions: CeoDecisionRecord[];
  debates: Debate[];
  challengeReports: ChallengeReport[];
  disciplineReviews: DisciplineReview[];
  caseStudies: CaseStudy[];
  portfolio: PaperPortfolio;
  onClose: () => void;
}) {
  const [stageKey, setStageKey] = useState<string | null>(null);
  const links = useMemo(
    () => buildDecisionReplay(decision, { ceoDecisions, debates, challengeReports, disciplineReviews, caseStudies, portfolio }),
    [decision, ceoDecisions, debates, challengeReports, disciplineReviews, caseStudies, portfolio]
  );
  const timeline = useMemo(() => buildReplayTimeline(links), [links]);
  const activeStage = timeline.find((s) => s.key === stageKey) ?? timeline.find((s) => s.status === "recorded") ?? timeline[0]!;

  return (
    <div className="absolute inset-0 z-10 flex items-center justify-center bg-cmd-bg/80 p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-4xl overflow-y-auto rounded-sm border border-cmd-border bg-cmd-panel shadow-cmd-cyan" onClick={(e) => e.stopPropagation()}>
        <header className="sticky top-0 flex items-center justify-between border-b border-cmd-border bg-cmd-panel/95 px-4 py-3 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <span className="font-cmdmono text-xl text-cmd-cyan">{decision.symbol}</span>
            <span className="text-cmd-textDim">Decision Replay</span>
          </div>
          <button type="button" onClick={onClose} className="rounded-sm border border-cmd-border px-2.5 py-1 text-cmd-textDim transition-colors hover:border-cmd-red/50 hover:text-cmd-red">
            CLOSE ✕
          </button>
        </header>

        <div className="space-y-3 p-4">
          <Glass className="p-3">
            <TerminalLabel>Full Decision Timeline — pause, jump to any stage, or step through in order</TerminalLabel>
            <div className="flex flex-wrap gap-1.5">
              {timeline.map((stage) => (
                <button
                  key={stage.key}
                  type="button"
                  onClick={() => setStageKey(stage.key)}
                  className={`rounded-sm border px-2 py-1 text-left text-[9px] ${
                    activeStage.key === stage.key ? "border-cmd-cyan/60 bg-cmd-cyan/10 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
                  }`}
                >
                  <div className="uppercase tracking-wide">{stage.label}</div>
                  <StatusPill tone={STAGE_STATUS_TONE[stage.status]}>{STAGE_STATUS_LABEL[stage.status]}</StatusPill>
                </button>
              ))}
            </div>
            <div className="mt-2 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2">
              <div className="mb-1 flex items-center gap-2">
                <span className="text-cmd-cyan">{activeStage.label}</span>
                <StatusPill tone={STAGE_STATUS_TONE[activeStage.status]}>{STAGE_STATUS_LABEL[activeStage.status]}</StatusPill>
              </div>
              <p className="text-cmd-text">{activeStage.detail}</p>
            </div>
          </Glass>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Glass className="p-3">
              <TerminalLabel>Team Replay — Every Real Opinion, Visible Forever</TerminalLabel>
              {decision.votes.length === 0 ? (
                <EmptyState>No votes on record for this decision.</EmptyState>
              ) : (
                <div className="max-h-56 space-y-1.5 overflow-y-auto">
                  {decision.votes.map((v) => {
                    const supporting = decision.supportingAgents.includes(v.agentId);
                    return (
                      <div key={v.agentId} className="border-b border-cmd-border/50 pb-1 last:border-0">
                        <div className="flex items-center justify-between">
                          <span className={supporting ? "text-cmd-green" : "text-cmd-red"}>{AGENT_PROFILES[v.agentId].name}</span>
                          <span className="text-[9px] uppercase text-cmd-textDim">{v.choice}</span>
                        </div>
                        <div className="text-[9px] text-cmd-textDim">{v.reason}</div>
                      </div>
                    );
                  })}
                </div>
              )}
              {links.debate && links.debate.turns.length > 0 && (
                <div className="mt-2 border-t border-cmd-border/50 pt-2">
                  <TerminalLabel>Debate Thread</TerminalLabel>
                  <div className="max-h-40 space-y-1 overflow-y-auto">
                    {links.debate.turns.map((t, i) => (
                      <div key={i} className="text-[9px]">
                        <span className="text-cmd-cyan">{AGENT_PROFILES[t.agentId].name}</span>{" "}
                        <span className="uppercase text-cmd-textDim">({t.stance})</span>: <span className="text-cmd-text">{t.text}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Glass>

            <Glass className="p-3">
              <TerminalLabel>Devil&apos;s Advocate Challenge</TerminalLabel>
              {links.challengeReport ? (
                <div className="space-y-1.5 text-[9px]">
                  <DataRow label="Assigned to" value={AGENT_PROFILES[links.challengeReport.assignedAgent].name} />
                  <DataRow label="Severity" value={links.challengeReport.severity.replace(/_/g, " ")} />
                  <div className="text-cmd-text">{links.challengeReport.bearCase}</div>
                  {links.challengeReport.hiddenRisks.length > 0 && (
                    <ul className="list-inside list-disc text-cmd-textDim">
                      {links.challengeReport.hiddenRisks.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ) : (
                <EmptyState>Not every proposal is escalated to a Devil&apos;s Advocate — none was assigned to this one.</EmptyState>
              )}
            </Glass>
          </div>

          <Glass className="p-3">
            <TerminalLabel>Decision Recording</TerminalLabel>
            <div className="grid grid-cols-2 gap-x-4 md:grid-cols-3">
              <DataRow label="Trade ID" value={decision.id} />
              <DataRow label="Date" value={new Date(decision.createdAt).toLocaleString()} />
              <DataRow label="Signal Category" value={links.trade?.marketConditions ?? "—"} />
              <DataRow label="Entry" value={links.order ? formatMoney(links.order.price) : links.trade ? formatMoney(links.trade.entryPrice) : "—"} />
              <DataRow label="Position Size" value={links.order?.quantity ?? links.trade?.quantity ?? "—"} />
              <DataRow label="Confidence Score" value={`${Math.round(decision.confidence)}%`} />
              <DataRow label="Final Outcome" value={links.trade ? `${links.trade.pnl >= 0 ? "+" : ""}${links.trade.pnlPct.toFixed(1)}%` : decision.outcome === "trade" ? "Open / pending" : "No trade"} />
            </div>
            <div className="mt-2 rounded-sm border border-cmd-amber/30 bg-cmd-bg/40 p-1.5 text-[9px] text-cmd-textDim">
              Stop Loss, Profit Target, and Expected Value are not shown — TradeTown&apos;s paper broker has never placed a real exit order and has no calibrated probability model to
              honestly compute an expected value from (the same documented boundary as DecisionDetail&apos;s own Trade Plan section and app/gatekeeper.py). Showing a number here
              would be inventing data this company doesn&apos;t have.
            </div>
          </Glass>

          {links.caseStudies.length > 0 && (
            <Glass className="p-3">
              <TerminalLabel>Lessons Generated</TerminalLabel>
              <div className="space-y-1.5">
                {links.caseStudies.map((study) => {
                  const isSuccess = SUCCESS_CASE_STUDY_CATEGORIES.has(study.category);
                  return (
                    <div key={study.id} className="border-b border-cmd-border/50 pb-1 last:border-0 text-[9px]">
                      <div className="flex items-center gap-1.5">
                        <StatusPill tone={isSuccess ? "green" : "red"}>{isSuccess ? "SUCCESS" : "MISTAKE"}</StatusPill>
                        <span className={isSuccess ? "text-cmd-green" : "text-cmd-purple"}>{study.title}</span>
                      </div>
                      <div className="mt-0.5 text-cmd-textDim">{study.lessonsLearned}</div>
                    </div>
                  );
                })}
              </div>
            </Glass>
          )}
        </div>
      </div>
    </div>
  );
}
