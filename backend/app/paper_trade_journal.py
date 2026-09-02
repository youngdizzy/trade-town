"""app/paper_trade_journal.py — CEO directive "TradeTown — Persisted Risk
Contract + Dynamic Risk Scaling, then Paper-Trade Journal + Drift
Detection + Strategy Health State Machine" (second increment).

See `PaperTradeJournalEntry`'s own docstring in app/schemas.py for the
full forensic-recon rationale: this is a thin, joined identity record
plus a one-time snapshot of the essential facts, never a re-declaration
of `PaperTrade`/`CeoDecisionRecord`/`RiskDecision`'s own already-real
fields.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import CeoDecisionRecord, PaperTrade, PaperTradeJournalEntry, PaperTradeJournalNote, RiskDecision


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_journal_entry(
    trade: PaperTrade,
    *,
    ceo_decision: CeoDecisionRecord | None,
    risk_decision: RiskDecision | None,
) -> PaperTradeJournalEntry:
    """One real journal entry for one just-closed `PaperTrade`. `trade`
    must already carry its real `decision_id`/`proposal_id` (see
    app/journal.py's `stamp_journal_entry()`, which always runs before
    this in app/nexus.py's tick()). `ceo_decision` is the matching
    `CeoDecisionRecord` (by `decision_id`), if any — supplies strategy
    identity/version and the real decision-time market snapshot.
    `risk_decision` is the matching `RiskDecision` (by `decision_id`),
    if any — supplies `risk_decision_id` for traceability; its own
    `scaling`/`approvedQuantity` are never copied here, only referenced,
    since `RiskDecision` is itself already a permanent record."""
    return PaperTradeJournalEntry(
        id=f"journal-{trade.id}",
        createdAt=_now_iso(),
        tradeId=trade.id,
        decisionId=trade.decision_id,
        proposalId=trade.proposal_id,
        riskDecisionId=risk_decision.id if risk_decision is not None else None,
        strategyId=ceo_decision.strategy_id if ceo_decision is not None else None,
        strategyCompiledDefinitionId=ceo_decision.strategy_compiled_definition_id if ceo_decision is not None else None,
        strategyCompiledDefinitionVersion=ceo_decision.strategy_compiled_definition_version if ceo_decision is not None else None,
        resolvedBy=ceo_decision.resolved_by if ceo_decision is not None else None,
        symbol=trade.symbol,
        side=trade.side,
        quantity=trade.quantity,
        entryPrice=trade.entry_price,
        exitPrice=trade.exit_price,
        stopPrice=trade.stop_price,
        targetPrice=trade.target_price,
        pnl=trade.pnl,
        pnlPct=trade.pnl_pct,
        maePct=trade.mae_pct,
        mfePct=trade.mfe_pct,
        durationMinutes=trade.duration_minutes,
        openedAt=trade.opened_at,
        closedAt=trade.closed_at,
        decisionMarketRegime=ceo_decision.decision_market_regime if ceo_decision is not None else None,
        decisionSession=ceo_decision.decision_session if ceo_decision is not None else None,
    )


def add_ceo_note(entry: PaperTradeJournalEntry, *, text: str) -> PaperTradeJournalEntry:
    """Appends one real CEO-authored note — never edits or removes an
    existing one (see the schema's own "never silently rewrite history"
    note)."""
    note = PaperTradeJournalNote(id=f"note-{entry.id}-{len(entry.ceo_notes) + 1}", createdAt=_now_iso(), text=text)
    return entry.model_copy(update={"ceo_notes": [*entry.ceo_notes, note]})


__all__ = ["build_journal_entry", "add_ceo_note"]
