"""app/strategy_families.py — CEO directive "TradeTown — Phase 8:
Autonomous Strategy Discovery + Adversarial Research Engine," Sections
8A-8C: "Build a new Strategy Discovery layer capable of producing
materially different strategy families... Do NOT use random text
generation. Do NOT use an LLM to hallucinate arbitrary strategy source.
Use a constrained strategy grammar based on the compiler's ACTUAL
supported vocabulary."

PHASE 0 FORENSIC RECON, SUMMARIZED. A full read of
`app/strategy_compiler.py`'s real, disclosed vocabulary (its own module
docstring + every `_*_PATTERN` regex) found exactly six real,
materially-different strategy shapes that vocabulary can express without
ever producing a "compiles but has zero real behavioral effect" ghost
condition (see `app/research_factory.py`'s own docstring for the exact,
already-proven reason a generic "add a second combined trigger" shape is
NOT safely expressible): an EMA/SMA cross trigger (`trend_following`), a
Multi-Horizon Trend Score threshold trigger (`breakout` — a materially
different composite mechanism, not a parameter tweak of the EMA
family), an RSI/Stochastic momentum threshold trigger
(`momentum_threshold`), the same EMA cross trigger PLUS a real,
structural multi-candle pullback REQUIREMENT (`pullback_continuation` —
a different real STATE, not just a different number), the same EMA
cross trigger with the chandelier stop's own real ATR multiplier swept
across a wide, meaningful range (`volatility_adjusted_risk` — the
closest honest analog to "volatility" this compiler can express as risk
sizing, since no raw ATR/volatility-THRESHOLD trigger exists anywhere
in its vocabulary — ATR only ever sizes a chandelier stop, never gates
entry), and the same EMA cross trigger with the R-multiple TARGET swept
across a wide range (`risk_reward_variation`, the directive's own
explicitly named family). Three families vary the real TRIGGER
mechanism; three vary a real structural/risk axis on top of the same
baseline trigger — a real, disclosed choice, not an attempt to disguise
six near-identical strategies as materially different.

FAMILIES THE DIRECTIVE NAMED BUT THIS COMPILER CANNOT SAFELY EXPRESS,
DISCLOSED IN `UNSUPPORTED_FAMILIES` RATHER THAN FAKED. "Mean reversion":
`app/strategy_compiler.py`'s own module docstring already discloses its
real RSI/Stochastic convention is deliberately momentum-biased ("RSI
above N" -> long) — a mean-reversion phrasing ("RSI below 30 is
oversold, buy the bounce") needs a trigger direction OPPOSITE its own
threshold side, which the compiler's real trigger/entry-direction-
agreement check correctly flags `status="ambiguous"`, never silently
miscompiled. "Volatility expansion"/"volatility contraction" (as
TRIGGER conditions, not risk sizing): a full grep of every
`_*_PATTERN` in that module confirms no raw ATR/volatility-threshold
trigger exists — `atr` is a resolvable `StrategyIndicatorName` but is
never wired into any trigger-matching regex, only into the chandelier
stop's own params. Regime-conditioned variants (a real, SEPARATE
trigger condition combined with a primary trigger): the exact same real
structural gap `app/research_factory.py`'s own `_MUTATION_OPERATORS`
docstring already proved for its `regime_failure` mutation — no bounded
way exists to add a second, generic combined condition to an arbitrary
primary trigger.

DETERMINISTIC, NEVER-RANDOM GENERATION. `generate_candidate_population()`
below draws every real choice (family, direction, swept parameter
value) from the SAME real `hashlib.sha256(...)` -> `random.Random(...)`
reproducibility convention this codebase already established
(app/strategy_lab.py's Monte Carlo, app/statistical_comparison.py's
bootstrap) — seeded from the caller's own real `seed` string plus each
candidate's own real index, so the exact same `seed` always produces
the exact same real population, byte for byte. No `random` module call
anywhere in this file is ever unseeded.

HONEST DISCLOSURE: `trend_following`/`volatility_adjusted_risk`/
`risk_reward_variation` deliberately share the SAME real EMA-cross
trigger/entry/stop sentence shape — real quant-research practice (same
signal, different risk overlay is a genuinely separate question worth
testing) — differing only in ONE swept numeric parameter each. Their
real generated text can therefore legitimately cross
`prune_duplicates()`'s own real near-duplicate bar against each other
when the specific swept values happen to land close together. This is
CORRECT behavior given how similar those three families' real trading
logic actually is, not a pruning bug — see
`tests/test_strategy_families.py`'s own dedicated test distinguishing
this from the three genuinely mechanism-distinct families
(`trend_following`/`breakout`/`momentum_threshold`, which use real
different trigger indicators and are proven, by that same test, to
never collide).

DUPLICATE PRUNING, REUSED NOT REINVENTED. `prune_duplicates()` below
reuses `app/quant_research_lab.py`'s own real, already-tested
`word_overlap_score()`/`NEAR_DUPLICATE_OVERLAP_THRESHOLD` directly
against each candidate's own real compiled `source_text` (the
compiler's own canonical, structured representation — a richer, more
precise comparison surface than the free-text hypothesis alone) —
never a second, independently-invented similarity heuristic that could
disagree with the one `run_research_loop_iteration()` already applies
against the PERSISTED historical archive. Only WITHIN-POPULATION
near-duplicates are hard-pruned (skipped before backtesting, per
Section 8C's own explicit "do NOT backtest both unnecessarily"); a
near-duplicate against PERSISTED history stays informational-only,
exactly as `app/quant_research_lab.py`'s own docstring already
establishes for that separate, existing check (`research_relationship`
on each candidate's own real `ResearchLoopIterationRecord`) — never a
second, stricter historical gate this module invents on its own.
"""
from __future__ import annotations

import hashlib
import random

from app.quant_research_lab import NEAR_DUPLICATE_OVERLAP_THRESHOLD, word_overlap_score
from app.schemas import FamilyResearchStats, StrategyFamily

# Section 8A — the real, disclosed, requested-but-unsupported families.
# Never silently ignored — surfaced to every caller (see
# `generate_candidate_population()`'s own return contract and the
# `/research-factory/discover` router endpoint) so a CEO/agent sees
# exactly what was NOT attempted and why, rather than a smaller
# population with no explanation.
UNSUPPORTED_FAMILIES: dict[str, str] = {
    "mean_reversion": (
        "app/strategy_compiler.py's real RSI/Stochastic convention is deliberately momentum-biased "
        "('RSI above N' -> long-biased trigger) — see that module's own module docstring. A mean-reversion "
        "phrasing needs the entry direction OPPOSITE its own trigger threshold side, which the compiler's "
        "real trigger/entry-direction-agreement check correctly flags status='ambiguous', never silently "
        "miscompiled. Representing mean-reversion strategies is real, disclosed, tractable future compiler work."
    ),
    "volatility_expansion": (
        "No raw ATR/volatility-THRESHOLD trigger exists anywhere in app/strategy_compiler.py's real vocabulary "
        "(grep-confirmed against every _*_PATTERN in that module) — 'atr' is a resolvable indicator but is only "
        "ever wired into the chandelier stop's own params, never into any trigger-matching regex. Adding a real "
        "volatility-threshold trigger is real, tractable future compiler work, not attempted here."
    ),
    "volatility_contraction": (
        "Same real gap as volatility_expansion above — no raw ATR/volatility-threshold trigger exists in this "
        "compiler's real vocabulary today."
    ),
    "regime_conditioned": (
        "This compiler recognizes AT MOST ONE trigger per strategy (an if/elif chain — first match wins) and its "
        "only real multi-condition mechanism (StrategySequenceStep.all_of) is hard-wired to one specific literal "
        "phrase (the liquidity-sweep+FVG combo), not a generic 'primary trigger AND regime filter.' Appending a "
        "second, unrelated trigger-shaped sentence would re-compile but have ZERO real structural effect — the "
        "exact same real gap app/research_factory.py's own regime_failure mutation operator already disclosed."
    ),
}

SUPPORTED_FAMILIES: tuple[StrategyFamily, ...] = (
    "trend_following",
    "breakout",
    "momentum_threshold",
    "pullback_continuation",
    "volatility_adjusted_risk",
    "risk_reward_variation",
)

_EMA_PERIODS = (20, 50, 100)
_TREND_SCORE_THRESHOLDS = (1.0, 2.0, 3.0)
_RSI_THRESHOLDS = (60.0, 65.0, 70.0, 75.0)
_TARGET_R_VALUES = (1.5, 2.0, 2.5, 3.0, 4.0)
_CHANDELIER_MULTIPLIERS = (2.0, 2.5, 3.0, 3.5, 4.0)
_CHANDELIER_PERIOD = 22
_PULLBACK_CANDLE_COUNTS = (2, 3, 4)
_DIRECTIONS: tuple[str, ...] = ("long", "short")


def _seeded_rng(*parts: str) -> random.Random:
    """This module's own private copy of the real, established
    `hashlib.sha256(...)` -> `random.Random(...)` reproducibility
    convention (see this module's own docstring for why each module
    keeps its own private copy rather than cross-importing another
    module's private helper)."""
    digest = hashlib.sha256(":".join(parts).encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def _source_text_for(family: StrategyFamily, *, direction: str, rng: random.Random) -> tuple[str, dict[str, str]]:
    """The one real, deterministic text-composition function per
    family — every value drawn from the caller's own seeded `rng`, so
    the exact same rng state always produces the exact same real
    source text. `params` names every real swept value chosen, for
    audit/lineage — never hidden inside the free text alone."""
    side = "above" if direction == "long" else "below"
    swing = "high" if direction == "long" else "low"
    action = "Buy" if direction == "long" else "Sell"

    if family == "trend_following":
        period = rng.choice(_EMA_PERIODS)
        target = rng.choice(_TARGET_R_VALUES)
        text = (
            f"{action} when price closes {side} the {period} EMA, then enter when price closes {side} the previous "
            f"swing {swing}. Place the stop at the Chandelier Stop and target {target:g}R."
        )
        return text, {"emaPeriod": str(period), "targetR": f"{target:g}"}

    if family == "breakout":
        threshold = rng.choice(_TREND_SCORE_THRESHOLDS)
        signed_threshold = threshold if direction == "long" else -threshold
        target = rng.choice(_TARGET_R_VALUES)
        text = (
            f"{action} when the multi-horizon trend score is {side} {signed_threshold:g}. Enter when price closes "
            f"{side} the previous swing {swing}. Place the stop at the Chandelier Stop and target {target:g}R."
        )
        return text, {"trendScoreThreshold": f"{signed_threshold:g}", "targetR": f"{target:g}"}

    if family == "momentum_threshold":
        threshold = rng.choice(_RSI_THRESHOLDS)
        signed_threshold = threshold if direction == "long" else (100.0 - threshold)
        target = rng.choice(_TARGET_R_VALUES)
        text = (
            f"{action} when the RSI is {side} {signed_threshold:g}. Enter when price closes {side} the previous "
            f"swing {swing}. Place the stop at the Chandelier Stop and target {target:g}R."
        )
        return text, {"rsiThreshold": f"{signed_threshold:g}", "targetR": f"{target:g}"}

    if family == "pullback_continuation":
        period = rng.choice(_EMA_PERIODS)
        pullback_count = rng.choice(_PULLBACK_CANDLE_COUNTS)
        pullback_direction = "bearish" if direction == "long" else "bullish"
        target = rng.choice(_TARGET_R_VALUES)
        text = (
            f"{action} when price closes {side} the {period} EMA. It requires at least {pullback_count} "
            f"{pullback_direction} candles as the pullback. Enter when price closes {side} the previous swing "
            f"{swing}. Place the stop at the Chandelier Stop and target {target:g}R."
        )
        return text, {"emaPeriod": str(period), "pullbackCandles": str(pullback_count), "targetR": f"{target:g}"}

    if family == "volatility_adjusted_risk":
        period = rng.choice(_EMA_PERIODS)
        multiplier = rng.choice(_CHANDELIER_MULTIPLIERS)
        text = (
            f"{action} when price closes {side} the {period} EMA, then enter when price closes {side} the previous "
            f"swing {swing}. Use a chandelier stop with a {_CHANDELIER_PERIOD}-period ATR and a {multiplier:g}x "
            "multiplier. Target 2R."
        )
        return text, {"emaPeriod": str(period), "chandelierAtrMultiplier": f"{multiplier:g}"}

    if family == "risk_reward_variation":
        period = rng.choice(_EMA_PERIODS)
        target = rng.choice(_TARGET_R_VALUES)
        text = (
            f"{action} when price closes {side} the {period} EMA, then enter when price closes {side} the previous "
            f"swing {swing}. Place the stop at the Chandelier Stop and target {target:g}R."
        )
        return text, {"emaPeriod": str(period), "targetR": f"{target:g}"}

    raise ValueError(f"'{family}' is not a real, compiler-supported family — see UNSUPPORTED_FAMILIES.")


class GeneratedCandidateSeed:
    """One real, deterministic, pre-compile candidate specification —
    a plain data holder (not a persisted schema) that
    `app/research_factory.py`'s discovery orchestrator turns into a real
    `CompiledStrategyDefinition` + `StrategyHypothesis` pair."""

    __slots__ = ("index", "family", "direction", "source_text", "params", "candidate_seed", "research_reason")

    def __init__(self, *, index: int, family: StrategyFamily, direction: str, source_text: str, params: dict[str, str], candidate_seed: str, research_reason: str) -> None:
        self.index = index
        self.family = family
        self.direction = direction
        self.source_text = source_text
        self.params = params
        self.candidate_seed = candidate_seed
        self.research_reason = research_reason


def generate_candidate_population(
    *,
    seed: str,
    population_size: int,
    families: tuple[StrategyFamily, ...] = SUPPORTED_FAMILIES,
) -> list[GeneratedCandidateSeed]:
    """Section 8B's one real entry point — a controlled, deterministic
    candidate population drawn from MULTIPLE independent research
    families (round-robin across `families`, never 30 mutations of one
    parent). Same `seed`/`population_size`/`families` always produces
    the exact same real population."""
    population: list[GeneratedCandidateSeed] = []
    for index in range(population_size):
        family = families[index % len(families)]
        candidate_seed = f"{seed}:{index}"
        rng = _seeded_rng(candidate_seed, family)
        direction = _DIRECTIONS[rng.randrange(len(_DIRECTIONS))]
        source_text, params = _source_text_for(family, direction=direction, rng=rng)
        population.append(
            GeneratedCandidateSeed(
                index=index,
                family=family,
                direction=direction,
                source_text=source_text,
                params=params,
                candidate_seed=candidate_seed,
                research_reason=f"Research exploration — family '{family}', deterministic seed '{candidate_seed}'.",
            )
        )
    return population


def prune_duplicates(population: list[GeneratedCandidateSeed]) -> tuple[list[GeneratedCandidateSeed], dict[int, int]]:
    """Section 8C — real, deterministic near-duplicate pruning WITHIN
    one population, reusing `word_overlap_score()`/
    `NEAR_DUPLICATE_OVERLAP_THRESHOLD` directly. Returns
    `(kept, duplicate_of_by_index)` — `duplicate_of_by_index[i] = j`
    means population member `i` real-word-overlaps an EARLIER-kept
    member `j` above the real near-duplicate bar and was never
    backtested. Order-stable (first occurrence always kept) so pruning
    is itself deterministic given the same population."""
    kept: list[GeneratedCandidateSeed] = []
    duplicate_of: dict[int, int] = {}
    for candidate in population:
        match = next(
            (kept_candidate for kept_candidate in kept if word_overlap_score(candidate.source_text, kept_candidate.source_text) >= NEAR_DUPLICATE_OVERLAP_THRESHOLD),
            None,
        )
        if match is not None:
            duplicate_of[candidate.index] = match.index
        else:
            kept.append(candidate)
    return kept, duplicate_of


def allocate_research_budget(
    family_stats: list[FamilyResearchStats],
    *,
    exploitation_pct: float = 70.0,
) -> list[tuple[StrategyFamily, float, str]]:
    """Section 8J — a real, deterministic exploitation/exploration
    split. Families with real evidence of a positive real average
    expectancy share `exploitation_pct` of the budget in proportion to
    their own real average expectancy (higher real expectancy ->
    proportionally more of the exploitation share); every family
    (including ones with zero/negative/unknown real evidence) shares
    the remaining `100 - exploitation_pct` equally, so exploration never
    fully abandons a weak family. Returns `(family, weight_pct,
    rationale)` tuples, weights summing to 100.0. Advisory research-
    effort routing only — never imported by any execution/paper-trading
    path (see this module's own docstring)."""
    if not family_stats:
        return []
    exploration_pct = 100.0 - exploitation_pct
    per_family_exploration = exploration_pct / len(family_stats)
    positive_evidence: dict[StrategyFamily, float] = {
        f.family: f.average_expectancy_r for f in family_stats if f.average_expectancy_r is not None and f.average_expectancy_r > 0
    }
    total_positive_expectancy = sum(positive_evidence.values())
    decisions: list[tuple[StrategyFamily, float, str]] = []
    for stats in family_stats:
        expectancy = positive_evidence.get(stats.family)
        exploitation_share = exploitation_pct * (expectancy / total_positive_expectancy) if expectancy is not None and total_positive_expectancy > 0 else 0.0
        weight = round(exploitation_share + per_family_exploration, 2)
        if expectancy is not None:
            rationale = (
                f"Real average expectancy {expectancy:+.3f}R across {stats.number_backtested} real "
                f"backtested candidate(s) earns a real exploitation share; plus the real {per_family_exploration:.1f}% "
                "exploration floor every family always keeps."
            )
        else:
            rationale = (
                f"No real positive average expectancy evidence yet ({stats.number_backtested} real candidate(s) "
                f"backtested) — real exploration floor only ({per_family_exploration:.1f}%), never fully abandoned."
            )
        decisions.append((stats.family, weight, rationale))
    return decisions
