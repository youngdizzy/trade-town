""""TradeTown — Learning Organization 1.0."

This directive's own Phase 0 forensic audit (four parallel research
passes over app/institutional_memory.py, app/discipline.py,
app/debate.py/devils_advocate.py/executive_intelligence.py/
performance_review.py, and app/constitution.py/override_governance.py)
found the "record a lesson" half of the learning loop already real and
nearly complete (Institutional Memory 2.0), but zero hits anywhere in
the codebase, under any name, for the "share it, apply it, confirm or
contradict it" half. This module is exactly that missing half — a thin
telemetry + distribution layer over real, already-computed evidence,
never a second lesson store and never an LLM narrative.

Three real, disclosed design decisions, each made because no honest
alternative existed:

1. Knowledge distribution (`share_lesson_with_relevant_agents`) uses a
   predeclared, static role-class → source mapping over
   app/performance_review.py's own AGENT_ROLE_CLASS (this codebase's
   first machine-usable agent taxonomy) rather than any kind of
   simulated "who would care about this" judgment.

2. Knowledge *application* (`record_knowledge_application_from_challenge`)
   reuses the one real, already-existing, non-behavior-changing signal
   this codebase has for "an agent actually cited a documented past
   lesson while reasoning about a new decision": a ChallengeReport's own
   `historical_comparisons` field (app/devils_advocate.py:107), which is
   already real CaseStudy titles cited for the live proposal's symbol.
   Nothing feeds this back into the Devil's Advocate's own severity or
   recommendation — recording that the citation happened does not change
   what it produced, so trading behavior is untouched (per this
   directive's own Section 22).

3. Lesson confirmation reuses app/institutional_memory.py's
   record_and_link_institutional_memory() — when a new promotion links
   to an existing active entry (real word-overlap on the same source),
   that link IS the corroboration signal; a lesson_confirmed
   KnowledgeEvent is emitted alongside it. True contradiction detection
   (opposite-valence evidence) has no real signal in this codebase to
   back it yet — KnowledgeEventType still reserves "lesson_contradicted"
   for a future milestone, but nothing here ever emits it. See
   CHANGELOG.md for this disclosed scope cut.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.performance_review import AGENT_ROLE_CLASS
from app.schemas import (
    AgentId,
    AgentRoleClass,
    CaseStudy,
    ChallengeReport,
    InstitutionalMemoryEntry,
    InstitutionalMemorySource,
    KnowledgeEvent,
)

MAX_KNOWLEDGE_EVENTS = 400

# Which real agent role classes a lesson from each real institutional-
# memory source is actually relevant to — a predeclared, static mapping
# (not a simulated judgment), matching this codebase's existing
# MISTAKE_ARTICLE_MAP (app/constitution.py) convention for "a fixed,
# disclosed table beats an invented per-case heuristic."
LESSON_RELEVANT_ROLE_CLASSES: dict[InstitutionalMemorySource, tuple[AgentRoleClass, ...]] = {
    "behavioral_mistake": ("researcher", "risk"),
    "behavioral_success": ("researcher", "quant"),
    "strategy_failure": ("quant", "researcher"),
    "strategy_success": ("quant", "researcher"),
    "model_validation": ("quant",),
    "risk_event": ("risk",),
    "market_regime_shift": ("researcher", "quant"),
    "prediction": ("researcher", "quant"),
    "failure_classification": ("risk", "researcher"),
    "research_lesson": ("researcher", "quant"),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_knowledge_event(
    existing: list[KnowledgeEvent],
    event: KnowledgeEvent | None,
    *,
    max_entries: int = MAX_KNOWLEDGE_EVENTS,
) -> list[KnowledgeEvent]:
    """The one real writer gateway (matches app/institutional_memory.py's
    own record_institutional_memory() append-and-cap convention).
    Idempotent by construction: every KnowledgeEvent id below is derived
    deterministically from its real originating record, so replaying the
    same real trigger twice (e.g. a re-run tick, a retried request)
    never double-records it."""
    if event is None:
        return existing
    if any(e.id == event.id for e in existing):
        return existing
    updated = [*existing, event]
    if len(updated) > max_entries:
        del updated[: len(updated) - max_entries]
    return updated


def lesson_created_event(entry: InstitutionalMemoryEntry) -> KnowledgeEvent | None:
    """Only fires for an entry that actually has a real, non-None
    `lesson` — many institutional-memory entries (e.g. a routine risk
    event with nothing to interpret) honestly carry no lesson at all,
    per InstitutionalMemoryEntry's own docstring, and recording a
    LESSON_CREATED event for one would misrepresent it as an actionable
    takeaway that was never actually filed."""
    if entry.lesson is None:
        return None
    return KnowledgeEvent(
        id=f"ke-created-{entry.id}",
        type="lesson_created",
        lessonId=entry.id,
        agentId=entry.originating_agent,
        simDay=entry.sim_day,
        detail=entry.lesson,
        createdAt=entry.created_at,
    )


def lesson_confirmed_event(entry: InstitutionalMemoryEntry, linked_to_id: str) -> KnowledgeEvent:
    """Called only when record_and_link_institutional_memory() actually
    linked `entry` to an existing active entry (`linked_to_id`) — the
    real corroboration signal itself, not an invented one."""
    return KnowledgeEvent(
        id=f"ke-confirmed-{entry.id}",
        type="lesson_confirmed",
        lessonId=linked_to_id,
        agentId=entry.originating_agent,
        simDay=entry.sim_day,
        detail=f"New evidence ({entry.id}) corroborates the standing lesson: {entry.observation}",
        createdAt=entry.created_at,
    )


def share_lesson_with_relevant_agents(
    entry: InstitutionalMemoryEntry,
    *,
    roster: dict[AgentId, AgentRoleClass] | None = None,
) -> list[KnowledgeEvent]:
    """Real, deterministic distribution: every agent whose real role
    class (AGENT_ROLE_CLASS) is on LESSON_RELEVANT_ROLE_CLASSES for this
    entry's own real source, excluding the entry's own originating agent
    when there is one. Returns [] for a lesson with no actionable
    `lesson` text (nothing to share) or a source with no declared
    relevant role class."""
    if entry.lesson is None:
        return []
    relevant_classes = LESSON_RELEVANT_ROLE_CLASSES.get(entry.source, ())
    if not relevant_classes:
        return []
    resolved_roster = roster if roster is not None else AGENT_ROLE_CLASS
    recipients = sorted(
        agent
        for agent, role_class in resolved_roster.items()
        if role_class in relevant_classes and agent != entry.originating_agent
    )
    if not recipients:
        return []
    events = [
        KnowledgeEvent(
            id=f"ke-shared-{entry.id}",
            type="lesson_shared",
            lessonId=entry.id,
            agentId=entry.originating_agent,
            simDay=entry.sim_day,
            detail=f"Shared with {', '.join(agent.title() for agent in recipients)}: {entry.lesson}",
            createdAt=entry.created_at,
        )
    ]
    events.extend(
        KnowledgeEvent(
            id=f"ke-received-{entry.id}-{agent}",
            type="knowledge_received",
            lessonId=entry.id,
            agentId=agent,
            simDay=entry.sim_day,
            detail=entry.lesson,
            createdAt=entry.created_at,
        )
        for agent in recipients
    )
    return events


def record_knowledge_application_from_challenge(
    report: ChallengeReport,
    case_studies: list[CaseStudy],
    institutional_memory: list[InstitutionalMemoryEntry],
    *,
    sim_day: int,
) -> KnowledgeEvent | None:
    """report.historical_comparisons already holds real CaseStudy titles
    this Devil's Advocate challenge cited for the live proposal's symbol
    (app/devils_advocate.py:107) — joined back here to the real promoted
    InstitutionalMemoryEntry (via promote_case_study()'s own
    `im-case-{case_study.id}` id / `event_ref` convention) so a
    KNOWLEDGE_APPLIED event only ever fires for a lesson this named
    agent genuinely retrieved and cited, never a fabricated "agent
    consulted memory" claim. Returns None when nothing was actually
    cited, or the citation doesn't resolve back to a real promoted
    entry."""
    if not report.historical_comparisons:
        return None
    cited_titles = set(report.historical_comparisons)
    cited_case_study_ids = {cs.id for cs in case_studies if cs.title in cited_titles}
    if not cited_case_study_ids:
        return None
    lesson_entry = next(
        (
            memory
            for memory in institutional_memory
            if memory.event_ref in cited_case_study_ids and memory.source in ("behavioral_mistake", "behavioral_success")
        ),
        None,
    )
    if lesson_entry is None:
        return None
    return KnowledgeEvent(
        id=f"ke-applied-{report.id}",
        type="knowledge_applied",
        lessonId=lesson_entry.id,
        agentId=report.assigned_agent,
        simDay=sim_day,
        detail=f'{report.assigned_agent.title()} cited a documented past lesson on {report.symbol}: "{lesson_entry.lesson or lesson_entry.observation}"',
        createdAt=_now_iso(),
    )
