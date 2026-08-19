"""CEO directive "Features 31-35," Feature 34 — Compliance Control
Effectiveness.

RESEARCH FIRST (per the directive's own mandatory rule): app/gatekeeper.py
already runs 11 real checks, unconditionally, on every real trade decision
that reaches a buy/sell choice — full results stored on
`TradeDecision.gatekeeper_verdict.checks`, never a second, independently
computed read. When a decision is rejected (`approved=False`), the
already-real `GatekeeperRejection` (app/gatekeeper.py's
grade_gatekeeper_rejections) resolves whether the block was actually
correct, purely from real subsequent watchlist price movement — never a
placed order, never a fabricated P&L.

This module answers Feature 34's core question per control: "Did the
control prevent or detect the problem it was designed to address?" —
computed fresh per request from state this codebase already persists
(`state.decisions`, `state.gatekeeper_rejections`), the same read-only,
never-persisted CAGS convention app/audit_log.py already established.
No new GameSaveState field; no WS broadcast change.

THE ATTRIBUTION HONESTY BOUNDARY: `evaluate_gatekeeper()` rejects a
decision when *any* check fails (`approved = all(c.passed for c in
checks)`), so a single rejected decision can have several checks failing
simultaneously. A real outcome can only be attributed to ONE specific
control when that control was the *sole* failing check for that decision
— every other case is counted separately as `ambiguousAttributionCount`
rather than guessed at. This is the same "never invent prevented
incidents" discipline the CEO directive requires everywhere else in this
body of work.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    ControlEffectivenessRecord,
    ControlEffectivenessSummary,
    GatekeeperControlEffectivenessState,
    GatekeeperRejection,
    TradeDecision,
)

# Feature 33's MIN_ACCURACY_SAMPLE_FOR_VERDICT established the "real,
# disclosed floor before a tracked read counts as a meaningful verdict"
# convention for this body of work. Reused verbatim here: fewer than this
# many confirmed (non-pending, sole-reason) outcomes for a control is
# INSUFFICIENT_DATA, never a forced effective/ineffective call.
MIN_CONTROL_SAMPLE_FOR_VERDICT = 3

# The same 60%/40% pass/fail convention Feature 33 reused from
# ExecutiveVoting.tsx's own pre-existing green/amber/red thresholds.
# Reused again here for one consistent evidence-grading language across
# the whole Compliance system, rather than a fourth arbitrary cutoff.
_EFFECTIVE_THRESHOLD_PCT = 60.0
_INEFFECTIVE_THRESHOLD_PCT = 40.0

# (control_id, control_label, purpose, owner) — purpose/owner text
# describes exactly what app/gatekeeper.py's own check functions already
# do (see each function's docstring/body), never invented behavior.
_CONTROL_CATALOG: list[tuple[str, str, str, str]] = [
    (
        "confidence",
        "Decision Confidence",
        "Blocks a trade whose real Decision Confidence Engine score falls below the required minimum.",
        "Decision Confidence Engine (app/confidence.py)",
    ),
    (
        "risk_manager",
        "Risk Manager Alignment",
        "Blocks a trade the desk's own Risk Manager analyst vote disagreed with.",
        "Risk Manager analyst vote (app/executive.py)",
    ),
    (
        "agreement",
        "Multi-Agent Agreement",
        "Blocks a trade that a majority of the analyst desk did not actually agree with.",
        "Multi-Agent analyst voting (app/executive.py)",
    ),
    (
        "debate",
        "AI Debate Outcome",
        "Blocks a trade whose AI Debate final recommendation contradicts the CEO's choice.",
        "AI Debate Engine (app/debate.py)",
    ),
    (
        "exposure",
        "Portfolio Exposure",
        "Blocks a trade once open positions already meet the account's max-open-positions limit.",
        "Risk Limits / Portfolio Exposure (app/portfolio.py, app/risk.py)",
    ),
    (
        "correlation",
        "Correlated Positions",
        "Blocks a trade that would push correlated same-category open positions past the allowed maximum.",
        "Symbol category correlation map (app/watchlist.py)",
    ),
    (
        "risk_warning",
        "Active Risk Warnings",
        "Blocks a trade on a symbol currently carrying an active critical Risk Warning.",
        "Risk warning engine (app/risk_engine.py)",
    ),
    (
        "market_intelligence",
        "Market Intelligence Quality",
        "Blocks a trade while the Market Intelligence Department's own Market Quality Score reads avoid_trading.",
        "Market Intelligence Department (app/market_intelligence.py)",
    ),
    (
        "weighted_executive",
        "Weighted Executive Recommendation",
        "Blocks a trade the Weighted Executive Decision Engine's own weighted action advises against.",
        "Weighted Executive Decision Engine (app/weighted_decisions.py)",
    ),
    (
        "behavioral",
        "Behavioral Circuit Breaker",
        "Blocks a trade showing a corroborated revenge-trading behavioral pattern.",
        "Behavioral Circuit Breaker (app/behavioral_risk.py)",
    ),
    (
        "failure_boundary",
        "Failure Boundary Distance",
        "Blocks a trade whose risk-per-trade would exceed the company's remaining real drawdown-ceiling room.",
        "Failure Boundary formula (app/prop_firm.py, app/portfolio.py)",
    ),
]


def _evaluation_state(confirmed: int, prevented: int) -> GatekeeperControlEffectivenessState:
    if confirmed < MIN_CONTROL_SAMPLE_FOR_VERDICT:
        return "insufficient_data"
    prevented_rate = prevented / confirmed * 100.0
    if prevented_rate >= _EFFECTIVE_THRESHOLD_PCT:
        return "effective"
    if prevented_rate < _INEFFECTIVE_THRESHOLD_PCT:
        return "ineffective"
    return "mixed"


def _detect_regression(chronological_outcomes: list[bool]) -> bool:
    """`chronological_outcomes` is one True (prevented)/False (false
    positive) entry per confirmed, sole-reason rejection for this
    control, oldest first. Splits it into an earlier half and a more
    recent half — only when each half independently clears
    MIN_CONTROL_SAMPLE_FOR_VERDICT — and flags regression only when the
    earlier half read `effective` and the recent half now reads
    `ineffective`. Never flagged from a single bad outcome or from a
    sample too thin to support either half's own verdict."""
    midpoint = len(chronological_outcomes) // 2
    earlier, recent = chronological_outcomes[:midpoint], chronological_outcomes[midpoint:]
    if len(earlier) < MIN_CONTROL_SAMPLE_FOR_VERDICT or len(recent) < MIN_CONTROL_SAMPLE_FOR_VERDICT:
        return False
    earlier_state = _evaluation_state(len(earlier), sum(earlier))
    recent_state = _evaluation_state(len(recent), sum(recent))
    return earlier_state == "effective" and recent_state == "ineffective"


def compute_control_effectiveness(
    decisions: list[TradeDecision],
    gatekeeper_rejections: list[GatekeeperRejection],
) -> ControlEffectivenessSummary:
    rejection_by_id = {r.id: r for r in gatekeeper_rejections}
    verdicted = sorted(
        (d for d in decisions if d.gatekeeper_verdict is not None),
        key=lambda d: d.created_at,
    )

    records: list[ControlEffectivenessRecord] = []
    for control_id, label, purpose, owner in _CONTROL_CATALOG:
        triggered = 0
        passed = 0
        sole_reason_rejections = 0
        confirmed_prevented = 0
        confirmed_false_positive = 0
        pending_evaluation = 0
        ambiguous_attribution = 0
        last_triggered_at: str | None = None
        last_evaluated_at: str | None = None
        chronological_outcomes: list[bool] = []

        for decision in verdicted:
            verdict = decision.gatekeeper_verdict
            assert verdict is not None
            check = next((c for c in verdict.checks if c.id == control_id), None)
            if check is None:
                continue
            triggered += 1
            if check.passed:
                passed += 1
                continue
            last_triggered_at = decision.created_at
            failing_checks = [c for c in verdict.checks if not c.passed]
            if len(failing_checks) != 1:
                ambiguous_attribution += 1
                continue
            sole_reason_rejections += 1
            rejection = rejection_by_id.get(f"gkreject-{decision.id}")
            if rejection is None or rejection.outcome == "pending":
                pending_evaluation += 1
                continue
            last_evaluated_at = rejection.resolved_at or last_evaluated_at
            if rejection.outcome == "would_have_lost":
                confirmed_prevented += 1
                chronological_outcomes.append(True)
            else:
                confirmed_false_positive += 1
                chronological_outcomes.append(False)

        confirmed_total = confirmed_prevented + confirmed_false_positive
        if triggered == 0 or triggered == passed:
            state: GatekeeperControlEffectivenessState = "not_yet_tested"
        else:
            state = _evaluation_state(confirmed_total, confirmed_prevented)

        records.append(
            ControlEffectivenessRecord(
                controlId=control_id,
                controlLabel=label,
                purpose=purpose,
                owner=owner,
                triggeredCount=triggered,
                passedCount=passed,
                failedCount=triggered - passed,
                soleReasonRejectionCount=sole_reason_rejections,
                confirmedPreventedCount=confirmed_prevented,
                confirmedFalsePositiveCount=confirmed_false_positive,
                pendingEvaluationCount=pending_evaluation,
                ambiguousAttributionCount=ambiguous_attribution,
                effectivenessState=state,
                controlRegression=_detect_regression(chronological_outcomes),
                lastTriggeredAt=last_triggered_at,
                lastEvaluatedAt=last_evaluated_at,
            )
        )

    return ControlEffectivenessSummary(
        controls=records,
        totalControls=len(records),
        effectiveCount=sum(1 for r in records if r.effectiveness_state == "effective"),
        ineffectiveCount=sum(1 for r in records if r.effectiveness_state == "ineffective"),
        mixedCount=sum(1 for r in records if r.effectiveness_state == "mixed"),
        insufficientDataCount=sum(1 for r in records if r.effectiveness_state == "insufficient_data"),
        notYetTestedCount=sum(1 for r in records if r.effectiveness_state == "not_yet_tested"),
        regressedControlCount=sum(1 for r in records if r.control_regression),
        updatedAt=datetime.now(timezone.utc).isoformat(),
    )
