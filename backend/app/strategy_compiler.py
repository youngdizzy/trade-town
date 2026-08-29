"""app/strategy_compiler.py — CEO directive "Professional Quant Trading
Firm — Quant Intelligence + Market Analysis Completion Phase," Phase F:
English-language strategy -> reproducible strategy compiler.

RESEARCH FIRST. A full grep audit of this codebase found no strategy
DSL, parser, or compiler anywhere — `app/schemas.py`'s `Strategy` is an
identity record (id/name/description/stage), never a structured rule
set; `app/simulation.py`'s backtest math is explicitly-placeholder RNG,
with no rules to interpret in the first place. This module and
`app/strategy_engine.py` are the first real strategy-compilation and
generic-backtest-execution pipeline in this codebase.

WHAT THIS IS NOT: an LLM. This codebase has no live LLM call anywhere
in its runtime (every "agent" text this whole project generates is
templated/pre-authored — see app/debate.py, app/foundational_mentors.py,
etc.'s own module docstrings for that same discipline). A "compiler"
that silently guessed thresholds from free-form natural language would
be exactly the "hidden assumptions presented as an objective backtest"
anti-pattern this directive explicitly forbids. Instead this is a real,
deterministic, auditable PATTERN MATCHER over a disclosed, limited
vocabulary (`_TRIGGER_PATTERNS`, `_REQUIREMENT_PATTERN`, `_ENTRY_
PATTERNS`, `_STOP_PATTERNS`, `_TARGET_PATTERNS` below) — every
recognized phrase maps to one specific, disclosed, real structured
condition; every phrase this compiler does not recognize is either
flagged as a disclosed `StrategyAmbiguity` (if it matches a known
vague-quality-judgment term) or simply contributes no structured
content at all. Nothing is ever guessed.

THE KNOWN VOCABULARY (exactly what this compiler can express — see each
pattern's own comment for the exact phrasing it matches):
  - a TRIGGER: price closing above/below a named EMA/SMA (the sustained-
    side "breaks and closes above/below the N EMA" shape); OR (CEO
    directive "...Quant Intelligence + Market Analysis Completion Phase
    (Next Research + Validation Pass)") an RSI/Stochastic %K threshold
    ("RSI above 70," "the 14 Stochastic is below 20" — an explicit
    period is optional, defaulting to the methodology's own standard 14)
    or a real MACD line/signal-line crossover ("MACD crosses above the
    signal line," always the methodology's own standard 12/26/9
    defaults — this compiler's `StrategyIndicatorRef` has no room for a
    stated fast/slow/signal triple, a real, disclosed v1 simplification,
    not a silent guess). At most ONE trigger is ever recognized per
    strategy — the first pattern that matches (EMA/SMA, then RSI, then
    Stochastic, then MACD, in that priority order) wins; this compiler
    does not attempt to combine multiple trigger types into one
    sequence.

    A REAL, DISCLOSED DIRECTIONAL CONVENTION FOR RSI/STOCHASTIC, NOT A
    GUESS: "indicator above N" always compiles to a real LONG-biased
    trigger (operator="gt"), "below N" to SHORT -- the exact same
    mechanical "higher value = bullish, lower value = bearish" rule the
    engine's own threshold-trigger branch already applies (see
    app/strategy_engine.py's own module docstring), matching a
    MOMENTUM/breakout reading of the threshold ("RSI breaking above 70
    confirms strong momentum, buy the continuation"). This is
    DELIBERATELY NOT the mean-reversion reading ("RSI below 30 is
    oversold, buy the bounce") -- that reading needs a trigger direction
    OPPOSITE its own threshold side, which this compiler's v1 grammar
    cannot express (the entry step's own stated direction is compared
    against the trigger's for a real contradiction, exactly the same
    "trigger and entry directions must agree" check the EMA/SMA trigger
    already enforces -- a mean-reversion-phrased strategy like "buy when
    RSI is below 30, enter when price closes above the swing high" is
    correctly flagged status="ambiguous" for this real, disclosed
    reason, never silently miscompiled). Representing mean-reversion
    RSI/Stochastic strategies is real, tractable future work.
  - (CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    Engine") a Multi-Horizon Trend Score threshold ("the multi-horizon
    trend score is above 2," "...is below -2"), the same real "above =
    long, below = short" convention as RSI/Stochastic above, resolving
    to app/trend_engine.py's own default, versioned composite
    methodology (see that module's `TREND_ENGINE_METHODOLOGY_VERSION`).
    Lowest priority in the trigger match order — checked only after
    EMA/SMA, RSI, Stochastic, and MACD all fail to match.
  - a REQUIREMENT: "at least N bullish/bearish candles" (a real
    consecutive-candle-direction count, English number words 1-20
    supported).
  - an ENTRY: "closes above/below the previous swing high/low" (the
    same real "breakout of the pre-pullback leg extreme" shape
    app/ema_pullback_research.py's own hand-built engine already
    implements).
  - a STOP: "Chandelier Stop" (the same real, standard 22-period/3.0x
    default that module already uses, or an explicitly stated
    period/multiplier), a plain swing-level stop, or a fixed percent.
  - a TARGET: "target NR" / "N:1 reward" (an R-multiple), or a fixed
    percent.

ANYTHING OUTSIDE THIS VOCABULARY is a real, disclosed gap in this
compiler's coverage, not a claim that no other strategy shape exists.
Growing the vocabulary further (pattern-based conditions referencing
app/technical_patterns.py, multi-leg/multi-trigger sequences, a stated
MACD fast/slow/signal triple) is real, tractable future work —
deliberately not attempted in one pass, per this directive's own "do
not add every possible indicator just for quantity" instruction; see
this module's own `STATUS_COVERAGE_NOTE` for the exact, current
disclosed scope.

NO AMBIGUOUS STRATEGIES. `_AMBIGUOUS_PHRASE_PATTERNS` is a disclosed
list of vague-quality-judgment phrases ("strong breakout," "significant
volume," "near support," "clean pullback," and similar) the directive
itself names as forbidden to silently convert. Any match anywhere in
the source text produces a real `StrategyAmbiguity` and the definition
is marked `status="ambiguous"` — `app/strategy_engine.py` refuses to
backtest anything that isn't `status="compiled"`.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from app.schemas import (
    AgentId,
    CompiledStrategyDefinition,
    StrategyAmbiguity,
    StrategyCondition,
    StrategyIndicatorRef,
    StrategySequenceStep,
    StrategyStopSpec,
    StrategyTargetSpec,
)

STATUS_COVERAGE_NOTE = (
    "This compiler recognizes a disclosed, limited vocabulary: an EMA/SMA close-above/below trigger, an RSI/"
    "Stochastic threshold trigger, a MACD line/signal-line crossover trigger (at most one trigger per strategy), an "
    "at-least-N-consecutive-candles pullback requirement, a breakout-of-the-prior-swing-level entry, a "
    "Chandelier/swing-level/fixed-percent stop, and an R-multiple or fixed-percent target. Pattern-based conditions "
    "(FVG/candlestick/order-block), a stated MACD fast/slow/signal triple, and multi-leg/multi-trigger sequences "
    "are real, disclosed gaps in this compiler's current coverage, not evidence no such strategy shape exists."
)

_NUMBER_WORDS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20,
}

# Real, disclosed vague-quality-judgment phrases the directive itself
# names as forbidden to silently convert into an invented threshold.
_AMBIGUOUS_PHRASE_PATTERNS: tuple[str, ...] = (
    r"\bstrong\s+breakout\b",
    r"\bsignificant\s+volume\b",
    r"\bnear\s+support\b",
    r"\bnear\s+resistance\b",
    r"\bstrong\s+momentum\b",
    r"\bclean\s+pullback\b",
    r"\bclean\s+breakout\b",
    r"\bbig\s+candle\b",
    r"\blarge\s+candle\b",
    r"\blooks\s+strong\b",
    r"\blooks\s+like\b",
    r"\bgood\s+setup\b",
    r"\bdecent\s+volume\b",
    r"\bobvious\b",
    r"\bsolid\s+(?:trend|setup|move)\b",
)

# Real trigger phrasing: "closes above/below the N EMA/SMA".
_TRIGGER_PATTERN = re.compile(
    r"clos(?:e|es|ed)\s+(above|below)\s+the\s+(\d+)[\s-]*(?:period\s+)?(EMA|SMA)", re.IGNORECASE
)

# CEO directive "...Quant Intelligence + Market Analysis Completion
# Phase (Next Research + Validation Pass)" — RSI/MACD/Stochastic
# threshold/crossover triggers, closing the "RSI/MACD/Stochastic-based
# triggers... real future increment" gap this module's own
# `STATUS_COVERAGE_NOTE` previously disclosed. Real, standard threshold
# phrasing: "RSI above/below N" (optionally with an explicit period,
# e.g. "the 14 RSI is above 70"), the mirror for Stochastic, and a real
# MACD line/signal-line crossover.
_RSI_THRESHOLD_PATTERN = re.compile(r"(?:the\s+)?(\d+)?[\s-]*(?:period\s+)?RSI\s+(?:is\s+)?(above|below)\s+(\d+(?:\.\d+)?)", re.IGNORECASE)
_STOCHASTIC_THRESHOLD_PATTERN = re.compile(r"(?:the\s+)?(\d+)?[\s-]*(?:period\s+)?stochastic\s+(?:is\s+)?(above|below)\s+(\d+(?:\.\d+)?)", re.IGNORECASE)
_MACD_CROSS_PATTERN = re.compile(r"MACD(?:\s+line)?\s+crosses\s+(above|below)\s+(?:the\s+)?signal(?:\s+line)?", re.IGNORECASE)

# CEO directive "AHL-Inspired Systematic Trend & Momentum Research
# Engine" — the one new real phrasing this compiler recognizes for
# app/trend_engine.py's real, versioned composite indicator (see
# StrategyIndicatorName's own "multi_horizon_trend_score" docstring in
# app/schemas.py). Real, standard threshold phrasing mirroring RSI/
# Stochastic above: "the multi-horizon trend score is above/below N".
_TREND_SCORE_THRESHOLD_PATTERN = re.compile(r"(?:the\s+)?multi[\s-]horizon\s+trend\s+score\s+(?:is\s+)?(above|below)\s+(-?\d+(?:\.\d+)?)", re.IGNORECASE)

# CEO directive "AHL-Inspired Systematic Trend & Momentum Research
# Engine," Phase 8 — the one new real phrasing this compiler recognizes
# for app/liquidity_sweep_research.py's real event-pulse indicator (see
# StrategyIndicatorName's own "liquidity_sweep_signal" docstring in
# app/schemas.py). "A bullish/bearish liquidity sweep occurs" ->
# signal above/below 0 (the same +1/-1/0 event-pulse convention that
# module's own docstring discloses).
_LIQUIDITY_SWEEP_PATTERN = re.compile(r"a\s+(bullish|bearish)\s+liquidity\s+sweep\s+occurs", re.IGNORECASE)

# CEO directive "AHL-Inspired Systematic Trend & Momentum Research
# Engine," Phase 10 — the one new real phrasing this compiler
# recognizes for app/structure_break_research.py's real event-pulse
# indicator (see StrategyIndicatorName's own "structure_break_signal"
# docstring in app/schemas.py). "A bullish/bearish break of structure
# occurs" -> signal crosses above/below 0, same convention as the
# liquidity-sweep pattern above.
_STRUCTURE_BREAK_PATTERN = re.compile(r"a\s+(bullish|bearish)\s+break\s+of\s+structure\s+occurs", re.IGNORECASE)

# CEO directive "AHL-Inspired Systematic Trend & Momentum Research
# Engine," Phase 10 — the one new real phrasing this compiler
# recognizes for app/structure_break_research.py's real
# change_of_character_signal_series() indicator (see
# StrategyIndicatorName's own "choch_signal" docstring in
# app/schemas.py, and MarketStructureRead.change_of_character's own
# docstring for the exact, disclosed CHoCH definition used). "A
# bullish/bearish change of character occurs" -> signal crosses
# above/below 0, same convention as the structure-break pattern above.
_CHOCH_PATTERN = re.compile(r"a\s+(bullish|bearish)\s+change\s+of\s+character\s+occurs", re.IGNORECASE)

# CEO directive "AHL-Inspired Systematic Trend & Momentum Research
# Engine," Phase 10 — the one new real phrasing this compiler
# recognizes for app/fvg_research.py's real event-pulse indicator (see
# StrategyIndicatorName's own "fvg_signal" docstring in app/schemas.py).
# "A bullish/bearish fair value gap forms" -> signal crosses above/below
# 0, same convention as every other event-pulse pattern above.
_FVG_PATTERN = re.compile(r"a\s+(bullish|bearish)\s+fair\s+value\s+gap\s+forms", re.IGNORECASE)

# CEO directive "AHL-Inspired Systematic Trend & Momentum Research
# Engine," Phase 10 — the one new real phrasing this compiler
# recognizes for app/fibonacci_research.py's real price-valued
# indicator (see StrategyIndicatorName's own "fibonacci_618_level"
# docstring in app/schemas.py, and that module's own docstring for why
# only the 61.8% ratio is wired). "Price closes above/below the 61.8%
# Fibonacci retracement level" -> real price_close crosses_above/below
# the real fibonacci_618_level series, reusing the exact same two-
# indicator crossing mechanism the MACD line/signal-line pattern above
# already established, never a new comparison primitive.
_FIBONACCI_618_PATTERN = re.compile(r"price\s+closes\s+(above|below)\s+the\s+(?:61\.8%?|0\.618)\s+Fibonacci\s+(?:retracement\s+)?level", re.IGNORECASE)

# CEO directive "AHL-Inspired Systematic Trend & Momentum Research
# Engine," Phase 9 — the sweep+FVG combo hypothesis (no real
# "displacement" detector exists anywhere in this codebase to include
# as a third leg — see app/strategy_engine.py's own
# `_combo_direction_at()` docstring for the same disclosure). "A
# bullish/bearish liquidity sweep AND a [same] bullish/bearish fair
# value gap both occur" -> a real StrategySequenceStep.all_of list of
# TWO conditions (see that field's own docstring in app/schemas.py) —
# the one new real phrasing recognizing app/strategy_engine.py's own
# real AND-combination support, never a claim every possible N-way
# combination is recognized. The `\1` backreference requires BOTH
# halves to state the SAME real direction — "a bullish sweep and a
# bearish FVG" is a real, self-contradictory request this pattern
# deliberately does not match (falls through to "no recognizable
# trigger" rather than silently picking one side).
_SWEEP_FVG_COMBO_PATTERN = re.compile(
    r"a\s+(bullish|bearish)\s+liquidity\s+sweep\s+and\s+a\s+\1\s+fair\s+value\s+gap\s+both\s+occur", re.IGNORECASE
)

# Real requirement phrasing: "at least N bullish/bearish candles".
_REQUIREMENT_PATTERN = re.compile(
    r"at\s+least\s+(\w+)\s+(bullish|bearish)\s+(?:opposite\s+)?candles?", re.IGNORECASE
)

# Real entry phrasing: "closes above/below the previous swing high/low".
_ENTRY_PATTERN = re.compile(
    r"clos(?:e|es|ed)\s+(above|below)\s+the\s+(?:previous\s+|pre-pullback\s+)?swing\s+(high|low)", re.IGNORECASE
)

# Real stop phrasing.
_CHANDELIER_STOP_PATTERN = re.compile(r"chandelier\s+stop", re.IGNORECASE)
_CHANDELIER_PARAMS_PATTERN = re.compile(r"(\d+)[\s-]*(?:period\s+)?ATR.{0,20}?(\d+(?:\.\d+)?)\s*[xX]", re.IGNORECASE)
_SWING_STOP_PATTERN = re.compile(r"stop\s+at\s+the\s+swing\s+(?:high|low)", re.IGNORECASE)
_PERCENT_STOP_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*%\s+stop", re.IGNORECASE)

# Real target phrasing: "target NR" or "N:1 reward" or "N% target".
_R_MULTIPLE_TARGET_PATTERN = re.compile(r"target\s+(\d+(?:\.\d+)?)\s*R\b", re.IGNORECASE)
_RATIO_TARGET_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?::|to)\s*1\s+(?:reward|reward-to-risk|risk[\s-]reward)", re.IGNORECASE)
_PERCENT_TARGET_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*%\s+target", re.IGNORECASE)

_DEFAULT_CHANDELIER_ATR_PERIOD = 22
_DEFAULT_CHANDELIER_ATR_MULTIPLIER = 3.0


def _number_from_word(word: str) -> int | None:
    lowered = word.lower()
    if lowered in _NUMBER_WORDS:
        return _NUMBER_WORDS[lowered]
    if lowered.isdigit():
        return int(lowered)
    return None


def _find_ambiguities(text: str) -> list[StrategyAmbiguity]:
    ambiguities: list[StrategyAmbiguity] = []
    for pattern in _AMBIGUOUS_PHRASE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            phrase = match.group(0)
            context_start = max(0, match.start() - 30)
            context_end = min(len(text), match.end() + 30)
            ambiguities.append(
                StrategyAmbiguity(
                    phrase=phrase,
                    context=text[context_start:context_end].strip(),
                    reason="This is a vague quality judgment with no single, universally agreed numeric definition — converting it to a threshold would be an invented assumption, not a real translation of the source text.",
                    suggestedResolution=f"Replace '{phrase}' with an explicit, measurable definition (e.g. a specific ATR multiple, a specific volume ratio, a specific price distance).",
                )
            )
    return ambiguities


def strategy_definition_slug(name: str) -> str:
    """The same real, deterministic slug `compile_strategy_text()`
    computes internally for `CompiledStrategyDefinition.id` — exposed
    separately so a caller (app/strategy_registry.py's
    `register_strategy_version()`) can look up a strategy's own
    persisted version history by this same real key BEFORE compiling a
    new version, without duplicating this regex."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "strategy"


def compile_strategy_text(
    *,
    name: str,
    source_text: str,
    timeframe: str = "1h",
    created_by: AgentId = "quant",
    previous_version: int | None = None,
) -> CompiledStrategyDefinition:
    """The one real, deterministic entry point. Same `source_text` in ->
    same `CompiledStrategyDefinition` out, every time — no randomness,
    no external call, no hidden state."""
    now_iso = datetime.now(timezone.utc).isoformat()
    definition_id = strategy_definition_slug(name)
    version = (previous_version + 1) if previous_version is not None else 1

    ambiguities = _find_ambiguities(source_text)
    sequence: list[StrategySequenceStep] = []
    step_counter = 0

    def _next_step_id() -> str:
        nonlocal step_counter
        step_counter += 1
        return f"{definition_id}-step-{step_counter}"

    direction: str | None = None  # "long" | "short"

    trigger_match = _TRIGGER_PATTERN.search(source_text)
    rsi_match = _RSI_THRESHOLD_PATTERN.search(source_text) if not trigger_match else None
    stochastic_match = _STOCHASTIC_THRESHOLD_PATTERN.search(source_text) if not trigger_match and not rsi_match else None
    macd_match = _MACD_CROSS_PATTERN.search(source_text) if not trigger_match and not rsi_match and not stochastic_match else None
    trend_score_match = (
        _TREND_SCORE_THRESHOLD_PATTERN.search(source_text) if not trigger_match and not rsi_match and not stochastic_match and not macd_match else None
    )
    # Checked BEFORE the individual sweep/FVG patterns below — "a
    # bullish liquidity sweep and a bullish fair value gap both occur"
    # would otherwise have its own leading "a bullish liquidity sweep"
    # clause greedily matched by _LIQUIDITY_SWEEP_PATTERN first, never
    # giving the combo pattern a chance.
    combo_match = (
        _SWEEP_FVG_COMBO_PATTERN.search(source_text)
        if not trigger_match and not rsi_match and not stochastic_match and not macd_match and not trend_score_match
        else None
    )
    sweep_match = (
        _LIQUIDITY_SWEEP_PATTERN.search(source_text)
        if not trigger_match and not rsi_match and not stochastic_match and not macd_match and not trend_score_match and not combo_match
        else None
    )
    structure_match = (
        _STRUCTURE_BREAK_PATTERN.search(source_text)
        if not trigger_match
        and not rsi_match
        and not stochastic_match
        and not macd_match
        and not trend_score_match
        and not combo_match
        and not sweep_match
        else None
    )
    choch_match = (
        _CHOCH_PATTERN.search(source_text)
        if not trigger_match
        and not rsi_match
        and not stochastic_match
        and not macd_match
        and not trend_score_match
        and not combo_match
        and not sweep_match
        and not structure_match
        else None
    )
    fvg_match = (
        _FVG_PATTERN.search(source_text)
        if not trigger_match
        and not rsi_match
        and not stochastic_match
        and not macd_match
        and not trend_score_match
        and not combo_match
        and not sweep_match
        and not structure_match
        and not choch_match
        else None
    )
    fibonacci_match = (
        _FIBONACCI_618_PATTERN.search(source_text)
        if not trigger_match
        and not rsi_match
        and not stochastic_match
        and not macd_match
        and not trend_score_match
        and not combo_match
        and not sweep_match
        and not structure_match
        and not choch_match
        and not fvg_match
        else None
    )

    if trigger_match:
        side, period_str, ma_kind = trigger_match.groups()
        direction = "long" if side.lower() == "above" else "short"
        indicator_name = "ema" if ma_kind.lower() == "ema" else "sma"
        indicator_ref = StrategyIndicatorRef(indicator=indicator_name, period=int(period_str))  # type: ignore[arg-type]
        condition = StrategyCondition(
            id=f"{definition_id}-trigger-condition",
            left=StrategyIndicatorRef(indicator="price_close"),
            operator="crosses_above" if direction == "long" else "crosses_below",
            rightIndicator=indicator_ref,
            detail=f"Real close crosses {'above' if direction == 'long' else 'below'} the {period_str}-period {indicator_name.upper()}, with a real close-confirmed bar (never a same-bar wick).",
        )
        sequence.append(
            StrategySequenceStep(
                id=_next_step_id(),
                stepType="trigger",
                condition=condition,
                detail=f"Trigger: real EMA/SMA cross-{'up' if direction == 'long' else 'down'} with close confirmation.",
            )
        )
    elif rsi_match:
        period_str, side, threshold_str = rsi_match.groups()
        period = int(period_str) if period_str else 14
        direction = "long" if side.lower() == "above" else "short"
        operator = "gt" if direction == "long" else "lt"
        condition = StrategyCondition(
            id=f"{definition_id}-trigger-condition",
            left=StrategyIndicatorRef(indicator="rsi", period=period),
            operator=operator,  # type: ignore[arg-type]
            rightValue=float(threshold_str),
            detail=f"Real RSI({period}) {side.lower()} {threshold_str}, with a real sustained-side confirmation window before triggering (the engine's own standard requirement — never a bare single-bar spike).",
        )
        sequence.append(
            StrategySequenceStep(
                id=_next_step_id(),
                stepType="trigger",
                condition=condition,
                detail=f"Trigger: real RSI({period}) {side.lower()} {threshold_str}.",
            )
        )
    elif stochastic_match:
        period_str, side, threshold_str = stochastic_match.groups()
        period = int(period_str) if period_str else 14
        direction = "long" if side.lower() == "above" else "short"
        operator = "gt" if direction == "long" else "lt"
        condition = StrategyCondition(
            id=f"{definition_id}-trigger-condition",
            left=StrategyIndicatorRef(indicator="stochastic_percent_k", period=period),
            operator=operator,  # type: ignore[arg-type]
            rightValue=float(threshold_str),
            detail=f"Real Stochastic %K({period}) {side.lower()} {threshold_str}, with a real sustained-side confirmation window before triggering (the engine's own standard requirement).",
        )
        sequence.append(
            StrategySequenceStep(
                id=_next_step_id(),
                stepType="trigger",
                condition=condition,
                detail=f"Trigger: real Stochastic %K({period}) {side.lower()} {threshold_str}.",
            )
        )
    elif macd_match:
        (side,) = macd_match.groups()
        direction = "long" if side.lower() == "above" else "short"
        condition = StrategyCondition(
            id=f"{definition_id}-trigger-condition",
            left=StrategyIndicatorRef(indicator="macd_line"),
            operator="crosses_above" if direction == "long" else "crosses_below",
            rightIndicator=StrategyIndicatorRef(indicator="macd_signal"),
            detail=f"Real MACD line crosses {side.lower()} its own real signal line (the methodology's own standard 12/26/9 defaults).",
        )
        sequence.append(
            StrategySequenceStep(
                id=_next_step_id(),
                stepType="trigger",
                condition=condition,
                detail=f"Trigger: real MACD line/signal-line cross-{'up' if direction == 'long' else 'down'}.",
            )
        )
    elif trend_score_match:
        side, threshold_str = trend_score_match.groups()
        direction = "long" if side.lower() == "above" else "short"
        operator = "gt" if direction == "long" else "lt"
        condition = StrategyCondition(
            id=f"{definition_id}-trigger-condition",
            left=StrategyIndicatorRef(indicator="multi_horizon_trend_score"),
            operator=operator,  # type: ignore[arg-type]
            rightValue=float(threshold_str),
            detail=f"Real Multi-Horizon Trend Score (app/trend_engine.py's own default, versioned methodology) {side.lower()} {threshold_str}.",
        )
        sequence.append(
            StrategySequenceStep(
                id=_next_step_id(),
                stepType="trigger",
                condition=condition,
                detail=f"Trigger: real Multi-Horizon Trend Score {side.lower()} {threshold_str}.",
            )
        )
    elif combo_match:
        (side,) = combo_match.groups()
        direction = "long" if side.lower() == "bullish" else "short"
        operator = "crosses_above" if direction == "long" else "crosses_below"
        sweep_condition = StrategyCondition(
            id=f"{definition_id}-trigger-condition-sweep",
            left=StrategyIndicatorRef(indicator="liquidity_sweep_signal"),
            operator=operator,  # type: ignore[arg-type]
            rightValue=0.0,
            detail=f"Real {side.lower()} liquidity sweep (app/liquidity_sweep_research.py) — combo leg 1 of 2.",
        )
        fvg_condition = StrategyCondition(
            id=f"{definition_id}-trigger-condition-fvg",
            left=StrategyIndicatorRef(indicator="fvg_signal"),
            operator=operator,  # type: ignore[arg-type]
            rightValue=0.0,
            detail=f"Real {side.lower()} Fair Value Gap (app/fvg_research.py) — combo leg 2 of 2.",
        )
        sequence.append(
            StrategySequenceStep(
                id=_next_step_id(),
                stepType="trigger",
                allOf=[sweep_condition, fvg_condition],
                detail=(
                    f"Trigger: real {side.lower()} liquidity sweep AND real {side.lower()} Fair Value Gap both confirmed on the SAME bar "
                    "(a real, strict same-bar simultaneity requirement — see app/strategy_engine.py's own _combo_direction_at() docstring). "
                    'No real "displacement" leg is included — no such detector exists anywhere in this codebase.'
                ),
            )
        )
    elif sweep_match:
        (side,) = sweep_match.groups()
        direction = "long" if side.lower() == "bullish" else "short"
        # crosses_above/crosses_below (never a bare gt/lt) — the real
        # liquidity_sweep_signal can stay at its nonzero value for
        # several consecutive bars while the sweep candle remains inside
        # compute_liquidity()'s own bounded "recent" detection window
        # (see app/liquidity_sweep_research.py's own module docstring);
        # a bare threshold would re-trigger on every one of those bars.
        # The one-shot crossing captures only the real bar the signal
        # first turns on.
        operator = "crosses_above" if direction == "long" else "crosses_below"
        condition = StrategyCondition(
            id=f"{definition_id}-trigger-condition",
            left=StrategyIndicatorRef(indicator="liquidity_sweep_signal"),
            operator=operator,  # type: ignore[arg-type]
            rightValue=0.0,
            detail=f"Real {side.lower()} liquidity sweep (app/market_intelligence.py's own equal-high/low sweep detector, wrapped by app/liquidity_sweep_research.py) just occurred.",
        )
        sequence.append(
            StrategySequenceStep(
                id=_next_step_id(),
                stepType="trigger",
                condition=condition,
                detail=f"Trigger: real {side.lower()} liquidity sweep detected.",
            )
        )
    elif structure_match:
        (side,) = structure_match.groups()
        direction = "long" if side.lower() == "bullish" else "short"
        # crosses_above/crosses_below — same real reason as the
        # liquidity-sweep pattern above: a real BOS state can persist
        # unchanged across many bars.
        operator = "crosses_above" if direction == "long" else "crosses_below"
        condition = StrategyCondition(
            id=f"{definition_id}-trigger-condition",
            left=StrategyIndicatorRef(indicator="structure_break_signal"),
            operator=operator,  # type: ignore[arg-type]
            rightValue=0.0,
            detail=f"Real {side.lower()} Break of Structure (app/market_intelligence.py's own swing-structure detector, wrapped by app/structure_break_research.py) just occurred.",
        )
        sequence.append(
            StrategySequenceStep(
                id=_next_step_id(),
                stepType="trigger",
                condition=condition,
                detail=f"Trigger: real {side.lower()} Break of Structure detected.",
            )
        )
    elif choch_match:
        (side,) = choch_match.groups()
        direction = "long" if side.lower() == "bullish" else "short"
        # crosses_above/crosses_below — same real reason as the
        # structure-break pattern above: a real CHoCH state can persist
        # unchanged across many bars.
        operator = "crosses_above" if direction == "long" else "crosses_below"
        condition = StrategyCondition(
            id=f"{definition_id}-trigger-condition",
            left=StrategyIndicatorRef(indicator="choch_signal"),
            operator=operator,  # type: ignore[arg-type]
            rightValue=0.0,
            detail=f"Real {side.lower()} Change of Character (app/market_intelligence.py's own swing-structure detector, wrapped by app/structure_break_research.py) just occurred.",
        )
        sequence.append(
            StrategySequenceStep(
                id=_next_step_id(),
                stepType="trigger",
                condition=condition,
                detail=f"Trigger: real {side.lower()} Change of Character detected.",
            )
        )
    elif fvg_match:
        (side,) = fvg_match.groups()
        direction = "long" if side.lower() == "bullish" else "short"
        # crosses_above/crosses_below — same real reason as every other
        # event-pulse pattern above: a real FVG can stay visible across
        # several consecutive bars while it remains inside the trailing
        # scan window.
        operator = "crosses_above" if direction == "long" else "crosses_below"
        condition = StrategyCondition(
            id=f"{definition_id}-trigger-condition",
            left=StrategyIndicatorRef(indicator="fvg_signal"),
            operator=operator,  # type: ignore[arg-type]
            rightValue=0.0,
            detail=f"Real {side.lower()} Fair Value Gap (app/technical_patterns.py's own standard 3-candle detector, wrapped by app/fvg_research.py) just formed.",
        )
        sequence.append(
            StrategySequenceStep(
                id=_next_step_id(),
                stepType="trigger",
                condition=condition,
                detail=f"Trigger: real {side.lower()} Fair Value Gap detected.",
            )
        )
    elif fibonacci_match:
        (side,) = fibonacci_match.groups()
        direction = "long" if side.lower() == "above" else "short"
        condition = StrategyCondition(
            id=f"{definition_id}-trigger-condition",
            left=StrategyIndicatorRef(indicator="price_close"),
            operator="crosses_above" if direction == "long" else "crosses_below",
            rightIndicator=StrategyIndicatorRef(indicator="fibonacci_618_level"),
            detail=f"Real price closes {side.lower()} its own real 61.8% Fibonacci retracement level (app/technical_patterns.py's own real swing-based calculation, wrapped by app/fibonacci_research.py).",
        )
        sequence.append(
            StrategySequenceStep(
                id=_next_step_id(),
                stepType="trigger",
                condition=condition,
                detail=f"Trigger: real price close crosses {side.lower()} the 61.8% Fibonacci retracement level.",
            )
        )

    requirement_match = _REQUIREMENT_PATTERN.search(source_text)
    if requirement_match:
        count_word, candle_direction_word = requirement_match.groups()
        min_bars = _number_from_word(count_word)
        if min_bars is not None:
            sequence.append(
                StrategySequenceStep(
                    id=_next_step_id(),
                    stepType="requirement",
                    minConsecutiveBars=min_bars,
                    candleDirection=candle_direction_word.lower(),  # type: ignore[arg-type]
                    detail=f"Requirement: at least {min_bars} real strictly-consecutive {candle_direction_word.lower()} candle(s) (a single candle short of this does not count).",
                )
            )
        else:
            ambiguities.append(
                StrategyAmbiguity(
                    phrase=requirement_match.group(0),
                    context=requirement_match.group(0),
                    reason="The consecutive-candle count could not be resolved to a real integer.",
                    suggestedResolution="State the count as a number or a supported English number word (one-twenty).",
                )
            )

    entry_match = _ENTRY_PATTERN.search(source_text)
    if entry_match:
        side, level = entry_match.groups()
        entry_direction = "long" if side.lower() == "above" else "short"
        if direction is not None and entry_direction != direction:
            ambiguities.append(
                StrategyAmbiguity(
                    phrase=entry_match.group(0),
                    context=entry_match.group(0),
                    reason=f"The entry direction (close {side.lower()} the swing {level.lower()}) contradicts the trigger direction found earlier in the text (a {direction} setup).",
                    suggestedResolution="Make the trigger and entry directions agree, or state them as two separate strategies.",
                )
            )
        else:
            direction = entry_direction
            sequence.append(
                StrategySequenceStep(
                    id=_next_step_id(),
                    stepType="entry",
                    detail=f"Entry: real candle body closes {side.lower()} the swing {level.lower()} established since the trigger (the pre-pullback leg extreme) — never a bare wick touch.",
                )
            )

    stop: StrategyStopSpec | None = None
    if _CHANDELIER_STOP_PATTERN.search(source_text):
        params_match = _CHANDELIER_PARAMS_PATTERN.search(source_text)
        if params_match:
            atr_period, atr_multiplier = int(params_match.group(1)), float(params_match.group(2))
        else:
            atr_period, atr_multiplier = _DEFAULT_CHANDELIER_ATR_PERIOD, _DEFAULT_CHANDELIER_ATR_MULTIPLIER
        stop = StrategyStopSpec(method="chandelier", atrPeriod=atr_period, atrMultiplier=atr_multiplier)
    elif _SWING_STOP_PATTERN.search(source_text):
        stop = StrategyStopSpec(method="swing_level")
    else:
        percent_match = _PERCENT_STOP_PATTERN.search(source_text)
        if percent_match:
            stop = StrategyStopSpec(method="fixed_percent", percent=float(percent_match.group(1)))

    target: StrategyTargetSpec | None = None
    r_multiple_match = _R_MULTIPLE_TARGET_PATTERN.search(source_text)
    ratio_match = _RATIO_TARGET_PATTERN.search(source_text)
    percent_target_match = _PERCENT_TARGET_PATTERN.search(source_text)
    if r_multiple_match:
        target = StrategyTargetSpec(method="r_multiple", value=float(r_multiple_match.group(1)))
    elif ratio_match:
        target = StrategyTargetSpec(method="r_multiple", value=float(ratio_match.group(1)))
    elif percent_target_match:
        target = StrategyTargetSpec(method="fixed_percent", value=float(percent_target_match.group(1)))

    has_trigger = any(s.step_type == "trigger" for s in sequence)
    has_entry = any(s.step_type == "entry" for s in sequence)

    if ambiguities:
        status: str = "ambiguous"
        detail = f"{len(ambiguities)} real ambiguous phrase(s) found — see ambiguities. Not backtestable until resolved."
    elif not has_trigger or not has_entry or stop is None or target is None:
        status = "invalid"
        missing = []
        if not has_trigger:
            missing.append("a recognizable trigger")
        if not has_entry:
            missing.append("a recognizable entry")
        if stop is None:
            missing.append("a recognizable stop")
        if target is None:
            missing.append("a recognizable target")
        detail = f"Missing {', '.join(missing)} — this compiler's known vocabulary did not match enough of the source text to produce a complete, backtestable definition. {STATUS_COVERAGE_NOTE}"
    else:
        status = "compiled"
        detail = f"Real {direction or 'directional'} sequence compiled from {len(sequence)} real step(s), a {stop.method} stop, and a {target.method} target."

    if not sequence and stop is None and target is None:
        sequence = []

    return CompiledStrategyDefinition(
        id=definition_id,
        name=name,
        sourceText=source_text,
        version=version,
        createdBy=created_by,
        createdAt=now_iso,
        timeframe=timeframe,
        sequence=sequence,
        stop=stop,
        target=target,
        ambiguities=ambiguities,
        status=status,  # type: ignore[arg-type]
        detail=detail,
    )
