"""MentorManager — v0.7 Feature 32, Sage the Socratic Mentor.

Sage never gives an answer — see agents.py's AGENT_PROFILES entry. This
module builds the one concrete artifact the brief actually asks for that
this codebase can back honestly: a daily QuestionOfTheDay drawn from a
small hand-authored QUESTION_LIBRARY (real curated content, the same
convention DialogueManager's own flavor lines already use — there is no
free-form question-generation capability here, so nothing claims the
Mentor is "writing" a new question each morning) plus a per-agent
ThinkingProfile computed purely from signals this codebase already
tracks for other real reasons.

Several of the brief's named sub-features were checked against this
codebase's real, checkable signals and explicitly NOT built, rather than
faked:

  A separate weekly "Mentor Session"  — app/wisdom.py's ReflectionSession
                                         already IS a real weekly/monthly
                                         company-wide gathering built
                                         around real, Socratic-style
                                         questions (see its own module
                                         docstring). Building a second,
                                         parallel "Thinking Session" would
                                         just be the same real signals
                                         re-packaged under a new name —
                                         the "redundant re-measurement"
                                         trap this session's other
                                         features have consistently
                                         avoided. Not duplicated here.
  "Thinking Exercises"                — this is app/reasoning_lab.py's
                                         ReasoningChallenge, already
                                         shipped (Feature 29) and already
                                         covering 7 of the brief's 10
                                         named exercise types with a real
                                         signal each. Not duplicated here.
  Personal Coaching / improvement
  areas per employee                  — would require a real per-agent
                                         weakness signal distinct from
                                         ThinkingProfile's own traits
                                         below; none exists, so this is
                                         left as an explicit scope cut
                                         rather than restating the same
                                         traits as "coaching areas."
  A graded "Daily Thinking Bonus"     — grading open-ended player free
                                         text has no honest mechanism in
                                         this codebase (the same
                                         constraint that already kept
                                         Reflection Journal entries
                                         ungraded in Feature 30). The
                                         player's QuestionOfTheDay answer
                                         is stored and never scored.
  "Connected Constitution Articles"   — no Company Constitution system
                                         exists anywhere in this codebase
                                         (checked directly); nothing here
                                         references one.
  Question Library "used live by
  departments during meetings"        — NEXUS's meeting-generation code
                                         (app/scribe.py's discussion
                                         generator) has no hook to pull
                                         from an external question bank
                                         without fabricating dialogue.
                                         The library is real, authored
                                         content the player can browse;
                                         it is not consumed by NPCs.
  A dedicated physical "Mentor
  Chamber" room                       — the same Command-Center-tab-not-
                                         new-scene precedent every recent
                                         feature (Academy, Discipline
                                         Chamber, Reasoning Lab,
                                         Reflection Chamber) already
                                         established; Sage's home
                                         location reuses brain-room (see
                                         agents.py).
"""
from __future__ import annotations

from app.schemas import (
    AgentId,
    AgentKnowledgeState,
    CaseStudy,
    DisciplineReview,
    ExecutiveReview,
    MentorState,
    QuestionCategory,
    QuestionOfTheDay,
    ReasoningChallenge,
    ReflectionSession,
    ResearchItem,
    RiskWarning,
    ThinkingProfile,
    ThinkingTrait,
)

MAX_QUESTION_ARCHIVE = 120  # roughly four in-game months of daily entries

# Two hand-authored questions per category — real, curated prompts (see
# module docstring). The Mentor cycles through this library
# deterministically by sim day (index = sim_day % len(QUESTION_LIBRARY)),
# so "today's question" is a real, repeatable fact about the calendar,
# never a random or fabricated daily generation.
QUESTION_LIBRARY: tuple[tuple[QuestionCategory, str], ...] = (
    ("critical_thinking", "What assumption are we making today that deserves another look?"),
    ("decision_making", "What would change our minds about our current biggest position?"),
    ("communication", "If another department heard our reasoning, would it actually make sense to them?"),
    ("leadership", "What are we avoiding saying out loud because it's uncomfortable?"),
    ("psychology", "Where might we be more confident than the evidence actually supports?"),
    ("risk_awareness", "What's the one thing that would hurt us most if we're wrong?"),
    ("research", "What's the simplest explanation for what we're seeing — and did we check it first?"),
    ("reflection", "What lesson from our own history applies to today?"),
    ("logic", "Does our conclusion actually follow from our evidence, or just from our hopes?"),
    ("teamwork", "Who on the team would disagree with us right now, and why might they be right?"),
    ("critical_thinking", "What question haven't we asked yet?"),
    ("decision_making", "Are we solving the problem in front of us, or the one we're used to solving?"),
    ("communication", "What are we saying that we haven't actually verified?"),
    ("leadership", "What would we tell a new hire to watch out for today?"),
    ("psychology", "What would a beginner notice here that we've stopped noticing?"),
    ("risk_awareness", "What's the quiet risk we've stopped mentioning because nothing's gone wrong yet?"),
    ("research", "What information are we missing that we haven't gone looking for?"),
    ("reflection", "What did we get right recently for the wrong reasons?"),
    ("logic", "What alternative explanation would a skeptic offer for what we just concluded?"),
    ("teamwork", "What did we learn from someone else's mistake this week instead of our own?"),
)

_CATEGORY_LABELS: dict[QuestionCategory, str] = {
    "critical_thinking": "Critical Thinking",
    "decision_making": "Decision Making",
    "communication": "Communication",
    "leadership": "Leadership",
    "psychology": "Psychology",
    "risk_awareness": "Risk Awareness",
    "research": "Research",
    "reflection": "Reflection",
    "logic": "Logic",
    "teamwork": "Teamwork",
}


def category_label(category: QuestionCategory) -> str:
    return _CATEGORY_LABELS[category]


def _related_reference(
    category: QuestionCategory,
    *,
    case_studies: list[CaseStudy],
    reasoning_challenges: list[ReasoningChallenge],
    research: list[ResearchItem],
    reflection_sessions: list[ReflectionSession],
    risk_warnings: list[RiskWarning],
    executive_reviews: list[ExecutiveReview],
) -> str | None:
    """At most one honest pointer into real, already-existing company
    content sharing this question's category — never a fabricated
    per-department "discussion." Returns None when nothing real yet
    exists to point to (a young company legitimately has nothing to
    reference), which the caller/UI must handle, not paper over."""
    if category in ("critical_thinking", "logic") and reasoning_challenges:
        latest_challenge = reasoning_challenges[-1]
        return f'This connects to the Reasoning Lab\'s "{latest_challenge.title}" challenge.'
    if category == "psychology" and case_studies:
        latest_case = case_studies[-1]
        return f'The Library of Mistakes\' "{latest_case.title}" case study explored exactly this.'
    if category == "risk_awareness":
        if risk_warnings:
            return f"Sentinel flagged this recently: {risk_warnings[-1].message}"
        if case_studies:
            return f'The Library of Mistakes\' "{case_studies[-1].title}" case study is worth revisiting here.'
    if category == "research":
        completed = [r for r in research if r.status == "completed"]
        if completed:
            return f'"{completed[-1].title}" is a recent example worth thinking about.'
    if category == "reflection" and reflection_sessions:
        lessons = reflection_sessions[-1].lessons_learned
        if lessons:
            return f"This period's Reflection Chamber session noted: {lessons[0]}"
    if category == "leadership" and executive_reviews:
        events = executive_reviews[-1].major_events
        if events:
            return f"Meridian's last review flagged: {events[0]}"
    if category == "decision_making" and case_studies:
        latest_decision_case = case_studies[-1]
        return f'"{latest_decision_case.title}" is a real decision worth revisiting here.'
    if category == "communication" and reflection_sessions and reflection_sessions[-1].insights:
        return reflection_sessions[-1].insights[0].insight
    if category == "teamwork" and reflection_sessions:
        latest_session = reflection_sessions[-1]
        return f"{len(latest_session.attendees)} departments sat down together at the last Reflection Chamber session."
    return None


def generate_question_of_the_day(
    *,
    sim_day: int,
    question_id: str,
    created_at: str,
    case_studies: list[CaseStudy],
    reasoning_challenges: list[ReasoningChallenge],
    research: list[ResearchItem],
    reflection_sessions: list[ReflectionSession],
    risk_warnings: list[RiskWarning],
    executive_reviews: list[ExecutiveReview],
) -> QuestionOfTheDay:
    category, question = QUESTION_LIBRARY[sim_day % len(QUESTION_LIBRARY)]
    reference = _related_reference(
        category,
        case_studies=case_studies,
        reasoning_challenges=reasoning_challenges,
        research=research,
        reflection_sessions=reflection_sessions,
        risk_warnings=risk_warnings,
        executive_reviews=executive_reviews,
    )
    return QuestionOfTheDay(
        id=question_id,
        category=category,
        question=question,
        relatedReference=reference,
        simDay=sim_day,
        createdAt=created_at,
    )


def record_question(archive: list[QuestionOfTheDay], question: QuestionOfTheDay) -> list[QuestionOfTheDay]:
    updated = [*archive, question]
    if len(updated) > MAX_QUESTION_ARCHIVE:
        del updated[: len(updated) - MAX_QUESTION_ARCHIVE]
    return updated


def submit_response(archive: list[QuestionOfTheDay], question_id: str, response: str, *, responded_at: str) -> tuple[list[QuestionOfTheDay], str | None]:
    """Stores the player's free-text answer verbatim — never graded or
    scored (see module docstring's "Daily Thinking Bonus" cut). Returns
    (archive, error); error is None on success."""
    if not response.strip():
        return archive, "A response can't be empty."
    found = False
    updated: list[QuestionOfTheDay] = []
    for entry in archive:
        if entry.id == question_id:
            found = True
            updated.append(entry.model_copy(update={"player_response": response.strip(), "player_responded_at": responded_at}))
        else:
            updated.append(entry)
    if not found:
        return archive, f"No QuestionOfTheDay found with id {question_id!r}."
    return updated, None


# Every trait below reuses a distinct, already-real signal — see
# ThinkingTraitId's own docstring in schemas.py for why "Patience"
# (DisciplineReview's own factor) and the brief's "Communication"/
# "Adaptability" (no real per-agent signal exists) are not traits here.
_TRAIT_NAMES: dict[str, str] = {
    "curiosity": "Curiosity",
    "evidence_quality": "Evidence Quality",
    "open_mindedness": "Open-Mindedness",
    "humility": "Humility",
    "reasoning": "Reasoning",
    "collaboration": "Collaboration",
}

# Academy points needed to read as a "fully curious" 100 on this trait —
# matches academy.py's own TIER_THRESHOLDS scale (30 points sits between
# its "advanced" and "expert" tiers), reused rather than inventing a
# second unrelated points scale.
_CURIOSITY_POINTS_FOR_100 = 30.0
# Reasoning Lab contributions + Reflection Chamber insights needed to
# read as a "fully collaborative" 100 — deliberately generous (10 real
# events) since both sources are capped, infrequent lists.
_COLLABORATION_EVENTS_FOR_100 = 10.0


def _factor_average(reviews: list[DisciplineReview], factor_id: str) -> float | None:
    scores = [f.score for review in reviews for f in review.factors if f.id == factor_id]
    if not scores:
        return None
    return sum(scores) / len(scores)


def compute_thinking_profiles(
    agent_ids: tuple[AgentId, ...],
    *,
    discipline_reviews: list[DisciplineReview],
    reasoning_challenges: list[ReasoningChallenge],
    reflection_sessions: list[ReflectionSession],
    agent_knowledge: dict[AgentId, AgentKnowledgeState],
    updated_at: str,
) -> dict[AgentId, ThinkingProfile]:
    profiles: dict[AgentId, ThinkingProfile] = {}
    for agent_id in agent_ids:
        reviews = [r for r in discipline_reviews if agent_id in r.attendees]

        research_depth_avg = _factor_average(reviews, "research_depth")
        viewpoint_avg = _factor_average(reviews, "viewpoint_diversity")
        uncertainty_avg = _factor_average(reviews, "uncertainty_acknowledged")
        assumptions_avg = _factor_average(reviews, "assumptions_challenged")
        cross_exam_avg = _factor_average(reviews, "cross_examination")
        reasoning_avg = None if assumptions_avg is None or cross_exam_avg is None else (assumptions_avg + cross_exam_avg) / 2

        knowledge = agent_knowledge.get(agent_id)
        curiosity_score = min(100.0, (knowledge.points / _CURIOSITY_POINTS_FOR_100) * 100.0) if knowledge else 0.0
        curiosity_detail = (
            f"{knowledge.points:.1f} Academy knowledge points earned in {knowledge.branch}." if knowledge else "No Academy points earned yet."
        )

        contribution_count = sum(1 for challenge in reasoning_challenges for c in challenge.contributions if c.agent_id == agent_id)
        insight_count = sum(1 for session in reflection_sessions for i in session.insights if i.agent_id == agent_id)
        collaboration_score = min(100.0, ((contribution_count + insight_count) / _COLLABORATION_EVENTS_FOR_100) * 100.0)

        traits = [
            ThinkingTrait(id="curiosity", name=_TRAIT_NAMES["curiosity"], score=round(curiosity_score, 1), detail=curiosity_detail),
            ThinkingTrait(
                id="evidence_quality",
                name=_TRAIT_NAMES["evidence_quality"],
                score=round(research_depth_avg if research_depth_avg is not None else 50.0, 1),
                detail=(f"Averaged {research_depth_avg:.0f}/100 Research Depth across {len(reviews)} Discipline Review(s)." if research_depth_avg is not None else "No Discipline Reviews attended yet — starts at a neutral baseline."),
            ),
            ThinkingTrait(
                id="open_mindedness",
                name=_TRAIT_NAMES["open_mindedness"],
                score=round(viewpoint_avg if viewpoint_avg is not None else 50.0, 1),
                detail=(f"Averaged {viewpoint_avg:.0f}/100 Viewpoint Diversity across {len(reviews)} Discipline Review(s)." if viewpoint_avg is not None else "No Discipline Reviews attended yet — starts at a neutral baseline."),
            ),
            ThinkingTrait(
                id="humility",
                name=_TRAIT_NAMES["humility"],
                score=round(uncertainty_avg if uncertainty_avg is not None else 50.0, 1),
                detail=(f"Averaged {uncertainty_avg:.0f}/100 Uncertainty Acknowledged across {len(reviews)} Discipline Review(s)." if uncertainty_avg is not None else "No Discipline Reviews attended yet — starts at a neutral baseline."),
            ),
            ThinkingTrait(
                id="reasoning",
                name=_TRAIT_NAMES["reasoning"],
                score=round(reasoning_avg if reasoning_avg is not None else 50.0, 1),
                detail=(f"Averaged {reasoning_avg:.0f}/100 across Assumptions Challenged and Cross-Examination in {len(reviews)} Discipline Review(s)." if reasoning_avg is not None else "No Discipline Reviews attended yet — starts at a neutral baseline."),
            ),
            ThinkingTrait(
                id="collaboration",
                name=_TRAIT_NAMES["collaboration"],
                score=round(collaboration_score, 1),
                detail=f"{contribution_count} Reasoning Lab contribution(s) + {insight_count} Reflection Chamber insight(s).",
            ),
        ]
        profiles[agent_id] = ThinkingProfile(agentId=agent_id, traits=traits, updatedAt=updated_at)
    return profiles


# Archive-length thresholds for MentorState.tier — matches the real
# calendar rhythm the brief itself describes ("over months of in-game
# time"): a week, a month, and a full season of daily questions.
_TIER_THRESHOLDS = (7, 30, 90)
_TIER_LABELS = ("New Tradition", "Taking Root", "Established Ritual", "Defining Tradition")


def compute_mentor_state(archive_length: int, updated_at: str) -> MentorState:
    tier = 0
    for threshold in _TIER_THRESHOLDS:
        if archive_length >= threshold:
            tier += 1
    return MentorState(tier=tier, tierLabel=_TIER_LABELS[tier], questionsAsked=archive_length, updatedAt=updated_at)
