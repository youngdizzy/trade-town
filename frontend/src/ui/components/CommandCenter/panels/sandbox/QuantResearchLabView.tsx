import { useEffect, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { api } from "@/net/api";
import { AGENT_IDS } from "@/types";
import type { AgentId, CompiledStrategyDefinition, QuantResearchExperiment, StrategyTournamentResult } from "@/types";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";

const CEO_EXAMPLE_TEXT =
  "Buy when price closes above the 50 EMA, then wait for at least two bearish candles, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R.";

const OUTCOME_TONE: Record<string, "green" | "amber" | "red"> = {
  promising: "green",
  inconclusive: "amber",
  rejected: "red",
};

const OVERFITTING_TONE: Record<string, "green" | "amber" | "red" | "purple"> = {
  robust: "green",
  fragile: "amber",
  overfit_suspected: "amber",
  oos_failure: "red",
  insufficient_data: "purple",
  pending_validation: "purple",
};

// CEO directive "Professional Quant Firm Phase 41-45," Feature 43 —
// Round 9 (Regime Stability).
const REGIME_STABILITY_TONE: Record<string, "green" | "amber" | "red" | "purple"> = {
  regime_validated: "green",
  no_validated_regime: "red",
  insufficient_data: "purple",
};

function VerdictPill({ verdict, tones }: { verdict: string; tones: Record<string, "green" | "amber" | "red" | "purple"> }) {
  return <StatusPill tone={tones[verdict] ?? "neutral"}>{verdict.replace(/_/g, " ")}</StatusPill>;
}

// CEO directive "Quant Research Factory / Strategy Discovery Engine,"
// Phase 17 — a strategy whose compiledDefinitionId matches a filed
// experiment's real definitionId and has since reached at least this
// stage is a real, verifiable "promoted from research" case — not a
// fabricated status, since Strategy.stage is itself already the real,
// evidence-gated pipeline (app/sandbox.py's STAGE_ORDER).
const PROMOTED_STAGES = new Set(["paper_trading", "limited_live_capital", "company_review", "approved"]);

/**
 * CEO directive "Quant Research Factory / Strategy Discovery Engine,"
 * Phase 17 — a real CEO-facing overview, not another giant tab. Per
 * the directive's own research-first audit: this codebase has no
 * PROPOSED/QUEUED/RUNNING concept (every experiment resolves
 * synchronously the moment it's filed — app/quant_research_lab.py's
 * `_classify_outcome()` runs inline), so this never fabricates a queue
 * or an in-progress state — it reads the real, already-persisted
 * `outcome` on every filed `QuantResearchExperiment` instead, plus a
 * real cross-reference against `Strategy.compiledDefinitionId` for
 * which research has genuinely been promoted onward.
 */
function ResearchFactoryOverview() {
  const { strategies } = useGameStore();
  const [experiments, setExperiments] = useState<QuantResearchExperiment[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .searchQuantResearchExperiments()
      .then(setExperiments)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Glass className="p-3"><EmptyState>Loading…</EmptyState></Glass>;
  if (experiments === null) return null;

  const promising = experiments.filter((e) => e.outcome === "promising");
  const rejected = experiments.filter((e) => e.outcome === "rejected");
  const inconclusive = experiments.filter((e) => e.outcome === "inconclusive");
  const promotedDefinitionIds = new Set(strategies.filter((s) => s.compiledDefinitionId !== null && PROMOTED_STAGES.has(s.stage)).map((s) => s.compiledDefinitionId));
  const promoted = experiments.filter((e) => promotedDefinitionIds.has(e.record.definitionId));
  const recentRejections = [...rejected].slice(0, 5);

  return (
    <Glass className="border border-cmd-purple/30 p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Research Factory Overview</TerminalLabel>
        <span className="text-[9px] text-cmd-textDim">{experiments.length} experiment{experiments.length === 1 ? "" : "s"} on file</span>
      </div>
      <div className="text-[9px] text-cmd-textDim">
        Research runs synchronously — every filed experiment resolves the instant it's submitted. There is no queue or in-progress state to report honestly.
      </div>
      <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-4">
        <DataRow label="Promising" value={promising.length} valueClassName="text-cmd-green" />
        <DataRow label="Rejected" value={rejected.length} valueClassName="text-cmd-red" />
        <DataRow label="Inconclusive" value={inconclusive.length} valueClassName="text-cmd-amber" />
        <DataRow label="Promoted Onward" value={promoted.length} valueClassName="text-cmd-cyan" />
      </div>
      {experiments.length === 0 ? (
        <EmptyState>No research filed yet — compile a definition below and file it as an experiment to start the record.</EmptyState>
      ) : (
        <>
          <div className="mt-2 border-t border-cmd-border/50 pt-2 text-[9px] uppercase text-cmd-textDim">Recent Rejections</div>
          {recentRejections.length === 0 ? (
            <p className="mt-1 text-[9px] text-cmd-textDim">Nothing rejected yet.</p>
          ) : (
            <div className="mt-1 space-y-1">
              {recentRejections.map((e) => (
                <div key={e.id} className="rounded-sm border border-cmd-red/30 bg-cmd-red/5 p-1.5 text-[9px]">
                  <div className="flex items-center justify-between">
                    <span className="text-cmd-text">{e.record.definitionName}</span>
                    <span className="text-cmd-textDim">{e.researcherAgentId}</span>
                  </div>
                  <div className="mt-0.5 text-cmd-textDim">{e.outcomeReason}</div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </Glass>
  );
}

/**
 * CEO directive "Professional Quant Firm Phase" — Features 36 (Quant
 * Research Lab), 37 (real, persisted strategy version history), and 40
 * (the Quant Strategy Tournament). Compiles a definition once (reusing
 * the same real POST /compile-strategy call the Strategy Compiler tab
 * uses), then offers three real, separate actions against it: file it
 * as a hypothesis-driven experiment into the permanent Research Lab
 * archive, register it as a real persisted version, or add it to an
 * in-memory tournament roster to compare against other compiled
 * definitions. See each backend module's own docstring (app/
 * quant_research_lab.py, app/strategy_registry.py, app/
 * strategy_tournament.py) for the full, disclosed methodology.
 */
export function QuantResearchLabView() {
  const [name, setName] = useState("50 EMA Pullback");
  const [sourceText, setSourceText] = useState(CEO_EXAMPLE_TEXT);
  const [definition, setDefinition] = useState<CompiledStrategyDefinition | null>(null);
  const [compiling, setCompiling] = useState(false);
  const [compileError, setCompileError] = useState<string | null>(null);

  const [hypothesis, setHypothesis] = useState("");
  const [researcher, setResearcher] = useState<AgentId>("quant");
  const [filing, setFiling] = useState(false);
  const [fileResult, setFileResult] = useState<Awaited<ReturnType<typeof api.submitQuantResearchExperiment>> | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  const [versions, setVersions] = useState<CompiledStrategyDefinition[]>([]);
  const [registering, setRegistering] = useState(false);
  const [registerError, setRegisterError] = useState<string | null>(null);

  const [roster, setRoster] = useState<CompiledStrategyDefinition[]>([]);
  const [tournament, setTournament] = useState<StrategyTournamentResult | null>(null);
  const [runningTournament, setRunningTournament] = useState(false);
  const [tournamentError, setTournamentError] = useState<string | null>(null);

  const [searchResults, setSearchResults] = useState<QuantResearchExperiment[] | null>(null);
  const [searching, setSearching] = useState(false);

  const compile = () => {
    setCompiling(true);
    setCompileError(null);
    setFileResult(null);
    api
      .compileStrategy(name, sourceText)
      .then((d) => {
        setDefinition(d);
        return api.getStrategyVersions(d.name).then(setVersions);
      })
      .catch((err) => setCompileError(err instanceof Error ? err.message : String(err)))
      .finally(() => setCompiling(false));
  };

  const fileExperiment = () => {
    if (!definition || !hypothesis.trim()) return;
    setFiling(true);
    setFileError(null);
    api
      .submitQuantResearchExperiment(definition, hypothesis.trim(), researcher)
      .then(setFileResult)
      .catch((err) => setFileError(err instanceof Error ? err.message : String(err)))
      .finally(() => setFiling(false));
  };

  const registerVersion = () => {
    if (!definition) return;
    setRegistering(true);
    setRegisterError(null);
    api
      .registerStrategyVersion(name, sourceText)
      .then((newDefinition) => api.getStrategyVersions(newDefinition.name).then(setVersions))
      .catch((err) => setRegisterError(err instanceof Error ? err.message : String(err)))
      .finally(() => setRegistering(false));
  };

  const addToRoster = () => {
    if (!definition || roster.some((d) => d.id === definition.id)) return;
    setRoster([...roster, definition]);
    setTournament(null);
  };

  const runTournament = () => {
    if (roster.length < 2) return;
    setRunningTournament(true);
    setTournamentError(null);
    api
      .runStrategyTournament(roster)
      .then(setTournament)
      .catch((err) => setTournamentError(err instanceof Error ? err.message : String(err)))
      .finally(() => setRunningTournament(false));
  };

  const runSearch = () => {
    setSearching(true);
    api
      .searchQuantResearchExperiments()
      .then(setSearchResults)
      .finally(() => setSearching(false));
  };

  return (
    <div className="space-y-3">
      <ResearchFactoryOverview />

      <Glass className="p-3">
        <TerminalLabel>Compile a Definition</TerminalLabel>
        <p className="mt-1 text-[9px] text-cmd-textDim">
          Same real, deterministic compiler as the Strategy Compiler tab. Compile once here, then file it into the Research Lab, register a real persisted
          version, or add it to a tournament roster below.
        </p>
        <div className="mt-2 space-y-1.5">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Strategy name"
            className="w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          />
          <textarea
            value={sourceText}
            onChange={(e) => setSourceText(e.target.value)}
            rows={3}
            placeholder="Describe the strategy in plain English…"
            className="w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          />
          <button
            type="button"
            disabled={compiling || !sourceText.trim() || !name.trim()}
            onClick={compile}
            className="rounded-sm border border-cmd-border px-3 py-1.5 text-[9px] uppercase text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
          >
            {compiling ? "Compiling…" : "Compile"}
          </button>
        </div>
        {compileError && <div className="mt-1.5 text-[9px] text-cmd-red">{compileError}</div>}
      </Glass>

      {definition && definition.status === "compiled" && (
        <>
          <Glass className="p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>Feature 36 — File to the Quant Research Lab</TerminalLabel>
              <span className="text-[8px] text-cmd-textDim">{definition.name} v{definition.version}</span>
            </div>
            <p className="text-[9px] text-cmd-textDim">
              A real, testable hypothesis — never a hard-coded conclusion. The system checks the evidence independently and files a real, permanent,
              searchable record either way.
            </p>
            <div className="mt-2 space-y-1.5">
              <textarea
                value={hypothesis}
                onChange={(e) => setHypothesis(e.target.value)}
                rows={2}
                placeholder='e.g. "The 50 EMA breakout + pullback setup performs better during the London session than at other times."'
                className="w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
              />
              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={researcher}
                  onChange={(e) => setResearcher(e.target.value as AgentId)}
                  className="rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
                >
                  {AGENT_IDS.map((a) => (
                    <option key={a} value={a}>
                      {a}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  disabled={filing || !hypothesis.trim()}
                  onClick={fileExperiment}
                  className="rounded-sm border border-cmd-border px-3 py-1.5 text-[9px] uppercase text-cmd-textDim transition-colors hover:enabled:border-cmd-purple/50 hover:enabled:text-cmd-purple disabled:opacity-40"
                >
                  {filing ? "Filing…" : "File Experiment"}
                </button>
              </div>
            </div>
            {fileError && <div className="mt-1.5 text-[9px] text-cmd-red">{fileError}</div>}
            {fileResult && (
              <div className="mt-2 space-y-1.5">
                <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] text-cmd-textDim">Filed as {fileResult.experiment.id}</span>
                    <VerdictPill verdict={fileResult.experiment.outcome} tones={OUTCOME_TONE} />
                  </div>
                  <div className="mt-1 text-[9px] text-cmd-text">{fileResult.experiment.outcomeReason}</div>
                </div>
                {fileResult.similarExperiments.length > 0 && (
                  <div className="rounded-sm border border-cmd-amber/40 bg-cmd-amber/5 p-1.5">
                    <div className="text-[9px] uppercase text-cmd-amber">Possible duplicate research on file</div>
                    {fileResult.similarExperiments.map((s) => (
                      <div key={s.experimentId} className="mt-1 border-t border-cmd-border/40 pt-1 text-[9px] first:mt-0 first:border-0 first:pt-0">
                        <div className="text-cmd-textDim">
                          {s.experimentId}: {s.reason}
                        </div>
                        {s.outcome === "rejected" ? (
                          <div className="mt-0.5 text-cmd-red">⚠ REJECTED — this idea already failed: {s.outcomeReason}</div>
                        ) : (
                          <div className="mt-0.5 text-cmd-textDim">
                            Prior outcome: <VerdictPill verdict={s.outcome} tones={OUTCOME_TONE} />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Glass>

          <Glass className="p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>Feature 37 — Persisted Version History</TerminalLabel>
              <button
                type="button"
                disabled={registering}
                onClick={registerVersion}
                className="rounded-sm border border-cmd-border px-2.5 py-1 text-[9px] uppercase text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
              >
                {registering ? "Registering…" : "Register This Text as a New Version"}
              </button>
            </div>
            {registerError && <div className="mt-1.5 text-[9px] text-cmd-red">{registerError}</div>}
            {versions.length === 0 ? (
              <p className="mt-1 text-[9px] text-cmd-textDim">Never registered — a compile preview alone is not persisted. Register to start real version history.</p>
            ) : (
              <div className="mt-1.5 space-y-1">
                {versions.map((v) => (
                  <div key={v.version} className="flex items-center justify-between rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                    <span className="text-cmd-cyan">v{v.version}</span>
                    <span className="truncate text-cmd-textDim">{v.sourceText}</span>
                  </div>
                ))}
              </div>
            )}
          </Glass>

          <Glass className="p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>Feature 40 — Tournament Roster ({roster.length})</TerminalLabel>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={roster.some((d) => d.id === definition.id)}
                  onClick={addToRoster}
                  className="rounded-sm border border-cmd-border px-2.5 py-1 text-[9px] uppercase text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
                >
                  Add To Roster
                </button>
                <button
                  type="button"
                  disabled={roster.length < 2 || runningTournament}
                  onClick={runTournament}
                  className="rounded-sm border border-cmd-border px-2.5 py-1 text-[9px] uppercase text-cmd-textDim transition-colors hover:enabled:border-cmd-purple/50 hover:enabled:text-cmd-purple disabled:opacity-40"
                >
                  {runningTournament ? "Running…" : "Run Tournament"}
                </button>
              </div>
            </div>
            {roster.length === 0 ? (
              <p className="text-[9px] text-cmd-textDim">Compile at least 2 definitions and add each to the roster to run a tournament.</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {roster.map((d) => (
                  <span key={d.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 px-1.5 py-0.5 text-[9px] text-cmd-text">
                    {d.name} v{d.version}
                  </span>
                ))}
              </div>
            )}
            {tournamentError && <div className="mt-1.5 text-[9px] text-cmd-red">{tournamentError}</div>}
          </Glass>
        </>
      )}

      {tournament && (
        <>
          <Glass className="overflow-x-auto p-3">
            <TerminalLabel>Tournament Comparison — every real dimension, never a fabricated composite score</TerminalLabel>
            <table className="mt-2 w-full min-w-[720px] border-collapse text-[9px]">
              <thead>
                <tr className="border-b border-cmd-border/60 text-left text-cmd-textDim">
                  <th className="py-1 pr-2">Strategy</th>
                  <th className="py-1 pr-2">Trades</th>
                  <th className="py-1 pr-2">Expectancy R</th>
                  <th className="py-1 pr-2">Profit Factor</th>
                  <th className="py-1 pr-2">Sharpe</th>
                  <th className="py-1 pr-2">Max DD R</th>
                  <th className="py-1 pr-2">Walk-Fwd</th>
                  <th className="py-1 pr-2">Overfitting</th>
                  <th className="py-1 pr-2">Regime Stability</th>
                  <th className="py-1 pr-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {tournament.entries.map((e) => (
                  <tr key={e.definitionId} className="border-b border-cmd-border/30 tabular-nums">
                    <td className="py-1 pr-2 text-cmd-text">
                      {e.definitionName} v{e.definitionVersion}
                    </td>
                    <td className="py-1 pr-2 text-cmd-textDim">{e.tradeCount}</td>
                    <td className="py-1 pr-2 text-cmd-textDim">{e.expectancyR !== null ? e.expectancyR.toFixed(2) : "—"}</td>
                    <td className="py-1 pr-2 text-cmd-textDim">{e.profitFactor !== null ? e.profitFactor.toFixed(2) : "—"}</td>
                    <td className="py-1 pr-2 text-cmd-textDim">{e.sharpeRatio !== null ? e.sharpeRatio.toFixed(2) : "—"}</td>
                    <td className="py-1 pr-2 text-cmd-textDim">{e.maxDrawdownR !== null ? e.maxDrawdownR.toFixed(2) : "—"}</td>
                    <td className="py-1 pr-2 text-cmd-textDim">{e.walkForwardVerdict.replace(/_/g, " ")}</td>
                    <td className="py-1 pr-2">
                      <VerdictPill verdict={e.overfittingVerdict} tones={OVERFITTING_TONE} />
                    </td>
                    <td className="py-1 pr-2" title={e.regimeStabilityDetail}>
                      <VerdictPill verdict={e.regimeStabilityVerdict} tones={REGIME_STABILITY_TONE} />
                    </td>
                    <td className="py-1 pr-2">
                      {e.eliminatedAtRound !== null ? (
                        <span className="text-cmd-red">eliminated R{e.eliminatedAtRound}</span>
                      ) : tournament.productionCandidates.includes(e.definitionId) ? (
                        <span className="text-cmd-green">production candidate</span>
                      ) : (
                        <span className="text-cmd-textDim">surviving</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Named Superlatives — one real dimension per slot, never blended</TerminalLabel>
            <div className="mt-1.5 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {[
                ["Highest Expectancy", tournament.highestExpectancy],
                ["Highest Profit Factor", tournament.highestProfitFactor],
                ["Highest Sharpe", tournament.highestSharpeRatio],
                ["Lowest Max Drawdown", tournament.lowestMaxDrawdown],
                ["Most Walk-Forward Stable", tournament.mostWalkForwardStable],
              ].map(([label, slot]) => (
                <div key={label as string} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                  <div className="text-cmd-textDim">{label as string}</div>
                  {slot ? (
                    <>
                      <div className="mt-0.5 text-cmd-cyan">{(slot as { strategyName: string }).strategyName}</div>
                      <div className="tabular-nums text-cmd-text">{(slot as { metricValue: number }).metricValue.toFixed(2)}</div>
                    </>
                  ) : (
                    <div className="mt-0.5 text-cmd-textDim">No real value yet</div>
                  )}
                </div>
              ))}
            </div>
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Elimination Rounds</TerminalLabel>
            <div className="mt-1.5 space-y-1">
              {tournament.rounds.map((r) => (
                <div key={r.roundNumber} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                  <div className="flex items-center justify-between">
                    <span className="text-cmd-cyan">
                      Round {r.roundNumber} — {r.name}
                    </span>
                    {r.blocked && <StatusPill tone="purple">architecturally blocked</StatusPill>}
                  </div>
                  <div className="mt-0.5 text-cmd-textDim">{r.description}</div>
                  <div className="mt-0.5 text-cmd-text">{r.detail}</div>
                </div>
              ))}
            </div>
          </Glass>

          {tournament.pairCorrelations.length > 0 && (
            <Glass className="p-3">
              <TerminalLabel>Round 7 — Real Pairwise Return Correlation (not a full portfolio backtest)</TerminalLabel>
              <div className="mt-1.5 space-y-1">
                {tournament.pairCorrelations.map((p, i) => {
                  const nameA = tournament.entries.find((e) => e.definitionId === p.definitionIdA)?.definitionName ?? p.definitionIdA;
                  const nameB = tournament.entries.find((e) => e.definitionId === p.definitionIdB)?.definitionName ?? p.definitionIdB;
                  return (
                    <div key={i} className="flex items-center justify-between rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                      <span className="text-cmd-textDim">
                        {nameA} vs. {nameB} ({p.symbol})
                      </span>
                      <span className={`tabular-nums ${p.correlation === null ? "text-cmd-textDim" : Math.abs(p.correlation) >= 0.6 ? "text-cmd-amber" : "text-cmd-text"}`}>
                        {p.correlation !== null ? p.correlation.toFixed(2) : `— (${p.windowsCompared} window${p.windowsCompared === 1 ? "" : "s"})`}
                      </span>
                    </div>
                  );
                })}
              </div>
            </Glass>
          )}

          <Glass className="p-3">
            <p className="text-[8px] italic text-cmd-textDim">{tournament.dataHonestyNote}</p>
          </Glass>
        </>
      )}

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Search Filed Experiments</TerminalLabel>
          <button
            type="button"
            disabled={searching}
            onClick={runSearch}
            className="rounded-sm border border-cmd-border px-2.5 py-1 text-[9px] uppercase text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
          >
            {searching ? "Searching…" : "Load All"}
          </button>
        </div>
        {searchResults === null ? (
          <EmptyState>Nothing loaded yet — every filed experiment is permanent and searchable.</EmptyState>
        ) : searchResults.length === 0 ? (
          <EmptyState>No experiments filed yet.</EmptyState>
        ) : (
          <div className="space-y-1">
            {searchResults.map((exp) => (
              <div key={exp.id} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="flex items-center justify-between">
                  <span className="text-cmd-cyan">{exp.record.definitionName}</span>
                  <VerdictPill verdict={exp.outcome} tones={OUTCOME_TONE} />
                </div>
                <div className="mt-0.5 text-cmd-text">{exp.hypothesis}</div>
                <div className="mt-0.5 grid grid-cols-2 gap-x-3 sm:grid-cols-4">
                  <DataRow label="Researcher" value={exp.researcherAgentId} />
                  <DataRow label="Trades" value={exp.record.backtest.overall.tradeCount} />
                </div>
              </div>
            ))}
          </div>
        )}
      </Glass>

      {!definition && !compiling && (
        <Glass className="p-3">
          <EmptyState>Compile a strategy above to file research, register a version, or add it to a tournament roster.</EmptyState>
        </Glass>
      )}
    </div>
  );
}
