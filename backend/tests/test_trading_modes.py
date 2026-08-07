"""Covers app/trading_modes.py — Design Bible Chapter 75, Company
Trading Modes & Institutional Capital Protection. Every lever must trace
back to a real formula over already-real state — never a fabricated
signal. See the module's own docstring for the full honesty boundary.
"""
from __future__ import annotations

from app.discipline import DisciplineReview
from app.portfolio import default_portfolio
from app.risk_engine import default_risk_limits
from app.schemas import PaperPosition, PaperPortfolio, PaperTrade, RegimeReconciliation, TradingModeState, TradingStyle
from app.trading_modes import (
    acknowledge_losing_streak,
    apply_circuit_breaker_tightening,
    assign_trading_style,
    build_circuit_breaker_tier_memory,
    change_trading_mode,
    circuit_breaker_confidence_bonus,
    compute_adaptive_mode_recommendation,
    compute_consecutive_losses,
    compute_daily_circuit_breaker,
    compute_losing_streak,
    compute_trading_mode_health,
    compute_trading_style_performance,
    default_trading_mode_state,
    flatten_day_positions,
    generate_recovery_briefing,
)


def _state(**overrides: object) -> TradingModeState:
    base = default_trading_mode_state("2026-01-01T00:00:00Z")
    return base.model_copy(update=overrides) if overrides else base


def _trade(*, pnl: float, pnl_pct: float | None = None, trading_style: TradingStyle | None = None, decision_id: str | None = None, closed_sim_minutes: int = 1440) -> PaperTrade:
    return PaperTrade(
        id=f"trade-{closed_sim_minutes}-{pnl}",
        symbol="AAPL",
        side="buy",  # type: ignore[arg-type]
        quantity=10.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl,
        pnl=pnl,
        pnlPct=pnl_pct if pnl_pct is not None else pnl,
        durationMinutes=60,
        confidence=70.0,
        reason="test",
        marketConditions="test",
        openedAt="2026-01-01T00:00:00Z",
        closedAt="2026-01-01T01:00:00Z",
        openedSimMinutes=closed_sim_minutes - 60,
        closedSimMinutes=closed_sim_minutes,
        tradingStyle=trading_style,
        decisionId=decision_id,
    )


def _position(*, symbol: str = "AAPL", trading_style: TradingStyle | None = "day") -> PaperPosition:
    return PaperPosition(
        id=f"pos-{symbol}",
        symbol=symbol,
        side="buy",  # type: ignore[arg-type]
        quantity=10.0,
        entryPrice=100.0,
        currentPrice=100.0,
        unrealizedPnl=0.0,
        unrealizedPnlPct=0.0,
        openedBy="atlas",  # type: ignore[arg-type]
        confidence=70.0,
        openedAt="2026-01-01T00:00:00Z",
        openedSimMinutes=0,
        tradingStyle=trading_style,
    )


def _reconciliation(**overrides: object) -> RegimeReconciliation:
    base = RegimeReconciliation(
        environmentRegime="bull",  # type: ignore[arg-type]
        environmentLabel="Bull Market",
        intelligenceRegime="strong_bull_trend",  # type: ignore[arg-type]
        intelligenceLabel="Strong Bull Trend",
        qualityTier="excellent",  # type: ignore[arg-type]
        confidencePct=88.0,
        agreement="aligned",  # type: ignore[arg-type]
        posture="opportunistic",  # type: ignore[arg-type]
        rationale="test",
    )
    return base.model_copy(update=overrides) if overrides else base


class TestAssignTradingStyle:
    def test_day_trading_mode_always_tags_day(self) -> None:
        state = _state(mode="day_trading")
        for _ in range(5):
            style, state = assign_trading_style(state)
            assert style == "day"

    def test_swing_trading_mode_always_tags_swing(self) -> None:
        state = _state(mode="swing_trading")
        for _ in range(5):
            style, state = assign_trading_style(state)
            assert style == "swing"

    def test_hybrid_rotation_converges_on_configured_split(self) -> None:
        state = _state(mode="hybrid", hybrid_day_allocation_pct=70.0)
        styles: list[str] = []
        for _ in range(100):
            style, state = assign_trading_style(state)
            styles.append(style)
        day_count = styles.count("day")
        # A deterministic largest-remainder rotation over 100 calls at a
        # 70% split lands exactly on 70 — never a probabilistic draw.
        assert day_count == 70
        assert state.rotation_counter == 100

    def test_hybrid_rotation_is_deterministic_not_a_coin_flip(self) -> None:
        state_a = _state(mode="hybrid", hybrid_day_allocation_pct=50.0)
        state_b = _state(mode="hybrid", hybrid_day_allocation_pct=50.0)
        styles_a: list[str] = []
        styles_b: list[str] = []
        for _ in range(20):
            style, state_a = assign_trading_style(state_a)
            styles_a.append(style)
        for _ in range(20):
            style, state_b = assign_trading_style(state_b)
            styles_b.append(style)
        assert styles_a == styles_b


class TestFlattenDayPositions:
    def test_flattens_only_day_tagged_positions(self) -> None:
        day_pos = _position(symbol="AAPL", trading_style="day")
        swing_pos = _position(symbol="MSFT", trading_style="swing")
        portfolio = default_portfolio().model_copy(update={"positions": [day_pos, swing_pos]})
        updated, closed = flatten_day_positions(portfolio, {"AAPL": 105.0, "MSFT": 200.0}, now_sim_minutes=1440)
        assert len(closed) == 1
        assert closed[0].symbol == "AAPL"
        remaining_symbols = {p.symbol for p in updated.positions}
        assert remaining_symbols == {"MSFT"}

    def test_no_day_positions_is_a_no_op(self) -> None:
        swing_pos = _position(symbol="MSFT", trading_style="swing")
        portfolio = default_portfolio().model_copy(update={"positions": [swing_pos]})
        updated, closed = flatten_day_positions(portfolio, {"MSFT": 200.0}, now_sim_minutes=1440)
        assert closed == []
        assert len(updated.positions) == 1


class TestDailyCircuitBreaker:
    def test_none_tier_when_within_all_thresholds(self) -> None:
        portfolio = default_portfolio()
        result = compute_daily_circuit_breaker(default_risk_limits(), _state(), portfolio, sim_day=1)
        assert result.tier == "none"

    def test_tier1_when_loss_crosses_first_threshold(self) -> None:
        trade = _trade(pnl=-1200.0, pnl_pct=-1.2, closed_sim_minutes=30)
        portfolio = default_portfolio().model_copy(update={"trade_history": [trade]})
        result = compute_daily_circuit_breaker(default_risk_limits(), _state(), portfolio, sim_day=0)
        assert result.tier == "tier1"

    def test_tier4_mirrors_max_daily_loss_pct_not_a_separate_field(self) -> None:
        limits = default_risk_limits()
        trade = _trade(pnl=-6000.0, pnl_pct=-6.0, closed_sim_minutes=30)
        portfolio = default_portfolio().model_copy(update={"trade_history": [trade]})
        result = compute_daily_circuit_breaker(limits, _state(), portfolio, sim_day=0)
        assert result.tier == "tier4"
        assert result.tier4_pct == limits.max_daily_loss_pct


class TestApplyCircuitBreakerTightening:
    def test_tier1_tightens_by_075x(self) -> None:
        limits = default_risk_limits()
        tightened = apply_circuit_breaker_tightening(limits, "tier1")
        assert tightened.risk_per_trade_pct == round(limits.risk_per_trade_pct * 0.75, 2)
        assert tightened.max_position_pct == round(limits.max_position_pct * 0.75, 2)

    def test_tier2_compounds_tightening(self) -> None:
        limits = default_risk_limits()
        tightened = apply_circuit_breaker_tightening(limits, "tier2")
        assert tightened.risk_per_trade_pct == round(limits.risk_per_trade_pct * 0.75 * 0.75, 2)

    def test_none_tier_leaves_limits_unchanged(self) -> None:
        limits = default_risk_limits()
        assert apply_circuit_breaker_tightening(limits, "none") == limits

    def test_tier3_and_tier4_leave_sizing_unchanged_new_trades_blocked_instead(self) -> None:
        limits = default_risk_limits()
        assert apply_circuit_breaker_tightening(limits, "tier3") == limits
        assert apply_circuit_breaker_tightening(limits, "tier4") == limits


class TestConfidenceBonus:
    def test_bonus_by_tier(self) -> None:
        assert circuit_breaker_confidence_bonus("none") == 0.0
        assert circuit_breaker_confidence_bonus("tier1") == 10.0
        assert circuit_breaker_confidence_bonus("tier2") == 20.0
        assert circuit_breaker_confidence_bonus("tier3") == 20.0
        assert circuit_breaker_confidence_bonus("tier4") == 20.0


class TestConsecutiveLosses:
    def test_counts_trailing_losses_only(self) -> None:
        history = [_trade(pnl=100.0, closed_sim_minutes=1), _trade(pnl=-50.0, closed_sim_minutes=2), _trade(pnl=-30.0, closed_sim_minutes=3)]
        assert compute_consecutive_losses(history) == 2

    def test_zero_when_most_recent_is_a_win(self) -> None:
        history = [_trade(pnl=-50.0, closed_sim_minutes=1), _trade(pnl=100.0, closed_sim_minutes=2)]
        assert compute_consecutive_losses(history) == 0

    def test_empty_history_is_zero(self) -> None:
        assert compute_consecutive_losses([]) == 0


class TestLosingStreak:
    def test_pause_activates_at_threshold(self) -> None:
        state = _state(losing_streak_pause_count=3)
        history = [_trade(pnl=-10.0, closed_sim_minutes=i) for i in range(3)]
        read, updated_state = compute_losing_streak(state, history)
        assert read.consecutive_losses == 3
        assert read.pause_active is True

    def test_acknowledgment_silences_current_streak(self) -> None:
        state = _state(losing_streak_pause_count=3, losing_streak_acknowledged=True)
        history = [_trade(pnl=-10.0, closed_sim_minutes=i) for i in range(3)]
        read, _ = compute_losing_streak(state, history)
        assert read.pause_active is False

    def test_acknowledgment_auto_clears_once_a_win_breaks_the_streak(self) -> None:
        state = _state(losing_streak_acknowledged=True)
        history = [_trade(pnl=-10.0, closed_sim_minutes=1), _trade(pnl=50.0, closed_sim_minutes=2)]
        read, updated_state = compute_losing_streak(state, history)
        assert read.consecutive_losses == 0
        assert updated_state.losing_streak_acknowledged is False

    def test_a_fresh_streak_after_ack_repauses_independently(self) -> None:
        # Simulates two sequential real ticks (the actual usage pattern
        # in app/nexus.py, which threads the returned state forward)
        # rather than one static snapshot — the acknowledgment auto-
        # clears the instant the win lands, then a brand-new streak
        # re-pauses on its own.
        state = _state(losing_streak_pause_count=2, losing_streak_acknowledged=True)
        history_after_win = [_trade(pnl=50.0, closed_sim_minutes=1)]
        _, state = compute_losing_streak(state, history_after_win)
        assert state.losing_streak_acknowledged is False

        history_after_losses = [*history_after_win, _trade(pnl=-10.0, closed_sim_minutes=2), _trade(pnl=-10.0, closed_sim_minutes=3)]
        read, _ = compute_losing_streak(state, history_after_losses)
        assert read.consecutive_losses == 2
        assert read.pause_active is True

    def test_acknowledge_losing_streak_sets_the_flag(self) -> None:
        state = _state()
        updated = acknowledge_losing_streak(state)
        assert updated.losing_streak_acknowledged is True


class TestCircuitBreakerTierMemory:
    def test_none_when_tier_unchanged(self) -> None:
        assert build_circuit_breaker_tier_memory("tier1", "tier1", -1.5, "2026-01-01T00:00:00Z") is None

    def test_real_record_when_tier_escalates(self) -> None:
        record = build_circuit_breaker_tier_memory("none", "tier2", -2.5, "2026-01-01T00:00:00Z")
        assert record is not None
        assert "escalated" in record.title.lower()
        assert "TIER2" in record.title

    def test_real_record_when_tier_eases(self) -> None:
        record = build_circuit_breaker_tier_memory("tier2", "tier1", -1.2, "2026-01-01T00:00:00Z")
        assert record is not None
        assert "eased" in record.title.lower()


class TestChangeTradingMode:
    def test_records_a_real_memory_entry_and_resets_rotation(self) -> None:
        state = _state(mode="swing_trading", rotation_counter=5)
        updated, memory = change_trading_mode(state, new_mode="day_trading", hybrid_day_allocation_pct=None, now_iso="2026-01-01T00:00:00Z")
        assert updated.mode == "day_trading"
        assert updated.previous_mode == "swing_trading"
        assert updated.rotation_counter == 0
        assert "swing_trading" in memory.title
        assert "day_trading" in memory.title

    def test_hybrid_allocation_clamped_to_0_100(self) -> None:
        state = _state()
        updated, _ = change_trading_mode(state, new_mode="hybrid", hybrid_day_allocation_pct=150.0, now_iso="2026-01-01T00:00:00Z")
        assert updated.hybrid_day_allocation_pct == 100.0


class TestRecoveryBriefing:
    def test_real_stats_computed_from_recent_trades(self) -> None:
        portfolio: PaperPortfolio = default_portfolio().model_copy(
            update={
                "trade_history": [
                    _trade(pnl=-100.0, pnl_pct=-2.0, decision_id="decision-1", closed_sim_minutes=1440),
                    _trade(pnl=-50.0, pnl_pct=-1.0, decision_id="decision-2", closed_sim_minutes=2880),
                ]
            }
        )
        review = DisciplineReview.model_construct(id="review-1", decision_id="decision-1")  # type: ignore[call-arg]
        briefing = generate_recovery_briefing("circuit_breaker_tier4", portfolio, [review], sim_day=2, briefing_id="briefing-1")
        assert briefing.trigger == "circuit_breaker_tier4"
        assert briefing.largest_loss_pct == -2.0
        assert briefing.linked_discipline_review_ids == ["review-1"]
        assert briefing.recent_win_rate == 0.0


class TestTradingStylePerformance:
    def test_splits_by_style(self) -> None:
        history = [
            _trade(pnl=100.0, pnl_pct=2.0, trading_style="day", closed_sim_minutes=1),
            _trade(pnl=-50.0, pnl_pct=-1.0, trading_style="day", closed_sim_minutes=2),
            _trade(pnl=200.0, pnl_pct=4.0, trading_style="swing", closed_sim_minutes=3),
        ]
        results = compute_trading_style_performance(history)
        by_style = {r.style: r for r in results}
        assert by_style["day"].trade_count == 2
        assert by_style["day"].win_rate == 50.0
        assert by_style["swing"].trade_count == 1
        assert by_style["swing"].win_rate == 100.0

    def test_untagged_trades_are_excluded(self) -> None:
        history = [_trade(pnl=50.0, trading_style=None, closed_sim_minutes=1)]
        assert compute_trading_style_performance(history) == []


class TestTradingModeHealth:
    def test_no_trades_no_assessment(self) -> None:
        assert compute_trading_mode_health([], sim_day=1) == []

    def test_strong_recent_performance_reads_excellent(self) -> None:
        history = [_trade(pnl=100.0, pnl_pct=5.0, trading_style="day", closed_sim_minutes=i) for i in range(10)]
        results = compute_trading_mode_health(history, sim_day=1)
        day_result = next(r for r in results if r.style == "day")
        assert day_result.status == "excellent"

    def test_poor_recent_performance_reads_critical_or_worse(self) -> None:
        history = [_trade(pnl=-100.0, pnl_pct=-5.0, trading_style="swing", closed_sim_minutes=i) for i in range(10)]
        results = compute_trading_mode_health(history, sim_day=1)
        swing_result = next(r for r in results if r.style == "swing")
        assert swing_result.status in ("critical", "retire_candidate")


class TestAdaptiveModeRecommendation:
    def test_aligned_opportunistic_recommends_swing(self) -> None:
        rec = compute_adaptive_mode_recommendation(_reconciliation(posture="opportunistic", agreement="aligned", quality_tier="excellent"))
        assert rec.recommended_mode == "swing_trading"

    def test_sideways_recommends_day_trading(self) -> None:
        rec = compute_adaptive_mode_recommendation(_reconciliation(environment_regime="sideways", quality_tier="average", posture="cautious", agreement="diverging"))
        # sideways + non-poor quality takes precedence in the decision table
        assert rec.recommended_mode == "day_trading"

    def test_diverging_recommends_hybrid_when_not_sideways(self) -> None:
        rec = compute_adaptive_mode_recommendation(_reconciliation(environment_regime="bull", agreement="diverging", quality_tier="average", posture="normal"))
        assert rec.recommended_mode == "hybrid"

    def test_poor_quality_never_recommends_a_mode_points_to_defensive_mode(self) -> None:
        rec = compute_adaptive_mode_recommendation(_reconciliation(quality_tier="avoid_trading", posture="cautious"))
        assert rec.recommended_mode is None
        assert rec.note is not None
        assert "defensive" in rec.note.lower()

    def test_no_strong_signal_recommends_nothing(self) -> None:
        rec = compute_adaptive_mode_recommendation(
            _reconciliation(environment_regime="bull", agreement="aligned", posture="normal", quality_tier="good")
        )
        assert rec.recommended_mode is None
