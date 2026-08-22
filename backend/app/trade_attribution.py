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
    CompiledStrategyDefinition,
    PaperTrade,
    TradeAttributionRecord,
    TradeAttributionSummary,
    TradeDecision,
    TradeStrategyProvenanceState,
    TradeStrategyRuleSnapshot,
)
from app.strategy_registry import get_compiled_definition_version

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


def _signal_price(fill_price: float, slippage_bps: float, *, action_side: str) -> float:
    """CEO directive "Complete Trade Provenance," Part 15 — the exact
    algebraic inverse of app/execution_quality.py's apply_slippage():
    the real pre-slippage price that, once that function's own real,
    always-adverse formula was applied, produced this real fill. Never
    a modeled/guessed price — a deterministic reversal of a real,
    already-applied calculation."""
    if slippage_bps == 0 or fill_price <= 0:
        return fill_price
    slippage_factor = slippage_bps / 10_000.0
    return fill_price / (1 + slippage_factor) if action_side == "buy" else fill_price / (1 - slippage_factor)


def _execution_attribution(trade: PaperTrade) -> tuple[float, float, float]:
    """Returns (price_movement_pnl, slippage_cost_usd,
    execution_cost_total_usd). Reconstructs the real pre-slippage
    "signal" entry/exit prices via `_signal_price()` above, using this
    trade's own real `side` to determine which real action
    (buy-to-open/sell-to-close for a long, sell-to-open/buy-to-close for
    a short) each fill actually was — then applies app/portfolio.py's
    own `close_position()` P&L formula
    `(exit - entry) * quantity * direction` to those signal prices
    instead of the real (post-slippage) fill prices, never a second,
    diverging P&L formula. `slippage_cost_usd` is always >= 0 (real
    slippage is always adverse to the trader, by
    execution_quality.py's own design) — a real, checkable property,
    not assumed. The three real numbers this function returns always
    reconcile exactly: price_movement_pnl - execution_cost_total_usd ==
    trade.pnl (within floating-point rounding)."""
    direction = 1 if trade.side == "buy" else -1
    entry_action = "buy" if trade.side == "buy" else "sell"
    exit_action = "sell" if trade.side == "buy" else "buy"
    signal_entry = _signal_price(trade.entry_price, trade.entry_slippage_bps, action_side=entry_action)
    signal_exit = _signal_price(trade.exit_price, trade.exit_slippage_bps, action_side=exit_action)
    # Unrounded intermediates throughout, rounded only once each at the
    # very end — avoids compounding rounding error into a spurious
    # negative (or "-0.0") slippage_cost_usd, which the max(0.0, ...)
    # below then also guards against as a final, disclosed floor: the
    # true mathematical value is always >= 0 (slippage is always
    # adverse to the trader, by execution_quality.py's own design), so
    # a negative result here could only ever be floating-point noise,
    # never real information worth preserving.
    price_movement_pnl_raw = (signal_exit - signal_entry) * trade.quantity * direction
    fill_pnl = (trade.exit_price - trade.entry_price) * trade.quantity * direction
    price_movement_pnl = round(price_movement_pnl_raw, 2)
    slippage_cost_usd = round(max(0.0, price_movement_pnl_raw - fill_pnl), 2)
    execution_cost_total_usd = round(slippage_cost_usd + trade.transaction_cost_usd, 2)
    return price_movement_pnl, slippage_cost_usd, execution_cost_total_usd


def compute_trade_attribution(
    trade: PaperTrade,
    decisions: list[TradeDecision],
    ceo_decisions: list[CeoDecisionRecord],
) -> TradeAttributionRecord:
    price_movement_pnl, slippage_cost_usd, execution_cost_total_usd = _execution_attribution(trade)
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
            strategyId=None,
            strategyProvenanceState="unavailable",
            strategyCompiledDefinitionId=None,
            strategyCompiledDefinitionVersion=None,
            priceMovementPnl=price_movement_pnl,
            slippageCostUsd=slippage_cost_usd,
            executionCostTotalUsd=execution_cost_total_usd,
        )

    ceo_decision = next((c for c in ceo_decisions if c.decision_id == decision.id), None)
    if ceo_decision is None:
        strategy_provenance_state: TradeStrategyProvenanceState = "unavailable"
    elif ceo_decision.strategy_id is not None:
        strategy_provenance_state = "known"
    else:
        strategy_provenance_state = "unknown"
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
        strategyId=ceo_decision.strategy_id if ceo_decision else None,
        strategyProvenanceState=strategy_provenance_state,
        strategyCompiledDefinitionId=ceo_decision.strategy_compiled_definition_id if ceo_decision else None,
        strategyCompiledDefinitionVersion=ceo_decision.strategy_compiled_definition_version if ceo_decision else None,
        entrySlippageBps=trade.entry_slippage_bps,
        exitSlippageBps=trade.exit_slippage_bps,
        transactionCostUsd=trade.transaction_cost_usd,
        pnl=trade.pnl,
        pnlPct=trade.pnl_pct,
        evidenceState="full_evidence",
        creditSplitNote=CREDIT_SPLIT_NOTE,
        priceMovementPnl=price_movement_pnl,
        slippageCostUsd=slippage_cost_usd,
        executionCostTotalUsd=execution_cost_total_usd,
    )


def compute_trade_attribution_history(
    trade_history: list[PaperTrade],
    decisions: list[TradeDecision],
    ceo_decisions: list[CeoDecisionRecord],
) -> TradeAttributionSummary:
    records = [compute_trade_attribution(trade, decisions, ceo_decisions) for trade in trade_history]
    return TradeAttributionSummary(records=records, updatedAt=_now_iso())


def resolve_trade_strategy_rule_snapshot(
    trade_id: str,
    trade_history: list[PaperTrade],
    decisions: list[TradeDecision],
    ceo_decisions: list[CeoDecisionRecord],
    compiled_strategy_versions: dict[str, list[CompiledStrategyDefinition]],
) -> TradeStrategyRuleSnapshot | None:
    """CEO directive "Complete Trade Provenance," Part 2. `None` only
    when `trade_id` doesn't match any real trade in `trade_history` (the
    one genuinely absent case — every other outcome, including "this
    trade has no strategy attribution at all," is a real
    `TradeStrategyRuleSnapshot` with `compiledDefinition=None`, never a
    bare `None` that could be mistaken for "trade not found")."""
    trade = next((t for t in trade_history if t.id == trade_id), None)
    if trade is None:
        return None
    attribution = compute_trade_attribution(trade, decisions, ceo_decisions)
    compiled_definition = None
    if attribution.strategy_compiled_definition_id is not None and attribution.strategy_compiled_definition_version is not None:
        compiled_definition = get_compiled_definition_version(
            compiled_strategy_versions,
            attribution.strategy_compiled_definition_id,
            attribution.strategy_compiled_definition_version,
        )
    return TradeStrategyRuleSnapshot(
        tradeId=trade_id,
        strategyId=attribution.strategy_id,
        strategyProvenanceState=attribution.strategy_provenance_state,
        compiledDefinition=compiled_definition,
    )
