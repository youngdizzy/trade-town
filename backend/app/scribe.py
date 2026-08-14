"""ScribeManager — turns what other managers produce into CompanyMemory
records and meeting minutes.

Scribe (the agent) doesn't run any simulation logic of its own beyond its
schedule (see app/schedule.py) — it's the "everyone else's output becomes
the historical record" glue, called from app/nexus.py's tick.

Every wrapper function here accepts an optional `max_records` (Design
Bible Chapter 61's Knowledge Retention Rules CEO control,
RiskLimits.maxMemoryRecords) and passes it straight through to
app/memory.py's record() — the one real writer gateway — defaulting to
MAX_MEMORY_RECORDS so a caller that omits it keeps today's exact
behavior.
"""
from __future__ import annotations

from app.academy import is_mentor_level
from app.agents import AGENT_PROFILES
from app.executive import MAX_PROPOSAL_HOLDS
from app.knowledge import derive_lesson
from app.memory import MAX_MEMORY_RECORDS, record
from app.schemas import (
    AcademyProject,
    AgentId,
    AgentKnowledgeState,
    CaseStudy,
    CoachReport,
    DisciplineReview,
    DiscussionMessage,
    ExecutiveReview,
    FailedStrategyArchiveEntry,
    HallOfFameEntry,
    HoldReason,
    LearningEvent,
    MemoryRecord,
    MeetingMinutes,
    PaperOrder,
    PaperTrade,
    ReasoningChallenge,
    ReflectionSession,
    ResearchItem,
    RuleEvaluationResult,
    ScannerAlert,
    SimulationResult,
    StrategyHallOfFameEntry,
    TimeState,
    TradeDecision,
    TradeProposal,
)

# Crossing this confidence on completion also logs a "future trade"
# candidate note — a flag for a human to consider later, not a trade.
# TradeTown v0.3 does not execute trades (see app/market_data.py).
FUTURE_TRADE_CONFIDENCE_THRESHOLD = 85.0


def record_research_completions(memory: list[MemoryRecord], completed: list[ResearchItem], max_records: int = MAX_MEMORY_RECORDS) -> None:
    for item in completed:
        record(memory, "research", item.title, item.summary, max_records=max_records)
        record(memory, "discovery", f"Discovery: {item.symbol or item.title}", item.summary, max_records=max_records)
        if item.confidence >= FUTURE_TRADE_CONFIDENCE_THRESHOLD:
            record(
                memory,
                "future_trade",
                f"Candidate flagged: {item.symbol}",
                f"{AGENT_PROFILES[item.assigned_agent].name} finished research on {item.symbol} with "
                f"{item.confidence:.0f}% confidence — flagged as a candidate for future trade consideration. "
                "No trade was placed; TradeTown does not execute trades.",
                max_records=max_records,
            )


def build_minutes(participants: list[AgentId], discussion: list[DiscussionMessage], research: list[ResearchItem], new_time: TimeState) -> MeetingMinutes:
    # Only each participant's *current* research focus, matching what
    # discussion.py actually generated lines about — research also holds
    # each agent's completed history (see research.py), and including
    # that here would claim the meeting covered everything an attendee
    # has ever researched instead of what was actually discussed.
    topics = sorted({item.symbol for item in research if item.status == "in_progress" and item.assigned_agent in participants and item.symbol})
    names = ", ".join(AGENT_PROFILES[a].name for a in participants)
    summary = f"{len(participants)} attended: {names}. Discussed {', '.join(topics)}." if topics else f"{len(participants)} attended: {names}."
    return MeetingMinutes(
        id=f"minutes-{new_time.day}-{new_time.hour}-{new_time.minute}",
        day=new_time.day,
        hour=new_time.hour,
        minute=new_time.minute,
        participants=participants,
        summary=summary,
        discussion=discussion,
    )


def record_meeting(memory: list[MemoryRecord], minutes: MeetingMinutes, max_records: int = MAX_MEMORY_RECORDS) -> None:
    when = f"Day {minutes.day} {minutes.hour:02d}:{minutes.minute:02d}"
    record(memory, "meeting", f"Meeting — {when}", minutes.summary, max_records=max_records)
    if minutes.discussion:
        transcript = " / ".join(f"{AGENT_PROFILES[m.speaker].name}: {m.line}" for m in minutes.discussion)
        record(memory, "discussion", f"Discussion — {when}", transcript, max_records=max_records)


def record_paper_trade(memory: list[MemoryRecord], trade: PaperTrade, max_records: int = MAX_MEMORY_RECORDS) -> None:
    """Logs a closed paper trade's outcome, then hands it to
    app/knowledge.py to derive a lesson/mistake record from the same
    trade — see the v0.5 brief's Feature 5 (Learning System) and Feature
    9 (searchable knowledge)."""
    outcome = "gained" if trade.pnl > 0 else "lost"
    record(
        memory,
        "paper_trade",
        f"Paper trade closed: {trade.symbol}",
        f"{trade.symbol} {outcome} {abs(trade.pnl_pct):.1f}% ({trade.pnl:+.2f} simulated) over a "
        f"{trade.duration_minutes}-minute hold. {trade.reason}. No real capital was involved.",
        max_records=max_records,
    )
    category, title, body = derive_lesson(trade)
    record(memory, category, title, body, max_records=max_records)


def record_simulation_result(memory: list[MemoryRecord], result: SimulationResult, max_records: int = MAX_MEMORY_RECORDS) -> None:
    record(
        memory,
        "simulation",
        f"Simulation complete: {result.strategy_name}",
        f"{AGENT_PROFILES[result.run_by].name} ran \"{result.strategy_name}\" on {result.symbol}: "
        f"{result.total_return_pct:+.1f}% return, {result.win_rate:.0f}% win rate, "
        f"{result.max_drawdown_pct:.1f}% max drawdown across {result.trade_count} simulated trades. "
        "Historical placeholder data — no real backtest data source is connected yet.",
        max_records=max_records,
    )


def record_coach_report(memory: list[MemoryRecord], report: CoachReport, max_records: int = MAX_MEMORY_RECORDS) -> None:
    top = f"{AGENT_PROFILES[report.agent_rankings[0].agent_id].name}" if report.agent_rankings else "no ranked agent yet"
    record(
        memory,
        "coach_review",
        f"Coach's {report.period} report",
        f"Company score {report.company_score:.1f}/100. Win rate {report.win_rate:.0f}%, research accuracy "
        f"{report.research_accuracy:.0f}%, risk score {report.risk_score:.0f}/100. Top agent this period: {top}. "
        f"{' '.join(report.recommendations)}",
        max_records=max_records,
    )


def record_hall_of_fame_entry(memory: list[MemoryRecord], entry: HallOfFameEntry, max_records: int = MAX_MEMORY_RECORDS) -> None:
    record(memory, "event", f"Hall of Fame: {entry.title}", entry.description, max_records=max_records)


def record_scanner_alert(memory: list[MemoryRecord], alert: ScannerAlert, max_records: int = MAX_MEMORY_RECORDS) -> None:
    record(memory, "alert", f"Scanner alert: {alert.symbol}", alert.message, max_records=max_records)


def record_ceo_decision(memory: list[MemoryRecord], decision: TradeDecision, max_records: int = MAX_MEMORY_RECORDS) -> None:
    """Feature 12 — every CEO Approval outcome (a player's real buy/sell/
    wait call, or an unactioned proposal auto-resolved as wait on
    expiry — see app/executive.py's resolve_proposal()) is logged here.
    decision.final_reasoning already states who decided and why, so it's
    used verbatim rather than re-deriving an attribution string."""
    record(memory, "decision", f"CEO decision: {decision.symbol}", decision.final_reasoning, max_records=max_records)


def record_emergency_stop_event(memory: list[MemoryRecord], *, activated: bool, max_records: int = MAX_MEMORY_RECORDS) -> None:
    """Design Bible Chapter 67 (TTOS) Part 3 — this record IS the
    Emergency Stop's "incident report": the brief asks for one, and
    rather than inventing a second, parallel incident-log object, the
    permanent, already-searchable Company Memory record is it (see
    app/emergency_stop.py's module docstring)."""
    if activated:
        record(memory, "emergency", "Emergency Stop activated", "The CEO halted all new trading. Research, monitoring, and dashboards continue; only the CEO can resume trading.", max_records=max_records)
    else:
        record(memory, "emergency", "Trading resumed", "The CEO resumed trading after an Emergency Stop.", max_records=max_records)


def record_proposal_hold(memory: list[MemoryRecord], proposal: TradeProposal, reason: HoldReason, max_records: int = MAX_MEMORY_RECORDS) -> None:
    """v0.7 Feature 40.5 — Request More Research / Delay Decision. Not a
    final call (see app/executive.py's hold_proposal()), but still a
    real CEO action worth a permanent record of when and why the desk
    was asked to wait."""
    label = "requested more research on" if reason == "more_research" else "delayed the decision on"
    record(
        memory,
        "decision",
        f"CEO held: {proposal.symbol}",
        f"CEO {label} {proposal.symbol} (hold {proposal.hold_count}/{MAX_PROPOSAL_HOLDS}).",
        max_records=max_records,
    )


def record_proposal_modify(memory: list[MemoryRecord], proposal: TradeProposal, old_quantity: float, max_records: int = MAX_MEMORY_RECORDS) -> None:
    """Design Bible Chapter 70 Part 2 — "Modify" as a real CEO decision
    action. Not a final call (the proposal stays pending — see
    app/executive.py's modify_proposal()), but still a real, permanent
    record of when and how the CEO resized a pending proposal."""
    record(
        memory,
        "decision",
        f"CEO resized: {proposal.symbol}",
        f"CEO reduced the pending {proposal.symbol} proposal from {old_quantity:.2f} to {proposal.quantity:.2f} shares.",
        max_records=max_records,
    )


def record_order_placed(memory: list[MemoryRecord], order: PaperOrder, max_records: int = MAX_MEMORY_RECORDS) -> None:
    record(
        memory,
        "order",
        f"Order placed: {order.symbol}",
        f"{AGENT_PROFILES[order.placed_by].name} placed a {order.order_type} {order.side} order for "
        f"{order.quantity:.2f} {order.symbol} — {order.reason}",
        max_records=max_records,
    )


def record_academy_project(memory: list[MemoryRecord], project: AcademyProject, max_records: int = MAX_MEMORY_RECORDS) -> None:
    """v0.7 Feature 25 — a completed AI Academy knowledge project. This is
    also the Company Knowledge Library's real entry point (see
    app/academy_research.py's module docstring)."""
    record(memory, "academy", f"Academy: {project.title}", project.summary, max_records=max_records)


def record_knowledge_tier_up(memory: list[MemoryRecord], event: LearningEvent, max_records: int = MAX_MEMORY_RECORDS) -> None:
    record(
        memory,
        "academy",
        f"{AGENT_PROFILES[event.agent_id].name} advances in {event.skill_domain}",
        f"{AGENT_PROFILES[event.agent_id].name} has reached {event.new_level.title()} level (Tier {event.new_competency}) in {event.skill_domain}, "
        f"with {event.total_points:.1f} knowledge points earned through real completed work.",
        max_records=max_records,
    )


def record_mentorship_session(
    memory: list[MemoryRecord],
    knowledge: dict[AgentId, AgentKnowledgeState],
    mentor_id: AgentId,
    mentee_id: AgentId,
    max_records: int = MAX_MEMORY_RECORDS,
) -> None:
    """v0.7 Feature 25/31 — see app/academy.py's module docstring for why
    "seniority" here is grounded in real knowledge points rather than a
    fabricated status; both agents' own real point totals are logged
    verbatim, not a generic "mentoring happened" line. Phrased as real
    teaching, not generic mentoring, only once the mentor has actually
    reached the top "mentor" Knowledge Level (see
    app/academy.py's is_mentor_level()) — the real gate the brief's
    Teaching System asks for."""
    mentor = knowledge[mentor_id]
    mentee = knowledge[mentee_id]
    verb = "teaches" if is_mentor_level(mentor) else "mentors"
    activity = "hosted a real teaching session for" if is_mentor_level(mentor) else "spent time coaching"
    record(
        memory,
        "mentorship",
        f"{AGENT_PROFILES[mentor_id].name} {verb} {AGENT_PROFILES[mentee_id].name}",
        f"{AGENT_PROFILES[mentor_id].name} ({mentor.branch}, {mentor.level.title()}, {mentor.points:.1f} pts) {activity} "
        f"{AGENT_PROFILES[mentee_id].name} ({mentee.branch}, {mentee.level.title()}, {mentee.points:.1f} pts) this afternoon.",
        max_records=max_records,
    )


def record_executive_review(memory: list[MemoryRecord], review: ExecutiveReview, max_records: int = MAX_MEMORY_RECORDS) -> None:
    record(memory, "executive", "Meridian's Executive Review", review.summary, max_records=max_records)


def record_discipline_review(memory: list[MemoryRecord], review: DisciplineReview, max_records: int = MAX_MEMORY_RECORDS) -> None:
    record(memory, "discipline", f"Discipline Review: {review.symbol}", review.summary, max_records=max_records)


def record_case_study(memory: list[MemoryRecord], case_study: CaseStudy, max_records: int = MAX_MEMORY_RECORDS) -> None:
    record(memory, "case_study", case_study.title, f"{case_study.symbol}: {case_study.missed_information}", max_records=max_records)


def record_reasoning_challenge(memory: list[MemoryRecord], challenge: ReasoningChallenge, max_records: int = MAX_MEMORY_RECORDS) -> None:
    record(
        memory,
        "reasoning_challenge",
        f"Reasoning Lab: {challenge.title}",
        f"{challenge.symbol}: {challenge.solution.why_reasonable}",
        max_records=max_records,
    )


def record_reflection_session(memory: list[MemoryRecord], session: ReflectionSession, max_records: int = MAX_MEMORY_RECORDS) -> None:
    record(
        memory,
        "reflection",
        f"{session.cadence.title()} Reflection Session",
        f"Company Wisdom stands at {session.wisdom_score:.0f}/100. {session.questions[0].answer if session.questions else ''}",
        max_records=max_records,
    )


# Design Bible Chapter 62 — the Innovation Lab's Knowledge Integration
# section. `strategy` has been a real MemoryCategory (and already
# included in app/knowledge.py's KNOWLEDGE_CATEGORIES for the Company
# Knowledge Library) since it was first declared, but nothing ever
# actually recorded one — closing that real, pre-existing gap.
def record_strategy_hall_of_fame_entry(memory: list[MemoryRecord], entry: StrategyHallOfFameEntry, max_records: int = MAX_MEMORY_RECORDS) -> None:
    record(
        memory,
        "strategy",
        f"Strategy Hall of Fame: {entry.strategy_name}",
        f"{AGENT_PROFILES[entry.created_by].name}'s \"{entry.strategy_name}\" earned induction into the Strategy Hall "
        f"of Fame after {entry.trades_executed} trades over {entry.sim_days_active} sim days. {entry.description}",
        max_records=max_records,
    )


def record_strategy_failed_archive_entry(memory: list[MemoryRecord], entry: FailedStrategyArchiveEntry, max_records: int = MAX_MEMORY_RECORDS) -> None:
    what_failed = "; ".join(entry.what_failed) if entry.what_failed else "no specific failure reason recorded"
    record(
        memory,
        "strategy",
        f"Strategy retired: {entry.strategy_name}",
        f"{AGENT_PROFILES[entry.created_by].name}'s \"{entry.strategy_name}\" was retired at the {entry.failed_at_stage.replace('_', ' ')} "
        f"stage ({entry.retired_reason}). What failed: {what_failed}.",
        max_records=max_records,
    )


def record_rule_violation(memory: list[MemoryRecord], account_name: str, result: RuleEvaluationResult, max_records: int = MAX_MEMORY_RECORDS) -> None:
    """Design Bible Chapter 69 Part 3 — Institutional Rule Engine. One
    real, permanent Company Memory record per real rule violation on an
    account, the same "record every real risk event" convention
    app/scribe.py already follows for every other risk signal in this
    codebase — never a fabricated audit trail."""
    failed = [c for c in result.checks if not c.passed]
    if not failed:
        return
    summary = "; ".join(f"{c.label} ({c.detail})" for c in failed)
    record(
        memory,
        "alert",
        f"Rule violation on {account_name}",
        f"{len(failed)} custom rule(s) failed: {summary}",
        max_records=max_records,
    )
