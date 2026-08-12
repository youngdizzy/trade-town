"""app/process_adherence.py — Trading Psychology & Discipline, Piece C:
the Process Adherence Score (Design Bible Chapter 66 addendum).

THE HONESTY BOUNDARY (read this before adding anything to this module):
the CEO's own request named a "Plan Adherence Engine" comparing PLANNED
vs. ACTUAL entry/exit conditions, stop-loss/take-profit placement, and
confluence requirements — none of that exists anywhere in this codebase.
`app/gatekeeper.py`'s own module docstring already establishes why:
there is no stop-loss/take-profit order concept, no entry/exit condition
model, and no confluence checklist anywhere in this paper-trading
engine, and inventing one here would be exactly the fabricated-precision
trap this project's engineering discipline exists to prevent. This
module builds the honest, narrower subset the CEO explicitly asked for
instead: a real "Process Adherence Score" using ONLY information this
architecture can actually verify, with every unbuildable component
reported as `not_trackable_yet` — never scored as pass, never as fail,
never silently omitted.

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

`score_pct` is computed only from checks this architecture could
actually evaluate (`verified_count` = passed + failed); `not_trackable_
count` is disclosed separately and never folded into either side of the
score, so the UI can honestly show "Process Adherence: 71% · Verified:
5/7 · Not Trackable Yet: 5 · Failed: 2" without ever implying full plan
adherence was measured.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import DisciplineReview, PaperTrade, ProcessAdherenceCheck, ProcessAdherenceRead, TradeDecision

# Day Trading discipline's own real same-day bar (Design Bible Chapter
# 75, app/trading_modes.py's flatten_day_positions() — force-closes any
# "day"-tagged position still open at sim-day rollover). A "day"-tagged
# closed trade held longer than this is real, checkable evidence the
# discipline was not followed for that specific trade.
DAY_TRADING_MAX_HOLD_MINUTES = 1440

# app/gatekeeper.py's own module docstring already names these as
# deliberately unbuilt — repeated here, never re-derived, so this
# module's own NOT_TRACKABLE_YET list stays in lockstep with that
# module's honesty boundary if it ever changes.
_NOT_TRACKABLE_CHECKS: tuple[tuple[str, str], ...] = (
    ("stop_loss_placement", "Stop-Loss Placement"),
    ("take_profit_placement", "Take-Profit Placement"),
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
