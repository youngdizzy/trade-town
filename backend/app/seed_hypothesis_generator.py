"""CEO directive "TradeTown — Autonomous Seed Hypothesis Generation 1.0."

PHASE 0 FORENSIC FINDING (verified against HEAD 00663eb — see this
module's own test file for the exact repository-truth commands run
before writing a single line here). The confirmed gap is real, and more
precise than "no hypothesis generator exists at all":

- `app/research_orchestrator.py::find_research_seed()` requires a
  caller (human or agent) to have ALREADY authored a real
  `StrategyHypothesis` somewhere in `state.factory_runs` or
  `state.research_iterations`. It never generates one — confirmed by
  that module's own docstring and by re-reading its source directly.
- `app/strategy_families.py::generate_candidate_population()` CAN
  already produce a first hypothesis-worthy candidate for any family in
  `SUPPORTED_FAMILIES`, but its own `research_reason` is explicitly,
  by its own docstring, NOT evidence-grounded: "Research exploration —
  family 'X', deterministic seed 'Y'" is a seeded-random EXPLORATION
  choice, never a claim that any real observation motivated picking
  that specific family/parameter. This is a real, useful, existing
  mechanism for POPULATION BREADTH — it is not "equivalent
  functionality" to what this directive asks for, which is a hypothesis
  justified by an actual observation.

This module closes exactly that narrower, still-real gap: for a
strategy that already has a real, compiled `CompiledStrategyDefinition`
(`state.compiled_strategy_versions`) but has never had ANY
`StrategyHypothesis` recorded in this save's lineage, propose exactly
one `StrategyHypothesis` whose every claim is derived from real,
already-computed evidence — the definition's own real, already-compiled
`source_text`/`stop`/`target`, and a fresh, read-only run of the
existing, unmodified `run_compiled_strategy_backtest()` against this
codebase's own default deterministic research dataset (the same
disclosed-as-simulated mock data every other research entry point
already defaults to — see `app/market_data.py`'s own docstring).

Phase 1 architecture choice (the directive explicitly offers two, and
asks for the smallest): this module implements **Choice A** — propose
only a `StrategyHypothesis` paired with the family's own EXISTING
compiled definition. It never constructs a new candidate definition
through the compiler (Choice B) — that would re-implement
`app/strategy_families.py`'s own job and risk a second, competing
text-generation mechanism. A direct consequence, disclosed here rather
than silently: this module can only ever propose a seed for a family
that is ALREADY compiled. A family with no compiled definition at all
gets an honest `no_compiled_definition` outcome, never an invented one.

Because `_latest_compiled_definition()` only ever returns definitions
with `status == "compiled"`, every definition this module reasons about
has, by construction, already been successfully parsed by
`app/strategy_compiler.py` — there is nothing left for THIS module to
re-check about compiler vocabulary compatibility. `unsupported_vocabulary`/
`no_compatible_strategy_family` (from the directive's Phase 4 vocabulary)
are therefore real, disclosed, UNREACHABLE outcomes under Choice A, not
implemented as live checks here — implementing a check that could never
meaningfully fire would itself be a dishonest facade, not real
gatekeeping. If a future milestone adopts Choice B, that module should
reuse `app/strategy_families.py::SUPPORTED_FAMILIES`/
`UNSUPPORTED_FAMILIES` directly rather than re-deriving compatibility.

NO LLM. NO new randomness (the only nondeterminism anywhere in the
called chain is `run_compiled_strategy_backtest()`'s own, which is
itself fully seeded/deterministic per `app/market_data.py`'s
`MockMarketDataProvider` — same inputs always produce the same trade
count, so this module's output is deterministic by construction, not by
a fingerprint alone papering over hidden nondeterminism).

NO automatic promotion, certification, or trading. This module returns
a `SeedHypothesisProposal` — a plain, non-persisted, ephemeral read
(the same pattern `app/research_orchestrator.py`'s own
`ResearchOrchestratorDecision`/`ResearchOrchestratorSeed` already
establish). It never calls `GameState.submit_research_factory_run()`,
never writes to `state.factory_runs`/`state.research_iterations`, never
imports anything from `app/champion_challenger.py`, `app/risk_contract.py`,
`app/gatekeeper.py`, `app/broker.py`, or `app/emergency_stop.py`. A
human/API caller must still separately call the existing, unmodified
`POST /api/sandbox/research-factory/run` with this proposal's own
`hypothesis`/`definition` pair to actually start research on it —
exactly the same existing gate a hand-authored hypothesis already goes
through. Zero new persistence: nothing about a generated-but-not-yet-
submitted proposal is stored anywhere, so "restart does not produce
duplicate seeds" holds trivially (there is nothing to duplicate) and
"the same evidence produces the same proposal" holds by the same
determinism argument above, computed fresh on every call.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from app.market_data import ExternalMarketDataProviderUnavailable, MarketDataProvider
from app.research_orchestrator import _latest_compiled_definition
from app.schemas import (
    CompiledStrategyDefinition,
    GameSaveState,
    StrategyHypothesis,
    StrategyStopSpec,
    StrategyTargetSpec,
)
from app.statistical_comparison import MIN_TRADES_FOR_BOOTSTRAP
from app.strategy_engine import run_compiled_strategy_backtest

SEED_GENERATOR_VERSION = "seed-hypothesis-generator-1.0"

SeedHypothesisStatus = Literal["generated", "not_generated"]

# Only the three outcomes this module's own Choice-A scope can actually
# reach (see module docstring for why `unsupported_vocabulary`/
# `no_compatible_strategy_family`/`insufficient_provenance` are real,
# disclosed, but structurally unreachable here rather than faked).
SeedHypothesisReason = Literal[
    "existing_lineage_found",
    "no_compiled_definition",
    "insufficient_evidence",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SeedHypothesisProposal:
    """A reviewable research proposal, never a certified strategy and
    never persisted by this module. `status="generated"` means
    `hypothesis`/`definition` are both populated and ready to be passed,
    unmodified, to the existing `POST /api/sandbox/research-factory/run`
    — nothing here calls that endpoint automatically."""

    status: SeedHypothesisStatus
    strategy_family: str
    reason: SeedHypothesisReason | None
    detail: str
    hypothesis: StrategyHypothesis | None = None
    definition: CompiledStrategyDefinition | None = None
    evidence_trade_count: int | None = None
    evidence_win_rate_pct: float | None = None
    evidence_expectancy_r: float | None = None
    fingerprint: str | None = None


def family_has_research_lineage(state: GameSaveState, strategy_family: str) -> bool:
    """Phase 6 duplicate protection, reusing existing lineage stores
    directly — no second deduplication database. True if ANY real
    hypothesis (any generation, any source) already exists for this
    exact family in either persisted lineage store."""
    if any(run.strategy_family == strategy_family for run in state.factory_runs):
        return True
    return any(record.strategy_family == strategy_family for record in state.research_iterations)


def _describe_stop(stop: StrategyStopSpec | None) -> str:
    if stop is None:
        return "Not specified in the compiled definition."
    if stop.method == "chandelier" and stop.atr_period is not None and stop.atr_multiplier is not None:
        return f"Chandelier stop: {stop.atr_period}-period ATR x {stop.atr_multiplier:g} multiplier (as compiled)."
    return f"{stop.method} stop (as compiled)."


def _describe_target(target: StrategyTargetSpec | None) -> str:
    if target is None:
        return "Not specified in the compiled definition."
    return f"{target.method} target of {target.value:g} (as compiled)."


def generate_seed_hypothesis(
    state: GameSaveState,
    *,
    strategy_family: str,
    market_data_provider: MarketDataProvider | None = None,
) -> SeedHypothesisProposal:
    """The one real entry point. Pure with respect to `state` (never
    mutates it) other than the read-only, already-existing
    `run_compiled_strategy_backtest()` call, which itself performs no
    I/O beyond the supplied/default `MarketDataProvider`.

    Evidence-sufficiency gate reuses this codebase's own existing
    `MIN_TRADES_FOR_BOOTSTRAP` floor (`app/statistical_comparison.py`)
    rather than inventing a new threshold — the same real bar every
    other bootstrap-comparison call in this codebase already applies to
    "is this enough real evidence to say anything.\""""
    if family_has_research_lineage(state, strategy_family):
        return SeedHypothesisProposal(
            status="not_generated",
            strategy_family=strategy_family,
            reason="existing_lineage_found",
            detail=(
                f"Strategy family '{strategy_family}' already has at least one real StrategyHypothesis in "
                "state.factory_runs/state.research_iterations — an autonomous seed would duplicate existing lineage."
            ),
        )

    definition = _latest_compiled_definition(state, strategy_family)
    if definition is None:
        return SeedHypothesisProposal(
            status="not_generated",
            strategy_family=strategy_family,
            reason="no_compiled_definition",
            detail=(
                f"No real, compiled CompiledStrategyDefinition exists yet for strategy family '{strategy_family}' "
                "in state.compiled_strategy_versions — nothing to ground a seed hypothesis in."
            ),
        )

    try:
        backtest = run_compiled_strategy_backtest(definition, timeframe=definition.timeframe, market_data_provider=market_data_provider)
    except ExternalMarketDataProviderUnavailable as exc:
        # Phase 15/16 — an explicitly-injected real provider that cannot
        # actually serve this definition's required symbols/timeframe is
        # a real evidence gap, never a crash. Fails closed exactly like
        # a genuinely low trade count would (same `insufficient_evidence`
        # reason — this codebase's own existing vocabulary for "not
        # enough real evidence to proceed," never a fabricated distinct
        # status just to describe a different cause of the same outcome).
        return SeedHypothesisProposal(
            status="not_generated",
            strategy_family=strategy_family,
            reason="insufficient_evidence",
            detail=(
                f"NO SEED GENERATED — INSUFFICIENT REAL EVIDENCE: the supplied market data provider could not serve "
                f"'{definition.name}' v{definition.version}'s required data: {exc}"
            ),
        )
    trade_count = backtest.overall.trade_count
    if trade_count < MIN_TRADES_FOR_BOOTSTRAP:
        return SeedHypothesisProposal(
            status="not_generated",
            strategy_family=strategy_family,
            reason="insufficient_evidence",
            detail=(
                f"Preliminary read-only backtest of '{definition.name}' v{definition.version} produced only "
                f"{trade_count} real trade(s) — below this codebase's own {MIN_TRADES_FOR_BOOTSTRAP}-trade "
                "statistical-evidence floor (app/statistical_comparison.py::MIN_TRADES_FOR_BOOTSTRAP). No seed generated."
            ),
            evidence_trade_count=trade_count,
        )

    win_rate = backtest.overall.win_rate_pct
    expectancy = backtest.overall.expectancy_r
    symbols_tested = list(backtest.symbols_tested)

    fingerprint_source = "|".join(
        [
            SEED_GENERATOR_VERSION,
            definition.id,
            str(definition.version),
            str(trade_count),
            "None" if win_rate is None else repr(win_rate),
            "None" if expectancy is None else repr(expectancy),
        ]
    )
    fingerprint = hashlib.sha256(fingerprint_source.encode()).hexdigest()

    observation = (
        f"OBSERVATION: the already-compiled strategy '{definition.name}' (id={definition.id}, version={definition.version}, "
        f"family '{strategy_family}') has never had a StrategyHypothesis recorded in this save's research lineage. A "
        "preliminary, read-only re-run of the existing, unmodified backtest engine "
        "(app/strategy_engine.py::run_compiled_strategy_backtest) against this codebase's own default research dataset "
        f"produced {trade_count} real trade(s) across {symbols_tested} at the {definition.timeframe} timeframe"
        + (f", win rate {win_rate:.1f}%" if win_rate is not None else "")
        + (f", expectancy {expectancy:+.3f}R" if expectancy is not None else "")
        + "."
    )
    interpretation = (
        "INTERPRETATION: this trade count clears this codebase's own existing MIN_TRADES_FOR_BOOTSTRAP evidence floor "
        f"({MIN_TRADES_FOR_BOOTSTRAP}), meaning the definition's entry logic fires often enough, on this dataset, to be "
        "worth carrying through the full existing validation funnel (walk-forward, holdout, robustness, statistical "
        "comparison). This is a signal-activity observation only — it makes no claim about profitability, edge, or "
        "real-market validity, none of which a preliminary trade count can establish."
    )
    invalidation = (
        "INVALIDATION: this proposal is invalidated if the existing walk-forward validation (app/walk_forward.py), "
        "holdout validation (app/holdout.py), or robustness testing (app/parameter_sensitivity.py / "
        f"app/cost_sensitivity.py) fails once actually run, or if the observed trade count no longer clears the "
        f"{MIN_TRADES_FOR_BOOTSTRAP}-trade floor against a different or larger dataset."
    )

    hypothesis = StrategyHypothesis(
        id=f"seed-hyp-{fingerprint[:16]}",
        hypothesis=(
            f"{observation} {interpretation} This hypothesis proposes running the existing research funnel on "
            f"'{definition.name}' v{definition.version} for the first time."
        ),
        marketMechanism=definition.source_text,
        expectedEdge=f"No edge is claimed. {interpretation}",
        invalidationConditions=invalidation,
        symbolUniverse=symbols_tested,
        timeframe=definition.timeframe,
        entryConditions=definition.source_text,
        exitConditions=f"stop: {_describe_stop(definition.stop)} target: {_describe_target(definition.target)}",
        stopLossLogic=_describe_stop(definition.stop),
        takeProfitLogic=_describe_target(definition.target),
        positionSizingLogic="Not set by this generator — governed unchanged by the existing Risk Contract / position sizing pipeline.",
        riskConstraints="Not set by this generator — existing RiskContract/RiskLimits apply unchanged.",
        indicatorsFeatures=[],
        regimeAssumptions="",
        researchRationale=(
            f"Autonomously proposed by {SEED_GENERATOR_VERSION} because strategy family '{strategy_family}' had a real "
            "compiled definition but no recorded research hypothesis. " + observation
        ),
        parentStrategyFamily=None,
        parentDefinitionId=None,
        parentDefinitionVersion=None,
        proposedBy="quant",
        createdAt=_now_iso(),
        generation=0,
        lineageId=None,
        reasonForGeneration=f"bootstrap: strategy family '{strategy_family}' had no existing research lineage.",
        lessonsUsed=[],
        failureCodesAddressed=[],
        mutationOperatorUsed=None,
        expectedImprovement=None,
        expectedRisk=None,
        reproducibilitySeed=fingerprint,
        sourceEvidenceIds=[definition.id, f"backtest-trade-count:{trade_count}"],
    )

    return SeedHypothesisProposal(
        status="generated",
        strategy_family=strategy_family,
        reason=None,
        detail=f"Evidence-grounded seed hypothesis generated for '{definition.name}' v{definition.version}.",
        hypothesis=hypothesis,
        definition=definition,
        evidence_trade_count=trade_count,
        evidence_win_rate_pct=win_rate,
        evidence_expectancy_r=expectancy,
        fingerprint=fingerprint,
    )
