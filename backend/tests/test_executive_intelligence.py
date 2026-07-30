"""Covers app/executive_intelligence.py — v0.7 Feature 50 (Part 1), the
Executive Intelligence Network's real "combine every perspective"
synthesis layer. Every DepartmentOpinion must trace back to a real
existing field on the proposal/ChallengeReport/CoachReport it reads,
never a fabricated read, and honest "not yet" states must appear when
the backing signal genuinely doesn't exist yet (no ChallengeReport, no
CoachReport).
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.executive_intelligence import (
    compute_executive_recommendation,
    generate_department_opinions,
    generate_meeting_log_entry,
    generate_weekly_self_evaluations,
    record_meeting_log_entry,
    record_self_evaluations,
)
from app.market_intelligence import default_market_intelligence_state
from app.schemas import AnalystVote, ChallengeReport, CoachReport, ConfidenceFactor, DecisionConfidence, ExecutiveMeetingLogEntry, TradeDecision, TradeProposal


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_DEFAULT_FACTORS = [
    ConfidenceFactor(name="agreement", score=90.0, weight=0.30, detail="d"),
    ConfidenceFactor(name="technical", score=80.0, weight=0.20, detail="d"),
    ConfidenceFactor(name="risk", score=85.0, weight=0.20, detail="d"),
    ConfidenceFactor(name="research", score=80.0, weight=0.15, detail="d"),
    ConfidenceFactor(name="sentiment", score=75.0, weight=0.10, detail="d"),
    ConfidenceFactor(name="exposure", score=90.0, weight=0.05, detail="d"),
]


def _proposal(*, tier: str = "strong", score: float = 90.0, risk_vote_choice: str = "buy", risk_summary: str = "Within all configured risk limits.", factors: list[ConfidenceFactor] | None = None) -> TradeProposal:
    return TradeProposal(
        id="proposal-1",
        symbol="NEXA",
        category="stock",
        quantity=1.0,
        price=100.0,
        confidence=score,
        analystVotes=[AnalystVote(role="risk", agentId="sentinel", choice=risk_vote_choice, reasoning="Position sized within limits.", evidence=["Real risk read"])],  # type: ignore[arg-type]
        overallRecommendation="buy",
        researchSummary="Nova's research backs this setup with a completed research item.",
        riskSummary=risk_summary,
        confidenceEngine=DecisionConfidence(score=score, tier=tier, summary="A well-supported setup.", factors=_DEFAULT_FACTORS if factors is None else factors),  # type: ignore[arg-type]
        createdAt=_now_iso(),
        createdSimMinutes=0,
    )


def _challenge_report(*, severity: str = "none_found", historical_comparisons: list[str] | None = None, worst_case: str = "Bearish reversal drops the position 4% before recovering.") -> ChallengeReport:
    return ChallengeReport(
        id="challenge-1",
        proposalId="proposal-1",
        symbol="NEXA",
        assignedAgent="atlas",
        tradeSummary="Buy NEXA",
        bullCase="Strong technical setup.",
        bearCase="Could reverse on macro news.",
        hiddenRisks=[],
        weakAssumptions=[],
        missingEvidence=[],
        historicalComparisons=historical_comparisons or [],
        worstCaseScenario=worst_case,
        suggestedImprovements=[],
        severity=severity,  # type: ignore[arg-type]
        finalRecommendation="Proceed with normal sizing." if severity == "none_found" else "Reduce size before proceeding.",
        citedArticleIds=[],
        createdAt=_now_iso(),
    )


def _coach_report(*, company_score: float = 70.0) -> CoachReport:
    return CoachReport(
        id="report-1",
        period="weekly",
        companyScore=company_score,
        agentRankings=[],
        researchAccuracy=80.0,
        winRate=60.0,
        lossRate=40.0,
        averageConfidence=75.0,
        riskScore=80.0,
        commonMistakes=[],
        strengths=["Consistent process discipline"],
        recommendations=[],
        createdAt=_now_iso(),
    )


class TestGenerateDepartmentOpinions:
    def test_all_nine_departments_produce_an_opinion(self) -> None:
        opinions = generate_department_opinions(_proposal(), None, [], default_market_intelligence_state())
        roles = {o.role for o in opinions}
        assert roles == {"research", "quant", "risk", "simulation", "decision_intelligence", "coach", "founders", "devils_advocate", "market_intelligence"}

    def test_research_opinion_reuses_the_real_research_summary(self) -> None:
        proposal = _proposal()
        opinions = generate_department_opinions(proposal, None, [], default_market_intelligence_state())
        research = next(o for o in opinions if o.role == "research")
        assert research.summary == proposal.research_summary

    def test_risk_opinion_reuses_the_real_risk_summary(self) -> None:
        proposal = _proposal(risk_summary="Sector concentration limit reached.")
        opinions = generate_department_opinions(proposal, None, [], default_market_intelligence_state())
        risk = next(o for o in opinions if o.role == "risk")
        assert risk.summary == "Sector concentration limit reached."

    def test_risk_dissents_when_the_risk_analyst_voted_wait(self) -> None:
        proposal = _proposal(risk_vote_choice="wait")
        opinions = generate_department_opinions(proposal, None, [], default_market_intelligence_state())
        risk = next(o for o in opinions if o.role == "risk")
        assert risk.stance == "disagree"

    def test_simulation_is_honestly_not_yet_stress_tested_without_a_challenge_report(self) -> None:
        opinions = generate_department_opinions(_proposal(), None, [], default_market_intelligence_state())
        simulation = next(o for o in opinions if o.role == "simulation")
        assert simulation.stance == "request_more_research"
        assert "not yet" in simulation.summary.lower()

    def test_simulation_reads_the_real_worst_case_scenario_off_the_challenge_report(self) -> None:
        report = _challenge_report(worst_case="Flash crash wipes out 8% in one bar.")
        opinions = generate_department_opinions(_proposal(), report, [], default_market_intelligence_state())
        simulation = next(o for o in opinions if o.role == "simulation")
        assert "Flash crash wipes out 8%" in simulation.summary

    def test_devils_advocate_is_honestly_not_yet_challenged_without_a_report(self) -> None:
        opinions = generate_department_opinions(_proposal(), None, [], default_market_intelligence_state())
        devils_advocate = next(o for o in opinions if o.role == "devils_advocate")
        assert devils_advocate.stance == "request_more_research"
        assert "not yet challenged" in devils_advocate.summary.lower()

    def test_devils_advocate_reads_the_real_final_recommendation_off_the_challenge_report(self) -> None:
        report = _challenge_report(severity="major")
        opinions = generate_department_opinions(_proposal(), report, [], default_market_intelligence_state())
        devils_advocate = next(o for o in opinions if o.role == "devils_advocate")
        assert devils_advocate.stance == "recommend_rejecting"
        assert devils_advocate.summary == report.final_recommendation

    def test_founders_is_honest_about_no_history_when_no_comparisons_exist(self) -> None:
        report = _challenge_report(historical_comparisons=[])
        opinions = generate_department_opinions(_proposal(), report, [], default_market_intelligence_state())
        founders = next(o for o in opinions if o.role == "founders")
        assert founders.stance == "agree"
        assert "no past company history" in founders.summary.lower()

    def test_founders_reuses_the_real_historical_comparison_titles(self) -> None:
        report = _challenge_report(historical_comparisons=["Chased a breakout that reversed (NEXA, Day 12)"])
        opinions = generate_department_opinions(_proposal(), report, [], default_market_intelligence_state())
        founders = next(o for o in opinions if o.role == "founders")
        assert founders.stance == "recommend_waiting"
        assert "Chased a breakout that reversed" in founders.summary

    def test_coach_is_honest_about_no_report_yet(self) -> None:
        opinions = generate_department_opinions(_proposal(), None, [], default_market_intelligence_state())
        coach = next(o for o in opinions if o.role == "coach")
        assert "no coach report" in coach.summary.lower()

    def test_coach_reuses_the_real_latest_report(self) -> None:
        report = _coach_report(company_score=85.0)
        opinions = generate_department_opinions(_proposal(), None, [report], default_market_intelligence_state())
        coach = next(o for o in opinions if o.role == "coach")
        assert coach.summary == "Consistent process discipline"
        assert coach.confidence_pct == 85.0

    def test_decision_intelligence_reuses_the_real_confidence_engine(self) -> None:
        proposal = _proposal(tier="poor", score=20.0)
        opinions = generate_department_opinions(proposal, None, [], default_market_intelligence_state())
        decision_intelligence = next(o for o in opinions if o.role == "decision_intelligence")
        assert decision_intelligence.stance == "recommend_rejecting"
        assert decision_intelligence.confidence_pct == 20.0
        assert decision_intelligence.summary == proposal.confidence_engine.summary

    def test_quant_reads_real_technical_and_research_factors(self) -> None:
        factors = [ConfidenceFactor(name="technical", score=80.0, weight=0.2, detail="d"), ConfidenceFactor(name="research", score=60.0, weight=0.15, detail="d")]
        proposal = _proposal(factors=factors)
        opinions = generate_department_opinions(proposal, None, [], default_market_intelligence_state())
        quant = next(o for o in opinions if o.role == "quant")
        assert quant.confidence_pct == 70.0  # (80 + 60) / 2
        assert "80" in quant.summary and "60" in quant.summary


class TestComputeExecutiveRecommendation:
    def test_no_concerns_recommends_trading_normally(self) -> None:
        proposal = _proposal(tier="elite", score=96.0)
        report = _challenge_report(severity="none_found")
        opinions = generate_department_opinions(proposal, report, [_coach_report(company_score=90.0)], default_market_intelligence_state())
        recommendation = compute_executive_recommendation(proposal, opinions)
        assert recommendation.action == "trade_normally"
        assert recommendation.proposal_id == "proposal-1"

    def test_major_devils_advocate_concern_recommends_reducing_risk(self) -> None:
        proposal = _proposal()
        report = _challenge_report(severity="major")
        opinions = generate_department_opinions(proposal, report, [], default_market_intelligence_state())
        recommendation = compute_executive_recommendation(proposal, opinions)
        assert recommendation.action == "reduce_risk"

    def test_no_simulation_yet_recommends_focusing_on_simulation(self) -> None:
        proposal = _proposal(tier="good", score=75.0)
        opinions = generate_department_opinions(proposal, None, [], default_market_intelligence_state())
        recommendation = compute_executive_recommendation(proposal, opinions)
        assert recommendation.action == "focus_on_simulation"

    def test_weak_research_factor_recommends_more_research(self) -> None:
        factors = [ConfidenceFactor(name="research", score=20.0, weight=0.15, detail="d")]
        proposal = _proposal(tier="good", score=75.0, factors=factors)
        report = _challenge_report(severity="none_found")
        opinions = generate_department_opinions(proposal, report, [], default_market_intelligence_state())
        recommendation = compute_executive_recommendation(proposal, opinions)
        assert recommendation.action == "research_more"

    def test_confidence_pct_is_the_real_average_of_opinion_confidences(self) -> None:
        proposal = _proposal()
        opinions = generate_department_opinions(proposal, None, [], default_market_intelligence_state())
        recommendation = compute_executive_recommendation(proposal, opinions)
        expected = round(sum(o.confidence_pct for o in opinions) / len(opinions), 1)
        assert recommendation.confidence_pct == expected

    def test_supporting_and_opposing_reflect_real_opinion_stances(self) -> None:
        proposal = _proposal(tier="elite", score=96.0)
        report = _challenge_report(severity="none_found")
        opinions = generate_department_opinions(proposal, report, [_coach_report(company_score=90.0)], default_market_intelligence_state())
        recommendation = compute_executive_recommendation(proposal, opinions)
        for role in recommendation.supporting:
            assert next(o for o in opinions if o.role == role).stance == "agree"
        for role in recommendation.opposing:
            assert next(o for o in opinions if o.role == role).stance in ("disagree", "recommend_rejecting")


def _decision(*, decision_grade: str = "A", decision_grade_score: float = 90.0) -> TradeDecision:
    return TradeDecision(
        id="decision-proposal-1",
        symbol="NEXA",
        outcome="trade",
        researchSummary="x",
        technicalSummary="x",
        fundamentalSummary="x",
        riskSummary="x",
        confidence=90.0,
        finalReasoning="x",
        decisionGrade=decision_grade,  # type: ignore[arg-type]
        decisionGradeScore=decision_grade_score,
        createdAt=_now_iso(),
    )


class TestGenerateMeetingLogEntry:
    """v0.7 Feature 50 (Part 2/3) — the Executive Meeting Log makes Part
    1's ephemeral synthesis permanent, reusing the same real opinion/
    recommendation engine above plus the already-computed TradeDecision's
    own real Decision Grade (never recomputed a second time)."""

    def test_reuses_the_decisions_own_grade_rather_than_recomputing(self) -> None:
        proposal = _proposal()
        decision = _decision(decision_grade="A+", decision_grade_score=98.0)
        entry = generate_meeting_log_entry(proposal, decision, "buy", None, [], default_market_intelligence_state(), sim_day=5, resolved_by="ceo")
        assert entry.decision_grade == "A+"
        assert entry.decision_grade_score == 98.0

    def test_buy_choice_agreeing_with_trade_normally_is_network_agreed(self) -> None:
        proposal = _proposal(tier="elite", score=96.0)
        report = _challenge_report(severity="none_found")
        opinions = generate_department_opinions(proposal, report, [_coach_report(company_score=90.0)], default_market_intelligence_state())
        recommendation = compute_executive_recommendation(proposal, opinions)
        assert recommendation.action == "trade_normally"
        entry = generate_meeting_log_entry(proposal, _decision(), "buy", report, [_coach_report(company_score=90.0)], default_market_intelligence_state(), sim_day=1, resolved_by="ceo")
        assert entry.network_agreed is True

    def test_wait_choice_against_trade_normally_is_not_network_agreed(self) -> None:
        proposal = _proposal(tier="elite", score=96.0)
        report = _challenge_report(severity="none_found")
        coach_reports = [_coach_report(company_score=90.0)]
        opinions = generate_department_opinions(proposal, report, coach_reports, default_market_intelligence_state())
        recommendation = compute_executive_recommendation(proposal, opinions)
        assert recommendation.action == "trade_normally"
        entry = generate_meeting_log_entry(proposal, _decision(), "wait", report, coach_reports, default_market_intelligence_state(), sim_day=1, resolved_by="ceo")
        assert entry.network_agreed is False

    def test_carries_the_real_proposal_and_provenance_fields(self) -> None:
        proposal = _proposal()
        entry = generate_meeting_log_entry(proposal, _decision(), "buy", None, [], default_market_intelligence_state(), sim_day=7, resolved_by="auto")
        assert entry.proposal_id == proposal.id
        assert entry.symbol == proposal.symbol
        assert entry.sim_day == 7
        assert entry.resolved_by == "auto"
        assert len(entry.opinions) == 9

    def test_record_meeting_log_entry_caps_at_the_max(self) -> None:
        from app.executive_intelligence import MAX_MEETING_LOG_ENTRIES

        log: list[ExecutiveMeetingLogEntry] = []
        proposal = _proposal()
        for i in range(MAX_MEETING_LOG_ENTRIES + 5):
            entry = generate_meeting_log_entry(proposal.model_copy(update={"id": f"p{i}"}), _decision(), "buy", None, [], default_market_intelligence_state(), sim_day=i, resolved_by="ceo")
            log = record_meeting_log_entry(log, entry)
        assert len(log) == MAX_MEETING_LOG_ENTRIES
        # Oldest entries roll off first — the newest survives.
        assert log[-1].proposal_id == f"p{MAX_MEETING_LOG_ENTRIES + 4}"


class TestGenerateWeeklySelfEvaluations:
    """v0.7 Feature 50 (Part 2/3) — Weekly Self-Evaluation, built entirely
    from real DepartmentOpinion entries already logged to the Executive
    Meeting Log over the trailing week — never a fabricated self-read."""

    def test_no_meeting_log_entries_is_an_honest_neutral_default(self) -> None:
        evaluations = generate_weekly_self_evaluations([], sim_day=7)
        assert len(evaluations) == 9
        for e in evaluations:
            assert e.score == 50.0
            assert e.decisions_reviewed == 0
            assert "No real decisions" in e.summary

    def test_entries_outside_the_trailing_window_are_excluded(self) -> None:
        proposal = _proposal()
        old_entry = generate_meeting_log_entry(proposal, _decision(), "buy", None, [], default_market_intelligence_state(), sim_day=1, resolved_by="ceo")
        evaluations = generate_weekly_self_evaluations([old_entry], sim_day=20)
        for e in evaluations:
            assert e.decisions_reviewed == 0

    def test_entries_inside_the_trailing_window_are_averaged_per_department(self) -> None:
        proposal = _proposal(tier="elite", score=96.0)
        report = _challenge_report(severity="none_found")
        coach_reports = [_coach_report(company_score=90.0)]
        entry = generate_meeting_log_entry(proposal, _decision(), "buy", report, coach_reports, default_market_intelligence_state(), sim_day=10, resolved_by="ceo")
        evaluations = generate_weekly_self_evaluations([entry], sim_day=12)
        research_eval = next(e for e in evaluations if e.role == "research")
        assert research_eval.decisions_reviewed == 1
        expected_score = next(o for o in entry.opinions if o.role == "research").confidence_pct
        assert research_eval.score == round(expected_score, 1)

    def test_record_self_evaluations_caps_at_the_max(self) -> None:
        from app.executive_intelligence import MAX_SELF_EVAL_HISTORY

        history: list = []
        for day in range(1, 400, 7):
            history = record_self_evaluations(history, generate_weekly_self_evaluations([], sim_day=day))
        assert len(history) == MAX_SELF_EVAL_HISTORY
