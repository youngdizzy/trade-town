import { useState } from "react";
import { api } from "@/net/api";
import type { CompiledStrategyBacktestResult, CompiledStrategyDefinition, ResearchExperimentRecord } from "@/types";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";
import { BucketGroup } from "./EmaPullbackResearchView";

const CONCLUSION_TONE: Record<string, "green" | "amber" | "red" | "purple"> = {
  INVALID: "red",
  REJECTED: "red",
  "INSUFFICIENT EVIDENCE": "amber",
  FRAGILE: "amber",
  CREDIBLE: "green",
};

function conclusionTone(conclusion: string): "green" | "amber" | "red" | "purple" {
  const prefix = Object.keys(CONCLUSION_TONE).find((key) => conclusion.startsWith(key));
  return (prefix && CONCLUSION_TONE[prefix]) || "purple";
}

const CEO_EXAMPLE_TEXT =
  "Buy when price closes above the 50 EMA, then wait for at least two bearish candles, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R.";

const STATUS_TONE: Record<string, "green" | "amber" | "red"> = {
  compiled: "green",
  ambiguous: "amber",
  invalid: "red",
};

/**
 * CEO directive "Professional Quant Trading Firm — Quant Intelligence +
 * Market Analysis Completion Phase," Phase F — the English-language
 * strategy compiler + generic backtest engine. A real, deterministic
 * pattern-matcher (never an LLM guess — see backend/app/
 * strategy_compiler.py's own module docstring), so vague phrases like
 * "strong breakout" are refused, not silently converted into an invented
 * threshold. Stateless: nothing typed or compiled here is persisted.
 *
 * That same directive's "Next Research + Validation Pass" adds "Run
 * Full Research Experiment" — one call bundling a real backtest, walk-
 * forward stability test, one-parameter-at-a-time stop/target
 * sensitivity sweep, transaction-cost/slippage sensitivity, and a
 * structural look-ahead audit for this compiled definition, packaged
 * with one disclosed, deterministic conclusion-synthesis rule (see
 * backend/app/research_experiment.py). Never a recommendation to trade
 * — see each section's own real verdict and detail.
 */
export function StrategyCompilerView() {
  const [name, setName] = useState("50 EMA Pullback");
  const [sourceText, setSourceText] = useState(CEO_EXAMPLE_TEXT);
  const [definition, setDefinition] = useState<CompiledStrategyDefinition | null>(null);
  const [compiling, setCompiling] = useState(false);
  const [compileError, setCompileError] = useState<string | null>(null);
  const [backtest, setBacktest] = useState<CompiledStrategyBacktestResult | null>(null);
  const [backtesting, setBacktesting] = useState(false);
  const [backtestError, setBacktestError] = useState<string | null>(null);
  const [experiment, setExperiment] = useState<ResearchExperimentRecord | null>(null);
  const [experimentRunning, setExperimentRunning] = useState(false);
  const [experimentError, setExperimentError] = useState<string | null>(null);

  const compile = () => {
    setCompiling(true);
    setCompileError(null);
    setBacktest(null);
    setExperiment(null);
    api
      .compileStrategy(name, sourceText)
      .then(setDefinition)
      .catch((err) => setCompileError(err instanceof Error ? err.message : String(err)))
      .finally(() => setCompiling(false));
  };

  const runResearchExperiment = () => {
    if (!definition) return;
    setExperimentRunning(true);
    setExperimentError(null);
    api
      .runResearchExperiment(definition)
      .then(setExperiment)
      .catch((err) => setExperimentError(err instanceof Error ? err.message : String(err)))
      .finally(() => setExperimentRunning(false));
  };

  const runBacktest = () => {
    if (!definition) return;
    setBacktesting(true);
    setBacktestError(null);
    api
      .backtestCompiledStrategy(definition)
      .then(setBacktest)
      .catch((err) => setBacktestError(err instanceof Error ? err.message : String(err)))
      .finally(() => setBacktesting(false));
  };

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <TerminalLabel>English Strategy → Structured, Reproducible Definition</TerminalLabel>
        <p className="mt-1 text-[9px] text-cmd-textDim">
          A real, deterministic pattern-matcher over a disclosed, limited vocabulary — never an LLM guess. Vague phrases ("strong breakout," "significant volume") are
          refused as ambiguous, never silently converted into an invented threshold.
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
            rows={4}
            placeholder="Describe the strategy in plain English…"
            className="w-full rounded-sm border border-cmd-border bg-cmd-bg/60 px-2 py-1.5 text-[9px] text-cmd-text outline-none focus:border-cmd-cyan/50"
          />
          <button
            type="button"
            disabled={compiling || !sourceText.trim() || !name.trim()}
            onClick={compile}
            className="rounded-sm border border-cmd-border px-3 py-1.5 text-[9px] uppercase text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
          >
            {compiling ? "Compiling…" : "Compile Strategy"}
          </button>
        </div>
        {compileError && <div className="mt-1.5 text-[9px] text-cmd-red">{compileError}</div>}
      </Glass>

      {definition && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Compiled Definition — {definition.name}</TerminalLabel>
            <StatusPill tone={STATUS_TONE[definition.status]}>{definition.status}</StatusPill>
          </div>
          <div className="grid grid-cols-2 gap-x-3 sm:grid-cols-4">
            <DataRow label="Version" value={definition.version} />
            <DataRow label="Timeframe" value={definition.timeframe} />
            <DataRow label="Steps" value={definition.sequence.length} />
            <DataRow label="Ambiguities" value={definition.ambiguities.length} valueClassName={definition.ambiguities.length > 0 ? "text-cmd-amber" : undefined} />
          </div>
          <div className="mt-1.5 text-[9px] text-cmd-text">{definition.detail}</div>

          {definition.sequence.length > 0 && (
            <div className="mt-1.5 space-y-1">
              {definition.sequence.map((step) => (
                <div key={step.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                  <span className="text-cmd-cyan uppercase">{step.stepType}</span> — <span className="text-cmd-textDim">{step.detail}</span>
                </div>
              ))}
            </div>
          )}

          {definition.stop && (
            <div className="mt-1.5 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
              <span className="text-cmd-textDim">Stop:</span> {definition.stop.method}
              {definition.stop.atrPeriod !== null && ` (ATR${definition.stop.atrPeriod} × ${definition.stop.atrMultiplier})`}
              {definition.stop.percent !== null && ` (${definition.stop.percent}%)`}
            </div>
          )}
          {definition.target && (
            <div className="mt-1 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
              <span className="text-cmd-textDim">Target:</span> {definition.target.method === "r_multiple" ? `${definition.target.value}R` : `${definition.target.value}%`}
            </div>
          )}

          {definition.ambiguities.length > 0 && (
            <div className="mt-1.5 space-y-1">
              {definition.ambiguities.map((a, i) => (
                <div key={i} className="rounded-sm border border-cmd-amber/40 bg-cmd-amber/5 p-1.5 text-[9px]">
                  <div className="text-cmd-amber">"{a.phrase}"</div>
                  <div className="mt-0.5 text-cmd-textDim">{a.reason}</div>
                  {a.suggestedResolution && <div className="mt-0.5 text-cmd-textDim italic">{a.suggestedResolution}</div>}
                </div>
              ))}
            </div>
          )}

          {definition.status === "compiled" && (
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={backtesting}
                onClick={runBacktest}
                className="rounded-sm border border-cmd-border px-3 py-1.5 text-[9px] uppercase text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
              >
                {backtesting ? "Backtesting…" : "Backtest This Definition"}
              </button>
              <button
                type="button"
                disabled={experimentRunning}
                onClick={runResearchExperiment}
                className="rounded-sm border border-cmd-border px-3 py-1.5 text-[9px] uppercase text-cmd-textDim transition-colors hover:enabled:border-cmd-purple/50 hover:enabled:text-cmd-purple disabled:opacity-40"
              >
                {experimentRunning ? "Running Full Research Experiment…" : "Run Full Research Experiment"}
              </button>
            </div>
          )}
          {backtestError && <div className="mt-1.5 text-[9px] text-cmd-red">{backtestError}</div>}
          {experimentError && <div className="mt-1.5 text-[9px] text-cmd-red">{experimentError}</div>}
        </Glass>
      )}

      {backtest && (
        <>
          <BucketGroup title={`Overall — ${backtest.symbolsTested.length} symbols, ${backtest.candlesPerSymbol.toLocaleString()} candles each`} buckets={[backtest.overall]} />
          <BucketGroup title="Session Breakdown" buckets={backtest.sessionBreakdown} />
          <BucketGroup title="Instrument Breakdown" buckets={backtest.instrumentBreakdown} />
          {backtest.modelValidation && (
            <Glass className="p-3">
              <div className="mb-1.5 flex items-center justify-between">
                <TerminalLabel>Model Validation</TerminalLabel>
                <StatusPill tone={backtest.modelValidation.verdict === "approved" ? "green" : backtest.modelValidation.verdict === "rejected" ? "red" : "amber"}>
                  {backtest.modelValidation.verdict.replace(/_/g, " ")}
                </StatusPill>
              </div>
              <div className="text-[9px] text-cmd-text">{backtest.modelValidation.evidenceSummary}</div>
            </Glass>
          )}
          <Glass className="p-3">
            <p className="text-[8px] italic text-cmd-textDim">{backtest.dataHonestyNote}</p>
          </Glass>
        </>
      )}

      {experiment && (
        <>
          <Glass className="p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>Research Experiment — {experiment.definitionName}</TerminalLabel>
              <StatusPill tone={conclusionTone(experiment.conclusion)}>{experiment.conclusion.split(" — ")[0]}</StatusPill>
            </div>
            <div className="text-[9px] text-cmd-text">{experiment.conclusion}</div>
            <div className="mt-1.5 grid grid-cols-2 gap-x-3 sm:grid-cols-4">
              <DataRow label="Symbols" value={experiment.symbolsTested.length} />
              <DataRow label="Candles/Symbol" value={experiment.candlesPerSymbol.toLocaleString()} />
              <DataRow label="Real Trades" value={experiment.backtest.overall.tradeCount} />
            </div>
          </Glass>

          <Glass className="p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>Walk-Forward Stability</TerminalLabel>
              <StatusPill tone={experiment.walkForward.verdict === "stable" ? "green" : experiment.walkForward.verdict === "unstable" ? "red" : "amber"}>{experiment.walkForward.verdict.replace(/_/g, " ")}</StatusPill>
            </div>
            <div className="text-[9px] text-cmd-text">{experiment.walkForward.detail}</div>
            {experiment.walkForward.symbols.length > 0 && (
              <div className="mt-1.5 space-y-1">
                {experiment.walkForward.symbols.map((s) => (
                  <div key={s.symbol} className="rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                    <div className="flex items-center justify-between">
                      <span className="text-cmd-cyan">{s.symbol}</span>
                      <span className="tabular-nums text-cmd-textDim">
                        {s.positiveWindowCount}/{s.evaluatedWindowCount} evaluated windows positive
                      </span>
                    </div>
                    <div className="mt-0.5 flex flex-wrap gap-1">
                      {s.windows.map((w) => (
                        <span
                          key={w.windowIndex}
                          className={`rounded-sm border px-1 py-0.5 tabular-nums ${
                            w.bucket.expectancyR === null ? "border-cmd-border/60 text-cmd-textDim" : w.bucket.expectancyR > 0 ? "border-cmd-green/40 text-cmd-green" : "border-cmd-red/40 text-cmd-red"
                          }`}
                        >
                          W{w.windowIndex}: {w.bucket.expectancyR !== null ? `${w.bucket.expectancyR > 0 ? "+" : ""}${w.bucket.expectancyR.toFixed(2)}R` : "—"}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Glass>

          <Glass className="p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>Parameter Sensitivity</TerminalLabel>
              <StatusPill tone={experiment.parameterSensitivity.verdict === "robust" ? "green" : experiment.parameterSensitivity.verdict === "fragile" ? "red" : "amber"}>
                {experiment.parameterSensitivity.verdict.replace(/_/g, " ")}
              </StatusPill>
            </div>
            <div className="text-[9px] text-cmd-text">{experiment.parameterSensitivity.detail}</div>
            {[experiment.parameterSensitivity.stopAxis, experiment.parameterSensitivity.targetAxis].map(
              (axis) =>
                axis && (
                  <div key={axis.parameter} className="mt-1.5 rounded-sm border border-cmd-border/50 bg-cmd-bg/40 p-1.5 text-[9px]">
                    <div className="text-cmd-textDim capitalize">{axis.parameter} axis</div>
                    {axis.sweepable ? (
                      <div className="mt-0.5 flex flex-wrap gap-1">
                        {axis.points.map((p) => (
                          <span
                            key={p.label}
                            className={`rounded-sm border px-1 py-0.5 tabular-nums ${
                              p.bucket.expectancyR === null ? "border-cmd-border/60 text-cmd-textDim" : p.bucket.expectancyR > 0 ? "border-cmd-green/40 text-cmd-green" : "border-cmd-red/40 text-cmd-red"
                            }`}
                          >
                            {p.label}: {p.bucket.expectancyR !== null ? `${p.bucket.expectancyR > 0 ? "+" : ""}${p.bucket.expectancyR.toFixed(2)}R` : "—"}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <div className="mt-0.5 text-cmd-textDim">{axis.detail}</div>
                    )}
                  </div>
                )
            )}
            <p className="mt-1.5 text-[8px] italic text-cmd-textDim">{experiment.parameterSensitivity.multipleTestingNote}</p>
          </Glass>

          <Glass className="p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>Cost / Slippage Sensitivity</TerminalLabel>
              <StatusPill tone={experiment.costSensitivity.verdict === "cost_resilient" ? "green" : experiment.costSensitivity.verdict === "cost_sensitive" ? "red" : "amber"}>
                {experiment.costSensitivity.verdict.replace(/_/g, " ")}
              </StatusPill>
            </div>
            <div className="text-[9px] text-cmd-text">{experiment.costSensitivity.detail}</div>
            <div className="mt-1.5 space-y-0.5">
              {experiment.costSensitivity.scenarios.map((s) => (
                <div key={s.label} className="flex items-center justify-between text-[9px]">
                  <span className="text-cmd-textDim">
                    {s.label} ({s.costBpsPerLeg.toFixed(1)} bps/leg)
                  </span>
                  <span className={`tabular-nums ${s.bucket.expectancyR === null ? "text-cmd-textDim" : s.bucket.expectancyR > 0 ? "text-cmd-green" : "text-cmd-red"}`}>
                    {s.bucket.expectancyR !== null ? `${s.bucket.expectancyR > 0 ? "+" : ""}${s.bucket.expectancyR.toFixed(2)}R` : "—"}
                  </span>
                </div>
              ))}
            </div>
          </Glass>

          <Glass className="p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>Look-Ahead Audit</TerminalLabel>
              <StatusPill tone={experiment.lookAheadAudit.verdict === "clean" ? "green" : experiment.lookAheadAudit.verdict === "violations_found" ? "red" : "amber"}>
                {experiment.lookAheadAudit.verdict.replace(/_/g, " ")}
              </StatusPill>
            </div>
            <div className="text-[9px] text-cmd-text">{experiment.lookAheadAudit.detail}</div>
            {experiment.lookAheadAudit.violations.length > 0 && (
              <div className="mt-1.5 space-y-1">
                {experiment.lookAheadAudit.violations.map((v, i) => (
                  <div key={i} className="rounded-sm border border-cmd-red/40 bg-cmd-red/5 p-1.5 text-[9px] text-cmd-text">
                    {v.detail}
                  </div>
                ))}
              </div>
            )}
          </Glass>

          <Glass className="p-3">
            <p className="text-[8px] italic text-cmd-textDim">{experiment.dataHonestyNote}</p>
          </Glass>
        </>
      )}

      {!definition && !compiling && (
        <Glass className="p-3">
          <EmptyState>Enter a strategy description and compile it — the CEO's own worked example is pre-filled above.</EmptyState>
        </Glass>
      )}
    </div>
  );
}
