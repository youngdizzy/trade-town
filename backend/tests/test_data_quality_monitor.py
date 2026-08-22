"""Covers app/data_quality_monitor.py — CEO directive "Complete Trade
Provenance," Part 18. Four real, checkable categories; this module only
ever reports, never repairs anything it finds.
"""
from __future__ import annotations

from app.data_quality_monitor import compute_data_quality_monitor
from app.schemas import CeoDecisionRecord, PaperTrade, Strategy


def _trade(*, trade_id: str = "trade-1", opened_sim_minutes: int = 0, closed_sim_minutes: int = 30) -> PaperTrade:
    return PaperTrade(
        id=trade_id,
        symbol="AAPL",
        side="buy",
        quantity=1.0,
        entryPrice=100.0,
        exitPrice=105.0,
        pnl=5.0,
        pnlPct=5.0,
        durationMinutes=30,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        supportingAgents=["scout"],
        opposingAgents=[],
        openedAt="2024-01-01T00:00:00+00:00",
        closedAt="2024-01-01T00:00:00+00:00",
        openedSimMinutes=opened_sim_minutes,
        closedSimMinutes=closed_sim_minutes,
    )


def _ceo_decision(
    *,
    decision_id: str = "ceo-1",
    ceo_decision: str = "buy",
    strategy_id: str | None = None,
    decision_session: str | None = "new_york",
    strategy_compiled_definition_id: str | None = None,
) -> CeoDecisionRecord:
    return CeoDecisionRecord(
        id=decision_id,
        proposalId="proposal-1",
        symbol="AAPL",
        category="stock",
        aiRecommendation="buy",
        ceoDecision=ceo_decision,  # type: ignore[arg-type]
        agreedWithAi=True,
        decisionId="decision-1",
        strategyId=strategy_id,
        decisionSession=decision_session,  # type: ignore[arg-type]
        strategyCompiledDefinitionId=strategy_compiled_definition_id,
        createdAt="2024-01-01T00:00:00+00:00",
    )


def _strategy(*, strategy_id: str = "strategy-momentum") -> Strategy:
    return Strategy(
        id=strategy_id,
        name="Momentum Breakout",
        description="test",
        createdBy="echo",  # type: ignore[arg-type]
        focusCategory="stock",  # type: ignore[arg-type]
        createdAt="2024-01-01T00:00:00+00:00",
    )


class TestComputeDataQualityMonitor:
    def test_no_issues_on_clean_data_reports_zero(self) -> None:
        trade = _trade()
        decision = _ceo_decision()
        monitor = compute_data_quality_monitor([trade], [decision], [])
        assert monitor.issues == []
        assert monitor.total_issue_count == 0

    def test_impossible_timestamp_is_detected(self) -> None:
        trade = _trade(trade_id="broken", opened_sim_minutes=100, closed_sim_minutes=50)
        monitor = compute_data_quality_monitor([trade], [], [])
        issue = next(i for i in monitor.issues if i.category == "impossible_timestamps")
        assert issue.count == 1
        assert "broken" in issue.example_ids

    def test_a_normal_trade_is_never_flagged_as_impossible(self) -> None:
        trade = _trade(opened_sim_minutes=0, closed_sim_minutes=30)
        monitor = compute_data_quality_monitor([trade], [], [])
        assert not any(i.category == "impossible_timestamps" for i in monitor.issues)

    def test_dangling_strategy_reference_is_detected(self) -> None:
        decision = _ceo_decision(strategy_id="strategy-does-not-exist")
        real_strategy = _strategy(strategy_id="strategy-momentum")
        monitor = compute_data_quality_monitor([], [decision], [real_strategy])
        issue = next(i for i in monitor.issues if i.category == "dangling_strategy_reference")
        assert issue.count == 1

    def test_a_real_matching_strategy_reference_is_never_flagged(self) -> None:
        decision = _ceo_decision(strategy_id="strategy-momentum")
        real_strategy = _strategy(strategy_id="strategy-momentum")
        monitor = compute_data_quality_monitor([], [decision], [real_strategy])
        assert not any(i.category == "dangling_strategy_reference" for i in monitor.issues)

    def test_no_strategy_selected_is_never_a_dangling_reference(self) -> None:
        # strategy_id=None is the honest majority (Part 1/2), never a
        # data-quality issue in itself.
        decision = _ceo_decision(strategy_id=None)
        monitor = compute_data_quality_monitor([], [decision], [])
        assert not any(i.category == "dangling_strategy_reference" for i in monitor.issues)

    def test_missing_decision_time_context_on_a_real_buy_is_detected(self) -> None:
        decision = _ceo_decision(ceo_decision="buy", decision_session=None)
        monitor = compute_data_quality_monitor([], [decision], [])
        issue = next(i for i in monitor.issues if i.category == "missing_decision_time_context")
        assert issue.count == 1

    def test_a_wait_decision_is_never_flagged_for_missing_context(self) -> None:
        # Part 8 sets decisionSession unconditionally for every REAL
        # decision -- but a "wait" with no session recorded is still not
        # a strategy-attribution-relevant issue for THIS category's
        # framing (which only inspects real buy/sell decisions).
        decision = _ceo_decision(ceo_decision="wait", decision_session=None)
        monitor = compute_data_quality_monitor([], [decision], [])
        assert not any(i.category == "missing_decision_time_context" for i in monitor.issues)

    def test_missing_strategy_rule_snapshot_is_detected(self) -> None:
        decision = _ceo_decision(strategy_id="strategy-momentum", strategy_compiled_definition_id=None)
        monitor = compute_data_quality_monitor([], [decision], [])
        issue = next(i for i in monitor.issues if i.category == "missing_strategy_rule_snapshot")
        assert issue.count == 1

    def test_a_real_compiled_definition_id_is_never_flagged_as_missing(self) -> None:
        decision = _ceo_decision(strategy_id="strategy-momentum", strategy_compiled_definition_id="strategy-momentum")
        monitor = compute_data_quality_monitor([], [decision], [])
        assert not any(i.category == "missing_strategy_rule_snapshot" for i in monitor.issues)

    def test_example_ids_are_capped(self) -> None:
        trades = [_trade(trade_id=f"broken-{i}", opened_sim_minutes=100, closed_sim_minutes=50) for i in range(10)]
        monitor = compute_data_quality_monitor(trades, [], [])
        issue = next(i for i in monitor.issues if i.category == "impossible_timestamps")
        assert issue.count == 10
        assert len(issue.example_ids) == 5

    def test_total_issue_count_sums_across_categories(self) -> None:
        trade = _trade(trade_id="broken", opened_sim_minutes=100, closed_sim_minutes=50)
        # This one decision genuinely trips two real categories at once
        # (a dangling reference AND, honestly, no compiled-rule snapshot
        # for a strategy that doesn't even exist) -- both real, both
        # counted, not collapsed into one.
        decision = _ceo_decision(strategy_id="strategy-does-not-exist")
        monitor = compute_data_quality_monitor([trade], [decision], [])
        assert monitor.total_issue_count == 3
        assert {i.category for i in monitor.issues} == {
            "impossible_timestamps",
            "dangling_strategy_reference",
            "missing_strategy_rule_snapshot",
        }

    def test_this_module_never_mutates_its_inputs(self) -> None:
        trade = _trade()
        decision = _ceo_decision()
        trades_before, decisions_before = [trade], [decision]
        compute_data_quality_monitor(trades_before, decisions_before, [])
        assert trades_before == [trade]
        assert decisions_before == [decision]
