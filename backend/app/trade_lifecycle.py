"""app/trade_lifecycle.py — CEO directive "TradeTown — Canonical Trade
Lifecycle 1.0 / Main Equities Pipeline / Foundation for Trade
Intelligence Loop."

See `TradeLifecycleRecord`'s own docstring in app/schemas.py for the full
Phase 0 forensic-recon rationale and honesty boundary. In short: this
module assembles, it never computes. Every field on a `TradeLifecycleRecord`
is a reference to an object that already lives elsewhere in
`GameSaveState` — no new P&L, risk, or journal math happens here, and no
new persisted record is created. The one real, bounded gap this module
closes is that the identity spine app/executive.py's resolve_proposal()
already derives deterministically (decision_id/position_id/trade_id/
risk_decision_id, all suffixed off one root `TradeProposal.id`) was never
assembled into a single read for a trade still OPEN — only
app/paper_trade_journal.py did that, and only at CLOSE.
"""
from __future__ import annotations

from typing import Literal

from app.schemas import (
    CeoDecisionRecord,
    FailureClassification,
    GameSaveState,
    InstitutionalMemoryEntry,
    PaperOrder,
    PaperPosition,
    PaperTrade,
    PaperTradeJournalEntry,
    PredictionRecord,
    RiskDecision,
    TradeDecision,
    TradeLifecycleRecord,
    TradeLifecycleStage,
    TradeProposal,
)


def resolve_trade_root_id(state: GameSaveState, trade_key: str) -> str | None:
    """Resolves any real id a caller might reasonably have on hand for
    one trade — a still-open `PaperPosition.id`, a closed `PaperTrade.id`,
    a `CeoDecisionRecord.id`/`.proposal_id`, a `PaperTradeJournalEntry.id`,
    or the originating `TradeProposal.id` itself — back to that root
    `TradeProposal.id`. Never parses/strips an id's string prefix (that
    convention is real today but not a contract this module should
    depend on); every match below is a real field-equality lookup.
    Returns None when `trade_key` matches nothing — an honest "not
    found," not a guess."""
    for position in state.paper_portfolio.positions:
        if position.id == trade_key and position.proposal_id is not None:
            return position.proposal_id
    for trade in state.paper_portfolio.trade_history:
        if trade.id == trade_key and trade.proposal_id is not None:
            return trade.proposal_id
    for entry in state.paper_trade_journal:
        if entry.id == trade_key and entry.proposal_id is not None:
            return entry.proposal_id
        if entry.trade_id == trade_key and entry.proposal_id is not None:
            return entry.proposal_id
    for record in state.ceo_decisions:
        if record.id == trade_key or record.proposal_id == trade_key:
            return record.proposal_id
    for proposal in state.trade_proposals:
        if proposal.id == trade_key:
            return proposal.id
    return None


def _find_ceo_decision(state: GameSaveState, root_id: str) -> CeoDecisionRecord | None:
    return next((r for r in state.ceo_decisions if r.proposal_id == root_id), None)


def _find_decision(state: GameSaveState, ceo_decision: CeoDecisionRecord | None) -> TradeDecision | None:
    if ceo_decision is None or ceo_decision.decision_id is None:
        return None
    return next((d for d in state.decisions if d.id == ceo_decision.decision_id), None)


def _find_risk_decision(state: GameSaveState, root_id: str) -> RiskDecision | None:
    return next((r for r in state.risk_decisions if r.proposal_id == root_id), None)


def _find_position(state: GameSaveState, root_id: str) -> PaperPosition | None:
    return next((p for p in state.paper_portfolio.positions if p.proposal_id == root_id), None)


def _find_trade(state: GameSaveState, root_id: str) -> PaperTrade | None:
    return next((t for t in state.paper_portfolio.trade_history if t.proposal_id == root_id), None)


def _find_journal_entry(state: GameSaveState, trade: PaperTrade | None) -> PaperTradeJournalEntry | None:
    if trade is None:
        return None
    return next((e for e in state.paper_trade_journal if e.trade_id == trade.id), None)


def _find_prediction(state: GameSaveState, decision: TradeDecision | None) -> PredictionRecord | None:
    if decision is None:
        return None
    return next((p for p in state.prediction_records if p.decision_id == decision.id), None)


def _find_failure(state: GameSaveState, decision: TradeDecision | None) -> FailureClassification | None:
    if decision is None:
        return None
    return next((f for f in state.failure_classifications if f.decision_id == decision.id), None)


def _find_institutional_memory(
    state: GameSaveState, prediction: PredictionRecord | None, failure: FailureClassification | None
) -> list[InstitutionalMemoryEntry]:
    """`InstitutionalMemoryEntry.event_ref` cites the id of the source
    record it was promoted from (see app/institutional_memory.py's
    promote_prediction_outcome/promote_failure_classification) — real,
    but indirect, so this only matches when this trade actually produced
    a graded prediction and/or a filed failure classification."""
    source_ids = {rec.id for rec in (prediction, failure) if rec is not None}
    if not source_ids:
        return []
    return [entry for entry in state.institutional_memory if entry.event_ref in source_ids]


def _linked_orders(state: GameSaveState, position: PaperPosition | None) -> list[PaperOrder]:
    if position is None:
        return []
    return [o for o in state.paper_portfolio.orders if o.linked_position_id == position.id]


def _build_stages(
    *,
    proposal: TradeProposal | None,
    ceo_decision: CeoDecisionRecord | None,
    decision: TradeDecision | None,
    risk_decision: RiskDecision | None,
    position: PaperPosition | None,
    trade: PaperTrade | None,
    linked_orders: list[PaperOrder],
    journal_entry: PaperTradeJournalEntry | None,
    prediction: PredictionRecord | None,
    failure: FailureClassification | None,
    institutional_memory: list[InstitutionalMemoryEntry],
) -> list[TradeLifecycleStage]:
    stages: list[TradeLifecycleStage] = []

    stages.append(
        TradeLifecycleStage(
            stage="signal",
            label="Signal",
            available=proposal is not None or ceo_decision is not None,
            occurredAt=proposal.created_at if proposal is not None else None,
            refId=proposal.id if proposal is not None else None,
            note=(
                "Real: six AnalystVote reads plus app/confidence.py's compute_confidence() "
                "produced this proposal. No durable id links back to the specific ResearchItem "
                "that seeded it — research.py's rotation pool is not append-only and TradeProposal "
                "carries no research_item_id — traceable only via research_summary/category text."
                if (proposal is not None or ceo_decision is not None)
                else "The originating TradeProposal has been resolved and removed from state (real, "
                "expected — proposals are not retained after a decision); no ResearchItem link ever existed."
            ),
        )
    )

    stages.append(
        TradeLifecycleStage(
            stage="decision",
            label="Decision",
            available=ceo_decision is not None,
            occurredAt=ceo_decision.resolved_at if ceo_decision is not None else None,
            refId=ceo_decision.id if ceo_decision is not None else None,
            note=(
                f"Real CEO/auto/delegated decision (resolvedBy={ceo_decision.resolved_by!r}) via "
                "app/state.py's submit_ceo_decision -> app/executive.py's resolve_proposal."
                if ceo_decision is not None
                else "No CeoDecisionRecord found for this root id."
            ),
        )
    )

    strategy_available = ceo_decision is not None and ceo_decision.strategy_id is not None
    stages.append(
        TradeLifecycleStage(
            stage="strategy_identity",
            label="Strategy Identity",
            available=strategy_available,
            occurredAt=ceo_decision.resolved_at if strategy_available and ceo_decision is not None else None,
            refId=ceo_decision.strategy_id if strategy_available and ceo_decision is not None else None,
            note=(
                f"Real, CEO-selected Strategy (compiledDefinitionId={ceo_decision.strategy_compiled_definition_id!r}, "
                f"version={ceo_decision.strategy_compiled_definition_version!r}, snapshotted at decision time — "
                "never re-derived later)."
                if strategy_available and ceo_decision is not None
                else "The CEO did not attribute a Strategy Lab strategy to this decision — the honest majority "
                "case, never inferred or backfilled (see CeoDecisionRecord.strategy_id's own docstring)."
            ),
        )
    )

    gatekeeper = decision.gatekeeper_verdict if decision is not None else None
    risk_note = (
        "Enforced pre-order: app/gatekeeper.py's evaluate_gatekeeper() and app/position_sizing.py's "
        "build_position_sizing() both ran before this trade could open. Advisory/post-hoc only: "
        "RiskContract dynamic scaling (app/risk_contract.py) is computed and recorded on the linked "
        "RiskDecision AFTER the order already executed — it names which contract 'governed' the trade, "
        "it does not gate it."
    )
    stages.append(
        TradeLifecycleStage(
            stage="risk_review",
            label="Risk Review",
            available=decision is not None,
            occurredAt=decision.created_at if decision is not None else None,
            refId=risk_decision.id if risk_decision is not None else (gatekeeper.checks[0].label if gatekeeper and gatekeeper.checks else None),
            note=risk_note if decision is not None else "No TradeDecision found for this root id.",
        )
    )

    order_approved = decision is not None and decision.order_id is not None
    stages.append(
        TradeLifecycleStage(
            stage="order_submitted",
            label="Order Accepted / Rejected",
            available=decision is not None,
            occurredAt=decision.created_at if decision is not None else None,
            refId=decision.order_id if decision is not None else None,
            note=(
                "Approved — Gatekeeper verdict passed and the position opened."
                if order_approved
                else (
                    f"Rejected: {gatekeeper.summary}" if gatekeeper is not None and not gatekeeper.approved
                    else "No TradeDecision found for this root id." if decision is None
                    else "CEO chose WAIT — no order was ever submitted."
                )
            ),
        )
    )

    fill_price = position.entry_price if position is not None else (trade.entry_price if trade is not None else None)
    stages.append(
        TradeLifecycleStage(
            stage="fill",
            label="Fill",
            available=fill_price is not None,
            occurredAt=position.opened_at if position is not None else (trade.opened_at if trade is not None else None),
            refId=None,
            note=(
                "Not a distinct object from Order/Position for the CEO's own buy/sell path — "
                "app/executive.py's resolve_proposal() applies real slippage "
                "(app/execution_quality.py) and calls open_position() in the same step; no queued "
                "order-then-fill gap exists for entries in this pipeline (only the protective "
                "stop/target exit legs are real, separately-filled PaperOrder objects)."
                if fill_price is not None
                else "No fill — no order was ever accepted."
            ),
        )
    )

    stages.append(
        TradeLifecycleStage(
            stage="position_open",
            label="Position Open",
            available=position is not None or trade is not None,
            occurredAt=position.opened_at if position is not None else (trade.opened_at if trade is not None else None),
            refId=position.id if position is not None else (trade.id if trade is not None else None),
            note=(
                "Real PaperPosition (app/portfolio.py's open_position())."
                if position is not None
                else ("Position has since closed — see the CLOSED stage." if trade is not None else "No position was ever opened.")
            ),
        )
    )

    stages.append(
        TradeLifecycleStage(
            stage="position_active",
            label="Position Active",
            available=position is not None,
            occurredAt=None,
            refId=position.id if position is not None else None,
            note=(
                f"Currently open. Live MAE/MFE watermark: {position.mae_pct:.2f}% / {position.mfe_pct:.2f}%. "
                f"{len([o for o in linked_orders if o.status == 'open'])} linked protective order(s) still live."
                if position is not None
                else "Not currently open (either never opened, or already closed)."
            ),
        )
    )

    exit_available = trade is not None
    exit_note = "No exit yet — position is still open." if trade is None else (
        f"Exit reason: {trade.reason!r}. "
        + (
            "A real, tick-evaluated stop/target PaperOrder governed this exit (see linked_orders)."
            if any(o.status == "filled" for o in linked_orders)
            else "No linked protective order was found filled at close — this exit came from a "
            "direct close_position() call (CEO manual/day-end flatten, or app/paper_trading.py's "
            "hold-duration close), not a distinct EXIT_ORDER object."
        )
    )
    stages.append(
        TradeLifecycleStage(
            stage="exit",
            label="Exit Intent / Exit Order",
            available=exit_available,
            occurredAt=trade.closed_at if trade is not None else None,
            refId=next((o.id for o in linked_orders if o.status == "filled"), None),
            note=exit_note,
        )
    )

    stages.append(
        TradeLifecycleStage(
            stage="closed",
            label="Closed",
            available=trade is not None,
            occurredAt=trade.closed_at if trade is not None else None,
            refId=trade.id if trade is not None else None,
            note=(
                f"Realized P&L: {trade.pnl:.2f} ({trade.pnl_pct:.2f}%), net of transaction cost and slippage. "
                "No partial exits exist anywhere in this pipeline — a trade closes in full or not at all."
                if trade is not None
                else "Not yet closed."
            ),
        )
    )

    outcome_available = journal_entry is not None or prediction is not None or failure is not None
    outcome_parts = []
    if journal_entry is not None:
        outcome_parts.append(f"journaled ({journal_entry.id})")
    if prediction is not None:
        outcome_parts.append(f"prediction graded {prediction.outcome!r}")
    if failure is not None:
        outcome_parts.append(f"failure classified {failure.reason!r}")
    stages.append(
        TradeLifecycleStage(
            stage="outcome_recorded",
            label="Outcome Recorded",
            available=outcome_available,
            occurredAt=journal_entry.created_at if journal_entry is not None else None,
            refId=journal_entry.id if journal_entry is not None else None,
            note=("; ".join(outcome_parts) if outcome_parts else "No journal/prediction/failure record found yet.")
            + (
                ""
                if prediction is None
                else "" if prediction.outcome != "pending" else " — prediction still pending real resolution."
            ),
        )
    )

    stages.append(
        TradeLifecycleStage(
            stage="trade_finalized",
            label="Trade Finalized (Institutional Memory)",
            available=bool(institutional_memory),
            occurredAt=institutional_memory[0].created_at if institutional_memory else None,
            refId=institutional_memory[0].id if institutional_memory else None,
            note=(
                f"{len(institutional_memory)} durable institutional-memory entr{'y' if len(institutional_memory) == 1 else 'ies'} "
                "promoted from this trade's real, evidence-gated outcome (app/institutional_memory.py)."
                if institutional_memory
                else "This trade's outcome did not clear any real promotion gate (see app/institutional_memory.py's "
                "should_promote_* predicates) — the honest majority case, never forced."
            ),
        )
    )

    return stages


def build_trade_lifecycle_record(state: GameSaveState, trade_key: str) -> TradeLifecycleRecord | None:
    """Assembles one real trade's full lifecycle from `trade_key` (a
    position id, a closed trade id, a journal entry/trade id, a CEO
    decision id, or the originating proposal id — see
    resolve_trade_root_id()). Returns None only when `trade_key` matches
    nothing real."""
    root_id = resolve_trade_root_id(state, trade_key)
    if root_id is None:
        return None

    proposal = next((p for p in state.trade_proposals if p.id == root_id), None)
    ceo_decision = _find_ceo_decision(state, root_id)
    decision = _find_decision(state, ceo_decision)
    risk_decision = _find_risk_decision(state, root_id)
    position = _find_position(state, root_id)
    trade = _find_trade(state, root_id)
    linked_orders = _linked_orders(state, position)
    if position is None and trade is not None:
        # Position has closed — its own linked orders no longer resolve
        # by position.id (the position object is gone), but PaperOrder
        # rows are never deleted, only status-transitioned, so the same
        # position_id this trade carries via app/portfolio.py's
        # `id=f"trade-{position_id}"` convention still matches real rows.
        closed_position_id = trade.id.removeprefix("trade-")
        linked_orders = [o for o in state.paper_portfolio.orders if o.linked_position_id == closed_position_id]
    journal_entry = _find_journal_entry(state, trade)
    prediction = _find_prediction(state, decision)
    failure = _find_failure(state, decision)
    institutional_memory = _find_institutional_memory(state, prediction, failure)

    symbol = (
        trade.symbol if trade is not None
        else position.symbol if position is not None
        else ceo_decision.symbol if ceo_decision is not None
        else proposal.symbol if proposal is not None
        else "UNKNOWN"
    )

    status: Literal["pending", "rejected", "open", "closed"]
    if trade is not None:
        status = "closed"
    elif position is not None:
        status = "open"
    elif decision is not None and decision.order_id is None:
        status = "rejected"
    else:
        status = "pending"

    stages = _build_stages(
        proposal=proposal,
        ceo_decision=ceo_decision,
        decision=decision,
        risk_decision=risk_decision,
        position=position,
        trade=trade,
        linked_orders=linked_orders,
        journal_entry=journal_entry,
        prediction=prediction,
        failure=failure,
        institutional_memory=institutional_memory,
    )

    return TradeLifecycleRecord(
        tradeRootId=root_id,
        symbol=symbol,
        status=status,
        stages=stages,
        proposal=proposal,
        decision=decision,
        ceoDecision=ceo_decision,
        riskDecision=risk_decision,
        position=position,
        trade=trade,
        linkedOrders=linked_orders,
        journalEntry=journal_entry,
        prediction=prediction,
        failure=failure,
        institutionalMemory=institutional_memory,
    )
