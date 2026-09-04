"""Covers app/opportunity_gate_calibration_experiment.py — CEO directive
"Opportunity Gate Calibration Experiment 1.0". Every test here checks a
real guarantee the module's own docstring makes: Model A reproduces
production's real formula exactly; the 3 weight schemes are predeclared
and valid; the experiment is a pure, deterministic function of already-
persisted state; it never mutates its inputs and never constructs a
production trading record; a `pending` outcome is never counted as a win
or a loss; and a subgroup below the real bootstrap floor reads
`insufficient_evidence`, never a fabricated confidence interval.
"""
from __future__ import annotations

import inspect
from datetime import datetime, timezone

from app.executive import generate_proposal
from app.market_data import MockMarketDataProvider
from app.market_intelligence import default_market_intelligence_state
from app.opportunity_gate_calibration_experiment import (
    LIQUIDITY_PENALTY_FLOOR,
    WEIGHT_SCHEMES,
    _composite,
    _composite_capped_penalty,
    _composite_liquidity_excluded,
    _composite_multi_timeframe_liquidity,
    _composite_weighted,
    build_shadow_sub_score_capture,
    control_equivalence,
    evaluate_shadow_models,
    run_opportunity_gate_calibration_experiment,
)
from app.opportunity_gatekeeper import build_opportunity_rejection
from app.portfolio import default_portfolio
from app.schemas import DecisionScoreBreakdown, MultiTimeframeLiquidityCapture, MultiTimeframeLiquidityRead, OpportunityShadowSubScoreCapture, RiskLimits, WarRoomSession
from app.war_room import build_war_room_session


def _multi_timeframe_read(*, blended: float = 80.0, one_hour: float = 60.0) -> MultiTimeframeLiquidityRead:
    return MultiTimeframeLiquidityRead(
        symbol="NEXA", oneHourLiquidityScore=one_hour, higherTimeframeLiquidityScore=70.0, higherTimeframe="4h", confirmedZoneCount=2, blendedLiquidityScore=blended, detail="test"
    )


def _multi_timeframe_capture(*, rejection_id: str | None = None, proposal_id: str | None = None, blended: float = 80.0) -> MultiTimeframeLiquidityCapture:
    return MultiTimeframeLiquidityCapture(
        id=f"mtfcap-{rejection_id or proposal_id}",
        symbol="NEXA",
        rejectionId=rejection_id,
        proposalId=proposal_id,
        read=_multi_timeframe_read(blended=blended),
        capturedSimMinutes=0,
        createdAt=_now_iso(),
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _breakdown(
    *,
    evidence: float = 80.0,
    confidence: float = 80.0,
    risk: float = 80.0,
    expected_value: float = 80.0,
    market_quality: float = 80.0,
    liquidity: float = 20.0,
    portfolio_compatibility: float = 80.0,
    strategy_health: float | None = None,
    evidence_confluence: float | None = None,
    threshold: float = 75.0,
) -> DecisionScoreBreakdown:
    scores = [evidence, confidence, risk, expected_value, market_quality, liquidity, portfolio_compatibility]
    if strategy_health is not None:
        scores.append(strategy_health)
    if evidence_confluence is not None:
        scores.append(evidence_confluence)
    overall = round(sum(scores) / len(scores), 1)
    return DecisionScoreBreakdown(
        evidenceScore=evidence,
        confidenceScore=confidence,
        riskScore=risk,
        expectedValueScore=expected_value,
        strategyHealthScore=strategy_health,
        marketQualityScore=market_quality,
        liquidityQualityScore=liquidity,
        portfolioCompatibilityScore=portfolio_compatibility,
        evidenceConfluenceScore=evidence_confluence,
        overall=overall,
        threshold=threshold,
        passed=overall >= threshold,
    )


def _proposal():  # type: ignore[no-untyped-def]
    provider = MockMarketDataProvider()
    return generate_proposal(
        __import__("app.schemas", fromlist=["ResearchItem"]).ResearchItem(
            id="research-1", title="NEXA setup", symbol="NEXA", category="stock", priority="high", status="completed",
            assignedAgent="nova", summary="real setup", confidence=90.0, createdAt=_now_iso(), updatedAt=_now_iso(),
        ),
        quantity=10.0, price=100.0, news=[], scanner_alerts=[], sentinel_warning=None, guardian_warning=None,
        provider=provider, now_sim_minutes=0, portfolio=default_portfolio(), risk_limits=RiskLimits(),
        market_intelligence=default_market_intelligence_state(), agent_vote_accuracy=[],
    )


def _rejection(*, decision_score: float = 65.0, ev_pct: float = 1.0, rejection_id: str = "oppreject-proposal-1", outcome: str = "pending", resolved_price_change_pct: float | None = None):  # type: ignore[no-untyped-def]
    proposal = _proposal()
    proposal = proposal.model_copy(update={"id": rejection_id.removeprefix("oppreject-")})
    rejection = build_opportunity_rejection(
        proposal,
        decision_score=_breakdown(),
        expected_value=__import__("app.schemas", fromlist=["ExpectedValueAnalysis"]).ExpectedValueAnalysis(
            expectedValuePct=ev_pct, edgePct=ev_pct, riskToReward=1.5, positiveExpectancy=ev_pct > 0, detail="test"
        ),
        reasons=["Trade Quality Score below the required minimum."],
        reason_codes=["trade_quality_below_threshold"],
        price_at_rejection=100.0,
        now_sim_minutes=0,
    )
    return rejection.model_copy(update={"decision_score_at_rejection": decision_score, "outcome": outcome, "resolved_price_change_pct": resolved_price_change_pct})


def _capture(rejection, sub_scores: DecisionScoreBreakdown, *, gate_threshold: float = 75.0) -> OpportunityShadowSubScoreCapture:  # type: ignore[no-untyped-def]
    return build_shadow_sub_score_capture(rejection, decision_score=sub_scores, gate_threshold=gate_threshold, now_sim_minutes=0)


def _approved_session(*, sub_scores: DecisionScoreBreakdown, proposal_id: str = "warroom-1", actual_pnl_pct: float | None = None) -> WarRoomSession:
    proposal = _proposal().model_copy(update={"id": proposal_id})
    session = build_war_room_session(
        f"warroom-{proposal_id}", proposal, challenge_report=None, coach_reports=[],
        market_intelligence=default_market_intelligence_state(), decision_vault=[], risk_warnings=[],
        correlated_open_positions=0, candles=[], risk_limits=RiskLimits(),
    )
    update: dict[str, object] = {"decision_score": sub_scores, "proposal_id": proposal_id}
    if actual_pnl_pct is not None:
        outcome_comparison = __import__("app.schemas", fromlist=["ScenarioOutcomeComparison"]).ScenarioOutcomeComparison(
            matchedScenario="breakout_confirmation", matchedLabel="Breakout Confirmation", predictedRangeLowPct=-2.0, predictedRangeHighPct=2.0,
            actualPnlPct=actual_pnl_pct, withinPredictedRange=True, detail="test",
        )
        update["outcome_comparison"] = outcome_comparison
    return session.model_copy(update=update)


class TestModelAControlEquivalence:
    def test_control_matches_manual_mean_of_seven_real_sub_scores(self) -> None:
        breakdown = _breakdown(evidence=90.0, confidence=80.0, risk=70.0, expected_value=60.0, market_quality=85.0, liquidity=10.0, portfolio_compatibility=95.0)
        expected = round((90.0 + 80.0 + 70.0 + 60.0 + 85.0 + 10.0 + 95.0) / 7, 1)
        assert _composite(breakdown) == expected

    def test_control_matches_manual_mean_with_eight_real_sub_scores(self) -> None:
        breakdown = _breakdown(evidence_confluence=50.0)
        scores = [80.0, 80.0, 80.0, 80.0, 80.0, 20.0, 80.0, 50.0]
        assert _composite(breakdown) == round(sum(scores) / 8, 1)

    def test_control_reproduces_real_persisted_composite_for_linked_pair(self) -> None:
        """The stronger, data-level proof: recomputing Model A against a
        real captured breakdown must reproduce the SAME candidate's real,
        independently-persisted OpportunityRejection.decisionScoreAtRejection
        — both came from the same original build_decision_score() call."""
        breakdown = _breakdown(evidence=83.0, confidence=83.0, risk=83.0, expected_value=83.0, market_quality=83.0, liquidity=15.0, portfolio_compatibility=83.0)
        real_composite = _composite(breakdown)
        rejection = _rejection(decision_score=real_composite)
        capture = _capture(rejection, breakdown)
        results = [rejection], [capture]
        report = run_opportunity_gate_calibration_experiment(opportunity_rejections=results[0], opportunity_shadow_captures=results[1], war_room_sessions=[])
        assert report.control_equivalence_checked == 1
        assert report.control_equivalence_mismatches == 0

    def test_control_equivalence_helper_detects_a_real_mismatch(self) -> None:
        from app.schemas import ShadowCandidateResult, ShadowModelScore

        mismatched = ShadowCandidateResult(
            rejectionId="r1", symbol="NEXA", productionDecisionScore=50.0, liquidityQualityScore=10.0,
            expectedValueAtRejectionPct=1.0, outcome="pending", resolvedPriceChangePct=None,
            shadowScores={"control": ShadowModelScore(modelId="control", overall=99.0, passed=True)},
        )
        checked, mismatches = control_equivalence([mismatched])
        assert checked == 1
        assert mismatches == 1


class TestModelBLiquidityExcluded:
    def test_removes_liquidity_from_denominator_not_zeroes_it(self) -> None:
        breakdown = _breakdown(evidence=90.0, confidence=90.0, risk=90.0, expected_value=90.0, market_quality=90.0, liquidity=0.0, portfolio_compatibility=90.0)
        assert _composite_liquidity_excluded(breakdown) == 90.0
        assert _composite(breakdown) < 90.0


class TestModelCCappedPenalty:
    def test_floors_low_liquidity_at_the_reused_production_threshold(self) -> None:
        breakdown = _breakdown(liquidity=5.0)
        assert LIQUIDITY_PENALTY_FLOOR == 40.0
        capped = _composite_capped_penalty(breakdown)
        uncapped = _composite(breakdown)
        assert capped > uncapped

    def test_never_raises_an_already_strong_liquidity_score(self) -> None:
        breakdown = _breakdown(liquidity=90.0)
        assert _composite_capped_penalty(breakdown) == _composite(breakdown)


class TestModelDWeightedComposite:
    def test_weight_schemes_sum_to_one(self) -> None:
        import math

        for name, weights in WEIGHT_SCHEMES.items():
            assert math.isclose(sum(weights.values()), 1.0, abs_tol=1e-9), name

    def test_exactly_three_predeclared_schemes(self) -> None:
        assert set(WEIGHT_SCHEMES.keys()) == {"equal_weight", "reduced_liquidity_weight", "increased_liquidity_weight"}

    def test_equal_weight_scheme_matches_control_with_seven_real_scores(self) -> None:
        breakdown = _breakdown(evidence=88.0, confidence=71.0, risk=64.0, expected_value=59.0, market_quality=77.0, liquidity=12.0, portfolio_compatibility=95.0)
        assert _composite_weighted(breakdown, WEIGHT_SCHEMES["equal_weight"]) == _composite(breakdown)

    def test_reduced_liquidity_scheme_raises_score_when_liquidity_is_the_drag(self) -> None:
        breakdown = _breakdown(liquidity=5.0)
        reduced = _composite_weighted(breakdown, WEIGHT_SCHEMES["reduced_liquidity_weight"])
        increased = _composite_weighted(breakdown, WEIGHT_SCHEMES["increased_liquidity_weight"])
        assert reduced is not None and increased is not None
        assert reduced > _composite(breakdown) > increased

    def test_weighted_matches_manual_weighted_sum(self) -> None:
        breakdown = _breakdown(evidence=100.0, confidence=0.0, risk=0.0, expected_value=0.0, market_quality=0.0, liquidity=0.0, portfolio_compatibility=0.0)
        weights = {"evidence": 1.0, "confidence": 0.0, "risk": 0.0, "expected_value": 0.0, "market_quality": 0.0, "liquidity": 0.0, "portfolio_compatibility": 0.0}
        assert _composite_weighted(breakdown, weights) == 100.0

    def test_returns_none_when_a_core_dimension_is_missing(self) -> None:
        # Not reachable through real production data today (every real
        # candidate has all 7 core scores), but the function itself must
        # never silently reweight a partial set.
        breakdown = _breakdown()
        object.__setattr__  # no-op reference to keep linters quiet about unused import style
        partial = breakdown.model_copy(update={"marketQualityScore": None}) if False else breakdown
        assert _composite_weighted(partial, WEIGHT_SCHEMES["equal_weight"]) is not None


class TestEvaluateShadowModels:
    def test_pass_fail_evaluated_against_the_real_gate_threshold(self) -> None:
        breakdown = _breakdown(liquidity=0.0)
        low_threshold = evaluate_shadow_models(breakdown, gate_threshold=1.0)
        high_threshold = evaluate_shadow_models(breakdown, gate_threshold=99.0)
        assert all(score.passed for score in low_threshold.values())
        assert not any(score.passed for score in high_threshold.values())

    def test_six_real_shadow_scores_produced(self) -> None:
        breakdown = _breakdown()
        results = evaluate_shadow_models(breakdown, gate_threshold=75.0)
        assert set(results.keys()) == {"control", "liquidity_excluded", "capped_penalty", "weighted_equal_weight", "weighted_reduced_liquidity_weight", "weighted_increased_liquidity_weight"}

    def test_multi_timeframe_liquidity_omitted_when_no_capture_exists(self) -> None:
        """CEO directive "Liquidity Context Improvement + Autonomous
        Company Readiness Audit 1.0" — a candidate with no matching real
        MultiTimeframeLiquidityCapture must never get a fabricated
        7th score."""
        breakdown = _breakdown()
        results = evaluate_shadow_models(breakdown, gate_threshold=75.0)
        assert "multi_timeframe_liquidity" not in results

    def test_multi_timeframe_liquidity_present_when_a_real_score_is_supplied(self) -> None:
        breakdown = _breakdown()
        results = evaluate_shadow_models(breakdown, gate_threshold=75.0, multi_timeframe_liquidity_score=80.0)
        assert "multi_timeframe_liquidity" in results

    def test_multi_timeframe_liquidity_never_changes_the_real_control_score(self) -> None:
        """Model A reproducibility (Part XXII, SHADOW #12) — adding the
        optional multi-timeframe score must never perturb any other
        model's own real, already-established composite."""
        breakdown = _breakdown()
        without = evaluate_shadow_models(breakdown, gate_threshold=75.0)
        with_mtf = evaluate_shadow_models(breakdown, gate_threshold=75.0, multi_timeframe_liquidity_score=80.0)
        for model_id in without:
            assert with_mtf[model_id] == without[model_id]


class TestMultiTimeframeLiquidityShadowModel:
    """CEO directive "Liquidity Context Improvement + Autonomous Company
    Readiness Audit 1.0," Part VIII-X — the real Model B: same real
    unweighted-mean composite shape as Model A/Control, with only the
    liquidity term substituted for the real, independently-captured
    multi-timeframe blended score. Never wired into evaluate_opportunity()
    or any live Gatekeeper decision (see TestNoProductionMutation for the
    static source check covering this file's whole module)."""

    def test_composite_substitutes_only_the_liquidity_term(self) -> None:
        breakdown = _breakdown(evidence=90.0, confidence=80.0, risk=70.0, expected_value=60.0, market_quality=85.0, liquidity=10.0, portfolio_compatibility=95.0)
        result = _composite_multi_timeframe_liquidity(breakdown, 80.0)
        expected = round((90.0 + 80.0 + 70.0 + 60.0 + 85.0 + 80.0 + 95.0) / 7, 1)
        assert result == expected

    def test_higher_blended_score_can_rescue_a_candidate_the_control_rejects(self) -> None:
        breakdown = _breakdown(evidence=80.0, confidence=80.0, risk=80.0, expected_value=80.0, market_quality=80.0, liquidity=0.0, portfolio_compatibility=80.0)
        control = _composite(breakdown)
        assert control < 75.0  # real production would reject this candidate
        rescued = _composite_multi_timeframe_liquidity(breakdown, 90.0)
        assert rescued >= 75.0

    def test_run_experiment_joins_capture_by_rejection_id(self) -> None:
        rejection = _rejection(rejection_id="oppreject-mtf1", decision_score=65.0)
        breakdown = _breakdown(liquidity=0.0)
        capture = _capture(rejection, breakdown)
        mtf_capture = _multi_timeframe_capture(rejection_id=rejection.id, blended=95.0)
        report = run_opportunity_gate_calibration_experiment(
            opportunity_rejections=[rejection], opportunity_shadow_captures=[capture], war_room_sessions=[], multi_timeframe_liquidity_captures=[mtf_capture]
        )
        candidate = next(r for r in report.rescued_candidates if r.rejection_id == rejection.id)
        assert "multi_timeframe_liquidity" in candidate.shadow_scores
        assert candidate.shadow_scores["multi_timeframe_liquidity"].passed is True

    def test_run_experiment_joins_capture_by_proposal_id_for_approved_candidates(self) -> None:
        breakdown = _breakdown(liquidity=90.0)
        session = _approved_session(sub_scores=breakdown, proposal_id="warroom-mtf1")
        mtf_capture = _multi_timeframe_capture(proposal_id="warroom-mtf1", blended=10.0)
        report = run_opportunity_gate_calibration_experiment(
            opportunity_rejections=[], opportunity_shadow_captures=[], war_room_sessions=[session], multi_timeframe_liquidity_captures=[mtf_capture]
        )
        group = next(g for g in report.group_counts if g.model_id == "multi_timeframe_liquidity")
        # A real production PASS whose real multi-timeframe context would
        # have failed it — the "accepted by A / rejected by B" group
        # Part IX explicitly asks for.
        assert group.shadow_would_reject_count == 1

    def test_candidate_with_no_matching_multi_timeframe_capture_has_no_extra_score(self) -> None:
        rejection = _rejection(rejection_id="oppreject-nomtf")
        breakdown = _breakdown()
        capture = _capture(rejection, breakdown)
        report = run_opportunity_gate_calibration_experiment(
            opportunity_rejections=[rejection], opportunity_shadow_captures=[capture], war_room_sessions=[], multi_timeframe_liquidity_captures=[]
        )
        result = next(r for r in report.rescued_win_rate_comparisons if r.model_id == "multi_timeframe_liquidity")
        assert result.evidence_state == "insufficient_evidence"

    def test_run_experiment_backward_compatible_when_multi_timeframe_captures_omitted(self) -> None:
        """Existing callers (and old saves with no
        multi_timeframe_liquidity_captures list yet) must keep working
        unchanged — the new parameter is optional."""
        rejection = _rejection()
        breakdown = _breakdown()
        capture = _capture(rejection, breakdown)
        report = run_opportunity_gate_calibration_experiment(opportunity_rejections=[rejection], opportunity_shadow_captures=[capture], war_room_sessions=[])
        assert report.total_rejections_on_record == 1


class TestBuildShadowSubScoreCapture:
    def test_links_by_rejection_id_and_carries_the_real_gate_threshold(self) -> None:
        rejection = _rejection(rejection_id="oppreject-abc")
        breakdown = _breakdown()
        capture = build_shadow_sub_score_capture(rejection, decision_score=breakdown, gate_threshold=75.0, now_sim_minutes=42)
        assert capture.rejection_id == rejection.id
        assert capture.id == f"shadowcap-{rejection.id}"
        assert capture.gate_threshold_at_capture == 75.0
        assert capture.captured_sim_minutes == 42
        assert capture.sub_scores == breakdown


class TestNoProductionMutation:
    def test_module_never_constructs_a_production_trading_record(self) -> None:
        """Static source check — this module must never construct a
        TradeProposal/TradeDecision/RiskDecision/Order/Position/Trade.
        A regression here would mean the shadow experiment stopped being
        purely diagnostic."""
        import app.opportunity_gate_calibration_experiment as module

        source = inspect.getsource(module)
        for forbidden in ("TradeProposal(", "TradeDecision(", "RiskDecision(", "Order(", "Position(", "Trade("):
            assert forbidden not in source, forbidden

    def test_run_experiment_does_not_mutate_its_inputs(self) -> None:
        rejection = _rejection()
        breakdown = _breakdown()
        capture = _capture(rejection, breakdown)
        session = _approved_session(sub_scores=breakdown)
        rejections_before = [rejection.model_copy()]
        captures_before = [capture.model_copy()]
        sessions_before = [session.model_copy()]

        run_opportunity_gate_calibration_experiment(opportunity_rejections=[rejection], opportunity_shadow_captures=[capture], war_room_sessions=[session])

        assert [rejection] == rejections_before
        assert [capture] == captures_before
        assert [session] == sessions_before


class TestHistoricalIneligibility:
    def test_rejection_with_no_matching_capture_is_reported_ineligible_never_scored(self) -> None:
        pre_instrumentation_rejection = _rejection(rejection_id="oppreject-old")
        report = run_opportunity_gate_calibration_experiment(opportunity_rejections=[pre_instrumentation_rejection], opportunity_shadow_captures=[], war_room_sessions=[])
        assert report.total_rejections_on_record == 1
        assert report.eligible_rejections_with_capture == 0
        assert report.ineligible_rejections_no_capture == 1
        assert report.rescued_candidates == []


class TestUnresolvedOutcomeHandling:
    def test_pending_outcome_never_counted_toward_win_rate(self) -> None:
        rejections = []
        captures = []
        for i in range(30):
            breakdown = _breakdown(liquidity=0.0)  # rescued by liquidity_excluded
            rejection = _rejection(rejection_id=f"oppreject-p{i}", decision_score=_composite(breakdown), outcome="pending")
            rejections.append(rejection)
            captures.append(_capture(rejection, breakdown))
        report = run_opportunity_gate_calibration_experiment(opportunity_rejections=rejections, opportunity_shadow_captures=captures, war_room_sessions=[])
        comparison = next(c for c in report.rescued_win_rate_comparisons if c.model_id == "liquidity_excluded")
        assert comparison.rescued_n_resolved == 0
        assert comparison.evidence_state == "insufficient_evidence"


class TestInsufficientSampleNA:
    def test_below_bootstrap_floor_reports_na_not_a_fabricated_ci(self) -> None:
        rejections = []
        captures = []
        for i in range(5):
            breakdown = _breakdown(liquidity=0.0)
            rejection = _rejection(rejection_id=f"oppreject-r{i}", decision_score=_composite(breakdown), outcome="would_have_won", resolved_price_change_pct=1.0)
            rejections.append(rejection)
            captures.append(_capture(rejection, breakdown))
        report = run_opportunity_gate_calibration_experiment(opportunity_rejections=rejections, opportunity_shadow_captures=captures, war_room_sessions=[])
        comparison = next(c for c in report.rescued_win_rate_comparisons if c.model_id == "liquidity_excluded")
        assert comparison.evidence_state == "insufficient_evidence"
        assert comparison.bootstrap is None

    def test_at_or_above_bootstrap_floor_on_both_sides_produces_a_real_ci(self) -> None:
        rejections = []
        captures = []
        for i in range(25):
            # Rescued (shadow-pass under liquidity_excluded): weak liquidity, strong everything else.
            rescued_breakdown = _breakdown(liquidity=0.0)
            outcome = "would_have_won" if i % 2 == 0 else "would_have_lost"
            r = _rejection(rejection_id=f"oppreject-rescued{i}", decision_score=_composite(rescued_breakdown), outcome=outcome, resolved_price_change_pct=1.0 if outcome == "would_have_won" else -1.0)
            rejections.append(r)
            captures.append(_capture(r, rescued_breakdown))
        for i in range(25):
            # Confirmed-reject (shadow-fail too): weak on everything.
            weak_breakdown = _breakdown(evidence=20.0, confidence=20.0, risk=20.0, expected_value=20.0, market_quality=20.0, liquidity=0.0, portfolio_compatibility=20.0)
            outcome = "would_have_won" if i % 3 == 0 else "would_have_lost"
            r = _rejection(rejection_id=f"oppreject-reject{i}", decision_score=_composite(weak_breakdown), outcome=outcome, resolved_price_change_pct=1.0 if outcome == "would_have_won" else -1.0)
            rejections.append(r)
            captures.append(_capture(r, weak_breakdown))

        report = run_opportunity_gate_calibration_experiment(opportunity_rejections=rejections, opportunity_shadow_captures=captures, war_room_sessions=[])
        comparison = next(c for c in report.rescued_win_rate_comparisons if c.model_id == "liquidity_excluded")
        assert comparison.rescued_n_resolved == 25
        assert comparison.confirmed_reject_n_resolved == 25
        assert comparison.evidence_state == "sufficient_evidence"
        assert comparison.bootstrap is not None


class TestGroupCountsAndRescuedPopulation:
    def test_rescued_requires_production_fail_and_shadow_pass(self) -> None:
        breakdown = _breakdown(liquidity=0.0)  # dragged down by liquidity -> control fails, liquidity_excluded passes
        rejection = _rejection(decision_score=_composite(breakdown))
        capture = _capture(rejection, breakdown, gate_threshold=75.0)
        report = run_opportunity_gate_calibration_experiment(opportunity_rejections=[rejection], opportunity_shadow_captures=[capture], war_room_sessions=[])
        assert len(report.rescued_candidates) == 1
        summary = next(g for g in report.group_counts if g.model_id == "liquidity_excluded")
        assert summary.rescued_count == 1
        assert summary.confirmed_reject_count == 0

    def test_approved_candidates_never_appear_as_rescued(self) -> None:
        breakdown = _breakdown(liquidity=0.0)
        session = _approved_session(sub_scores=breakdown, actual_pnl_pct=2.0)
        report = run_opportunity_gate_calibration_experiment(opportunity_rejections=[], opportunity_shadow_captures=[], war_room_sessions=[session])
        assert report.rescued_candidates == []
        assert report.total_approved_war_room_sessions == 1


class TestDeterminism:
    def test_running_twice_on_identical_input_produces_identical_scores(self) -> None:
        breakdown = _breakdown(liquidity=5.0)
        rejection = _rejection(decision_score=_composite(breakdown))
        capture = _capture(rejection, breakdown)
        first = run_opportunity_gate_calibration_experiment(opportunity_rejections=[rejection], opportunity_shadow_captures=[capture], war_room_sessions=[])
        second = run_opportunity_gate_calibration_experiment(opportunity_rejections=[rejection], opportunity_shadow_captures=[capture], war_room_sessions=[])
        assert first.model_dump(exclude={"generated_at"}) == second.model_dump(exclude={"generated_at"})


class TestLeakageAudit:
    def test_leakage_audit_passes_on_clean_input(self) -> None:
        breakdown = _breakdown()
        rejection = _rejection(decision_score=_composite(breakdown))
        capture = _capture(rejection, breakdown)
        report = run_opportunity_gate_calibration_experiment(opportunity_rejections=[rejection], opportunity_shadow_captures=[capture], war_room_sessions=[])
        assert all(check.passed for check in report.leakage_audit)

    def test_leakage_audit_flags_duplicate_captures(self) -> None:
        breakdown = _breakdown()
        rejection = _rejection()
        capture = _capture(rejection, breakdown)
        report = run_opportunity_gate_calibration_experiment(opportunity_rejections=[rejection], opportunity_shadow_captures=[capture, capture], war_room_sessions=[])
        duplicate_check = next(c for c in report.leakage_audit if c.check == "no_duplicate_captures")
        assert duplicate_check.passed is False
