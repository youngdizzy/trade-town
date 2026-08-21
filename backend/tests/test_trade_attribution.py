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
    resolve_trade_strategy_rule_snapshot,
)


def _trade(*, trade_id: str = "trade-1", decision_id: str | None = "decision-1", side: str = "buy", pnl: float = 10.0, pnl_pct: float = 1.0) -> PaperTrade:
    return PaperTrade(
        id=trade_id,
        symbol="AAPL",
        side=side,  # type: ignore[arg-type]
        quantity=1.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl,
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
        closedSimMinutes=30,
        decisionId=decision_id,
        entrySlippageBps=4.2,
        exitSlippageBps=3.1,
        transactionCostUsd=1.5,
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
