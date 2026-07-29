"""Covers app/talent.py — v0.7 Feature 44, the Talent Discovery System.
Every Discovery Event must trace to a real ThinkingProfile trait plus a
real, consistent CoachReport score history — this file checks the report
only fires when both real thresholds hold, and never re-fires the same
agent/trait pair twice.
"""
from __future__ import annotations

from app.schemas import AgentScore, CoachReport, ThinkingProfile, ThinkingTrait
from app.talent import (
    CONSISTENCY_MIN_SCORE,
    CONSISTENCY_REPORT_WINDOW,
    TALENT_SCORE_THRESHOLD,
    generate_talent_reports,
)


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _profile(agent_id: str, *, trait_id: str = "reasoning", score: float = 90.0) -> ThinkingProfile:
    return ThinkingProfile(
        agentId=agent_id,  # type: ignore[arg-type]
        traits=[
            ThinkingTrait(id=trait_id, name=trait_id.replace("_", " ").title(), score=score, detail="test detail"),  # type: ignore[arg-type]
            ThinkingTrait(id="curiosity", name="Curiosity", score=10.0, detail="test detail"),  # type: ignore[arg-type]
        ],
        updatedAt=_now_iso(),
    )


def _coach_report(agent_id: str, score: float, report_id: str = "r1") -> CoachReport:
    return CoachReport(
        id=report_id,
        period="weekly",  # type: ignore[arg-type]
        companyScore=score,
        agentRankings=[AgentScore(agentId=agent_id, score=score, researchAccuracy=score, confidenceCalibration=score)],  # type: ignore[arg-type]
        researchAccuracy=score,
        winRate=50.0,
        lossRate=50.0,
        averageConfidence=score,
        riskScore=score,
        commonMistakes=[],
        recommendations=[],
        createdAt=_now_iso(),
    )


def _consistent_reports(agent_id: str, score: float = 85.0, count: int = CONSISTENCY_REPORT_WINDOW) -> list[CoachReport]:
    return [_coach_report(agent_id, score, report_id=f"r{i}") for i in range(count)]


class TestGenerateTalentReports:
    def test_fires_when_both_the_trait_and_the_history_clear_threshold(self) -> None:
        profiles = {"echo": _profile("echo", trait_id="reasoning", score=TALENT_SCORE_THRESHOLD + 5)}
        reports = generate_talent_reports(("echo",), profiles, _consistent_reports("echo"), set(), sim_day=10)
        assert len(reports) == 1
        assert reports[0].agent_id == "echo"
        assert reports[0].trait_id == "reasoning"

    def test_does_not_fire_when_the_trait_score_is_below_threshold(self) -> None:
        profiles = {"echo": _profile("echo", trait_id="reasoning", score=TALENT_SCORE_THRESHOLD - 1)}
        reports = generate_talent_reports(("echo",), profiles, _consistent_reports("echo"), set(), sim_day=10)
        assert reports == []

    def test_does_not_fire_without_enough_coach_report_history(self) -> None:
        profiles = {"echo": _profile("echo", score=95.0)}
        short_history = _consistent_reports("echo", count=CONSISTENCY_REPORT_WINDOW - 1)
        reports = generate_talent_reports(("echo",), profiles, short_history, set(), sim_day=10)
        assert reports == []

    def test_does_not_fire_when_recent_scores_are_inconsistent(self) -> None:
        profiles = {"echo": _profile("echo", score=95.0)}
        history = [*_consistent_reports("echo", score=90.0, count=CONSISTENCY_REPORT_WINDOW - 1), _coach_report("echo", CONSISTENCY_MIN_SCORE - 1, report_id="bad")]
        reports = generate_talent_reports(("echo",), profiles, history, set(), sim_day=10)
        assert reports == []

    def test_does_not_refile_an_already_filed_agent_trait_pair(self) -> None:
        profiles = {"echo": _profile("echo", score=95.0)}
        existing = {"talent-echo-reasoning"}
        reports = generate_talent_reports(("echo",), profiles, _consistent_reports("echo"), existing, sim_day=10)
        assert reports == []

    def test_missing_profile_is_skipped_not_errored(self) -> None:
        reports = generate_talent_reports(("echo",), {}, _consistent_reports("echo"), set(), sim_day=10)
        assert reports == []

    def test_report_names_the_real_highest_trait_not_a_lower_one(self) -> None:
        profile = ThinkingProfile(
            agentId="echo",  # type: ignore[arg-type]
            traits=[
                ThinkingTrait(id="reasoning", name="Reasoning", score=95.0, detail="best"),  # type: ignore[arg-type]
                ThinkingTrait(id="curiosity", name="Curiosity", score=40.0, detail="worse"),  # type: ignore[arg-type]
            ],
            updatedAt=_now_iso(),
        )
        reports = generate_talent_reports(("echo",), {"echo": profile}, _consistent_reports("echo"), set(), sim_day=10)
        assert reports[0].trait_id == "reasoning"
        assert reports[0].evidence == ["best"]

    def test_no_literal_career_path_language_is_promised(self) -> None:
        profiles = {"echo": _profile("echo", score=95.0)}
        reports = generate_talent_reports(("echo",), profiles, _consistent_reports("echo"), set(), sim_day=10)
        assert "roster is fixed" in reports[0].suggested_focus
