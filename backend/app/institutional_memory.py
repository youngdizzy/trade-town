"""Institutional Memory 2.0 — CEO directive "Features 26-30: Agent
Intelligence, Learning & Institutional Memory System," Feature 26 (the
first stage of that pipeline; see this directive's own explicit staging
rule that 27-30 do not start until this feature is tested and
integrated).

Research finding (recorded here per the directive's "document what was
found before coding" rule): this codebase already had a flat company-
history log (app/scribe.py's MemoryRecord, "an infinite event log") and
a similarity/scoring layer over one specific record type
(app/decision_vault.py's KnowledgeQualityScore, computed fresh per
request over DecisionVaultEntry). Neither is a reusable-lesson store
that promotes evidence from *multiple* record types into one queryable,
contradiction-aware, confidence-scored knowledge base. This module adds
exactly that gap — a promotion layer sitting on top of what already
exists, not a second event log and not a second knowledge graph
(app/knowledge_graph.py's non-causal-edge graph stays exactly as-is;
this module does not touch it).

Every `promote_*` function below reads only fields that already exist on
its real source record (CaseStudy, FailedStrategyArchiveEntry,
StrategyHallOfFameEntry, ModelValidationReport, RiskWarning, a
MarketEnvironmentEntry regime change) — nothing here invents a
statistic, a lesson, or an agent attribution that isn't honestly present
on the source. Where a source record genuinely has no interpretation or
lesson to offer (e.g. a routine risk event), the corresponding field is
left `None` rather than padded out with invented text.

Confidence and relevance are both computed fresh at write time by
`record_institutional_memory()` (confidence: a real corroboration count
against this memory's own existing entries, in the exact
count-normalized-against-a-cap shape app/decision_vault.py's
PATTERN_FREQUENCY_CAP already established) and recomputed fresh again at
read time by `retrieve_relevant_memory()` (relevance: decision_vault.py's
`compute_knowledge_quality_score()` recency-decay formula, verbatim) —
matching that module's own "computed fresh per request, never a second
driftable copy" discipline for time-sensitive scores, rather than
letting a persisted relevance number silently go stale as sim days pass.

Contradiction/update handling never deletes or silently overwrites a
row: `find_related_memory()` only ever returns *candidate* related ids
via the same real significant-word-overlap check
app/constitution.py's `_founder_verdict()` already uses for its own
"does this restate something we already have" judgment — it does not
itself decide whether a match is an update, a contradiction, or mere
corroboration, because no signal in this codebase can honestly make that
semantic call automatically. Making that call explicit is
`supersede_memory()`'s job: it flips the old entry's `status` and links
both rows together, keeping the old row on file permanently rather than
erasing it — "preserve history rather than silently overwriting it," per
the directive.

`retrieve_relevant_memory()` returns `None` — not a weak forced answer —
when nothing on file matches the query at all, or when the single best
match's relevance has decayed below `MIN_RELEVANCE_FOR_RETRIEVAL`. That
threshold, like `CORROBORATION_CAP` below, is a disclosed configurable
research assumption (this module's own choice, not a value already
load-bearing elsewhere in this codebase) rather than presented as an
established statistical fact — the same provenance discipline
app/model_validation.py's own threshold table already uses.

CEO directive "TradeTown — Knowledge Application Loop 1.0" — this
milestone's own Phase 0 forensic audit found `retrieve_relevant_memory()`
fully built, fully tested, and never once called from the live pipeline
(dead code) — the one real consumer that plausibly should have used it,
Devil's Advocate's `historical_comparisons`, instead reimplemented a
cruder raw same-symbol title match directly over `CaseStudy` records.
This milestone makes it the canonical retrieval path for that consumer
(see app/devils_advocate.py), which required one honest, additive
schema change: `InstitutionalMemoryEntry.symbol`, populated only where
the real source record actually has one, so a symbol-scoped query is a
real filter, never a guess. It also adds the one new status transition
this codebase previously had no real signal to justify —
`apply_contradiction_evidence()`, called only after real, repeated,
net-negative graded evidence (see app/knowledge_sharing.py's
`grade_knowledge_applications()`/`lessons_needing_contradiction_flag()`)
— closing the "contradicted is never chosen here" gap this module's own
docstring above used to disclose.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from app.constitution import _significant_words
from app.schemas import (
    CaseStudy,
    FailedStrategyArchiveEntry,
    FailureClassification,
    InstitutionalMemoryEntry,
    InstitutionalMemorySource,
    MarketEnvironmentRegime,
    ModelValidationReport,
    PredictionRecord,
    ResearchLessonRecord,
    RiskWarning,
    StrategyHallOfFameEntry,
    SUCCESS_CASE_STUDY_CATEGORIES,
)

MAX_INSTITUTIONAL_MEMORY = 200

# Mirrors decision_vault.py's PATTERN_FREQUENCY_CAP shape exactly (a raw
# corroboration count, normalized against a cap, never presented as an
# unbounded number) — applied here to institutional memory's own real
# match key (same source, same market_regime when both entries have one)
# rather than the Decision Vault's symbol/regime/confidence-tier profile.
CORROBORATION_CAP = 10

# Word-overlap thresholds for find_related_memory() — the same shape as
# app/constitution.py's REDUNDANCY_WORD_OVERLAP_THRESHOLD/
# MIN_SHARED_WORDS_FOR_REDUNDANCY, re-tuned as its own disclosed
# assumption since institutional-memory observation/lesson text is
# typically longer and more varied than a one-sentence Constitution
# Article.
MIN_SHARED_WORDS_FOR_RELATION = 3
RELATION_WORD_OVERLAP_THRESHOLD = 0.3

# Below this recomputed relevance, retrieve_relevant_memory() reports
# NOT ENOUGH EVIDENCE (returns None) rather than surfacing a badly stale
# best-effort match.
MIN_RELEVANCE_FOR_RETRIEVAL = 10.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def promote_case_study(case_study: CaseStudy) -> InstitutionalMemoryEntry:
    """CaseStudy.department_opinions is a list of several agents' own
    real votes, not one agent's decision — attributing this memory to a
    single originating_agent would misrepresent a multi-agent record, so
    it's honestly left None (matches the CaseStudy schema itself, which
    carries no single decision-maker field either)."""
    is_success = case_study.category in SUCCESS_CASE_STUDY_CATEGORIES
    source: InstitutionalMemorySource = "behavioral_success" if is_success else "behavioral_mistake"
    return InstitutionalMemoryEntry(
        id=f"im-case-{case_study.id}",
        source=source,
        createdAt=_now_iso(),
        simDay=case_study.sim_day,
        originatingAgent=None,
        eventRef=case_study.id,
        marketRegime=None,
        observation=case_study.background,
        interpretation=case_study.decision_process or None,
        lesson=case_study.lessons_learned or None,
        confidence=0.0,
        provenance=f"Promoted from CaseStudy {case_study.id} ({case_study.category}) on trade {case_study.decision_id}, sim day {case_study.sim_day}.",
        relevancePct=0.0,
        supportingEvidence=case_study.department_opinions,
        symbol=case_study.symbol,
    )


def promote_failed_strategy(entry: FailedStrategyArchiveEntry) -> InstitutionalMemoryEntry:
    return InstitutionalMemoryEntry(
        id=f"im-failedstrat-{entry.id}",
        source="strategy_failure",
        createdAt=_now_iso(),
        simDay=entry.sim_day,
        originatingAgent=entry.created_by,
        eventRef=entry.id,
        marketRegime=None,
        observation=entry.retired_reason,
        interpretation="; ".join(entry.what_failed) or None,
        lesson="; ".join(entry.lessons_learned) or None,
        confidence=0.0,
        provenance=f"Promoted from FailedStrategyArchiveEntry {entry.id} ({entry.strategy_name}), failed at stage {entry.failed_at_stage}, sim day {entry.sim_day}.",
        relevancePct=0.0,
        supportingEvidence=entry.what_failed,
    )


def promote_hall_of_fame_strategy(entry: StrategyHallOfFameEntry) -> InstitutionalMemoryEntry:
    observation = (
        f"{entry.strategy_name} was inducted into the Strategy Hall of Fame after "
        f"{entry.trades_executed} trades over {entry.sim_days_active} sim days: "
        f"{entry.win_rate:.1f}% win rate, {entry.profit_factor:.2f} profit factor, "
        f"{entry.max_drawdown_pct:.2f}% max drawdown."
    )
    return InstitutionalMemoryEntry(
        id=f"im-halloffame-{entry.id}",
        source="strategy_success",
        createdAt=_now_iso(),
        simDay=entry.sim_day,
        originatingAgent=entry.created_by,
        eventRef=entry.id,
        marketRegime=None,
        observation=observation,
        interpretation=entry.description or None,
        lesson="; ".join(entry.legacy_notes) or None,
        confidence=0.0,
        provenance=f"Promoted from StrategyHallOfFameEntry {entry.id} ({entry.strategy_name}), inducted sim day {entry.sim_day}.",
        relevancePct=0.0,
        supportingEvidence=entry.legacy_notes,
    )


def promote_model_validation(report: ModelValidationReport) -> InstitutionalMemoryEntry:
    """Only a non-"approved" verdict is promoted (see
    should_promote_model_validation()) — a routine approval isn't a
    lesson, it's the expected outcome of Meridian's process working
    normally. See app/model_validation.py's module docstring for why
    ModelValidationReport.verdict is advisory-only; that boundary is
    unaffected here — this only files the finding as institutional
    knowledge, it never feeds back into any gate."""
    lesson = None
    if report.verdict in ("rejected", "not_validatable"):
        lesson = f"Do not treat {report.strategy_name}'s prior validation evidence as sufficient without addressing: {report.evidence_summary}"
    elif report.verdict == "needs_more_evidence":
        lesson = f"{report.strategy_name} needs more evidence before Meridian can render a verdict — do not treat its current evidence as proven."
    return InstitutionalMemoryEntry(
        id=f"im-modelval-{report.id}",
        source="model_validation",
        createdAt=_now_iso(),
        simDay=report.sim_day,
        originatingAgent=report.validator_agent_id,
        eventRef=report.id,
        marketRegime=None,
        observation=report.evidence_summary,
        interpretation="; ".join(report.data_sources_and_assumptions) or None,
        lesson=lesson,
        confidence=0.0,
        provenance=f"Promoted from ModelValidationReport {report.id} ({report.strategy_name}), verdict={report.verdict}, sim day {report.sim_day}.",
        relevancePct=0.0,
        supportingEvidence=[c.evidence for c in report.checks if c.evidence],
    )


def should_promote_model_validation(report: ModelValidationReport) -> bool:
    return report.verdict != "approved"


def promote_risk_event(warning: RiskWarning, *, sim_day: int) -> InstitutionalMemoryEntry:
    """RiskWarning carries no agent-attribution field of its own (see
    app/risk_engine.py) and no sim_day (see app/schemas.py's RiskWarning
    docstring context) — sim_day is supplied by the caller from the same
    tick's real TimeState, matching app/prop_firm.py's own established
    pattern for functions whose source data lacks a day field."""
    return InstitutionalMemoryEntry(
        id=f"im-riskevent-{warning.id}",
        source="risk_event",
        createdAt=_now_iso(),
        simDay=sim_day,
        originatingAgent=None,
        eventRef=warning.id,
        marketRegime=None,
        observation=f"[{warning.severity}] {warning.symbol}: {warning.message}",
        interpretation=None,
        lesson=f"Treat future {warning.symbol} setups with the same conditions as elevated risk until conditions change." if warning.severity == "critical" else None,
        confidence=0.0,
        provenance=f"Promoted from RiskWarning {warning.id} ({warning.symbol}, {warning.severity}), sim day {sim_day}.",
        relevancePct=0.0,
        supportingEvidence=[],
        symbol=warning.symbol,
    )


def promote_market_regime_shift(
    *, regime: MarketEnvironmentRegime, label: str, detail: str, event_ref: str, sim_day: int
) -> InstitutionalMemoryEntry:
    return InstitutionalMemoryEntry(
        id=f"im-regime-{event_ref}",
        source="market_regime_shift",
        createdAt=_now_iso(),
        simDay=sim_day,
        originatingAgent=None,
        eventRef=event_ref,
        marketRegime=regime,
        observation=f"Market conditions shifted to {label}. {detail}",
        interpretation=None,
        lesson=f"Setups validated under a different regime should not be assumed reliable under {label} without additional confirmation.",
        confidence=0.0,
        provenance=f"Promoted from a real MarketEnvironmentEntry regime change ({event_ref}), sim day {sim_day}.",
        relevancePct=0.0,
        supportingEvidence=[],
    )


def promote_prediction_outcome(record: PredictionRecord) -> InstitutionalMemoryEntry:
    """CEO directive Feature 29 — only called when
    app/prediction_tracking.py's should_promote_prediction_outcome()
    says this is a real, notable miscalibration (high stated confidence,
    resolved wrong), not every resolved prediction. `originating_agent`
    is only ever a single real agent id, matching every other multi-
    agent-source promote_* function's own honesty rule above — this
    record's real supporting agents may be more than one, so a single
    attribution would misrepresent it unless exactly one agent backed
    it."""
    return InstitutionalMemoryEntry(
        id=f"im-prediction-{record.id}",
        source="prediction",
        createdAt=_now_iso(),
        simDay=record.sim_day,
        originatingAgent=record.attributed_agents[0] if len(record.attributed_agents) == 1 else None,
        eventRef=record.id,
        marketRegime=None,
        observation=(
            f"A {record.confidence_pct:.0f}% confidence {record.predicted_direction.upper()} prediction on "
            f"{record.symbol} resolved incorrect (real P&L {record.resolved_pnl_pct:+.2f}%)."
        ),
        interpretation="High stated confidence did not track the real outcome — a real calibration gap, not necessarily a process failure.",
        lesson=f"Treat future high-confidence {record.symbol} calls with extra scrutiny until calibration on this symbol improves.",
        confidence=0.0,
        provenance=f"Promoted from PredictionRecord {record.id} (trade_direction, {record.predicted_direction}), resolved sim day {record.sim_day}.",
        relevancePct=0.0,
        supportingEvidence=list(record.attributed_agents),
        symbol=record.symbol,
    )


def promote_failure_classification(classification: FailureClassification) -> InstitutionalMemoryEntry:
    """CEO directive Feature 30 — only ever called when
    app/failure_review.py's should_promote_failure_classification() says
    this classification has a real, named reason (never "unknown", which
    has no real lesson to file). `originating_agent` follows the same
    single-attribution honesty rule as promote_prediction_outcome() above
    — a failure classification's `attributed_agents` is the trade's real
    supporting agents, which is usually more than one."""
    return InstitutionalMemoryEntry(
        id=f"im-failure-{classification.id}",
        source="failure_classification",
        createdAt=_now_iso(),
        simDay=classification.sim_day,
        originatingAgent=classification.attributed_agents[0] if len(classification.attributed_agents) == 1 else None,
        eventRef=classification.id,
        marketRegime=None,
        observation=(
            f"{classification.symbol} closed at {classification.trade_pnl_pct:+.2f}% and was classified "
            f"{classification.reason.replace('_', ' ')}: {classification.evidence}"
        ),
        interpretation=None,
        lesson=f"Watch for {classification.reason.replace('_', ' ')} on future {classification.symbol} decisions before this trade's own real evidence.",
        confidence=0.0,
        provenance=f"Promoted from FailureClassification {classification.id} ({classification.reason}) on trade {classification.trade_id}, sim day {classification.sim_day}.",
        relevancePct=0.0,
        supportingEvidence=list(classification.attributed_agents),
        symbol=classification.symbol,
    )


# "TradeTown — Learning Organization 1.0" — RESEARCH_CANDIDATE_MIN_TRADE_
# COUNT (app/research_loop.py) is this codebase's own existing definition
# of "enough real trades to trust this," and ResearchLessonRecord's own
# confidence_pct is already trade_count normalized against that exact
# threshold — so gating promotion on confidence_pct reaching 100 reuses
# a real, already-established bar rather than inventing a new one. A
# lesson explicitly binned "insufficient_evidence" is excluded even if
# confidence_pct happens to read high, since that binning is itself a
# real signal the evidence wasn't trustworthy for another reason.
def should_promote_research_lesson(record: ResearchLessonRecord) -> bool:
    return record.confidence_pct >= 100.0 and record.candidacy != "insufficient_evidence"


def promote_research_lesson(record: ResearchLessonRecord, *, sim_day: int) -> InstitutionalMemoryEntry:
    """Bridges app/research_loop.py's ResearchLessonRecord — a complete,
    real, but previously fully disconnected parallel lesson store — into
    the one canonical institutional-memory hub. `sim_day` is passed by
    the caller (ResearchLessonRecord itself carries no sim_day field,
    only `created_at`) the same way promote_market_regime_shift() and
    promote_risk_event() already take it as an explicit parameter rather
    than assuming one is on the source record."""
    return InstitutionalMemoryEntry(
        id=f"im-researchlesson-{record.id}",
        source="research_lesson",
        createdAt=record.created_at,
        simDay=sim_day,
        originatingAgent=None,
        eventRef=record.id,
        marketRegime=None,
        observation=f'"{record.strategy_family}" (v{record.definition_version}) — {record.candidacy.replace("_", " ")}: {record.reason}',
        interpretation=None,
        lesson=record.lesson,
        confidence=0.0,
        provenance=(
            f"Promoted from ResearchLessonRecord {record.id} (iteration {record.iteration_id}), "
            f"{record.confidence_pct:.0f}% evidence confidence."
        ),
        relevancePct=0.0,
        supportingEvidence=list(record.key_metrics),
    )


def _compute_confidence(entry: InstitutionalMemoryEntry, all_entries: list[InstitutionalMemoryEntry]) -> float:
    matches = 0
    for other in all_entries:
        if other.id == entry.id or other.status != "active":
            continue
        if other.source != entry.source:
            continue
        if entry.market_regime is not None and other.market_regime != entry.market_regime:
            continue
        matches += 1
    return round(min(matches, CORROBORATION_CAP) / CORROBORATION_CAP * 100, 1)


def _compute_relevance_pct(entry: InstitutionalMemoryEntry, all_entries: list[InstitutionalMemoryEntry], current_sim_day: int) -> float:
    oldest_sim_day = min((e.sim_day for e in all_entries), default=entry.sim_day)
    span = max(current_sim_day - oldest_sim_day, 1)
    age = max(current_sim_day - entry.sim_day, 0)
    return round(max(0.0, min(1.0, 1 - age / span)) * 100, 1)


def record_institutional_memory(
    existing: list[InstitutionalMemoryEntry],
    entry: InstitutionalMemoryEntry,
    *,
    current_sim_day: int,
    max_entries: int = MAX_INSTITUTIONAL_MEMORY,
) -> list[InstitutionalMemoryEntry]:
    """The one real writer gateway (matches app/memory.py's record() and
    app/decision_vault.py's own append-and-cap convention) — stamps
    confidence and relevance fresh against the list as it stands right
    now, appends, then caps at max_entries the same way every other
    capped list in this codebase is capped."""
    confidence = _compute_confidence(entry, existing)
    relevance_pct = _compute_relevance_pct(entry, existing, current_sim_day)
    stamped = entry.model_copy(update={"confidence": confidence, "relevance_pct": relevance_pct})
    updated = [*existing, stamped]
    if len(updated) > max_entries:
        del updated[: len(updated) - max_entries]
    return updated


def find_related_memory(entry: InstitutionalMemoryEntry, existing: list[InstitutionalMemoryEntry]) -> list[str]:
    """Returns candidate related/possibly-contradicting entry ids only —
    see this module's own docstring for why deciding what the
    relationship actually is stays a separate, explicit step
    (supersede_memory()) rather than an automatic judgment call."""
    new_words = _significant_words(f"{entry.observation} {entry.lesson or ''}")
    related: list[str] = []
    for other in existing:
        if other.id == entry.id or other.status != "active" or other.source != entry.source:
            continue
        other_words = _significant_words(f"{other.observation} {other.lesson or ''}")
        if not other_words:
            continue
        shared = new_words & other_words
        if len(shared) < MIN_SHARED_WORDS_FOR_RELATION:
            continue
        overlap = len(shared) / len(other_words)
        if overlap >= RELATION_WORD_OVERLAP_THRESHOLD:
            related.append(other.id)
    return related


def supersede_memory(
    existing: list[InstitutionalMemoryEntry],
    *,
    old_id: str,
    new_entry: InstitutionalMemoryEntry,
    relationship: Literal["superseded", "contradicted"],
    current_sim_day: int,
    max_entries: int = MAX_INSTITUTIONAL_MEMORY,
) -> list[InstitutionalMemoryEntry]:
    """Never deletes or overwrites the old entry — flips its status and
    links both rows together, then records the new entry as the current
    active read. If `old_id` isn't found (already resolved by a
    concurrent call, or a bad id), returns `existing` unchanged rather
    than silently fabricating a link."""
    if not any(e.id == old_id and e.status == "active" for e in existing):
        return existing
    relinked = [
        e.model_copy(update={"status": relationship, "superseded_by_id": new_entry.id}) if e.id == old_id else e
        for e in existing
    ]
    stamped_new = new_entry.model_copy(update={"supersedes_id": old_id})
    return record_institutional_memory(relinked, stamped_new, current_sim_day=current_sim_day, max_entries=max_entries)


def record_and_link_institutional_memory(
    existing: list[InstitutionalMemoryEntry],
    entry: InstitutionalMemoryEntry,
    *,
    current_sim_day: int,
    max_entries: int = MAX_INSTITUTIONAL_MEMORY,
) -> tuple[list[InstitutionalMemoryEntry], str | None]:
    """"TradeTown — Learning Organization 1.0" — the real gateway every
    nexus.py/state.py write site now calls instead of a raw
    record_institutional_memory(): find_related_memory() and
    supersede_memory() were both fully built (see their own docstrings
    above) but, per this milestone's own Phase 0 forensic audit, never
    once called from the live pipeline — every promotion was a flat,
    unlinked append, so a recurring pattern silently became dozens of
    duplicate-looking rows instead of one linked, corroborated thread.

    This function closes exactly that gap and nothing else: when a
    genuinely related *active* entry already exists (same source, real
    word-overlap — find_related_memory()'s own bar), the new entry is
    linked to it via supersede_memory(relationship="superseded") — "an
    intentional update, not a contradiction" per InstitutionalMemory-
    Status's own docstring, i.e. real corroboration of a standing
    lesson. This module has no real signal that can honestly tell
    agreement from disagreement between two related entries' text, so
    relationship="contradicted" is never chosen here — that stays a
    disclosed gap for a future milestone with real valence evidence to
    back it, not something this function guesses at.

    Returns the updated list plus the id of the entry that was linked
    (or None for a plain, unrelated append) — callers use that to decide
    between a lesson_created and a lesson_confirmed KnowledgeEvent (see
    app/knowledge_sharing.py)."""
    related = find_related_memory(entry, existing)
    if related:
        updated = supersede_memory(
            existing,
            old_id=related[0],
            new_entry=entry,
            relationship="superseded",
            current_sim_day=current_sim_day,
            max_entries=max_entries,
        )
        return updated, related[0]
    return record_institutional_memory(existing, entry, current_sim_day=current_sim_day, max_entries=max_entries), None


def retrieve_relevant_memory(
    memory: list[InstitutionalMemoryEntry],
    *,
    current_sim_day: int,
    source: InstitutionalMemorySource | None = None,
    market_regime: MarketEnvironmentRegime | None = None,
    symbol: str | None = None,
) -> InstitutionalMemoryEntry | None:
    """Returns the single most relevant+corroborated active entry
    matching the query, with confidence/relevance recomputed fresh
    against the full current memory list (never trusting whatever was
    stamped at write time, which grows stale as sim days pass). Returns
    None — NOT ENOUGH EVIDENCE — when nothing matches the query at all,
    or when the best match's freshly recomputed relevance has decayed
    below MIN_RELEVANCE_FOR_RETRIEVAL. Never forces an answer from weak
    or absent evidence.

    CEO directive "TradeTown — Knowledge Application Loop 1.0" — `symbol`
    is a new, optional, additive filter (this is the canonical retrieval
    function's ONLY consumer-facing change for that milestone): when
    given, only entries whose own real `symbol` field matches are
    considered. An entry with `symbol=None` (a source that genuinely
    isn't symbol-specific, e.g. a strategy-family or market-wide record)
    is correctly excluded from a symbol-scoped query — it was never
    honestly about that symbol in the first place. Every prior caller
    (there were none — this function was previously dead code, per that
    directive's own Phase 0 audit) is unaffected, since omitting `symbol`
    reproduces the exact old behavior."""
    candidates = [e for e in memory if e.status == "active"]
    if source is not None:
        candidates = [e for e in candidates if e.source == source]
    if market_regime is not None:
        candidates = [e for e in candidates if e.market_regime == market_regime]
    if symbol is not None:
        candidates = [e for e in candidates if e.symbol == symbol]
    if not candidates:
        return None

    scored: list[tuple[float, float, float, InstitutionalMemoryEntry]] = []
    for entry in candidates:
        relevance_pct = _compute_relevance_pct(entry, memory, current_sim_day)
        confidence = _compute_confidence(entry, memory)
        scored.append((relevance_pct + confidence, relevance_pct, confidence, entry))
    scored.sort(key=lambda t: t[0], reverse=True)
    _combined, relevance_pct, confidence, best = scored[0]
    if relevance_pct < MIN_RELEVANCE_FOR_RETRIEVAL:
        return None
    return best.model_copy(update={"relevance_pct": relevance_pct, "confidence": confidence})


def apply_contradiction_evidence(memory: list[InstitutionalMemoryEntry], *, memory_id: str) -> list[InstitutionalMemoryEntry]:
    """CEO directive "TradeTown — Knowledge Application Loop 1.0" — the
    one new status transition this milestone finally has a real signal
    to justify: `app/knowledge_sharing.py`'s
    `lessons_needing_contradiction_flag()` only ever names a memory id
    here after real, graded `knowledge_applied` outcomes show repeated,
    net-negative evidence against it (never a single disagreeing
    example — see that function's own docstring for the exact
    conservative threshold). Flips ONLY that one entry's `status` to
    "contradicted" — never deletes it, never rewrites its `observation`/
    `lesson` text, and is NOT `supersede_memory()`: a contradiction is
    evidence about the SAME claim, not a replacement by a new, better
    one, so no new row is created. A no-op if `memory_id` doesn't exist
    or is no longer `active` (already superseded/contradicted/stale —
    never re-flagged). Once contradicted, `retrieve_relevant_memory()`'s
    own `status == "active"` filter naturally stops surfacing it as
    current truth, per this directive's own Part XV."""
    return [e.model_copy(update={"status": "contradicted"}) if e.id == memory_id and e.status == "active" else e for e in memory]
