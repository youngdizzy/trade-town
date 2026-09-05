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
   originally reused a ChallengeReport's own `historical_comparisons`
   field (real CaseStudy titles for the live proposal's symbol) via a
   fragile reverse title-match. CEO directive "TradeTown — Knowledge
   Application Loop 1.0" replaced that with a real, direct id link:
   app/devils_advocate.py's generate_challenge_report() now runs
   app/institutional_memory.py's own canonical
   retrieve_relevant_memory() (previously fully built, fully tested, and
   never once called — this directive's own Phase 0 finding) for every
   real ChallengeReport, and `ChallengeReport.retrieved_memory_id` is
   what this function keys off of. Nothing feeds this back into the
   Devil's Advocate's own severity or recommendation — recording that
   the retrieval/citation happened does not change what it produced, so
   trading behavior is untouched.

3. Lesson confirmation reuses app/institutional_memory.py's
   record_and_link_institutional_memory() — when a new promotion links
   to an existing active entry (real word-overlap on the same source),
   that link IS the corroboration signal; a lesson_confirmed
   KnowledgeEvent is emitted alongside it.

4. CEO directive "TradeTown — Knowledge Application Loop 1.0" closes the
   loop this module's prior version disclosed as its one open gap:
   `grade_knowledge_applications()` grades every real `knowledge_applied`
   event against real subsequent evidence (a real decision's own
   "no_trade" outcome, or a real closed trade's own real P&L via
   PaperTradeJournalEntry) — never a single-example judgment, and never
   forced into supported/contradicted when the evidence is genuinely
   absent (an honest "inconclusive"/still-"pending" instead).
   `lessons_needing_contradiction_flag()` then names which memories have
   earned real, repeated, net-negative evidence, for
   app/institutional_memory.py's `apply_contradiction_evidence()` to
   act on — the first real, evidence-backed use of
   InstitutionalMemoryStatus "contradicted" this codebase has ever had.
   True *automatic* contradiction detection from raw text valence
   remains out of scope (see CHANGELOG.md) — this is trade-outcome-based
   evidence, not NLP.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from app.performance_review import AGENT_ROLE_CLASS
from app.schemas import (
    AgentId,
    AgentRoleClass,
    ChallengeReport,
    InstitutionalMemoryEntry,
    InstitutionalMemorySource,
    KnowledgeEvent,
    PaperTradeJournalEntry,
    TradeDecision,
)

MAX_KNOWLEDGE_EVENTS = 400

# CEO directive "TradeTown — Knowledge Application Loop 1.0" — a
# conservative, disclosed threshold for `lessons_needing_contradiction_
# flag()`: never flip a memory to "contradicted" from one disagreeing
# example. Same disclosed-constant convention as
# app/institutional_memory.py's own CORROBORATION_CAP.
CONTRADICTION_THRESHOLD = 2

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
    institutional_memory: list[InstitutionalMemoryEntry],
    *,
    sim_day: int,
) -> KnowledgeEvent | None:
    """CEO directive "TradeTown — Knowledge Application Loop 1.0" —
    superseding this function's own prior title-string reverse-match
    (which only ever worked for CaseStudy-sourced memories, and could
    silently mismatch on a duplicate title). `report.retrieved_memory_id`
    is now the real, direct, id-linked signal: app/devils_advocate.py's
    generate_challenge_report() already ran the canonical
    retrieve_relevant_memory() for this proposal's own symbol before the
    report was ever built, so this id — when present — IS a real
    retrieval this named agent genuinely consulted while building the
    report, for ANY real memory source type, never a fabricated "agent
    consulted memory" claim. Returns None when no real memory was
    retrieved for this report, or (defensively) if the id no longer
    resolves to a real entry."""
    if report.retrieved_memory_id is None:
        return None
    lesson_entry = next((memory for memory in institutional_memory if memory.id == report.retrieved_memory_id), None)
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
        contextRef=report.proposal_id,
        applicationStatus="pending",
    )


def grade_knowledge_applications(
    events: list[KnowledgeEvent],
    *,
    institutional_memory: list[InstitutionalMemoryEntry],
    decisions: list[TradeDecision],
    paper_trade_journal: list[PaperTradeJournalEntry],
) -> list[KnowledgeEvent]:
    """CEO directive "TradeTown — Knowledge Application Loop 1.0" — the
    one real outcome grader for `knowledge_applied` events, reusing the
    exact "grade later, against real subsequent evidence, never
    fabricated" pattern app/opportunity_gatekeeper.py's
    grade_opportunity_rejections()/app/gatekeeper.py's
    grade_gatekeeper_rejections() already established — except here a
    real EXECUTED trade's own real P&L is available (a strictly more
    precise signal than those two functions' window-elapsed price-change
    proxy, since no proxy is needed once a real trade has actually
    closed).

    For each event with type=="knowledge_applied" and
    application_status=="pending" (every other event is left untouched —
    grading is idempotent, never re-evaluates an already-evaluated
    event):

      1. Resolve the real TradeDecision this application's proposal
         produced via resolve_proposal()'s own established
         `f"decision-{proposal.id}"` id convention (app/executive.py).
         No matching decision yet -> still PENDING, left unchanged (the
         CEO hasn't decided this proposal yet).
      2. decision.outcome == "no_trade" (CEO chose wait, OR the Trade
         Gatekeeper rejected a buy/sell — app/executive.py's own
         `outcome="trade" if order_id is not None else "no_trade"`
         collapses both into this one value) -> a real TERMINAL state:
         no trade will ever exist to grade this application against.
         Evaluated as "inconclusive", `outcome_ref` = the decision's own
         id (the real evidence for "no outcome exists"), never left
         pending forever.
      3. decision.outcome == "trade" but no matching
         PaperTradeJournalEntry yet (`proposal_id` match) -> the position
         is still open -> still PENDING, left unchanged.
      4. A matching PaperTradeJournalEntry exists -> real, closed P&L.
         The one real, disclosed, conservative evaluation rule this
         milestone can honestly support (see this module's own CHANGELOG
         entry for why a fully general free-text claim parser is out of
         scope): the retrieved memory's own real `source` encodes its
         claim's valence — "behavioral_mistake" is a real documented
         WARNING (a past mistake), "behavioral_success" is a real
         documented POSITIVE precedent. A warning is SUPPORTED by a real
         losing trade and CONTRADICTED by a real winning one; a positive
         precedent is SUPPORTED by a real winning trade and CONTRADICTED
         by a real losing one. A real breakeven trade (`pnl == 0`) is
         honestly "inconclusive" — no directional evidence either way.
         Any OTHER memory source (risk_event, model_validation, ...) has
         no honest valence rule defined here — grading such an
         application would require fabricating a claim direction this
         milestone has no real signal for, so it stays "inconclusive"
         with a disclosed reason rather than a guessed verdict. Never a
         second outcome-grading engine — this is the one place any
         KnowledgeEvent is ever graded."""
    decisions_by_id = {d.id: d for d in decisions}
    journal_by_proposal = {j.proposal_id: j for j in paper_trade_journal if j.proposal_id is not None}
    memory_by_id = {m.id: m for m in institutional_memory}
    now = _now_iso()

    graded: list[KnowledgeEvent] = []
    for event in events:
        if event.type != "knowledge_applied" or event.application_status != "pending" or event.context_ref is None:
            graded.append(event)
            continue
        decision = decisions_by_id.get(f"decision-{event.context_ref}")
        if decision is None:
            graded.append(event)  # still PENDING — not yet decided
            continue
        if decision.outcome == "no_trade":
            graded.append(
                event.model_copy(
                    update={
                        "application_status": "evaluated",
                        "outcome": "inconclusive",
                        "outcome_ref": decision.id,
                        "evaluated_at": now,
                    }
                )
            )
            continue
        journal_entry = journal_by_proposal.get(event.context_ref)
        if journal_entry is None:
            graded.append(event)  # a real order was placed; position still open — still PENDING
            continue
        memory = memory_by_id.get(event.lesson_id)
        outcome: Literal["supported", "contradicted", "inconclusive"]
        if memory is None or journal_entry.pnl == 0:
            outcome = "inconclusive"
        elif memory.source == "behavioral_mistake":
            outcome = "supported" if journal_entry.pnl < 0 else "contradicted"
        elif memory.source == "behavioral_success":
            outcome = "supported" if journal_entry.pnl > 0 else "contradicted"
        else:
            outcome = "inconclusive"
        graded.append(
            event.model_copy(
                update={
                    "application_status": "evaluated",
                    "outcome": outcome,
                    "outcome_ref": journal_entry.id,
                    "evaluated_at": now,
                }
            )
        )
    return graded


def lessons_needing_contradiction_flag(events: list[KnowledgeEvent], *, threshold: int = CONTRADICTION_THRESHOLD) -> set[str]:
    """CEO directive "TradeTown — Knowledge Application Loop 1.0" — the
    real, conservative, disclosed rule for when a memory has earned
    InstitutionalMemoryStatus "contradicted" (app/institutional_memory.py's
    apply_contradiction_evidence()): recomputed fresh from the full real
    graded-event history every tick (never a persisted, driftable
    counter, matching this codebase's confidence/relevance discipline) —
    a lesson_id qualifies only when its real graded `knowledge_applied`
    events show at least `threshold` contradictions AND contradictions
    outnumber supports (net-negative evidence, never a single
    disagreeing example, per this directive's own explicit instruction)."""
    supported: dict[str, int] = {}
    contradicted: dict[str, int] = {}
    for event in events:
        if event.type != "knowledge_applied" or event.outcome is None:
            continue
        if event.outcome == "supported":
            supported[event.lesson_id] = supported.get(event.lesson_id, 0) + 1
        elif event.outcome == "contradicted":
            contradicted[event.lesson_id] = contradicted.get(event.lesson_id, 0) + 1
    return {lesson_id for lesson_id, count in contradicted.items() if count >= threshold and count > supported.get(lesson_id, 0)}
