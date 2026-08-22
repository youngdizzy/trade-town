"""CEO directive "Complete Trade Provenance," Part 18 — Data Quality
Monitor.

RESEARCH FIRST (per the directive's own mandatory rule): a full audit
confirmed no generic "data quality issue" or "audit trail" primitive
exists anywhere in this codebase — app/audit_log.py merges a fixed list
of eight source types and app/data_provenance.py is a one-shot,
whole-codebase report, neither a pluggable per-record diagnostic. This
module is new, narrowly scoped plumbing for exactly the four categories
below, not a general event-bus (which nothing in this codebase's own
architecture calls for building).

WHY ONLY FOUR OF PART 18'S NAMED CATEGORIES: each of the four below has
a genuine, already-real, non-fabricated signal this codebase can check.
The other three Part 18 names — missing decision evidence, missing
execution evidence, missing exit evidence — are already separately
surfaced by `TradeAttributionRecord.evidenceState`
(app/trade_attribution.py) and `TradeExitEfficiency.evidenceState`
(app/exit_efficiency.py); re-detecting the identical real condition a
second time here would be duplicated architecture, not new coverage,
so this module reports only what it doesn't already have a home.

This module only ever REPORTS — it never repairs, backfills, or
silently corrects anything it finds, per the directive's own explicit
rule ("treated as DATA QUALITY, not silently repaired")."""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    CeoDecisionRecord,
    DataQualityIssue,
    DataQualityIssueCategory,
    DataQualityMonitor,
    PaperTrade,
    Strategy,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# A real record id sample, not an unbounded dump — enough to
# investigate a real issue without the response growing without bound
# on a save with many affected records.
MAX_EXAMPLE_IDS = 5


def _issue(category: DataQualityIssueCategory, ids: list[str], detail: str) -> DataQualityIssue | None:
    if not ids:
        return None
    return DataQualityIssue(category=category, count=len(ids), detail=detail, exampleIds=ids[:MAX_EXAMPLE_IDS])


def compute_data_quality_monitor(
    trade_history: list[PaperTrade],
    ceo_decisions: list[CeoDecisionRecord],
    strategies: list[Strategy],
) -> DataQualityMonitor:
    """Four real, checkable categories — see this module's own
    docstring for exactly why these four and not Part 18's full list."""
    real_strategy_ids = {s.id for s in strategies}

    impossible_timestamp_ids = [t.id for t in trade_history if t.closed_sim_minutes < t.opened_sim_minutes]

    dangling_reference_ids = [
        d.id for d in ceo_decisions if d.strategy_id is not None and d.strategy_id not in real_strategy_ids
    ]

    missing_context_ids = [
        d.id
        for d in ceo_decisions
        if d.ceo_decision in ("buy", "sell") and d.decision_session is None
    ]

    missing_snapshot_ids = [
        d.id
        for d in ceo_decisions
        if d.strategy_id is not None and d.strategy_compiled_definition_id is None
    ]

    issues = [
        i
        for i in (
            _issue(
                "impossible_timestamps",
                impossible_timestamp_ids,
                "A real closed trade whose closedSimMinutes is earlier than its own openedSimMinutes — physically impossible, a real data-integrity signal.",
            ),
            _issue(
                "dangling_strategy_reference",
                dangling_reference_ids,
                "A real CeoDecisionRecord names a strategyId that no longer matches any real Strategy in the current roster.",
            ),
            _issue(
                "missing_decision_time_context",
                missing_context_ids,
                "A real buy/sell CeoDecisionRecord with no decisionSession recorded — expected only for decisions made before this directive's Part 8 Decision-Time Snapshot existed, never for a new one.",
            ),
            _issue(
                "missing_strategy_rule_snapshot",
                missing_snapshot_ids,
                "A real CeoDecisionRecord names a strategyId but has no strategyCompiledDefinitionId — either that Strategy genuinely has no compiled rules yet (an honest 'idea'-stage pick), or the decision predates this directive's Part 2 Strategy Rule Snapshot. This module cannot distinguish the two cases from what's on record, so both are reported together, honestly, rather than guessing which applies.",
            ),
        )
        if i is not None
    ]

    total = sum(i.count for i in issues)

    return DataQualityMonitor(
        issues=issues,
        totalIssueCount=total,
        detail=(f"{total} real data-quality issue(s) across {len(issues)} categor{'y' if len(issues) == 1 else 'ies'}." if total else "No real data-quality issues found in any of the four categories this module checks."),
        updatedAt=_now_iso(),
    )
