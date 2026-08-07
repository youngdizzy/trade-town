"""Covers app/board.py — Design Bible Chapter 70 Part 1, Executive
Board & CEO Intelligence System. The Board Roster and Board Report both
compose already-real signals; these tests check that composition is
honest (no fabricated seats, no fabricated per-department numbers) and
that the three real cadences behave as documented.
"""
from __future__ import annotations

from app.board import (
    FILLED_BOARD_SEAT_AGENT_IDS,
    MAX_BOARD_REPORTS,
    VACANT_BOARD_SEAT_TITLES,
    compute_board_roster,
    generate_board_report,
    record_board_report,
)
from app.schemas import BoardReport, CompanyHealth, ResearchItem, TradeDecision


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _research(agent: str = "nova", status: str = "completed", confidence: float = 80.0) -> ResearchItem:
    return ResearchItem(
        id=f"r-{agent}",
        title="test",
        symbol="AAPL",
        category="stock",
        priority="normal",
        status=status,  # type: ignore[arg-type]
        assignedAgent=agent,  # type: ignore[arg-type]
        summary="test",
        confidence=confidence,
        createdAt=_now_iso(),
        updatedAt=_now_iso(),
    )


def _decision(supporting: list[str], opposing: list[str]) -> TradeDecision:
    return TradeDecision(
        id="d1",
        symbol="AAPL",
        outcome="trade",
        votes=[],
        researchSummary="test",
        technicalSummary="test",
        fundamentalSummary="test",
        riskSummary="test",
        supportingAgents=supporting,  # type: ignore[arg-type]
        opposingAgents=opposing,  # type: ignore[arg-type]
        confidence=80.0,
        finalReasoning="test",
        orderId="order-1",
        createdAt=_now_iso(),
    )


def _company_health(tier: str = "stable", recommendations: list[str] | None = None, department_consensus: float = 72.0) -> CompanyHealth:
    return CompanyHealth(
        overall=60.0,
        tier=tier,  # type: ignore[arg-type]
        operationalStability=60.0,
        departmentEfficiency=60.0,
        employeeMorale=60.0,
        researchProgress=60.0,
        capitalHealth=60.0,
        resourceUsage=60.0,
        reputation=60.0,
        technologyLevel=60.0,
        officeExpansion=60.0,
        educationProgress=60.0,
        recommendations=recommendations or [],
        departmentConsensus=department_consensus,
        updatedAt=_now_iso(),
    )


class TestComputeBoardRoster:
    def test_eleven_seats_total(self) -> None:
        roster = compute_board_roster(now_iso=_now_iso())
        assert len(roster.seats) == 11
        assert len(FILLED_BOARD_SEAT_AGENT_IDS) == 4
        assert len(VACANT_BOARD_SEAT_TITLES) == 7

    def test_filled_seats_use_real_agent_occupations(self) -> None:
        roster = compute_board_roster(now_iso=_now_iso())
        filled = [s for s in roster.seats if s.agent_id is not None]
        assert len(filled) == 4
        cio_seat = next(s for s in filled if s.agent_id == "cio")
        assert cio_seat.title == "Chief Investment Officer"
        assert cio_seat.agent_name == "Meridian"

    def test_vacant_seats_have_no_agent(self) -> None:
        roster = compute_board_roster(now_iso=_now_iso())
        vacant = [s for s in roster.seats if s.agent_id is None]
        assert len(vacant) == 7
        assert all(s.agent_name is None for s in vacant)
        assert {s.title for s in vacant} == set(VACANT_BOARD_SEAT_TITLES)

    def test_never_invents_a_twelfth_seat(self) -> None:
        # The brief's own source names only 11 of its 12 seats anywhere
        # in the document — the 12th is deliberately not fabricated.
        roster = compute_board_roster(now_iso=_now_iso())
        assert len(roster.seats) == 11


class TestGenerateBoardReport:
    def _report(self, **overrides: object) -> BoardReport:
        base = dict(
            cadence="daily",
            trigger=None,
            trigger_detail=None,
            research=[_research()],
            decisions=[_decision(["nova"], [])],
            agent_ids=("nova", "sentinel"),
            company_health=_company_health(),
            black_swan_tier="green",
            circuit_breaker_tier="none",
            pending_ceo_decisions=3,
            sim_day=10,
            report_id="board-test-1",
            now_iso=_now_iso(),
        )
        base.update(overrides)
        return generate_board_report(**base)  # type: ignore[arg-type]

    def test_daily_report_has_no_trigger(self) -> None:
        report = self._report(cadence="daily")
        assert report.cadence == "daily"
        assert report.trigger is None
        assert "Triggered by" not in report.summary

    def test_quarterly_report_has_no_trigger(self) -> None:
        report = self._report(cadence="quarterly")
        assert report.cadence == "quarterly"
        assert report.trigger is None

    def test_emergency_report_carries_trigger_and_detail(self) -> None:
        report = self._report(cadence="emergency", trigger="black_swan_tier", trigger_detail="Black Swan Risk crossing into RED")
        assert report.cadence == "emergency"
        assert report.trigger == "black_swan_tier"
        assert "Triggered by Black Swan Risk crossing into RED" in report.summary

    def test_department_activity_reuses_the_real_shared_computation(self) -> None:
        report = self._report(decisions=[_decision(["nova"], [])], research=[_research(agent="nova")])
        assert any(a.agent_id == "nova" for a in report.department_activity)

    def test_recommendations_reuse_company_health_verbatim(self) -> None:
        report = self._report(company_health=_company_health(recommendations=["Diversify more."]))
        assert report.recommendations == ["Diversify more."]

    def test_confidence_level_reuses_department_consensus_verbatim(self) -> None:
        report = self._report(company_health=_company_health(department_consensus=88.0))
        assert report.confidence_level == 88.0

    def test_required_ceo_decisions_matches_pending_count(self) -> None:
        report = self._report(pending_ceo_decisions=7)
        assert report.required_ceo_decisions == 7

    def test_problems_empty_when_everything_is_healthy(self) -> None:
        report = self._report(company_health=_company_health(tier="stable"), black_swan_tier="green", circuit_breaker_tier="none")
        assert report.problems == []

    def test_problems_flag_poor_company_health(self) -> None:
        report = self._report(company_health=_company_health(tier="critical"))
        assert any("Company Health" in p for p in report.problems)

    def test_problems_flag_elevated_black_swan_risk(self) -> None:
        report = self._report(black_swan_tier="critical")
        assert any("Black Swan" in p for p in report.problems)

    def test_problems_flag_high_circuit_breaker_tier(self) -> None:
        report = self._report(circuit_breaker_tier="tier4")
        assert any("Circuit Breaker" in p for p in report.problems)

    def test_risk_assessment_names_both_real_tiers(self) -> None:
        report = self._report(black_swan_tier="orange", circuit_breaker_tier="tier2")
        assert "ORANGE" in report.risk_assessment
        assert "TIER2" in report.risk_assessment


class TestRecordBoardReport:
    def test_appends(self) -> None:
        reports = record_board_report([], generate_board_report(
            cadence="daily", trigger=None, trigger_detail=None, research=[], decisions=[], agent_ids=(), company_health=_company_health(),
            black_swan_tier="green", circuit_breaker_tier="none", pending_ceo_decisions=0, sim_day=1, report_id="r1", now_iso=_now_iso(),
        ))
        assert len(reports) == 1

    def test_caps_at_max(self) -> None:
        reports: list[BoardReport] = []
        for i in range(MAX_BOARD_REPORTS + 10):
            reports = record_board_report(reports, generate_board_report(
                cadence="daily", trigger=None, trigger_detail=None, research=[], decisions=[], agent_ids=(), company_health=_company_health(),
                black_swan_tier="green", circuit_breaker_tier="none", pending_ceo_decisions=0, sim_day=i, report_id=f"r{i}", now_iso=_now_iso(),
            ))
        assert len(reports) == MAX_BOARD_REPORTS
        # Trims from the front — the most recent reports survive.
        assert reports[-1].id == f"r{MAX_BOARD_REPORTS + 9}"
