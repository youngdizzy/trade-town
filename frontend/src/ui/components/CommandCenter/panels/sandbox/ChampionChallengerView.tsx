import { useState } from "react";
import { api } from "@/net/api";
import { AGENT_IDS } from "@/types";
import type { AgentId, ChallengerComparison, ChallengerVerdict, ChampionChallengerFamilyRead } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";

const VERDICT_TONE: Record<ChallengerVerdict, "green" | "amber" | "red"> = {
  challenger_recommended: "green",
  champion_retained: "amber",
  insufficient_evidence: "red",
};

function MetricRow({ label, champion, challenger, suffix = "" }: { label: string; champion: number | null; challenger: number | null; suffix?: string }) {
  return (
    <div className="grid grid-cols-3 gap-2 border-t border-cmd-border/40 py-1 text-[9px]">
      <span className="text-cmd-textDim">{label}</span>
      <span className="text-cmd-text">{champion !== null ? `${champion}${suffix}` : "—"}</span>
      <span className="text-cmd-cyan">{challenger !== null ? `${challenger}${suffix}` : "—"}</span>
    </div>
  );
}

/**
 * CEO directive "TradeTown — 11/10 Self-Improving Quant Agent System,"
 * Section 1 (Champion vs Challenger — The Core Upgrade). A challenger
 * must prove it beats the champion — both sides run through the exact
 * same real backtest pipeline over the identical real candle window,
 * and the promotion recommendation is a real, disclosed economic
 * tradeoff rule (see backend/app/champion_challenger.py's own module
 * docstring for exactly what it is and is not — never a statistical-
 * significance claim). Promotion is always a separate, explicit action;
 * a comparison alone never changes the current champion.
 */
export function ChampionChallengerView() {
  const [strategyFamily, setStrategyFamily] = useState("50 EMA Family");
  const [championName, setChampionName] = useState("50 EMA Champion");
  const [championText, setChampionText] = useState(
    "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
  );
  const [challengerName, setChallengerName] = useState("50 EMA + RSI Challenger");
  const [challengerText, setChallengerText] = useState(
    "Buy when price closes above the 50 EMA and RSI is above 70, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
  );
  const [hypothesis, setHypothesis] = useState("Filtering by RSI confirmation may cut false breakouts and improve expectancy.");
  const [proposedBy, setProposedBy] = useState<AgentId>("quant");

  const [comparing, setComparing] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<ChallengerComparison | null>(null);

  const [promoting, setPromoting] = useState(false);
  const [promoteError, setPromoteError] = useState<string | null>(null);
  const [promoted, setPromoted] = useState(false);

  const [family, setFamily] = useState<ChampionChallengerFamilyRead | null>(null);
  const [familyLoading, setFamilyLoading] = useState(false);

  const loadFamily = (name: string) => {
    setFamilyLoading(true);
    api
      .getChampionChallengerFamily(name)
      .then(setFamily)
      .catch(() => undefined)
      .finally(() => setFamilyLoading(false));
  };

  const compare = async () => {
    setComparing(true);
    setCompareError(null);
    setComparison(null);
    setPromoted(false);
    try {
      const [championDefinition, challengerDefinition] = await Promise.all([api.compileStrategy(championName, championText), api.compileStrategy(challengerName, challengerText)]);
      const result = await api.compareChampionChallenger(championDefinition, challengerDefinition, strategyFamily, hypothesis, proposedBy, ["AAPL"]);
      setComparison(result);
      loadFamily(strategyFamily);
    } catch (err) {
      setCompareError(err instanceof Error ? err.message : String(err));
    } finally {
      setComparing(false);
    }
  };

  const promote = () => {
    if (!comparison) return;
    setPromoting(true);
    setPromoteError(null);
    api
      .promoteChallenger(comparison.id, proposedBy, `Cleared the real disclosed comparison bar: ${comparison.reasoning}`)
      .then(() => {
        setPromoted(true);
        loadFamily(strategyFamily);
      })
      .catch((err) => setPromoteError(err instanceof Error ? err.message : String(err)))
      .finally(() => setPromoting(false));
  };

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <TerminalLabel>Champion vs Challenger — a challenger must prove it, never assumed</TerminalLabel>
        <p className="mt-1 text-[9px] text-cmd-textDim">
          Both sides run the exact same real backtest pipeline over the identical real candle window. The promotion recommendation is a real, disclosed economic tradeoff rule
          (expectancy vs. drawdown) — never a claim of statistical significance, and never applied automatically. Promoting a challenger is always a separate, explicit action.
        </p>

        <div className="mt-2">
          <input
            type="text"
            value={strategyFamily}
            onChange={(e) => setStrategyFamily(e.target.value)}
            placeholder="Strategy family name"
            className="w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          />
        </div>

        <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
          <div className="space-y-1.5 rounded-sm border border-cmd-border/60 p-2">
            <div className="text-[8px] uppercase tracking-wide text-cmd-textDim">Champion</div>
            <input
              type="text"
              value={championName}
              onChange={(e) => setChampionName(e.target.value)}
              placeholder="Champion name"
              className="w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
            <textarea
              value={championText}
              onChange={(e) => setChampionText(e.target.value)}
              rows={3}
              className="w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </div>
          <div className="space-y-1.5 rounded-sm border border-cmd-border/60 p-2">
            <div className="text-[8px] uppercase tracking-wide text-cmd-cyan">Challenger</div>
            <input
              type="text"
              value={challengerName}
              onChange={(e) => setChallengerName(e.target.value)}
              placeholder="Challenger name"
              className="w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
            <textarea
              value={challengerText}
              onChange={(e) => setChallengerText(e.target.value)}
              rows={3}
              className="w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
            />
          </div>
        </div>

        <div className="mt-2 space-y-1.5">
          <textarea
            value={hypothesis}
            onChange={(e) => setHypothesis(e.target.value)}
            rows={2}
            placeholder="What testable hypothesis does the challenger stand on?"
            className="w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          />
          <div className="flex items-center gap-2">
            <select
              value={proposedBy}
              onChange={(e) => setProposedBy(e.target.value as AgentId)}
              className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
            >
              {AGENT_IDS.map((id) => (
                <option key={id} value={id}>
                  {AGENT_PROFILES[id].name}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={comparing || !championText.trim() || !challengerText.trim() || !strategyFamily.trim() || !hypothesis.trim()}
              onClick={compare}
              className="rounded-sm border border-cmd-border px-3 py-1.5 text-[9px] uppercase text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
            >
              {comparing ? "Comparing…" : "Compare Champion vs Challenger"}
            </button>
          </div>
        </div>
        {compareError && <div className="mt-1.5 text-[9px] text-cmd-red">{compareError}</div>}
      </Glass>

      {comparison && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Comparison Result</TerminalLabel>
            <StatusPill tone={VERDICT_TONE[comparison.verdict]}>{comparison.verdict.replace(/_/g, " ")}</StatusPill>
          </div>
          <div className="text-[9px] text-cmd-text">{comparison.reasoning}</div>

          <div className="mt-2 grid grid-cols-3 gap-2 text-[9px] font-cmdmono uppercase tracking-wide text-cmd-textDim">
            <span>Metric</span>
            <span className="text-cmd-text">Champion</span>
            <span className="text-cmd-cyan">Challenger</span>
          </div>
          <MetricRow label="Trade count" champion={comparison.championTradeCount} challenger={comparison.challengerTradeCount} />
          <MetricRow label="Expectancy" champion={comparison.championExpectancyR} challenger={comparison.challengerExpectancyR} suffix="R" />
          <MetricRow label="Profit factor" champion={comparison.championProfitFactor} challenger={comparison.challengerProfitFactor} />
          <MetricRow label="Max drawdown" champion={comparison.championMaxDrawdownR} challenger={comparison.challengerMaxDrawdownR} suffix="R" />

          <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px] text-cmd-textDim">{comparison.championConclusion}</div>
            <div className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px] text-cmd-textDim">{comparison.challengerConclusion}</div>
          </div>

          <div className="mt-2 flex items-center gap-2">
            <button
              type="button"
              disabled={promoting || promoted || comparison.verdict !== "challenger_recommended"}
              onClick={promote}
              className="rounded-sm border border-cmd-green/50 px-3 py-1.5 text-[9px] uppercase text-cmd-green transition-colors hover:enabled:bg-cmd-green/10 disabled:opacity-40"
            >
              {promoted ? "Promoted" : promoting ? "Promoting…" : "Promote Challenger"}
            </button>
            {comparison.verdict !== "challenger_recommended" && <span className="text-[8px] text-cmd-textDim">Only a "challenger recommended" verdict can be promoted.</span>}
          </div>
          {promoteError && <div className="mt-1.5 text-[9px] text-cmd-red">{promoteError}</div>}
        </Glass>
      )}

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Current Champion — {strategyFamily}</TerminalLabel>
          <button
            type="button"
            onClick={() => loadFamily(strategyFamily)}
            disabled={familyLoading || !strategyFamily.trim()}
            className="rounded-sm border border-cmd-border px-2 py-1 text-[8px] uppercase text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
          >
            {familyLoading ? "Loading…" : "Refresh"}
          </button>
        </div>
        {!family && <EmptyState>Compare a champion and challenger, or refresh, to see this family's real record.</EmptyState>}
        {family && !family.current && <EmptyState>No real champion has ever been promoted for this family yet.</EmptyState>}
        {family?.current && (
          <div className="grid grid-cols-2 gap-x-3 sm:grid-cols-4">
            <DataRow label="Definition" value={family.current.definitionId} />
            <DataRow label="Version" value={family.current.definitionVersion} />
            <DataRow label="Promoted by" value={AGENT_PROFILES[family.current.promotedBy].name} />
            <DataRow label="Promoted at" value={new Date(family.current.promotedAt).toLocaleString()} />
          </div>
        )}
        {family && family.history.length > 1 && (
          <div className="mt-2 space-y-1">
            <div className="text-[8px] uppercase tracking-wide text-cmd-textDim">Lineage ({family.history.length} real promotions, never deleted)</div>
            {family.history.map((h) => (
              <div key={h.id} className="border-t border-cmd-border/40 py-1 text-[9px] text-cmd-textDim">
                v{h.definitionVersion} — {AGENT_PROFILES[h.promotedBy].name} — {h.reasoning}
              </div>
            ))}
          </div>
        )}
        {family && family.comparisons.length > 0 && (
          <div className="mt-2 space-y-1">
            <div className="text-[8px] uppercase tracking-wide text-cmd-textDim">Every real comparison on file for this family ({family.comparisons.length})</div>
            {family.comparisons.map((c) => (
              <div key={c.id} className="flex items-center justify-between gap-2 border-t border-cmd-border/40 py-1 text-[9px]">
                <span className="text-cmd-textDim">{c.hypothesis}</span>
                <StatusPill tone={VERDICT_TONE[c.verdict]}>{c.verdict.replace(/_/g, " ")}</StatusPill>
              </div>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}
