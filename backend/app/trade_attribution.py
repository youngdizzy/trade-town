"""CEO directive "Next Phase: Professional Trading Firm Intelligence,"
Phase 1 — Symbol -> Agent Attribution.

RESEARCH FIRST (per the directive's own mandatory rule): can TradeTown
currently answer "which agent(s) were actually responsible for this
trade, and how much P&L should each receive credit for?" A full audit
of every trade/decision/agent-vote data structure in this codebase
found real, rich, PERMANENTLY-STORED per-role evidence
(`TradeDecision.votes` — one real vote per one of the six real analyst
seats app/executive.py's Executive Voting already built, preserved
forever, not just at proposal time) — but confirmed, by grep, zero
existing P&L-credit-splitting methodology anywhere. The directive is
explicit that this module must NOT invent one ("do not arbitrarily
assign 100% credit to the agent that clicked BUY/SELL... if a CEO
credit-split rule is required, surface that explicitly instead of
silently inventing one").

WHAT THIS MODULE DOES INSTEAD, per the directive's own fallback
instruction ("preserve the original attribution evidence so that
attribution can be audited later"): joins three real, already-permanent
records per trade — `TradeDecision.votes` (who advised what, and via
the fixed `ROLE_TO_AGENT` mapping, in what functional role: Research/
News=Scout, Market-Technical=Echo, Macro=Nova, Risk=Sentinel,
Sentiment=Pulse, Execution-Synthesis=Atlas), `CeoDecisionRecord` (the
real CEO-override provenance), and `PaperTrade` (the real execution
detail — including Priority 1's real slippage — and final P&L) — into
one auditable per-trade record. `agreed_with_side_traded` is a real,
checkable fact (did this agent's vote match the side that actually got
traded), not a credit weight. No numeric P&L split is computed,
implied, or stored anywhere in this record; `credit_split_note` says so
explicitly on every record, rather than a silent omission a future
reader could mistake for "not yet gotten to."

A DISCLOSED LIMIT: `decisions` is capped at `MAX_DECISIONS` (200) and
`trade_history` at `MAX_TRADE_HISTORY` (50) — the decisions cap is
generously larger, so in practice every trade still in history has its
originating decision still on record, but a save carried forward with
an unusual decision/trade ratio could see `no_decision_on_record` for a
trade whose real decision was simply evicted first, not one that never
existed. This module makes no attempt to distinguish the two cases
(neither can be told apart from what's left in memory) and reports both
identically, honestly, as "no decision on record" rather than guessing.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.executive import ROLE_TO_AGENT
from app.schemas import (
    AgentContributionRead,
    AnalystRole,
    CeoDecisionRecord,
    PaperTrade,
    TradeAttributionRecord,
    TradeAttributionSummary,
    TradeDecision,
)

CREDIT_SPLIT_NOTE = (
    "TradeTown records real per-agent contribution evidence (who advised what, and whether the final trade "
    "agreed with them) for every trade with a matched decision. It does not assign a numeric P&L credit split "
    "across agents — no CEO-authorized methodology for doing so exists in this codebase, and inventing one "
    "unilaterally would be a fabricated convention, not a real metric. A CEO decision on a credit-split rule "
    "would be required before that number could honestly exist."
)

_AGENT_TO_ROLE: dict[str, AnalystRole] = {agent_id: role for role, agent_id in ROLE_TO_AGENT.items()}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _contributions(decision: TradeDecision, trade: PaperTrade) -> list[AgentContributionRead]:
    reads: list[AgentContributionRead] = []
    for vote in decision.votes:
        role = _AGENT_TO_ROLE.get(vote.agent_id)
        if role is None:
            # A vote from an agent outside the six real analyst seats
            # (never happens today — every TradeDecision.votes entry
            # comes from generate_analyst_votes()'s fixed roster — but
            # skipped rather than guessed at if this codebase's roster
            # ever changes without this module being updated too).
            continue
        traded_side = "buy" if trade.side == "buy" else "sell"
        agreed = (vote.choice == traded_side) if vote.choice in ("buy", "sell") else False
        reads.append(
            AgentContributionRead(
                agentId=vote.agent_id,
                role=role,
                choice=vote.choice,
                reason=vote.reason,
                agreedWithSideTraded=agreed,
            )
        )
    return reads


def compute_trade_attribution(
    trade: PaperTrade,
    decisions: list[TradeDecision],
    ceo_decisions: list[CeoDecisionRecord],
) -> TradeAttributionRecord:
    decision = next((d for d in decisions if d.id == trade.decision_id), None) if trade.decision_id else None
    if decision is None:
        return TradeAttributionRecord(
            tradeId=trade.id,
            decisionId=None,
            symbol=trade.symbol,
            contributions=[],
            supportingAgents=[],
            opposingAgents=[],
            ceoChoice=None,
            ceoOverrodeTheDesk=None,
            gatekeeperApproved=None,
            entrySlippageBps=trade.entry_slippage_bps,
            exitSlippageBps=trade.exit_slippage_bps,
            transactionCostUsd=trade.transaction_cost_usd,
            pnl=trade.pnl,
            pnlPct=trade.pnl_pct,
            evidenceState="no_decision_on_record",
            creditSplitNote=CREDIT_SPLIT_NOTE,
        )

    ceo_decision = next((c for c in ceo_decisions if c.decision_id == decision.id), None)
    return TradeAttributionRecord(
        tradeId=trade.id,
        decisionId=decision.id,
        symbol=trade.symbol,
        contributions=_contributions(decision, trade),
        supportingAgents=decision.supporting_agents,
        opposingAgents=decision.opposing_agents,
        ceoChoice=ceo_decision.ceo_decision if ceo_decision else None,
        ceoOverrodeTheDesk=(not ceo_decision.agreed_with_ai) if ceo_decision else None,
        gatekeeperApproved=decision.gatekeeper_verdict.approved if decision.gatekeeper_verdict else None,
        entrySlippageBps=trade.entry_slippage_bps,
        exitSlippageBps=trade.exit_slippage_bps,
        transactionCostUsd=trade.transaction_cost_usd,
        pnl=trade.pnl,
        pnlPct=trade.pnl_pct,
        evidenceState="full_evidence",
        creditSplitNote=CREDIT_SPLIT_NOTE,
    )


def compute_trade_attribution_history(
    trade_history: list[PaperTrade],
    decisions: list[TradeDecision],
    ceo_decisions: list[CeoDecisionRecord],
) -> TradeAttributionSummary:
    records = [compute_trade_attribution(trade, decisions, ceo_decisions) for trade in trade_history]
    return TradeAttributionSummary(records=records, updatedAt=_now_iso())
