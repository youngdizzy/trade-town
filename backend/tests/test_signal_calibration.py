"""Covers app/signal_calibration.py — v0.6.2 Phase 7. The core property
under test throughout: grading is a fixed function of signals visible at
challenge time (trend/volatility/risk/research), never of what price did
next, so a correct answer always means "matched the rubric," not "got
lucky."
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.market_data import MockMarketDataProvider
from app.research import default_research
from app.schemas import RiskWarning
from app.signal_calibration import (
    MAX_LEVEL,
    UNLOCK_STREAK,
    _disciplined_choice,
    _pending,
    _trend_pct,
    _volatility_pct,
    generate_challenge,
    grade_submission,
)
from app.state import default_state
from app.watchlist import default_watchlist


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_trend_pct_matches_first_to_last_close():
    provider = MockMarketDataProvider()
    candles = provider.get_candles("AAPL", "1h", 30)
    expected = (candles[-1].close - candles[0].close) / candles[0].close * 100
    assert _trend_pct(candles) == expected


def test_volatility_pct_is_nonnegative():
    provider = MockMarketDataProvider()
    candles = provider.get_candles("MSFT", "1h", 30)
    assert _volatility_pct(candles) >= 0


def test_level_1_rubric_reads_trend_alone():
    assert _disciplined_choice(1, 3.0, 1.0, None, None)[0] == "enter"
    assert _disciplined_choice(1, -3.0, 1.0, None, None)[0] == "avoid"
    assert _disciplined_choice(1, 0.2, 1.0, None, None)[0] == "wait"


def test_level_3_ranging_market_is_always_wait_regardless_of_direction():
    # abs(trend) not > 2x volatility -> ranging, must be WAIT even though
    # trend is nonzero (a small drift inside a noisy range isn't a real
    # trend to trade on).
    choice, _ = _disciplined_choice(3, 1.0, 5.0, None, None)
    assert choice == "wait"


def test_level_4_active_warning_overrides_an_otherwise_positive_entry():
    warning = RiskWarning(id="w1", symbol="AAPL", severity="critical", message="Elevated drawdown risk", createdAt=_now_iso())
    # Strong positive trend that level 3 alone would call ENTER...
    base_choice, _ = _disciplined_choice(3, 5.0, 1.0, None, None)
    assert base_choice == "enter"
    # ...but level 4 must downgrade to WAIT once a real active warning exists.
    choice, notes = _disciplined_choice(4, 5.0, 1.0, warning, None)
    assert choice == "wait"
    assert "risk warning" in notes.lower()


def test_level_4_with_no_warning_falls_back_to_level_3_rubric():
    choice, _ = _disciplined_choice(4, 5.0, 1.0, None, None)
    assert choice == "enter"  # same as level 3 with no conflicting evidence


def test_level_5_combines_all_real_signals_into_one_score():
    # Positive trend, low volatility, no warning, high research confidence -> ENTER.
    choice, _ = _disciplined_choice(5, 4.0, 0.5, None, 90.0)
    assert choice == "enter"
    # Same trend but a critical warning and low research confidence should pull it down.
    warning = RiskWarning(id="w2", symbol="MSFT", severity="critical", message="Halted pending news", createdAt=_now_iso())
    choice2, _ = _disciplined_choice(5, 4.0, 0.5, warning, 10.0)
    assert choice2 != "enter"


def test_generate_challenge_respects_level_bounds_and_produces_real_candles():
    provider = MockMarketDataProvider()
    watchlist = default_watchlist()
    challenge = generate_challenge(99, provider, watchlist, [], [])  # out-of-range clamps to MAX_LEVEL
    assert challenge.level == MAX_LEVEL
    assert len(challenge.candles) > 0
    assert challenge.symbol in {w.symbol for w in watchlist}
    assert challenge.id in _pending  # held server-side, not returned with the answer


def test_generate_challenge_raises_on_empty_watchlist():
    provider = MockMarketDataProvider()
    try:
        generate_challenge(1, provider, [], [], [])
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_generate_challenge_never_leaks_the_correct_answer_to_the_client_shape():
    provider = MockMarketDataProvider()
    challenge = generate_challenge(1, provider, default_watchlist(), [], [])
    # The pydantic model the client actually receives has no correctness field at all.
    assert not hasattr(challenge, "correct_choice")
    assert not hasattr(challenge, "correctChoice")


def test_grade_submission_correct_answer_awards_energy_and_records_attempt():
    state = default_state()
    # Start below the cap so a real award is actually observable — a
    # fresh default_state() starts already-full, which would make this
    # assertion pass or fail for the wrong reason.
    state = state.model_copy(update={"agent_energy": state.agent_energy.model_copy(update={"current": 50.0})})
    provider = MockMarketDataProvider()
    challenge = generate_challenge(1, provider, state.watchlist, [], [])
    _, correct_choice, _ = _pending[challenge.id]

    new_calibration, new_energy, error = grade_submission(state.signal_calibration, state.agent_energy, challenge.id, correct_choice)
    assert error is None
    assert new_calibration.total_count == 1
    assert new_calibration.correct_count == 1
    assert new_calibration.attempts[-1].correct is True
    assert new_energy.current > state.agent_energy.current


def test_grade_submission_wrong_answer_awards_no_energy():
    state = default_state()
    provider = MockMarketDataProvider()
    challenge = generate_challenge(1, provider, state.watchlist, [], [])
    _, correct_choice, _ = _pending[challenge.id]
    wrong_choice = next(c for c in ("enter", "wait", "avoid") if c != correct_choice)

    new_calibration, new_energy, error = grade_submission(state.signal_calibration, state.agent_energy, challenge.id, wrong_choice)
    assert error is None
    assert new_calibration.correct_count == 0
    assert new_calibration.total_count == 1
    assert new_energy.current == state.agent_energy.current


def test_grade_submission_unknown_challenge_id_changes_nothing():
    state = default_state()
    new_calibration, new_energy, error = grade_submission(state.signal_calibration, state.agent_energy, "not-a-real-id", "enter")
    assert error is not None
    assert new_calibration == state.signal_calibration
    assert new_energy == state.agent_energy


def test_grade_submission_consumes_the_pending_challenge_once():
    state = default_state()
    provider = MockMarketDataProvider()
    challenge = generate_challenge(1, provider, state.watchlist, [], [])
    _, correct_choice, _ = _pending[challenge.id]

    grade_submission(state.signal_calibration, state.agent_energy, challenge.id, correct_choice)
    assert challenge.id not in _pending
    # Submitting the same id again must fail, not double-grade.
    _, _, error = grade_submission(state.signal_calibration, state.agent_energy, challenge.id, correct_choice)
    assert error is not None


def test_unlocked_level_advances_only_after_a_correct_streak_at_the_current_level():
    state = default_state()
    provider = MockMarketDataProvider()
    calibration = state.signal_calibration
    energy = state.agent_energy
    assert calibration.unlocked_level == 1

    for _ in range(UNLOCK_STREAK - 1):
        challenge = generate_challenge(1, provider, state.watchlist, [], [])
        _, correct_choice, _ = _pending[challenge.id]
        calibration, energy, error = grade_submission(calibration, energy, challenge.id, correct_choice)
        assert error is None
    assert calibration.unlocked_level == 1  # not yet a full streak

    challenge = generate_challenge(1, provider, state.watchlist, [], [])
    _, correct_choice, _ = _pending[challenge.id]
    calibration, energy, error = grade_submission(calibration, energy, challenge.id, correct_choice)
    assert error is None
    assert calibration.unlocked_level == 2


def test_a_miss_resets_the_streak_toward_unlocking_the_next_level():
    state = default_state()
    provider = MockMarketDataProvider()
    calibration = state.signal_calibration
    energy = state.agent_energy

    challenge = generate_challenge(1, provider, state.watchlist, [], [])
    _, correct_choice, _ = _pending[challenge.id]
    calibration, energy, _ = grade_submission(calibration, energy, challenge.id, correct_choice)

    challenge = generate_challenge(1, provider, state.watchlist, [], [])
    _, correct_choice, _ = _pending[challenge.id]
    wrong_choice = next(c for c in ("enter", "wait", "avoid") if c != correct_choice)
    calibration, energy, _ = grade_submission(calibration, energy, challenge.id, wrong_choice)

    for _ in range(UNLOCK_STREAK):
        challenge = generate_challenge(1, provider, state.watchlist, [], [])
        _, correct_choice, _ = _pending[challenge.id]
        calibration, energy, _ = grade_submission(calibration, energy, challenge.id, correct_choice)
    # Exactly UNLOCK_STREAK fresh correct answers after the miss should unlock — the
    # miss must not have left a stale partial streak that unlocks early or late.
    assert calibration.unlocked_level == 2


def test_level_4_prefers_a_symbol_with_an_active_warning_when_one_exists():
    provider = MockMarketDataProvider()
    watchlist = default_watchlist()
    target_symbol = watchlist[0].symbol
    warnings = [RiskWarning(id="w3", symbol=target_symbol, severity="warning", message="Test warning", createdAt=_now_iso())]
    # Run several times — random symbol choice should consistently prefer
    # the one real symbol with an active warning over the rest.
    for _ in range(10):
        challenge = generate_challenge(4, provider, watchlist, warnings, [])
        assert challenge.symbol == target_symbol


def test_research_backed_watchlist_symbols_available_for_level_5_factor():
    # Sanity check that default_research()'s symbols actually overlap the
    # watchlist, so level 5's research-confidence factor is exercised
    # somewhere in normal play rather than always reading "no research".
    research = default_research()
    watchlist_symbols = {w.symbol for w in default_watchlist()}
    assert any(r.symbol in watchlist_symbols for r in research)
