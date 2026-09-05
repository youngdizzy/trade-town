"""Covers app/sniper_ai_context.py — CEO directive "TradeTown — Memecoin
Sniper AI 1.0." Confirms: (1) every evidence item traces to a real
SniperCandidate/SniperPosition/SniperTrade field; (2) market structure is
always reported UNKNOWN, never fabricated from the scalar fields that
happen to exist; (3) the domain-tagged institutional-memory retrieval +
anti-lookahead cutoff; (4) deterministic_sniper_recommendation()/
resolve_sniper_deterministic_outcome()'s real branches, keyed by `mint`;
(5) compare_sniper_ai_to_deterministic()'s real AGREE/DISAGREE/PARTIAL/
INCONCLUSIVE branches; (6) promote_sniper_lesson()'s domain tagging and
retrieve_relevant_memory()'s new `domain` filter.
"""
from __future__ import annotations

import json

from app.institutional_memory import promote_sniper_lesson, retrieve_relevant_memory
from app.schemas import (
    AIReasoningResult,
    InstitutionalMemoryEntry,
    SniperCandidate,
    SniperLesson,
    SniperPosition,
    SniperScoreComponent,
    SniperTrade,
)
from app.sniper_ai_context import (
    CONTEXT_BUILDER_VERSION,
    build_sniper_evidence_packet,
    compare_sniper_ai_to_deterministic,
    deterministic_sniper_recommendation,
    resolve_sniper_deterministic_outcome,
)

_CREATED_AT = "2026-01-01T00:00:00+00:00"


def _candidate(*, mint: str = "m" * 32, symbol: str = "MEWPEPE", opportunity_score: float = 82.0, classification: str = "high_conviction") -> SniperCandidate:
    return SniperCandidate(
        id=f"cand-{mint[:8]}", mint=mint, symbol=symbol, name=f"{symbol} Token", discoveredAt=_CREATED_AT, ageSeconds=20.0,
        priceUsd=0.0001, marketCapUsd=100_000.0, liquidityUsd=80_000.0, liquidityTrend="rising", buyCount1m=40,
        buyPressurePct=80.0, uniqueBuyers=30, uniqueSellers=8, top10ConcentrationPct=25.0, mintAuthorityRevoked=True,
        freezeAuthorityRevoked=True, creatorRisk="weak_signal", whaleSignalCount=2, socialMomentumPct=50.0,
        expectedSlippagePct=2.0, rugRisk="low", dataQuality="sufficient", safetyStatus="safe_enough", safetyChecks=[],
        opportunityScore=opportunity_score, scoreComponents=[SniperScoreComponent(name="momentum", rawValue=20.0, normalizedScore=54.0, weightPct=20.0, detail="Price momentum +20.0%.")],
        classification=classification, timingState="entry_window", decisionReason="test reason",  # type: ignore[arg-type]
    )


def _position(*, mint: str) -> SniperPosition:
    return SniperPosition(
        id=f"snipe-{mint[:8]}", mint=mint, symbol="MEWPEPE", entryPrice=0.0001, currentPrice=0.00012, sizeSol=1.0,
        stopPrice=0.000088, targetPrice=0.000155, openedAt=_CREATED_AT, status="open", pnlSol=0.02, pnlPct=20.0, riskSol=0.012,
    )


def _trade(*, mint: str, pnl_sol: float) -> SniperTrade:
    return SniperTrade(
        id=f"trade-{mint[:8]}", mint=mint, symbol="MEWPEPE", openedAt=_CREATED_AT, closedAt=_CREATED_AT, entryPrice=0.0001,
        exitPrice=0.00012 if pnl_sol >= 0 else 0.00008, stopPrice=0.000088, targetPrice=0.000155, sizeSol=1.0, riskSol=0.012,
        rMultiple=pnl_sol / 0.012 if pnl_sol else 0.0, pnlSol=pnl_sol, maxFavorableExcursionPct=20.0, maxAdverseExcursionPct=-5.0,
        holdTimeSeconds=30.0, exitReason="take_profit" if pnl_sol >= 0 else "stop_loss", thesis="x",
    )


def _memory(*, sim_day: int, domain: str = "memecoin_sniper", symbol: str | None = "MEWPEPE") -> InstitutionalMemoryEntry:
    return InstitutionalMemoryEntry(
        id="im-1", source="research_lesson", createdAt=_CREATED_AT, simDay=sim_day, eventRef="event-1",
        observation="A real observed pattern.", lesson="A real, actionable lesson.", confidence=70.0,
        provenance="test provenance", relevancePct=90.0, symbol=symbol, domain=domain,  # type: ignore[arg-type]
    )


def test_evidence_items_trace_to_real_candidate_fields() -> None:
    candidate = _candidate()
    packet = build_sniper_evidence_packet(candidate, packet_id="pkt-1", task="Evaluate MEWPEPE", cutoff_sim_minutes=100, institutional_memory=[], current_sim_day=0)
    assert packet.context_builder_version == CONTEXT_BUILDER_VERSION
    assert packet.domain == "memecoin_sniper"
    assert packet.agent_role == "sniper_analyst"
    assert packet.proposal_id == candidate.mint
    by_id = {item.id: item for item in packet.items}
    assert by_id["fact-symbol"].detail == "MEWPEPE (MEWPEPE Token)"
    assert "80,000" in by_id["fact-liquidity"].detail
    assert "rising" in by_id["fact-liquidity"].detail
    assert "25.0%" in by_id["fact-holder-concentration"].detail


def test_market_structure_is_always_reported_unknown() -> None:
    candidate = _candidate()
    packet = build_sniper_evidence_packet(candidate, packet_id="pkt-1", task="Evaluate MEWPEPE", cutoff_sim_minutes=100, institutional_memory=[], current_sim_day=0)
    structure_item = next(item for item in packet.items if item.id == "fact-market-structure")
    assert structure_item.kind == "unknown"
    assert "UNKNOWN" in structure_item.detail


def test_manipulation_risk_uses_stricter_of_creator_risk_and_concentration() -> None:
    candidate = _candidate()
    candidate = candidate.model_copy(update={"creator_risk": "weak_signal", "top10_concentration_pct": 80.0})
    packet = build_sniper_evidence_packet(candidate, packet_id="pkt-1", task="x", cutoff_sim_minutes=100, institutional_memory=[], current_sim_day=0)
    manipulation_item = next(item for item in packet.items if item.id == "fact-manipulation-risk")
    assert manipulation_item.detail == "high"  # concentration (high) is stricter than creator_risk=weak_signal (low)


def test_position_evidence_is_included_when_a_position_exists() -> None:
    candidate = _candidate()
    position = _position(mint=candidate.mint)
    packet = build_sniper_evidence_packet(candidate, packet_id="pkt-1", task="x", cutoff_sim_minutes=100, institutional_memory=[], current_sim_day=0, position=position)
    assert any(item.id == "fact-position-open" for item in packet.items)
    assert not any(item.id == "fact-trade-outcome" for item in packet.items)


def test_trade_evidence_discloses_closure_but_never_leaks_the_real_outcome() -> None:
    """"Sniper AI Shadow Reasoning Burn-In 1.0" directive, Part XI/XXVI —
    a real hindsight-leak this pass's own fresh audit found and fixed:
    the evidence packet must disclose that the candidate already closed
    (never silently omit that fact) but must NEVER include the real
    pnl_sol/r_multiple/exit_reason/mfe/mae that would let the model's own
    recommendation be trivially informed by the answer it's meant to be
    predicting."""
    candidate = _candidate()
    trade = _trade(mint=candidate.mint, pnl_sol=0.05)
    packet = build_sniper_evidence_packet(candidate, packet_id="pkt-1", task="x", cutoff_sim_minutes=100, institutional_memory=[], current_sim_day=0, trade=trade)
    trade_item = next(item for item in packet.items if item.id == "fact-trade-outcome")
    assert trade_item.kind == "unknown"
    serialized = " ".join(item.detail for item in packet.items) + " ".join(item.label for item in packet.items)
    assert "take_profit" not in serialized
    assert "0.05" not in serialized
    assert str(trade.pnl_sol) not in serialized
    assert str(trade.r_multiple) not in serialized


def test_trade_evidence_never_leaks_outcome_across_a_range_of_real_trades() -> None:
    """Same guarantee as above, swept across several distinct real
    pnl/r-multiple/exit-reason combinations so the fix isn't accidentally
    narrow to one specific fixture's numeric values."""
    candidate = _candidate()
    for pnl_sol, exit_reason in [(0.05, "take_profit"), (-0.03, "stop_loss"), (0.0, "manual_exit")]:
        trade = _trade(mint=candidate.mint, pnl_sol=pnl_sol)
        trade = trade.model_copy(update={"exit_reason": exit_reason})  # type: ignore[arg-type]
        packet = build_sniper_evidence_packet(candidate, packet_id="pkt-1", task="x", cutoff_sim_minutes=100, institutional_memory=[], current_sim_day=0, trade=trade)
        trade_item = next(item for item in packet.items if item.id == "fact-trade-outcome")
        outcome_text = json.dumps(trade_item.model_dump())
        assert exit_reason not in outcome_text
        assert f"{pnl_sol:+.4f}" not in outcome_text
        assert f"{trade.r_multiple:+.2f}" not in outcome_text
        assert f"{trade.max_favorable_excursion_pct:+.1f}" not in outcome_text


def test_no_position_or_trade_means_no_entry_evidence_items() -> None:
    candidate = _candidate()
    packet = build_sniper_evidence_packet(candidate, packet_id="pkt-1", task="x", cutoff_sim_minutes=100, institutional_memory=[], current_sim_day=0)
    assert not any(item.id in ("fact-entry-risk", "fact-position-open", "fact-trade-outcome") for item in packet.items)


def test_domain_tagged_memory_before_cutoff_is_retrieved_as_knowledge() -> None:
    candidate = _candidate()
    memory = _memory(sim_day=0)
    packet = build_sniper_evidence_packet(candidate, packet_id="pkt-1", task="x", cutoff_sim_minutes=60, institutional_memory=[memory], current_sim_day=0)
    knowledge_items = [item for item in packet.items if item.kind == "knowledge"]
    assert len(knowledge_items) == 1
    assert knowledge_items[0].id == "knowledge-im-1"


def test_memory_promoted_after_discovery_but_before_now_is_excluded_from_evidence() -> None:
    """"Sniper AI Burn-In + Provider Activation 1.0" directive, Part VII/
    VIII/XXXVI — regression-tests the RESIDUAL hindsight-leak this pass's
    own fresh audit found: the prior pass redacted the leaked trade
    OUTCOME value but left `cutoff_sim_minutes` itself anchored to
    "whenever a human happens to click Ask AI" rather than the
    candidate's own real discovery instant. This test proves actual
    temporal semantics, not just a field-name check: institutional
    memory promoted strictly AFTER a candidate's real discovery time but
    strictly BEFORE some later "now" must be excluded from that
    candidate's evidence packet when the caller correctly passes the
    candidate's own discovery-time cutoff — even though the memory
    predates "now." Under the old (pre-fix) behavior of always passing
    `cutoff_sim_minutes = sim_minutes(now)`, this exact memory would have
    been WRONGLY included (1440 <= 1500) — this test would have failed
    then and must pass now."""
    candidate = _candidate().model_copy(update={"discovered_sim_minutes": 100})
    # Institutional memory promoted at sim_day=1 (minute 1440) — strictly
    # after the candidate's own discovery at minute 100, and strictly
    # before a hypothetical "now" at minute 1500 (still day 1).
    memory = _memory(sim_day=1)
    assert 100 < memory.sim_day * 1440 < 1500

    # The REAL caller (app/state.py's submit_sniper_ai_reasoning_request)
    # now passes the candidate's own discovery-time cutoff, not "now".
    packet_using_discovery_cutoff = build_sniper_evidence_packet(
        candidate, packet_id="pkt-1", task="x", cutoff_sim_minutes=candidate.discovered_sim_minutes,
        institutional_memory=[memory], current_sim_day=1,
    )
    assert not [item for item in packet_using_discovery_cutoff.items if item.kind == "knowledge"]

    # Sanity check that the memory genuinely WOULD have leaked under the
    # old "cutoff = now" behavior, proving this is a real regression test
    # and not a tautology.
    packet_using_now_cutoff = build_sniper_evidence_packet(
        candidate, packet_id="pkt-2", task="x", cutoff_sim_minutes=1500,
        institutional_memory=[memory], current_sim_day=1,
    )
    assert any(item.kind == "knowledge" for item in packet_using_now_cutoff.items)


def test_equities_domain_memory_is_never_surfaced_to_sniper_ai() -> None:
    candidate = _candidate()
    equities_memory = _memory(sim_day=0, domain="equities")
    packet = build_sniper_evidence_packet(candidate, packet_id="pkt-1", task="x", cutoff_sim_minutes=60, institutional_memory=[equities_memory], current_sim_day=0)
    assert not [item for item in packet.items if item.kind == "knowledge"]


def test_retrieve_relevant_memory_domain_filter_excludes_other_domain() -> None:
    sniper_memory = _memory(sim_day=0, domain="memecoin_sniper")
    equities_memory = _memory(sim_day=0, domain="equities")
    result = retrieve_relevant_memory([sniper_memory, equities_memory], current_sim_day=0, domain="memecoin_sniper", symbol="MEWPEPE")
    assert result is not None
    assert result.id == sniper_memory.id


def test_retrieve_relevant_memory_domain_omitted_preserves_old_behavior() -> None:
    """Every pre-existing (equities) caller of retrieve_relevant_memory()
    omits `domain` entirely — confirms that path is completely
    unaffected by this directive's addition."""
    equities_memory = _memory(sim_day=0, domain="equities", symbol="AAPL")
    result = retrieve_relevant_memory([equities_memory], current_sim_day=0, symbol="AAPL")
    assert result is not None
    assert result.id == equities_memory.id


def test_promote_sniper_lesson_tags_domain() -> None:
    lesson = SniperLesson(
        id="lesson-1", observation="Late entries underperformed.", sampleSize=20, effect="-0.5R average difference.",
        confidence="medium", regime="all", recommendation="Tighten the timing window.", createdAt=_CREATED_AT,
    )
    entry = promote_sniper_lesson(lesson, sim_day=5)
    assert entry.domain == "memecoin_sniper"
    assert entry.source == "research_lesson"
    assert entry.event_ref == "lesson-1"
    assert entry.lesson == "Tighten the timing window."
    assert entry.sim_day == 5


def test_deterministic_recommendation_is_buy_when_a_trade_exists() -> None:
    mint = "z" * 32
    trade = _trade(mint=mint, pnl_sol=0.05)
    assert deterministic_sniper_recommendation(mint, positions=[], trade_history=[trade]) == "buy"


def test_deterministic_recommendation_is_buy_when_an_open_position_exists() -> None:
    mint = "y" * 32
    position = _position(mint=mint)
    assert deterministic_sniper_recommendation(mint, positions=[position], trade_history=[]) == "buy"


def test_deterministic_recommendation_is_wait_when_neither_exists() -> None:
    assert deterministic_sniper_recommendation("no-such-mint", positions=[], trade_history=[]) == "wait"


def test_resolve_outcome_supported_for_winning_trade() -> None:
    mint = "w" * 32
    trade = _trade(mint=mint, pnl_sol=0.05)
    outcome, ref = resolve_sniper_deterministic_outcome(mint, positions=[], trade_history=[trade])
    assert outcome == "supported"
    assert ref == trade.id


def test_resolve_outcome_contradicted_for_losing_trade() -> None:
    mint = "v" * 32
    trade = _trade(mint=mint, pnl_sol=-0.05)
    outcome, ref = resolve_sniper_deterministic_outcome(mint, positions=[], trade_history=[trade])
    assert outcome == "contradicted"
    assert ref == trade.id


def test_resolve_outcome_pending_for_still_open_position() -> None:
    mint = "u" * 32
    position = _position(mint=mint)
    outcome, ref = resolve_sniper_deterministic_outcome(mint, positions=[position], trade_history=[])
    assert outcome == "pending"
    assert ref == position.id


def test_resolve_outcome_inconclusive_when_never_entered() -> None:
    """A candidate the deterministic engine never entered can never
    accumulate further real evidence (tick_sniper_engine() only ever
    evaluates entry once, at discovery) — graded inconclusive immediately,
    never left "pending forever"."""
    outcome, ref = resolve_sniper_deterministic_outcome("never-entered-mint", positions=[], trade_history=[])
    assert outcome == "inconclusive"
    assert ref is None


def _result(*, status: str = "completed", recommendation: str | None = "buy", deterministic_recommendation: str | None = "buy") -> AIReasoningResult:
    return AIReasoningResult(
        id="res-1", agentId="quant", role="sniper_analyst", domain="memecoin_sniper", task="x", evidencePacketId="pkt-1",  # type: ignore[arg-type]
        proposalId="m" * 32, symbol="MEWPEPE", modelProvider="fake", modelVersion="fake", promptVersion="test-1.0",
        status=status, createdAt=_CREATED_AT, recommendation=recommendation, deterministicRecommendation=deterministic_recommendation,  # type: ignore[arg-type]
    )


def test_comparison_agree_when_both_want_a_trade() -> None:
    assert compare_sniper_ai_to_deterministic(_result(recommendation="buy", deterministic_recommendation="buy")) == "agree"


def test_comparison_agree_when_both_want_no_trade() -> None:
    assert compare_sniper_ai_to_deterministic(_result(recommendation="wait", deterministic_recommendation="wait")) == "agree"


def test_comparison_disagree_when_ai_wants_trade_but_deterministic_did_not() -> None:
    assert compare_sniper_ai_to_deterministic(_result(recommendation="buy", deterministic_recommendation="wait")) == "disagree"


def test_comparison_disagree_when_ai_rejects_thesis_but_deterministic_traded() -> None:
    assert compare_sniper_ai_to_deterministic(_result(recommendation="reject_thesis", deterministic_recommendation="buy")) == "disagree"


def test_comparison_partial_for_research_more() -> None:
    assert compare_sniper_ai_to_deterministic(_result(recommendation="research_more")) == "partial"


def test_comparison_inconclusive_when_ai_reasoning_did_not_complete() -> None:
    assert compare_sniper_ai_to_deterministic(_result(status="provider_unavailable", recommendation=None)) == "inconclusive"
