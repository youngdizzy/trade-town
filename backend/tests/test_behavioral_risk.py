"""Covers app/behavioral_risk.py — the Behavioral Circuit Breaker, the
real revenge-trading detector. Every case below traces directly to the
CEO's own review requirements: timing alone must never trigger (a
legitimate setup immediately following a loss must remain possible),
only a real corroborating signal (same-instrument or a loss-driven size
increase) can. compute_behavioral_check() must never crash or fabricate
a value on missing/degenerate optional data.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.behavioral_risk import (
    REPEATED_REENTRY_LOOKBACK_TRADES,
    SIZE_BASELINE_TRADES,
    compute_behavioral_check,
    default_behavioral_circuit_breaker,
)
from app.schemas import ConfidenceFactor, DecisionConfidence, PaperTrade, TradeProposal


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _proposal(*, symbol: str = "NEXA", quantity: float = 10.0, price: float = 100.0, recommendation: str = "buy") -> TradeProposal:
    return TradeProposal(
        id=f"proposal-{symbol}",
        symbol=symbol,
        category="stock",
        quantity=quantity,
        price=price,
        confidence=90.0,
        analystVotes=[],
        overallRecommendation=recommendation,  # type: ignore[arg-type]
        researchSummary="test research summary",
        riskSummary="test risk summary",
        confidenceEngine=DecisionConfidence(score=90.0, tier="strong", summary="test", factors=[ConfidenceFactor(name="test", score=90.0, weight=1.0, detail="test")]),
        createdAt=_now_iso(),
        createdSimMinutes=0,
    )


def _trade(
    *,
    symbol: str = "NEXA",
    side: str = "buy",
    quantity: float = 10.0,
    entry_price: float = 100.0,
    pnl: float = -100.0,
    opened_sim_minutes: int = 0,
    closed_sim_minutes: int = 0,
) -> PaperTrade:
    return PaperTrade(
        id=f"trade-{symbol}-{closed_sim_minutes}",
        symbol=symbol,
        side=side,  # type: ignore[arg-type]
        quantity=quantity,
        entryPrice=entry_price,
        exitPrice=entry_price * (0.9 if pnl < 0 else 1.1),
        pnl=pnl,
        pnlPct=-10.0 if pnl < 0 else 10.0,
        durationMinutes=max(closed_sim_minutes - opened_sim_minutes, 0),
        confidence=80.0,
        reason="test trade",
        marketConditions="test conditions",
        openedAt=_now_iso(),
        closedAt=_now_iso(),
        openedSimMinutes=opened_sim_minutes,
        closedSimMinutes=closed_sim_minutes,
    )


class TestDefaultBehavioralCircuitBreaker:
    def test_defaults_to_clear(self) -> None:
        read = default_behavioral_circuit_breaker()
        assert read.status == "clear"
        assert read.reasons == []


class TestComputeBehavioralCheck:
    def test_case_a_true_revenge_behavior_triggers(self) -> None:
        """Loss, then rapid re-entry, same instrument, increased size."""
        loss = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, pnl=-100.0, closed_sim_minutes=100)
        candidate = _proposal(symbol="NEXA", quantity=20.0, price=100.0)  # 2x normal size
        read = compute_behavioral_check(candidate, [loss], now_sim_minutes=110, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status == "triggered"
        assert read.same_instrument is True

    def test_case_b_legitimate_follow_up_never_triggers(self) -> None:
        """Different instrument, normal size, even though rapid."""
        loss = _trade(symbol="NEXA", closed_sim_minutes=100)
        candidate = _proposal(symbol="DIFFERENT", quantity=10.0, price=100.0)
        read = compute_behavioral_check(candidate, [loss], now_sim_minutes=110, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status != "triggered"

    def test_same_size_different_instrument_stays_at_most_warning(self) -> None:
        prior = _trade(symbol="AAPL", quantity=10.0, entry_price=100.0, pnl=100.0, closed_sim_minutes=0)
        loss = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, pnl=-100.0, opened_sim_minutes=50, closed_sim_minutes=100)
        candidate = _proposal(symbol="DIFFERENT", quantity=10.0, price=100.0)
        read = compute_behavioral_check(candidate, [prior, loss], now_sim_minutes=110, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status != "triggered"

    def test_smaller_risk_trade_never_triggers_purely_from_downsizing(self) -> None:
        baseline = _trade(symbol="AAPL", quantity=10.0, entry_price=100.0, pnl=100.0, opened_sim_minutes=0, closed_sim_minutes=50)
        loss = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, pnl=-100.0, opened_sim_minutes=60, closed_sim_minutes=100)
        candidate = _proposal(symbol="DIFFERENT", quantity=5.0, price=100.0)  # half the baseline size, different instrument
        read = compute_behavioral_check(candidate, [baseline, loss], now_sim_minutes=110, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.size_increase_pct is not None
        assert read.size_increase_pct <= 0
        assert read.status != "triggered"

    def test_larger_but_legitimate_size_different_instrument_slow_timing_stays_clear(self) -> None:
        """Larger than recent normal, but limit-compliant sizing choice,
        on a different instrument, well outside the cooldown window —
        the loss-driven-vs-legitimate distinction the CEO's review
        required."""
        loss = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, pnl=-100.0, closed_sim_minutes=0)
        candidate = _proposal(symbol="DIFFERENT", quantity=30.0, price=100.0)  # 3x normal size
        read = compute_behavioral_check(candidate, [loss], now_sim_minutes=1000, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status == "clear"

    def test_different_instrument_same_size_not_triggered_from_instrument_alone_without_rapid_timing(self) -> None:
        loss = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, pnl=-100.0, closed_sim_minutes=0)
        candidate = _proposal(symbol="NEXA", quantity=10.0, price=100.0)
        read = compute_behavioral_check(candidate, [loss], now_sim_minutes=1000, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status == "clear"

    def test_multiple_consecutive_losses_reflected_in_consecutive_losses(self) -> None:
        losses = [
            _trade(symbol="NEXA", pnl=-10.0, opened_sim_minutes=0, closed_sim_minutes=10),
            _trade(symbol="NEXA", pnl=-10.0, opened_sim_minutes=20, closed_sim_minutes=30),
            _trade(symbol="NEXA", pnl=-10.0, opened_sim_minutes=40, closed_sim_minutes=50),
        ]
        read = compute_behavioral_check(None, losses, now_sim_minutes=1000, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.consecutive_losses == 3
        # Cooldown timing keys off the most recent loss only.
        assert read.minutes_since_loss == 1000 - 50

    def test_multiple_consecutive_wins_reflected_in_consecutive_wins(self) -> None:
        wins = [
            _trade(symbol="NEXA", pnl=10.0, opened_sim_minutes=0, closed_sim_minutes=10),
            _trade(symbol="NEXA", pnl=10.0, opened_sim_minutes=20, closed_sim_minutes=30),
            _trade(symbol="NEXA", pnl=10.0, opened_sim_minutes=40, closed_sim_minutes=50),
        ]
        read = compute_behavioral_check(None, wins, now_sim_minutes=1000, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.consecutive_wins == 3
        assert read.consecutive_losses == 0

    def test_no_previous_trade_stays_clear_no_crash(self) -> None:
        candidate = _proposal()
        read = compute_behavioral_check(candidate, [], now_sim_minutes=0, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status == "clear"
        assert read.consecutive_losses == 0
        assert read.repeated_rapid_reentry_count == 0

    def test_winning_trade_followed_by_increased_size_stays_clear(self) -> None:
        win = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, pnl=100.0, closed_sim_minutes=0)
        candidate = _proposal(symbol="NEXA", quantity=50.0, price=100.0)
        read = compute_behavioral_check(candidate, [win], now_sim_minutes=1, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status == "clear"

    def test_cooldown_boundary_exactly_at_threshold_stays_clear(self) -> None:
        loss = _trade(symbol="NEXA", closed_sim_minutes=0)
        candidate = _proposal(symbol="NEXA", quantity=100.0)
        # now_sim_minutes - closed == cooldown_minutes exactly: not < cooldown, so not rapid.
        read = compute_behavioral_check(candidate, [loss], now_sim_minutes=60, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status == "clear"

    def test_cooldown_boundary_one_minute_inside_can_trigger(self) -> None:
        loss = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, closed_sim_minutes=0)
        candidate = _proposal(symbol="NEXA", quantity=100.0, price=100.0)
        read = compute_behavioral_check(candidate, [loss], now_sim_minutes=59, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status == "triggered"

    def test_size_threshold_boundary_exactly_at_threshold_does_not_corroborate(self) -> None:
        loss = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, closed_sim_minutes=0)
        # Baseline is 10*100=1000; candidate at exactly +50% = 1500.
        candidate = _proposal(symbol="DIFFERENT", quantity=15.0, price=100.0)
        read = compute_behavioral_check(candidate, [loss], now_sim_minutes=10, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status != "triggered"

    def test_ambient_mode_never_triggers(self) -> None:
        loss = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, closed_sim_minutes=0)
        read = compute_behavioral_check(None, [loss], now_sim_minutes=10, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status != "triggered"
        assert read.same_instrument is None
        assert read.size_increase_pct is None

    def test_zero_price_candidate_fails_safe_no_crash(self) -> None:
        loss = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, closed_sim_minutes=0)
        candidate = _proposal(symbol="DIFFERENT", quantity=10.0, price=0.0)
        read = compute_behavioral_check(candidate, [loss], now_sim_minutes=10, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.size_increase_pct is None

    def test_single_trade_history_no_baseline_no_crash(self) -> None:
        """The only trade in history is the loss itself — no prior
        trades exist to establish a size baseline against."""
        loss = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, closed_sim_minutes=0)
        candidate = _proposal(symbol="DIFFERENT", quantity=10.0, price=100.0)
        read = compute_behavioral_check(candidate, [loss], now_sim_minutes=10, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.size_increase_pct is None
        assert read.status != "triggered"

    def test_repeated_rapid_reentry_count_reflects_the_real_pattern(self) -> None:
        trades = [
            _trade(symbol="NEXA", pnl=-10.0, opened_sim_minutes=0, closed_sim_minutes=10),
            _trade(symbol="AAPL", pnl=-10.0, opened_sim_minutes=20, closed_sim_minutes=30),  # rapid re-entry #1 (20-10=10 < 60)
            _trade(symbol="MSFT", pnl=-10.0, opened_sim_minutes=40, closed_sim_minutes=50),  # rapid re-entry #2 (40-30=10 < 60)
        ]
        read = compute_behavioral_check(None, trades, now_sim_minutes=1000, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.repeated_rapid_reentry_count == 2
        assert any("Repeated rapid re-entry" in r for r in read.reasons) or read.status == "clear"

    def test_single_rapid_reentry_not_labeled_repeated(self) -> None:
        trades = [
            _trade(symbol="NEXA", pnl=100.0, opened_sim_minutes=0, closed_sim_minutes=10),
            _trade(symbol="AAPL", pnl=-10.0, opened_sim_minutes=20, closed_sim_minutes=30),
        ]
        read = compute_behavioral_check(None, trades, now_sim_minutes=1000, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.repeated_rapid_reentry_count == 0
        assert not any("Repeated rapid re-entry" in r for r in read.reasons)

    def test_lookback_window_constants_are_positive(self) -> None:
        assert SIZE_BASELINE_TRADES > 0
        assert REPEATED_REENTRY_LOOKBACK_TRADES > 0


class TestSameDirectionSignal:
    """Piece 8b — Prop-Firm Risk Intelligence Addendum, Requirement 10.
    Same-direction is informational only: it must never, by itself,
    turn a "warning" into a "triggered" the way same-instrument or a
    loss-driven size increase can (see app/behavioral_risk.py's own
    docstring for why a direction match is too common by chance to be
    real evidence on its own)."""

    def test_same_direction_alone_never_triggers(self) -> None:
        # Same direction ("buy"), different instrument, normal size,
        # rapid re-entry — the CEO's own "legitimate setup" case, now
        # with same_direction also true. Must stay well short of triggered.
        loss = _trade(symbol="NEXA", side="buy", closed_sim_minutes=100)
        candidate = _proposal(symbol="DIFFERENT", quantity=10.0, price=100.0, recommendation="buy")
        read = compute_behavioral_check(candidate, [loss], now_sim_minutes=110, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.same_direction is True
        assert read.status != "triggered"

    def test_same_direction_true_is_reported(self) -> None:
        loss = _trade(symbol="NEXA", side="buy", closed_sim_minutes=100)
        candidate = _proposal(symbol="NEXA", quantity=10.0, price=100.0, recommendation="buy")
        read = compute_behavioral_check(candidate, [loss], now_sim_minutes=110, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.same_direction is True
        assert any("same direction" in r.lower() for r in read.reasons)

    def test_same_direction_false_when_recommendation_differs(self) -> None:
        loss = _trade(symbol="NEXA", side="buy", closed_sim_minutes=100)
        candidate = _proposal(symbol="DIFFERENT", quantity=10.0, price=100.0, recommendation="sell")
        read = compute_behavioral_check(candidate, [loss], now_sim_minutes=110, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.same_direction is False

    def test_same_direction_none_in_ambient_mode(self) -> None:
        loss = _trade(symbol="NEXA", side="buy", closed_sim_minutes=100)
        read = compute_behavioral_check(None, [loss], now_sim_minutes=110, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.same_direction is None

    def test_same_direction_does_not_change_true_revenge_behavior_outcome(self) -> None:
        # Same instrument + size increase already corroborate on their
        # own (TestComputeBehavioralCheck's own case A) — same_direction
        # being true too must not change that this still triggers.
        loss = _trade(symbol="NEXA", side="buy", quantity=10.0, entry_price=100.0, pnl=-100.0, closed_sim_minutes=100)
        candidate = _proposal(symbol="NEXA", quantity=20.0, price=100.0, recommendation="buy")
        read = compute_behavioral_check(candidate, [loss], now_sim_minutes=110, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status == "triggered"
        assert read.same_direction is True


class TestWinTriggeredEscalation:
    """Piece 8b — Requirement 10's other half: "detect risk escalation
    after wins too, never blocking on one weak signal alone." Reuses the
    loss side's exact size-increase math, keyed off a real win instead.
    Must never reach "triggered" — the regression case every
    implementation of this signal must satisfy is that legitimate
    confidence-driven size growth after a win is never blocked, only
    ever surfaced as information."""

    def test_large_size_increase_after_a_rapid_win_reaches_warning_not_triggered(self) -> None:
        baseline = _trade(symbol="AAPL", quantity=10.0, entry_price=100.0, pnl=-10.0, opened_sim_minutes=0, closed_sim_minutes=10)
        win = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, pnl=500.0, opened_sim_minutes=20, closed_sim_minutes=30)
        candidate = _proposal(symbol="NEXA", quantity=50.0, price=100.0)  # 5x the 1000 baseline
        read = compute_behavioral_check(candidate, [baseline, win], now_sim_minutes=31, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status == "warning"
        assert read.status != "triggered"
        assert read.win_size_increase_pct is not None
        assert read.win_size_increase_pct > 50.0
        assert read.previous_win_symbol == "NEXA"
        assert read.previous_win_pnl == 500.0

    def test_even_an_extreme_size_increase_after_a_win_never_triggers(self) -> None:
        # This is the real regression proof: no matter how large the
        # increase, win-side escalation alone must never fail the
        # Gatekeeper check — legitimate confidence-driven growth (e.g.
        # after a strategy earns real certification) must never be
        # blocked by this signal.
        baseline = _trade(symbol="AAPL", quantity=10.0, entry_price=100.0, pnl=-10.0, opened_sim_minutes=0, closed_sim_minutes=10)
        win = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, pnl=1000.0, opened_sim_minutes=20, closed_sim_minutes=30)
        candidate = _proposal(symbol="NEXA", quantity=500.0, price=100.0)  # 50x the baseline
        read = compute_behavioral_check(candidate, [baseline, win], now_sim_minutes=31, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status != "triggered"

    def test_normal_size_after_a_win_stays_clear(self) -> None:
        baseline = _trade(symbol="AAPL", quantity=10.0, entry_price=100.0, pnl=-10.0, opened_sim_minutes=0, closed_sim_minutes=10)
        win = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, pnl=100.0, opened_sim_minutes=20, closed_sim_minutes=30)
        candidate = _proposal(symbol="NEXA", quantity=10.0, price=100.0)
        read = compute_behavioral_check(candidate, [baseline, win], now_sim_minutes=31, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status == "clear"
        assert read.win_size_increase_pct is not None
        assert read.win_size_increase_pct <= 50.0

    def test_win_outside_cooldown_window_stays_clear(self) -> None:
        baseline = _trade(symbol="AAPL", quantity=10.0, entry_price=100.0, pnl=-10.0, opened_sim_minutes=0, closed_sim_minutes=10)
        win = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, pnl=500.0, closed_sim_minutes=0)
        candidate = _proposal(symbol="NEXA", quantity=50.0, price=100.0)
        read = compute_behavioral_check(candidate, [baseline, win], now_sim_minutes=1000, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status == "clear"
        assert read.win_size_increase_pct is None

    def test_ambient_mode_never_flags_win_escalation(self) -> None:
        baseline = _trade(symbol="AAPL", quantity=10.0, entry_price=100.0, pnl=-10.0, opened_sim_minutes=0, closed_sim_minutes=10)
        win = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, pnl=500.0, opened_sim_minutes=20, closed_sim_minutes=30)
        read = compute_behavioral_check(None, [baseline, win], now_sim_minutes=31, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status != "triggered"
        assert read.win_size_increase_pct is None

    def test_no_baseline_win_escalation_no_crash(self) -> None:
        """The only trade in history is the win itself — no prior trades
        exist to establish a size baseline against."""
        win = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, pnl=100.0, closed_sim_minutes=0)
        candidate = _proposal(symbol="NEXA", quantity=50.0, price=100.0)
        read = compute_behavioral_check(candidate, [win], now_sim_minutes=1, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.status == "clear"
        assert read.win_size_increase_pct is None

    def test_win_side_never_populates_loss_side_fields(self) -> None:
        baseline = _trade(symbol="AAPL", quantity=10.0, entry_price=100.0, pnl=-10.0, opened_sim_minutes=0, closed_sim_minutes=10)
        win = _trade(symbol="NEXA", quantity=10.0, entry_price=100.0, pnl=500.0, opened_sim_minutes=20, closed_sim_minutes=30)
        candidate = _proposal(symbol="NEXA", quantity=50.0, price=100.0)
        read = compute_behavioral_check(candidate, [baseline, win], now_sim_minutes=31, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.previous_loss_symbol is None
        assert read.previous_loss_pnl is None
        assert read.minutes_since_loss is None
        assert read.same_instrument is None
        assert read.size_increase_pct is None

    def test_loss_side_never_populates_win_side_fields(self) -> None:
        loss = _trade(symbol="NEXA", side="buy", quantity=10.0, entry_price=100.0, pnl=-100.0, closed_sim_minutes=100)
        candidate = _proposal(symbol="NEXA", quantity=20.0, price=100.0)
        read = compute_behavioral_check(candidate, [loss], now_sim_minutes=110, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert read.previous_win_symbol is None
        assert read.previous_win_pnl is None
        assert read.minutes_since_win is None
        assert read.win_size_increase_pct is None
