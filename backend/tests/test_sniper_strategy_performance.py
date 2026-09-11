"""Covers app/sniper_strategy_performance.py — CEO directive "TradeTown
— Sniper Per-Strategy Performance Observability 1.0." Pure, read-only
aggregation over already-persisted SniperTrade records — these tests
never touch SniperRiskState, never call evaluate_entry_firewall(),
never mutate a trade or a strategy definition."""
from __future__ import annotations

import math

from app.schemas import SniperStrategyDefinition, SniperTrade
from app.sniper_strategy_performance import compute_sniper_strategy_performance

_NOW = "2026-01-01T00:00:00+00:00"


def _trade(
    trade_id: str,
    pnl_sol: float,
    *,
    strategy_id: str = "memecoin-sniper",
    strategy_name: str = "Memecoin Sniper — Liquidity/Momentum Discovery",
    strategy_version_id: str | None = "1",
    strategy_version_status: str = "versioned",
) -> SniperTrade:
    return SniperTrade(
        id=trade_id,
        mint="m",
        symbol="X",
        openedAt=_NOW,
        closedAt=_NOW,
        entryPrice=1.0,
        exitPrice=1.0 + pnl_sol,
        stopPrice=0.8,
        targetPrice=1.5,
        sizeSol=1.0,
        riskSol=0.1,
        rMultiple=pnl_sol / 0.1 if pnl_sol else 0.0,
        pnlSol=pnl_sol,
        maxFavorableExcursionPct=0.0,
        maxAdverseExcursionPct=0.0,
        holdTimeSeconds=10.0,
        exitReason="take_profit" if pnl_sol > 0 else "stop_loss",
        failureCodes=[],
        thesis="x",
        thesisValidated=pnl_sol > 0,
        strategyId=strategy_id,
        strategyName=strategy_name,
        strategyVersionId=strategy_version_id,
        strategyVersionStatus=strategy_version_status,  # type: ignore[arg-type]
    )


def _strategy(strategy_id: str, *, status: str = "enabled", family: str = "liquidity_momentum", version: str = "1") -> SniperStrategyDefinition:
    return SniperStrategyDefinition(id=strategy_id, name=f"Name for {strategy_id}", family=family, version=version, status=status, provenance="hardcoded", createdAt=_NOW)  # type: ignore[arg-type]


def _read_for(summary, strategy_id: str):
    return next(r for r in summary.reads if r.strategy_id == strategy_id)


class TestCoreAggregation:
    def test_zero_trades_yields_null_rate_and_average_fields_not_zero(self) -> None:
        strategies = [_strategy("memecoin-sniper")]
        summary = compute_sniper_strategy_performance([], strategies)
        read = _read_for(summary, "memecoin-sniper")
        assert read.closed_trade_count == 0
        assert read.win_count == 0
        assert read.loss_count == 0
        assert read.win_rate_pct is None
        assert read.average_realized_pnl_sol is None
        assert read.average_winning_trade_sol is None
        assert read.average_losing_trade_sol is None
        assert read.observed_expectancy_per_closed_trade_sol is None
        # total_realized_pnl_sol is a real, valid zero — never null.
        assert read.total_realized_pnl_sol == 0.0

    def test_one_winning_trade(self) -> None:
        trades = [_trade("t1", 0.5)]
        summary = compute_sniper_strategy_performance(trades, [_strategy("memecoin-sniper")])
        read = _read_for(summary, "memecoin-sniper")
        assert read.closed_trade_count == 1
        assert read.win_count == 1
        assert read.loss_count == 0
        assert read.win_rate_pct == 100.0
        assert read.total_realized_pnl_sol == 0.5
        assert read.average_winning_trade_sol == 0.5
        assert read.average_losing_trade_sol is None

    def test_one_losing_trade(self) -> None:
        trades = [_trade("t1", -0.3)]
        summary = compute_sniper_strategy_performance(trades, [_strategy("memecoin-sniper")])
        read = _read_for(summary, "memecoin-sniper")
        assert read.win_count == 0
        assert read.loss_count == 1
        assert read.win_rate_pct == 0.0
        assert read.average_winning_trade_sol is None
        assert read.average_losing_trade_sol == -0.3

    def test_break_even_trade_counts_as_a_loss_matching_codebase_convention(self) -> None:
        """WIN = pnl_sol > 0; LOSS = pnl_sol <= 0 — the same boundary
        app/portfolio.py::close_position() and
        app/performance_attribution.py already use codebase-wide."""
        trades = [_trade("t1", 0.0)]
        summary = compute_sniper_strategy_performance(trades, [_strategy("memecoin-sniper")])
        read = _read_for(summary, "memecoin-sniper")
        assert read.win_count == 0
        assert read.loss_count == 1
        assert read.average_losing_trade_sol == 0.0

    def test_multiple_strategies_each_get_their_own_row(self) -> None:
        trades = [_trade("t1", 0.5, strategy_id="memecoin-sniper"), _trade("t2", -0.2, strategy_id="memecoin-sniper-whale-confirmation")]
        strategies = [_strategy("memecoin-sniper"), _strategy("memecoin-sniper-whale-confirmation", family="whale_confirmation")]
        summary = compute_sniper_strategy_performance(trades, strategies)
        assert len(summary.reads) == 2
        assert _read_for(summary, "memecoin-sniper").closed_trade_count == 1
        assert _read_for(summary, "memecoin-sniper-whale-confirmation").closed_trade_count == 1

    def test_mixed_outcomes_and_manual_metric_verification(self) -> None:
        """Directive Section 19's own worked example: 3 closed trades,
        2 wins, 1 loss, explicit known P&L, hand-computed expected
        metrics."""
        trades = [_trade("t1", 1.0), _trade("t2", 0.5), _trade("t3", -0.3)]
        summary = compute_sniper_strategy_performance(trades, [_strategy("memecoin-sniper")])
        read = _read_for(summary, "memecoin-sniper")
        assert read.closed_trade_count == 3
        assert read.win_count == 2
        assert read.loss_count == 1
        assert read.win_rate_pct == round(2 / 3 * 100.0, 1)
        assert read.total_realized_pnl_sol == round(1.0 + 0.5 - 0.3, 6)
        assert read.average_realized_pnl_sol == round((1.0 + 0.5 - 0.3) / 3, 6)
        assert read.average_winning_trade_sol == round((1.0 + 0.5) / 2, 6)
        assert read.average_losing_trade_sol == -0.3
        # expectancy = win_share*avg_winner + loss_share*avg_loser
        expected_expectancy = round((2 / 3) * 0.75 + (1 / 3) * -0.3, 6)
        assert read.observed_expectancy_per_closed_trade_sol == expected_expectancy
        # Algebraically identical to the simple average under this
        # partition — this module's own documented relationship.
        assert read.observed_expectancy_per_closed_trade_sol == read.average_realized_pnl_sol


class TestAttribution:
    def test_strategy_a_and_b_attribution_are_independent(self) -> None:
        """Directive Section 19's own example: A has 3 trades (2W/1L),
        B has 2 trades (1W/1L) — proves A's metrics != B's metrics and
        attribution is based on the historical strategy_id."""
        a_trades = [_trade("a1", 1.0, strategy_id="memecoin-sniper"), _trade("a2", 0.5, strategy_id="memecoin-sniper"), _trade("a3", -0.4, strategy_id="memecoin-sniper")]
        b_trades = [_trade("b1", 0.3, strategy_id="memecoin-sniper-whale-confirmation"), _trade("b2", -0.6, strategy_id="memecoin-sniper-whale-confirmation")]
        strategies = [_strategy("memecoin-sniper"), _strategy("memecoin-sniper-whale-confirmation", family="whale_confirmation")]
        summary = compute_sniper_strategy_performance(a_trades + b_trades, strategies)
        a_read = _read_for(summary, "memecoin-sniper")
        b_read = _read_for(summary, "memecoin-sniper-whale-confirmation")
        assert a_read.closed_trade_count == 3
        assert b_read.closed_trade_count == 2
        assert a_read.total_realized_pnl_sol != b_read.total_realized_pnl_sol
        assert a_read.win_rate_pct != b_read.win_rate_pct

    def test_id_is_the_canonical_grouping_key_not_name(self) -> None:
        """Two trades share the same strategy_id but carry different
        historical strategy_name values (a real possible scenario if a
        display name is ever edited) — they must still be grouped
        together as ONE strategy."""
        trades = [
            _trade("t1", 0.5, strategy_id="memecoin-sniper", strategy_name="Old Display Name"),
            _trade("t2", 0.3, strategy_id="memecoin-sniper", strategy_name="New Display Name"),
        ]
        summary = compute_sniper_strategy_performance(trades, [_strategy("memecoin-sniper")])
        assert len(summary.reads) == 1
        assert _read_for(summary, "memecoin-sniper").closed_trade_count == 2

    def test_name_is_not_used_as_a_grouping_key(self) -> None:
        """Two DIFFERENT strategy ids that happen to share the same
        display name must NOT be merged into one row."""
        trades = [
            _trade("t1", 0.5, strategy_id="strategy-a", strategy_name="Same Name"),
            _trade("t2", 0.3, strategy_id="strategy-b", strategy_name="Same Name"),
        ]
        summary = compute_sniper_strategy_performance(trades, [])
        assert len(summary.reads) == 2
        assert {r.strategy_id for r in summary.reads} == {"strategy-a", "strategy-b"}

    def test_historical_version_is_preserved_not_collapsed_to_current_registry_version(self) -> None:
        """Directive Section 9/20 — a strategy that has run under two
        different versions historically must show both, never silently
        implying every trade ran under whichever version is registered
        today."""
        trades = [
            _trade("t1", 0.5, strategy_id="memecoin-sniper-whale-confirmation", strategy_version_id="1"),
            _trade("t2", 0.3, strategy_id="memecoin-sniper-whale-confirmation", strategy_version_id="1"),
            _trade("t3", -0.2, strategy_id="memecoin-sniper-whale-confirmation", strategy_version_id="2"),
        ]
        # Registry now reports version "2" — but the report must not
        # rewrite the v1 trades' own historical version.
        strategies = [_strategy("memecoin-sniper-whale-confirmation", family="whale_confirmation", version="2")]
        summary = compute_sniper_strategy_performance(trades, strategies)
        read = _read_for(summary, "memecoin-sniper-whale-confirmation")
        assert read.closed_trade_count == 3
        assert read.distinct_strategy_versions_observed == ["1", "2"]

    def test_unknown_legacy_identity_is_handled_honestly_not_fabricated(self) -> None:
        """Every real SniperTrade always carries a real, non-null
        strategy_id (schema default `SNIPER_STRATEGY_ID` — accurate for
        a trade closed before the registry existed, since that really
        was this engine's only implementation at the time). There is no
        actual "missing identity" case to fabricate a policy for —
        proven here directly against the schema's own real default."""
        trade = SniperTrade(
            id="legacy1", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=1.1,
            sizeSol=1.0, riskSol=0.1, rMultiple=1.0, pnlSol=0.1, maxFavorableExcursionPct=0.0,
            maxAdverseExcursionPct=0.0, holdTimeSeconds=10.0, exitReason="take_profit", failureCodes=[],
            thesis="x", thesisValidated=True,
            # strategyId/strategyVersionId intentionally omitted — this
            # simulates a trade closed before strategy identity fields
            # existed, relying purely on the schema's own real default.
        )  # type: ignore[call-arg]
        assert trade.strategy_id  # never empty/None
        summary = compute_sniper_strategy_performance([trade], [])
        assert len(summary.reads) == 1
        assert summary.reads[0].closed_trade_count == 1


class TestRegistryVsHistoricalData:
    def test_disabled_strategy_history_remains_fully_visible(self) -> None:
        trades = [_trade("t1", 0.5, strategy_id="memecoin-sniper"), _trade("t2", -0.2, strategy_id="memecoin-sniper")]
        disabled = _strategy("memecoin-sniper", status="disabled")
        summary = compute_sniper_strategy_performance(trades, [disabled])
        read = _read_for(summary, "memecoin-sniper")
        assert read.closed_trade_count == 2
        assert read.status == "disabled"
        assert read.is_registered is True

    def test_re_enabling_does_not_alter_historical_metrics(self) -> None:
        trades = [_trade("t1", 0.5, strategy_id="memecoin-sniper"), _trade("t2", -0.2, strategy_id="memecoin-sniper")]
        disabled_summary = compute_sniper_strategy_performance(trades, [_strategy("memecoin-sniper", status="disabled")])
        enabled_summary = compute_sniper_strategy_performance(trades, [_strategy("memecoin-sniper", status="enabled")])
        disabled_read = _read_for(disabled_summary, "memecoin-sniper")
        enabled_read = _read_for(enabled_summary, "memecoin-sniper")
        assert disabled_read.closed_trade_count == enabled_read.closed_trade_count
        assert disabled_read.total_realized_pnl_sol == enabled_read.total_realized_pnl_sol
        assert disabled_read.win_rate_pct == enabled_read.win_rate_pct
        assert disabled_read.status != enabled_read.status  # only status itself differs

    def test_a_historical_strategy_no_longer_registered_still_appears(self) -> None:
        """Section 22 — a strategy_id observed in trade_history but
        absent from the CURRENT registry (no delete mechanism exists
        today, but the report must not assume one never will) is still
        represented, using its own trades' real historical name, marked
        `is_registered=False` rather than silently erased."""
        trades = [_trade("t1", 0.4, strategy_id="retired-strategy", strategy_name="Retired Strategy")]
        summary = compute_sniper_strategy_performance(trades, [_strategy("memecoin-sniper")])
        assert {r.strategy_id for r in summary.reads} == {"memecoin-sniper", "retired-strategy"}
        retired_read = _read_for(summary, "retired-strategy")
        assert retired_read.is_registered is False
        assert retired_read.name == "Retired Strategy"
        assert retired_read.family is None
        assert retired_read.provenance is None
        assert retired_read.status is None
        assert retired_read.closed_trade_count == 1

    def test_a_registered_strategy_with_zero_trades_still_appears(self) -> None:
        summary = compute_sniper_strategy_performance([], [_strategy("brand-new-strategy")])
        read = _read_for(summary, "brand-new-strategy")
        assert read.is_registered is True
        assert read.closed_trade_count == 0


class TestDataIntegrity:
    def test_a_trade_with_non_finite_pnl_is_excluded_and_counted(self) -> None:
        good = _trade("t1", 0.5)
        bad_nan = _trade("t2", math.nan)
        bad_inf = _trade("t3", math.inf)
        summary = compute_sniper_strategy_performance([good, bad_nan, bad_inf], [_strategy("memecoin-sniper")])
        read = _read_for(summary, "memecoin-sniper")
        assert read.closed_trade_count == 1
        assert summary.trades_excluded_malformed == 2
        assert summary.closed_trades_considered == 1

    def test_duplicate_trade_ids_are_counted_once(self) -> None:
        trade = _trade("t1", 0.5)
        duplicate = trade.model_copy()
        summary = compute_sniper_strategy_performance([trade, duplicate], [_strategy("memecoin-sniper")])
        read = _read_for(summary, "memecoin-sniper")
        assert read.closed_trade_count == 1
        assert summary.closed_trades_considered == 1


class TestDeterminism:
    def test_identical_input_produces_identical_reads(self) -> None:
        trades = [_trade("t1", 0.5, strategy_id="memecoin-sniper"), _trade("t2", -0.2, strategy_id="memecoin-sniper-whale-confirmation")]
        strategies = [_strategy("memecoin-sniper"), _strategy("memecoin-sniper-whale-confirmation", family="whale_confirmation")]
        summary_1 = compute_sniper_strategy_performance(trades, strategies)
        summary_2 = compute_sniper_strategy_performance(trades, strategies)
        assert summary_1.reads == summary_2.reads
        assert summary_1.trades_excluded_malformed == summary_2.trades_excluded_malformed
        assert summary_1.closed_trades_considered == summary_2.closed_trades_considered

    def test_reads_are_sorted_by_strategy_id_never_by_a_performance_metric(self) -> None:
        trades = [_trade("t1", -5.0, strategy_id="zzz-strategy"), _trade("t2", 5.0, strategy_id="aaa-strategy")]
        summary = compute_sniper_strategy_performance(trades, [])
        assert [r.strategy_id for r in summary.reads] == ["aaa-strategy", "zzz-strategy"]
