"""app/champion_challenger.py — CEO directive "TradeTown — 11/10
Self-Improving Quant Agent System," Section 1 (Champion vs Challenger
— The Core Upgrade): "A challenger must prove that it is better before
replacing the champion. Never replace a champion simply because the
challenger has a higher historical return."

RESEARCH FIRST. A dedicated background audit (before any code was
written) confirmed the real, previously-missing gap: `Strategy`/
`CompiledStrategyDefinition` are already really versioned
(`app/strategy_registry.py`), and `app/strategy_tournament.py` already
runs a real N-way elimination bracket over multiple candidates — but
`register_strategy_version()` is purely additive (it never compares
anything), the tournament's own "production_candidates" is a CAGS
(computed-fresh, never-persisted) set-membership label from
independent-threshold elimination, never a real head-to-head A-vs-B
verdict, and nothing anywhere persists "which ONE version is currently
the live champion for this strategy family." This module closes
exactly that gap — it adds NO new backtest math (both sides of every
comparison run through the exact same already-real
`run_research_experiment()` this codebase already trusts) and does NOT
duplicate the tournament (which stays the right tool for "rank many
candidates against each other"; this module is the right tool for "did
this ONE proposed change actually beat what's live right now").

IDENTICAL DATA, PER THE DIRECTIVE'S OWN STEP 5. "Run identical
historical dataset against champion and challenger" — `compare_champion_
challenger()` always runs BOTH sides through `run_research_experiment()`
in the same call with the same `symbols`/`timeframe`/`candles_per_symbol`,
never comparing a possibly-stale persisted record for one side against a
freshly-computed one for the other.

THE PROMOTION RULE IS ECONOMIC SIGNIFICANCE, NOT STATISTICAL
SIGNIFICANCE — A REAL, DISCLOSED SCOPE CUT. The directive's own Section
7 asks for confidence intervals / bootstrap comparisons / effect sizes /
probability-of-superiority between two strategies' return distributions.
The same background audit confirmed no two-sample statistical-comparison
utility exists anywhere in this codebase (the real bootstrap machinery
that does exist — `app/strategy_lab.py`'s Monte Carlo,
`app/portfolio_monte_carlo.py` — is all single-strategy/single-portfolio
resampling, not a champion-vs-challenger hypothesis test). Building one
honestly is real, non-trivial, additional work, deliberately NOT
attempted in this pass — see `_decide_verdict()`'s own docstring for the
exact real rule this module uses instead: a disclosed, bounded, ECONOMIC
tradeoff over already-real metrics (expectancy, drawdown), directly
implementing the directive's own two worked examples in Section 6,
never dressed up as a statistical proof. `_synthesize_conclusion()`'s
own real per-side conclusion (from `app/research_experiment.py`) is
still checked first — a FRAGILE/REJECTED/INVALID/INSUFFICIENT EVIDENCE
challenger can never be recommended regardless of its raw numbers,
covering the directive's own Section 11 "a FAIL blocks promotion" rule
via the exact same real machinery `strategy_tournament.py` already
reuses for the same purpose, never a second red-team system.

MINIMUM SAMPLE, REUSED NOT REINVENTED. Section 3 ("never learn from one
trade... use minimum sample thresholds") is enforced by requiring BOTH
sides' own real `EmaPullbackStatsBucket.verdict == "enough_evidence"`
(the same real `DEFAULT_MIN_TRADES_FOR_BUCKET_VERDICT` floor
`app/backtest_primitives.py::aggregate_bucket()` already applies to
every bucket in this codebase) before any recommend/retain verdict is
possible — otherwise `insufficient_evidence`, honestly, never a forced
call.

PROMOTION IS ALWAYS A SEPARATE, EXPLICIT, NAMED-AGENT ACTION. Section
31 ("agents cannot... secretly change production strategies") —
`compare_champion_challenger()` only ever RECOMMENDS; it never mutates
`champion_history`. Only `promote_challenger()` does that, and it
refuses (raises `ValueError`) unless the comparison it's given actually
carries `verdict == "challenger_recommended"` — a comparison that
retained the champion or found insufficient evidence can never be used
to justify a promotion, no matter who calls this function.
"""
from __future__ import annotations

from app.backtest_primitives import DEFAULT_MIN_TRADES_FOR_BUCKET_VERDICT
from app.research_experiment import run_research_experiment
from app.schemas import AgentId, ChallengerComparison, ChallengerVerdict, ChampionRecord, CompiledStrategyDefinition
from app.strategy_engine import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME

# CEO directive "TradeTown — 11/10 Self-Improving Quant Agent System,"
# Section 6 — real, disclosed thresholds directly implementing the
# directive's own two worked examples below. One reasonable convention
# among several valid ones, not derived from any statistical study —
# the same "real, disclosed, simple threshold, never the only valid
# one" honesty idiom this codebase's other per-module thresholds
# already use.
#
# Path A ("meaningfully better return, without a meaningfully worse
# drawdown"): the directive's own example — 30% return vs. 28% (a real
# improvement) but drawdown 19% vs. 10% (a +90% relative regression,
# far past MAX_DRAWDOWN_REGRESSION_PCT below) — is correctly BLOCKED.
MIN_EXPECTANCY_IMPROVEMENT_PCT = 10.0
MAX_DRAWDOWN_REGRESSION_PCT = 15.0
# Path B ("meaningfully lower drawdown, without a meaningfully worse
# return"): the directive's own second example — 27% return vs. 28% (a
# real but small -3.6% relative regression, within
# MAX_EXPECTANCY_REGRESSION_PCT below) with drawdown 8% vs. 15% (a real
# -46.7% relative improvement, past MIN_DRAWDOWN_IMPROVEMENT_PCT below)
# — is correctly PROMOTED.
MIN_DRAWDOWN_IMPROVEMENT_PCT = 20.0
MAX_EXPECTANCY_REGRESSION_PCT = 10.0


def get_current_champion(champion_history: list[ChampionRecord], *, strategy_family: str) -> ChampionRecord | None:
    """The current champion for a family is always the most recent real
    promotion event for that family — no separate, driftable "current
    pointer" field exists anywhere. `None` when this family has never
    had a real champion promoted."""
    return next((c for c in reversed(champion_history) if c.strategy_family == strategy_family), None)


def _relative_change_pct(previous: float, current: float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / abs(previous) * 100.0, 1)


def _decide_verdict(
    *,
    champion_evidence_sufficient: bool,
    challenger_evidence_sufficient: bool,
    challenger_conclusion_credible: bool,
    champion_expectancy_r: float | None,
    challenger_expectancy_r: float | None,
    champion_max_drawdown_r: float | None,
    challenger_max_drawdown_r: float | None,
) -> tuple[ChallengerVerdict, str]:
    """The one real, disclosed decision rule — see this module's own
    docstring for why it is an ECONOMIC tradeoff rule, not a
    statistical-significance test. Never called directly by a router;
    always through compare_champion_challenger()."""
    if not (champion_evidence_sufficient and challenger_evidence_sufficient):
        return "insufficient_evidence", (
            f"Below the real {DEFAULT_MIN_TRADES_FOR_BUCKET_VERDICT}-trade evidence floor on at least one side — "
            "no real verdict can be honestly reached yet."
        )
    if not challenger_conclusion_credible:
        return "champion_retained", "The challenger's own real research conclusion was not credible evidence of a real edge — retained regardless of its raw numbers."
    if champion_expectancy_r is None or challenger_expectancy_r is None or champion_max_drawdown_r is None or challenger_max_drawdown_r is None:
        return "insufficient_evidence", "At least one real metric (expectancy or max drawdown) could not be computed on one side — no real verdict can be honestly reached yet."

    expectancy_delta_pct = _relative_change_pct(champion_expectancy_r, challenger_expectancy_r)
    drawdown_delta_pct = _relative_change_pct(abs(champion_max_drawdown_r), abs(challenger_max_drawdown_r))

    # A champion with a non-positive real expectancy sets no real bar to clear proportionally —
    # any real positive challenger expectancy is itself the real improvement.
    expectancy_meaningfully_better = (
        challenger_expectancy_r > 0 if champion_expectancy_r <= 0 else expectancy_delta_pct is not None and expectancy_delta_pct >= MIN_EXPECTANCY_IMPROVEMENT_PCT
    )
    drawdown_not_meaningfully_worse = drawdown_delta_pct is not None and drawdown_delta_pct <= MAX_DRAWDOWN_REGRESSION_PCT
    if expectancy_meaningfully_better and drawdown_not_meaningfully_worse:
        return "challenger_recommended", (
            f"Real expectancy improved {expectancy_delta_pct if expectancy_delta_pct is not None else 'from a non-positive champion baseline'}% "
            f"without a meaningfully worse real max drawdown ({drawdown_delta_pct}% change)."
        )

    drawdown_meaningfully_better = drawdown_delta_pct is not None and drawdown_delta_pct <= -MIN_DRAWDOWN_IMPROVEMENT_PCT
    expectancy_not_meaningfully_worse = expectancy_delta_pct is not None and expectancy_delta_pct >= -MAX_EXPECTANCY_REGRESSION_PCT
    if drawdown_meaningfully_better and expectancy_not_meaningfully_worse:
        return "challenger_recommended", (
            f"Real max drawdown improved {drawdown_delta_pct}% without a meaningfully worse real expectancy ({expectancy_delta_pct}% change) — "
            "superior on a risk-adjusted basis."
        )

    return "champion_retained", (
        f"Real expectancy change {expectancy_delta_pct}%, real max drawdown change {drawdown_delta_pct}% — "
        "neither real tradeoff path cleared its own disclosed bar; the champion's own real track record stands."
    )


def compare_champion_challenger(
    champion_definition: CompiledStrategyDefinition,
    challenger_definition: CompiledStrategyDefinition,
    *,
    strategy_family: str,
    hypothesis: str,
    proposed_by: AgentId,
    comparison_id: str,
    generated_at: str,
    symbols: list[str] | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    candles_per_symbol: int = DEFAULT_CANDLES_PER_SYMBOL,
) -> ChallengerComparison:
    """The one real entry point. Runs BOTH definitions through the
    exact same real `run_research_experiment()` pipeline over the
    IDENTICAL real symbols/timeframe/candle window (the directive's own
    Section 5 Step 5), then applies `_decide_verdict()`'s real,
    disclosed rule. Read-only — never mutates `champion_history`; the
    caller decides whether/how to persist this comparison."""
    champion_record = run_research_experiment(champion_definition, symbols=symbols, timeframe=timeframe, candles_per_symbol=candles_per_symbol)
    challenger_record = run_research_experiment(challenger_definition, symbols=symbols, timeframe=timeframe, candles_per_symbol=candles_per_symbol)

    champion_bucket = champion_record.backtest.overall
    challenger_bucket = challenger_record.backtest.overall
    challenger_conclusion_credible = challenger_record.conclusion.startswith("CREDIBLE")

    verdict, reasoning = _decide_verdict(
        champion_evidence_sufficient=champion_bucket.verdict == "enough_evidence",
        challenger_evidence_sufficient=challenger_bucket.verdict == "enough_evidence",
        challenger_conclusion_credible=challenger_conclusion_credible,
        champion_expectancy_r=champion_bucket.expectancy_r,
        challenger_expectancy_r=challenger_bucket.expectancy_r,
        champion_max_drawdown_r=champion_bucket.max_drawdown_r,
        challenger_max_drawdown_r=challenger_bucket.max_drawdown_r,
    )

    return ChallengerComparison(
        id=comparison_id,
        strategyFamily=strategy_family,
        championDefinitionId=champion_definition.id,
        championDefinitionVersion=champion_definition.version,
        challengerDefinitionId=challenger_definition.id,
        challengerDefinitionVersion=challenger_definition.version,
        hypothesis=hypothesis,
        proposedBy=proposed_by,
        symbolsTested=champion_record.symbols_tested,
        timeframe=timeframe,
        candlesPerSymbol=candles_per_symbol,
        championTradeCount=champion_bucket.trade_count,
        challengerTradeCount=challenger_bucket.trade_count,
        championExpectancyR=champion_bucket.expectancy_r,
        challengerExpectancyR=challenger_bucket.expectancy_r,
        championProfitFactor=champion_bucket.profit_factor,
        challengerProfitFactor=challenger_bucket.profit_factor,
        championMaxDrawdownR=champion_bucket.max_drawdown_r,
        challengerMaxDrawdownR=challenger_bucket.max_drawdown_r,
        championConclusion=champion_record.conclusion,
        challengerConclusion=challenger_record.conclusion,
        verdict=verdict,
        reasoning=reasoning,
        generatedAt=generated_at,
    )


def promote_challenger(
    comparison: ChallengerComparison,
    *,
    promoted_by: AgentId,
    reasoning: str,
    record_id: str,
    promoted_at: str,
) -> ChampionRecord:
    """The one real, explicit action that ever changes who the current
    champion is — see this module's own docstring for why this is
    deliberately separate from compare_champion_challenger(). Refuses
    (raises ValueError) unless `comparison.verdict ==
    "challenger_recommended"` — a champion-retained or
    insufficient-evidence comparison can never justify a promotion, no
    matter who calls this."""
    if comparison.verdict != "challenger_recommended":
        raise ValueError(f"Cannot promote from a comparison whose own real verdict was '{comparison.verdict}', not 'challenger_recommended'.")
    return ChampionRecord(
        id=record_id,
        strategyFamily=comparison.strategy_family,
        definitionId=comparison.challenger_definition_id,
        definitionVersion=comparison.challenger_definition_version,
        sourceComparisonId=comparison.id,
        promotedBy=promoted_by,
        reasoning=reasoning,
        promotedAt=promoted_at,
    )
