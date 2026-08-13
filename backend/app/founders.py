"""FounderManager — v0.7 Feature 39, the Original Founders.

The brief describes two Founders whose "teaching style" for both is
near-identical to Sage's already-shipped Socratic Mentor mechanic
(app/mentor.py, Feature 32): "teaches through questions... rarely gives
direct answers... guides employees toward discovering the correct
reasoning themselves." Building a second, independent daily-teaching/
grading system under new names would be exactly the "redundant
re-measurement" trap mentor.py's own module docstring already checked
for once (see its cut "Thinking Session"). It is not repeated here.

Instead, Keystone (Chief Risk Architect) and Compass (Chief Learning
Architect) are framed as the spiritual originators of two already-real
system clusters this codebase built across earlier features — Keystone
for the Discipline Chamber / Library of Mistakes / Risk Engine
(app/discipline.py, app/mistakes.py, Sentinel/Guardian's real
RiskWarnings), Compass for the Academy / Reasoning Lab / Reflection
Chamber (app/reasoning_lab.py, app/wisdom.py, Sage's own domain). Their
presence is: (1) real, hand-authored philosophy/specialty/quote content
taken directly from the brief, displayed as static identity — never
claimed to be freshly "written" by an LLM; (2) one real dialogue line
per day, alternating between the two, that reacts to whichever real
event most recently landed in that Founder's domain (the same
templated-framing-over-real-state convention mentor.py's own
`_related_reference` already established) — never a fabricated
free-form conversation; (3) a real monthly Founder Council session
alongside the existing monthly CoachReport, summarizing the Coach's own
real highlight plus each Founder's own latest domain commentary.

Legendary Status: `FounderState.retired` flips permanently to True the
first time `CompanyHealth.tier` reaches "excellent" — the single most
comprehensive real milestone this codebase already computes (a genuine
average across ten real sub-scores, not a single cherry-picked number).
It never reverts if company health later dips, the same "a crossed
milestone stays crossed" convention app/hall_of_fame.py already
established for its own permanent records. Retirement does not remove
either Founder from the world or change their schedule/personality/
quotes in any way (see schedule.py) — it only unlocks the Hall of
Founders view in the UI.

Explicitly NOT built, and why:
  Unique portraits/animations   — reuse the exact same palette-swapped
                                   sprite convention every other agent
                                   already uses (see AGENT_PROFILES'
                                   `tint`); no new art pipeline exists.
  Voice acting                  — the brief itself calls this
                                   optional ("if voice acting is added
                                   later"); no audio/TTS system exists
                                   anywhere in this codebase.
  Onboarding for new employees  — this codebase has a fixed 11-then-13
                                   agent roster; no new-hire system, no
                                   employee ever joins the company after
                                   the game starts. Nothing to onboard.
  Employees "speaking about them
  with respect" in meetings     — would require editing app/discussion.py's
                                   real, already-tested meeting-dialogue
                                   generator to inject Founder references.
                                   Left as a clean follow-up rather than
                                   risking a working system in this pass.
"""
from __future__ import annotations

from app.schemas import (
    BlackBoxProject,
    BreakthroughReview,
    CaseStudy,
    ChallengeReport,
    CoachReport,
    DisciplineReview,
    FounderCouncilSession,
    FounderId,
    FounderLogEntry,
    FounderState,
    ReasoningChallenge,
    ReflectionSession,
)

# v0.7 — the Advanced Quantitative Research Division's Founder Council
# Review. A completed Black Box Project's discovery survives (or doesn't)
# a real, checkable gate: the Devil's Advocate found no major weakness,
# and the project's own confidence level actually cleared a real bar —
# never a coin flip, and never a fabricated "the Founders debated for
# hours" narrative. See app/black_box.py's module docstring for why this
# is a new mode of generate_council_session() rather than a second,
# independently-invented Founder meeting type.
BREAKTHROUGH_CONFIDENCE_THRESHOLD = 55.0

MAX_FOUNDER_LOG = 120  # roughly four in-game months of daily entries
MAX_COUNCIL_SESSIONS = 24  # two in-game years of monthly sessions

# Verbatim from the brief's own "Common Quotes" for each Founder — real
# authored content, never invented. Cycled deterministically by sim day
# (index = sim_day % len(quotes)), the same convention mentor.py's own
# QUESTION_LIBRARY already established, so "today's quote" is a real,
# repeatable fact about the calendar rather than a random pick.
FOUNDER_QUOTES: dict[FounderId, tuple[str, ...]] = {
    "keystone": (
        "Protecting capital is the first victory.",
        "Discipline beats emotion.",
        "A trade avoided can be just as valuable as a trade taken.",
        "Great traders survive long enough to become great.",
    ),
    "compass": (
        "Curiosity creates breakthroughs.",
        "Never stop asking why.",
        "Knowledge compounds.",
        "The best companies never stop learning.",
    ),
}

FOUNDER_PHILOSOPHY: dict[FounderId, str] = {
    "keystone": "Protect the company first. Profit comes second.",
    "compass": "Every mistake is an opportunity to improve.",
}

FOUNDER_SPECIALTIES: dict[FounderId, tuple[str, ...]] = {
    "keystone": ("Risk Management", "Capital Preservation", "Position Sizing", "Consistency", "Decision Frameworks", "Process Improvement"),
    "compass": ("Research", "Education", "Critical Thinking", "Innovation", "Knowledge Systems", "Long-Term Improvement"),
}

FOUNDER_TEACHING_STYLE: dict[FounderId, str] = {
    "keystone": "Teaches through questions, case studies, and reviewing mistakes. Rarely gives direct answers — guides employees toward discovering the correct reasoning themselves.",
    "compass": "Encourages experimentation, discussion, and challenging assumptions. Rewards thoughtful questions more than quick answers.",
}


def _keystone_reference(
    discipline_reviews: list[DisciplineReview],
    case_studies: list[CaseStudy],
) -> tuple[str, str] | None:
    """Returns (reference, line) pointing at whichever real Keystone-domain
    event happened most recently — never a fabricated one. None if the
    company genuinely has neither yet."""
    review = discipline_reviews[-1] if discipline_reviews else None
    case = case_studies[-1] if case_studies else None
    if review is None and case is None:
        return None
    # Both are append-only permanent logs; whichever was filed more
    # recently by real sim day wins (a tie favors the review, since a
    # CaseStudy is itself derived from a review's own process gap).
    if case is not None and (review is None or case.sim_day >= review.sim_day):
        return (f'the "{case.title}" case in the Library of Mistakes', f'Keystone studied the "{case.title}" case in the Library of Mistakes.')
    assert review is not None
    return (
        f"the {review.symbol} trade's {review.tier} discipline review",
        f"Keystone reviewed the {review.symbol} trade — a {review.tier} process, filed at a discipline score of {review.score:.0f}.",
    )


def _compass_reference(
    reasoning_challenges: list[ReasoningChallenge],
    reflection_sessions: list[ReflectionSession],
) -> tuple[str, str] | None:
    challenge = reasoning_challenges[-1] if reasoning_challenges else None
    session = reflection_sessions[-1] if reflection_sessions else None
    if challenge is None and session is None:
        return None
    if challenge is not None and (session is None or challenge.sim_day >= session.sim_day):
        return (f'the Reasoning Lab\'s "{challenge.title}" challenge', f'Compass sat in on the Reasoning Lab\'s "{challenge.title}" challenge.')
    assert session is not None
    if session.lessons_learned:
        return ("this period's Reflection Chamber session", f'Compass noted the Reflection Chamber\'s own lesson: "{session.lessons_learned[0]}"')
    return ("this period's Reflection Chamber session", "Compass sat in on this period's Reflection Chamber session.")


def generate_founder_log_entry(
    founder_id: FounderId,
    *,
    sim_day: int,
    entry_id: str,
    created_at: str,
    discipline_reviews: list[DisciplineReview],
    case_studies: list[CaseStudy],
    reasoning_challenges: list[ReasoningChallenge],
    reflection_sessions: list[ReflectionSession],
) -> FounderLogEntry | None:
    """One real line for the given Founder, or None if their domain
    genuinely has nothing real to react to yet (an honest empty state,
    never papered over with filler)."""
    found = _keystone_reference(discipline_reviews, case_studies) if founder_id == "keystone" else _compass_reference(reasoning_challenges, reflection_sessions)
    if found is None:
        return None
    reference, line_prefix = found
    quotes = FOUNDER_QUOTES[founder_id]
    quote = quotes[sim_day % len(quotes)]
    return FounderLogEntry(
        id=entry_id,
        founderId=founder_id,
        line=f'{line_prefix} "{quote}"',
        reference=reference,
        simDay=sim_day,
        createdAt=created_at,
    )


def record_founder_log(log: list[FounderLogEntry], entry: FounderLogEntry) -> list[FounderLogEntry]:
    updated = [*log, entry]
    if len(updated) > MAX_FOUNDER_LOG:
        del updated[: len(updated) - MAX_FOUNDER_LOG]
    return updated


def generate_council_session(
    *,
    sim_day: int,
    session_id: str,
    created_at: str,
    latest_coach_report: CoachReport | None,
    discipline_reviews: list[DisciplineReview],
    case_studies: list[CaseStudy],
    reasoning_challenges: list[ReasoningChallenge],
    reflection_sessions: list[ReflectionSession],
) -> FounderCouncilSession:
    """v0.7 Feature 39 — the Founder Council: the Coach's real monthly
    sit-down with both Founders, generated alongside the existing
    monthly CoachReport (see nexus.py's own monthly-cadence gate) —
    never a duplicate, independently-invented meeting transcript.

    CEO Company/Executive Health directive, Phase 4 — each note's real
    `_is_real` flag (see FounderCouncilSession's own schema docstring)
    is set from the exact same truthy check already used to choose that
    note's text, never re-derived by string-matching the fallback text
    after the fact."""
    coach_highlight_is_real = latest_coach_report is not None and bool(latest_coach_report.strengths or latest_coach_report.recommendations)
    if latest_coach_report is None:
        coach_highlight = "No Coach Report has been filed yet this month."
    elif latest_coach_report.strengths:
        coach_highlight = latest_coach_report.strengths[0]
    elif latest_coach_report.recommendations:
        coach_highlight = latest_coach_report.recommendations[0]
    else:
        coach_highlight = "No standout pattern yet this period."

    keystone_found = _keystone_reference(discipline_reviews, case_studies)
    keystone_note = f"Worth revisiting: {keystone_found[0]}." if keystone_found else "Nothing to review yet — no trades have closed."

    compass_found = _compass_reference(reasoning_challenges, reflection_sessions)
    compass_note = f"Worth revisiting: {compass_found[0]}." if compass_found else "Nothing new to add yet."

    return FounderCouncilSession(
        id=session_id,
        simDay=sim_day,
        coachHighlight=coach_highlight,
        keystoneNote=keystone_note,
        compassNote=compass_note,
        coachHighlightIsReal=coach_highlight_is_real,
        keystoneNoteIsReal=keystone_found is not None,
        compassNoteIsReal=compass_found is not None,
        createdAt=created_at,
    )


def record_council_session(sessions: list[FounderCouncilSession], session: FounderCouncilSession) -> list[FounderCouncilSession]:
    updated = [*sessions, session]
    if len(updated) > MAX_COUNCIL_SESSIONS:
        del updated[: len(updated) - MAX_COUNCIL_SESSIONS]
    return updated


def generate_breakthrough_review(
    project: BlackBoxProject,
    *,
    challenge: ChallengeReport,
    sim_day: int,
    review_id: str,
    created_at: str,
) -> BreakthroughReview:
    """The Founder Council's real, checkable verdict on whether a
    completed Black Box Project becomes an official Company Breakthrough
    (see module-level BREAKTHROUGH_CONFIDENCE_THRESHOLD)."""
    approved = challenge.severity != "major" and project.confidence_level >= BREAKTHROUGH_CONFIDENCE_THRESHOLD
    if approved:
        verdict_reason = f"The Devil's Advocate found {challenge.severity.replace('_', ' ')}, and confidence held at {project.confidence_level:.0f}/100 — the Council approves this as an official Company Breakthrough."
    elif challenge.severity == "major":
        verdict_reason = f"The Devil's Advocate found real weaknesses ({len(challenge.hidden_risks) + len(challenge.weak_assumptions) + len(challenge.missing_evidence)} concerns raised) — the Council is not willing to sign off yet."
    else:
        verdict_reason = f"Confidence only reached {project.confidence_level:.0f}/100, short of the Council's {BREAKTHROUGH_CONFIDENCE_THRESHOLD:.0f} bar for an official breakthrough."

    return BreakthroughReview(
        id=review_id,
        projectId=project.id,
        projectTitle=project.title,
        simDay=sim_day,
        hypothesis=project.objective,
        evidence=project.quant_journal[-5:],
        statisticalResults=f"Final confidence level: {project.confidence_level:.0f}/100 after {project.progress:.0f}% completion over {project.estimated_completion_sim_day - project.started_sim_day} in-game days.",
        risks=project.obstacles,
        limitations=", ".join(challenge.weak_assumptions) if challenge.weak_assumptions else "No weak assumptions were flagged.",
        devilsAdvocateCase=challenge.bear_case,
        recommendation=challenge.final_recommendation,
        verdict="approved" if approved else "rejected",
        verdictReason=verdict_reason,
        createdAt=created_at,
    )


def compute_founder_state(
    previous: FounderState,
    *,
    company_health_tier: str,
    updated_at: str,
) -> FounderState:
    """`retired` only ever turns True, never back False — a crossed
    milestone stays crossed (see module docstring)."""
    newly_retired = not previous.retired and company_health_tier == "excellent"
    return previous.model_copy(
        update={
            "retired": previous.retired or newly_retired,
            "retired_at": updated_at if newly_retired else previous.retired_at,
            "updated_at": updated_at,
        }
    )
