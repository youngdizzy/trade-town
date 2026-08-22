import { useEffect, useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { api } from "@/net/api";
import type { DecisionVaultEntry, KnowledgeQualityScore, SimilarTradesSummary, Strategy, TradeReportCard, TradeStrategyRuleSnapshot } from "@/types";
import { decisionGradeTone } from "../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

function strategyLabel(id: string | null, strategies: Strategy[]): string {
  if (id === null) return "No strategy attributed";
  return strategies.find((s) => s.id === id)?.name ?? id;
}

/**
 * v0.7 Feature 54 (the brief self-numbered it "Feature 53," already used
 * elsewhere in this codebase for Company Certification) — the Decision
 * Memory System. The Decision Vault is the permanent, capped archive of
 * every closed trade's real process trail (backend/app/decision_vault.py).
 * Selecting an entry fetches its real Trade Report Card and runs the real
 * rule-based Similarity Engine against every other vault entry — both
 * computed fresh on request, never cached client-side beyond this view.
 */
export function DecisionVaultPanel() {
  const { decisionVault } = useGameStore();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const recentEntries = useMemo(() => [...decisionVault].reverse(), [decisionVault]);
  const selected = useMemo(() => decisionVault.find((e) => e.id === selectedId) ?? null, [decisionVault, selectedId]);

  useEffect(() => {
    if (!selectedId && recentEntries[0]) setSelectedId(recentEntries[0].id);
  }, [recentEntries, selectedId]);

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <Glass className="max-h-[32rem] overflow-y-auto p-3 lg:col-span-1">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Decision Vault</TerminalLabel>
          <StatusPill tone="purple">{decisionVault.length} record{decisionVault.length === 1 ? "" : "s"}</StatusPill>
        </div>
        {recentEntries.length === 0 ? (
          <EmptyState>Nothing archived yet — every closed trade with a real matched decision files one permanent record here, joining its Decision Grade, Discipline Review, and any case study filed against it.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {recentEntries.map((entry) => (
              <VaultEntryRow key={entry.id} entry={entry} selected={entry.id === selectedId} onSelect={() => setSelectedId(entry.id)} />
            ))}
          </div>
        )}
      </Glass>

      <div className="space-y-3 lg:col-span-2">{selected ? <VaultEntryDetail entry={selected} /> : <Glass className="p-3"><EmptyState>Select a record to see its real Trade Report Card and Similarity Engine read.</EmptyState></Glass>}</div>
    </div>
  );
}

function VaultEntryRow({ entry, selected, onSelect }: { entry: DecisionVaultEntry; selected: boolean; onSelect: () => void }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-sm border p-1.5 text-left text-[9px] ${selected ? "border-cmd-cyan/60 bg-cmd-cyan/10" : "border-cmd-border/60 bg-cmd-bg/40 hover:border-cmd-border"}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5">
          <span className="text-cmd-cyan">{entry.symbol}</span>
          <StatusPill tone={decisionGradeTone(entry.decisionGrade)}>{entry.decisionGrade}</StatusPill>
        </span>
        <span className={`tabular-nums ${entry.pnlPct >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>
          {entry.pnlPct >= 0 ? "+" : ""}
          {entry.pnlPct.toFixed(1)}%
        </span>
      </div>
      <div className="mt-0.5 flex items-center justify-between text-cmd-textDim">
        <span>Day {entry.simDay} · {entry.marketRegimeLabel}</span>
        {entry.caseStudyCategory && <span className="text-cmd-amber">flagged</span>}
      </div>
    </button>
  );
}

function VaultEntryDetail({ entry }: { entry: DecisionVaultEntry }) {
  const { strategies } = useGameStore();
  const [reportCard, setReportCard] = useState<TradeReportCard | null>(null);
  const [similar, setSimilar] = useState<SimilarTradesSummary | null>(null);
  const [qualityScore, setQualityScore] = useState<KnowledgeQualityScore | null>(null);
  const [ruleSnapshot, setRuleSnapshot] = useState<TradeStrategyRuleSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      api.getDecisionVaultReportCard(entry.id),
      api.getDecisionVaultSimilar({ symbol: entry.symbol, marketRegime: entry.marketRegime, confidenceTier: entry.confidenceTier, excludeId: entry.id }),
      api.getDecisionVaultQualityScore(entry.id),
      api.getTradeStrategyRuleSnapshot(entry.tradeId),
    ])
      .then(([reportCardRes, similarRes, qualityScoreRes, ruleSnapshotRes]) => {
        if (!cancelled) {
          setReportCard(reportCardRes);
          setSimilar(similarRes);
          setQualityScore(qualityScoreRes);
          setRuleSnapshot(ruleSnapshotRes);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [entry.id, entry.tradeId, entry.symbol, entry.marketRegime, entry.confidenceTier]);

  return (
    <>
      <Glass className="p-3">
        <TerminalLabel>
          {entry.symbol} — Day {entry.simDay} · {entry.session.replace(/_/g, " ")}
        </TerminalLabel>
        <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
          <DataRow label="Entry" value={`$${entry.entryPrice.toFixed(2)}`} />
          <DataRow label="Exit" value={`$${entry.exitPrice.toFixed(2)}`} />
          <DataRow label="P&L" value={`${entry.pnlPct >= 0 ? "+" : ""}${entry.pnlPct.toFixed(1)}%`} valueClassName={entry.pnlPct >= 0 ? "text-cmd-green" : "text-cmd-red"} />
          <DataRow label="Position Size" value={entry.positionSize.toFixed(2)} />
          <DataRow label="Hold Duration" value={`${entry.holdDurationMinutes} min`} />
          <DataRow label="Market Regime" value={entry.marketRegimeLabel} />
        </div>
        <div className="mt-1.5 flex items-center gap-1.5 text-[9px]">
          <span className="text-cmd-textDim">Strategy:</span>
          <span className={entry.strategyId === null ? "italic text-cmd-textDim" : "text-cmd-cyan"}>{strategyLabel(entry.strategyId, strategies)}</span>
        </div>
        {entry.executiveNotes && <p className="mt-1.5 text-[9px] text-cmd-textDim">{entry.executiveNotes}</p>}
        <p className="mt-1.5 text-[9px] text-cmd-textDim">{entry.lessonsLearned}</p>
        {entry.companyDnaChange && <p className="mt-1.5 text-[8px] italic text-cmd-purple">Company DNA: {entry.companyDnaChange}</p>}
      </Glass>

      {/* CEO directive "Complete Trade Provenance..." Part 16 — RULES,
          the disclosure level between STRATEGY and SESSION in the
          directive's own chain. Reuses TradeStrategyRuleSnapshot (Part
          2) rather than re-deriving compiled rules here. */}
      {entry.strategyId !== null && (
        <Glass className="p-3">
          <TerminalLabel>Compiled Rules at Decision Time</TerminalLabel>
          {ruleSnapshot === null ? (
            loading && <EmptyState>Loading this trade&apos;s real rule snapshot…</EmptyState>
          ) : ruleSnapshot.compiledDefinition === null ? (
            <EmptyState>
              No compiled rule snapshot on record for this trade — either the picked strategy had no compiled rules yet at decision time, or this trade predates this directive&apos;s Part 2 snapshot mechanism. Never fabricated.
            </EmptyState>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-x-3 sm:grid-cols-4">
                <DataRow label="Version" value={ruleSnapshot.compiledDefinition.version} />
                <DataRow label="Timeframe" value={ruleSnapshot.compiledDefinition.timeframe} />
                <DataRow label="Steps" value={ruleSnapshot.compiledDefinition.sequence.length} />
              </div>
              {ruleSnapshot.compiledDefinition.sequence.length > 0 && (
                <div className="mt-1.5 space-y-1">
                  {ruleSnapshot.compiledDefinition.sequence.map((step) => (
                    <div key={step.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                      <span className="uppercase text-cmd-cyan">{step.stepType}</span> — <span className="text-cmd-textDim">{step.detail}</span>
                    </div>
                  ))}
                </div>
              )}
              {ruleSnapshot.compiledDefinition.stop && (
                <div className="mt-1.5 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                  <span className="text-cmd-textDim">Stop:</span> {ruleSnapshot.compiledDefinition.stop.method}
                  {ruleSnapshot.compiledDefinition.stop.atrPeriod !== null && ` (ATR${ruleSnapshot.compiledDefinition.stop.atrPeriod} × ${ruleSnapshot.compiledDefinition.stop.atrMultiplier})`}
                  {ruleSnapshot.compiledDefinition.stop.percent !== null && ` (${ruleSnapshot.compiledDefinition.stop.percent}%)`}
                </div>
              )}
              {ruleSnapshot.compiledDefinition.target && (
                <div className="mt-1 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                  <span className="text-cmd-textDim">Target:</span>{" "}
                  {ruleSnapshot.compiledDefinition.target.method === "r_multiple" ? `${ruleSnapshot.compiledDefinition.target.value}R` : `${ruleSnapshot.compiledDefinition.target.value}%`}
                </div>
              )}
            </>
          )}
        </Glass>
      )}

      {loading && !reportCard && (
        <Glass className="p-3">
          <EmptyState>Computing this trade's real Report Card and Similarity Engine read…</EmptyState>
        </Glass>
      )}
      {error && (
        <Glass className="p-3">
          <div className="text-[9px] text-cmd-red">{error}</div>
        </Glass>
      )}

      {reportCard && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Trade Report Card — graded on process, never on P&amp;L</TerminalLabel>
            <StatusPill tone={reportCard.wouldTakeAgain ? "green" : "red"}>{reportCard.wouldTakeAgain ? "WOULD TAKE AGAIN" : "WOULD NOT REPEAT"}</StatusPill>
          </div>
          <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
            <GradeCell label="Evidence Score" value={`${reportCard.evidenceScore.toFixed(0)}/100`} />
            <GradeCell label="Confidence Score" value={`${reportCard.confidenceScore.toFixed(0)}/100`} />
            <GradeCell label="Capital Allocation" value={reportCard.capitalAllocationGrade} tone={decisionGradeTone(reportCard.capitalAllocationGrade)} />
            <GradeCell label="Decision Grade" value={reportCard.decisionGrade} tone={decisionGradeTone(reportCard.decisionGrade)} />
            <GradeCell label="Discipline" value={reportCard.disciplineGrade} />
            <GradeCell label="Patience" value={reportCard.patienceGrade} tone={decisionGradeTone(reportCard.patienceGrade)} />
          </div>
          <p className="mt-2 text-[9px] text-cmd-text">{reportCard.recommendation}</p>

          {(reportCard.maePct !== null || reportCard.entrySlippageBps !== null) && (
            <div className="mt-3 border-t border-cmd-border/60 pt-2">
              <div className="mb-1.5 text-[9px] uppercase tracking-wide text-cmd-textDim">Post-Trade Evidence — joined by this trade&apos;s own real ID</div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
                {reportCard.maePct !== null && <DataRow label="MAE" value={`${reportCard.maePct.toFixed(2)}%`} />}
                {reportCard.mfePct !== null && <DataRow label="MFE" value={`${reportCard.mfePct.toFixed(2)}%`} />}
                {reportCard.capturePct !== null && <DataRow label="Capture" value={`${reportCard.capturePct.toFixed(0)}%`} />}
                {reportCard.entrySlippageBps !== null && <DataRow label="Entry Slippage" value={`${reportCard.entrySlippageBps.toFixed(1)} bps`} />}
                {reportCard.exitSlippageBps !== null && <DataRow label="Exit Slippage" value={`${reportCard.exitSlippageBps.toFixed(1)} bps`} />}
                {reportCard.transactionCostUsd !== null && <DataRow label="Transaction Cost" value={`$${reportCard.transactionCostUsd.toFixed(2)}`} />}
              </div>
              {reportCard.supportingAgents.length > 0 && (
                <div className="mt-1.5 text-[9px] text-cmd-textDim">
                  Supporting: <span className="text-cmd-text">{reportCard.supportingAgents.join(", ")}</span>
                  {reportCard.opposingAgents.length > 0 && (
                    <>
                      {" "}
                      · Opposing: <span className="text-cmd-text">{reportCard.opposingAgents.join(", ")}</span>
                    </>
                  )}
                </div>
              )}
              <p className="mt-1.5 text-[8px] italic text-cmd-textDim">{reportCard.dataHonestyNote}</p>
            </div>
          )}
        </Glass>
      )}

      {similar && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Similarity Engine — real, rule-based matching</TerminalLabel>
            <StatusPill tone="cyan">{similar.matchCount} match{similar.matchCount === 1 ? "" : "es"}</StatusPill>
          </div>
          {similar.matchCount === 0 ? (
            <EmptyState>No comparable historical decisions yet — nothing to honestly compare this trade against.</EmptyState>
          ) : (
            <>
              <div className="mb-1.5 flex flex-wrap gap-1">
                {similar.matchedOn.map((dim) => (
                  <span key={dim} className="rounded-sm border border-cmd-border/60 px-1.5 py-0.5 text-[8px] uppercase tracking-wider text-cmd-textDim">
                    matched on {dim}
                  </span>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
                <DataRow label="Win Rate" value={`${similar.winRatePct.toFixed(0)}%`} />
                <DataRow label="Avg P&L" value={`${similar.avgPnlPct >= 0 ? "+" : ""}${similar.avgPnlPct.toFixed(1)}%`} valueClassName={similar.avgPnlPct >= 0 ? "text-cmd-green" : "text-cmd-red"} />
                <DataRow label="Worst P&L" value={`${similar.worstPnlPct.toFixed(1)}%`} valueClassName="text-cmd-red" />
                {similar.bestRegime && <DataRow label="Best Regime" value={similar.bestRegime.replace(/_/g, " ")} />}
                {similar.worstRegime && <DataRow label="Worst Regime" value={similar.worstRegime.replace(/_/g, " ")} />}
              </div>
              {similar.warning && (
                <div className="mt-2 rounded-sm border border-cmd-amber/50 bg-cmd-amber/10 p-1.5 text-[9px] text-cmd-amber">⚠ {similar.warning}</div>
              )}
              <div className="mt-2 space-y-1">
                {similar.examples.map((ex) => (
                  <div key={ex.vaultEntryId} className="flex items-center justify-between text-[9px] text-cmd-textDim">
                    <span>
                      {ex.symbol} · Day {ex.simDay}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <StatusPill tone={decisionGradeTone(ex.decisionGrade)}>{ex.decisionGrade}</StatusPill>
                      <span className={`tabular-nums ${ex.pnlPct >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>
                        {ex.pnlPct >= 0 ? "+" : ""}
                        {ex.pnlPct.toFixed(1)}%
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </Glass>
      )}

      {qualityScore && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Knowledge Quality Score</TerminalLabel>
            <StatusPill tone={qualityScore.overallScore >= 60 ? "green" : qualityScore.overallScore >= 35 ? "amber" : "red"}>{qualityScore.overallScore.toFixed(0)}/100</StatusPill>
          </div>
          {qualityScore.patternFrequency === 0 ? (
            <EmptyState>No comparable Vault entry exists yet — this reads as pure Relevance until history builds up.</EmptyState>
          ) : (
            <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
              <DataRow label="Historical Success" value={`${(qualityScore.historicalSuccessPct ?? 0).toFixed(0)}%`} />
              <DataRow label="Pattern Frequency" value={`${qualityScore.patternFrequency} seen`} />
              <DataRow label="Relevance" value={`${qualityScore.relevancePct.toFixed(0)}%`} />
            </div>
          )}
          <p className="mt-1.5 text-[8px] text-cmd-textDim">Pattern Frequency counts other Vault entries sharing this trade's own real profile — a proxy for how often this kind of situation has recurred, not a literal usage log.</p>
        </Glass>
      )}
    </>
  );
}

const GRADE_CELL_TONE_CLASS: Record<"green" | "cyan" | "amber" | "red", string> = {
  green: "text-cmd-green",
  cyan: "text-cmd-cyan",
  amber: "text-cmd-amber",
  red: "text-cmd-red",
};

function GradeCell({ label, value, tone }: { label: string; value: string; tone?: "green" | "cyan" | "amber" | "red" }) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
      <div className="text-cmd-textDim">{label}</div>
      <div className={tone ? GRADE_CELL_TONE_CLASS[tone] : "text-cmd-text"}>{value}</div>
    </div>
  );
}
