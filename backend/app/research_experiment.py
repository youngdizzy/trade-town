"""app/research_experiment.py — CEO directive "Professional Quant
Trading Firm — Quant Intelligence + Market Analysis Completion Phase
(Next Research + Validation Pass)," item 11: the Research Desk's one
real, reproducible experiment record.

RESEARCH FIRST. No experiment-record concept existed anywhere in this
codebase before this module — every prior research result
(`CompiledStrategyBacktestResult`, and now `WalkForwardValidationResult`/
`ParameterSensitivityResult`/`CostSensitivityResult`/
`LookAheadAuditResult`) was returned as its own independent, disconnected
read. A CEO asking "what exactly did we test, on what data, using what
assumptions, and why did we believe the result" had no single place to
look. This module is pure orchestration — it calls each of those five
already-real, already-tested functions once and packages their real
results together; it computes NO new backtest math of its own.

WHAT COUNTS AS "DATASET/VERSION" AND "DATE RANGE" HERE, HONESTLY. This
codebase's candle history is app/market_data.py's own real, seeded,
procedurally-generated mock OHLCV series — there is no real external
dataset with its own version number, and the ISO timestamps on each mock
candle describe a synthetic walk anchored to wall-clock "now," not real
historical dates. `symbols_tested`/`timeframe`/`candles_per_symbol`
below are the real, honest, disclosed substitute for "dataset version" +
"date range" this codebase can actually offer — never dressed up as if
they were real historical dates.

THE CONCLUSION SYNTHESIS RULE, DISCLOSED AND DETERMINISTIC.
`_synthesize_conclusion()` combines five already-real verdicts
(model validation, walk-forward, parameter sensitivity, cost
sensitivity, look-ahead audit) via one fixed, real priority order — a
look-ahead violation or a rejected model-validation check always
overrides everything else (a real bug or a real rejected strategy is
never "mostly fine"); missing evidence anywhere always reads
"insufficient evidence," never silently treated as a pass; and only a
definition that is genuinely clean, approved-or-conditionally-passing,
stable, robust, AND cost-resilient across every real axis reads
"credible, professional-grade evidence" — this module's own honest
ceiling, never a claim of certainty. See the function's own body for the
exact real rule; it is intentionally simple and auditable rather than a
black-box score.

CEO directive "Professional Quant Firm Phase," Feature 39 adds
`overfitting_diagnosis` alongside `conclusion` — the directive's own
requested ROBUST/FRAGILE/INSUFFICIENT_DATA/OVERFIT_SUSPECTED/
OOS_FAILURE/PENDING_VALIDATION vocabulary, computed by app/
overfitting_diagnostics.py purely by relabeling the same walk-forward/
parameter-sensitivity/cost-sensitivity verdicts `_synthesize_conclusion`
already reads — a second, narrower lens on the same real evidence, never
a second set of statistics.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.cost_sensitivity import run_cost_sensitivity
from app.leakage_audit import audit_definition_for_look_ahead
from app.overfitting_diagnostics import classify_overfitting_risk
from app.parameter_sensitivity import run_parameter_sensitivity
from app.schemas import CompiledStrategyDefinition, ResearchExperimentRecord
from app.strategy_engine import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME, run_compiled_strategy_backtest
from app.walk_forward import run_walk_forward_validation
from app.watchlist import SEED_SYMBOLS


def _synthesize_conclusion(record_parts: tuple[str | None, str, str, str, str]) -> str:
    model_validation_verdict, walk_forward_verdict, parameter_verdict, cost_verdict, look_ahead_verdict = record_parts

    if look_ahead_verdict == "violations_found":
        return "INVALID — a real look-ahead dependency was found in this definition's own setup detection. No conclusion from any other axis is meaningful until that is fixed."
    if model_validation_verdict == "rejected":
        return "REJECTED — Model Validation's own real checks reject this backtest outright. No further evidence changes that conclusion."

    missing = [
        label
        for label, verdict in (
            ("model validation", model_validation_verdict),
            ("walk-forward", walk_forward_verdict),
            ("parameter sensitivity", parameter_verdict),
            ("cost sensitivity", cost_verdict),
            ("look-ahead audit", look_ahead_verdict),
        )
        if verdict is None or verdict in ("needs_more_evidence", "not_validatable", "insufficient_data")
    ]
    if missing:
        return f"INSUFFICIENT EVIDENCE — {', '.join(missing)} could not yet reach a real verdict from this sample. Re-run with more real history before treating this definition as validated or rejected."

    fragile_axes = [
        label
        for label, is_fragile in (
            ("walk-forward stability", walk_forward_verdict == "unstable"),
            ("parameter robustness", parameter_verdict == "fragile"),
            ("cost resilience", cost_verdict == "cost_sensitive"),
        )
        if is_fragile
    ]
    if fragile_axes:
        return f"FRAGILE — real evidence exists on every axis, but {', '.join(fragile_axes)} did not hold up. This edge is not yet credible, professional-grade evidence of a real trading advantage."

    return (
        "CREDIBLE, PRELIMINARY EVIDENCE — every real axis this Research Desk currently checks (model validation, walk-forward stability, "
        "parameter robustness, cost resilience, look-ahead cleanliness) reads favorably on this real (mock) sample. This is NOT a claim of "
        "certainty, live profitability, or a recommendation to trade — only that no real check this module runs found a reason to doubt it yet."
    )


def run_research_experiment(
    definition: CompiledStrategyDefinition,
    *,
    symbols: list[str] | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    candles_per_symbol: int = DEFAULT_CANDLES_PER_SYMBOL,
) -> ResearchExperimentRecord:
    """The one real entry point. Runs the definition through every real
    validation axis this codebase currently has and packages the results
    into one reproducible record. Each underlying module refuses on its
    own (an unresolved definition, an unsupported indicator) exactly as
    it would standalone — this function does not add a second refusal
    check, it just surfaces whatever each real module already decided."""
    now_iso = datetime.now(timezone.utc).isoformat()
    resolved_symbols = symbols if symbols is not None else [s for s, _name, _cat in SEED_SYMBOLS]

    backtest = run_compiled_strategy_backtest(definition, symbols=resolved_symbols, timeframe=timeframe, candles_per_symbol=candles_per_symbol)
    walk_forward = run_walk_forward_validation(definition, symbols=resolved_symbols, timeframe=timeframe, candles_per_symbol=candles_per_symbol)
    parameter_sensitivity = run_parameter_sensitivity(definition, symbols=resolved_symbols, timeframe=timeframe, candles_per_symbol=candles_per_symbol)
    cost_sensitivity = run_cost_sensitivity(definition, symbols=resolved_symbols, timeframe=timeframe, candles_per_symbol=candles_per_symbol)
    look_ahead_audit = audit_definition_for_look_ahead(definition, symbols=resolved_symbols, timeframe=timeframe, candles_per_symbol=candles_per_symbol)

    model_validation_verdict = backtest.model_validation.verdict if backtest.model_validation is not None else None
    conclusion = _synthesize_conclusion((model_validation_verdict, walk_forward.verdict, parameter_sensitivity.verdict, cost_sensitivity.verdict, look_ahead_audit.verdict))
    overfitting_diagnosis = classify_overfitting_risk(walk_forward, parameter_sensitivity, cost_sensitivity)

    return ResearchExperimentRecord(
        id=f"experiment-{definition.id}-{definition.version}",
        definitionId=definition.id,
        definitionName=definition.name,
        definitionVersion=definition.version,
        sourceText=definition.source_text,
        symbolsTested=resolved_symbols,
        timeframe=timeframe,
        candlesPerSymbol=candles_per_symbol,
        backtest=backtest,
        walkForward=walk_forward,
        parameterSensitivity=parameter_sensitivity,
        costSensitivity=cost_sensitivity,
        lookAheadAudit=look_ahead_audit,
        overfittingDiagnosis=overfitting_diagnosis,
        conclusion=conclusion,
        dataHonestyNote=(
            "Every real number in this record comes from app/market_data.py's own real, procedurally-generated (seeded, reproducible) "
            "mock OHLCV series — never real historical market data, and 'candlesPerSymbol' above is this record's own honest substitute "
            "for a real dataset version/date range, which this codebase has no source for."
        ),
        generatedAt=now_iso,
    )
