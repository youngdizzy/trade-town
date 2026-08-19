"""Company Trading Modes & Institutional Capital Protection — Design
Bible Chapter 75 (see docs/DesignBible/volumes/09-departments/
chapter-75-company-trading-modes-institutional-capital-protection.md for
the full honesty boundary).

Two real, previously-confirmed gaps closed here, extending rather than
duplicating Chapter 65 (Market Regime & Adaptive Strategy) and Chapter 66
(Institutional Safety & Capital Protection):

1. **Trading Mode** — the CEO picks day_trading/swing_trading/hybrid.
   Every new TradeProposal is tagged `"day"`/`"swing"` (assign_trading_style)
   via a disclosed deterministic rotation for hybrid, never a coin flip
   dressed up as AI judgment. The tag threads through the ONE real,
   live position-opening call site this codebase has —
   app/executive.py's resolve_proposal() → app/portfolio.py's
   open_position()/close_position() — never through app/broker.py's
   place_order()/tick_broker() path, which is real but confirmed unused
   by any live caller (grep-confirmed before writing this module). Day
   Trading discipline (flatten_day_positions) force-closes any `"day"`-
   tagged position still open at sim-day rollover.

2. **Daily Circuit Breaker Tiers** — three new graduated tiers layered
   in front of the existing real `RiskLimits.max_daily_loss_pct` halt
   (Chapter 66), reusing app/nexus.py's own `_effective_risk_limits()`
   pattern (a derived, non-persisted RiskLimits copy) for Tier 1/2's
   tightening, and the real `activate_emergency_stop()` (Chapter 67) for
   Tier 4 — never a duplicate halt state.

Also real here: Losing Streak Protection (a real consecutive-loss count
over `trade_history`, pausing new proposals at a CEO threshold and
triggering the same real Emergency Stop at a higher one), a Recovery
Briefing generated only for tier/streak-triggered stops (modeled on
Chapter 72's `generate_crisis_briefing()`), an Adaptive Mode
recommendation reading Chapter 65's real `RegimeReconciliation` off a
disclosed decision table (recommendation only — no Automatic Mode this
pass, see the chapter's own Decision Logic), and a Trading Mode
Performance Split / Health Score reusing `app/strategy_lab.py`'s real
`StrategyHealthStatus` vocabulary and threshold constants rather than a
second, differently-worded scale.

Explicitly NOT built here: true per-account capital isolation for a live
Hybrid mode (blocked on Chapter 69 Part 1's own documented execution-
routing gap), Automatic Adaptive Mode, and a cross-regime learning loop
(not enough real tagged trade history exists yet in a fresh game to
learn from) — see the Design Bible chapter's own Implementation Notes.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from app.risk_engine import daily_realized_pnl_pct
from app.strategy_lab import (
    HEALTH_CRITICAL_WIN_RATE,
    HEALTH_DECLINING_RETURN_DELTA,
    HEALTH_EXCELLENT_MAX_DRAWDOWN,
    HEALTH_EXCELLENT_WIN_RATE,
    HEALTH_HEALTHY_RETURN_DELTA,
    HEALTH_HEALTHY_WIN_RATE,
    HEALTH_NEEDS_REVIEW_WIN_RATE,
    HEALTH_RETIRE_CANDIDATE_RETURN_PCT,
    HEALTH_RETIRE_CANDIDATE_WIN_RATE,
)
from app.execution_quality import apply_slippage
from app.portfolio import close_position
from app.schemas import (
    AdaptiveModeRecommendation,
    DailyCircuitBreakerRead,
    DailyCircuitBreakerTier,
    DisciplineReview,
    LosingStreakRead,
    MarketIntelligenceState,
    MemoryRecord,
    OrderSide,
    PaperPortfolio,
    PaperTrade,
    RecoveryBriefing,
    RegimeReconciliation,
    RiskLimits,
    StrategyHealthStatus,
    StrategyHealthTrend,
    TradingMode,
    TradingModeHealthAssessment,
    TradingModeState,
    TradingStyle,
    TradingStylePerformance,
)

# Circuit breaker levers. Tier 1/2 compound (Tier 2's factor applies on
# top of Tier 1's), the same "derived copy, never mutates the CEO's own
# saved limits" convention app/nexus.py's own _effective_risk_limits()
# already established for Company Priority.
TIER_RISK_FACTOR = 0.75
TIER1_CONFIDENCE_BONUS = 10.0
TIER2_CONFIDENCE_BONUS = 20.0

# Trades, not SimulationResult runs — a real, different, noisier input
# shape than app/strategy_lab.py's own HEALTH_RECENT_WINDOW = 3, so a
# wider window is used here rather than reusing that constant verbatim.
HEALTH_RECENT_TRADE_WINDOW = 10

MAX_RECOVERY_BRIEFINGS = 20


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_trading_mode_state(now_iso: str) -> TradingModeState:
    return TradingModeState(changedAt=now_iso)


def default_daily_circuit_breaker() -> DailyCircuitBreakerRead:
    return DailyCircuitBreakerRead(
        tier="none",
        dailyPnlPct=0.0,
        tier1Pct=1.0,
        tier2Pct=2.0,
        tier3Pct=3.0,
        tier4Pct=5.0,
        updatedAt=_now_iso(),
    )


def default_losing_streak() -> LosingStreakRead:
    return LosingStreakRead(
        consecutiveLosses=0,
        pauseActive=False,
        pauseThreshold=3,
        suspendThreshold=5,
    )


def change_trading_mode(
    state: TradingModeState,
    *,
    new_mode: TradingMode,
    hybrid_day_allocation_pct: float | None,
    now_iso: str,
) -> tuple[TradingModeState, MemoryRecord]:
    """The CEO's real trading-mode change. Resets the hybrid rotation
    counter on every change (a fresh mode deserves a fresh rotation, not
    one continuing mid-cycle from whatever the previous mode was doing)."""
    allocation = state.hybrid_day_allocation_pct if hybrid_day_allocation_pct is None else max(0.0, min(100.0, hybrid_day_allocation_pct))
    updated = state.model_copy(
        update={
            "mode": new_mode,
            "hybrid_day_allocation_pct": allocation,
            "changed_at": now_iso,
            "previous_mode": state.mode,
            "change_reason": "CEO manual change",
            "rotation_counter": 0,
        }
    )
    memory = MemoryRecord(
        id=f"trading-mode-{now_iso}",
        category="alert",
        title=f"Trading Mode changed: {state.mode} → {new_mode}",
        body=f"The CEO switched the company's Trading Mode from {state.mode.replace('_', ' ')} to {new_mode.replace('_', ' ')}"
        + (f", with a {allocation:.0f}% day-trading allocation." if new_mode == "hybrid" else "."),
        timestamp=now_iso,
    )
    return updated, memory


def assign_trading_style(state: TradingModeState) -> tuple[TradingStyle, TradingModeState]:
    """A disclosed, deterministic rotation for hybrid mode — a running
    counter `n` compares floor(n * split / 100) against floor((n-1) *
    split / 100); the proposal is tagged "day" exactly when that count
    just incremented, so any real run of proposals converges on the
    configured split, never a probability draw. day_trading/
    swing_trading modes always return their own fixed tag and never
    touch the counter."""
    if state.mode == "day_trading":
        return "day", state
    if state.mode == "swing_trading":
        return "swing", state
    n = state.rotation_counter + 1
    prev_day_count = math.floor((n - 1) * state.hybrid_day_allocation_pct / 100)
    new_day_count = math.floor(n * state.hybrid_day_allocation_pct / 100)
    style: TradingStyle = "day" if new_day_count > prev_day_count else "swing"
    return style, state.model_copy(update={"rotation_counter": n})


def flatten_day_positions(
    portfolio: PaperPortfolio,
    prices: dict[str, float],
    now_sim_minutes: int,
    risk_limits: RiskLimits | None = None,
    market_intelligence: MarketIntelligenceState | None = None,
) -> tuple[PaperPortfolio, list[PaperTrade]]:
    """Force-closes every open `"day"`-tagged position via the real
    close_position() — called once per sim-day rollover. A position's
    own tag governs it regardless of the company's *current* Trading
    Mode, so a CEO who opened a day trade and then switched to Swing
    mid-hold still gets that specific position flattened honestly.

    Piece 10b — `risk_limits`, when supplied, is threaded straight into
    close_position() for the real distance-to-drawdown-ceiling snapshot.

    CEO directive "Next Professional Trading Firm Phase," Priority 1
    (Execution Realism) — a forced end-of-day flatten is a market-style
    exit (no guaranteed price, unlike a limit order), so real slippage
    applies via app/execution_quality.py when `market_intelligence` is
    supplied; None (the default) keeps the exact pre-slippage fill."""
    closed: list[PaperTrade] = []
    day_positions = [p for p in portfolio.positions if p.trading_style == "day"]
    for position in day_positions:
        signal_price = prices.get(position.symbol, position.current_price)
        closing_side: OrderSide = "sell" if position.side == "buy" else "buy"
        exit_price, exit_slippage_bps = apply_slippage(
            signal_price, action_side=closing_side, market_intelligence=market_intelligence, symbol=position.symbol
        )
        portfolio, trade = close_position(
            portfolio,
            position_id=position.id,
            exit_price=exit_price,
            duration_minutes=now_sim_minutes - position.opened_sim_minutes,
            reason="Day Trading Mode — flattened at day-end",
            market_conditions=f"{position.symbol} flattened per Day Trading discipline (no overnight positions).",
            supporting_agents=[],
            opposing_agents=[],
            risk_limits=risk_limits,
            exit_slippage_bps=exit_slippage_bps,
        )
        if trade is not None:
            closed.append(trade)
    return portfolio, closed


def compute_daily_circuit_breaker(
    limits: RiskLimits,
    trading_mode_state: TradingModeState,
    portfolio: PaperPortfolio,
    sim_day: int,
) -> DailyCircuitBreakerRead:
    """Reads the exact same real daily P&L% app/risk_engine.py's own
    evaluate_sentinel_risk() already computes — never a second,
    independently-derived number. Tier 4 always mirrors
    limits.max_daily_loss_pct, never a separate CEO-set field, so there
    is only ever one real "daily maximum loss" number in this codebase."""
    daily_pnl_pct = daily_realized_pnl_pct(portfolio, sim_day)
    loss_pct = -daily_pnl_pct
    tier: DailyCircuitBreakerTier = "none"
    if loss_pct >= limits.max_daily_loss_pct:
        tier = "tier4"
    elif loss_pct >= trading_mode_state.tier3_pct:
        tier = "tier3"
    elif loss_pct >= trading_mode_state.tier2_pct:
        tier = "tier2"
    elif loss_pct >= trading_mode_state.tier1_pct:
        tier = "tier1"
    return DailyCircuitBreakerRead(
        tier=tier,
        dailyPnlPct=round(daily_pnl_pct, 2),
        tier1Pct=trading_mode_state.tier1_pct,
        tier2Pct=trading_mode_state.tier2_pct,
        tier3Pct=trading_mode_state.tier3_pct,
        tier4Pct=limits.max_daily_loss_pct,
        updatedAt=_now_iso(),
    )


def apply_circuit_breaker_tightening(limits: RiskLimits, tier: DailyCircuitBreakerTier) -> RiskLimits:
    """A derived, non-persisted RiskLimits copy — the identical pattern
    app/nexus.py's own _effective_risk_limits() already uses for Company
    Priority. Tier 1 applies one 0.75x tightening; Tier 2 compounds a
    second 0.75x on top (0.5625x total). Tier 3/4 don't need a tightened
    sizing copy — proposal generation is blocked outright at those
    tiers (see Decision Logic)."""
    if tier == "tier1":
        factor = TIER_RISK_FACTOR
    elif tier == "tier2":
        factor = TIER_RISK_FACTOR * TIER_RISK_FACTOR
    else:
        return limits
    return limits.model_copy(
        update={
            "risk_per_trade_pct": round(limits.risk_per_trade_pct * factor, 2),
            "max_position_pct": round(limits.max_position_pct * factor, 2),
        }
    )


def circuit_breaker_confidence_bonus(tier: DailyCircuitBreakerTier) -> float:
    """The real, disclosed points added to Gatekeeper's minimum
    confidence threshold while a tier is active — see
    app/gatekeeper.py's evaluate_gatekeeper() min_confidence_override
    param."""
    if tier == "tier1":
        return TIER1_CONFIDENCE_BONUS
    if tier in ("tier2", "tier3", "tier4"):
        return TIER2_CONFIDENCE_BONUS
    return 0.0


def compute_consecutive_losses(trade_history: list[PaperTrade]) -> int:
    """Walks backward from the most recently closed trade, counting
    consecutive real losses (pnl < 0) until a win or the history ends."""
    count = 0
    for trade in reversed(trade_history):
        if trade.pnl < 0:
            count += 1
        else:
            break
    return count


def compute_consecutive_wins(trade_history: list[PaperTrade]) -> int:
    """Prop-Firm Risk Intelligence Addendum, Piece 11b — Requirement 24's
    "consecutive wins" data point. Exact mirror of
    compute_consecutive_losses() above, walking backward until a real
    loss (pnl <= 0) or the history ends — a breakeven trade (pnl == 0)
    breaks a win streak the same honest way it fails to extend one."""
    count = 0
    for trade in reversed(trade_history):
        if trade.pnl > 0:
            count += 1
        else:
            break
    return count


def compute_losing_streak(state: TradingModeState, trade_history: list[PaperTrade]) -> tuple[LosingStreakRead, TradingModeState]:
    """`losing_streak_acknowledged` auto-clears the instant a real win
    breaks the streak (consecutive_losses hits 0) — a CEO's
    acknowledgment only ever silences the *current* streak; a fresh bad
    streak later re-pauses independently, never permanently disabled by
    one earlier click."""
    n = compute_consecutive_losses(trade_history)
    acknowledged = state.losing_streak_acknowledged if n > 0 else False
    pause_active = n >= state.losing_streak_pause_count and not acknowledged
    updated_state = state if acknowledged == state.losing_streak_acknowledged else state.model_copy(update={"losing_streak_acknowledged": acknowledged})
    read = LosingStreakRead(
        consecutiveLosses=n,
        pauseActive=pause_active,
        pauseThreshold=state.losing_streak_pause_count,
        suspendThreshold=state.losing_streak_suspend_count,
    )
    return read, updated_state


def acknowledge_losing_streak(state: TradingModeState) -> TradingModeState:
    """The CEO's real, explicit clear — never a silent auto-timer."""
    return state.model_copy(update={"losing_streak_acknowledged": True})


def build_circuit_breaker_tier_memory(previous_tier: DailyCircuitBreakerTier, new_tier: DailyCircuitBreakerTier, daily_pnl_pct: float, now_iso: str) -> MemoryRecord | None:
    if previous_tier == new_tier:
        return None
    severity = "escalated to" if _tier_rank(new_tier) > _tier_rank(previous_tier) else "eased to"
    return MemoryRecord(
        id=f"circuit-breaker-{new_tier}-{now_iso}",
        category="alert",
        title=f"Daily Circuit Breaker {severity} {new_tier.upper()}",
        body=f"Today's realized P&L is {daily_pnl_pct:+.1f}% — the Daily Circuit Breaker moved from {previous_tier} to {new_tier}.",
        timestamp=now_iso,
    )


def _tier_rank(tier: DailyCircuitBreakerTier) -> int:
    return {"none": 0, "tier1": 1, "tier2": 2, "tier3": 3, "tier4": 4}[tier]


def generate_recovery_briefing(
    trigger: str,
    portfolio: PaperPortfolio,
    discipline_reviews: list[DisciplineReview],
    sim_day: int,
    briefing_id: str,
) -> RecoveryBriefing:
    """Modeled on Chapter 72's generate_crisis_briefing() pattern — real
    recent stats, real links to Discipline Chamber reviews (matched by
    the real shared decision_id, never regenerated), a single new
    MemoryRecord-backed report, no new report series."""
    recent = trade_history_window(portfolio.trade_history, HEALTH_RECENT_TRADE_WINDOW)
    losses = [t for t in recent if t.pnl < 0]
    wins = [t for t in recent if t.pnl >= 0]
    recent_win_rate = round(len(wins) / len(recent) * 100, 1) if recent else 0.0
    recent_avg_loss_pct = round(sum(t.pnl_pct for t in losses) / len(losses), 2) if losses else 0.0
    largest_loss_pct = round(min((t.pnl_pct for t in recent), default=0.0), 2)
    days_since_profitable = _days_since_last_profitable_day(portfolio.trade_history, sim_day)
    recent_decision_ids = {t.decision_id for t in losses if t.decision_id}
    linked_reviews = [r.id for r in discipline_reviews if r.decision_id in recent_decision_ids]
    summary = (
        f"Trading halted after {trigger.replace('_', ' ')}. Over the last {len(recent)} closed trade(s): "
        f"{recent_win_rate:.0f}% win rate, average loss {recent_avg_loss_pct:+.1f}%, largest loss {largest_loss_pct:+.1f}%."
    )
    return RecoveryBriefing(
        id=briefing_id,
        trigger=trigger,  # type: ignore[arg-type]
        summary=summary,
        recentWinRate=recent_win_rate,
        recentAvgLossPct=recent_avg_loss_pct,
        largestLossPct=largest_loss_pct,
        daysSinceLastProfitableDay=days_since_profitable,
        linkedDisciplineReviewIds=linked_reviews,
        createdAt=_now_iso(),
    )


def trade_history_window(trade_history: list[PaperTrade], window: int) -> list[PaperTrade]:
    return trade_history[-window:]


def _days_since_last_profitable_day(trade_history: list[PaperTrade], sim_day: int) -> int | None:
    if not trade_history:
        return None
    by_day: dict[int, float] = {}
    for trade in trade_history:
        day = trade.closed_sim_minutes // 1440
        by_day[day] = by_day.get(day, 0.0) + trade.pnl
    profitable_days = sorted(day for day, pnl in by_day.items() if pnl > 0)
    if not profitable_days:
        return None
    return sim_day - profitable_days[-1]


def compute_trading_style_performance(trade_history: list[PaperTrade]) -> list[TradingStylePerformance]:
    """A real win-rate/P&L split by the tradingStyle tag — never claims
    independent capital pools (see this chapter's own Ownership
    section)."""
    results: list[TradingStylePerformance] = []
    for style in ("day", "swing"):
        trades = [t for t in trade_history if t.trading_style == style]
        if not trades:
            continue
        wins = sum(1 for t in trades if t.pnl >= 0)
        results.append(
            TradingStylePerformance(
                style=style,  # type: ignore[arg-type]
                tradeCount=len(trades),
                winRate=round(wins / len(trades) * 100, 1),
                totalPnl=round(sum(t.pnl for t in trades), 2),
                avgPnlPct=round(sum(t.pnl_pct for t in trades) / len(trades), 2),
            )
        )
    return results


def compute_trading_mode_health(trade_history: list[PaperTrade], sim_day: int) -> list[TradingModeHealthAssessment]:
    """Mirrors app/strategy_lab.py's compute_strategy_health() exact
    threshold shape and StrategyHealthStatus vocabulary, adapted to a
    trading style's own real PaperTrade history instead of a backtested
    Strategy's SimulationResult history."""
    del sim_day  # kept for signature symmetry with compute_strategy_health(); not needed for a pure trade-history read
    results: list[TradingModeHealthAssessment] = []
    for style in ("day", "swing"):
        style_trades = [t for t in trade_history if t.trading_style == style]
        if not style_trades:
            continue
        recent = style_trades[-HEALTH_RECENT_TRADE_WINDOW:]
        lifetime = style_trades
        recent_win_rate = sum(1 for t in recent if t.pnl >= 0) / len(recent) * 100
        lifetime_win_rate = sum(1 for t in lifetime if t.pnl >= 0) / len(lifetime) * 100
        recent_avg_return = sum(t.pnl_pct for t in recent) / len(recent)
        lifetime_avg_return = sum(t.pnl_pct for t in lifetime) / len(lifetime)
        recent_avg_drawdown = abs(min((t.pnl_pct for t in recent if t.pnl_pct < 0), default=0.0))
        return_delta = recent_avg_return - lifetime_avg_return

        trend: StrategyHealthTrend = "improving" if return_delta > 1.0 else "declining" if return_delta < -1.0 else "stable"
        reasoning = [
            f"Recent {len(recent)}-trade average return {recent_avg_return:+.1f}% vs. this style's own lifetime average {lifetime_avg_return:+.1f}% across {len(lifetime)} real trade(s)."
        ]

        status: StrategyHealthStatus
        if recent_win_rate < HEALTH_RETIRE_CANDIDATE_WIN_RATE or recent_avg_return <= HEALTH_RETIRE_CANDIDATE_RETURN_PCT:
            status = "retire_candidate"
            reasoning.append(f"Recent win rate {recent_win_rate:.0f}% / recent average return {recent_avg_return:+.1f}% is a real, serious warning sign.")
        elif recent_avg_drawdown > HEALTH_EXCELLENT_MAX_DRAWDOWN * 2:
            status = "critical"
            reasoning.append(f"Recent average loss magnitude {recent_avg_drawdown:.1f}% is a real, serious warning sign.")
        elif recent_win_rate < HEALTH_CRITICAL_WIN_RATE:
            status = "critical"
            reasoning.append(f"Recent win rate {recent_win_rate:.0f}% is critically low.")
        elif return_delta < HEALTH_DECLINING_RETURN_DELTA:
            status = "declining"
            reasoning.append(f"Recent performance has fallen {abs(return_delta):.1f} points below this style's own lifetime average.")
        elif return_delta < 0.0 and recent_win_rate < HEALTH_NEEDS_REVIEW_WIN_RATE:
            status = "needs_review"
            reasoning.append("Recent performance is below this style's own lifetime average and its recent win rate has slipped under 50%.")
        elif recent_win_rate >= HEALTH_EXCELLENT_WIN_RATE and return_delta >= 0.0 and recent_avg_drawdown <= HEALTH_EXCELLENT_MAX_DRAWDOWN:
            status = "excellent"
            reasoning.append("Recent performance matches or beats this style's own lifetime average with a strong win rate and low average loss.")
        elif recent_win_rate >= HEALTH_HEALTHY_WIN_RATE and return_delta >= HEALTH_HEALTHY_RETURN_DELTA:
            status = "healthy"
            reasoning.append("Recent performance is holding close to or above this style's own lifetime average.")
        else:
            status = "stable"
            reasoning.append("No strong real trend either way yet.")

        results.append(
            TradingModeHealthAssessment(
                style=style,  # type: ignore[arg-type]
                status=status,
                trend=trend,
                recentWinRate=round(recent_win_rate, 1),
                lifetimeWinRate=round(lifetime_win_rate, 1),
                recentAvgReturnPct=round(recent_avg_return, 2),
                lifetimeAvgReturnPct=round(lifetime_avg_return, 2),
                recentSampleSize=len(recent),
                lifetimeSampleSize=len(lifetime),
                reasoning=reasoning,
            )
        )
    return results


def compute_adaptive_mode_recommendation(reconciliation: RegimeReconciliation) -> AdaptiveModeRecommendation:
    """Read-only — exactly like Chapter 65's own posture field, never
    applied to TradingModeState automatically. See this chapter's own
    Decision Logic for the full disclosed table this mirrors."""
    now_iso = _now_iso()
    if reconciliation.quality_tier in ("poor", "avoid_trading"):
        return AdaptiveModeRecommendation(
            recommendedMode=None,
            reasoning=f"Market Quality is {reconciliation.quality_tier.replace('_', ' ')} — conditions this poor call for Chapter 72's Defensive Mode, not a trading-style pick.",
            confidencePct=reconciliation.confidence_pct,
            note="Consider activating Defensive Mode instead.",
            generatedAt=now_iso,
        )
    if reconciliation.posture == "opportunistic" and reconciliation.agreement == "aligned":
        return AdaptiveModeRecommendation(
            recommendedMode="swing_trading",
            reasoning=f"Both regime engines agree ({reconciliation.environment_label} / {reconciliation.intelligence_label}) with {reconciliation.confidence_pct:.0f}% confidence — a real, sustained directional read favors holding through it.",
            confidencePct=reconciliation.confidence_pct,
            generatedAt=now_iso,
        )
    if reconciliation.environment_regime == "sideways" and reconciliation.quality_tier not in ("poor", "avoid_trading"):
        return AdaptiveModeRecommendation(
            recommendedMode="day_trading",
            reasoning=f"The Market Environment engine reads sideways/range-bound conditions ({reconciliation.quality_tier.replace('_', ' ')} quality) — shorter holding periods have historically outperformed sustained directional bets in range-bound markets.",
            confidencePct=reconciliation.confidence_pct,
            generatedAt=now_iso,
        )
    if reconciliation.agreement == "diverging":
        return AdaptiveModeRecommendation(
            recommendedMode="hybrid",
            reasoning=f"The two real regime engines disagree ({reconciliation.environment_label} vs. {reconciliation.intelligence_label}) — diversifying across both holding-period disciplines hedges that real uncertainty.",
            confidencePct=reconciliation.confidence_pct,
            generatedAt=now_iso,
        )
    return AdaptiveModeRecommendation(
        recommendedMode=None,
        reasoning="No single real signal is strong enough right now to recommend a Trading Mode change.",
        confidencePct=reconciliation.confidence_pct,
        generatedAt=now_iso,
    )


def adaptive_recommendations_disabled_reading() -> AdaptiveModeRecommendation:
    """The real reading returned when the CEO has turned
    `adaptiveRecommendationsEnabled` off — no regime reconciliation is
    computed at all in this case (matches this chapter's own CEO
    Controls claim: "when off, no recommendation is computed"), never a
    stale/cached recommendation from before it was disabled."""
    return AdaptiveModeRecommendation(
        recommendedMode=None,
        reasoning="Adaptive Recommendations are turned off.",
        confidencePct=0.0,
        note="Turn Adaptive Recommendations back on in Trading Modes to see a live read.",
        generatedAt=_now_iso(),
    )
