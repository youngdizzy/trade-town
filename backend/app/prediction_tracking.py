"""Prediction -> Outcome Tracking — CEO directive "Features 26-30: Agent
Intelligence, Learning & Institutional Memory System," Feature 29 (the
fourth stage of the 26->27->28->29->30 learning loop; per the
directive's own staging rule, this does not begin until Feature 28 is
tested and integrated, and Feature 30 does not begin until this one is).

NAMING COLLISION, disclosed up front: `app/reasoning_lab.py` already
carries an unrelated "v0.7 Feature 29" tag from this codebase's older,
independent versioning scheme (the Reasoning Lab — a process-quality
practice log, structurally forbidden from ever reading a trade's real
pnl). That is a different numbering system than this directive's own
26->27->28->29->30 scheme, which is what every reference to "Feature 29"
in this module and its sibling schemas means. The two collided by
accident; both are real, both stay as-is — see `decision_vault.py`'s own
docstring for the identical disambiguation this codebase already applied
once before for a "Feature 53"/"Feature 54" collision.

Research finding (recorded here per the directive's "document what was
found before coding" rule): no general-purpose, per-claim prediction
ledger existed anywhere in this codebase before this module — confirmed
by an exhaustive grep for prediction/forecast/calibration/hindsight/
resolve/pending_outcome across the whole backend. What already existed:

  - `app/analytics.py`'s `confidence_accuracy()`/`research_accuracy()` —
    real, aggregate confidence-vs-outcome grading, already reused
    verbatim by Feature 27's `calibration`/`decision_accuracy`
    dimensions and Feature 28's `prediction_calibration` skill domain.
    These stay the one source of truth for those two dimensions — this
    module does NOT recompute them. What they structurally cannot
    provide, and what this module adds: a persisted, individually-
    addressable per-prediction audit trail (today you can only ever see
    the current blended aggregate, never list or drill into one specific
    staked claim).
  - `app/schemas.py`'s `CeoDecisionRecord` (`app/executive.py`'s
    `grade_ceo_decisions()`) — a real pending -> resolved lifecycle for
    CEO trade decisions, matched to a closed `PaperTrade` by
    `decision_id` (the same real link `app/journal.py` stamps onto every
    closed trade). This is the closest real precedent and the pattern
    this module's own `grade_predictions()` mirrors exactly, generalized
    into its own persisted schema rather than folded into
    `CeoDecisionRecord`'s CEO-Accuracy-specific fields.
  - `app/gatekeeper.py`/`app/opportunity_gatekeeper.py`'s
    `GatekeeperRejection`/`OpportunityRejection` (a fixed-window,
    price-resolved hypothetical-trade ledger) and
    `app/market_intelligence.py`'s `MarketIntelligenceLearningEntry` (a
    real, day-boundary-gated regime-call grading loop) are each already
    complete, working, single-purpose pending->resolved systems with
    their own real frontend surfaces (`ExecutivePanel.tsx`,
    `MarketIntelPanel.tsx`'s "Learning Loop"). This module does not wrap
    or re-persist them a second time — doing so would duplicate real,
    already-shipped machinery. They stay exactly as they are; a future
    addendum could fold their already-resolved verdicts into
    Institutional Memory too, but that is explicitly out of scope here.

`ResearchItem.confidence` claims are explicitly NOT tracked here either:
`research_accuracy()`'s ">=70%" check is a self-consistency threshold
against the research item's own claimed confidence, not a resolution
against independent later truth (no real `research_item_id -> trade_id`
link exists anywhere in this codebase) — tracking it here would either
silently duplicate that threshold check or fabricate a link that isn't
real. Same for `ModelValidationReport.verdict` (explicitly advisory-only,
never re-checked against later strategy performance anywhere) and a
strategy's original Company Review expectancy claim (`compute_
strategy_health()` is a continuously rolling read, not a single
resolvable terminal claim). All three are disclosed, honest scope cuts,
not a silent gap.

The one real, in-scope claim type: **trade direction**. Every trade the
CEO's real decision actually caused (`TradeDecision.order_id is not
None`) stakes a real, checkable claim — the exact `predicted_direction`/
`confidence_pct` already stamped on the `CeoDecisionRecord` at the same
real decision moment, generalized here into its own persisted record
rather than only ever contributing to the CEO-Accuracy aggregate. Built,
never resolved with hindsight: `build_prediction_record()` runs at
decision time (mirroring `CeoDecisionRecord`'s own creation moment
exactly), `grade_predictions()` only ever resolves a record from a real
closed trade recorded strictly after it — the same hindsight-safety
`app/market_intelligence.py`'s Learning Loop already established for its
own regime-call grading (grade only after a full real trade has
genuinely closed).
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import CeoDecisionRecord, PaperTrade, PredictionRecord, TradeDecision

MAX_PREDICTION_RECORDS = 150

# A "notable" miscalibration worth promoting to Institutional Memory: a
# real high-confidence claim that still resolved wrong — the same
# "overconfident loser scores low" framing app/analytics.py's
# confidence_accuracy() docstring already uses, formalized here as a
# disclosed threshold rather than promoting every single resolved
# prediction (which would flood institutional memory with routine,
# unremarkable outcomes).
HIGH_CONFIDENCE_MISS_THRESHOLD = 70.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_prediction_record(decision: TradeDecision, record: CeoDecisionRecord, *, sim_day: int) -> PredictionRecord | None:
    """Returns None when no real trade-direction claim exists to track —
    a CEO "wait" (`decision.order_id is None`) makes no directional claim
    at all. `record.ceo_decision` (not the caller's original proposed
    choice) is read deliberately: `app/executive.py`'s resolve_proposal()
    can internally downgrade a real buy/sell to "wait" when the position
    sizes to zero, and `CeoDecisionRecord.ceo_decision` is already the
    real, final, post-downgrade choice — the same field
    `grade_ceo_decisions()` itself trusts."""
    if decision.order_id is None:
        return None
    direction = record.ceo_decision
    if direction != "buy" and direction != "sell":
        return None
    return PredictionRecord(
        id=f"prediction-{decision.id}",
        decisionId=decision.id,
        symbol=decision.symbol,
        claimType="trade_direction",
        predictedDirection=direction,
        confidencePct=decision.confidence,
        attributedAgents=list(decision.supporting_agents),
        simDay=sim_day,
        createdAt=decision.created_at,
    )


def grade_predictions(records: list[PredictionRecord], trade_history: list[PaperTrade]) -> list[PredictionRecord]:
    """Resolves any "pending" record whose linked trade has since closed
    — matched by decision_id, the exact same real link
    `app/executive.py`'s `grade_ceo_decisions()` already uses. A record
    with no matching closed trade yet stays "pending" unchanged; nothing
    here ever resolves early or from data older than the record's own
    `created_at`."""
    if not records:
        return records
    by_decision_id: dict[str, PaperTrade] = {t.decision_id: t for t in trade_history if t.decision_id}
    updated: list[PredictionRecord] = []
    for prediction in records:
        if prediction.outcome != "pending":
            updated.append(prediction)
            continue
        trade = by_decision_id.get(prediction.decision_id)
        if trade is None:
            updated.append(prediction)
            continue
        outcome = "correct" if trade.pnl > 0 else "incorrect"
        updated.append(
            prediction.model_copy(
                update={
                    "outcome": outcome,
                    "resolved_trade_id": trade.id,
                    "resolved_pnl_pct": trade.pnl_pct,
                    "resolved_at": _now_iso(),
                }
            )
        )
    return updated


def should_promote_prediction_outcome(record: PredictionRecord) -> bool:
    """Only a real, notable miscalibration is worth filing as
    institutional knowledge — a routine correct call, or an incorrect
    call made with honestly low confidence, isn't a surprising lesson."""
    return record.outcome == "incorrect" and record.confidence_pct >= HIGH_CONFIDENCE_MISS_THRESHOLD
