"""BlackBoxManager — the Advanced Quantitative Research Division.

The Quant (agentId "quant", Chief Quantitative Strategist) leads a single
company-wide Black Box Research Project at a time — the same "exactly one
active project" convention app/academy_research.py already established
for the Academy's own knowledge track, now applied to a much longer-running
one: progress advances once per in-game day (not per tick), so a project
genuinely takes weeks of in-game time to reach review, honoring the brief's
"unlike ordinary research they may require weeks or months."

What this module deliberately reuses rather than duplicates (see the
overlap research this feature was scoped from):

  Backtesting Engine      - already real (app/simulation.py's
                             SimulationManager). Not rebuilt here; the
                             Quant's "Quant Lab" is real content layered
                             onto the existing Simulation Lab room, the
                             same "Command-Center-tab-not-new-scene"
                             precedent app/mentor.py and app/founders.py
                             already established for Sage/Keystone/Compass
                             — no new physical scene was built.
  Devil's Advocate         - a project's `devils_advocate` field reuses
                             the exact ChallengeReport schema
                             app/devils_advocate.py already built for
                             trade proposals (see generate_project_challenge
                             below); the resulting report is appended into
                             the same `challenge_reports` history, so it
                             flows through app/innovation.py's existing
                             Innovation Points pipeline automatically —
                             never a second, parallel points ladder.
  Founder Council Review   - app/founders.py's generate_breakthrough_review()
                             is a new mode of the same council-session
                             generator Feature 39 already built.
  Museum of Discoveries    - an approved breakthrough files a real
                             HallOfFameEntry (category="breakthrough",
                             with the discovery_timeline/supporting_evidence/
                             company_impact fields Feature 41 added) —
                             the Hall of Fame's own "permanent, never-
                             evicted record" mechanism, not a second one.
  Failed Research          - a rejected project moves into `archive` with
                             status="failed" — the archive itself *is* the
                             brief's Research Archives; no separate schema.
  World Reputation         - company_health.py's real `reputation`
                             sub-score already grows with Hall of Fame
                             entry count; a breakthrough adds one real
                             NewsItem naming that real number (see
                             nexus.py's tick()), never a fabricated
                             external-institution simulation.

What's genuinely new: the Quant agent itself, the BlackBoxProject
lifecycle/dashboard, the team-formation logic below, Team Chemistry (a
real derived reading of the team's own current mood — no fabricated
pairwise relationship system), and the Eureka! cinematic moment (frontend).

Team formation is real and deterministic, never a fabricated multi-factor
"Skill/Experience/Workload" score: four seats are matched to whichever
existing agent already has that real occupation (Echo/Technical, Nova/
Fundamental, Sentinel-or-Guardian/Risk alternating by project count,
Coach/Psychology). There is no "AI Research Scientist" seat — no agent in
this roster has that occupation, and this feature already adds one new
agent; inventing a second is out of scope. The Devil's Advocate seat
reuses app/devils_advocate.py's own eligible pool, picking whichever
candidate (not already on this project's fixed team) has the highest real
Innovation Points among that pool — a genuine additional real signal, not
a new fabricated one — falling back to plain rotation before any agent has
earned points yet.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from app.agents import AGENT_PROFILES
from app.devils_advocate import ELIGIBLE_DEVILS_ADVOCATES
from app.schemas import (
    AgentId,
    BlackBoxCategory,
    BlackBoxPriority,
    BlackBoxProject,
    BlackBoxState,
    BlackBoxTeamMember,
    BreakthroughReview,
    ChallengeReport,
    ChallengeSeverity,
    InnovationState,
)

MAX_ARCHIVE = 30
MAX_REVIEWS = 30
MAX_VIEWED_BREAKTHROUGH_IDS = 30
MAX_JOURNAL_ENTRIES = 40
MAX_OBSTACLES = 5

STARTING_BUDGET = 1000.0
OBSTACLE_CHANCE_PER_DAY = 0.15
WEAK_CONFIDENCE_THRESHOLD = 55.0

_PRIORITY_GAIN_MULTIPLIER: dict[BlackBoxPriority, float] = {"low": 0.7, "normal": 1.0, "high": 1.5}
_PRIORITY_BURN_MULTIPLIER: dict[BlackBoxPriority, float] = {"low": 0.6, "normal": 1.0, "high": 1.8}

FUNDED_PROGRESS_RANGE = (2.0, 5.5)
STARVED_PROGRESS_RANGE = (0.2, 0.8)
DAILY_BURN_RANGE = (15.0, 35.0)
DURATION_DAYS_RANGE = (21, 35)  # "weeks" of in-game time, per the brief

_CATEGORY_CATALOG: tuple[tuple[BlackBoxCategory, str, str], ...] = (
    ("new_trading_framework", "A New Trading Framework", "Explore an entirely new framework for evaluating trade setups, beyond what the desk currently uses."),
    ("portfolio_allocation", "Better Portfolio Allocation", "Investigate whether the company's current position-sizing approach can be meaningfully improved."),
    ("statistical_edge", "A New Statistical Edge", "Search the company's own historical data for a real, repeatable statistical edge not yet in use."),
    ("ai_communication", "AI Communication Improvements", "Study how the desk's agents share findings with each other, looking for real communication gaps."),
    ("risk_model", "A Better Risk Model", "Stress-test the current risk model against edge cases it wasn't originally built for."),
    ("decision_framework", "A New Decision Framework", "Formalize a clearer framework for how trade decisions get made under uncertainty."),
    ("journaling_improvement", "Journaling Improvements", "Look for gaps in what the Decision Journal currently captures about a trade's process."),
    ("automation_improvement", "Automation Improvements", "Identify one real manual step in the company's workflow that could be safely automated."),
    ("market_regime_detection", "Market Regime Detection", "Build and test a real method for detecting when the market's overall regime has shifted."),
    ("portfolio_optimization", "Portfolio Optimization", "Re-examine the portfolio's current diversification for real, measurable improvement."),
    ("academy_improvement", "Academy Improvements", "Study whether the Academy's current curriculum actually improves real trading outcomes."),
)

_OBSTACLE_POOL: tuple[str, ...] = (
    "Backtest data for this period is noisier than expected.",
    "Two team members disagree on the underlying assumption.",
    "An early signal didn't replicate in a second sample.",
    "The effect only shows up in a narrow slice of the data so far.",
    "Progress has been slower than the Quant's own initial estimate.",
    "A related result from a past project doesn't quite line up with this one.",
)

_RISK_SEATS: tuple[AgentId, ...] = ("sentinel", "guardian")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_team(archive_count: int) -> list[BlackBoxTeamMember]:
    risk_seat = _RISK_SEATS[archive_count % len(_RISK_SEATS)]
    return [
        BlackBoxTeamMember(agentId="quant", role="Project Leader"),
        BlackBoxTeamMember(agentId="echo", role="Technical Analyst"),
        BlackBoxTeamMember(agentId="nova", role="Fundamental Analyst"),
        BlackBoxTeamMember(agentId=risk_seat, role="Risk Specialist"),
        BlackBoxTeamMember(agentId="coach", role="Psychology Coach"),
    ]


def _select_devils_advocate(
    team: list[BlackBoxTeamMember],
    *,
    archive_count: int,
    innovation_state: dict[AgentId, InnovationState],
) -> AgentId:
    team_ids = {m.agent_id for m in team}
    candidates = [a for a in ELIGIBLE_DEVILS_ADVOCATES if a not in team_ids]
    if not candidates:
        candidates = list(ELIGIBLE_DEVILS_ADVOCATES)
    ranked = sorted(candidates, key=lambda a: innovation_state[a].points if a in innovation_state else -1.0, reverse=True)
    best_points = innovation_state[ranked[0]].points if ranked[0] in innovation_state else -1.0
    if best_points <= 0.0:
        return candidates[archive_count % len(candidates)]
    return ranked[0]


def _new_project(*, sim_day: int, archive_count: int, innovation_state: dict[AgentId, InnovationState]) -> BlackBoxProject:
    category, title, objective = _CATEGORY_CATALOG[archive_count % len(_CATEGORY_CATALOG)]
    team = _build_team(archive_count)
    devils_advocate = _select_devils_advocate(team, archive_count=archive_count, innovation_state=innovation_state)
    now = _now_iso()
    duration = random.randint(*DURATION_DAYS_RANGE)
    return BlackBoxProject(
        id=f"blackbox-{category}-{now}",
        category=category,
        title=title,
        objective=objective,
        status="active",
        priority="normal",
        team=team,
        devilsAdvocate=devils_advocate,
        progress=round(random.uniform(1.0, 4.0), 1),
        confidenceLevel=50.0,
        budget=STARTING_BUDGET,
        obstacles=[],
        researchNotes=[],
        quantJournal=[f"Day {sim_day}: {AGENT_PROFILES['quant'].name} opened a new Black Box investigation — {objective}"],
        startedSimDay=sim_day,
        estimatedCompletionSimDay=sim_day + duration,
        createdAt=now,
        updatedAt=now,
    )


def default_black_box_state() -> BlackBoxState:
    return BlackBoxState(active=None, archive=[], reviews=[], viewedBreakthroughIds=[], updatedAt=_now_iso())


def _confidence_for(progress: float, obstacles: list[str]) -> float:
    return round(max(0.0, min(100.0, 40.0 + progress * 0.5 - len(obstacles) * 7.0)), 1)


def tick_black_box_daily(
    state: BlackBoxState,
    *,
    sim_day: int,
    innovation_state: dict[AgentId, InnovationState],
) -> BlackBoxState:
    """Advances the one active project by one real in-game day. Returns
    the updated state; the caller (nexus.py) checks whether `active.status`
    just became "under_review" to trigger the Devil's Advocate + Founder
    Council review in the same tick."""
    active = state.active
    if active is None:
        new_active = _new_project(sim_day=sim_day, archive_count=len(state.archive), innovation_state=innovation_state)
        return state.model_copy(update={"active": new_active, "updatedAt": _now_iso()})

    if active.status == "paused":
        return state

    priority_gain_mult = _PRIORITY_GAIN_MULTIPLIER[active.priority]
    priority_burn_mult = _PRIORITY_BURN_MULTIPLIER[active.priority]

    obstacles = list(active.obstacles)
    funded = active.budget > 0.0
    gain = random.uniform(*FUNDED_PROGRESS_RANGE) * priority_gain_mult if funded else random.uniform(*STARVED_PROGRESS_RANGE)
    progress = round(min(100.0, active.progress + gain), 1)

    burn = random.uniform(*DAILY_BURN_RANGE) * priority_burn_mult if funded else 0.0
    budget = round(max(0.0, active.budget - burn), 2)

    obstacle_line: str | None = None
    if not funded and "Insufficient funding is slowing this project down." not in obstacles:
        obstacle_line = "Insufficient funding is slowing this project down."
    elif random.random() < OBSTACLE_CHANCE_PER_DAY:
        candidates = [o for o in _OBSTACLE_POOL if o not in obstacles]
        if candidates:
            obstacle_line = random.choice(candidates)
    if obstacle_line is not None:
        obstacles = [*obstacles, obstacle_line]
        if len(obstacles) > MAX_OBSTACLES:
            del obstacles[: len(obstacles) - MAX_OBSTACLES]

    confidence = _confidence_for(progress, obstacles)

    journal_line = f"Day {sim_day}: progress reached {progress:.1f}%. {obstacle_line or 'No major issues today.'}"
    journal = [*active.quant_journal, journal_line]
    if len(journal) > MAX_JOURNAL_ENTRIES:
        del journal[: len(journal) - MAX_JOURNAL_ENTRIES]

    new_status = "under_review" if progress >= 100.0 else active.status
    updated = active.model_copy(
        update={
            "progress": progress,
            "budget": budget,
            "obstacles": obstacles,
            "confidence_level": confidence,
            "quant_journal": journal,
            "status": new_status,
            "updated_at": _now_iso(),
        }
    )
    return state.model_copy(update={"active": updated, "updatedAt": _now_iso()})


def generate_project_challenge(project: BlackBoxProject, *, existing_count: int) -> ChallengeReport:
    """The project's Devil's Advocate review — same ChallengeReport schema
    app/devils_advocate.py built for trade proposals, built here entirely
    from the project's own real fields (obstacles, confidence, notes).
    Feeds into the same challenge_reports history, so it earns Innovation
    Points through the existing pipeline (see module docstring)."""
    hidden_risks = list(project.obstacles)
    weak_assumptions = [f"Confidence level only reached {project.confidence_level:.0f}/100."] if project.confidence_level < WEAK_CONFIDENCE_THRESHOLD else []
    missing_evidence = ["No research notes were logged for this project."] if not project.research_notes else []

    days_spent = project.estimated_completion_sim_day - project.started_sim_day
    worst_case_scenario = f"If this doesn't hold up, {days_spent} in-game days and ${project.budget:.0f} in remaining budget bought no lasting system change."

    concern_signals = sum(1 for bucket in (hidden_risks, weak_assumptions, missing_evidence) if bucket)
    if concern_signals == 0:
        severity: ChallengeSeverity = "none_found"
        final_recommendation = "I attempted to disprove this project's findings but found no major weaknesses. The research holds up under scrutiny."
    elif concern_signals == 1:
        severity = "minor"
        final_recommendation = "Minor weaknesses only — address the item(s) above before the Founder Council signs off."
    else:
        severity = "major"
        final_recommendation = "Real weaknesses found. This project should not become an official breakthrough without further work."

    return ChallengeReport(
        id=f"challenge-blackbox-{project.id}-{existing_count}",
        proposalId=project.id,
        symbol=project.category,
        assignedAgent=project.devils_advocate,
        tradeSummary=f'{project.title}: {project.objective} ({project.progress:.0f}% complete, {project.confidence_level:.0f}/100 confidence)',
        bullCase=project.quant_journal[-1] if project.quant_journal else project.objective,
        bearCase="; ".join(hidden_risks) if hidden_risks else "No obstacles were logged during this project.",
        hiddenRisks=hidden_risks,
        weakAssumptions=weak_assumptions,
        missingEvidence=missing_evidence,
        historicalComparisons=[],
        worstCaseScenario=worst_case_scenario,
        suggestedImprovements=[],
        severity=severity,
        finalRecommendation=final_recommendation,
        createdAt=_now_iso(),
    )


def mark_breakthrough_viewed(viewed_ids: list[str], review_id: str) -> list[str]:
    if review_id in viewed_ids:
        return viewed_ids
    updated = [*viewed_ids, review_id]
    if len(updated) > MAX_VIEWED_BREAKTHROUGH_IDS:
        del updated[: len(updated) - MAX_VIEWED_BREAKTHROUGH_IDS]
    return updated


def archive_project(state: BlackBoxState, project: BlackBoxProject) -> BlackBoxState:
    archive = [*state.archive, project]
    if len(archive) > MAX_ARCHIVE:
        del archive[: len(archive) - MAX_ARCHIVE]
    return state.model_copy(update={"active": None, "archive": archive, "updatedAt": _now_iso()})


def record_review(state: BlackBoxState, review: BreakthroughReview) -> BlackBoxState:
    reviews = [*state.reviews, review]
    if len(reviews) > MAX_REVIEWS:
        del reviews[: len(reviews) - MAX_REVIEWS]
    return state.model_copy(update={"reviews": reviews, "updatedAt": _now_iso()})
