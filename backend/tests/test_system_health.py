"""Covers app/system_health.py — CEO directive "TradeTown — Autonomous
Quant Company End-State 1.0," Phase 21 (Self-Monitoring). Every
assertion checks a real, honest read over already-persisted state —
never a fabricated "all systems normal" default.
"""
from __future__ import annotations

from app.champion_challenger import compare_champion_challenger
from app.schemas import ChampionRecord, DriftEvent, FactoryRunConfig, FactoryRunRecord
from app.state import default_state
from app.strategy_compiler import compile_strategy_text
from app.system_health import compute_system_health
from tests.test_trade_pipeline_health import _decision, _research_item

_CHAMPION_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
_CHALLENGER_TEXT = "Buy when price closes above the 50 EMA and RSI is above 70, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."


def _factory_run(run_id: str, *, created_at: str = "2024-01-01T00:00:00+00:00") -> FactoryRunRecord:
    return FactoryRunRecord(
        id=run_id,
        strategyFamily="Test Family",
        seedDefinitionId="def-1",
        seedDefinitionVersion=1,
        lineageId="lineage-1",
        config=FactoryRunConfig(maxGenerations=1, maxTotalBacktests=1, maxMutationsPerParent=1, maxIterationsPerFamily=1),
        candidates=[],
        generationsCompleted=1,
        candidatesGenerated=1,
        candidatesCompiled=1,
        candidatesBacktested=1,
        candidatesValidated=0,
        candidatesRejected=1,
        stopReason="max_generations_reached",
        createdAt=created_at,
    )


def _real_comparison(comparison_id: str, verdict: str):  # type: ignore[no-untyped-def]
    """One real ChallengerComparison from the real compare_champion_
    challenger(), verdict force-set for test determinism — same
    lightweight convention tests/test_champion_challenger.py's own
    TestPromoteChallenger and tests/test_autonomous_promotion.py already
    establish."""
    champion_definition = compile_strategy_text(name=f"SH Champion {comparison_id}", source_text=_CHAMPION_TEXT)
    challenger_definition = compile_strategy_text(name=f"SH Challenger {comparison_id}", source_text=_CHALLENGER_TEXT)
    comparison = compare_champion_challenger(
        champion_definition, challenger_definition, strategy_family="Test Family", hypothesis="h", proposed_by="quant",
        comparison_id=comparison_id, generated_at="2024-01-01T00:00:00+00:00", symbols=["AAPL"],
    )
    return comparison.model_copy(update={"verdict": verdict})


def _drift_event(severity: str) -> DriftEvent:
    return DriftEvent(
        id=f"drift-{severity}", createdAt="2024-01-01T00:00:00+00:00", simDay=1, strategyId="strat-1", strategyName="Test Strategy",
        category="performance", severity=severity, metric="test metric", sampleSize=20, evidence=["test evidence"], detail="test",  # type: ignore[arg-type]
    )


class TestComputeSystemHealth:
    def test_a_fresh_save_reports_honest_zero_state_not_fabricated_health(self) -> None:
        snapshot = compute_system_health(default_state())
        assert snapshot.research_completed_signals == 0
        assert snapshot.resolved_decisions == 0
        assert snapshot.research_to_decision_stall_detected is False  # no research completed yet, so no stall to report
        assert snapshot.factory_ever_run is False
        assert snapshot.factory_run_count == 0
        assert snapshot.last_factory_run_at is None
        assert snapshot.pending_autonomous_promotions == 0
        assert snapshot.champion_history_count == 0
        assert snapshot.concerning_drift_event_count == 0

    def test_research_completing_with_zero_decisions_is_a_real_detected_stall(self) -> None:
        state = default_state().model_copy(update={"research": [_research_item("completed")]})
        snapshot = compute_system_health(state)
        assert snapshot.research_completed_signals == 1
        assert snapshot.resolved_decisions == 0
        assert snapshot.research_to_decision_stall_detected is True

    def test_research_completing_with_a_real_decision_is_not_a_stall(self) -> None:
        state = default_state().model_copy(update={"research": [_research_item("completed")], "decisions": [_decision("no_trade")]})
        snapshot = compute_system_health(state)
        assert snapshot.research_to_decision_stall_detected is False

    def test_a_real_factory_run_is_honestly_reflected(self) -> None:
        run = _factory_run("run-1", created_at="2024-06-01T00:00:00+00:00")
        state = default_state().model_copy(update={"factory_runs": [run]})
        snapshot = compute_system_health(state)
        assert snapshot.factory_ever_run is True
        assert snapshot.factory_run_count == 1
        assert snapshot.last_factory_run_at == "2024-06-01T00:00:00+00:00"

    def test_last_factory_run_at_is_the_most_recent_real_run(self) -> None:
        first = _factory_run("run-1", created_at="2024-01-01T00:00:00+00:00")
        second = _factory_run("run-2", created_at="2024-06-01T00:00:00+00:00")
        state = default_state().model_copy(update={"factory_runs": [first, second]})
        snapshot = compute_system_health(state)
        assert snapshot.last_factory_run_at == "2024-06-01T00:00:00+00:00"

    def test_a_real_qualifying_unpromoted_comparison_is_counted_as_a_pending_anomaly(self) -> None:
        comparison = _real_comparison("cmp-1", "challenger_recommended")
        state = default_state().model_copy(update={"challenger_comparisons": [comparison]})
        snapshot = compute_system_health(state)
        assert snapshot.pending_autonomous_promotions == 1

    def test_an_already_promoted_comparison_is_never_counted_as_pending(self) -> None:
        comparison = _real_comparison("cmp-2", "challenger_recommended")
        record = ChampionRecord(
            id="champion-cmp-2", strategyFamily="Test Family", definitionId="chal-1", definitionVersion=1,
            sourceComparisonId="cmp-2", promotedBy="quant", reasoning="already handled", promotedAt="2024-01-01T00:00:00+00:00",
        )
        state = default_state().model_copy(update={"challenger_comparisons": [comparison], "champion_history": [record]})
        snapshot = compute_system_health(state)
        assert snapshot.pending_autonomous_promotions == 0
        assert snapshot.champion_history_count == 1

    def test_a_champion_retained_comparison_is_never_counted_as_pending(self) -> None:
        comparison = _real_comparison("cmp-3", "champion_retained")
        state = default_state().model_copy(update={"challenger_comparisons": [comparison]})
        snapshot = compute_system_health(state)
        assert snapshot.pending_autonomous_promotions == 0

    def test_watch_and_critical_drift_events_are_counted_as_concerning(self) -> None:
        state = default_state().model_copy(update={"drift_events": [_drift_event("normal"), _drift_event("watch"), _drift_event("critical")]})
        snapshot = compute_system_health(state)
        assert snapshot.concerning_drift_event_count == 2
        assert snapshot.total_drift_event_count == 3

    def test_last_persisted_at_reads_the_real_save_timestamp(self) -> None:
        state = default_state()
        snapshot = compute_system_health(state)
        assert snapshot.last_persisted_at == state.updated_at

    def test_sim_day_and_minute_read_the_real_time_state(self) -> None:
        state = default_state()
        state = state.model_copy(update={"time": state.time.model_copy(update={"day": 42, "hour": 3, "minute": 15})})
        snapshot = compute_system_health(state)
        assert snapshot.sim_day == 42
        assert snapshot.sim_minute == 3 * 60 + 15

    def test_computing_twice_never_mutates_the_input_state(self) -> None:
        state = default_state().model_copy(update={"research": [_research_item("completed")]})
        before = state.model_copy()
        compute_system_health(state)
        compute_system_health(state)
        assert state == before
