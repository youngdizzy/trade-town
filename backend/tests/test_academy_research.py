"""Covers app/academy_research.py — v0.7 Feature 25's one company-wide
AI Academy knowledge project, mirroring app/research.py's own rotating-
queue mechanics (progress climbs each tick, completes, rotates) but
keyed to a fixed topic catalog instead of a ticker symbol.
"""
from __future__ import annotations

from app.academy_research import (
    ACADEMY_RESEARCHER_IDS,
    PROGRESS_COMPLETE,
    default_academy_projects,
    tick_academy_projects,
)


class TestDefaultAcademyProjects:
    def test_starts_with_exactly_one_in_progress_project(self) -> None:
        projects = default_academy_projects()
        assert len(projects) == 1
        assert projects[0].status == "in_progress"
        assert projects[0].assigned_agent == ACADEMY_RESEARCHER_IDS[0]

    def test_cio_is_never_the_assigned_agent(self) -> None:
        assert "cio" not in ACADEMY_RESEARCHER_IDS


class TestTickAcademyProjects:
    def test_progress_climbs_each_tick_without_completing_immediately(self) -> None:
        projects = default_academy_projects()
        start_progress = projects[0].progress
        updated, completed = tick_academy_projects(projects, completed_count=0)
        assert completed is None
        assert len(updated) == 1
        assert updated[0].progress > start_progress
        assert updated[0].status == "in_progress"

    def test_empty_project_list_starts_a_fresh_one_deterministically(self) -> None:
        updated, completed = tick_academy_projects([], completed_count=3)
        assert completed is None
        assert len(updated) == 1
        assert updated[0].assigned_agent == ACADEMY_RESEARCHER_IDS[3 % len(ACADEMY_RESEARCHER_IDS)]

    def test_reaching_full_progress_completes_and_rotates_to_a_new_project(self) -> None:
        projects = default_academy_projects()
        almost_done = projects[0].model_copy(update={"progress": PROGRESS_COMPLETE - 0.1})
        updated, completed = tick_academy_projects([almost_done], completed_count=0)
        assert completed is not None
        assert completed.status == "completed"
        assert completed.progress >= PROGRESS_COMPLETE
        assert len(updated) == 1
        assert updated[0].status == "in_progress"
        assert updated[0].id != completed.id

    def test_next_agent_after_a_completion_rotates_deterministically(self) -> None:
        projects = default_academy_projects()
        almost_done = projects[0].model_copy(update={"progress": PROGRESS_COMPLETE - 0.1})
        updated, completed = tick_academy_projects([almost_done], completed_count=0)
        assert completed is not None
        assert updated[0].assigned_agent == ACADEMY_RESEARCHER_IDS[1 % len(ACADEMY_RESEARCHER_IDS)]

    def test_completed_project_summary_names_the_real_agent_and_title(self) -> None:
        projects = default_academy_projects()
        almost_done = projects[0].model_copy(update={"progress": PROGRESS_COMPLETE - 0.1})
        _updated, completed = tick_academy_projects([almost_done], completed_count=0)
        assert completed is not None
        assert completed.title in completed.summary
