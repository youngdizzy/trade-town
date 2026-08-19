"""app/strategy_tournament.py — CEO directive "Professional Quant Firm
Phase," Feature 40: the Quant Strategy Tournament.

RESEARCH FIRST. There was no tournament/ranking concept anywhere in this
codebase before this module (a repo-wide search for "tournament" found
zero hits). This module computes NO new backtest math of its own: for
every candidate `CompiledStrategyDefinition` it calls the already-real,
already-tested `run_research_experiment()` exactly once (the same
pipeline `POST /research-experiment` and the Quant Research Lab use) and
reads its already-real results. One owner per capability: the backtest
engine is app/strategy_engine.py, the validation axes are app/
walk_forward.py / app/parameter_sensitivity.py / app/cost_sensitivity.py
/ app/leakage_audit.py, the overfitting classification is app/
overfitting_diagnostics.py — this module orchestrates and compares,
never re-implements.

NEVER A FABRICATED COMPOSITE SCORE. The directive is explicit that a
90%-win-rate strategy with catastrophic tail losses must not
automatically beat a lower-win-rate strategy with stronger
expectancy/robustness — which rules out collapsing every dimension into
one invented "tournament score." This module produces exactly two kinds
of real, auditable output instead: (1) named-slot superlatives
(`StrategyTournamentResult.highest_expectancy` etc — reusing
`StrategyExecutiveDashboardEntry`'s existing "always cites the real
strategy and metric_label that earned it the slot" pattern), one real
dimension per slot, and (2) staged elimination rounds, each gated on one
real, existing verdict.

THE EIGHT ROUNDS, DISCLOSED. The directive lists 8 rounds; this module
implements 7 as real, evidence-based gates and discloses the 8th as
architecturally blocked rather than fabricating it:

1. Basic validity — the definition compiled AND produced at least one
   real closed trade. (Real: `backtest.overall.trade_count`.)
2. Cost/slippage realism — eliminates only a CONFIRMED "cost_sensitive"
   verdict; "insufficient_data" survives (missing evidence is not
   negative evidence — see this directive family's own repeated rule).
3. OOS/validation — eliminates a confirmed look-ahead violation (a real
   bug, never survivable) or a "rejected" model-validation verdict.
4. Walk-forward — eliminates only a confirmed "unstable" verdict.
5. Session robustness — REAL data (`backtest.session_breakdown`), but
   SOFT: this module has no real, non-fabricated threshold for "enough
   session diversity," so this round never eliminates — it only
   attaches the real per-session evidence count to `detail` for CEO/
   agent judgment.
6. Parameter robustness — eliminates only a confirmed "fragile" verdict.
7. Portfolio interaction — ARCHITECTURALLY BLOCKED. This codebase has no
   cross-strategy portfolio-level backtest, correlation model, or
   combined-exposure simulation (every backtest here is single-strategy,
   single-symbol-at-a-time). Every entrant passes this round
   automatically with `blocked=True` and a disclosed reason — never a
   fabricated portfolio metric.
8. Final research review — the closing gate: survivors must read
   "robust" on `overfitting_diagnosis` (Feature 39). Survivors of every
   real round become `production_candidates` — a real, cited LABEL for
   CEO visibility only. It is NEVER an autonomous production promotion:
   this codebase's own separate risk/governance approval flow
   (app/gatekeeper.py's TradeGatekeeper, StrategyReview, Model
   Validation) is the only real path to live capital, and nothing here
   bypasses it.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.research_experiment import run_research_experiment
from app.schemas import (
    CompiledStrategyDefinition,
    ResearchExperimentRecord,
    StrategyExecutiveDashboardEntry,
    StrategyTournamentEntry,
    StrategyTournamentResult,
    StrategyTournamentRoundResult,
)
from app.strategy_engine import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME


def _walk_forward_positive_window_pct(record: ResearchExperimentRecord) -> float | None:
    total_evaluated = sum(s.evaluated_window_count for s in record.walk_forward.symbols)
    if total_evaluated == 0:
        return None
    total_positive = sum(s.positive_window_count for s in record.walk_forward.symbols)
    return round(total_positive / total_evaluated * 100, 1)


def _build_entry(record: ResearchExperimentRecord) -> StrategyTournamentEntry:
    overall = record.backtest.overall
    model_validation_verdict = record.backtest.model_validation.verdict if record.backtest.model_validation is not None else None
    return StrategyTournamentEntry(
        definitionId=record.definition_id,
        definitionName=record.definition_name,
        definitionVersion=record.definition_version,
        tradeCount=overall.trade_count,
        winRatePct=overall.win_rate_pct,
        expectancyR=overall.expectancy_r,
        profitFactor=overall.profit_factor,
        maxDrawdownR=overall.max_drawdown_r,
        sharpeRatio=overall.sharpe_ratio,
        sortinoRatio=overall.sortino_ratio,
        calmarRatio=overall.calmar_ratio,
        walkForwardPositiveWindowPct=_walk_forward_positive_window_pct(record),
        walkForwardVerdict=record.walk_forward.verdict,
        parameterSensitivityVerdict=record.parameter_sensitivity.verdict,
        costSensitivityVerdict=record.cost_sensitivity.verdict,
        lookAheadVerdict=record.look_ahead_audit.verdict,
        modelValidationVerdict=model_validation_verdict,
        overfittingVerdict=record.overfitting_diagnosis.verdict,
    )


def _eliminate(entries: dict[str, StrategyTournamentEntry], survivors: list[str], round_number: int, name: str, description: str, should_eliminate) -> tuple[StrategyTournamentRoundResult, list[str]]:  # noqa: ANN001
    still_in = []
    eliminated = []
    for definition_id in survivors:
        entry = entries[definition_id]
        reason = should_eliminate(entry)
        if reason:
            entry.eliminated_at_round = round_number
            entry.elimination_reason = reason
            eliminated.append(definition_id)
        else:
            still_in.append(definition_id)
    detail = f"{len(still_in)} of {len(survivors)} candidate(s) survived." if survivors else "No candidates entered this round."
    return StrategyTournamentRoundResult(roundNumber=round_number, name=name, description=description, survivors=still_in, eliminated=eliminated, detail=detail), still_in


def _superlative(entries: list[StrategyTournamentEntry], *, metric_label: str, value_fn, higher_is_better: bool) -> StrategyExecutiveDashboardEntry | None:  # noqa: ANN001
    """Real, disclosed named-slot pick — `None` (never a fabricated
    default) when no entry has a real value for this metric."""
    candidates = [(entry, value_fn(entry)) for entry in entries]
    candidates = [(entry, value) for entry, value in candidates if value is not None]
    if not candidates:
        return None
    best = max(candidates, key=lambda pair: pair[1]) if higher_is_better else min(candidates, key=lambda pair: pair[1])
    entry, value = best
    return StrategyExecutiveDashboardEntry(strategyId=entry.definition_id, strategyName=entry.definition_name, metricLabel=metric_label, metricValue=value)


def run_strategy_tournament(
    definitions: list[CompiledStrategyDefinition],
    *,
    symbols: list[str] | None = None,
    timeframe: str | None = None,
    candles_per_symbol: int | None = None,
) -> StrategyTournamentResult:
    """The one real entry point. Runs every candidate through the
    already-real `run_research_experiment()` pipeline once each, then
    compares the real results — see this module's own docstring for the
    exact, disclosed round-by-round rule."""
    resolved_timeframe = timeframe if timeframe is not None else DEFAULT_TIMEFRAME
    resolved_candles = candles_per_symbol if candles_per_symbol is not None else DEFAULT_CANDLES_PER_SYMBOL
    now_iso = datetime.now(timezone.utc).isoformat()

    records = [run_research_experiment(d, symbols=symbols, timeframe=resolved_timeframe, candles_per_symbol=resolved_candles) for d in definitions]
    entries_by_id = {record.definition_id: _build_entry(record) for record in records}
    all_ids = [record.definition_id for record in records]

    rounds: list[StrategyTournamentRoundResult] = []

    round_result, survivors = _eliminate(
        entries_by_id, all_ids, 1, "Basic validity",
        "The definition must have compiled and produced at least one real closed trade.",
        lambda e: None if e.trade_count > 0 else "No real closed trades — refuses rather than ranks an untested definition.",
    )
    rounds.append(round_result)

    round_result, survivors = _eliminate(
        entries_by_id, survivors, 2, "Cost/slippage realism",
        "Eliminates only a confirmed 'cost_sensitive' verdict; missing evidence survives.",
        lambda e: "Cost sensitivity confirmed 'cost_sensitive' — the edge does not survive this codebase's own real transaction-cost/slippage constants." if e.cost_sensitivity_verdict == "cost_sensitive" else None,
    )
    rounds.append(round_result)

    round_result, survivors = _eliminate(
        entries_by_id, survivors, 3, "OOS / validation",
        "Eliminates a confirmed look-ahead violation or a rejected model-validation verdict.",
        lambda e: (
            "A real look-ahead violation was found in this definition's own setup detection." if e.look_ahead_verdict == "violations_found"
            else ("Model Validation rejected this backtest outright." if e.model_validation_verdict == "rejected" else None)
        ),
    )
    rounds.append(round_result)

    round_result, survivors = _eliminate(
        entries_by_id, survivors, 4, "Walk-forward testing",
        "Eliminates only a confirmed 'unstable' verdict — the edge does not hold up across real, disjoint chronological windows.",
        lambda e: "Walk-forward validation confirmed 'unstable'." if e.walk_forward_verdict == "unstable" else None,
    )
    rounds.append(round_result)

    session_detail_parts = []
    for definition_id in survivors:
        record = next(r for r in records if r.definition_id == definition_id)
        with_evidence = sum(1 for b in record.backtest.session_breakdown if b.verdict == "enough_evidence")
        session_detail_parts.append(f"{definition_id}: {with_evidence}/{len(record.backtest.session_breakdown)} real session(s) with enough evidence")
    rounds.append(
        StrategyTournamentRoundResult(
            roundNumber=5, name="Session robustness",
            description="Real per-session evidence (app/strategy_engine.py's session_breakdown) — soft round, never eliminates (no non-fabricated diversity threshold exists yet).",
            survivors=list(survivors), eliminated=[],
            detail="; ".join(session_detail_parts) if session_detail_parts else "No candidates entered this round.",
        )
    )

    round_result, survivors = _eliminate(
        entries_by_id, survivors, 6, "Parameter robustness",
        "Eliminates only a confirmed 'fragile' verdict — edge sign is not stable across neighboring real parameter values.",
        lambda e: "Parameter sensitivity confirmed 'fragile'." if e.parameter_sensitivity_verdict == "fragile" else None,
    )
    rounds.append(round_result)

    rounds.append(
        StrategyTournamentRoundResult(
            roundNumber=7, name="Portfolio interaction",
            description="ARCHITECTURALLY BLOCKED — this codebase has no cross-strategy portfolio-level backtest, correlation model, or combined-exposure simulation.",
            survivors=list(survivors), eliminated=[], blocked=True,
            detail="Every real backtest in this codebase tests one strategy on one symbol at a time; there is no capability yet to measure how multiple strategies' positions would interact in one shared portfolio. Every real survivor of round 6 passes this round automatically rather than a fabricated portfolio metric.",
        )
    )

    round_result, survivors = _eliminate(
        entries_by_id, survivors, 8, "Final research review",
        "Eliminates unless the overfitting diagnosis (Feature 39) reads 'robust'.",
        lambda e: f"Overfitting diagnosis read '{e.overfitting_verdict}', not 'robust'." if e.overfitting_verdict != "robust" else None,
    )
    rounds.append(round_result)

    entries = [entries_by_id[i] for i in all_ids]
    return StrategyTournamentResult(
        id=f"tournament-{now_iso}",
        entries=entries,
        rounds=rounds,
        highestExpectancy=_superlative(entries, metric_label="Expectancy (R)", value_fn=lambda e: e.expectancy_r, higher_is_better=True),
        highestProfitFactor=_superlative(entries, metric_label="Profit Factor", value_fn=lambda e: e.profit_factor, higher_is_better=True),
        highestSharpeRatio=_superlative(entries, metric_label="Sharpe Ratio", value_fn=lambda e: e.sharpe_ratio, higher_is_better=True),
        lowestMaxDrawdown=_superlative(entries, metric_label="Max Drawdown (R)", value_fn=lambda e: e.max_drawdown_r, higher_is_better=False),
        mostWalkForwardStable=_superlative(entries, metric_label="Walk-Forward Positive Window %", value_fn=lambda e: e.walk_forward_positive_window_pct, higher_is_better=True),
        productionCandidates=list(survivors),
        dataHonestyNote=(
            "Every real number above comes from app/market_data.py's own real, procedurally-generated (seeded, reproducible) mock OHLCV "
            "series — never real historical market data. 'productionCandidates' is a real, cited LABEL only (every real round this module "
            "runs was survived) — it is never an autonomous production promotion and never bypasses this codebase's own separate risk/"
            "governance approval flow (app/gatekeeper.py, StrategyReview, Model Validation)."
        ),
        generatedAt=now_iso,
    )
