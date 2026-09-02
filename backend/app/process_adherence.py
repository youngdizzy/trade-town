"""app/process_adherence.py — Trading Psychology & Discipline, Piece C:
the Process Adherence Score (Design Bible Chapter 66 addendum).

THE HONESTY BOUNDARY (read this before adding anything to this module):
the CEO's own request named a "Plan Adherence Engine" comparing PLANNED
vs. ACTUAL entry/exit conditions, stop-loss/take-profit placement, and
confluence requirements. This module builds a real "Process Adherence
Score" using ONLY information this architecture can actually verify,
with every unbuildable component reported as `not_trackable_yet` —
never scored as pass, never as fail, never silently omitted.

CEO directive "UI / Governance / Travel Mode Hardening," Phase 6 — this
boundary is RE-AUDITED against the current codebase on every pass, not
assumed frozen at whatever it was when this module was first written.
Stop-Loss/Take-Profit Placement used to be `not_trackable_yet` (no
stop-loss/take-profit order concept existed anywhere in this paper-
trading engine at the time) — Hard Risk Gates 2.0 later gave
`PaperTrade` a real, persisted `stop_price`/`target_price` plus a real
`entry_price`/`side` to validate them against, so `_stop_loss_check()`/
`_take_profit_check()` below now report a real pass/fail whenever a
trade has one, honestly falling back to `not_trackable_yet` for any
trade that predates that directive or never had real ATR evidence.
Entry Condition Match / Exit Condition Match / Confluence Requirements
remain genuinely `not_trackable_yet`: `StrategyHypothesis.entry_
conditions`/`exit_conditions` are CEO/agent-authored free text (that
schema's own docstring: "never independently verified by this schema
itself"), not a structured, machine-checkable condition, most decisions
carry no `strategy_id` at all (the CEO strategy selector is opt-in), and
no confluence-requirement field exists anywhere in this codebase.
Comparing a real exit reason against a free-text sentence, or inventing
a confluence checklist, would be exactly the fabricated-precision trap
this project's engineering discipline exists to prevent.

Every check below reuses data this codebase already computes for a
different real reason, never a second, parallel computation:

  Gatekeeper checks       -> the real, already-produced GatekeeperCheck
                              list on TradeDecision.gatekeeper_verdict
                              (app/gatekeeper.py) — surfaced exactly as
                              produced, one row per real check, so a
                              rejected decision honestly shows which
                              specific check(s) failed.
  Discipline Process
  Quality                  -> the Discipline Chamber's own real tier
                              (app/discipline.py's DisciplineReview,
                              reused by decision_id — never a second,
                              differently-weighted computation).
  Trading Mode Compliance  -> the trade's own real `trading_style` tag
                              (Design Bible Chapter 75,
                              app/trading_modes.py's assign_trading_style())
                              plus its real closed duration — a
                              "day"-tagged position that outlived the
                              1440-minute same-day discipline bar is a
                              real, checkable violation; every other
                              tagged case is compliant by construction
                              (the single real assignment point).
  Stop-Loss/Take-Profit
  Placement                 -> PaperTrade.stop_price/target_price/
                              entry_price/side (Hard Risk Gates 2.0),
                              carried over from PaperPosition by
                              app/portfolio.py's close_position() the
                              same way maePct/mfePct already are —
                              never a second, independently-derived
                              price.

`score_pct` is computed only from checks this architecture could
actually evaluate (`verified_count` = passed + failed); `not_trackable_
count` is disclosed separately and never folded into either side of the
score, so the UI can honestly show "Process Adherence: 71% · Verified:
5/7 · Not Trackable Yet: 5 · Failed: 2" without ever implying full plan
adherence was measured.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    DisciplineReview,
    PaperTrade,
    ProcessAdherenceCheck,
    ProcessAdherenceRead,
    ProcessAdherenceSummaryRead,
    TradeDecision,
)

# Trading Psychology & Discipline, Piece G — how many of the most recent
# decisions the company-wide summary looks at. Matches the same window
# size app/self_improvement.py's own recurring-pattern generators
# (RECURRING_MISTAKE_WINDOW/RECURRING_SUCCESS_WINDOW) already settled on
# for "recent enough to be a real, current read" without reusing that
# constant directly — this module has no dependency on self_improvement.py
# and shouldn't gain one just to share one number.
RECENT_DECISIONS_WINDOW = 10

# Day Trading discipline's own real same-day bar (Design Bible Chapter
# 75, app/trading_modes.py's flatten_day_positions() — force-closes any
# "day"-tagged position still open at sim-day rollover). A "day"-tagged
# closed trade held longer than this is real, checkable evidence the
# discipline was not followed for that specific trade.
DAY_TRADING_MAX_HOLD_MINUTES = 1440

# CEO directive "UI / Governance / Travel Mode Hardening," Phase 6 —
# re-audited against the CURRENT codebase (not this module's own,
# now-stale founding claim) whether each item below can be made real.
# Stop-Loss/Take-Profit Placement were promoted out of this list: Hard
# Risk Gates 2.0 (built after this module was first written) gave
# PaperTrade a real, persisted stop_price/target_price plus a real
# entry_price/side to validate them against (see _stop_loss_check()/
# _take_profit_check() below) — genuine evidence, not a schema stub.
# Entry Condition Match / Exit Condition Match / Confluence Requirements
# stay here: StrategyHypothesis.entry_conditions/exit_conditions are
# CEO/agent-authored free text (its own docstring: "never independently
# verified by this schema itself"), not a structured, machine-checkable
# condition — and most decisions carry no strategy_id at all (the CEO
# strategy selector is opt-in). No confluence-requirement field exists
# anywhere in this codebase. Comparing a real exit_reason/exit_price
# against a free-text sentence, or inventing a confluence checklist,
# would be exactly the fabricated-precision trap this project's
# engineering discipline exists to prevent — so these three stay
# honestly not_trackable_yet.
_NOT_TRACKABLE_CHECKS: tuple[tuple[str, str], ...] = (
    ("entry_condition_match", "Entry Condition Match"),
    ("exit_condition_match", "Exit Condition Match"),
    ("confluence_requirements", "Confluence Requirements"),
)
_NOT_TRACKABLE_DETAIL = "Full plan adherence requires future execution/order-plan infrastructure this paper-trading engine does not have yet."


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gatekeeper_checks(decision: TradeDecision) -> list[ProcessAdherenceCheck]:
    if decision.gatekeeper_verdict is None:
        return [
            ProcessAdherenceCheck(
                id="gatekeeper_verdict",
                label="Gatekeeper Verdict",
                status="not_trackable_yet",
                detail="Not applicable — the CEO chose WAIT (no trade was ever proposed to the Gatekeeper), or this decision predates the Trade Gatekeeper.",
            )
        ]
    return [
        ProcessAdherenceCheck(
            id=f"gatekeeper_{c.id}",
            label=f"Gatekeeper — {c.label}",
            status="passed" if c.passed else "failed",
            detail=c.detail,
        )
        for c in decision.gatekeeper_verdict.checks
    ]


def _discipline_check(discipline_review: DisciplineReview | None) -> ProcessAdherenceCheck:
    if discipline_review is None:
        return ProcessAdherenceCheck(
            id="discipline_process_quality",
            label="Discipline Process Quality",
            status="not_trackable_yet",
            detail="No trade ever closed for this decision yet — the Discipline Chamber only files a review once a position closes.",
        )
    passed = discipline_review.tier in ("exemplary", "sound", "adequate")
    return ProcessAdherenceCheck(
        id="discipline_process_quality",
        label="Discipline Process Quality",
        status="passed" if passed else "failed",
        detail=f"The Discipline Chamber's own real review scored this decision's process {discipline_review.score:.0f}/100 ({discipline_review.tier}).",
    )


def _trading_mode_check(trade: PaperTrade | None) -> ProcessAdherenceCheck:
    if trade is None:
        return ProcessAdherenceCheck(
            id="trading_mode_compliance",
            label="Trading Mode Compliance",
            status="not_trackable_yet",
            detail="No trade ever opened for this decision yet — nothing real to check against a Trading Mode.",
        )
    if trade.trading_style is None:
        return ProcessAdherenceCheck(
            id="trading_mode_compliance",
            label="Trading Mode Compliance",
            status="not_trackable_yet",
            detail="This trade predates Trading Mode tagging (Design Bible Chapter 75) — no real trading style was ever recorded for it.",
        )
    if trade.trading_style == "day" and trade.duration_minutes > DAY_TRADING_MAX_HOLD_MINUTES:
        return ProcessAdherenceCheck(
            id="trading_mode_compliance",
            label="Trading Mode Compliance",
            status="failed",
            detail=f"Tagged \"day\" but held {trade.duration_minutes} real minutes — exceeds the {DAY_TRADING_MAX_HOLD_MINUTES}-minute Day Trading same-day discipline bar.",
        )
    return ProcessAdherenceCheck(
        id="trading_mode_compliance",
        label="Trading Mode Compliance",
        status="passed",
        detail=f"Tagged \"{trade.trading_style}\" at proposal creation and carried through to close — Trading Mode assignment is enforced at the one real assignment point (assign_trading_style()), never independently variable per trade.",
    )


def _stop_loss_check(trade: PaperTrade | None) -> ProcessAdherenceCheck:
    """CEO directive "UI / Governance / Travel Mode Hardening," Phase 6
    — real evidence: PaperTrade.stop_price/entry_price/side, carried
    over from PaperPosition by app/portfolio.py's close_position() the
    same way maePct/mfePct already are. PASS requires the stop to
    actually sit on the correct side of entry for this trade's real
    direction — never just "a stop_price exists.\""""
    if trade is None:
        return ProcessAdherenceCheck(
            id="stop_loss_placement",
            label="Stop-Loss Placement",
            status="not_trackable_yet",
            detail="No trade was ever opened for this decision — nothing real to check yet.",
        )
    if trade.stop_price is None:
        return ProcessAdherenceCheck(
            id="stop_loss_placement",
            label="Stop-Loss Placement",
            status="not_trackable_yet",
            detail="This trade predates Hard Risk Gates 2.0, or no real ATR-based stop evidence existed for this symbol at open time — no real stop price was ever recorded.",
        )
    is_long = trade.side == "buy"
    valid = trade.stop_price > 0 and ((trade.stop_price < trade.entry_price) if is_long else (trade.stop_price > trade.entry_price))
    direction = "long" if is_long else "short"
    if valid:
        return ProcessAdherenceCheck(
            id="stop_loss_placement",
            label="Stop-Loss Placement",
            status="passed",
            detail=f"Real stop-loss at {trade.stop_price:.4f} is correctly placed {'below' if is_long else 'above'} the {trade.entry_price:.4f} entry for this {direction}.",
        )
    return ProcessAdherenceCheck(
        id="stop_loss_placement",
        label="Stop-Loss Placement",
        status="failed",
        detail=f"Real stop-loss at {trade.stop_price:.4f} is on the wrong side of the {trade.entry_price:.4f} entry for this {direction} — Hard Risk Gates 2.0 should never allow this.",
    )


def _take_profit_check(trade: PaperTrade | None) -> ProcessAdherenceCheck:
    """Same real-evidence pattern as _stop_loss_check() above, using
    PaperTrade.target_price — the real reward:risk-multiple level
    app/executive.py's resolve_proposal() computes at fill time
    (TARGET_REWARD_RISK_MULTIPLE x the real ATR stop distance), never a
    fabricated one. A trade can have a valid stop but no target
    (target_price is only set alongside a valid stop_distance) — that
    combination is real and honestly not_trackable_yet, never inferred
    as a failure."""
    if trade is None:
        return ProcessAdherenceCheck(
            id="take_profit_placement",
            label="Take-Profit Placement",
            status="not_trackable_yet",
            detail="No trade was ever opened for this decision — nothing real to check yet.",
        )
    if trade.target_price is None:
        return ProcessAdherenceCheck(
            id="take_profit_placement",
            label="Take-Profit Placement",
            status="not_trackable_yet",
            detail="This trade predates Hard Risk Gates 2.0, or no real ATR-based stop evidence existed for this symbol at open time — no real take-profit target was ever recorded.",
        )
    is_long = trade.side == "buy"
    valid = trade.target_price > 0 and ((trade.target_price > trade.entry_price) if is_long else (trade.target_price < trade.entry_price))
    direction = "long" if is_long else "short"
    if valid:
        return ProcessAdherenceCheck(
            id="take_profit_placement",
            label="Take-Profit Placement",
            status="passed",
            detail=f"Real take-profit at {trade.target_price:.4f} is correctly placed {'above' if is_long else 'below'} the {trade.entry_price:.4f} entry for this {direction}.",
        )
    return ProcessAdherenceCheck(
        id="take_profit_placement",
        label="Take-Profit Placement",
        status="failed",
        detail=f"Real take-profit at {trade.target_price:.4f} is on the wrong side of the {trade.entry_price:.4f} entry for this {direction} — this should never happen if target computation is intact.",
    )


def _not_trackable_checks() -> list[ProcessAdherenceCheck]:
    return [ProcessAdherenceCheck(id=check_id, label=label, status="not_trackable_yet", detail=_NOT_TRACKABLE_DETAIL) for check_id, label in _NOT_TRACKABLE_CHECKS]


def compute_process_adherence(decision: TradeDecision, trade: PaperTrade | None, discipline_review: DisciplineReview | None) -> ProcessAdherenceRead:
    """The one real function computing this score — never persisted,
    computed fresh on demand (the same "computed fresh per request,
    never a second drifting copy" convention app/strategy_lab.py's
    Certification already established), so a review filed after this
    was first read automatically shows up the next time it's read."""
    checks: list[ProcessAdherenceCheck] = [
        *_gatekeeper_checks(decision),
        _discipline_check(discipline_review),
        _trading_mode_check(trade),
        _stop_loss_check(trade),
        _take_profit_check(trade),
        *_not_trackable_checks(),
    ]
    passed_count = sum(1 for c in checks if c.status == "passed")
    failed_count = sum(1 for c in checks if c.status == "failed")
    not_trackable_count = sum(1 for c in checks if c.status == "not_trackable_yet")
    verified_count = passed_count + failed_count
    score_pct = round(passed_count / verified_count * 100, 1) if verified_count > 0 else None

    return ProcessAdherenceRead(
        decisionId=decision.id,
        symbol=decision.symbol,
        scorePct=score_pct,
        verifiedCount=verified_count,
        passedCount=passed_count,
        failedCount=failed_count,
        notTrackableCount=not_trackable_count,
        checks=checks,
        computedAt=_now_iso(),
    )


def compute_recent_process_adherence_summary(
    decisions: list[TradeDecision],
    trade_history: list[PaperTrade],
    discipline_reviews: list[DisciplineReview],
    *,
    window: int = RECENT_DECISIONS_WINDOW,
) -> ProcessAdherenceSummaryRead:
    """Trading Psychology & Discipline, Piece G — the one company-wide
    aggregate over ProcessAdherenceRead this codebase never needed
    before every other consumer read a single decision's own score by
    id. Reuses compute_process_adherence() unchanged for each of the
    most recent `window` decisions (the same trailing-window convention
    app/self_improvement.py's own recurring-pattern generators already
    use) — never a second, differently-weighted scoring path.
    `average_score_pct` is the mean of only the decisions that actually
    had a real score (`scorePct is not None`) — a decision with zero
    verified checks contributes to `decisions_reviewed` honestly but
    never gets averaged in as a fabricated 0%."""
    recent = decisions[-window:]
    trade_by_decision = {t.decision_id: t for t in trade_history if t.decision_id is not None}
    review_by_decision = {r.decision_id: r for r in discipline_reviews}

    scores: list[float] = []
    for decision in recent:
        read = compute_process_adherence(
            decision,
            trade_by_decision.get(decision.id),
            review_by_decision.get(decision.id),
        )
        if read.score_pct is not None:
            scores.append(read.score_pct)

    average_score_pct = round(sum(scores) / len(scores), 1) if scores else None

    return ProcessAdherenceSummaryRead(
        decisionsReviewed=len(recent),
        decisionsWithVerifiedChecks=len(scores),
        averageScorePct=average_score_pct,
        computedAt=_now_iso(),
    )
