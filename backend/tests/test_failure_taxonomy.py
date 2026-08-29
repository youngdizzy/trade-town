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
