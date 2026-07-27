"""Signal Calibration (v0.6.2 Phase 7) — a five-level practice mini-game
that grades the player's ENTER/WAIT/AVOID read of a real symbol against a
fixed, transparent rubric computed from real signals available *at
challenge time*: the sampled candles' own trend and volatility, any
currently-active real RiskWarning on that symbol, and that symbol's real
in-progress ResearchItem confidence (if any).

Deliberately never graded against what price did next. Grading on future
price would reward lucky guessing on a random walk; grading on a fixed
function of already-visible signals rewards the disciplined habit of
actually reading them, which is what the v0.6.2 brief asks for ("reward
disciplined decisions based on information available at the time, not
lucky guessing").

Challenges are transient, regenerable practice content — never part of
GameSaveState (see v0.6.2's save-payload-size fix for why). They're held
in `_pending` (an in-process dict, cleared on submit or backend restart)
between GET .../challenge and POST .../submit; only the graded
SignalCalibrationAttempt is persisted.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from app.agent_energy import award as award_energy
from app.market_data import MarketDataProvider
from app.market_data import trend_pct as _trend_pct
from app.market_data import volatility_pct as _volatility_pct
from app.schemas import (
    AgentEnergy,
    Candle,
    ResearchItem,
    RiskWarning,
    SignalCalibrationAttempt,
    SignalCalibrationState,
    SignalChallenge,
    SignalChoice,
    WatchlistEntry,
)

MIN_LEVEL = 1
MAX_LEVEL = 5
CHALLENGE_TIMEFRAME = "1h"
CHALLENGE_CANDLE_COUNT = 30

# How much Agent Energy a correct answer pays out, scaled with how much
# harder the level's rubric is to read correctly.
LEVEL_ENERGY_REWARD: dict[int, float] = {1: 5.0, 2: 8.0, 3: 12.0, 4: 16.0, 5: 20.0}

# Consecutive correct answers at the current unlocked level needed to
# advance — a streak, not a cumulative count, so grinding easy wrong
# answers in between can't slip the level up.
UNLOCK_STREAK = 3

MAX_ATTEMPTS = 100

# Transient in-process store: challenge id -> (challenge, correct_choice,
# rubric_notes). Not persisted — see module docstring.
_pending: dict[str, tuple[SignalChallenge, SignalChoice, str]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _active_warning(symbol: str, risk_warnings: list[RiskWarning]) -> RiskWarning | None:
    return next((w for w in risk_warnings if w.symbol == symbol), None)


def _research_confidence(symbol: str, research: list[ResearchItem]) -> float | None:
    item = next((r for r in research if r.symbol == symbol and r.status != "completed"), None)
    return item.confidence if item else None


def _disciplined_choice(
    level: int,
    trend_pct: float,
    volatility_pct: float,
    warning: RiskWarning | None,
    research_confidence: float | None,
) -> tuple[SignalChoice, str]:
    """The fixed rubric each level grades against. Returns (choice, plain-
    English explanation shown to the player after grading)."""
    if level == 1:
        # Level 1: trend alone.
        if trend_pct > 1.5:
            return "enter", f"Trend was +{trend_pct:.1f}% over the sample — a clear uptrend, worth entering."
        if trend_pct < -1.5:
            return "avoid", f"Trend was {trend_pct:.1f}% over the sample — a clear downtrend, best avoided."
        return "wait", f"Trend was only {trend_pct:+.1f}% over the sample — too flat to act on either way."

    if level == 2:
        # Level 2: weigh the move against its own volatility (risk/reward).
        ratio = abs(trend_pct) / max(volatility_pct, 0.1)
        if ratio >= 1.2 and trend_pct > 0:
            return "enter", f"Reward/risk ratio was {ratio:.1f} on a positive {trend_pct:+.1f}% move — the move was large relative to its own volatility."
        if ratio < 0.6 or (trend_pct < 0 and volatility_pct > 1.5):
            return "avoid", f"Reward/risk ratio was only {ratio:.1f} (volatility {volatility_pct:.1f}%) — too noisy or against you to justify entering."
        return "wait", f"Reward/risk ratio was {ratio:.1f} — not decisive enough either way."

    if level == 3:
        # Level 3: trend/regime — only trending markets are actionable;
        # ranging markets are correctly a WAIT regardless of direction.
        trending = abs(trend_pct) > 2 * max(volatility_pct, 0.1)
        if not trending:
            return "wait", f"Move ({trend_pct:+.1f}%) was small relative to volatility ({volatility_pct:.1f}%) — a ranging market, not a trend worth trading."
        if trend_pct > 0:
            return "enter", f"A real trending regime (+{trend_pct:.1f}% vs {volatility_pct:.1f}% volatility) — worth riding."
        return "avoid", f"A real trending regime ({trend_pct:.1f}% vs {volatility_pct:.1f}% volatility) — trending against you, avoid."

    if level == 4:
        # Level 4: conflicting evidence — an active risk warning overrides
        # an otherwise-positive trend read into caution.
        base_choice, base_note = _disciplined_choice(3, trend_pct, volatility_pct, None, None)
        if warning is not None and warning.severity in ("warning", "critical") and base_choice == "enter":
            return "wait", f"Trend alone said ENTER ({base_note}) — but there's an active {warning.severity.upper()} risk warning on this symbol ({warning.message}). Disciplined play is to wait it out."
        return base_choice, base_note

    # Level 5: full analysis — trend, volatility, an active warning, and
    # real research confidence combined into one weighted score.
    score = trend_pct - 0.5 * volatility_pct
    if warning is not None:
        score -= 10 if warning.severity == "critical" else 5 if warning.severity == "warning" else 0
    if research_confidence is not None:
        score += (research_confidence - 50) * 0.2
    notes = (
        f"Weighted score {score:+.1f} = trend {trend_pct:+.1f}% - 0.5x volatility {volatility_pct:.1f}%"
        f"{' - risk warning penalty' if warning is not None else ''}"
        f"{f' + research confidence {research_confidence:.0f}% factor' if research_confidence is not None else ''}."
    )
    if score > 3:
        return "enter", notes
    if score < -3:
        return "avoid", notes
    return "wait", notes


def _factors(level: int, trend_pct: float, volatility_pct: float, warning: RiskWarning | None, research_confidence: float | None) -> list[str]:
    """What's actually shown to the player before they answer — strictly
    a subset of what the rubric uses, gated by level, and always plainly
    labeled as real (never an invented feed)."""
    factors = [f"Recent trend: {trend_pct:+.1f}% over the last {CHALLENGE_CANDLE_COUNT} {CHALLENGE_TIMEFRAME} bars."]
    if level >= 2:
        factors.append(f"Volatility: {volatility_pct:.1f}% average bar range.")
    if level >= 3:
        regime = "trending" if abs(trend_pct) > 2 * max(volatility_pct, 0.1) else "ranging"
        factors.append(f"Regime read: market looks {regime} over this sample.")
    if level >= 4:
        if warning is not None:
            factors.append(f"Active risk warning: {warning.severity.upper()} — {warning.message}")
        else:
            factors.append("No active risk warning on this symbol right now.")
    if level >= 5:
        if research_confidence is not None:
            factors.append(f"Research confidence on this symbol: {research_confidence:.0f}%.")
        else:
            factors.append("No in-progress research on this symbol right now.")
    return factors


def _prompt(level: int, symbol: str) -> str:
    prompts = {
        1: f"Looking only at the recent trend, would you ENTER, WAIT, or AVOID {symbol}?",
        2: f"Weighing the move against its own volatility, would you ENTER, WAIT, or AVOID {symbol}?",
        3: f"Is {symbol} in a real trend or just ranging? ENTER, WAIT, or AVOID?",
        4: f"There may be conflicting evidence on {symbol}. Weigh it all — ENTER, WAIT, or AVOID?",
        5: f"Full analysis: trend, volatility, risk, and research on {symbol}. ENTER, WAIT, or AVOID?",
    }
    return prompts.get(level, prompts[1])


def generate_challenge(
    level: int,
    provider: MarketDataProvider,
    watchlist: list[WatchlistEntry],
    risk_warnings: list[RiskWarning],
    research: list[ResearchItem],
) -> SignalChallenge:
    if not watchlist:
        raise ValueError("No watchlist symbols available to build a challenge from.")
    level = max(MIN_LEVEL, min(MAX_LEVEL, level))

    # Level 4+ is most meaningful when a real conflict/signal actually
    # exists — prefer a symbol that has one, but never fabricate one if
    # none do; every symbol is still a legitimate (if simpler) round.
    candidates = watchlist
    if level >= 4:
        with_warning = [w for w in watchlist if _active_warning(w.symbol, risk_warnings) is not None]
        if with_warning:
            candidates = with_warning
    entry = random.choice(candidates)
    symbol = entry.symbol

    provider_candles = provider.get_candles(symbol, CHALLENGE_TIMEFRAME, CHALLENGE_CANDLE_COUNT)
    trend_pct = _trend_pct(provider_candles)
    volatility_pct = _volatility_pct(provider_candles)
    warning = _active_warning(symbol, risk_warnings)
    research_confidence = _research_confidence(symbol, research)

    correct_choice, rubric_notes = _disciplined_choice(level, trend_pct, volatility_pct, warning, research_confidence)
    factors = _factors(level, trend_pct, volatility_pct, warning, research_confidence)

    challenge_id = f"calibration-{level}-{symbol}-{_now_iso()}"
    challenge = SignalChallenge(
        id=challenge_id,
        level=level,
        symbol=symbol,
        timeframe=CHALLENGE_TIMEFRAME,
        candles=[Candle.model_validate(c.__dict__) for c in provider_candles],
        prompt=_prompt(level, symbol),
        factors=factors,
        createdAt=_now_iso(),
    )
    _pending[challenge_id] = (challenge, correct_choice, rubric_notes)
    return challenge


def _recent_streak_correct(attempts: list[SignalCalibrationAttempt], level: int) -> int:
    """How many of the most recent attempts *at this level* were correct,
    counting back from the newest until the first miss (or a different
    level, which just means "not yet re-attempted at this level")."""
    streak = 0
    for attempt in reversed(attempts):
        if attempt.level != level:
            continue
        if not attempt.correct:
            break
        streak += 1
    return streak


def grade_submission(
    state: SignalCalibrationState, energy: AgentEnergy, challenge_id: str, choice: SignalChoice
) -> tuple[SignalCalibrationState, AgentEnergy, str | None]:
    """Grades a pending challenge, records the attempt, and awards energy
    on a correct answer. `energy` is the caller's AgentEnergy; returned as
    the (possibly-awarded) second element. Returns (state, energy, error)
    — error is set (and nothing else changes) if the challenge id is
    unknown or already consumed, e.g. a stale tab or a backend restart."""
    pending = _pending.pop(challenge_id, None)
    if pending is None:
        return state, energy, "That challenge has expired or was already answered — request a new one."

    challenge, correct_choice, rubric_notes = pending
    correct = choice == correct_choice
    energy_awarded = LEVEL_ENERGY_REWARD[challenge.level] if correct else 0.0
    new_energy = award_energy(energy, energy_awarded) if energy_awarded else energy

    attempt = SignalCalibrationAttempt(
        id=f"{challenge_id}-attempt",
        level=challenge.level,
        symbol=challenge.symbol,
        choice=choice,
        correctChoice=correct_choice,
        correct=correct,
        energyAwarded=energy_awarded,
        rubricNotes=rubric_notes,
        createdAt=_now_iso(),
    )
    attempts = [*state.attempts, attempt][-MAX_ATTEMPTS:]

    unlocked_level = state.unlocked_level
    if correct and challenge.level == unlocked_level and unlocked_level < MAX_LEVEL:
        if _recent_streak_correct(attempts, unlocked_level) >= UNLOCK_STREAK:
            unlocked_level += 1

    new_state = state.model_copy(
        update={
            "attempts": attempts,
            "correct_count": state.correct_count + (1 if correct else 0),
            "total_count": state.total_count + 1,
            "unlocked_level": unlocked_level,
        }
    )
    return new_state, new_energy, None
