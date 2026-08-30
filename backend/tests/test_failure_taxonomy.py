"""Covers app/failure_taxonomy.py — CEO directive "TradeTown —
Statistical Validation + Research Failure Taxonomy," Part 2. Every
code assigned here traces to a real, hand-verifiable threshold
crossing — never a fabricated finding.
"""
from __future__ import annotations

from typing import get_args

from app.failure_taxonomy import FAILURE_CODE_METADATA, compute_top_failure_modes, derive_failure_codes
from app.schemas import FailedStrategyArchiveEntry, FailureCode, FailureCodeEntry

_CREATED_AT = "2024-01-01T00:00:00+00:00"

_MIN_TRADE_COUNT = 30
_MIN_PROFIT_FACTOR = 1.5
_MAX_AVG_DRAWDOWN = 20.0
_MIN_WIN_RATE = 55.0


def _derive(**overrides: object) -> list[FailureCodeEntry]:
    base: dict[str, object] = dict(
        trade_count=50,
        win_rate=60.0,
        profit_factor=2.0,
        avg_drawdown=10.0,
        avg_return=15.0,
        min_trade_count=_MIN_TRADE_COUNT,
        min_profit_factor=_MIN_PROFIT_FACTOR,
        max_avg_drawdown=_MAX_AVG_DRAWDOWN,
        min_win_rate=_MIN_WIN_RATE,
    )
    base.update(overrides)
    return derive_failure_codes(**base)  # type: ignore[arg-type]


class TestFailureCodeMetadataCompleteness:
    def test_every_real_directive_taxonomy_code_has_a_real_disclosed_severity_and_category(self) -> None:
        all_codes = set(get_args(FailureCode))
        assert set(FAILURE_CODE_METADATA.keys()) == all_codes

    def test_the_directives_own_two_worked_severity_examples_match_exactly(self) -> None:
        assert FAILURE_CODE_METADATA["insufficient_sample"][1] == "high"
        assert FAILURE_CODE_METADATA["benchmark_underperformance"][1] == "medium"

    def test_a_real_data_integrity_violation_reads_the_most_severe_real_tier(self) -> None:
        assert FAILURE_CODE_METADATA["lookahead_detected"][1] == "critical"
        assert FAILURE_CODE_METADATA["data_leakage"][1] == "critical"


class TestDeriveFailureCodes:
    def test_a_clean_real_track_record_carries_no_real_failure_codes(self) -> None:
        codes = _derive()
        assert codes == []

    def test_below_the_real_trade_count_bar_reads_insufficient_sample(self) -> None:
        codes = _derive(trade_count=_MIN_TRADE_COUNT - 1)
        assert any(c.code == "insufficient_sample" for c in codes)
        entry = next(c for c in codes if c.code == "insufficient_sample")
        assert entry.category == "statistical_failure"
        assert entry.severity == "high"
        assert str(_MIN_TRADE_COUNT - 1) in entry.evidence

    def test_at_exactly_the_real_trade_count_bar_reads_no_insufficient_sample_code(self) -> None:
        codes = _derive(trade_count=_MIN_TRADE_COUNT)
        assert not any(c.code == "insufficient_sample" for c in codes)

    def test_a_non_positive_real_return_reads_negative_net_return_never_low_profit_factor_too(self) -> None:
        codes = _derive(avg_return=-5.0, profit_factor=0.5)
        codes_set = {c.code for c in codes}
        assert "negative_net_return" in codes_set
        # Real, deliberate choice: a non-positive return is itself the whole real
        # story -- a redundant "and the profit factor was also low" is not double-filed.
        assert "low_profit_factor" not in codes_set

    def test_a_positive_return_with_a_real_low_profit_factor_reads_low_profit_factor(self) -> None:
        codes = _derive(avg_return=1.0, profit_factor=_MIN_PROFIT_FACTOR - 0.1)
        assert any(c.code == "low_profit_factor" for c in codes)

    def test_exceeding_the_real_drawdown_bar_reads_excessive_drawdown(self) -> None:
        codes = _derive(avg_drawdown=_MAX_AVG_DRAWDOWN + 0.1)
        entry = next(c for c in codes if c.code == "excessive_drawdown")
        assert entry.category == "risk_failure"
        assert entry.severity == "high"

    def test_a_low_win_rate_with_a_real_positive_return_reads_inconsistent_returns(self) -> None:
        codes = _derive(avg_return=5.0, win_rate=_MIN_WIN_RATE - 1.0)
        assert any(c.code == "inconsistent_returns" for c in codes)

    def test_a_low_win_rate_with_a_non_positive_return_does_not_double_file_inconsistent_returns(self) -> None:
        codes = _derive(avg_return=-1.0, win_rate=10.0)
        codes_set = {c.code for c in codes}
        assert "negative_net_return" in codes_set
        assert "inconsistent_returns" not in codes_set

    def test_multiple_real_failures_are_all_independently_reported(self) -> None:
        codes = _derive(trade_count=5, avg_return=-10.0, avg_drawdown=50.0)
        codes_set = {c.code for c in codes}
        assert {"insufficient_sample", "negative_net_return", "excessive_drawdown"} <= codes_set

    def test_zero_trades_and_zero_everything_is_a_real_pathological_case_handled_cleanly(self) -> None:
        codes = _derive(trade_count=0, win_rate=0.0, profit_factor=0.0, avg_drawdown=0.0, avg_return=0.0)
        codes_set = {c.code for c in codes}
        assert "insufficient_sample" in codes_set
        assert "negative_net_return" in codes_set  # avg_return=0.0 is non-positive

    def test_every_returned_entry_carries_real_nonempty_evidence(self) -> None:
        codes = _derive(trade_count=1, avg_return=-50.0, avg_drawdown=90.0)
        assert codes
        for entry in codes:
            assert entry.evidence.strip()


class TestLifecycleFailureCodes:
    """CEO directive "TradeTown — Research Engine Hardening +
    Self-Improvement Implementation Pass," Phase 2 — closes the real,
    confirmed "missing failure reason" gap the prior forensic audit
    proved reachable with executed code: a strategy clearing every
    numeric Hall-of-Fame bar could still retire with `failureCodes: []`
    because `qualifies_for_hall_of_fame` also requires `stage ==
    "approved"` and a real approved Founder Approval, neither of which
    `derive_failure_codes()` used to read at all."""

    def test_a_strategy_that_never_reached_approved_stage_gets_a_real_lifecycle_code(self) -> None:
        codes = _derive(strategy_stage="market_simulation")
        assert any(c.code == "never_reached_required_stage" for c in codes)
        entry = next(c for c in codes if c.code == "never_reached_required_stage")
        assert entry.category == "research_failure"
        assert entry.severity == "medium"
        assert "market simulation" in entry.evidence

    def test_a_strategy_at_the_approved_stage_gets_no_lifecycle_stage_code(self) -> None:
        codes = _derive(strategy_stage="approved")
        assert not any(c.code == "never_reached_required_stage" for c in codes)

    def test_no_strategy_stage_passed_means_the_check_is_honestly_skipped(self) -> None:
        codes = _derive()
        assert not any(c.code == "never_reached_required_stage" for c in codes)

    def test_a_real_founder_approval_rejection_gets_a_real_lifecycle_code(self) -> None:
        from app.schemas import StrategyFounderApproval

        rejection = StrategyFounderApproval(
            id="fa1", strategyId="s1", strategyName="x", simDay=10,
            evidenceSummary="Strong numeric track record", confidencePct=40.0,
            verdict="rejected", verdictReason="Confidence only reached 40/100, short of the Council's 60 bar.",
            createdAt=_CREATED_AT,
        )
        codes = _derive(latest_founder_approval=rejection)
        assert any(c.code == "founder_approval_rejected" for c in codes)
        entry = next(c for c in codes if c.code == "founder_approval_rejected")
        assert entry.category == "research_failure"
        assert "rejected" in entry.evidence

    def test_a_real_approved_founder_approval_gets_no_lifecycle_code(self) -> None:
        from app.schemas import StrategyFounderApproval

        approval = StrategyFounderApproval(
            id="fa1", strategyId="s1", strategyName="x", simDay=10,
            evidenceSummary="Strong numeric track record", confidencePct=90.0,
            verdict="approved", verdictReason="Approved.",
            createdAt=_CREATED_AT,
        )
        codes = _derive(latest_founder_approval=approval)
        assert not any(c.code == "founder_approval_rejected" for c in codes)

    def test_the_confirmed_audit_gap_is_closed_strong_metrics_plus_non_approved_stage_now_yields_a_real_code(self) -> None:
        """The exact scenario the prior forensic audit proved reachable
        with executed code: every numeric bar clears, but the strategy
        never reached "approved" — previously `failureCodes == []`."""
        codes = _derive(strategy_stage="paper_trading")
        assert codes != []
        assert any(c.code == "never_reached_required_stage" for c in codes)

    def test_both_lifecycle_codes_can_fire_together(self) -> None:
        from app.schemas import StrategyFounderApproval

        rejection = StrategyFounderApproval(
            id="fa1", strategyId="s1", strategyName="x", simDay=10,
            evidenceSummary="x", confidencePct=40.0, verdict="rejected", verdictReason="x", createdAt=_CREATED_AT,
        )
        codes = _derive(strategy_stage="paper_trading", latest_founder_approval=rejection)
        codes_set = {c.code for c in codes}
        assert {"never_reached_required_stage", "founder_approval_rejected"} <= codes_set


def _failed_entry(strategy_name: str, codes: list[FailureCodeEntry]) -> FailedStrategyArchiveEntry:
    return FailedStrategyArchiveEntry(
        id=f"failedarchive-{strategy_name}",
        strategyId=strategy_name,
        strategyName=strategy_name,
        createdBy="quant",
        failedAtStage="market_simulation",
        whatFailed=["x"],
        lessonsLearned=["x"],
        failureCodes=codes,
        retiredReason="x",
        simDay=1,
        createdAt=_CREATED_AT,
    )


class TestComputeTopFailureModes:
    def test_an_empty_archive_reads_an_honest_empty_list(self) -> None:
        assert compute_top_failure_modes([]) == []

    def test_entries_with_no_real_failure_codes_contribute_nothing(self) -> None:
        entries = [_failed_entry("Strategy A", []), _failed_entry("Strategy B", [])]
        assert compute_top_failure_modes(entries) == []

    def test_a_recurring_code_across_multiple_real_strategies_is_counted_correctly(self) -> None:
        drawdown_code = _derive(avg_drawdown=_MAX_AVG_DRAWDOWN + 5.0)
        entries = [_failed_entry(f"Strategy {i}", drawdown_code) for i in range(5)]
        modes = compute_top_failure_modes(entries)
        excessive = next(m for m in modes if m.code == "excessive_drawdown")
        assert excessive.occurrence_count == 5
        assert excessive.category == "risk_failure"
        assert excessive.severity == "high"

    def test_the_most_common_real_failure_mode_sorts_first(self) -> None:
        common_code = _derive(avg_drawdown=_MAX_AVG_DRAWDOWN + 5.0)
        rare_code = _derive(trade_count=1)
        entries = [_failed_entry(f"Common {i}", common_code) for i in range(4)] + [_failed_entry("Rare", rare_code)]
        modes = compute_top_failure_modes(entries)
        assert modes[0].code == "excessive_drawdown"
        assert modes[0].occurrence_count == 4

    def test_example_strategy_names_are_capped_and_real(self) -> None:
        code = _derive(avg_drawdown=_MAX_AVG_DRAWDOWN + 5.0)
        entries = [_failed_entry(f"Strategy {i}", code) for i in range(10)]
        modes = compute_top_failure_modes(entries, max_examples_per_mode=2)
        excessive = next(m for m in modes if m.code == "excessive_drawdown")
        assert len(excessive.example_strategy_names) == 2
        assert excessive.occurrence_count == 10

    def test_one_real_strategy_with_a_code_appearing_twice_still_counts_once(self) -> None:
        code = _derive(avg_drawdown=_MAX_AVG_DRAWDOWN + 5.0)
        duplicated = code + code  # a defensive, unrealistic-but-possible double-tag
        entries = [_failed_entry("Strategy A", duplicated)]
        modes = compute_top_failure_modes(entries)
        excessive = next(m for m in modes if m.code == "excessive_drawdown")
        assert excessive.occurrence_count == 1


class TestFindSimilarFailedStrategies:
    """CEO directive "TradeTown — Research Engine Hardening +
    Self-Improvement Implementation Pass," Phase 3 — closes the real,
    confirmed gap the prior forensic audit proved: research memory
    checked prior experiments but never the Failed Strategy Archive at
    all. Never auto-rejects — every test here only proves matches are
    found/surfaced, never that filing is blocked."""

    def test_the_directives_own_test_scenario_a_materially_similar_failed_strategy_is_surfaced(self) -> None:
        from app.failure_taxonomy import find_similar_failed_strategies

        code = _derive(avg_drawdown=_MAX_AVG_DRAWDOWN + 20.0)
        archive = [_failed_entry("50 EMA Breakout Momentum", code)]
        matches = find_similar_failed_strategies(archive, hypothesis="50 EMA breakout momentum trend follower", strategy_name="50 EMA Breakout Momentum V2")
        assert len(matches) == 1
        assert matches[0].strategy_name == "50 EMA Breakout Momentum"
        assert matches[0].failure_codes == ["excessive_drawdown"]
        assert matches[0].overlap_score > 0

    def test_an_unrelated_hypothesis_finds_no_match(self) -> None:
        from app.failure_taxonomy import find_similar_failed_strategies

        code = _derive(avg_drawdown=_MAX_AVG_DRAWDOWN + 20.0)
        archive = [_failed_entry("Value Fundamentals Screener", code)]
        matches = find_similar_failed_strategies(archive, hypothesis="News sentiment reaction on breaking headlines", strategy_name="News Momentum Scanner")
        assert matches == []

    def test_an_empty_archive_finds_no_match_never_a_crash(self) -> None:
        from app.failure_taxonomy import find_similar_failed_strategies

        assert find_similar_failed_strategies([], hypothesis="anything", strategy_name="anything") == []

    def test_matches_are_capped_at_max_matches(self) -> None:
        from app.failure_taxonomy import find_similar_failed_strategies

        code = _derive(avg_drawdown=_MAX_AVG_DRAWDOWN + 20.0)
        archive = [_failed_entry(f"Momentum Breakout Strategy {i}", code) for i in range(10)]
        matches = find_similar_failed_strategies(archive, hypothesis="momentum breakout strategy", strategy_name="Momentum Breakout Strategy New", max_matches=3)
        assert len(matches) == 3

    def test_similarity_never_blocks_the_caller_purely_informational(self) -> None:
        """The directive's own explicit rule: 'Do NOT automatically
        reject a strategy merely because something similar failed.'
        This function only ever returns evidence — it has no reject
        path, no exception, no boolean gate at all."""
        from app.failure_taxonomy import find_similar_failed_strategies

        code = _derive(avg_drawdown=_MAX_AVG_DRAWDOWN + 20.0)
        archive = [_failed_entry("Exact Same Strategy Name", code)]
        matches = find_similar_failed_strategies(archive, hypothesis="exact same strategy name", strategy_name="Exact Same Strategy Name")
        assert isinstance(matches, list)  # a real list of evidence, never a raised exception or a bool
