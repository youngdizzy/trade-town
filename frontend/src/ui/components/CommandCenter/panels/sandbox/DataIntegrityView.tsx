import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type {
  CompiledStrategyDefinition,
  EvidenceQualityReport,
  ExternalMarketDataStatus,
  HoldoutEvaluationResult,
  LineageIntegrityIssue,
  PortfolioRecommendation,
  PortfolioResearchReport,
} from "@/types";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";
import { BucketGroup } from "./EmaPullbackResearchView";

const DEFAULT_SOURCE_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R.";

const HOLDOUT_STATUS_TONE: Record<string, "green" | "amber" | "red"> = {
  valid: "green",
  invalid: "red",
  unavailable: "amber",
};

const EVIDENCE_STATE_TONE: Record<string, "green" | "amber" | "red" | "purple"> = {
  external_data_validated: "green",
  holdout_validated: "green",
  research_validated: "amber",
  simulated_only: "purple",
  insufficient_data: "red",
};

const PORTFOLIO_RECOMMENDATION_TONE: Record<PortfolioRecommendation, "green" | "amber" | "red" | "purple"> = {
  portfolio_robust: "green",
  diversifying: "green",
  mixed: "amber",
  high_redundancy: "amber",
  portfolio_fragile: "red",
  insufficient_evidence: "purple",
};

function BoolValue({ value }: { value: boolean | null }) {
  if (value === null) return <span className="text-cmd-textDim">NOT VERIFIED</span>;
  return <span className={value ? "text-cmd-green" : "text-cmd-red"}>{value ? "yes" : "no"}</span>;
}

/**
 * CEO directive "TradeTown — Phase 10: Real Data + True Holdout +
 * Portfolio Intelligence," Section I. Four real, on-demand research
 * tools sitting alongside the existing Research Factory sub-tabs, each
 * a thin, honest window onto its own backend endpoint — nothing here
 * computes anything client-side, and nothing here writes Champion/
 * Challenger, certification, or risk-gate state. No fake AI confidence
 * score appears anywhere in this view: every number shown is a direct,
 * disclosed read of the backend's own real response.
 */
export function DataIntegrityView() {
  return (
    <div className="space-y-3">
      <ExternalDataProvenanceCard />
      <HoldoutEvaluationCard />
      <PortfolioAnalystCard />
      <EvidenceQualityCard />
      <LineageCheckCard />
    </div>
  );
}

function ExternalDataProvenanceCard() {
  const [status, setStatus] = useState<ExternalMarketDataStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getExternalMarketDataStatus()
      .then(setStatus)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  return (
    <Glass className="p-3">
      <TerminalLabel>DATA PROVENANCE — EXTERNAL MARKET DATA</TerminalLabel>
      {error && <div className="mt-1.5 text-[9px] text-cmd-red">{error}</div>}
      {!error && !status && <div className="mt-1.5 text-[9px] text-cmd-textDim">Loading…</div>}
      {status && (
        <div className="mt-1.5 space-y-0.5">
          <DataRow
            label="Status"
            value={
              <StatusPill tone={status.available ? "green" : "amber"}>{status.available ? "AVAILABLE" : "UNAVAILABLE"}</StatusPill>
            }
          />
          <DataRow label="Provider" value={status.providerName} />
          <DataRow label="Reason" value={status.reason} />
          <p className="mt-1 text-[8px] text-cmd-textDim">
            Every other panel in this Sandbox (backtests, research, Champion/Challenger) trades against the separate, always-on
            simulated mock provider — this status describes only the opt-in real-data adapter, never a silent substitute for it.
          </p>
        </div>
      )}
    </Glass>
  );
}

function CompileForm({
  name,
  setName,
  sourceText,
  setSourceText,
}: {
  name: string;
  setName: (v: string) => void;
  sourceText: string;
  setSourceText: (v: string) => void;
}) {
  return (
    <div className="mt-1.5 grid grid-cols-1 gap-1.5 sm:grid-cols-3">
      <input
        className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 px-1.5 py-1 text-[9px] text-cmd-text sm:col-span-1"
        placeholder="Strategy name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <textarea
        className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 px-1.5 py-1 text-[9px] text-cmd-text sm:col-span-2"
        rows={2}
        value={sourceText}
        onChange={(e) => setSourceText(e.target.value)}
      />
    </div>
  );
}

function HoldoutEvaluationCard() {
  const [name, setName] = useState("Holdout Candidate");
  const [sourceText, setSourceText] = useState(DEFAULT_SOURCE_TEXT);
  const [symbol, setSymbol] = useState("AAPL");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<HoldoutEvaluationResult | null>(null);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      const definition: CompiledStrategyDefinition = await api.compileStrategy(name, sourceText);
      const evaluation = await api.evaluateHoldout(definition, symbol);
      setResult(evaluation);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  const report = result?.report;

  return (
    <Glass className="p-3">
      <TerminalLabel>HOLDOUT — TRAIN / VALIDATION / HOLDOUT EVALUATION</TerminalLabel>
      <p className="mt-1 text-[8px] text-cmd-textDim">
        Compiles the strategy above, chronologically partitions the fetched candle series (never shuffled), freezes this exact
        definition version, and reports whether the split is structurally valid — never called automatically by the mutation
        loop. No real, pre-partitioned historical dataset exists in this environment, so this partitions the same
        synthetic-but-realistic candles every other panel uses; the split LOGIC is real, the underlying candles are simulated.
      </p>
      <CompileForm name={name} setName={setName} sourceText={sourceText} setSourceText={setSourceText} />
      <div className="mt-1.5 flex items-center gap-1.5">
        <input
          className="w-20 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 px-1.5 py-1 text-[9px] text-cmd-text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
        />
        <button
          type="button"
          onClick={() => void run()}
          disabled={running}
          className="rounded-sm border border-cmd-cyan/60 bg-cmd-cyan/10 px-2 py-1 text-[9px] uppercase tracking-wide text-cmd-cyan hover:bg-cmd-cyan/20 disabled:opacity-50"
        >
          {running ? "Evaluating…" : "Compile & Evaluate"}
        </button>
      </div>
      {error && <div className="mt-1.5 text-[9px] text-cmd-red">{error}</div>}
      {report && (
        <div className="mt-2 space-y-1.5">
          <DataRow label="Status" value={<StatusPill tone={HOLDOUT_STATUS_TONE[report.status] ?? "neutral"}>{report.status.toUpperCase()}</StatusPill>} />
          <DataRow label="Detail" value={report.detail} />
          <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-3">
            {[report.train, report.validation, report.holdout].map((p) => (
              <div key={p.label} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="uppercase tracking-wide text-cmd-cyan">{p.label}</div>
                <div className="mt-0.5 text-cmd-textDim">{p.candleCount} candles</div>
                <div className="text-cmd-textDim">{p.startTimestamp ?? "—"} → {p.endTimestamp ?? "—"}</div>
              </div>
            ))}
          </div>
          <DataRow label="Chronological order valid" value={<BoolValue value={report.chronologicalOrderValid} />} />
          <DataRow label="Overlap detected" value={<BoolValue value={report.overlapDetected} />} />
          <DataRow label="Leakage detected" value={<BoolValue value={report.leakageDetected} />} />
          {report.freeze && (
            <DataRow label="Frozen version" value={`${report.freeze.definitionId} v${report.freeze.definitionVersion} @ ${report.freeze.frozenAt}`} />
          )}
          {result.bucket ? (
            <BucketGroup title="HOLDOUT-ONLY RESULT" buckets={[result.bucket]} />
          ) : (
            <p className="text-[9px] text-cmd-textDim">No holdout backtest bucket — status is not "valid", so this evidence is not shown as if it were trustworthy.</p>
          )}
        </div>
      )}
    </Glass>
  );
}

function PortfolioAnalystCard() {
  const [candidates, setCandidates] = useState<{ name: string; sourceText: string }[]>([
    { name: "Candidate A", sourceText: DEFAULT_SOURCE_TEXT },
    { name: "Candidate B", sourceText: "Buy when the 20-period RSI crosses above 30 from below, with the stop at the recent swing low and a 1.5R target." },
  ]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<PortfolioResearchReport | null>(null);

  function updateCandidate(i: number, patch: Partial<{ name: string; sourceText: string }>) {
    setCandidates((prev) => prev.map((c, idx) => (idx === i ? { ...c, ...patch } : c)));
  }

  async function run() {
    setRunning(true);
    setError(null);
    try {
      const definitions = await Promise.all(candidates.map((c) => api.compileStrategy(c.name, c.sourceText)));
      const result = await api.analyzePortfolio(definitions);
      setReport(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  return (
    <Glass className="p-3">
      <TerminalLabel>PORTFOLIO ANALYST — CROSS-STRATEGY RESEARCH</TerminalLabel>
      <p className="mt-1 text-[8px] text-cmd-textDim">
        RESEARCH INFORMATION ONLY — never promotes a strategy, never touches Champion/Challenger or any risk gate. Reuses each
        candidate's own real backtest trades; no second backtest engine.
      </p>
      <div className="mt-1.5 space-y-1.5">
        {candidates.map((c, i) => (
          <CompileForm key={i} name={c.name} setName={(v) => updateCandidate(i, { name: v })} sourceText={c.sourceText} setSourceText={(v) => updateCandidate(i, { sourceText: v })} />
        ))}
      </div>
      <button
        type="button"
        onClick={() => void run()}
        disabled={running}
        className="mt-1.5 rounded-sm border border-cmd-cyan/60 bg-cmd-cyan/10 px-2 py-1 text-[9px] uppercase tracking-wide text-cmd-cyan hover:bg-cmd-cyan/20 disabled:opacity-50"
      >
        {running ? "Analyzing…" : "Analyze Portfolio"}
      </button>
      {error && <div className="mt-1.5 text-[9px] text-cmd-red">{error}</div>}
      {report && (
        <div className="mt-2 space-y-1.5">
          <DataRow
            label="Recommendation"
            value={<StatusPill tone={PORTFOLIO_RECOMMENDATION_TONE[report.recommendation]}>{report.recommendation.replace(/_/g, " ").toUpperCase()}</StatusPill>}
          />
          <DataRow label="Reason" value={report.recommendationReason} />
          <DataRow label="Simultaneous drawdown detected" value={<BoolValue value={report.simultaneousDrawdownDetected} />} />
          <DataRow label="Concentration" value={report.concentrationPct !== null ? `${report.concentrationPct.toFixed(1)}%` : "—"} />
          <DataRow label="Evidence confidence" value={report.evidenceConfidence} />
          {report.pairCorrelations.length > 0 && (
            <div className="space-y-1">
              <div className="text-[8px] uppercase tracking-wide text-cmd-textDim">Pairwise correlation</div>
              {report.pairCorrelations.map((pc, i) => (
                <div key={i} className="text-[9px] text-cmd-text">
                  {pc.candidateIdA} × {pc.candidateIdB}: {pc.correlation !== null ? pc.correlation.toFixed(2) : "insufficient paired days"} ({pc.pairedDayCount} paired days)
                </div>
              ))}
            </div>
          )}
          {report.marginalContributions.length > 0 && (
            <div className="space-y-1">
              <div className="text-[8px] uppercase tracking-wide text-cmd-textDim">Marginal contribution (strategy-removal test)</div>
              {report.marginalContributions.map((mc, i) => (
                <div key={i} className="text-[9px] text-cmd-text">
                  {mc.candidateId}: expectancy with {mc.expectancyRWith ?? "—"}R / without {mc.expectancyRWithout ?? "—"}R
                </div>
              ))}
            </div>
          )}
          <BucketGroup title="COMBINED PORTFOLIO RESULT" buckets={[report.combinedBucket]} />
          <DataRow label="Worst combined period" value={report.worstCombinedPeriod.detail} />
        </div>
      )}
    </Glass>
  );
}

function EvidenceQualityCard() {
  const [name, setName] = useState("Evidence Check");
  const [sourceText, setSourceText] = useState(DEFAULT_SOURCE_TEXT);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<EvidenceQualityReport | null>(null);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      const definition = await api.compileStrategy(name, sourceText);
      const result = await api.getEvidenceQuality(definition);
      setReport(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  return (
    <Glass className="p-3">
      <TerminalLabel>DATA QUALITY — EVIDENCE STATE</TerminalLabel>
      <p className="mt-1 text-[8px] text-cmd-textDim">
        A disclosed evidence STATE, never a trading approval and never a blended confidence score — every axis below stays
        independently visible.
      </p>
      <CompileForm name={name} setName={setName} sourceText={sourceText} setSourceText={setSourceText} />
      <button
        type="button"
        onClick={() => void run()}
        disabled={running}
        className="mt-1.5 rounded-sm border border-cmd-cyan/60 bg-cmd-cyan/10 px-2 py-1 text-[9px] uppercase tracking-wide text-cmd-cyan hover:bg-cmd-cyan/20 disabled:opacity-50"
      >
        {running ? "Checking…" : "Check Evidence Quality"}
      </button>
      {error && <div className="mt-1.5 text-[9px] text-cmd-red">{error}</div>}
      {report && (
        <div className="mt-2 space-y-0.5">
          <DataRow label="State" value={<StatusPill tone={EVIDENCE_STATE_TONE[report.state] ?? "neutral"}>{report.state.replace(/_/g, " ").toUpperCase()}</StatusPill>} />
          <DataRow label="Detail" value={report.detail} />
          <DataRow label="Data provenance" value={report.dataProvenance} />
          <DataRow label="Data quality valid" value={<BoolValue value={report.dataQualityValid} />} />
          <DataRow label="Point-in-time verified" value={<BoolValue value={report.pointInTimeVerified} />} />
          <DataRow label="Holdout status" value={report.holdoutStatus ?? "not evaluated this call"} />
          <DataRow label="Sample size" value={report.sampleSize ?? "—"} />
          <DataRow label="External provider available" value={<BoolValue value={report.externalProviderAvailable} />} />
          <DataRow label="Benchmark available" value={<BoolValue value={report.benchmarkAvailable} />} />
        </div>
      )}
    </Glass>
  );
}

function LineageCheckCard() {
  const [runId, setRunId] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);
  const [issues, setIssues] = useState<LineageIntegrityIssue[]>([]);

  async function run() {
    if (!runId.trim()) return;
    setRunning(true);
    setError(null);
    setChecked(false);
    try {
      const result = await api.checkLineage(runId.trim());
      setIssues(result);
      setChecked(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  return (
    <Glass className="p-3">
      <TerminalLabel>LINEAGE INTEGRITY CHECK</TerminalLabel>
      <p className="mt-1 text-[8px] text-cmd-textDim">
        A real structural check over one already-run Research Factory run's own candidates — flags a broken parent link or a
        generation gap. Enter a Research Factory run id (see the RESEARCH FACTORY sub-tab's own run list).
      </p>
      <div className="mt-1.5 flex items-center gap-1.5">
        <input
          className="flex-1 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 px-1.5 py-1 text-[9px] text-cmd-text"
          placeholder="factory-run-…"
          value={runId}
          onChange={(e) => setRunId(e.target.value)}
        />
        <button
          type="button"
          onClick={() => void run()}
          disabled={running || !runId.trim()}
          className="rounded-sm border border-cmd-cyan/60 bg-cmd-cyan/10 px-2 py-1 text-[9px] uppercase tracking-wide text-cmd-cyan hover:bg-cmd-cyan/20 disabled:opacity-50"
        >
          {running ? "Checking…" : "Check Lineage"}
        </button>
      </div>
      {error && <div className="mt-1.5 text-[9px] text-cmd-red">{error}</div>}
      {checked && issues.length === 0 && <EmptyState>No lineage break found for this run.</EmptyState>}
      {checked && issues.length > 0 && (
        <div className="mt-1.5 space-y-1">
          {issues.map((issue, i) => (
            <div key={i} className="rounded-sm border border-cmd-red/40 bg-cmd-red/5 p-1.5 text-[9px] text-cmd-red">
              <span className="text-cmd-textDim">{issue.candidateId}:</span> {issue.issue}
            </div>
          ))}
        </div>
      )}
    </Glass>
  );
}
