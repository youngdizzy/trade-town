"""Covers app/war_room.py — v0.7 Feature 55, the Executive Decision
Simulator's Digital War Room (brief self-numbered "Feature 54"; renamed
to avoid the collision with the already-shipped Decision Memory System —
see the module's own docstring). Every WarRoomSession field must trace
back to a real existing artifact (department opinions, the What-If
Simulation Lab, the Decision Vault's similarity engine) or a real
computation over one — never a fabricated read.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.market_data import Candle
from app.market_intelligence import default_market_intelligence_state
from app.schemas import (
    AnalystVote,
    ConfidenceFactor,
    DecisionConfidence,
    EvidenceConfluenceRead,
    LiquidityRead,
    NewsRiskRead,
    PaperTrade,
    RiskLimits,
    RiskWarning,
    ScenarioResult,
    TradeProposal,
    WarRoomSession,
    WhatIfSimulation,
)
from app.war_room import (
    DECISION_SCORE_THRESHOLD,
    MAX_WAR_ROOM_SESSIONS,
    TOTAL_DIRECTIONAL_EVIDENCE_FAMILIES,
    _evidence_confluence_score,
    build_contingency_plan,
    build_decision_score,
    build_expected_value_analysis,
    build_war_room_session,
    compare_scenario_to_outcome,
    evidence_never_exceeds_confidence,
    record_war_room_session,
)
from app.whatif import run_whatif_simulation


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_DEFAULT_FACTORS = [
    ConfidenceFactor(name="Multi-Agent Agreement", score=80.0, weight=0.30, detail="d"),
    ConfidenceFactor(name="Technical Alignment", score=80.0, weight=0.20, detail="d"),
    ConfidenceFactor(name="Risk Conditions", score=80.0, weight=0.20, detail="d"),
    ConfidenceFactor(name="Research Confidence", score=80.0, weight=0.15, detail="d"),
    ConfidenceFactor(
        name="News, Macro & Sentiment", score=80.0, weight=0.10, detail="d"
    ),
    ConfidenceFactor(name="Portfolio Exposure", score=80.0, weight=0.05, detail="d"),
]


def _proposal(
    *,
    symbol: str = "NEXA",
    score: float = 80.0,
    tier: str = "strong",
    factors: list[ConfidenceFactor] | None = None,
) -> TradeProposal:
    return TradeProposal(
        id="proposal-1",
        symbol=symbol,
        category="stock",
        quantity=1.0,
        price=100.0,
        confidence=score,
        analystVotes=[
            AnalystVote(
                role="risk",
                agentId="sentinel",
                choice="buy",
                reasoning="Within limits.",
                evidence=["Real risk read"],
            )
        ],  # type: ignore[arg-type]
        overallRecommendation="buy",
        researchSummary="Nova's research backs this setup.",
        riskSummary="Within all configured risk limits.",
        confidenceEngine=DecisionConfidence(
            score=score,
            tier=tier,  # type: ignore[arg-type]
            summary="A well-supported setup.",
            factors=factors or _DEFAULT_FACTORS,
        ),
        createdAt=_now_iso(),
        createdSimMinutes=0,
    )


def _candles(closes: list[float], symbol: str = "NEXA") -> list[Candle]:
    candles = []
    for i, close in enumerate(closes):
        candles.append(
            Candle(
                symbol=symbol,
                timeframe="1h",
                timestamp=f"2026-01-01T{i:02d}:00:00Z",
                open=close,
                high=close + 1,
                low=close - 1,
                close=close,
                volume=1000.0,
                data_status="simulated",
            )
        )
    return candles


def _simulation(symbol: str = "NEXA") -> WhatIfSimulation:
    return run_whatif_simulation(
        symbol, _candles([100.0 + i * 0.5 for i in range(30)], symbol=symbol)
    )


def _scenario(
    *,
    low: float = -5.0,
    high: float = 10.0,
    drawdown: float = -3.0,
    probability: float = 60.0,
) -> ScenarioResult:
    return ScenarioResult(
        scenarioType="bullish_continuation",  # type: ignore[arg-type]
        label="Bullish Continuation",
        rewardRangeLowPct=low,
        rewardRangeHighPct=high,
        mostLikelyPct=(low + high) / 2,
        typicalDrawdownPct=drawdown,
        maxRiskPct=drawdown * 2,
        probabilityOfProfitPct=probability,
        invalidation="Trend breaks down.",
    )


def _trade(*, pnl_pct: float = 2.0) -> PaperTrade:
    return PaperTrade(
        id="trade-1",
        symbol="NEXA",
        side="buy",  # type: ignore[arg-type]
        quantity=10.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl_pct,
        pnl=pnl_pct * 10.0,
        pnlPct=pnl_pct,
        durationMinutes=60,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        openedAt=_now_iso(),
        closedAt=_now_iso(),
    )


class TestBuildExpectedValueAnalysis:
    def test_positive_expectancy_when_expected_value_is_positive(self) -> None:
        simulation = _simulation()
        analysis = build_expected_value_analysis(simulation)
        assert analysis.positive_expectancy == (analysis.expected_value_pct > 0)

    def test_risk_to_reward_is_zero_when_average_drawdown_is_zero(self) -> None:
        simulation = WhatIfSimulation(
            symbol="NEXA",
            holdBars=24,
            scenarios=[_scenario(drawdown=0.0)],
            baseline=_scenario(),
            bestCaseScenario="bullish_continuation",
            worstCaseScenario="bullish_continuation",
        )  # type: ignore[arg-type]
        analysis = build_expected_value_analysis(simulation)
        assert analysis.risk_to_reward == 0.0

    def test_edge_is_the_gap_between_expected_value_and_the_baseline(self) -> None:
        baseline = _scenario(low=0.0, high=0.0, probability=100.0)
        scenario = _scenario(low=10.0, high=10.0, probability=100.0)
        simulation = WhatIfSimulation(
            symbol="NEXA",
            holdBars=24,
            scenarios=[scenario],
            baseline=baseline,
            bestCaseScenario="bullish_continuation",
            worstCaseScenario="bullish_continuation",
        )  # type: ignore[arg-type]
        analysis = build_expected_value_analysis(simulation)
        assert analysis.expected_value_pct == 10.0
        assert analysis.edge_pct == 10.0

    def test_detail_mentions_edge_or_shortfall_honestly(self) -> None:
        simulation = _simulation()
        analysis = build_expected_value_analysis(simulation)
        assert (
            "edge" in analysis.detail.lower() or "shortfall" in analysis.detail.lower()
        )


class TestBuildDecisionScore:
    def test_no_risk_warnings_scores_risk_at_the_ceiling(self) -> None:
        proposal = _proposal()
        score = build_decision_score(
            proposal,
            risk_warnings=[],
            correlated_open_positions=0,
            expected_value=build_expected_value_analysis(_simulation()),
            market_intelligence=default_market_intelligence_state(),
            liquidity=None,
        )
        assert score.risk_score == 100.0

    def test_critical_risk_warning_for_this_symbol_tanks_risk_score(self) -> None:
        proposal = _proposal(symbol="NEXA")
        warnings = [
            RiskWarning(
                id="w1",
                symbol="NEXA",
                severity="critical",
                message="Breach.",
                createdAt=_now_iso(),
            )
        ]  # type: ignore[arg-type]
        score = build_decision_score(
            proposal,
            risk_warnings=warnings,
            correlated_open_positions=0,
            expected_value=build_expected_value_analysis(_simulation()),
            market_intelligence=default_market_intelligence_state(),
            liquidity=None,
        )
        assert score.risk_score == 20.0

    def test_risk_warning_for_a_different_symbol_is_ignored(self) -> None:
        proposal = _proposal(symbol="NEXA")
        warnings = [
            RiskWarning(
                id="w1",
                symbol="OTHER",
                severity="critical",
                message="Breach.",
                createdAt=_now_iso(),
            )
        ]  # type: ignore[arg-type]
        score = build_decision_score(
            proposal,
            risk_warnings=warnings,
            correlated_open_positions=0,
            expected_value=build_expected_value_analysis(_simulation()),
            market_intelligence=default_market_intelligence_state(),
            liquidity=None,
        )
        assert score.risk_score == 100.0

    def test_portfolio_compatibility_score_penalizes_per_correlated_position(
        self,
    ) -> None:
        proposal = _proposal()
        expected_value = build_expected_value_analysis(_simulation())
        no_overlap = build_decision_score(
            proposal,
            risk_warnings=[],
            correlated_open_positions=0,
            expected_value=expected_value,
            market_intelligence=default_market_intelligence_state(),
            liquidity=None,
        )
        some_overlap = build_decision_score(
            proposal,
            risk_warnings=[],
            correlated_open_positions=2,
            expected_value=expected_value,
            market_intelligence=default_market_intelligence_state(),
            liquidity=None,
        )
        assert no_overlap.portfolio_compatibility_score == 100.0
        assert some_overlap.portfolio_compatibility_score == 50.0

    def test_strategy_health_score_is_always_none_for_ordinary_proposals(self) -> None:
        proposal = _proposal()
        score = build_decision_score(
            proposal,
            risk_warnings=[],
            correlated_open_positions=0,
            expected_value=build_expected_value_analysis(_simulation()),
            market_intelligence=default_market_intelligence_state(),
            liquidity=None,
        )
        assert score.strategy_health_score is None

    def test_threshold_and_passed_reflect_the_shared_seventy_point_bar(self) -> None:
        proposal = _proposal(score=95.0, tier="elite")
        score = build_decision_score(
            proposal,
            risk_warnings=[],
            correlated_open_positions=0,
            expected_value=build_expected_value_analysis(_simulation()),
            market_intelligence=default_market_intelligence_state(),
            liquidity=None,
        )
        assert score.threshold == DECISION_SCORE_THRESHOLD
        assert score.passed == (score.overall >= DECISION_SCORE_THRESHOLD)

    def test_liquidity_quality_falls_back_to_a_neutral_default_when_none(self) -> None:
        proposal = _proposal()
        score = build_decision_score(
            proposal,
            risk_warnings=[],
            correlated_open_positions=0,
            expected_value=build_expected_value_analysis(_simulation()),
            market_intelligence=default_market_intelligence_state(),
            liquidity=None,
        )
        assert score.liquidity_quality_score == 50.0

    def test_liquidity_quality_reads_the_real_liquidity_score_when_present(
        self,
    ) -> None:
        proposal = _proposal()
        liquidity = LiquidityRead(
            symbol="NEXA",
            zones=[],
            sweepDetected=False,
            sweepDirection="none",
            liquidityScore=90.0,
            detail="test",
        )  # type: ignore[arg-type]
        score = build_decision_score(
            proposal,
            risk_warnings=[],
            correlated_open_positions=0,
            expected_value=build_expected_value_analysis(_simulation()),
            market_intelligence=default_market_intelligence_state(),
            liquidity=liquidity,
        )
        assert score.liquidity_quality_score == 90.0

    def test_evidence_confluence_score_is_none_when_no_confluence_read_supplied(self) -> None:
        proposal = _proposal()
        score = build_decision_score(
            proposal,
            risk_warnings=[],
            correlated_open_positions=0,
            expected_value=build_expected_value_analysis(_simulation()),
            market_intelligence=default_market_intelligence_state(),
            liquidity=None,
        )
        assert score.evidence_confluence_score is None

    def test_the_composite_renormalizes_over_8_sub_scores_when_confluence_is_real(self) -> None:
        proposal = _proposal()
        expected_value = build_expected_value_analysis(_simulation())
        without_confluence = build_decision_score(
            proposal, risk_warnings=[], correlated_open_positions=0, expected_value=expected_value, market_intelligence=default_market_intelligence_state(), liquidity=None
        )
        with_confluence = build_decision_score(
            proposal,
            risk_warnings=[],
            correlated_open_positions=0,
            expected_value=expected_value,
            market_intelligence=default_market_intelligence_state(),
            liquidity=None,
            evidence_confluence=_confluence(independent_family_count=6, majority="bullish"),
        )
        assert with_confluence.evidence_confluence_score == 100.0
        # Adding a real, high (100.0) 8th sub-score to an otherwise-identical composite
        # can only ever raise or hold the overall average — never lower it.
        assert with_confluence.overall >= without_confluence.overall


def _confluence(*, independent_family_count: int, majority: str, raw_signal_count: int | None = None) -> EvidenceConfluenceRead:
    return EvidenceConfluenceRead(
        symbol="NEXA",
        families=[],
        rawSignalCount=raw_signal_count if raw_signal_count is not None else independent_family_count,
        independentFamilyCount=independent_family_count,
        majorityDirection=majority,  # type: ignore[arg-type]
        agreeingFamilies=[],
        detail="test",
    )


class TestEvidenceConfluenceScore:
    """_evidence_confluence_score() — CEO directive "Professional Quant
    Firm Phase 41-45," Confluence Quality. Every case checks the real
    rule: score reflects independent-family support for THIS proposal's
    own chosen direction, never app/evidence_confluence.py's own
    internal majority taken at face value."""

    def test_none_confluence_reads_none_never_a_fabricated_default(self) -> None:
        assert _evidence_confluence_score(None, "buy") is None

    def test_full_independent_family_agreement_scores_100(self) -> None:
        confluence = _confluence(independent_family_count=TOTAL_DIRECTIONAL_EVIDENCE_FAMILIES, majority="bullish")
        assert _evidence_confluence_score(confluence, "buy") == 100.0

    def test_partial_independent_family_agreement_scores_proportionally(self) -> None:
        confluence = _confluence(independent_family_count=3, majority="bullish")
        assert _evidence_confluence_score(confluence, "buy") == round(3 / TOTAL_DIRECTIONAL_EVIDENCE_FAMILIES * 100, 1)

    def test_evidence_majority_opposing_the_proposals_own_direction_scores_zero(self) -> None:
        # A real, disclosed red flag: the independent evidence's own majority actively
        # disagrees with this proposal's chosen direction — never softened.
        confluence = _confluence(independent_family_count=5, majority="bearish")
        assert _evidence_confluence_score(confluence, "buy") == 0.0

    def test_neutral_market_evidence_scores_a_real_midpoint_not_zero_or_a_fabricated_high(self) -> None:
        confluence = _confluence(independent_family_count=0, majority="neutral")
        assert _evidence_confluence_score(confluence, "buy") == 50.0

    def test_a_wait_recommendation_has_no_real_direction_to_check_against_and_scores_the_midpoint(self) -> None:
        confluence = _confluence(independent_family_count=5, majority="bullish")
        assert _evidence_confluence_score(confluence, "wait") == 50.0

    def test_never_exceeds_100_even_if_independent_family_count_is_somehow_higher_than_the_total(self) -> None:
        confluence = _confluence(independent_family_count=99, majority="bullish")
        assert _evidence_confluence_score(confluence, "buy") == 100.0


class TestBuildContingencyPlan:
    def test_five_real_steps_always_present(self) -> None:
        steps = build_contingency_plan(default_market_intelligence_state(), None)
        assert len(steps) == 5

    def test_none_triggered_on_a_calm_default_market(self) -> None:
        steps = build_contingency_plan(default_market_intelligence_state(), None)
        assert all(not s.triggered for s in steps)

    def test_liquidity_sweep_step_triggers_off_the_real_liquidity_read(self) -> None:
        liquidity = LiquidityRead(
            symbol="NEXA",
            zones=[],
            sweepDetected=True,
            sweepDirection="above_highs",
            liquidityScore=50.0,
            detail="test",
        )  # type: ignore[arg-type]
        steps = build_contingency_plan(default_market_intelligence_state(), liquidity)
        sweep_step = next(s for s in steps if "sweep" in s.condition.lower())
        assert sweep_step.triggered is True

    def test_high_volatility_regime_triggers_the_volatility_step(self) -> None:
        market_intelligence = default_market_intelligence_state().model_copy(
            update={"regime": "high_volatility"}
        )
        steps = build_contingency_plan(market_intelligence, None)
        step = next(s for s in steps if "volatility" in s.condition.lower())
        assert step.triggered is True

    def test_liquidity_hunt_regime_triggers_the_liquidity_hunt_step(self) -> None:
        market_intelligence = default_market_intelligence_state().model_copy(
            update={"regime": "liquidity_hunt"}
        )
        steps = build_contingency_plan(market_intelligence, None)
        step = next(s for s in steps if "liquidity hunt" in s.condition.lower())
        assert step.triggered is True

    def test_elevated_news_risk_triggers_the_news_step(self) -> None:
        news_risk = NewsRiskRead(
            activeMarketNewsCount=3, riskLevel="elevated", detail="test"
        )  # type: ignore[arg-type]
        market_intelligence = default_market_intelligence_state().model_copy(
            update={"news_risk": news_risk}
        )
        steps = build_contingency_plan(market_intelligence, None)
        step = next(s for s in steps if "news" in s.condition.lower())
        assert step.triggered is True

    def test_avoid_trading_quality_tier_triggers_the_quality_step(self) -> None:
        market_intelligence = default_market_intelligence_state()
        quality = market_intelligence.quality.model_copy(
            update={"tier": "avoid_trading"}
        )
        market_intelligence = market_intelligence.model_copy(
            update={"quality": quality}
        )
        steps = build_contingency_plan(market_intelligence, None)
        step = next(s for s in steps if "market quality" in s.condition.lower())
        assert step.triggered is True


class TestEvidenceNeverExceedsConfidence:
    def test_holds_by_construction_for_a_real_proposal(self) -> None:
        assert evidence_never_exceeds_confidence(_proposal()) is True

    def test_holds_even_when_evidence_factors_score_lower_than_consensus_factors(
        self,
    ) -> None:
        factors = [
            ConfidenceFactor(
                name="Multi-Agent Agreement", score=100.0, weight=0.30, detail="d"
            ),
            ConfidenceFactor(
                name="Technical Alignment", score=10.0, weight=0.20, detail="d"
            ),
            ConfidenceFactor(
                name="Risk Conditions", score=100.0, weight=0.20, detail="d"
            ),
            ConfidenceFactor(
                name="Research Confidence", score=10.0, weight=0.15, detail="d"
            ),
            ConfidenceFactor(
                name="News, Macro & Sentiment", score=10.0, weight=0.10, detail="d"
            ),
            ConfidenceFactor(
                name="Portfolio Exposure", score=100.0, weight=0.05, detail="d"
            ),
        ]
        proposal = _proposal(factors=factors, score=68.5)
        assert evidence_never_exceeds_confidence(proposal) is True


class TestCompareScenarioToOutcome:
    def test_within_predicted_range_true_when_outcome_falls_inside_the_closest_scenario(
        self,
    ) -> None:
        simulation = _simulation()
        closest = min(
            [*simulation.scenarios, simulation.baseline],
            key=lambda s: abs((s.reward_range_low_pct + s.reward_range_high_pct) / 2),
        )
        midpoint_pnl = (
            closest.reward_range_low_pct + closest.reward_range_high_pct
        ) / 2
        trade = _trade(pnl_pct=midpoint_pnl)
        comparison = compare_scenario_to_outcome(simulation, trade)
        assert comparison.within_predicted_range is True
        assert "fell inside it" in comparison.detail

    def test_within_predicted_range_false_when_outcome_lands_outside_every_range(
        self,
    ) -> None:
        simulation = _simulation()
        extreme_trade = _trade(pnl_pct=-9999.0)
        comparison = compare_scenario_to_outcome(simulation, extreme_trade)
        assert comparison.within_predicted_range is False
        assert "but outside it" in comparison.detail

    def test_actual_pnl_pct_carries_the_real_trade_outcome(self) -> None:
        simulation = _simulation()
        trade = _trade(pnl_pct=3.3)
        comparison = compare_scenario_to_outcome(simulation, trade)
        assert comparison.actual_pnl_pct == 3.3


class TestBuildWarRoomSession:
    def test_assembles_a_full_session_from_real_artifacts(self) -> None:
        proposal = _proposal()
        session = build_war_room_session(
            "warroom-proposal-1",
            proposal,
            challenge_report=None,
            coach_reports=[],
            market_intelligence=default_market_intelligence_state(),
            decision_vault=[],
            risk_warnings=[],
            correlated_open_positions=0,
            candles=_candles([100.0 + i * 0.5 for i in range(30)]),
            risk_limits=RiskLimits(),
        )
        assert session.id == "warroom-proposal-1"
        assert session.proposal_id == "proposal-1"
        assert session.symbol == "NEXA"
        assert len(session.department_opinions) == 9
        assert len(session.scenario_simulation.scenarios) == 12
        assert session.outcome_comparison is None
        assert session.confidence_validated is True

    def test_no_prior_vault_entries_reports_an_honest_zero_similar_trades(self) -> None:
        proposal = _proposal()
        session = build_war_room_session(
            "warroom-proposal-1",
            proposal,
            challenge_report=None,
            coach_reports=[],
            market_intelligence=default_market_intelligence_state(),
            decision_vault=[],
            risk_warnings=[],
            correlated_open_positions=0,
            candles=_candles([100.0 for _ in range(30)]),
            risk_limits=RiskLimits(),
        )
        assert session.similar_trades.match_count == 0

    def test_evidence_confluence_is_computed_when_real_candles_are_supplied(self) -> None:
        proposal = _proposal()
        session = build_war_room_session(
            "warroom-proposal-1",
            proposal,
            challenge_report=None,
            coach_reports=[],
            market_intelligence=default_market_intelligence_state(),
            decision_vault=[],
            risk_warnings=[],
            correlated_open_positions=0,
            candles=_candles([100.0 + i * 0.5 for i in range(30)]),
            risk_limits=RiskLimits(),
        )
        assert session.evidence_confluence is not None
        assert session.evidence_confluence.symbol == "NEXA"
        assert session.decision_score.evidence_confluence_score is not None

    def test_evidence_confluence_is_none_when_no_real_candles_are_available(self) -> None:
        proposal = _proposal()
        session = build_war_room_session(
            "warroom-proposal-1",
            proposal,
            challenge_report=None,
            coach_reports=[],
            market_intelligence=default_market_intelligence_state(),
            decision_vault=[],
            risk_warnings=[],
            correlated_open_positions=0,
            candles=[],
            risk_limits=RiskLimits(),
        )
        assert session.evidence_confluence is None
        assert session.decision_score.evidence_confluence_score is None

    def test_statistical_correlated_positions_defaults_to_none_build_war_room_session_does_not_set_it(self) -> None:
        # CEO directive "Portfolio Construction, Capital Allocation &
        # Execution Realism," Phase 9 — the real Pearson-correlation
        # count is computed in app/nexus.py (where paper_portfolio/
        # market_data_provider are in scope) and attached via a
        # follow-up .model_copy(), not by build_war_room_session()
        # itself. This confirms that division of responsibility.
        proposal = _proposal()
        session = build_war_room_session(
            "warroom-proposal-1", proposal, challenge_report=None, coach_reports=[], market_intelligence=default_market_intelligence_state(),
            decision_vault=[], risk_warnings=[], correlated_open_positions=0, candles=_candles([100.0 for _ in range(30)]), risk_limits=RiskLimits(),
        )
        assert session.statistical_correlated_positions is None
        updated = session.model_copy(update={"statistical_correlated_positions": 3})
        assert updated.statistical_correlated_positions == 3


class TestWarRoomSessionBackwardCompat:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism," Phase 9 — `WarRoomSession` lives inside the
    persisted `war_room_sessions` LIST, so per app/persistence.py's own
    `_deep_merge_defaults` rule, a new field needs a real Pydantic
    default or an old save's existing sessions fail to validate on load."""

    def test_a_session_persisted_before_this_field_existed_still_validates(self) -> None:
        proposal = _proposal()
        session = build_war_room_session(
            "warroom-proposal-1", proposal, challenge_report=None, coach_reports=[], market_intelligence=default_market_intelligence_state(),
            decision_vault=[], risk_warnings=[], correlated_open_positions=0, candles=_candles([100.0 for _ in range(30)]), risk_limits=RiskLimits(),
        )
        old_save_shape = session.model_dump(by_alias=True)
        del old_save_shape["statisticalCorrelatedPositions"]
        restored = WarRoomSession.model_validate(old_save_shape)
        assert restored.statistical_correlated_positions is None


class TestRecordWarRoomSession:
    def test_caps_at_max_war_room_sessions_oldest_evicted_first(self) -> None:
        proposal = _proposal()
        base = build_war_room_session(
            "warroom-0",
            proposal,
            challenge_report=None,
            coach_reports=[],
            market_intelligence=default_market_intelligence_state(),
            decision_vault=[],
            risk_warnings=[],
            correlated_open_positions=0,
            candles=_candles([100.0 for _ in range(30)]),
            risk_limits=RiskLimits(),
        )
        sessions: list = []
        for i in range(MAX_WAR_ROOM_SESSIONS + 10):
            session = base.model_copy(update={"id": f"warroom-{i}"})
            sessions = record_war_room_session(sessions, session)
        assert len(sessions) == MAX_WAR_ROOM_SESSIONS
        assert sessions[-1].id == f"warroom-{MAX_WAR_ROOM_SESSIONS + 9}"
        assert sessions[0].id == "warroom-10"
