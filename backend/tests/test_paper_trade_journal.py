"""Covers app/paper_trade_journal.py."""
from __future__ import annotations

from app.paper_trade_journal import add_ceo_note, build_journal_entry
from app.schemas import CeoDecisionRecord, PaperTrade, RiskContractScalingRead, RiskDecision


def _trade(**overrides: object) -> PaperTrade:
    base: dict[str, object] = dict(
        id="t1",
        symbol="AAPL",
        side="buy",
        quantity=2.0,
        entryPrice=100.0,
        exitPrice=108.0,
        pnl=16.0,
        pnlPct=8.0,
        durationMinutes=45,
        confidence=82.0,
        reason="Breakout confirmed.",
        marketConditions="Trending.",
        supportingAgents=["scout"],
        openedAt="2026-01-01T00:00:00+00:00",
        closedAt="2026-01-01T00:45:00+00:00",
        openedSimMinutes=0,
        closedSimMinutes=45,
        decisionId="decision-p1",
        proposalId="p1",
        stopPrice=97.0,
        targetPrice=112.0,
        maePct=-0.5,
        mfePct=9.0,
    )
    base.update(overrides)
    return PaperTrade(**base)  # type: ignore[arg-type]


def _ceo_record(**overrides: object) -> CeoDecisionRecord:
    base: dict[str, object] = dict(
        id="cd1",
        proposalId="p1",
        symbol="AAPL",
        category="stock",
        aiRecommendation="buy",
        ceoDecision="buy",
        agreedWithAi=True,
        decisionId="decision-p1",
        createdAt="2026-01-01T00:00:00+00:00",
        resolvedBy="ceo",
        strategyId="strategy-1",
        strategyCompiledDefinitionId="def-1",
        strategyCompiledDefinitionVersion=2,
        decisionMarketRegime="weak_uptrend",
        decisionSession="new_york",
    )
    base.update(overrides)
    return CeoDecisionRecord(**base)  # type: ignore[arg-type]


def _risk_decision() -> RiskDecision:
    scaling = RiskContractScalingRead(
        riskContractId="rc-1",
        riskContractVersion=1,
        drawdownPct=0.0,
        drawdownFactor=1.0,
        consecutiveLosses=0,
        losingStreakFactor=1.0,
        combinedFactor=1.0,
        baseRiskPerTradePct=2.0,
        approvedRiskPerTradePct=2.0,
        baseMaxPositionPct=10.0,
        approvedMaxPositionPct=10.0,
        killSwitchTriggered=False,
        detail="No scaling applied.",
    )
    return RiskDecision(
        id="riskdecision-decision-p1",
        createdAt="2026-01-01T00:00:00+00:00",
        proposalId="p1",
        decisionId="decision-p1",
        symbol="AAPL",
        scaling=scaling,
        requestedQuantity=2.0,
        approvedQuantity=2.0,
        rejected=False,
    )


def test_build_journal_entry_snapshots_trade_facts_never_referencing_only() -> None:
    entry = build_journal_entry(_trade(), ceo_decision=_ceo_record(), risk_decision=_risk_decision())
    assert entry.id == "journal-t1"
    assert entry.trade_id == "t1"
    assert entry.decision_id == "decision-p1"
    assert entry.proposal_id == "p1"
    assert entry.risk_decision_id == "riskdecision-decision-p1"
    assert entry.symbol == "AAPL"
    assert entry.quantity == 2.0
    assert entry.entry_price == 100.0
    assert entry.exit_price == 108.0
    assert entry.stop_price == 97.0
    assert entry.target_price == 112.0
    assert entry.pnl == 16.0
    assert entry.mae_pct == -0.5
    assert entry.mfe_pct == 9.0


def test_build_journal_entry_carries_strategy_identity_and_version() -> None:
    entry = build_journal_entry(_trade(), ceo_decision=_ceo_record(), risk_decision=None)
    assert entry.strategy_id == "strategy-1"
    assert entry.strategy_compiled_definition_id == "def-1"
    assert entry.strategy_compiled_definition_version == 2
    assert entry.resolved_by == "ceo"


def test_build_journal_entry_carries_decision_time_market_snapshot() -> None:
    entry = build_journal_entry(_trade(), ceo_decision=_ceo_record(), risk_decision=None)
    assert entry.decision_market_regime == "weak_uptrend"
    assert entry.decision_session == "new_york"


def test_build_journal_entry_handles_no_matched_ceo_decision() -> None:
    entry = build_journal_entry(_trade(), ceo_decision=None, risk_decision=None)
    assert entry.strategy_id is None
    assert entry.strategy_compiled_definition_id is None
    assert entry.resolved_by is None
    assert entry.decision_market_regime is None
    assert entry.risk_decision_id is None
    # The trade's own facts are still real and present.
    assert entry.symbol == "AAPL"
    assert entry.pnl == 16.0


def test_build_journal_entry_defaults_data_provenance_to_simulated() -> None:
    entry = build_journal_entry(_trade(), ceo_decision=None, risk_decision=None)
    assert entry.data_provenance == "simulated"


def test_build_journal_entry_starts_with_no_ceo_notes() -> None:
    entry = build_journal_entry(_trade(), ceo_decision=None, risk_decision=None)
    assert entry.ceo_notes == []


def test_add_ceo_note_appends_never_replaces() -> None:
    entry = build_journal_entry(_trade(), ceo_decision=None, risk_decision=None)
    entry = add_ceo_note(entry, text="Held to plan.")
    entry = add_ceo_note(entry, text="Would size smaller next time.")
    assert len(entry.ceo_notes) == 2
    assert entry.ceo_notes[0].text == "Held to plan."
    assert entry.ceo_notes[1].text == "Would size smaller next time."
    assert entry.ceo_notes[0].id != entry.ceo_notes[1].id
