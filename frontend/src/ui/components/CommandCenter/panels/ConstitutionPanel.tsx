import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { NexusManager } from "@/game/systems/NexusManager";
import { api } from "@/net/api";
import type { ConstitutionCitationSource } from "@/types";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

const SOURCE_LABELS: Record<ConstitutionCitationSource, string> = {
  case_study: "Library of Mistakes/Successes",
  devils_advocate: "Devil's Advocate",
  risk_department: "Risk Department",
  academy: "Academy",
  founders: "Founders",
  coach: "Coach",
};

/**
 * v0.7 Feature 46 — the Company Constitution. See
 * backend/app/constitution.py's module docstring for the full scope:
 * 8 real Articles seeded verbatim from the brief, a real "Live
 * Enforcement" citation log fed by 6 real event hooks (never a
 * fabricated quote), and a real amendment pipeline (Founder debate ->
 * Coach evaluation -> Employee vote -> CEO ratification) where every
 * step is a checkable computation over the amendment's own real
 * proposed text.
 */
export function ConstitutionPanel() {
  const { constitution } = useGameStore();
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState<ConstitutionCitationSource | "all">("all");

  const recentCitations = useMemo(() => [...constitution.citations].reverse().filter((c) => sourceFilter === "all" || c.source === sourceFilter), [constitution.citations, sourceFilter]);
  const pendingAmendments = useMemo(() => [...constitution.amendments].reverse(), [constitution.amendments]);

  const runAction = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const propose = () =>
    runAction(async () => {
      if (!title.trim() || !text.trim()) return;
      const res = await api.proposeConstitutionAmendment(title.trim(), text.trim());
      NexusManager.setConstitution(res.constitution);
      setTitle("");
      setText("");
    });

  const advance = (amendmentId: string) =>
    runAction(async () => {
      const res = await api.advanceConstitutionAmendment(amendmentId);
      NexusManager.setConstitution(res.constitution);
    });

  const decide = (amendmentId: string, approve: boolean) =>
    runAction(async () => {
      const res = await api.decideConstitutionAmendment(amendmentId, approve);
      NexusManager.setConstitution(res.constitution);
    });

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <Glass className="p-3 lg:col-span-2">
        <TerminalLabel>The Articles — permanent company law</TerminalLabel>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {constitution.articles.map((article) => (
            <div key={article.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
              <div className="mb-0.5 flex items-center justify-between">
                <span className="text-cmd-cyan">Article {article.id}</span>
                {article.ratifiedSimDay > 1 && <StatusPill tone="purple">Amendment</StatusPill>}
              </div>
              <div className="text-cmd-text">{article.text}</div>
            </div>
          ))}
        </div>
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Live Enforcement</TerminalLabel>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value as ConstitutionCitationSource | "all")}
            className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-0.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          >
            <option value="all">Every source</option>
            {(Object.keys(SOURCE_LABELS) as ConstitutionCitationSource[]).map((s) => (
              <option key={s} value={s}>
                {SOURCE_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
        <p className="mb-2 text-[9px] text-cmd-textDim">
          Coach quotes it, Founders teach it, Academy explains it, Risk Department enforces it, Devil&apos;s Advocate references it — every entry below is a real citation fired by
          one of those five real systems, plus the Library of Mistakes/Successes.
        </p>
        {recentCitations.length === 0 ? (
          <EmptyState>No citations on record yet — these fire as real company events happen.</EmptyState>
        ) : (
          <div className="max-h-72 space-y-1.5 overflow-y-auto">
            {recentCitations.map((c) => (
              <div key={c.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="mb-0.5 flex items-center justify-between">
                  <StatusPill tone="cyan">Article {c.articleId}</StatusPill>
                  <span className="text-cmd-textDim">{SOURCE_LABELS[c.source]} — Day {c.simDay}</span>
                </div>
                <div className="text-cmd-text">{c.detail}</div>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Propose an Amendment</TerminalLabel>
        <div className="space-y-1.5">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Article title"
            className="w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text placeholder:text-cmd-textDim outline-none focus:border-cmd-cyan/50"
          />
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Article text"
            rows={2}
            className="w-full resize-none rounded-sm border border-cmd-border bg-cmd-bg/60 px-1.5 py-1 text-[9px] text-cmd-text placeholder:text-cmd-textDim outline-none focus:border-cmd-cyan/50"
          />
          <button
            type="button"
            onClick={() => void propose()}
            disabled={busy || !title.trim() || !text.trim()}
            className="rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-cyan shadow-cmd-cyan transition-colors hover:bg-cmd-cyan/10 disabled:opacity-40"
          >
            Propose
          </button>
          {error && <div className="text-[9px] text-cmd-red">{error}</div>}
        </div>
      </Glass>

      <Glass className="p-3 lg:col-span-2">
        <TerminalLabel>Amendments</TerminalLabel>
        {pendingAmendments.length === 0 ? (
          <EmptyState>No amendments proposed yet.</EmptyState>
        ) : (
          <div className="space-y-2">
            {pendingAmendments.map((amendment) => {
              const supportCount = amendment.employeeVotes.filter((v) => v.choice === "support").length;
              const opposeCount = amendment.employeeVotes.filter((v) => v.choice === "oppose").length;
              const abstainCount = amendment.employeeVotes.filter((v) => v.choice === "abstain").length;
              return (
                <div key={amendment.id} data-testid="amendment-card" className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-cmd-cyan">{amendment.proposedTitle}</span>
                    <StatusPill tone={amendment.status === "approved" ? "green" : amendment.status === "rejected" ? "red" : "amber"}>{amendment.status}</StatusPill>
                  </div>
                  <div className="mb-1 text-cmd-text">{amendment.proposedText}</div>

                  {amendment.status === "proposed" && (
                    <button type="button" onClick={() => void advance(amendment.id)} disabled={busy} className="rounded-sm border border-cmd-purple/50 px-2 py-0.5 text-[9px] uppercase text-cmd-purple hover:bg-cmd-purple/10 disabled:opacity-40">
                      Send to Founders, Coach &amp; Employees
                    </button>
                  )}

                  {amendment.founderVerdicts.length > 0 && (
                    <div className="mt-1.5 space-y-1 border-t border-cmd-border/50 pt-1.5">
                      {amendment.founderVerdicts.map((v) => (
                        <div key={v.founderId} className="text-cmd-textDim">{v.verdict}</div>
                      ))}
                      {amendment.coachEvaluation && <div className="text-cmd-textDim">{amendment.coachEvaluation}</div>}
                      <DataRow label="Employee vote (advisory)" value={`${supportCount} support / ${opposeCount} oppose / ${abstainCount} abstain`} />
                    </div>
                  )}

                  {amendment.status === "voted" && (
                    <div className="mt-1.5 flex gap-2">
                      <button type="button" onClick={() => void decide(amendment.id, true)} disabled={busy} className="rounded-sm border border-cmd-green/50 px-2 py-0.5 text-[9px] uppercase text-cmd-green hover:bg-cmd-green/10 disabled:opacity-40">
                        Ratify
                      </button>
                      <button type="button" onClick={() => void decide(amendment.id, false)} disabled={busy} className="rounded-sm border border-cmd-red/50 px-2 py-0.5 text-[9px] uppercase text-cmd-red hover:bg-cmd-red/10 disabled:opacity-40">
                        Reject
                      </button>
                    </div>
                  )}
                  {amendment.status === "approved" && amendment.ratifiedArticleId && <StatusPill tone="green">Now Article {amendment.ratifiedArticleId}</StatusPill>}
                </div>
              );
            })}
          </div>
        )}
      </Glass>
    </div>
  );
}
