import { useState } from "react";
import { api } from "@/net/api";
import type { CompiledStrategyBacktestResult, CompiledStrategyDefinition } from "@/types";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";
import { BucketGroup } from "./EmaPullbackResearchView";

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

  const compile = () => {
    setCompiling(true);
    setCompileError(null);
    setBacktest(null);
    api
      .compileStrategy(name, sourceText)
      .then(setDefinition)
      .catch((err) => setCompileError(err instanceof Error ? err.message : String(err)))
      .finally(() => setCompiling(false));
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
            <button
              type="button"
              disabled={backtesting}
              onClick={runBacktest}
              className="mt-2 rounded-sm border border-cmd-border px-3 py-1.5 text-[9px] uppercase text-cmd-textDim transition-colors hover:enabled:border-cmd-cyan/50 hover:enabled:text-cmd-cyan disabled:opacity-40"
            >
              {backtesting ? "Backtesting…" : "Backtest This Definition"}
            </button>
          )}
          {backtestError && <div className="mt-1.5 text-[9px] text-cmd-red">{backtestError}</div>}
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

      {!definition && !compiling && (
        <Glass className="p-3">
          <EmptyState>Enter a strategy description and compile it — the CEO's own worked example is pre-filled above.</EmptyState>
        </Glass>
      )}
    </div>
  );
}
