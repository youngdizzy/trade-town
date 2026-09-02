"""app/research_factory.py — CEO directive "TradeTown — Phase 7:
Autonomous Strategy Evolution Engine": "Turn the existing Research
Factory into a genuine closed-loop strategy evolution system... OBSERVE
-> GENERATE -> MUTATE -> COMPILE -> BACKTEST -> VALIDATE -> STRESS ->
COMPARE -> ACCEPT OR BIN -> LEARN -> GENERATE AGAIN."

PHASE 0 FORENSIC RECON, SUMMARIZED (the full trace is in this module's
own git history / session transcript): `app/research_loop.py`'s
`run_research_loop_iteration()` already runs the ENTIRE real funnel
(backtest, walk-forward, cost sensitivity, parameter sensitivity,
look-ahead audit, benchmark comparison, failure diagnosis, candidacy
classification, mutation recommendation, budget check, lesson
generation) for exactly one hypothesis/definition pair. What Phase 4-6
deliberately did NOT build was the seam AFTER that: the loop always
stopped at a human-readable `MutationRecord.proposedChange` string,
requiring a human to hand-author new `sourceText` and manually resubmit
it through `app/strategy_registry.py::register_strategy_version()`.
This module closes exactly that seam — nothing else. It adds NO new
backtest math, NO second compiler, NO second validation pipeline: every
generation of the loop below calls the exact same
`run_research_loop_iteration()`/`register_strategy_version()`/
`classify_research_relationship()` this codebase already shipped and
tested in Phase 4-6.

THE ONE GENUINE FIX THIS PASS MADE TO ALREADY-SHIPPED CODE, DISCLOSED.
Tracing the real call path from a generation-0 (non-mutated) hypothesis
found a real, confirmed latent inconsistency in
`app/research_loop.py::run_research_loop_iteration()`: it always passed
`hypothesis.parent_definition_id or definition.id` into
`propose_mutation()` (a real fallback to "diagnose against the
definition just tested" when no earlier lineage exists) — but the
OUTER guard around that call only fired when
`hypothesis.parent_definition_id is not None`, making that fallback
dead code. A fresh, non-mutated hypothesis could therefore never
receive a first real mutation proposal at all, which would make this
directive's entire closed loop impossible to start. Fixed with a
minimal, one-line change (see that function's own updated comment) —
every hypothesis that already carried an explicit parent is completely
unaffected; the existing test suite was updated for the one assertion
that depended on the old, buggy behavior (see
tests/test_research_loop.py's own updated comment).

WHY MUTATION CAN NOW BE "EXECUTABLE" WITHOUT AN LLM AND WITHOUT A
SECOND, COMPETING STRATEGY REPRESENTATION. `app/strategy_compiler.py`'s
own module docstring already establishes this codebase's strategy
compiler is a real, deterministic, disclosed-vocabulary PATTERN MATCHER
over English text — never an LLM, and this codebase runs no LLM at
runtime anywhere (see that module's own docstring and
`app/debate.py`/`app/foundational_mentors.py`'s same discipline). This
module's mutation engine respects that exact same discipline: every
`_MUTATION_OPERATORS` entry below either (a) numerically nudges ONE
already-compiled, already-structured value on the parent
`CompiledStrategyDefinition` (its own real `stop.atr_multiplier`/
`stop.percent`/`target.value`/a swept threshold/a consecutive-bar
count) by a small, disclosed, capped step, using the EXACT SAME private
regex patterns `app/strategy_compiler.py` itself uses to recognize that
value (imported directly, never re-derived, so the two can never
silently drift out of sync), or (b) appends one new sentence in that
same disclosed vocabulary. Rule 12 of this directive ("do not allow the
LLM to directly execute arbitrary trading code") is trivially satisfied
because there is no LLM in this path at all — every mutated string is
produced by bounded, testable, deterministic Python.

THE ONE MUTATION CATEGORY THIS PASS DELIBERATELY DID NOT BUILD, AND
WHY. Section 2 also asks for a "regime filter"/"trend filter" mutation
operator. Tracing `compile_strategy_text()`'s real control flow proved
this is NOT safely buildable as a bounded text splice today: the
compiler recognizes AT MOST ONE trigger per strategy (an if/elif chain
— EMA/SMA, then RSI, then Stochastic, then MACD, then trend-score, ...,
first match wins), and its only multi-condition mechanism
(`StrategySequenceStep.all_of`) is hard-wired to one specific literal
phrase (the liquidity-sweep+FVG combo), not a generic "AND also require
indicator X." Appending a second, unrelated trigger-shaped sentence
(e.g. "also require the multi-horizon trend score above 0") to a
strategy whose trigger is already EMA/SMA-based would re-compile
successfully but have ZERO real structural effect — the compiler would
silently ignore it, since only the FIRST matched trigger type ever
becomes part of the real sequence. Producing that text anyway would be
exactly the "candidate looks mutated but isn't" anti-pattern this
directive's own honesty rules forbid. `regime_failure` therefore joins
`negative_net_return`/`benchmark_underperformance` (already disclosed
non-automatable in app/research_loop.py) as a real, disclosed
NOT-BOUNDED-AUTOMATICALLY case: a real `MutationCandidate` is still
produced with `mutatedSourceText=None` and an explicit `constraints`
string naming this exact limitation. Genuinely extending
`app/strategy_compiler.py`'s own trigger-matching grammar to support a
combined "primary trigger AND regime filter" condition is real,
tractable future work — not attempted in this pass (a compiler-grammar
change is a materially larger, riskier change than a bounded mutation
operator, and Phase 0's own instruction was "do not modify production
behavior until you understand existing contracts").

CANDIDATE LIFECYCLE, HONESTLY SCOPED. `CandidateLifecycleStage`
(app/schemas.py) declares the full requested vocabulary (`generated`/
`compile_rejected`/`backtested`/`candidate`/`rejected`/`survivor`/
`challenger_eligible`) for future finer-grained use, but
`derive_lifecycle_stage()` below only ever actually PRODUCES
`compile_rejected`/`candidate`/`rejected`/`survivor` — `generated`
never appears because this orchestrator never creates a
`FactoryCandidateRecord` for a hypothesis it hasn't yet attempted to
compile; `backtested` never appears as a terminal state because
`run_research_loop_iteration()` always synchronously classifies
candidacy in the same call, so a candidate is never left in a
"backtested but not yet classified" state; `challenger_eligible` is
folded into a SURVIVOR's own `decision_reason` text (which states
plainly that it is eligible for a real, separate, unmodified
Champion/Challenger submission) rather than a distinct enum value,
because no automatic-submission action exists for this pass to
distinguish it from a bare `survivor` — see Section 10 below for why
that stays a deliberate non-feature.

CHAMPION/CHALLENGER BOUNDARY, ENFORCED BY IMPORT SHAPE, NOT PROSE.
Section 10's own explicit authority split ("Factory: GENERATE/TEST/
FILTER/CLASSIFY/PROPOSE. Champion/Challenger: COMPARE/RECOMMEND/
PROMOTE/RETAIN. No factory candidate gets direct live/paper execution
authority.") is enforced the same way app/research_loop.py already
proved out for the Certification/Hall-of-Fame boundary: this module
imports ONLY `get_current_champion()` (read-only) from
`app.champion_challenger` — never `compare_champion_challenger()` or
`promote_challenger()` — see tests/test_research_factory.py's own
module-source-inspection test. A `survivor`'s own real, existing
Champion/Challenger submission stays a completely separate, unmodified,
human/agent-triggered call to the EXISTING `POST
/api/sandbox/champion-challenger/compare` endpoint — this module never
calls it automatically.

DETERMINISM (Section 21). Every id below is derived deterministically
from the caller-supplied `run_id` and each generation's own integer
index (`f"{run_id}-gen{N}-..."`) — no `uuid`/`random` call anywhere in
this module. `MutationCandidate.reproducibility_seed` is a real SHA-256
hash of (parent definition id/version, mutation type) — this codebase's
mutation logic has no actual randomness to seed; the field exists
purely as a real, stable, auditable per-candidate identity, not because
true randomness is involved anywhere in this pass.

WHAT ELSE THIS PASS DELIBERATELY DID NOT BUILD (Section 15's own "if a
requirement cannot honestly be implemented, STOP and explain the
constraint"): entry-condition/exit-condition/timeframe/position-sizing/
explicit-trade-frequency mutation operators (Section 2's own fuller
list) — no bounded, deterministic text-splice exists for any of these
against the compiler's real vocabulary without either guessing at
semantics the compiler doesn't expose as a swept parameter, or (for
timeframe) requiring a full new candle-fetch/backtest shape this pass
did not build. `LessonEvidenceSummary` (Section 12) is a real, disclosed,
SIMPLE proxy (same-family lesson candidacy-bucket agreement/disagreement
counts) — never a fabricated statistical confidence measure; see that
schema's own docstring. No new specialized agent personas/dialogue —
same disclosed cut as Phase 4-6.

CEO DIRECTIVE "TRADETOWN — AUTONOMOUS MUTATION APPLICATION + PARETO
SURVIVOR ENGINE," ADDENDUM. Phase 0 forensic recon for that directive
(three parallel research passes over this module, `app/research_
fitness.py`, `app/adversarial_research.py`, `app/champion_challenger.py`,
`app/holdout.py`, `app/evidence_quality.py`, and every persistence/API/
frontend file touching this domain) found the directive's headline ask —
"the research factory must be able to observe/diagnose/mutate/compile/
test/compare/survivor-select/learn without a human resubmission step" —
ALREADY BUILT, end to end, by this exact module (`run_research_factory_
cycle()` below). `docs/Architecture.md`'s own now-corrected note that
called this "the separate 'Autonomous Strategy Factory' directive... not
yet built" was written before this module existed and was stale; it has
been corrected as part of this pass rather than left to mislead a future
reader. Two real, previously-disclosed gaps THIS pass closes instead
(see this module's own updated code + `app/research_pareto.py`'s
docstring for the full detail):

  1. PARETO SURVIVOR SELECTION. Real, multi-dimensional Pareto dominance
     (`app/research_pareto.py::compute_pareto_frontier()`) now decides
     which non-dominated sibling's mutation lineage continues (Section
     6/16) — layered ON TOP OF, never replacing, the existing real
     lexicographic comparator (`app/research_fitness.py::rank_
     candidates()`), which still breaks ties among Pareto-equals. Every
     completed run also gets one real, disclosed frontier over its ENTIRE
     lineage tree, persisted as `FactoryRunRecord.pareto_frontier`.
  2. ANTI-OSCILLATION / DUPLICATE-STATE GUARD (Section 10). A real,
     lineage-scoped set of every mutated definition's own exact
     `source_text` already tested — an exact repeat (a parameter-state
     duplicate, or a direct A->B->A reversal) is pruned via the SAME
     `duplicate_pruned` lifecycle stage `app/research_discovery.py`'s
     own `prune_duplicates()` already established, never spending a real
     backtest on a state this lineage has already proven out.

Genuine gaps this addendum does NOT attempt, disclosed rather than
silently skipped: no auto-continuation from a Discovery cycle straight
into a Factory run (still a real, disclosed manual hand-off — see
`app/research_discovery.py`'s own docstring); no auto-restart of a
stopped lineage with a materially different, non-parameter-tweak
hypothesis; no new mutation operators for `regime_failure`/
`negative_net_return`/`benchmark_underperformance` (still requires a
compiler-grammar change — see this module's own "THE ONE MUTATION
CATEGORY..." section above, unchanged); no full pairwise statistical-
significance test between every sibling (see `app/research_pareto.py`'s
own docstring for why trade count stands in as the real, disclosed
evidence-quantity dimension instead).
"""
from __future__ import annotations

import hashlib
import time
from collections import Counter
from typing import Literal

from app.adversarial_research import run_adversarial_research
from app.champion_challenger import ChampionRecord, get_current_champion
from app.research_council import convene_research_council
from app.research_fitness import describe_fitness_rank, rank_candidates
from app.research_pareto import compute_pareto_frontier
from app.research_loop import (
    FAILURE_CODE_MUTATION_PRIORITY,
    MAX_ITERATIONS_PER_FAMILY,
    MAX_MUTATIONS_PER_PARENT,
    _MUTATION_TEMPLATES,
    evaluate_research_budget,
    generate_research_lesson,
    run_research_loop_iteration,
)
from app.schemas import (
    CandidacyBinning,
    CandidateLifecycleStage,
    CompiledStrategyDefinition,
    CompiledStrategyStatus,
    FactoryCandidateRecord,
    FactoryRunConfig,
    FactoryRunRecord,
    FailedStrategyArchiveEntry,
    FailureCode,
    LessonEvidenceSummary,
    MutationCandidate,
    MutationRecord,
    QuantResearchExperiment,
    ResearchLessonRecord,
    ResearchLoopIterationRecord,
    StrategyHypothesis,
)
from app.strategy_compiler import (
    _CHANDELIER_PARAMS_PATTERN,
    _DEFAULT_CHANDELIER_ATR_MULTIPLIER,
    _DEFAULT_CHANDELIER_ATR_PERIOD,
    _PERCENT_STOP_PATTERN,
    _R_MULTIPLE_TARGET_PATTERN,
    _RATIO_TARGET_PATTERN,
    _REQUIREMENT_PATTERN,
    _RSI_THRESHOLD_PATTERN,
    _STOCHASTIC_THRESHOLD_PATTERN,
    _TREND_SCORE_THRESHOLD_PATTERN,
    _number_from_word,
)
from app.strategy_engine import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME
from app.strategy_registry import register_strategy_version

# Section 15/21 — a real, disclosed, bounded factory-run budget. Layered
# ON TOP OF (never replacing) app/research_loop.py's own real
# MAX_ITERATIONS_PER_FAMILY/MAX_MUTATIONS_PER_PARENT, which this module
# still enforces every generation via evaluate_research_budget().
MAX_GENERATIONS_PER_FACTORY_RUN = 5
MAX_TOTAL_BACKTESTS_PER_FACTORY_RUN = 10

# CEO directive "TradeTown — Phase 9: Full Autonomous Quant Research
# Factory," Phase 5 — real, disclosed hard limits for the multi-child
# ("branching") mode `run_research_factory_cycle()`'s own
# `max_children_per_parent` parameter enables. NOT the pure function's
# own default (which stays 1 — see that parameter's own docstring for
# why every existing caller/test keeps the original single-child
# behavior unless it explicitly opts in); these are the values
# `app/routers/sandbox.py`'s `/research-factory/run` endpoint passes
# for a NEW, real, tree-shaped factory run going forward.
MAX_CHILDREN_PER_PARENT = 3
MAX_RUNTIME_SECONDS = 300

# Section 2's own bounded-mutation-operator caps — one reasonable,
# disclosed convention per parameter, not derived from any study,
# matching this codebase's own "real, disclosed, simple threshold"
# idiom used throughout app/research_loop.py.
MIN_TARGET_R = 1.0
MAX_TARGET_R = 5.0
TARGET_STEP_R = 0.5
MAX_CHANDELIER_ATR_MULTIPLIER = 6.0
CHANDELIER_STEP = 0.5
MAX_FIXED_STOP_PERCENT = 10.0
FIXED_STOP_STEP_PCT = 1.0
MAX_CONSECUTIVE_CANDLES = 10
THRESHOLD_RELAX_STEP = 5.0
THRESHOLD_MIN_GAP_FROM_NEUTRAL = 5.0
TREND_SCORE_RELAX_STEP = 0.5
TREND_SCORE_MIN_GAP_FROM_NEUTRAL = 0.5


def _infer_direction(definition: CompiledStrategyDefinition) -> Literal["long", "short"] | None:
    """A real, disclosed read of the parent's own already-compiled
    trigger direction — `gt`/`crosses_above` is this codebase's own
    established long-biased convention (see app/strategy_compiler.py's
    own module docstring), `lt`/`crosses_below` short. `None` when the
    trigger step has no directional operator (e.g. `eq`) or no trigger
    step exists at all — never guessed."""
    for step in definition.sequence:
        if step.step_type != "trigger":
            continue
        conditions = step.all_of if step.all_of else ([step.condition] if step.condition is not None else [])
        for condition in conditions:
            if condition is None:
                continue
            if condition.operator in ("gt", "crosses_above"):
                return "long"
            if condition.operator in ("lt", "crosses_below"):
                return "short"
    return None


def _widen_stop(source_text: str, definition: CompiledStrategyDefinition) -> tuple[str | None, dict[str, str], str]:
    """`excessive_drawdown` — widens the parent's own real, already-
    compiled stop by one bounded step, reusing the EXACT SAME private
    regex `app/strategy_compiler.py` itself uses to recognize the
    value, so the mutated text is guaranteed to re-parse identically."""
    stop = definition.stop
    if stop is None:
        return None, {}, "No recognizable stop in the parent definition to widen."
    if stop.method == "chandelier":
        current_mult = stop.atr_multiplier if stop.atr_multiplier is not None else _DEFAULT_CHANDELIER_ATR_MULTIPLIER
        current_period = stop.atr_period if stop.atr_period is not None else _DEFAULT_CHANDELIER_ATR_PERIOD
        new_mult = round(min(current_mult + CHANDELIER_STEP, MAX_CHANDELIER_ATR_MULTIPLIER), 2)
        if new_mult <= current_mult:
            return None, {}, f"Chandelier ATR multiplier already at the real {MAX_CHANDELIER_ATR_MULTIPLIER:g}x bound — no further bounded widening available."
        replacement = f"{current_period}-period ATR and a {new_mult:g}x"
        params_match = _CHANDELIER_PARAMS_PATTERN.search(source_text)
        mutated = _CHANDELIER_PARAMS_PATTERN.sub(replacement, source_text, count=1) if params_match else source_text.rstrip() + f" Use a chandelier stop with a {replacement} multiplier."
        return mutated, {"chandelierAtrMultiplier": f"{current_mult:g}x -> {new_mult:g}x"}, f"Bounded: ATR multiplier widens by at most {CHANDELIER_STEP:g}x per mutation, capped at {MAX_CHANDELIER_ATR_MULTIPLIER:g}x."
    if stop.method == "fixed_percent" and stop.percent is not None:
        new_pct = round(min(stop.percent + FIXED_STOP_STEP_PCT, MAX_FIXED_STOP_PERCENT), 2)
        if new_pct <= stop.percent:
            return None, {}, f"Fixed-percent stop already at the real {MAX_FIXED_STOP_PERCENT:g}% bound."
        mutated = _PERCENT_STOP_PATTERN.sub(f"{new_pct:g}% stop", source_text, count=1)
        return mutated, {"fixedStopPercent": f"{stop.percent:g}% -> {new_pct:g}%"}, f"Bounded: stop widens by at most {FIXED_STOP_STEP_PCT:g}% per mutation, capped at {MAX_FIXED_STOP_PERCENT:g}%."
    return None, {}, f"Stop method '{stop.method}' has no bounded numeric parameter this operator can widen (a swing-level stop has no free parameter at all)."


def _adjust_target(source_text: str, definition: CompiledStrategyDefinition, *, delta: float) -> tuple[str | None, dict[str, str], str]:
    """`low_profit_factor`/`cost_sensitivity` (delta > 0, widen) and
    `outlier_dependent` (delta < 0, cap the biggest wins) — both real,
    bounded nudges to the parent's own already-compiled R-multiple
    target."""
    target = definition.target
    if target is None or target.method != "r_multiple":
        return None, {}, "No recognizable R-multiple target in the parent definition to adjust (a fixed-percent target has no bounded operator in this pass)."
    new_value = round(max(MIN_TARGET_R, min(target.value + delta, MAX_TARGET_R)), 2)
    if new_value == target.value:
        return None, {}, f"Target already at the real [{MIN_TARGET_R:g}R, {MAX_TARGET_R:g}R] bound."
    r_match = _R_MULTIPLE_TARGET_PATTERN.search(source_text)
    ratio_match = _RATIO_TARGET_PATTERN.search(source_text)
    if r_match:
        mutated = _R_MULTIPLE_TARGET_PATTERN.sub(f"target {new_value:g}R", source_text, count=1)
    elif ratio_match:
        mutated = _RATIO_TARGET_PATTERN.sub(f"{new_value:g}:1 reward", source_text, count=1)
    else:
        return None, {}, "Target phrasing not recognized for bounded substitution."
    direction = "widens" if delta > 0 else "narrows"
    return mutated, {"targetRMultiple": f"{target.value:g}R -> {new_value:g}R"}, f"Bounded: target {direction} by at most {abs(delta):g}R per mutation, within [{MIN_TARGET_R:g}R, {MAX_TARGET_R:g}R]."


def _add_confirmation_bar(source_text: str, definition: CompiledStrategyDefinition) -> tuple[str | None, dict[str, str], str]:
    """`walk_forward_failure` — a real, bounded +1 to the parent's own
    consecutive-candle pullback requirement (or, if none exists yet,
    appends a real, minimal 2-candle one in the direction opposite the
    trigger, matching this codebase's own seed-strategy convention —
    see app/strategy_registry.py's `_ema_pullback_source_text()`)."""
    requirement_match = _REQUIREMENT_PATTERN.search(source_text)
    if requirement_match:
        count_word, candle_direction_word = requirement_match.groups()
        current = _number_from_word(count_word)
        if current is None:
            return None, {}, "Existing consecutive-candle count could not be parsed as a real integer."
        new_count = min(current + 1, MAX_CONSECUTIVE_CANDLES)
        if new_count <= current:
            return None, {}, f"Consecutive-candle requirement already at the real {MAX_CONSECUTIVE_CANDLES}-candle bound."
        mutated = _REQUIREMENT_PATTERN.sub(f"at least {new_count} {candle_direction_word.lower()} candles", source_text, count=1)
        return mutated, {"minConsecutiveBars": f"{current} -> {new_count}"}, f"Bounded: +1 candle per mutation, capped at {MAX_CONSECUTIVE_CANDLES}."
    direction = _infer_direction(definition)
    if direction is None:
        return None, {}, "No existing requirement clause and no inferable trigger direction to add one safely."
    candle_word = "bearish" if direction == "long" else "bullish"
    mutated = source_text.rstrip() + f" It also requires at least 2 {candle_word} candles as the pullback."
    return mutated, {"minConsecutiveBars": f"none -> 2 {candle_word}"}, "Bounded: adds a real, minimal 2-candle pullback confirmation requirement."


def _relax_toward_neutral(threshold: float, side: str, step: float, neutral: float, min_gap: float) -> float | None:
    if side.lower() == "above":
        new_value = max(threshold - step, neutral + min_gap)
    else:
        new_value = min(threshold + step, neutral - min_gap)
    return round(new_value, 2) if new_value != threshold else None


def _relax_threshold(source_text: str, definition: CompiledStrategyDefinition) -> tuple[str | None, dict[str, str], str]:
    """`parameter_sensitivity` — a real, bounded relaxation of the
    parent's own swept numeric trigger threshold (RSI/Stochastic/
    multi-horizon trend score) toward its own neutral midpoint, never
    crossing it. EMA/SMA/MACD/event-pulse triggers have no swept
    threshold — `None`, disclosed, for those trigger shapes."""
    for pattern, label in ((_RSI_THRESHOLD_PATTERN, "RSI"), (_STOCHASTIC_THRESHOLD_PATTERN, "Stochastic")):
        match = pattern.search(source_text)
        if not match:
            continue
        period_str, side, threshold_str = match.groups()
        new_value = _relax_toward_neutral(float(threshold_str), side, THRESHOLD_RELAX_STEP, 50.0, THRESHOLD_MIN_GAP_FROM_NEUTRAL)
        if new_value is None:
            return None, {}, f"{label} threshold already within the real {THRESHOLD_MIN_GAP_FROM_NEUTRAL:g}-point bounded-relaxation floor of neutral (50)."
        period_clause = f"{period_str} " if period_str else ""
        mutated = pattern.sub(f"the {period_clause}{label} is {side.lower()} {new_value:g}", source_text, count=1)
        return mutated, {f"{label.lower()}Threshold": f"{threshold_str} -> {new_value:g}"}, f"Bounded: threshold relaxes toward neutral by at most {THRESHOLD_RELAX_STEP:g} per mutation, never closer than {THRESHOLD_MIN_GAP_FROM_NEUTRAL:g} to neutral (50)."
    match = _TREND_SCORE_THRESHOLD_PATTERN.search(source_text)
    if match:
        side, threshold_str = match.groups()
        new_value = _relax_toward_neutral(float(threshold_str), side, TREND_SCORE_RELAX_STEP, 0.0, TREND_SCORE_MIN_GAP_FROM_NEUTRAL)
        if new_value is None:
            return None, {}, f"Multi-horizon trend score threshold already within the real {TREND_SCORE_MIN_GAP_FROM_NEUTRAL:g}-point bounded-relaxation floor of neutral (0)."
        mutated = _TREND_SCORE_THRESHOLD_PATTERN.sub(f"the multi-horizon trend score is {side.lower()} {new_value:g}", source_text, count=1)
        return mutated, {"trendScoreThreshold": f"{threshold_str} -> {new_value:g}"}, f"Bounded: threshold relaxes toward neutral (0) by at most {TREND_SCORE_RELAX_STEP:g} per mutation."
    return None, {}, "No RSI/Stochastic/multi-horizon-trend-score numeric threshold trigger found — EMA/SMA/MACD/event-pulse triggers have no swept numeric threshold for this operator."


# Section 2 — the real, disclosed mapping from a failure code this
# codebase can diagnose to a bounded, deterministic text operator.
# `regime_failure`/`negative_net_return`/`benchmark_underperformance`
# are deliberately absent (see this module's own docstring for exactly
# why) — `build_mutation_candidate()` below produces a real
# `MutationCandidate` for them too, with `mutatedSourceText=None` and an
# explicit, disclosed `constraints` string, never silently dropped.
_MUTATION_OPERATOR_TYPE: dict[FailureCode, str] = {
    "excessive_drawdown": "widen_stop",
    "low_profit_factor": "widen_target",
    "cost_sensitivity": "widen_target",
    "outlier_dependent": "narrow_target",
    "walk_forward_failure": "add_confirmation_bar",
    "parameter_sensitivity": "relax_threshold",
}


def _mutation_record_for_code(
    code: FailureCode,
    *,
    parent_definition_id: str,
    parent_definition_version: int,
    parent_iteration_id: str,
    mutation_number: int,
    mutation_id: str,
    created_at: str,
) -> MutationRecord | None:
    """CEO directive "TradeTown — Phase 9: Full Autonomous Quant
    Research Factory," Phase 5/9 (Recursive Evolution / Failure-Driven
    Evolution) — the SAME real template lookup
    `app/research_loop.py::propose_mutation()` uses for ITS single
    highest-priority code, applied here to an EXPLICIT code so multiple
    real, distinctly-diagnosed failure codes from the SAME iteration can
    each get their own correctly-worded `MutationRecord` (never reusing
    the top-priority code's own `proposed_change`/`reason`/
    `expected_effect` text for a DIFFERENT code, which would misdescribe
    the actual mutation being tested). `None` when `code` has no
    template — same real, disclosed limitation `propose_mutation()`
    already has for `regime_failure`."""
    if code not in _MUTATION_TEMPLATES:
        return None
    proposed_change, reason, expected_effect = _MUTATION_TEMPLATES[code]
    return MutationRecord(
        id=mutation_id,
        parentDefinitionId=parent_definition_id,
        parentDefinitionVersion=parent_definition_version,
        parentIterationId=parent_iteration_id,
        mutationNumber=mutation_number,
        observedFailureCodes=[code],
        proposedChange=proposed_change,
        reason=reason,
        expectedEffect=expected_effect,
        validationRequirements="Must clear the same real research funnel this parent went through — historical backtest, cost stress, walk-forward, regime, parameter robustness, statistical evidence, and benchmark comparison — before any candidacy decision is honored.",
        createdAt=created_at,
    )


def retrieve_relevant_lessons(
    lessons: list[ResearchLessonRecord],
    *,
    strategy_family: str,
    failure_codes: list[FailureCode],
    max_matches: int = 5,
) -> list[ResearchLessonRecord]:
    """CEO directive "Phase 9: Full Autonomous Quant Research Factory,"
    Phase 8 (Self-Improvement Memory) — STRUCTURED retrieval (exact
    field matches: same `strategy_family` AND at least one overlapping
    real `failure_code`), most-recent-first, capped at `max_matches`.
    Deliberately NOT `app/failure_taxonomy.py::find_similar_failed_
    strategies()`'s fuzzy word-overlap match — that already-real
    function serves a different purpose (screening a brand-new proposal
    against the PERMANENT failed archive before it is even filed; see
    `run_research_loop_iteration()`'s own `similar_failed_strategies`
    field) and this module never duplicates it. An empty result is
    itself a real, honest outcome (no relevant memory on file yet),
    never fabricated as "no similar history."" """
    matches: list[ResearchLessonRecord] = []
    for lesson in reversed(lessons):
        if lesson.strategy_family != strategy_family:
            continue
        if not any(code in lesson.failure_codes for code in failure_codes):
            continue
        matches.append(lesson)
        if len(matches) >= max_matches:
            break
    return matches


def build_mutation_candidate(
    mutation: MutationRecord, definition: CompiledStrategyDefinition, *, mutation_candidate_id: str, created_at: str
) -> MutationCandidate:
    """Section 2's real, executable successor to `MutationRecord` —
    wraps that already-real, already-persisted recommendation with
    either a real, bounded, re-compilable mutated source text, or an
    honest `None` and a disclosed reason. `mutation.observed_failure_
    codes[0]` is always this iteration's own single highest-priority
    real failure code (app/research_loop.py's `propose_mutation()` own
    disclosed priority order) — never a second, independent choice."""
    target_code = mutation.observed_failure_codes[0] if mutation.observed_failure_codes else None
    operator_type = _MUTATION_OPERATOR_TYPE.get(target_code) if target_code is not None else None
    mutated_text: str | None
    changed_parameters: dict[str, str]
    constraints: str
    if operator_type == "widen_stop":
        mutated_text, changed_parameters, constraints = _widen_stop(definition.source_text, definition)
    elif operator_type == "widen_target":
        mutated_text, changed_parameters, constraints = _adjust_target(definition.source_text, definition, delta=TARGET_STEP_R)
    elif operator_type == "narrow_target":
        mutated_text, changed_parameters, constraints = _adjust_target(definition.source_text, definition, delta=-TARGET_STEP_R)
    elif operator_type == "add_confirmation_bar":
        mutated_text, changed_parameters, constraints = _add_confirmation_bar(definition.source_text, definition)
    elif operator_type == "relax_threshold":
        mutated_text, changed_parameters, constraints = _relax_threshold(definition.source_text, definition)
    else:
        mutated_text, changed_parameters = None, {}
        constraints = (
            f"No bounded, deterministic textual operator exists for failure code '{target_code}' — this codebase's "
            "real compiler vocabulary supports at most one trigger per strategy with no generic way to add a second, "
            "combined regime-confirmation condition (regime_failure), or requires a materially different, "
            "human-authored hypothesis rather than a parameter tweak (negative_net_return/benchmark_underperformance). "
            "See app/research_factory.py's own module docstring."
        )
    reproducibility_seed = hashlib.sha256(f"{definition.id}:{definition.version}:{operator_type or 'none'}:{mutation.mutation_number}".encode()).hexdigest()[:16]
    return MutationCandidate(
        id=mutation_candidate_id,
        parentDefinitionId=mutation.parent_definition_id,
        parentDefinitionVersion=mutation.parent_definition_version,
        mutationType=operator_type or "unsupported",
        changedParameters=changed_parameters,
        hypothesis=f"{definition.name}, mutated: {mutation.proposed_change}",
        rationale=mutation.reason,
        expectedEffect=mutation.expected_effect,
        constraints=constraints,
        mutatedSourceText=mutated_text,
        reproducibilitySeed=reproducibility_seed,
        createdAt=created_at,
    )


def generate_next_hypothesis(
    parent_hypothesis: StrategyHypothesis,
    parent_definition: CompiledStrategyDefinition,
    mutation: MutationCandidate,
    *,
    lesson_ids_used: list[str],
    failure_codes_addressed: list[FailureCode],
    hypothesis_id: str,
    lineage_id: str,
    created_at: str,
) -> StrategyHypothesis:
    """Section 1's real generator — consumes the parent's own real
    lesson(s)/mutation and produces a new, structured, falsifiable
    `StrategyHypothesis` with a real, disclosed reason, never a randomly
    invented trading rule. `research_rationale` is the mutation's own
    real rationale (traceable to a real failure code and real evidence
    — never a fabricated narrative)."""
    return StrategyHypothesis(
        id=hypothesis_id,
        hypothesis=mutation.hypothesis,
        marketMechanism=parent_hypothesis.market_mechanism,
        expectedEdge=mutation.expected_effect,
        invalidationConditions=parent_hypothesis.invalidation_conditions,
        symbolUniverse=parent_hypothesis.symbol_universe,
        timeframe=parent_hypothesis.timeframe,
        entryConditions="See compiled definition.",
        exitConditions="See compiled definition.",
        stopLossLogic="See compiled definition.",
        takeProfitLogic="See compiled definition.",
        positionSizingLogic=parent_hypothesis.position_sizing_logic,
        riskConstraints=parent_hypothesis.risk_constraints,
        indicatorsFeatures=parent_hypothesis.indicators_features,
        regimeAssumptions=parent_hypothesis.regime_assumptions,
        researchRationale=mutation.rationale,
        parentStrategyFamily=parent_definition.name,
        parentDefinitionId=parent_definition.id,
        parentDefinitionVersion=parent_definition.version,
        proposedBy=parent_hypothesis.proposed_by,
        createdAt=created_at,
        generation=parent_hypothesis.generation + 1,
        lineageId=lineage_id,
        reasonForGeneration=f"Generation {parent_hypothesis.generation + 1}: {mutation.rationale}",
        lessonsUsed=lesson_ids_used,
        failureCodesAddressed=failure_codes_addressed,
        mutationOperatorUsed=mutation.mutation_type,
        expectedImprovement=mutation.expected_effect,
        expectedRisk=(
            "This mutation may introduce a new failure mode not present in the parent — it must independently clear "
            "the full real research funnel again, never assumed safe purely from the parent's own evidence."
        ),
        reproducibilitySeed=mutation.reproducibility_seed,
        sourceEvidenceIds=[mutation.id, *lesson_ids_used],
    )


def derive_lifecycle_stage(*, compile_status: CompiledStrategyStatus, candidacy: CandidacyBinning | None) -> CandidateLifecycleStage:
    """Section 7's real, minimal, honestly-reachable lifecycle
    derivation — see this module's own docstring for exactly which
    declared states this function can and cannot actually produce."""
    if compile_status != "compiled":
        return "compile_rejected"
    if candidacy is None:
        return "backtested"
    if candidacy == "accepted":
        return "survivor"
    if candidacy == "promising":
        return "candidate"
    return "rejected"


def run_research_factory_cycle(
    seed_hypothesis: StrategyHypothesis,
    seed_definition: CompiledStrategyDefinition,
    *,
    compiled_strategy_registry: dict[str, list[CompiledStrategyDefinition]],
    quant_research_experiments: list[QuantResearchExperiment],
    research_iterations: list[ResearchLoopIterationRecord],
    research_lessons: list[ResearchLessonRecord],
    failed_archive: list[FailedStrategyArchiveEntry],
    champion_history: list[ChampionRecord],
    risk_per_trade_pct: float,
    run_id: str,
    created_at: str,
    max_generations: int = MAX_GENERATIONS_PER_FACTORY_RUN,
    max_total_backtests: int = MAX_TOTAL_BACKTESTS_PER_FACTORY_RUN,
    symbols: list[str] | None = None,
    timeframe: str | None = None,
    candles_per_symbol: int | None = None,
    # CEO directive "TradeTown — Phase 9: Full Autonomous Quant Research
    # Factory," Phase 5 — additive, opt-in. Both default to the exact
    # original Phase 7 behavior (one child per parent, no wall-clock
    # cap) so every existing caller/test is completely unaffected unless
    # it explicitly passes a larger value — see this function's own
    # updated docstring below for what changes when it does.
    max_children_per_parent: int = 1,
    max_runtime_seconds: int = 0,
) -> tuple[FactoryRunRecord, dict[str, list[CompiledStrategyDefinition]], list[ResearchLoopIterationRecord], list[ResearchLessonRecord]]:
    """Section 26's one real entry point — the complete, bounded,
    deterministic, multi-generation OBSERVE->GENERATE->MUTATE->COMPILE->
    BACKTEST->ADVERSARIAL-ATTACK->VALIDATE->STRESS->COMPARE->
    ACCEPT-OR-BIN->LEARN loop.

    A PURE function, matching this codebase's own established
    app/*.py-is-pure/app/state.py-persists-under-lock convention (see
    app/research_loop.py's own `run_research_loop_iteration()` for the
    same discipline): mutates no shared state, generates no random/uuid
    identity, and returns the full real result set (the new
    `FactoryRunRecord`, the updated `compiled_strategy_registry`, and
    the EXTENDED `research_iterations`/`research_lessons` lists — every
    generation's own real `ResearchLoopIterationRecord`/
    `ResearchLessonRecord` is appended into these SAME lists Phase 4-6
    already persists, never a second, parallel copy) for the caller
    (app/state.py) to persist under its own lock.

    CEO directive "TradeTown — Phase 9: Full Autonomous Quant Research
    Factory" closed two real, previously-disclosed gaps in this SAME
    loop: (1) every generation's own primary candidate now ALSO runs a
    real adversarial attack suite (app/adversarial_research.py) and a
    real Research Council evidence-aggregation pass
    (app/research_council.py) — this module's own Phase 7/8 docstring
    (see git history) and app/research_discovery.py's own module
    docstring both explicitly flagged this as the "next real milestone"
    (population-based discovery already ran adversarial tests per
    candidate; this single-lineage mutation loop never did). (2) when
    `max_children_per_parent > 1`, each generation branches into up to
    that many real sibling mutation candidates — one per DISTINCT real
    diagnosed `FailureCode` in that generation's own `iteration.
    failure_codes` (never a fabricated split of one code into several;
    a generation with only one real diagnosed code still produces
    exactly one real child, identical to the original Phase 7 behavior)
    — each independently compiled, backtested, and adversarially
    attacked, then ranked by app/research_fitness.py's real,
    robustness-first (never raw-return-first) comparator. Every
    sibling, winning or not, is permanently recorded with its own real
    `sibling_rank`/`fitness_rationale`; only the best-ranked COMPILED
    child continues the lineage into the next generation — the rest
    stay in `candidates`, never deleted (Section 17).

    Stops the first time ANY of the following becomes true, and always
    records a real, disclosed `stop_reason`: a generation's mutated text
    fails to compile (`compile_rejected`); the real
    app/research_loop.py budget (family iteration count / mutations for
    this parent) is exhausted; this run's own `max_total_backtests` is
    reached; `max_runtime_seconds` real wall-clock elapses (0 disables
    this check — a real safety net, not a reproducibility mechanism, so
    disabled by default for deterministic test runs); `max_generations`
    is reached; a generation (or, in branching mode, any of its real
    siblings) reaches `candidacy == "accepted"` (a real SURVIVOR —
    Section 26's own "repeat within budget" stops once a qualified
    survivor exists, since further mutating an already-accepted
    candidate is not this directive's own ask); or none of this
    generation's diagnosed failure code(s) has a real mutation template,
    or none of the resulting mutation candidates has a bounded automatic
    text operator (Section 15's own "STOP and explain the constraint"
    rule, applied per-lineage rather than only in prose)."""
    resolved_timeframe = timeframe if timeframe is not None else (seed_definition.timeframe or DEFAULT_TIMEFRAME)
    resolved_candles = candles_per_symbol if candles_per_symbol is not None else DEFAULT_CANDLES_PER_SYMBOL
    lineage_id = run_id
    registry = compiled_strategy_registry
    all_iterations = list(research_iterations)
    all_lessons = list(research_lessons)
    run_lessons: list[ResearchLessonRecord] = []
    candidates: list[FactoryCandidateRecord] = []
    backtests_run = 0
    start_time = time.monotonic()

    def _test_definition(
        definition: CompiledStrategyDefinition, hypothesis: StrategyHypothesis, *, generation_num: int, parent_id: str | None, gen_label: str
    ) -> FactoryCandidateRecord:
        """Runs ONE real definition through the full funnel + a real
        adversarial attack + a real Research Council pass, and packages
        the result — never called twice for the same real (definition,
        hypothesis) pair (see this closure's two call sites below:
        once for the seed, once per real sibling)."""
        nonlocal backtests_run
        candidate_id = f"{gen_label}-candidate"
        if definition.status != "compiled":
            return FactoryCandidateRecord(
                id=candidate_id,
                runId=run_id,
                generation=generation_num,
                parentCandidateId=parent_id,
                lineageId=lineage_id,
                strategyFamily=definition.name,
                definitionId=definition.id,
                definitionVersion=definition.version,
                hypothesis=hypothesis,
                lifecycleStage="compile_rejected",
                compileStatus=definition.status,
                compileDetail=definition.detail,
                iteration=None,
                mutationCandidate=None,
                survived=False,
                decisionReason=f"Compilation status '{definition.status}': {definition.detail}",
                createdAt=created_at,
            )

        iteration = run_research_loop_iteration(
            hypothesis,
            definition,
            quant_research_experiments=quant_research_experiments,
            research_iterations=all_iterations,
            failed_archive=failed_archive,
            risk_per_trade_pct=risk_per_trade_pct,
            iteration_id=f"{gen_label}-experiment",
            mutation_id=f"{gen_label}-mutation-record",
            created_at=created_at,
            symbols=symbols,
            timeframe=resolved_timeframe,
            candles_per_symbol=resolved_candles,
        )
        backtests_run += 1
        all_iterations.append(iteration)

        lesson = generate_research_lesson(
            lesson_id=f"{gen_label}-lesson",
            strategy_family=iteration.strategy_family,
            definition_id=definition.id,
            definition_version=definition.version,
            iteration_id=iteration.id,
            parent_definition_id=hypothesis.parent_definition_id,
            mutation_id=(iteration.mutation.id if iteration.mutation is not None else None),
            hypothesis=hypothesis.hypothesis,
            candidacy=iteration.candidacy,
            candidacy_reason=iteration.candidacy_reason,
            scorecard=iteration.scorecard,
            trade_count=iteration.scorecard.trade_count or 0,
            created_at=created_at,
            failure_codes=[fc.code for fc in iteration.failure_codes],
        )
        all_lessons.append(lesson)
        run_lessons.append(lesson)

        # CEO directive "Phase 9: Full Autonomous Quant Research
        # Factory" — every real candidate now gets a real adversarial
        # attack, reusing the real trades this same backtest already
        # computed (never a second fetch/backtest — see
        # CompiledStrategyBacktestResult.trades's own docstring).
        adversarial_result = run_adversarial_research(
            definition,
            regime_trend_breakdown=iteration.experiment.backtest.regime_trend_breakdown,
            regime_volatility_breakdown=iteration.experiment.backtest.regime_volatility_breakdown,
            parameter_sensitivity=iteration.experiment.parameter_sensitivity,
            risk_per_trade_pct=risk_per_trade_pct,
            result_id=f"{gen_label}-adversarial",
            generated_at=created_at,
            symbols=symbols,
            timeframe=resolved_timeframe,
            candles_per_symbol=resolved_candles,
            closed_trades=iteration.experiment.backtest.trades,
        )
        council = convene_research_council(
            iteration, report_id=f"{gen_label}-council", candidate_id=candidate_id, generated_at=created_at, adversarial_result=adversarial_result
        )

        lifecycle_stage = derive_lifecycle_stage(compile_status=definition.status, candidacy=iteration.candidacy)
        survived = lifecycle_stage == "survivor"
        decision_reason = iteration.candidacy_reason
        if survived:
            decision_reason += (
                " SURVIVOR — eligible for a real, separate Champion/Challenger submission via the existing, "
                "unmodified POST /api/sandbox/champion-challenger/compare endpoint (never auto-submitted by this factory)."
            )

        return FactoryCandidateRecord(
            id=candidate_id,
            runId=run_id,
            generation=generation_num,
            parentCandidateId=parent_id,
            lineageId=lineage_id,
            strategyFamily=definition.name,
            definitionId=definition.id,
            definitionVersion=definition.version,
            hypothesis=hypothesis,
            lifecycleStage=lifecycle_stage,
            compileStatus=definition.status,
            compileDetail=definition.detail,
            iteration=iteration,
            mutationCandidate=None,
            survived=survived,
            decisionReason=decision_reason,
            createdAt=created_at,
            adversarialResult=adversarial_result,
            researchCouncil=council,
        )

    def _replace_candidate(updated: FactoryCandidateRecord) -> None:
        """Updates the already-appended record with `updated.id` in
        place, wherever it landed in `candidates` — never assumes it is
        the last element (a chosen best child is frequently NOT the
        last sibling tested; see the ranking step below)."""
        for idx, existing in enumerate(candidates):
            if existing.id == updated.id:
                candidates[idx] = updated
                return
        raise AssertionError(f"_replace_candidate: {updated.id!r} was never appended to candidates — a real bug, not a legitimate research outcome.")

    current_hypothesis = seed_hypothesis.model_copy(update={"lineage_id": lineage_id})
    current_definition = seed_definition
    generation = current_hypothesis.generation
    parent_candidate_id: str | None = None
    stop_reason = f"Reached the real {max_generations}-generation cap for this factory run."
    current_candidate: FactoryCandidateRecord | None = None
    # Section 10 — real, lineage-scoped anti-oscillation state: every
    # mutated definition's own exact `source_text` this lineage has
    # already tested (seeded with the seed definition itself, so a
    # mutation that would recreate the ORIGINAL, un-mutated strategy is
    # caught too), mapped to the id of the first candidate that tested
    # it. Never reset per-generation — an A->B->A reversal spans two
    # generations, not one.
    tested_source_texts: set[str] = {seed_definition.source_text}
    source_text_first_tested_by: dict[str, str] = {seed_definition.source_text: f"{run_id}-gen{generation}-candidate"}
    # True whenever `current_definition`/`current_hypothesis` still need
    # their own real test — true for the seed; false for a generation
    # whose `current_candidate` already came from the branching step
    # below (already tested there — never re-tested here).
    needs_test = True

    while True:
        gen_label = f"{run_id}-gen{generation}"

        if needs_test:
            if current_definition.status != "compiled":
                current_candidate = _test_definition(current_definition, current_hypothesis, generation_num=generation, parent_id=parent_candidate_id, gen_label=gen_label)
                candidates.append(current_candidate)
                stop_reason = f"Generation {generation}'s mutated source text did not compile (status={current_candidate.compile_status!r}) — a legitimate research failure; this lineage stops here."
                break

            budget = evaluate_research_budget(
                quant_research_experiments, all_iterations, strategy_family=current_definition.name, parent_definition_id=current_hypothesis.parent_definition_id
            )
            if budget.stopped:
                stop_reason = f"Real research budget exhausted before generation {generation}: {budget.stop_reason}"
                break
            if backtests_run >= max_total_backtests:
                stop_reason = f"Reached the real {max_total_backtests}-backtest cap for this single factory run."
                break
            if max_runtime_seconds > 0 and (time.monotonic() - start_time) >= max_runtime_seconds:
                stop_reason = f"Reached the real {max_runtime_seconds}-second wall-clock runtime cap for this factory run."
                break

            current_candidate = _test_definition(current_definition, current_hypothesis, generation_num=generation, parent_id=parent_candidate_id, gen_label=gen_label)
            candidates.append(current_candidate)

        assert current_candidate is not None
        if current_candidate.survived:
            stop_reason = f"Generation {generation} produced a real SURVIVOR clearing every research-candidate requirement — this lineage stops here (repeat-within-budget is for un-accepted lineages)."
            break
        if generation >= max_generations:
            stop_reason = f"Reached the real {max_generations}-generation cap for this factory run without a surviving candidate."
            break
        iteration = current_candidate.iteration
        assert iteration is not None  # guaranteed by compile_status == "compiled" above
        if iteration.mutation is None:
            stop_reason = f"Generation {generation} had no real diagnosed failure code this module has a mutation template for — nothing further to try automatically."
            break

        # Real, distinct, priority-ordered failure codes this generation
        # actually diagnosed (never fabricated splits of one code) —
        # app/research_loop.py's own FAILURE_CODE_MUTATION_PRIORITY,
        # capped at max_children_per_parent (1 by default: reproduces
        # the exact original single-child behavior).
        diagnosed_codes = [fc.code for fc in iteration.failure_codes] or list(iteration.mutation.observed_failure_codes)
        seen: set[str] = set()
        distinct_codes: list[FailureCode] = []
        for code in FAILURE_CODE_MUTATION_PRIORITY:
            if code in diagnosed_codes and code not in seen:
                distinct_codes.append(code)
                seen.add(code)
            if len(distinct_codes) >= max(1, max_children_per_parent):
                break

        sibling_mutation_records = [
            mr
            for i, code in enumerate(distinct_codes, start=1)
            if (
                mr := _mutation_record_for_code(
                    code,
                    parent_definition_id=current_definition.id,
                    parent_definition_version=current_definition.version,
                    parent_iteration_id=iteration.id,
                    mutation_number=i,
                    mutation_id=f"{gen_label}-mutation-record-{i}",
                    created_at=created_at,
                )
            )
            is not None
        ]
        if not sibling_mutation_records:
            stop_reason = f"Generation {generation}: none of the real diagnosed failure code(s) {distinct_codes} has a real mutation template."
            break

        sibling_mutation_candidates = [
            build_mutation_candidate(mr, current_definition, mutation_candidate_id=f"{gen_label}-mutation-candidate-{mr.mutation_number}", created_at=created_at)
            for mr in sibling_mutation_records
        ]
        current_candidate = current_candidate.model_copy(update={"mutation_candidate": sibling_mutation_candidates[0]})
        _replace_candidate(current_candidate)

        viable = [(mc, mr) for mc, mr in zip(sibling_mutation_candidates, sibling_mutation_records) if mc.mutated_source_text is not None]
        if not viable:
            stop_reason = f"Generation {generation}: none of the {len(sibling_mutation_candidates)} diagnosed failure code(s) tested have a bounded, deterministic textual operator ({[mc.constraints for mc in sibling_mutation_candidates]})."
            break

        # Section 13 — real duplicate/redundancy control is already
        # applied to every generation, including every sibling this loop
        # is about to create: run_research_loop_iteration() (inside
        # _test_definition() above) internally runs
        # app/quant_research_lab.py's find_similar_experiments()/
        # classify_research_relationship() against the mutated
        # definition's own real name/hypothesis before this loop ever
        # sees the result — surfaced on each candidate's own real
        # iteration.research_relationship field. No second, duplicate
        # duplicate-check is added here.
        child_entries: list[tuple[FactoryCandidateRecord, CompiledStrategyDefinition, StrategyHypothesis]] = []
        for sib_idx, (mc, mr) in enumerate(viable, start=1):
            if backtests_run >= max_total_backtests:
                break
            child_gen_label = f"{run_id}-gen{generation + 1}" if len(viable) == 1 else f"{run_id}-gen{generation + 1}-sibling{sib_idx}"
            assert mc.mutated_source_text is not None  # guaranteed by the `viable` filter above
            new_definition, registry = register_strategy_version(
                registry, name=current_definition.name, source_text=mc.mutated_source_text, timeframe=resolved_timeframe, created_by=current_hypothesis.proposed_by
            )
            relevant_lessons = retrieve_relevant_lessons(all_lessons, strategy_family=current_definition.name, failure_codes=mr.observed_failure_codes)
            # Deterministic derivation of the parent's OWN lesson id
            # (never `all_lessons[-1]`, which would drift once earlier
            # siblings this same loop have appended their own lessons
            # ahead of this point) — see _test_definition()'s own
            # `f"{gen_label}-lesson"` naming convention.
            parent_lesson_id = f"{current_candidate.id.removesuffix('-candidate')}-lesson"
            child_hypothesis = generate_next_hypothesis(
                current_hypothesis,
                current_definition,
                mc,
                lesson_ids_used=[parent_lesson_id, *[rl.id for rl in relevant_lessons]],
                failure_codes_addressed=list(mr.observed_failure_codes),
                hypothesis_id=f"{child_gen_label}-hypothesis",
                lineage_id=lineage_id,
                created_at=created_at,
            )

            # Section 10 — real anti-oscillation/duplicate-parameter-state
            # guard: an exact repeat of a source text already tested
            # anywhere earlier in THIS lineage (a duplicate parameter
            # state, or a direct A->B->A reversal) is pruned before
            # spending a real backtest — reusing the exact
            # `duplicate_pruned` lifecycle stage app/research_
            # discovery.py's own `prune_duplicates()` already
            # established for the same real concept, never a second
            # dedup vocabulary.
            if new_definition.source_text in tested_source_texts:
                duplicate_of_id = source_text_first_tested_by[new_definition.source_text]
                child_candidate = FactoryCandidateRecord(
                    id=f"{child_gen_label}-candidate",
                    runId=run_id,
                    generation=generation + 1,
                    parentCandidateId=current_candidate.id,
                    lineageId=lineage_id,
                    strategyFamily=new_definition.name,
                    definitionId=new_definition.id,
                    definitionVersion=new_definition.version,
                    hypothesis=child_hypothesis,
                    lifecycleStage="duplicate_pruned",
                    compileStatus=new_definition.status,
                    compileDetail="Not tested — this exact mutated parameter state was already tested earlier in this same lineage (Section 10 anti-oscillation/duplicate-state guard).",
                    iteration=None,
                    mutationCandidate=mc,
                    survived=False,
                    decisionReason=f"Oscillation/duplicate prevented: identical real compiled source text to candidate '{duplicate_of_id}', already tested in this lineage — never re-tested.",
                    createdAt=created_at,
                    duplicateOfCandidateId=duplicate_of_id,
                )
                child_entries.append((child_candidate, new_definition, child_hypothesis))
                continue

            tested_source_texts.add(new_definition.source_text)
            source_text_first_tested_by[new_definition.source_text] = f"{child_gen_label}-candidate"
            child_candidate = _test_definition(new_definition, child_hypothesis, generation_num=generation + 1, parent_id=current_candidate.id, gen_label=child_gen_label)
            child_entries.append((child_candidate, new_definition, child_hypothesis))

        if not child_entries:
            stop_reason = f"Reached the real {max_total_backtests}-backtest cap for this single factory run before any generation {generation + 1} sibling could be tested."
            break

        non_duplicate_entries = [(c, d, h) for c, d, h in child_entries if c.lifecycle_stage != "duplicate_pruned"]
        if not non_duplicate_entries:
            stop_reason = f"Generation {generation + 1}: every real mutation candidate this generation would recreate an already-tested parameter state in this lineage (Section 10 anti-oscillation guard) — no further bounded mutation is available."
            candidates.extend(c for c, _, _ in child_entries)
            break

        tested_children = [c for c, _, _ in child_entries]
        ranked_children = rank_candidates(tested_children)
        rank_by_id = {c.id: i + 1 for i, c in enumerate(ranked_children)}
        total_siblings = len(tested_children)
        # Section 6/15's real, disclosed ranking only means something
        # among ACTUAL siblings — a lone real child (max_children_per_
        # parent=1, the exact original Phase 7 shape, or every other
        # code simply having no template this generation) stays
        # `sibling_rank=None`/`fitness_rationale=None`, matching
        # FactoryCandidateRecord's own schema docstring, never a vacuous
        # "rank 1 of 1."
        if total_siblings > 1:
            child_entries = [
                (child.model_copy(update={"sibling_rank": rank_by_id[child.id], "fitness_rationale": describe_fitness_rank(child, rank=rank_by_id[child.id], total_siblings=total_siblings)}), d, h)
                for child, d, h in child_entries
            ]
        candidates.extend(c for c, _, _ in child_entries)

        survivors = [c for c, _, _ in child_entries if c.survived]
        if survivors:
            best_survivor = min(survivors, key=lambda c: rank_by_id[c.id])
            rank_note = f" (rank {best_survivor.sibling_rank}/{total_siblings} among {total_siblings} real mutation children)" if total_siblings > 1 else ""
            stop_reason = f"A generation {generation + 1} sibling{rank_note} produced a real SURVIVOR — this lineage stops here."
            break

        # Real candidates only — a `duplicate_pruned` sibling never got a
        # real backtest (`iteration is None`) even when its mutated text
        # happened to compile fine, so it can never continue the
        # lineage (the top of the next loop pass assumes `current_
        # candidate.iteration is not None` once `needs_test = False`).
        compiled_children = [(c, d, h) for c, d, h in non_duplicate_entries if c.compile_status == "compiled"]
        if not compiled_children:
            stop_reason = f"All {len(non_duplicate_entries)} real, non-duplicate generation {generation + 1} sibling(s) failed to compile — this lineage stops here."
            break

        # Section 6/16 — real Pareto dominance decides who is even IN
        # CONTENTION to continue the lineage; the existing, unmodified
        # lexicographic comparator above still breaks ties among
        # Pareto-equals. Only meaningful among ACTUAL siblings with real
        # evidence to compare (see app/research_pareto.py's own
        # docstring) — a lone real compiled child (max_children_per_
        # parent=1, the exact original Phase 7 shape) has no real
        # frontier to compute and passes through unfiltered.
        pareto_pool = [c for c, _, _ in compiled_children if c.iteration is not None]
        if len(pareto_pool) > 1:
            generation_frontier = compute_pareto_frontier(pareto_pool)
            non_dominated_ids = {cid for cid, entry in generation_frontier.items() if entry.pareto_status == "non_dominated"}
        else:
            non_dominated_ids = {c.id for c, _, _ in compiled_children}
        # Defensive fallback only — `compute_pareto_frontier()` can never
        # return an empty non-dominated set for a non-empty real pool
        # (dominance is irreflexive), but this keeps the lineage alive
        # rather than crashing if that invariant is ever violated.
        eligible_ids = non_dominated_ids if non_dominated_ids else {c.id for c, _, _ in compiled_children}

        best_candidate, best_definition, best_hypothesis = next((c, d, h) for c, d, h in compiled_children if c.id == next(rc.id for rc in ranked_children if rc.id in eligible_ids))

        current_candidate = best_candidate
        current_definition = best_definition
        current_hypothesis = best_hypothesis
        generation += 1
        needs_test = False  # already tested above — the top of the next loop pass must not re-test it

    candidates_generated = len(candidates)
    candidates_compiled = sum(1 for c in candidates if c.compile_status == "compiled")
    candidates_backtested = sum(1 for c in candidates if c.iteration is not None)
    candidates_validated = sum(1 for c in candidates if c.lifecycle_stage in ("candidate", "survivor"))
    candidates_rejected = sum(1 for c in candidates if c.lifecycle_stage in ("rejected", "compile_rejected"))
    survivor_ids = [c.id for c in candidates if c.survived]

    rejection_counter: Counter[str] = Counter()
    for c in candidates:
        if c.lifecycle_stage == "compile_rejected":
            rejection_counter["compile_rejected"] += 1
        elif c.iteration is not None and c.lifecycle_stage == "rejected":
            for entry in c.iteration.failure_codes:
                rejection_counter[entry.code] += 1
    top_rejection_reasons = [f"{code} ({count})" for code, count in rejection_counter.most_common(5)]

    # Section 16 — one real, disclosed Pareto frontier over EVERY real
    # (backtested) candidate in this run's own lineage tree, computed
    # once at the end from already-real evidence (never a second,
    # per-generation-only view — see app/research_pareto.py's own
    # docstring). A candidate with no real backtest (compile_rejected,
    # duplicate_pruned) simply gets no entry — `pareto_status` stays
    # `None` on it, an honest "no evidence to place on a frontier."
    lineage_frontier = compute_pareto_frontier(candidates)
    if lineage_frontier:
        candidates = [
            (
                c.model_copy(update={"pareto_status": lineage_frontier[c.id].pareto_status, "pareto_dominated_by": lineage_frontier[c.id].dominated_by, "pareto_reason": lineage_frontier[c.id].reason})
                if c.id in lineage_frontier
                else c
            )
            for c in candidates
        ]

    current_champion = get_current_champion(champion_history, strategy_family=seed_definition.name)
    config = FactoryRunConfig(
        maxGenerations=max_generations,
        maxTotalBacktests=max_total_backtests,
        maxMutationsPerParent=MAX_MUTATIONS_PER_PARENT,
        maxIterationsPerFamily=MAX_ITERATIONS_PER_FAMILY,
        maxChildrenPerParent=max_children_per_parent,
        maxRuntimeSeconds=max_runtime_seconds,
    )
    run_record = FactoryRunRecord(
        id=run_id,
        strategyFamily=seed_definition.name,
        seedDefinitionId=seed_definition.id,
        seedDefinitionVersion=seed_definition.version,
        lineageId=lineage_id,
        config=config,
        candidates=candidates,
        generationsCompleted=len({c.generation for c in candidates}),
        candidatesGenerated=candidates_generated,
        candidatesCompiled=candidates_compiled,
        candidatesBacktested=candidates_backtested,
        candidatesValidated=candidates_validated,
        candidatesRejected=candidates_rejected,
        survivorCandidateIds=survivor_ids,
        bestSurvivorCandidateId=(survivor_ids[-1] if survivor_ids else None),
        topRejectionReasons=top_rejection_reasons,
        topLessons=[record.lesson for record in run_lessons[-5:]],
        stopReason=stop_reason,
        currentChampionDefinitionId=(current_champion.definition_id if current_champion is not None else None),
        currentChampionDefinitionVersion=(current_champion.definition_version if current_champion is not None else None),
        createdAt=created_at,
        runtimeSeconds=round(time.monotonic() - start_time, 3),
        paretoFrontier=list(lineage_frontier.values()),
    )
    return run_record, registry, all_iterations, all_lessons


def summarize_lesson_evidence(lessons: list[ResearchLessonRecord]) -> list[LessonEvidenceSummary]:
    """Section 12 — see `LessonEvidenceSummary`'s own docstring
    (app/schemas.py) for the exact real methodology. Computed fresh
    every call; never persisted, never mutates `lessons`."""
    _FAVORABLE: frozenset[str] = frozenset({"accepted", "promising"})

    def _bucket(candidacy: str) -> str:
        return "favorable" if candidacy in _FAVORABLE else "unfavorable"

    by_family: dict[str, list[ResearchLessonRecord]] = {}
    for lesson in lessons:
        by_family.setdefault(lesson.strategy_family, []).append(lesson)

    summaries: list[LessonEvidenceSummary] = []
    for lesson in lessons:
        siblings = [other for other in by_family[lesson.strategy_family] if other.id != lesson.id]
        this_bucket = _bucket(lesson.candidacy)
        supporting = sum(1 for other in siblings if _bucket(other.candidacy) == this_bucket)
        contradicting = sum(1 for other in siblings if _bucket(other.candidacy) != this_bucket)
        summaries.append(
            LessonEvidenceSummary(
                lessonId=lesson.id,
                supportingIterations=supporting,
                contradictingIterations=contradicting,
                lastSeen=lesson.created_at,
                strategiesAffected=[lesson.strategy_family],
            )
        )
    return summaries
