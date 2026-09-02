"""Covers app/strategy_drift.py — the Drift Detection Engine. Every
scenario reuses app/performance_attribution.py's own real
compute_strategy_degradation() signals (never a second computation);
these tests exercise the category-routing/severity-diffing layer this
module actually adds.
"""
from __future__ import annotations

from app.schemas import DecisionVaultEntry, MarketEnvironmentState, PaperTrade, Strategy
from app.strategy_drift import REGIME_LOOKBACK_SIM_MINUTES, evaluate_strategy_drift


def _strategy(strategy_id: str = "s1") -> Strategy:
    return Strategy(id=strategy_id, name="Test Strategy", description="d", createdBy="atlas", focusCategory="stock", createdAt="2026-01-01T00:00:00+00:00")


def _trade(i: int, pnl: float, *, entry_slippage: float = 0.0) -> PaperTrade:
    return PaperTrade(
        id=f"t{i}",
        symbol="AAPL",
        side="buy",
        quantity=1.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl,
        pnl=pnl,
        pnlPct=pnl,
        durationMinutes=30,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        supportingAgents=["scout"],
        openedAt="2026-01-01T00:00:00+00:00",
        closedAt="2026-01-01T00:30:00+00:00",
        openedSimMinutes=i * 100,
        closedSimMinutes=i * 100 + 30,
        decisionId=f"decision-p{i}",
        entrySlippageBps=entry_slippage,
    )


def _vault(strategy_id: str, count: int) -> list[DecisionVaultEntry]:
    return [DecisionVaultEntry.model_construct(id=f"v{i}", trade_id=f"t{i}", strategy_id=strategy_id) for i in range(count)]


def _market_environment(timeline: list | None = None) -> MarketEnvironmentState:
    return MarketEnvironmentState(current="sideways", label="Sideways", detail="d", changedSimMinutes=0, updatedAt="2026-01-01T00:00:00+00:00", timeline=timeline or [])


def test_insufficient_evidence_below_min_sample_never_fabricates_a_real_severity() -> None:
    strategy = _strategy()
    trades = [_trade(0, 5.0), _trade(1, -3.0)]  # below MIN_SYMBOL_SAMPLE_FOR_VERDICT (3)
    events = evaluate_strategy_drift(
        strategies=[strategy], trade_history=trades, decision_vault=_vault("s1", 2), failure_classifications=[],
        market_environment=_market_environment(), now_sim_minutes=1000, sim_day=1, previous_severity={},
    )
    assert len(events) == 4  # one per category
    for event in events:
        assert event.severity == "insufficient_evidence"
        assert event.sample_size == 2


def test_loss_clustering_produces_a_real_critical_performance_event() -> None:
    strategy = _strategy()
    trades = [_trade(i, -5.0) for i in range(5)]  # 5 consecutive losses -> critical
    events = evaluate_strategy_drift(
        strategies=[strategy], trade_history=trades, decision_vault=_vault("s1", 5), failure_classifications=[],
        market_environment=_market_environment(), now_sim_minutes=1000, sim_day=1, previous_severity={},
    )
    perf = next(e for e in events if e.category == "performance")
    assert perf.severity == "critical"
    assert "Loss clustering" in perf.metric
    other_categories = {e.category for e in events if e.category != "performance"}
    assert other_categories == {"execution", "risk", "regime"}
    for event in events:
        if event.category != "performance":
            assert event.severity == "normal"


def test_execution_degradation_routes_to_execution_category_only() -> None:
    strategy = _strategy()
    # Lifetime trades with low slippage, recent trades with much higher slippage.
    lifetime = [_trade(i, 1.0, entry_slippage=2.0) for i in range(10)]
    recent = [_trade(i, 1.0, entry_slippage=50.0) for i in range(10, 13)]
    trades = lifetime + recent
    events = evaluate_strategy_drift(
        strategies=[strategy], trade_history=trades, decision_vault=_vault("s1", 13), failure_classifications=[],
        market_environment=_market_environment(), now_sim_minutes=2000, sim_day=1, previous_severity={},
    )
    execution_event = next(e for e in events if e.category == "execution")
    assert execution_event.severity in ("watch", "critical")
    assert "Execution degradation" in execution_event.metric
    performance_event = next(e for e in events if e.category == "performance")
    assert performance_event.severity == "normal"


def test_no_event_emitted_when_severity_unchanged_from_previous() -> None:
    strategy = _strategy()
    trades = [_trade(i, -5.0) for i in range(5)]
    previous = {("s1", "performance"): "critical", ("s1", "execution"): "normal", ("s1", "risk"): "normal", ("s1", "regime"): "normal"}
    events = evaluate_strategy_drift(
        strategies=[strategy], trade_history=trades, decision_vault=_vault("s1", 5), failure_classifications=[],
        market_environment=_market_environment(), now_sim_minutes=1000, sim_day=1, previous_severity=previous,
    )
    assert events == []


def test_severity_change_from_critical_back_to_normal_is_reported() -> None:
    strategy = _strategy()
    trades = [_trade(i, 5.0) for i in range(5)]  # all wins now -> normal_variation
    previous = {("s1", "performance"): "critical", ("s1", "execution"): "normal", ("s1", "risk"): "normal", ("s1", "regime"): "normal"}
    events = evaluate_strategy_drift(
        strategies=[strategy], trade_history=trades, decision_vault=_vault("s1", 5), failure_classifications=[],
        market_environment=_market_environment(), now_sim_minutes=1000, sim_day=1, previous_severity=previous,
    )
    perf = next(e for e in events if e.category == "performance")
    assert perf.severity == "normal"
    assert perf.previous_severity == "critical"


def test_regime_changed_flag_only_set_for_regime_category() -> None:
    from app.schemas import MarketEnvironmentEntry

    strategy = _strategy()
    trades = [_trade(i, -5.0) for i in range(5)]
    recent_change = MarketEnvironmentEntry(id="e1", regime="high_volatility", label="High Vol", detail="d", simMinutes=900, createdAt="2026-01-01T00:00:00+00:00")
    me = _market_environment(timeline=[recent_change])
    events = evaluate_strategy_drift(
        strategies=[strategy], trade_history=trades, decision_vault=_vault("s1", 5), failure_classifications=[],
        market_environment=me, now_sim_minutes=1000, sim_day=1, previous_severity={},
    )
    for event in events:
        if event.category == "regime":
            assert event.regime_changed is True
        else:
            assert event.regime_changed is False


def test_regime_changed_false_when_no_recent_timeline_entry() -> None:
    from app.schemas import MarketEnvironmentEntry

    strategy = _strategy()
    trades = [_trade(i, -5.0) for i in range(5)]
    old_change = MarketEnvironmentEntry(id="e1", regime="high_volatility", label="High Vol", detail="d", simMinutes=100, createdAt="2026-01-01T00:00:00+00:00")
    me = _market_environment(timeline=[old_change])
    events = evaluate_strategy_drift(
        strategies=[strategy], trade_history=trades, decision_vault=_vault("s1", 5), failure_classifications=[],
        market_environment=me, now_sim_minutes=100 + REGIME_LOOKBACK_SIM_MINUTES + 1, sim_day=1, previous_severity={},
    )
    regime_event = next(e for e in events if e.category == "regime")
    assert regime_event.regime_changed is False


def test_multiple_strategies_evaluated_independently() -> None:
    strategy_a = _strategy("s1")
    strategy_b = _strategy("s2")
    trades = [_trade(i, -5.0) for i in range(5)] + [_trade(i, 5.0) for i in range(5, 10)]
    vault = _vault("s1", 5) + [DecisionVaultEntry.model_construct(id=f"v{i}", trade_id=f"t{i}", strategy_id="s2") for i in range(5, 10)]
    events = evaluate_strategy_drift(
        strategies=[strategy_a, strategy_b], trade_history=trades, decision_vault=vault, failure_classifications=[],
        market_environment=_market_environment(), now_sim_minutes=2000, sim_day=1, previous_severity={},
    )
    s1_perf = next(e for e in events if e.strategy_id == "s1" and e.category == "performance")
    s2_perf = next(e for e in events if e.strategy_id == "s2" and e.category == "performance")
    assert s1_perf.severity == "critical"
    assert s2_perf.severity == "normal"


def test_deterministic_same_inputs_same_events() -> None:
    strategy = _strategy()
    trades = [_trade(i, -5.0) for i in range(5)]
    kwargs = dict(
        strategies=[strategy], trade_history=trades, decision_vault=_vault("s1", 5), failure_classifications=[],
        market_environment=_market_environment(), now_sim_minutes=1000, sim_day=1, previous_severity={},
    )
    events_a = evaluate_strategy_drift(**kwargs)  # type: ignore[arg-type]
    events_b = evaluate_strategy_drift(**kwargs)  # type: ignore[arg-type]
    assert [(e.strategy_id, e.category, e.severity) for e in events_a] == [(e.strategy_id, e.category, e.severity) for e in events_b]
