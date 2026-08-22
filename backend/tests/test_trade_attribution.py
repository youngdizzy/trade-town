"""Covers app/trade_attribution.py — CEO directive "Next Phase:
Professional Trading Firm Intelligence," Phase 1 (Symbol -> Agent
Attribution). This module preserves real per-agent evidence per trade;
it must never compute or imply a numeric P&L credit split, and must
never fabricate a decision/vote for a trade with no real match.
"""
from __future__ import annotations

from app.schemas import (
    AgentVote,
    CeoDecisionRecord,
    CompiledStrategyDefinition,
    GatekeeperCheck,
    GatekeeperVerdict,
    PaperTrade,
    TradeDecision,
)
from app.trade_attribution import (
    CREDIT_SPLIT_NOTE,
    compute_trade_attribution,
    compute_trade_attribution_history,
    compute_unattributed_trade_monitor,
    resolve_trade_strategy_rule_snapshot,
)


def _trade(
    *,
    trade_id: str = "trade-1",
    decision_id: str | None = "decision-1",
    side: str = "buy",
    pnl: float = 10.0,
    pnl_pct: float = 1.0,
    quantity: float = 1.0,
    entry_price: float = 100.0,
    exit_price: float | None = None,
    entry_slippage_bps: float = 4.2,
    exit_slippage_bps: float = 3.1,
    transaction_cost_usd: float = 1.5,
    closed_sim_minutes: int = 30,
) -> PaperTrade:
    return PaperTrade(
        id=trade_id,
        symbol="AAPL",
        side=side,  # type: ignore[arg-type]
        quantity=quantity,
        entryPrice=entry_price,
        exitPrice=exit_price if exit_price is not None else entry_price + pnl,
        pnl=pnl,
        pnlPct=pnl_pct,
        durationMinutes=30,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        supportingAgents=["scout"],
        opposingAgents=[],
        openedAt="2024-01-01T00:00:00+00:00",
        closedAt="2024-01-01T00:00:00+00:00",
        openedSimMinutes=0,
        closedSimMinutes=closed_sim_minutes,
        decisionId=decision_id,
        entrySlippageBps=entry_slippage_bps,
        exitSlippageBps=exit_slippage_bps,
        transactionCostUsd=transaction_cost_usd,
    )


def _decision(
    *,
    decision_id: str = "decision-1",
    votes: list[AgentVote] | None = None,
    supporting: list[str] | None = None,
    opposing: list[str] | None = None,
    gatekeeper: GatekeeperVerdict | None = None,
) -> TradeDecision:
    return TradeDecision(
        id=decision_id,
        symbol="AAPL",
        outcome="trade",
        votes=votes or [],
        researchSummary="x",
        technicalSummary="x",
        fundamentalSummary="x",
        riskSummary="x",
        supportingAgents=supporting or [],
        opposingAgents=opposing or [],
        confidence=90.0,
        finalReasoning="x",
        gatekeeperVerdict=gatekeeper,
        createdAt="2024-01-01T00:00:00+00:00",
    )


class TestComputeTradeAttribution:
    def test_no_matching_decision_reads_no_decision_on_record_never_fabricated(self) -> None:
        trade = _trade(decision_id="decision-does-not-exist")
        record = compute_trade_attribution(trade, [], [])
        assert record.evidence_state == "no_decision_on_record"
        assert record.contributions == []
        assert record.decision_id is None
        assert record.ceo_choice is None
        assert record.gatekeeper_approved is None
        # Real execution/pnl data still shows regardless of decision match.
        assert record.entry_slippage_bps == 4.2
        assert record.pnl == 10.0

    def test_trade_with_no_decision_id_at_all_also_reads_no_decision_on_record(self) -> None:
        trade = _trade(decision_id=None)
        record = compute_trade_attribution(trade, [_decision()], [])
        assert record.evidence_state == "no_decision_on_record"

    def test_a_matched_decision_produces_full_evidence_with_real_role_tagged_votes(self) -> None:
        votes = [
            AgentVote(agentId="echo", choice="buy", reason="trend is up"),
            AgentVote(agentId="sentinel", choice="hold", reason="risk elevated"),
        ]
        decision = _decision(votes=votes, supporting=["echo"], opposing=["sentinel"])
        trade = _trade(side="buy")
        record = compute_trade_attribution(trade, [decision], [])
        assert record.evidence_state == "full_evidence"
        assert len(record.contributions) == 2
        echo_contribution = next(c for c in record.contributions if c.agent_id == "echo")
        assert echo_contribution.role == "technical"
        assert echo_contribution.agreed_with_side_traded is True
        sentinel_contribution = next(c for c in record.contributions if c.agent_id == "sentinel")
        assert sentinel_contribution.role == "risk"
        # "hold" isn't buy/sell -- never coerced to agreeing with the side traded.
        assert sentinel_contribution.agreed_with_side_traded is False

    def test_agreement_is_checked_against_the_real_side_actually_traded(self) -> None:
        votes = [AgentVote(agentId="echo", choice="sell", reason="reversal expected")]
        decision = _decision(votes=votes)
        trade = _trade(side="buy")
        record = compute_trade_attribution(trade, [decision], [])
        assert record.contributions[0].agreed_with_side_traded is False

    def test_ceo_override_is_read_from_the_real_ceo_decision_record(self) -> None:
        decision = _decision()
        ceo_decision = CeoDecisionRecord(
            id="ceo-1",
            proposalId="proposal-1",
            symbol="AAPL",
            category="stock",
            aiRecommendation="sell",
            ceoDecision="buy",
            agreedWithAi=False,
            decisionId="decision-1",
            createdAt="2024-01-01T00:00:00+00:00",
        )
        trade = _trade()
        record = compute_trade_attribution(trade, [decision], [ceo_decision])
        assert record.ceo_choice == "buy"
        assert record.ceo_overrode_the_desk is True

    def test_no_ceo_decision_match_leaves_ceo_fields_honestly_none(self) -> None:
        decision = _decision()
        trade = _trade()
        record = compute_trade_attribution(trade, [decision], [])
        assert record.ceo_choice is None
        assert record.ceo_overrode_the_desk is None

    def test_gatekeeper_approval_is_read_from_the_real_verdict(self) -> None:
        verdict = GatekeeperVerdict(approved=True, checks=[GatekeeperCheck(id="c1", label="x", passed=True, detail="x")], summary="approved", createdAt="2024-01-01T00:00:00+00:00")
        decision = _decision(gatekeeper=verdict)
        trade = _trade()
        record = compute_trade_attribution(trade, [decision], [])
        assert record.gatekeeper_approved is True

    def test_every_record_carries_the_same_honest_credit_split_disclosure(self) -> None:
        trade = _trade()
        record = compute_trade_attribution(trade, [], [])
        assert record.credit_split_note == CREDIT_SPLIT_NOTE
        assert "no CEO-authorized methodology" in CREDIT_SPLIT_NOTE

    def test_never_computes_or_stores_a_numeric_per_agent_pnl_split(self) -> None:
        # A structural guarantee, not just a docstring claim: nothing on
        # AgentContributionRead carries a dollar or percentage value.
        votes = [AgentVote(agentId="echo", choice="buy", reason="x")]
        decision = _decision(votes=votes)
        record = compute_trade_attribution(_trade(), [decision], [])
        contribution_fields = set(record.contributions[0].model_dump().keys())
        assert not any("pnl" in f.lower() or "credit" in f.lower() for f in contribution_fields)


class TestExecutionAttribution:
    """CEO directive "Complete Trade Provenance," Part 15 — real
    decomposition of realized P&L into price-movement edge vs.
    execution cost (slippage + transaction cost), reconstructed by
    reversing app/execution_quality.py's own real, already-applied
    slippage formula — never a modeled or guessed number."""

    def test_long_trade_reconciles_exactly_price_movement_minus_execution_cost_equals_pnl(self) -> None:
        # entry fill 101.0 with 1% slippage -> real signal price 100.0;
        # exit fill 110.0 with 2% slippage -> real signal price ~112.24.
        trade = _trade(
            side="buy",
            quantity=10.0,
            entry_price=101.0,
            exit_price=110.0,
            entry_slippage_bps=100.0,
            exit_slippage_bps=200.0,
            transaction_cost_usd=5.0,
            pnl=85.0,  # the real close_position() formula for these exact fills
        )
        record = compute_trade_attribution(trade, [], [])
        assert record.price_movement_pnl == 122.45
        assert record.slippage_cost_usd == 32.45
        assert record.execution_cost_total_usd == 37.45
        # The core correctness proof: these three real numbers always
        # reconcile back to the trade's own real, already-realized pnl.
        assert round(record.price_movement_pnl - record.execution_cost_total_usd, 2) == record.pnl == 85.0

    def test_short_trade_reconciles_exactly_with_the_correct_signed_direction(self) -> None:
        # entry fill 99.0 with 1% slippage (short opens via a sell,
        # receiving less) -> real signal price 100.0; exit fill 90.0
        # with 2% slippage (covering a short via a buy, paying more) ->
        # real signal price ~88.24.
        trade = _trade(
            side="sell",
            quantity=10.0,
            entry_price=99.0,
            exit_price=90.0,
            entry_slippage_bps=100.0,
            exit_slippage_bps=200.0,
            transaction_cost_usd=5.0,
            pnl=85.0,
        )
        record = compute_trade_attribution(trade, [], [])
        assert record.price_movement_pnl == 117.65
        assert record.slippage_cost_usd == 27.65
        assert record.execution_cost_total_usd == 32.65
        assert round(record.price_movement_pnl - record.execution_cost_total_usd, 2) == record.pnl == 85.0

    def test_slippage_cost_is_never_negative_since_slippage_is_always_adverse(self) -> None:
        trade = _trade(entry_slippage_bps=50.0, exit_slippage_bps=75.0)
        record = compute_trade_attribution(trade, [], [])
        assert record.slippage_cost_usd >= 0

    def test_zero_slippage_makes_price_movement_pnl_equal_the_pre_transaction_cost_fill_pnl(self) -> None:
        trade = _trade(side="buy", quantity=1.0, entry_price=100.0, exit_price=110.0, entry_slippage_bps=0.0, exit_slippage_bps=0.0, transaction_cost_usd=2.0, pnl=8.0)
        record = compute_trade_attribution(trade, [], [])
        assert record.price_movement_pnl == 10.0  # (110-100)*1, no slippage to reconstruct
        assert record.slippage_cost_usd == 0.0
        assert record.execution_cost_total_usd == 2.0  # transaction cost only

    def test_execution_attribution_is_computed_regardless_of_decision_match(self) -> None:
        # Unlike agent/CEO attribution, this never depends on a matched
        # TradeDecision -- it's derived purely from the trade's own real
        # execution fields.
        trade = _trade(decision_id="decision-does-not-exist", entry_slippage_bps=100.0, exit_slippage_bps=100.0)
        record = compute_trade_attribution(trade, [], [])
        assert record.evidence_state == "no_decision_on_record"
        assert record.price_movement_pnl != 0.0 or record.slippage_cost_usd != 0.0


class TestStrategyProvenance:
    """CEO directive "Live Trade -> Strategy Provenance" — the real
    three-way state (known/unknown/unavailable), never a fabricated
    "the strategy caused this trade" claim."""

    def test_no_matching_decision_reads_unavailable(self) -> None:
        trade = _trade(decision_id="decision-does-not-exist")
        record = compute_trade_attribution(trade, [], [])
        assert record.strategy_provenance_state == "unavailable"
        assert record.strategy_id is None

    def test_matched_decision_but_no_ceo_decision_record_reads_unavailable(self) -> None:
        decision = _decision()
        trade = _trade()
        record = compute_trade_attribution(trade, [decision], [])
        assert record.strategy_provenance_state == "unavailable"
        assert record.strategy_id is None

    def test_matched_ceo_decision_with_no_strategy_selected_reads_unknown(self) -> None:
        decision = _decision()
        ceo_decision = CeoDecisionRecord(
            id="ceo-1",
            proposalId="proposal-1",
            symbol="AAPL",
            category="stock",
            aiRecommendation="buy",
            ceoDecision="buy",
            agreedWithAi=True,
            decisionId="decision-1",
            createdAt="2024-01-01T00:00:00+00:00",
        )
        trade = _trade()
        record = compute_trade_attribution(trade, [decision], [ceo_decision])
        assert record.strategy_provenance_state == "unknown"
        assert record.strategy_id is None

    def test_matched_ceo_decision_with_a_real_strategy_selected_reads_known(self) -> None:
        decision = _decision()
        ceo_decision = CeoDecisionRecord(
            id="ceo-1",
            proposalId="proposal-1",
            symbol="AAPL",
            category="stock",
            aiRecommendation="buy",
            ceoDecision="buy",
            agreedWithAi=True,
            decisionId="decision-1",
            strategyId="strategy-momentum",
            createdAt="2024-01-01T00:00:00+00:00",
        )
        trade = _trade()
        record = compute_trade_attribution(trade, [decision], [ceo_decision])
        assert record.strategy_provenance_state == "known"
        assert record.strategy_id == "strategy-momentum"

    def test_strategy_rule_snapshot_is_carried_through_from_the_ceo_decision(self) -> None:
        # CEO directive "Complete Trade Provenance," Part 2.
        decision = _decision()
        ceo_decision = CeoDecisionRecord(
            id="ceo-1",
            proposalId="proposal-1",
            symbol="AAPL",
            category="stock",
            aiRecommendation="buy",
            ceoDecision="buy",
            agreedWithAi=True,
            decisionId="decision-1",
            strategyId="50-ema-breakout-pullback-long",
            strategyCompiledDefinitionId="50-ema-breakout-pullback-long",
            strategyCompiledDefinitionVersion=2,
            createdAt="2024-01-01T00:00:00+00:00",
        )
        trade = _trade()
        record = compute_trade_attribution(trade, [decision], [ceo_decision])
        assert record.strategy_compiled_definition_id == "50-ema-breakout-pullback-long"
        assert record.strategy_compiled_definition_version == 2

    def test_strategy_rule_snapshot_is_none_when_no_strategy_was_selected(self) -> None:
        decision = _decision()
        ceo_decision = CeoDecisionRecord(
            id="ceo-1",
            proposalId="proposal-1",
            symbol="AAPL",
            category="stock",
            aiRecommendation="buy",
            ceoDecision="buy",
            agreedWithAi=True,
            decisionId="decision-1",
            createdAt="2024-01-01T00:00:00+00:00",
        )
        trade = _trade()
        record = compute_trade_attribution(trade, [decision], [ceo_decision])
        assert record.strategy_compiled_definition_id is None
        assert record.strategy_compiled_definition_version is None


def _compiled_definition(*, definition_id: str = "50-ema-breakout-pullback-long", version: int = 1) -> CompiledStrategyDefinition:
    return CompiledStrategyDefinition(
        id=definition_id,
        name="50 EMA Breakout Pullback (Long)",
        sourceText="test source",
        version=version,
        createdBy="quant",
        createdAt="2024-01-01T00:00:00+00:00",
        timeframe="1h",
        sequence=[],
        stop=None,
        target=None,
        ambiguities=[],
        status="compiled",
        detail="test",
    )


class TestResolveTradeStrategyRuleSnapshot:
    """CEO directive "Complete Trade Provenance," Part 2 —
    resolve_trade_strategy_rule_snapshot() resolves a trade's real
    snapshot reference back into the actual immutable
    CompiledStrategyDefinition, never fabricating one."""

    def test_unknown_trade_id_returns_none(self) -> None:
        snapshot = resolve_trade_strategy_rule_snapshot("no-such-trade", [_trade()], [], [], {})
        assert snapshot is None

    def test_known_trade_with_no_strategy_selected_resolves_with_no_compiled_definition(self) -> None:
        trade = _trade()
        snapshot = resolve_trade_strategy_rule_snapshot(trade.id, [trade], [], [], {})
        assert snapshot is not None
        assert snapshot.strategy_id is None
        assert snapshot.strategy_provenance_state == "unavailable"
        assert snapshot.compiled_definition is None

    def test_known_trade_with_a_strategy_but_no_matching_registry_entry_resolves_with_no_compiled_definition(self) -> None:
        decision = _decision()
        ceo_decision = CeoDecisionRecord(
            id="ceo-1",
            proposalId="proposal-1",
            symbol="AAPL",
            category="stock",
            aiRecommendation="buy",
            ceoDecision="buy",
            agreedWithAi=True,
            decisionId="decision-1",
            strategyId="strategy-momentum",
            createdAt="2024-01-01T00:00:00+00:00",
        )
        trade = _trade()
        snapshot = resolve_trade_strategy_rule_snapshot(trade.id, [trade], [decision], [ceo_decision], {})
        assert snapshot is not None
        assert snapshot.strategy_id == "strategy-momentum"
        assert snapshot.strategy_provenance_state == "known"
        assert snapshot.compiled_definition is None  # real: an "idea"-stage strategy has no compiled rules to resolve

    def test_known_trade_with_a_real_compiled_definition_resolves_the_exact_version(self) -> None:
        decision = _decision()
        ceo_decision = CeoDecisionRecord(
            id="ceo-1",
            proposalId="proposal-1",
            symbol="AAPL",
            category="stock",
            aiRecommendation="buy",
            ceoDecision="buy",
            agreedWithAi=True,
            decisionId="decision-1",
            strategyId="50-ema-breakout-pullback-long",
            strategyCompiledDefinitionId="50-ema-breakout-pullback-long",
            strategyCompiledDefinitionVersion=2,
            createdAt="2024-01-01T00:00:00+00:00",
        )
        trade = _trade()
        registry = {
            "50-ema-breakout-pullback-long": [
                _compiled_definition(version=1),
                _compiled_definition(version=2),
            ]
        }
        snapshot = resolve_trade_strategy_rule_snapshot(trade.id, [trade], [decision], [ceo_decision], registry)
        assert snapshot is not None
        assert snapshot.compiled_definition is not None
        assert snapshot.compiled_definition.version == 2
        assert snapshot.compiled_definition.id == "50-ema-breakout-pullback-long"


class TestComputeTradeAttributionHistory:
    def test_produces_one_record_per_trade_in_order(self) -> None:
        trades = [_trade(trade_id="a", decision_id=None), _trade(trade_id="b", decision_id=None)]
        summary = compute_trade_attribution_history(trades, [], [])
        assert [r.trade_id for r in summary.records] == ["a", "b"]

    def test_empty_history_produces_no_records(self) -> None:
        summary = compute_trade_attribution_history([], [], [])
        assert summary.records == []


def _known_trade(*, trade_id: str, closed_sim_minutes: int) -> tuple[PaperTrade, TradeDecision, CeoDecisionRecord]:
    trade = _trade(trade_id=trade_id, decision_id=f"decision-{trade_id}", closed_sim_minutes=closed_sim_minutes)
    decision = _decision(decision_id=f"decision-{trade_id}")
    ceo_decision = CeoDecisionRecord(
        id=f"ceo-{trade_id}",
        proposalId=f"proposal-{trade_id}",
        symbol="AAPL",
        category="stock",
        aiRecommendation="buy",
        ceoDecision="buy",
        agreedWithAi=True,
        decisionId=f"decision-{trade_id}",
        strategyId="strategy-momentum",
        createdAt="2024-01-01T00:00:00+00:00",
    )
    return trade, decision, ceo_decision


def _unknown_trade(*, trade_id: str, closed_sim_minutes: int) -> tuple[PaperTrade, TradeDecision, CeoDecisionRecord]:
    trade = _trade(trade_id=trade_id, decision_id=f"decision-{trade_id}", closed_sim_minutes=closed_sim_minutes)
    decision = _decision(decision_id=f"decision-{trade_id}")
    ceo_decision = CeoDecisionRecord(
        id=f"ceo-{trade_id}",
        proposalId=f"proposal-{trade_id}",
        symbol="AAPL",
        category="stock",
        aiRecommendation="buy",
        ceoDecision="buy",
        agreedWithAi=True,
        decisionId=f"decision-{trade_id}",
        createdAt="2024-01-01T00:00:00+00:00",
    )
    return trade, decision, ceo_decision


class TestComputeUnattributedTradeMonitor:
    """CEO directive "Complete Trade Provenance," Part 17."""

    def test_counts_unknown_and_unavailable_separately(self) -> None:
        known_trade, known_decision, known_ceo = _known_trade(trade_id="known", closed_sim_minutes=100)
        unknown_trade, unknown_decision, unknown_ceo = _unknown_trade(trade_id="unknown", closed_sim_minutes=200)
        unavailable_trade = _trade(trade_id="unavailable", decision_id="decision-does-not-exist", closed_sim_minutes=300)
        monitor = compute_unattributed_trade_monitor(
            [known_trade, unknown_trade, unavailable_trade],
            [known_decision, unknown_decision],
            [known_ceo, unknown_ceo],
        )
        assert monitor.total_trades == 3
        assert monitor.unknown_count == 1
        assert monitor.unavailable_count == 1
        assert monitor.unattributed_count == 2
        assert monitor.unattributed_pct == round(2 / 3 * 100, 1)

    def test_not_enough_data_below_the_sample_threshold(self) -> None:
        trade, decision, ceo = _known_trade(trade_id="a", closed_sim_minutes=100)
        monitor = compute_unattributed_trade_monitor([trade], [decision], [ceo])
        assert monitor.trend == "not_enough_data"

    def test_empty_trade_history_reports_zero_with_not_enough_data(self) -> None:
        monitor = compute_unattributed_trade_monitor([], [], [])
        assert monitor.total_trades == 0
        assert monitor.unattributed_count == 0
        assert monitor.trend == "not_enough_data"

    def test_improving_trend_when_the_recent_half_has_a_higher_attribution_rate(self) -> None:
        trades, decisions, ceo_decisions = [], [], []
        for i in range(3):
            t, d, c = _unknown_trade(trade_id=f"early-{i}", closed_sim_minutes=i)
            trades.append(t)
            decisions.append(d)
            ceo_decisions.append(c)
        for i in range(3):
            t, d, c = _known_trade(trade_id=f"recent-{i}", closed_sim_minutes=1000 + i)
            trades.append(t)
            decisions.append(d)
            ceo_decisions.append(c)
        monitor = compute_unattributed_trade_monitor(trades, decisions, ceo_decisions)
        assert monitor.trend == "improving"

    def test_worsening_trend_when_the_recent_half_has_a_lower_attribution_rate(self) -> None:
        trades, decisions, ceo_decisions = [], [], []
        for i in range(3):
            t, d, c = _known_trade(trade_id=f"early-{i}", closed_sim_minutes=i)
            trades.append(t)
            decisions.append(d)
            ceo_decisions.append(c)
        for i in range(3):
            t, d, c = _unknown_trade(trade_id=f"recent-{i}", closed_sim_minutes=1000 + i)
            trades.append(t)
            decisions.append(d)
            ceo_decisions.append(c)
        monitor = compute_unattributed_trade_monitor(trades, decisions, ceo_decisions)
        assert monitor.trend == "worsening"

    def test_stable_trend_when_the_rate_is_unchanged_across_both_halves(self) -> None:
        trades, decisions, ceo_decisions = [], [], []
        for i in range(3):
            t, d, c = _unknown_trade(trade_id=f"early-{i}", closed_sim_minutes=i)
            trades.append(t)
            decisions.append(d)
            ceo_decisions.append(c)
        for i in range(3):
            t, d, c = _unknown_trade(trade_id=f"recent-{i}", closed_sim_minutes=1000 + i)
            trades.append(t)
            decisions.append(d)
            ceo_decisions.append(c)
        monitor = compute_unattributed_trade_monitor(trades, decisions, ceo_decisions)
        assert monitor.trend == "stable"

    def test_ordering_by_closed_sim_minutes_not_list_order(self) -> None:
        # Trades passed in reverse chronological order must still be
        # split into real earlier/later halves by their own real
        # closedSimMinutes, not by list position.
        trades, decisions, ceo_decisions = [], [], []
        for i in range(3):
            t, d, c = _known_trade(trade_id=f"recent-{i}", closed_sim_minutes=1000 + i)
            trades.append(t)
            decisions.append(d)
            ceo_decisions.append(c)
        for i in range(3):
            t, d, c = _unknown_trade(trade_id=f"early-{i}", closed_sim_minutes=i)
            trades.append(t)
            decisions.append(d)
            ceo_decisions.append(c)
        # trades list is [recent..., early...] -- deliberately reversed
        monitor = compute_unattributed_trade_monitor(trades, decisions, ceo_decisions)
        assert monitor.trend == "improving"
