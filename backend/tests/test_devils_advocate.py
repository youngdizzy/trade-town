"""Covers app/devils_advocate.py — v0.7 Feature 41, the Intelligent
Devil's Advocate System. Every ChallengeReport field must trace back to a
real signal already computed elsewhere (AnalystVote reasoning,
DecisionConfidence factors, risk_summary, What-If Simulation Lab, past
CaseStudy history) — never invented evidence.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.devils_advocate import ELIGIBLE_DEVILS_ADVOCATES, generate_challenge_report
from app.market_data import MockMarketDataProvider
from app.schemas import AnalystVote, CaseStudy, CaseStudyTimelineEntry, ConfidenceFactor, DecisionConfidence, TradeProposal

_ROLE_TO_AGENT = {"technical": "echo", "news": "scout", "macro": "nova", "risk": "sentinel", "sentiment": "pulse", "execution": "atlas"}


def _vote(role: str, choice: str, evidence: list[str] | None = None) -> AnalystVote:
    return AnalystVote(
        role=role,  # type: ignore[arg-type]
        agentId=_ROLE_TO_AGENT[role],  # type: ignore[arg-type]
        choice=choice,  # type: ignore[arg-type]
        reasoning=f"{role} reasoning",
        evidence=evidence if evidence is not None else ["real evidence line"],
    )


def _six_votes(choice: str = "buy", missing_evidence_role: str | None = None) -> list[AnalystVote]:
    return [_vote(role, choice, evidence=[] if role == missing_evidence_role else None) for role in _ROLE_TO_AGENT]


def _factor(name: str, score: float) -> ConfidenceFactor:
    return ConfidenceFactor(name=name, score=score, weight=0.2, detail=f"{name} detail")


def _proposal(
    votes: list[AnalystVote],
    *,
    overall: str = "buy",
    symbol: str = "NEXA",
    risk_summary: str = "NEXA is within all configured risk limits.",
    factors: list[ConfidenceFactor] | None = None,
) -> TradeProposal:
    return TradeProposal(
        id="proposal-1",
        symbol=symbol,
        category="stock",
        quantity=10.0,
        price=100.0,
        confidence=90.0,
        analystVotes=votes,
        overallRecommendation=overall,  # type: ignore[arg-type]
        researchSummary="test research summary",
        riskSummary=risk_summary,
        confidenceEngine=DecisionConfidence(score=80.0, tier="strong", summary="Strong Setup (80/100).", factors=factors or [_factor("agreement", 90.0)]),
        createdAt=datetime.now(timezone.utc).isoformat(),
        createdSimMinutes=0,
    )


def _case_study(symbol: str, title: str) -> CaseStudy:
    return CaseStudy(
        id=f"case-{title}",
        category="overconfidence",
        title=title,
        symbol=symbol,
        decisionId="decision-1",
        timeline=[CaseStudyTimelineEntry(label="filed", timestamp=datetime.now(timezone.utc).isoformat())],
        background="test background",
        decisionProcess="test decision process",
        departmentOpinions=["test opinion"],
        missedInformation="test missed information",
        lessonsLearned="test lessons learned",
        recommendedImprovements="test recommended improvements",
        relatedPrinciples=["test principle"],
        tradePnlPct=-5.0,
        simDay=1,
        createdAt=datetime.now(timezone.utc).isoformat(),
    )


class TestGenerateChallengeReport:
    def test_assigns_an_eligible_non_desk_agent(self) -> None:
        proposal = _proposal(_six_votes())
        report = generate_challenge_report(proposal, provider=MockMarketDataProvider(), case_studies=[], existing_count=0)
        assert report.assigned_agent in ELIGIBLE_DEVILS_ADVOCATES
        assert report.assigned_agent not in _ROLE_TO_AGENT.values()

    def test_assignment_rotates_deterministically_with_existing_count(self) -> None:
        proposal = _proposal(_six_votes())
        assigned = [
            generate_challenge_report(proposal, provider=MockMarketDataProvider(), case_studies=[], existing_count=i).assigned_agent
            for i in range(len(ELIGIBLE_DEVILS_ADVOCATES) * 2)
        ]
        assert assigned == list(ELIGIBLE_DEVILS_ADVOCATES) * 2

    def test_unanimous_agreement_full_evidence_no_risk_strong_factors_yields_none_found(self) -> None:
        votes = _six_votes("buy")
        proposal = _proposal(votes, overall="buy", risk_summary="NEXA is within all configured risk limits.", factors=[_factor("agreement", 90.0)])
        report = generate_challenge_report(proposal, provider=MockMarketDataProvider(), case_studies=[], existing_count=0)
        assert report.severity == "none_found"
        assert report.hidden_risks == []
        assert report.weak_assumptions == []
        assert report.missing_evidence == []
        assert "no major weaknesses" in report.final_recommendation

    def test_one_dissenting_vote_alone_yields_minor_severity(self) -> None:
        votes = _six_votes("buy")
        votes[0] = _vote("technical", "sell")
        proposal = _proposal(votes, overall="buy", risk_summary="NEXA is within all configured risk limits.", factors=[_factor("agreement", 90.0)])
        report = generate_challenge_report(proposal, provider=MockMarketDataProvider(), case_studies=[], existing_count=0)
        assert report.severity == "minor"
        assert votes[0].reasoning in report.bear_case  # the real dissenting vote's own reasoning, never invented text

    def test_dissent_plus_hidden_risk_yields_major_severity(self) -> None:
        votes = _six_votes("buy")
        votes[0] = _vote("technical", "sell")
        proposal = _proposal(votes, overall="buy", risk_summary="Sentinel flags NEXA over the configured exposure limit.", factors=[_factor("agreement", 90.0)])
        report = generate_challenge_report(proposal, provider=MockMarketDataProvider(), case_studies=[], existing_count=0)
        assert report.severity == "major"
        assert report.hidden_risks == [proposal.risk_summary]

    def test_missing_evidence_is_flagged_per_vote(self) -> None:
        votes = _six_votes("buy", missing_evidence_role="news")
        proposal = _proposal(votes)
        report = generate_challenge_report(proposal, provider=MockMarketDataProvider(), case_studies=[], existing_count=0)
        assert len(report.missing_evidence) == 1
        assert "news" in report.missing_evidence[0]

    def test_weak_confidence_factor_is_flagged(self) -> None:
        votes = _six_votes("buy")
        proposal = _proposal(votes, factors=[_factor("agreement", 90.0), _factor("research_confidence", 30.0)])
        report = generate_challenge_report(proposal, provider=MockMarketDataProvider(), case_studies=[], existing_count=0)
        assert len(report.weak_assumptions) == 1
        assert "research_confidence" in report.weak_assumptions[0]

    def test_historical_comparisons_only_include_same_symbol_case_studies(self) -> None:
        votes = _six_votes("buy")
        proposal = _proposal(votes, symbol="NEXA")
        case_studies = [_case_study("NEXA", "NEXA mistake"), _case_study("OTHR", "OTHR mistake")]
        report = generate_challenge_report(proposal, provider=MockMarketDataProvider(), case_studies=case_studies, existing_count=0)
        assert report.historical_comparisons == ["NEXA mistake"]

    def test_no_case_studies_for_symbol_yields_empty_historical_comparisons(self) -> None:
        votes = _six_votes("buy")
        proposal = _proposal(votes, symbol="NEXA")
        report = generate_challenge_report(proposal, provider=MockMarketDataProvider(), case_studies=[_case_study("OTHR", "OTHR mistake")], existing_count=0)
        assert report.historical_comparisons == []

    def test_worst_case_scenario_is_a_real_non_empty_line(self) -> None:
        votes = _six_votes("buy")
        proposal = _proposal(votes)
        report = generate_challenge_report(proposal, provider=MockMarketDataProvider(), case_studies=[], existing_count=0)
        assert report.worst_case_scenario
        assert "%" in report.worst_case_scenario

    def test_report_id_and_proposal_id_are_stable_and_linked(self) -> None:
        votes = _six_votes("buy")
        proposal = _proposal(votes)
        report = generate_challenge_report(proposal, provider=MockMarketDataProvider(), case_studies=[], existing_count=3)
        assert report.proposal_id == proposal.id
        assert report.symbol == proposal.symbol
        assert proposal.id in report.id
