"""The Foundational Mentor Program (v0.7 Feature 49, Phase 3) — an
expandable, CEO-facing library of named "tracks", each modeled on a
real, respected trading educator's real, publicly-known area of
expertise, worked through as a sequential lesson-and-quiz curriculum.

CONTENT ATTRIBUTION BOUNDARY (read this before adding or editing a
lesson): this codebase has no HTTP client, no PDF/video parser, and no
LLM call anywhere (confirmed by grep across the whole backend, and
consistent with the precedent already established in app/education.py
and Feature 40's own module docstring) — so TradeTown has no mechanism
to actually watch, read, or otherwise ingest any real person's real
video, book, or article content. A real educator's name is used ONLY as
a CEO-assigned track label naming the real subject area their track
covers. Every lesson's actual teaching content below is 100%
original TradeTown-authored material on that same subject, written the
same way every other lesson in app/education.py already is — never a
transcription, summary, paraphrase, or quote of that person's actual
published work, and never a claim that TradeTown has processed their
content in any way. `_CONTENT_DISCLAIMER` states this explicitly on
every mentor profile so it's never implied otherwise in-product. This
was an explicit CEO (user) decision, not an assumption: given the
choice between (a) refusing to use real names at all, or (b) using real
names as track labels over original content with an explicit
disclaimer, the CEO chose (b).

WHAT'S REAL VS. ROADMAP: only the "tjr" track ships real lesson
content (6 original lessons on real, checkable TradeTown mechanics —
see `_TJR_LESSONS` below). The other five named tracks in the brief
(Al Brooks, Linda Raschke, Mark Douglas, Tom Hougaard, Mike Bellafiore)
are seeded as real, ordered, named roadmap entries — real display name,
real track label, real focus-area topics drawn straight from the
brief — but deliberately ship with zero lessons and `status: "planned"`
rather than five fabricated placeholder shells. `_LESSON_SPECS_BY_MENTOR`
is exactly where a future track's real `_LessonSpec` tuple gets added
once someone actually authors it; nothing else needs to change for it
to come online. Graduating a track flips the next roadmap entry from
"planned" to "active" (a real mechanical unlock), but that next track
still has no real lessons until its own content is authored — the
unlock is honest about what it does and doesn't provide.

GRADUATION SIGNAL: gated purely on the real, checkable "has this agent
viewed and correctly progressed through every lesson in this track"
signal (`completed_lesson_ids` covering every lesson id). Deliberately
NOT tied to a Research Sandbox backtest threshold — app/sandbox.py's own
module docstring already establishes there's no mechanism to attribute
a real executed trade to a specific Strategy; a "mentor track concept"
is one level further removed than that, so reusing Sandbox stats here
would be a second, worse version of the same non-attribution problem.

EXPLICIT SCOPE CUTS (checked against the brief, not built): no
CEO custom-mentor-authoring UI — the data model above is expandable
(add an id, roadmap entry, and `_LessonSpec` tuple) but there's no
in-product form to author one live; a repo-side content contribution is
the real workflow for now. No "concepts adopted/rejected" or
"statistical success" mentor rating — there's no real signal in this
codebase that could honestly measure whether an agent "adopted" a
mentor's concept in a later trade. External resources
(`FoundationalMentorResource`) are bookmark-only: a CEO-provided title/
URL/type TradeTown stores and displays, never fetches, parses, or
grades — the same "bookmark, never ingest" boundary this docstring
opens with.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.schemas import (
    FoundationalMentorId,
    FoundationalMentorLesson,
    FoundationalMentorProfile,
    FoundationalMentorProgress,
    FoundationalMentorResource,
    FoundationalMentorState,
    FoundationalResourceType,
)

MAX_RESOURCES_PER_MENTOR = 20

_CONTENT_DISCLAIMER = (
    "This track's name credits a real, respected trading educator whose stated area of expertise inspired it. "
    "TradeTown has no ability to watch, read, or otherwise ingest real external video, book, or article content "
    "(no HTTP client or content-parsing exists anywhere in this codebase) — every lesson below is original "
    "TradeTown-authored teaching material on that same subject area, never a transcription, summary, or quote of "
    "that person's actual work."
)

_ROADMAP_ORDER: tuple[FoundationalMentorId, ...] = (
    "tjr",
    "al_brooks",
    "linda_raschke",
    "mark_douglas",
    "tom_hougaard",
    "mike_bellafiore",
)

_ROADMAP_FOCUS: dict[FoundationalMentorId, tuple[str, list[str]]] = {
    "tjr": ("TJR", ["Trading Psychology", "Discipline", "Daily Routines", "Patience", "Trade Planning", "Journaling"]),
    "al_brooks": (
        "Al Brooks",
        ["Advanced Price Action", "Reading Candles", "Market Structure", "Trend Development", "Breakouts", "Trading Ranges", "Probability-Based Thinking"],
    ),
    "linda_raschke": (
        "Linda Raschke",
        ["Professional Trading Process", "Swing and Intraday Concepts", "Risk Management", "Market Preparation", "Trade Management", "Professional Discipline"],
    ),
    "mark_douglas": ("Mark Douglas", ["Trading Psychology", "Consistency", "Probabilistic Thinking", "Emotional Control", "Confidence", "Decision Making"]),
    "tom_hougaard": ("Tom Hougaard", ["Professional Execution", "Mental Toughness", "Managing Pressure", "Confidence Under Stress", "Performance Improvement"]),
    "mike_bellafiore": (
        "Mike Bellafiore",
        ["Professional Trading Team Development", "Journaling", "Performance Reviews", "Deliberate Practice", "Continuous Improvement", "Building Elite Traders"],
    ),
}


@dataclass(frozen=True)
class _LessonSpec:
    id: str
    order: int
    title: str
    simple_explanation: str
    deeper_explanation: str
    quiz_question: str
    quiz_options: tuple[str, str, str, str]
    correct_index: int


_TJR_LESSONS: tuple[_LessonSpec, ...] = (
    _LessonSpec(
        id="tjr-psychology",
        order=1,
        title="Trading Psychology: Process Over Outcome",
        simple_explanation="A single trade's outcome is mostly noise — even a well-planned, well-executed trade loses sometimes. Judging yourself by whether one trade won or lost, instead of whether you followed your process, is the single most common psychological trap in trading.",
        deeper_explanation="TradeTown's own Discipline Score (app/discipline.py) is built around exactly this idea: it never reads a trade's P&L. It scores real, checkable process signals instead — stop-loss discipline, position sizing, patience, and following the Gatekeeper's approval — so a losing trade with a strong process still earns a strong Discipline Score, and a winning trade with a sloppy process doesn't.",
        quiz_question="An agent takes a properly-sized, stop-loss-protected trade that the Gatekeeper approved, and it still loses money. What does TradeTown's Discipline Score do?",
        quiz_options=(
            "It stays high — Discipline Score never reads trade P&L",
            "It drops sharply because the trade lost",
            "It's deleted since the trade failed",
            "It's replaced by the trade's dollar loss",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="tjr-daily-routine",
        order=2,
        title="Building a Daily Routine",
        simple_explanation="A consistent pre-market routine — reviewing the plan, checking risk limits, confirming what setups you're looking for — reduces how many decisions you have to make in the heat of the moment, which is when trading mistakes are most likely.",
        deeper_explanation="This lesson is honestly conceptual: TradeTown's own app/schedule.py governs when an agent is available to trade (a workday/off-hours mechanic), which is a different concept from a pre-market mental routine — there's no real 'ritual' system here to point at as an example. The real, actionable version of this lesson is the CEO's own Daily Trading Objectives (Command Center → RISK tab) — reviewing today's profit target, max loss, and trade count limit before the day starts is a real routine step this codebase actually supports.",
        quiz_question="Why does having a routine reduce trading mistakes, according to this lesson?",
        quiz_options=(
            "It cuts down on in-the-moment decisions made under pressure",
            "It guarantees every trade will be profitable",
            "It removes the need for stop losses",
            "It replaces the need for a trading plan",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="tjr-patience",
        order=3,
        title="Patience as a Skill",
        simple_explanation="Patience in trading isn't just 'waiting for a good setup' — it also means giving a position room to work once you're in it, instead of closing it out of nerves the moment it moves against you slightly.",
        deeper_explanation="TradeTown's Discipline Score has a real Patience factor (app/discipline.py's PATIENCE_TARGET_MINUTES, currently 240 simulated minutes): a position held at or past that target scores well on patience, one closed out early scores lower. That's a real, measured signal, not a vibe — you can check any agent's real hold durations against it.",
        quiz_question="What does TradeTown's real Patience factor actually measure?",
        quiz_options=(
            "How long a position was actually held versus a real target duration",
            "How many trades an agent avoided taking",
            "How much money a position made",
            "How many minutes the agent spent thinking before entering",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="tjr-trade-selection",
        order=4,
        title="High-Quality Trade Selection",
        simple_explanation="Not every setup that looks interesting is worth taking. Professional traders filter aggressively — most potential trades get passed on, and that's the system working, not a missed opportunity.",
        deeper_explanation="TradeTown has two real filters that do exactly this: the Gatekeeper (app/gatekeeper.py) blocks a proposal outright on confidence, risk-manager veto, debate disagreement, exposure, correlation, or an active risk warning; and the Daily Trading Objectives (app/risk_engine.py) halt new trades for the rest of the day once the daily loss limit, profit target, or trade-count cap is hit. Both are real, visible rejections in the Command Center — not bugs.",
        quiz_question="A trade proposal gets blocked by the Gatekeeper. What does that mean?",
        quiz_options=(
            "The filter is working as intended — a real check caught a real problem with the trade",
            "The system has a bug and needs to be restarted",
            "The agent is being punished unfairly",
            "The trade will be automatically resubmitted with different numbers",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="tjr-journaling",
        order=5,
        title="Trade Planning & Journaling",
        simple_explanation="Writing down why you took a trade, what you expected, and what actually happened turns a single trade into a reusable lesson — without a journal, you're relying on memory, which quietly rewrites itself to make you look better or worse than you were.",
        deeper_explanation="TradeTown's real Trading Journal (app/journal.py) auto-fills a coach review and lessons-learned entry for every closed trade, tied to the exact TradeDecision that approved it. Its `screenshot` field is honestly a fixed placeholder string, not a real chart image — there's no chart-rendering pipeline in this codebase to generate one, and journal.py's own docstring says so directly rather than faking an image.",
        quiz_question="Why is the Trading Journal's `screenshot` field just a placeholder string?",
        quiz_options=(
            "Because there's no real chart-rendering pipeline to generate an actual image, and the code says so honestly",
            "Because screenshots are considered unimportant",
            "Because it's a bug that was never fixed",
            "Because it's a real image that's just compressed",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="tjr-consistency",
        order=6,
        title="Emotional Control & Consistency",
        simple_explanation="Consistency means trading the same process on your best day and your worst day. It's less about never feeling anything and more about not letting how you feel change what you do.",
        deeper_explanation="TradeTown honestly can't read literal emotion — there's no sentiment or mood signal anywhere in this codebase. The closest real, checkable analogs are the Discipline Score's tier stability over time (app/discipline.py) and the company-wide Wisdom Score (app/wisdom.py), both of which measure real behavioral consistency from real trade and review history, rather than inventing a fabricated 'mood' number.",
        quiz_question="How does TradeTown honestly approach measuring 'emotional control'?",
        quiz_options=(
            "By measuring real behavioral consistency (Discipline tier stability, Wisdom Score) instead of fabricating an emotion reading",
            "By running a sentiment-analysis model on agent dialogue",
            "By asking the agent directly how it feels",
            "It doesn't attempt to measure this at all, silently",
        ),
        correct_index=0,
    ),
)

_LESSON_SPECS_BY_MENTOR: dict[FoundationalMentorId, tuple[_LessonSpec, ...]] = {
    "tjr": _TJR_LESSONS,
    # The other five roadmap tracks intentionally have no entry here yet —
    # see this module's docstring. Adding real content for one of them
    # later is exactly: write its own _LessonSpec tuple and add it here.
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _specs_for(mentor_id: FoundationalMentorId) -> tuple[_LessonSpec, ...]:
    return _LESSON_SPECS_BY_MENTOR.get(mentor_id, ())


def _public_lessons(specs: tuple[_LessonSpec, ...]) -> list[FoundationalMentorLesson]:
    return [
        FoundationalMentorLesson(
            id=s.id,
            order=s.order,
            title=s.title,
            simpleExplanation=s.simple_explanation,
            deeperExplanation=s.deeper_explanation,
            quizQuestion=s.quiz_question,
            quizOptions=list(s.quiz_options),
        )
        for s in sorted(specs, key=lambda s: s.order)
    ]


def default_foundational_mentor_state() -> FoundationalMentorState:
    mentors = []
    for mentor_id in _ROADMAP_ORDER:
        name, focus_areas = _ROADMAP_FOCUS[mentor_id]
        specs = _specs_for(mentor_id)
        mentors.append(
            FoundationalMentorProfile(
                id=mentor_id,
                name=name,
                trackLabel=f"{name} Track",
                focusAreas=focus_areas,
                contentNote=_CONTENT_DISCLAIMER,
                status="active" if specs else "planned",
                lessons=_public_lessons(specs),
                resources=[],
            )
        )
    return FoundationalMentorState(mentors=mentors, progress={}, activeMentorId="tjr", updatedAt=_now_iso())


def _mentor_by_id(state: FoundationalMentorState, mentor_id: FoundationalMentorId) -> FoundationalMentorProfile | None:
    for m in state.mentors:
        if m.id == mentor_id:
            return m
    return None


def _lesson_by_id(mentor: FoundationalMentorProfile, lesson_id: str) -> FoundationalMentorLesson | None:
    for lesson in mentor.lessons:
        if lesson.id == lesson_id:
            return lesson
    return None


def _progress_for(state: FoundationalMentorState, mentor_id: FoundationalMentorId) -> FoundationalMentorProgress:
    return state.progress.get(mentor_id) or FoundationalMentorProgress(mentorId=mentor_id)


def _is_graduated(mentor: FoundationalMentorProfile, progress: FoundationalMentorProgress) -> bool:
    if not mentor.lessons:
        return False
    completed = set(progress.completed_lesson_ids)
    return all(lesson.id in completed for lesson in mentor.lessons)


def _next_roadmap_id(mentor_id: FoundationalMentorId) -> FoundationalMentorId | None:
    idx = _ROADMAP_ORDER.index(mentor_id)
    if idx + 1 >= len(_ROADMAP_ORDER):
        return None
    return _ROADMAP_ORDER[idx + 1]


def mark_lesson_viewed(state: FoundationalMentorState, mentor_id: FoundationalMentorId, lesson_id: str) -> FoundationalMentorState:
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None or _lesson_by_id(mentor, lesson_id) is None:
        return state
    progress = _progress_for(state, mentor_id)
    if lesson_id in progress.viewed_lesson_ids:
        return state
    new_progress = progress.model_copy(update={"viewed_lesson_ids": [*progress.viewed_lesson_ids, lesson_id]})
    new_progress_map = {**state.progress, mentor_id: new_progress}
    return state.model_copy(update={"progress": new_progress_map, "updated_at": _now_iso()})


def grade_lesson_quiz(
    state: FoundationalMentorState,
    mentor_id: FoundationalMentorId,
    lesson_id: str,
    selected_index: int,
    *,
    sim_day: int,
) -> tuple[FoundationalMentorState, bool, int, str] | None:
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None:
        return None
    lesson = _lesson_by_id(mentor, lesson_id)
    spec = next((s for s in _specs_for(mentor_id) if s.id == lesson_id), None)
    if lesson is None or spec is None:
        return None

    correct = selected_index == spec.correct_index
    progress = _progress_for(state, mentor_id)
    completed_ids = list(progress.completed_lesson_ids)
    if correct and lesson_id not in completed_ids:
        completed_ids.append(lesson_id)

    new_progress = progress.model_copy(
        update={
            "completed_lesson_ids": completed_ids,
            "quiz_attempts": progress.quiz_attempts + 1,
            "correct_quiz_attempts": progress.correct_quiz_attempts + (1 if correct else 0),
        }
    )
    new_progress_map = {**state.progress, mentor_id: new_progress}
    new_mentors = list(state.mentors)
    new_active_id = state.active_mentor_id

    already_graduated = mentor.status == "graduated"
    if correct and not already_graduated and _is_graduated(mentor, new_progress):
        new_progress = new_progress.model_copy(update={"graduated_sim_day": sim_day})
        new_progress_map[mentor_id] = new_progress
        new_mentors = [m.model_copy(update={"status": "graduated"}) if m.id == mentor_id else m for m in new_mentors]

        next_id = _next_roadmap_id(mentor_id)
        if next_id is not None:
            next_mentor = _mentor_by_id(state, next_id)
            if next_mentor is not None and next_mentor.status == "planned":
                new_mentors = [m.model_copy(update={"status": "active"}) if m.id == next_id else m for m in new_mentors]
                new_active_id = next_id

    new_state = state.model_copy(update={"mentors": new_mentors, "progress": new_progress_map, "active_mentor_id": new_active_id, "updated_at": _now_iso()})
    return new_state, correct, spec.correct_index, spec.quiz_options[spec.correct_index]


def pause_mentor(state: FoundationalMentorState, mentor_id: FoundationalMentorId) -> tuple[FoundationalMentorState, str | None]:
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None:
        return state, "Unknown mentor track."
    if mentor.status != "active":
        return state, "Only an active track can be paused."
    new_mentors = [m.model_copy(update={"status": "paused"}) if m.id == mentor_id else m for m in state.mentors]
    return state.model_copy(update={"mentors": new_mentors, "updated_at": _now_iso()}), None


def resume_mentor(state: FoundationalMentorState, mentor_id: FoundationalMentorId) -> tuple[FoundationalMentorState, str | None]:
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None:
        return state, "Unknown mentor track."
    if mentor.status != "paused":
        return state, "Only a paused track can be resumed."
    new_mentors = [m.model_copy(update={"status": "active"}) if m.id == mentor_id else m for m in state.mentors]
    return state.model_copy(update={"mentors": new_mentors, "active_mentor_id": mentor_id, "updated_at": _now_iso()}), None


def skip_mentor(state: FoundationalMentorState, mentor_id: FoundationalMentorId) -> tuple[FoundationalMentorState, str | None]:
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None:
        return state, "Unknown mentor track."
    if mentor.status not in ("active", "paused"):
        return state, "Only an active or paused track can be skipped."
    next_id = _next_roadmap_id(mentor_id)
    if next_id is None:
        return state, "This is the last track on the roadmap — nothing to skip to."
    new_mentors = [
        m.model_copy(update={"status": "paused"}) if m.id == mentor_id else (m.model_copy(update={"status": "active"}) if m.id == next_id else m)
        for m in state.mentors
    ]
    return state.model_copy(update={"mentors": new_mentors, "active_mentor_id": next_id, "updated_at": _now_iso()}), None


def repeat_mentor(state: FoundationalMentorState, mentor_id: FoundationalMentorId) -> tuple[FoundationalMentorState, str | None]:
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None:
        return state, "Unknown mentor track."
    if mentor.status != "graduated":
        return state, "Only a graduated track can be repeated."
    new_mentors = [m.model_copy(update={"status": "active"}) if m.id == mentor_id else m for m in state.mentors]
    new_progress_map = {**state.progress, mentor_id: FoundationalMentorProgress(mentorId=mentor_id)}
    return state.model_copy(update={"mentors": new_mentors, "progress": new_progress_map, "active_mentor_id": mentor_id, "updated_at": _now_iso()}), None


def add_resource(
    state: FoundationalMentorState,
    mentor_id: FoundationalMentorId,
    *,
    title: str,
    url: str | None,
    resource_type: FoundationalResourceType,
) -> tuple[FoundationalMentorState, str | None]:
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None:
        return state, "Unknown mentor track."
    clean_title = title.strip()
    if not clean_title:
        return state, "Resource title cannot be empty."
    if len(mentor.resources) >= MAX_RESOURCES_PER_MENTOR:
        return state, f"This track already has the maximum of {MAX_RESOURCES_PER_MENTOR} bookmarked resources."
    resource = FoundationalMentorResource(
        id=f"resource-{mentor_id}-{len(mentor.resources)}",
        title=clean_title,
        url=url,
        resourceType=resource_type,
        addedAt=_now_iso(),
    )
    new_mentors = [m.model_copy(update={"resources": [*m.resources, resource]}) if m.id == mentor_id else m for m in state.mentors]
    return state.model_copy(update={"mentors": new_mentors, "updated_at": _now_iso()}), None
