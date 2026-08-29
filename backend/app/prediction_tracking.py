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

from app.schemas import (
    AGENT_IDS,
    AgentBrierCalibration,
    BrierCalibrationSummary,
    CeoDecisionRecord,
    ConfidenceBucketCalibration,
    FailureClassification,
    PaperTrade,
    PredictionRecord,
    TradeDecision,
)

MAX_PREDICTION_RECORDS = 150

# CEO directive "Professional Quant Trading Core," Phase B P2 item —
# Brier-score calibration. Same real-evidence-floor reasoning as this
# codebase's other MIN_*_FOR_VERDICT constants (MIN_RETIREMENT_TRADE_
# COUNT / MIN_TRADES_FOR_PORTFOLIO_MONTE_CARLO, both 10) — reused value,
# not independently chosen.
MIN_PREDICTIONS_FOR_BRIER_VERDICT = 10
# Same reasoning, applied per-bucket: a bucket with 1-2 real resolved
# predictions can't honestly report a real accuracy rate.
MIN_PREDICTIONS_FOR_BUCKET_VERDICT = 3

# Real trades only ever reach this ledger with confidence_pct at or
# above the Gatekeeper's own MIN_CONFIDENCE (55.0 by default, CEO-
# configurable) — see app/gatekeeper.py's `_confidence_check()` — so a
# resolved prediction's real confidence never falls below roughly this
# floor. Buckets still span the full 0-100 range so a lower CEO-
# configured threshold, or a future claim type, is never silently
# dropped.
_CALIBRATION_BUCKET_EDGES: list[float] = [0.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

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


def grade_predictions(
    records: list[PredictionRecord],
    trade_history: list[PaperTrade],
    failure_classifications: list[FailureClassification] | None = None,
) -> list[PredictionRecord]:
    """Resolves any "pending" record whose linked trade has since closed
    — matched by decision_id, the exact same real link
    `app/executive.py`'s `grade_ceo_decisions()` already uses. A record
    with no matching closed trade yet stays "pending" unchanged; nothing
    here ever resolves early or from data older than the record's own
    `created_at`.

    CEO directive Feature 30 feed-back: when a prediction resolves
    "incorrect", `failure_reason` is filled from the real
    FailureClassification app/failure_review.py already filed for the
    same trade (matched by `trade.id`, the same real trade-close moment
    both records are generated from) — never a second, independent
    guess. Stays None when no classification exists yet for that trade
    (e.g. `failure_classifications` omitted by an older caller, or the
    trade predates Feature 30)."""
    if not records:
        return records
    by_decision_id: dict[str, PaperTrade] = {t.decision_id: t for t in trade_history if t.decision_id}
    by_trade_id: dict[str, FailureClassification] = {c.trade_id: c for c in (failure_classifications or [])}
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
        classification = by_trade_id.get(trade.id) if outcome == "incorrect" else None
        updated.append(
            prediction.model_copy(
                update={
                    "outcome": outcome,
                    "resolved_trade_id": trade.id,
                    "resolved_pnl_pct": trade.pnl_pct,
                    "failure_reason": classification.reason if classification is not None else None,
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


def compute_brier_calibration(records: list[PredictionRecord]) -> BrierCalibrationSummary:
    """CEO directive "Professional Quant Trading Core," Phase B P2 item.

    The real Brier score — a standard proper scoring rule, not a new
    invented metric — is the mean squared error between a stated
    probability and its real binary outcome:
    `mean((confidence_pct / 100 - is_correct) ** 2)` over every real
    RESOLVED prediction in this ledger (`outcome != "pending"`). 0.0 is
    perfect calibration; 1.0 is the worst possible (always confidently
    wrong); ~0.25 is what a constantly-50%-confident forecaster scores
    against a 50/50 real base rate. Lower is better. `is_correct` is
    exactly `PredictionRecord.outcome == "correct"`, the same real
    win/loss read `grade_predictions()` above already assigns from a
    trade's own real `pnl > 0` — no second, independent grading.

    Distinct from `app/analytics.py::confidence_accuracy()` — that
    function is a cruder per-trade heuristic ("a confident winner or an
    unconfident loser both score high") averaged directly, not a real
    proper scoring rule, and runs over the whole trade history rather
    than this ledger's specifically-tracked directional claims. Both are
    real; neither replaces the other.

    `buckets` is the standard reliability-diagram breakdown: real
    resolved predictions grouped by their own stated confidence range,
    each showing the real observed accuracy in that range next to the
    average confidence actually claimed there — a well-calibrated desk's
    real accuracy in each bucket should track its own stated confidence
    closely; a systematically overconfident or underconfident desk shows
    up as a real, visible gap between the two columns."""
    resolved = [r for r in records if r.outcome != "pending"]
    now_iso = _now_iso()

    buckets: list[ConfidenceBucketCalibration] = []
    for low, high in zip(_CALIBRATION_BUCKET_EDGES[:-1], _CALIBRATION_BUCKET_EDGES[1:]):
        in_bucket = [r for r in resolved if low <= r.confidence_pct < high or (high == 100.0 and r.confidence_pct == 100.0)]
        if not in_bucket:
            continue
        correct_count = sum(1 for r in in_bucket if r.outcome == "correct")
        buckets.append(
            ConfidenceBucketCalibration(
                rangeLowPct=low,
                rangeHighPct=high,
                predictedCount=len(in_bucket),
                realAccuracyPct=round(correct_count / len(in_bucket) * 100, 1) if len(in_bucket) >= MIN_PREDICTIONS_FOR_BUCKET_VERDICT else None,
                avgStatedConfidencePct=round(sum(r.confidence_pct for r in in_bucket) / len(in_bucket), 1),
            )
        )

    if len(resolved) < MIN_PREDICTIONS_FOR_BRIER_VERDICT:
        return BrierCalibrationSummary(
            resolvedPredictionCount=len(resolved),
            brierScore=None,
            evidenceState="not_enough_data",
            buckets=buckets,
            summary=f"Only {len(resolved)} real resolved prediction(s) so far — below the {MIN_PREDICTIONS_FOR_BRIER_VERDICT}-prediction minimum for a real Brier-score verdict.",
            updatedAt=now_iso,
        )

    squared_errors = [((r.confidence_pct / 100.0) - (1.0 if r.outcome == "correct" else 0.0)) ** 2 for r in resolved]
    brier_score = round(sum(squared_errors) / len(squared_errors), 4)
    quality = "well-calibrated" if brier_score <= 0.15 else "moderately calibrated" if brier_score <= 0.25 else "poorly calibrated"
    summary = f"Brier score {brier_score:.3f} over {len(resolved)} real resolved predictions — {quality} (0.0 = perfect, ~0.25 = a coin-flip forecaster, 1.0 = worst possible)."

    return BrierCalibrationSummary(
        resolvedPredictionCount=len(resolved),
        brierScore=brier_score,
        evidenceState="sufficient_evidence",
        buckets=buckets,
        summary=summary,
        updatedAt=now_iso,
    )


def compute_agent_brier_calibration(records: list[PredictionRecord]) -> list[AgentBrierCalibration]:
    """CEO directive "Professional Quant Portfolio Intelligence + Alpha
    Research Engine," Phase 7 — the exact same real Brier-score
    methodology `compute_brier_calibration()` above already implements,
    computed once per real named agent over only the real predictions
    that agent is an actual `attributed_agents` member of (the same
    real per-agent split `app/executive.py`'s `resolve_proposal()`
    already stamps onto every real trade decision — never a fabricated
    per-agent confidence split). One agent's own real prediction can
    (and often will) also count toward another agent's own real
    calibration read when they jointly supported the same decision —
    an honest reflection of how this codebase's own desk actually
    votes (`AnalystVote`s are per-role, not solo), not a double-count
    bug: each agent's own summary answers "how calibrated is THIS
    agent's own stated confidence," independently of who else agreed.
    Every agent still gets a real, honest `not_enough_data` state below
    `MIN_PREDICTIONS_FOR_BRIER_VERDICT`, exactly like the desk-wide
    read — never a fabricated per-agent verdict from a handful of
    shared predictions."""
    return [
        AgentBrierCalibration(
            agentId=agent_id,
            calibration=compute_brier_calibration([r for r in records if agent_id in r.attributed_agents]),
        )
        for agent_id in AGENT_IDS
    ]
