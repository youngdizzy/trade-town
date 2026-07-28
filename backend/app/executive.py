"""ExecutiveVoting — Feature 12, "the player is the CEO of TradeTown."

Every research candidate that crosses the trade-confidence threshold
used to execute automatically (app/decision.py's old auto-approve path).
Now it becomes a TradeProposal and waits for the CEO (the player) to
decide. Six analyst seats cast independent votes, each grounded in real
data already produced elsewhere in the sim — never a bare opinion with
no backing:

  technical  (Echo)     - real trend/volatility read on the symbol's
                           own candles (the same computation Signal
                           Calibration's level 3 and Player vs AI's
                           regime read already use — see market_data.py).
  news       (Scout)     - reuses app/voting.py's existing researcher-
                           vote shape (confidence-driven, deterministic-
                           but-varied, the same convention every other
                           researcher vote in this codebase already
                           follows).
  macro      (Nova)      - same researcher-vote shape.
  risk       (Sentinel)  - the real RiskWarning app/risk_engine.py's
                           evaluate_sentinel_risk() already computes.
  sentiment  (Pulse)     - the real ScannerAlert app/scanner.py already
                           detects for the symbol, if any.
  execution  (Atlas)     - not an independent seventh opinion: Atlas's
                           vote *is* the desk's synthesis (majority of
                           the other five), framed as "Atlas agrees with
                           the desk" rather than inventing a sixth real
                           signal that doesn't exist.

The CEO's own choice (buy/sell/wait) — not any vote tally — is what
actually happens: buy opens a real long, sell opens a real short
(app/portfolio.py's open_position() already supports both sides
correctly, see its `direction` math), wait does nothing. Either way a
permanent TradeDecision is still recorded (see resolve_proposal), so
every existing consumer of TradeDecision (DecisionsPanel, DecisionDetail,
Player vs AI) keeps working unchanged — only *who* makes the call, and
*when*, has changed.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.market_data import Candle as ProviderCandle
from app.market_data import MarketDataProvider
from app.market_data import trend_pct, volatility_pct
from app.portfolio import open_position
from app.risk_engine import recommended_quantity
from app.schemas import (
    AgentId,
    AgentVote,
    AnalystChoice,
    AnalystRole,
    AnalystVote,
    CeoDecisionRecord,
    NewsItem,
    PaperPortfolio,
    PaperTrade,
    RiskLimits,
    RiskWarning,
    ResearchItem,
    ScannerAlert,
    TradeDecision,
    TradeProposal,
)
from app.voting import researcher_vote

ROLE_TO_AGENT: dict[AnalystRole, AgentId] = {
    "technical": "echo",
    "news": "scout",
    "macro": "nova",
    "risk": "sentinel",
    "sentiment": "pulse",
    "execution": "atlas",
}

MAX_PENDING_PROPOSALS = 5
MAX_CEO_DECISIONS = 200
PROPOSAL_TIMEFRAME = "1h"
PROPOSAL_CANDLE_COUNT = 30
# A proposal the CEO never acts on doesn't sit forever — after this many
# in-game minutes it's auto-resolved as "wait" (see expire_stale_proposals),
# freeing its slot for a fresh opportunity rather than blocking the desk
# indefinitely on one stale candidate.
PROPOSAL_EXPIRY_SIM_MINUTES = 3 * 1440  # 3 in-game days


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _vote_choice_to_analyst_choice(choice: str) -> AnalystChoice:
    """AgentVote.choice (buy/sell/hold/risk_too_high/position_too_large)
    -> AnalystChoice (buy/sell/wait). A hard-reject risk vote reads as
    "wait" here — it's advisory in this system (the CEO can still
    override it), not an automatic veto the way it was in the old
    fully-automatic pipeline."""
    if choice == "buy":
        return "buy"
    if choice == "sell":
        return "sell"
    return "wait"


def _agent_vote_to_analyst_vote(role: AnalystRole, vote: AgentVote, evidence: list[str]) -> AnalystVote:
    return AnalystVote(
        role=role,
        agentId=vote.agent_id,
        choice=_vote_choice_to_analyst_choice(vote.choice),
        reasoning=vote.reason,
        evidence=evidence,
    )


def _technical_vote(item: ResearchItem, candles: list[ProviderCandle]) -> AnalystVote:
    trend = trend_pct(candles)
    volatility = volatility_pct(candles)
    if abs(trend) <= 2 * max(volatility, 0.1):
        choice: AnalystChoice = "wait"
        reasoning = f"{item.symbol} is ranging ({trend:+.1f}% vs {volatility:.1f}% volatility) — no clear technical edge yet."
    elif trend > 0:
        choice = "buy"
        reasoning = f"{item.symbol} is in a real uptrend ({trend:+.1f}% over the sample) relative to its own volatility."
    else:
        choice = "sell"
        reasoning = f"{item.symbol} is in a real downtrend ({trend:+.1f}% over the sample) relative to its own volatility."
    return AnalystVote(
        role="technical",
        agentId="echo",
        choice=choice,
        reasoning=reasoning,
        evidence=[f"Trend: {trend:+.1f}% over the last {PROPOSAL_CANDLE_COUNT} {PROPOSAL_TIMEFRAME} bars.", f"Volatility: {volatility:.1f}% average bar range."],
    )


def _sentiment_vote(symbol: str, alerts: list[ScannerAlert]) -> AnalystVote:
    recent = [a for a in alerts if a.symbol == symbol]
    if not recent:
        return AnalystVote(
            role="sentiment",
            agentId="pulse",
            choice="wait",
            reasoning=f"No unusual volume or price activity detected on {symbol} recently.",
            evidence=["No active scanner alerts for this symbol."],
        )
    alert = recent[-1]
    choice: AnalystChoice
    if alert.alert_type in ("gap_up", "breakout"):
        choice = "buy"
    elif alert.alert_type == "gap_down":
        choice = "sell"
    else:  # volume_spike / high_volatility — elevated activity, direction unclear
        choice = "wait"
    return AnalystVote(
        role="sentiment",
        agentId="pulse",
        choice=choice,
        reasoning=alert.message,
        evidence=[f"Scanner alert: {alert.alert_type.replace('_', ' ')} — {alert.message}"],
    )


def _risk_vote(symbol: str, sentinel_warning: RiskWarning | None, guardian_warning: RiskWarning | None) -> AnalystVote:
    warning = sentinel_warning or guardian_warning
    if warning is None:
        return AnalystVote(
            role="risk",
            agentId="sentinel",
            choice="buy",
            reasoning=f"{symbol} is within all configured risk limits.",
            evidence=["No active Sentinel or Guardian warning for this symbol."],
        )
    return AnalystVote(
        role="risk",
        agentId="sentinel",
        choice="wait",
        reasoning=warning.message,
        evidence=[warning.message],
    )


def _execution_vote(votes: list[AnalystVote]) -> tuple[AnalystVote, AnalystChoice]:
    """Atlas's vote is the desk's synthesis, not a fabricated sixth
    signal — majority of the other five, tie-breaking toward "wait"
    (the conservative default, same reasoning app/decision.py's old
    majority rule already used)."""
    tally: dict[AnalystChoice, int] = {"buy": 0, "sell": 0, "wait": 0}
    for v in votes:
        tally[v.choice] += 1
    overall: AnalystChoice
    if tally["buy"] > tally["sell"] and tally["buy"] > tally["wait"]:
        overall = "buy"
    elif tally["sell"] > tally["buy"] and tally["sell"] > tally["wait"]:
        overall = "sell"
    else:
        overall = "wait"
    summary = f"{tally['buy']} buy, {tally['sell']} sell, {tally['wait']} wait among the desk."
    return (
        AnalystVote(
            role="execution",
            agentId="atlas",
            choice=overall,
            reasoning=f"Atlas synthesizes the desk's view: {summary}",
            evidence=[summary],
        ),
        overall,
    )


def generate_analyst_votes(
    item: ResearchItem,
    *,
    news: list[NewsItem],
    scanner_alerts: list[ScannerAlert],
    sentinel_warning: RiskWarning | None,
    guardian_warning: RiskWarning | None,
    provider: MarketDataProvider,
) -> tuple[list[AnalystVote], AnalystChoice]:
    symbol = item.symbol
    assert symbol is not None

    candles = provider.get_candles(symbol, PROPOSAL_TIMEFRAME, PROPOSAL_CANDLE_COUNT)
    technical = _technical_vote(item, candles)

    news_agent_vote = researcher_vote("scout", originated=(item.assigned_agent == "scout"), confidence=item.confidence, symbol=symbol)
    mentions = [n.headline for n in news if symbol in n.headline][:3]
    news_vote = _agent_vote_to_analyst_vote("news", news_agent_vote, mentions or [f"No recent company news mentioning {symbol}."])

    macro_agent_vote = researcher_vote("nova", originated=(item.assigned_agent == "nova"), confidence=item.confidence, symbol=symbol)
    macro_vote = _agent_vote_to_analyst_vote(
        "macro", macro_agent_vote, [f"Research category: {item.category}.", f"Research confidence: {item.confidence:.0f}%."]
    )

    risk = _risk_vote(symbol, sentinel_warning, guardian_warning)
    sentiment = _sentiment_vote(symbol, scanner_alerts)

    execution, overall = _execution_vote([technical, news_vote, macro_vote, risk, sentiment])
    return [technical, news_vote, macro_vote, risk, sentiment, execution], overall


def generate_proposal(
    item: ResearchItem,
    *,
    quantity: float,
    price: float,
    news: list[NewsItem],
    scanner_alerts: list[ScannerAlert],
    sentinel_warning: RiskWarning | None,
    guardian_warning: RiskWarning | None,
    provider: MarketDataProvider,
    now_sim_minutes: int,
) -> TradeProposal:
    assert item.symbol is not None
    votes, overall = generate_analyst_votes(
        item, news=news, scanner_alerts=scanner_alerts, sentinel_warning=sentinel_warning, guardian_warning=guardian_warning, provider=provider
    )
    risk_summary = (
        sentinel_warning.message if sentinel_warning else guardian_warning.message if guardian_warning else f"{item.symbol} is within all configured risk limits."
    )
    return TradeProposal(
        id=f"proposal-{item.id}",
        symbol=item.symbol,
        category=item.category,
        quantity=quantity,
        price=price,
        confidence=item.confidence,
        analystVotes=votes,
        overallRecommendation=overall,
        researchSummary=f"{item.title} — {item.summary}",
        riskSummary=risk_summary,
        createdAt=_now_iso(),
        createdSimMinutes=now_sim_minutes,
    )


def resolve_proposal(
    proposal: TradeProposal,
    ceo_choice: AnalystChoice,
    *,
    portfolio: PaperPortfolio,
    risk_limits: RiskLimits,
    current_price: float | None,
    now_sim_minutes: int,
) -> tuple[PaperPortfolio, TradeDecision, CeoDecisionRecord]:
    """Applies the CEO's real decision: buy opens a real long, sell opens
    a real short, wait does nothing. Always produces a permanent
    TradeDecision (so every existing consumer — DecisionsPanel,
    DecisionDetail, Player vs AI — keeps working unchanged) and a
    CeoDecisionRecord (the accuracy-tracking side of this feature)."""
    decision_id = f"decision-{proposal.id}"
    order_id: str | None = None
    price = current_price if current_price and current_price > 0 else proposal.price

    if ceo_choice in ("buy", "sell"):
        quantity = recommended_quantity(risk_limits, portfolio, price)
        if quantity <= 0:
            # Sized to zero (portfolio too small / budget floor) — falls
            # back to "wait" honestly rather than pretending a trade of
            # size zero happened.
            ceo_choice = "wait"
        else:
            position_id = f"pos-{proposal.id}"
            portfolio = open_position(
                portfolio,
                position_id=position_id,
                symbol=proposal.symbol,
                price=price,
                opened_by="atlas",
                confidence=proposal.confidence,
                opened_sim_minutes=now_sim_minutes,
                side="buy" if ceo_choice == "buy" else "sell",
                quantity=quantity,
            )
            order_id = position_id

    final_reasoning = (
        f"CEO {'approved' if ceo_choice == proposal.overall_recommendation else 'overrode the desk and chose'} "
        f"{ceo_choice.upper()} on {proposal.symbol}."
        if ceo_choice != "wait"
        else f"CEO chose to WAIT on {proposal.symbol} — no trade placed."
    )
    supporting = [v.agent_id for v in proposal.analyst_votes if v.choice == ceo_choice]
    opposing = [v.agent_id for v in proposal.analyst_votes if v.choice != ceo_choice]
    technical_vote = next((v for v in proposal.analyst_votes if v.role == "technical"), None)
    decision = TradeDecision(
        id=decision_id,
        symbol=proposal.symbol,
        outcome="trade" if ceo_choice in ("buy", "sell") else "no_trade",
        votes=[AgentVote(agentId=v.agent_id, choice=v.choice if v.choice != "wait" else "hold", reason=v.reasoning) for v in proposal.analyst_votes],
        researchSummary=proposal.research_summary,
        technicalSummary=technical_vote.reasoning if technical_vote else "No technical read available.",
        fundamentalSummary=f"Research category: {proposal.category}.",
        riskSummary=proposal.risk_summary,
        supportingAgents=supporting,
        opposingAgents=opposing,
        confidence=proposal.confidence,
        finalReasoning=final_reasoning,
        orderId=order_id,
        createdAt=_now_iso(),
    )
    record = CeoDecisionRecord(
        id=f"ceo-{proposal.id}",
        proposalId=proposal.id,
        symbol=proposal.symbol,
        category=proposal.category,
        aiRecommendation=proposal.overall_recommendation,
        ceoDecision=ceo_choice,
        agreedWithAi=(ceo_choice == proposal.overall_recommendation),
        decisionId=decision_id,
        outcome="pending" if ceo_choice in ("buy", "sell") else "undecidable",
        createdAt=_now_iso(),
    )
    return portfolio, decision, record


def grade_ceo_decisions(records: list[CeoDecisionRecord], trade_history: list[PaperTrade]) -> list[CeoDecisionRecord]:
    """Resolves any "pending" record whose linked trade has since closed
    — matched by decision_id, the same real link app/journal.py already
    stamps onto every closed PaperTrade. Never grades a "wait"/override
    (those stay "undecidable" forever — no real trade exists to test
    them against)."""
    if not records:
        return records
    by_decision_id: dict[str, PaperTrade] = {t.decision_id: t for t in trade_history if t.decision_id}
    updated: list[CeoDecisionRecord] = []
    for record in records:
        if record.outcome != "pending" or record.decision_id is None:
            updated.append(record)
            continue
        trade = by_decision_id.get(record.decision_id)
        if trade is None:
            updated.append(record)
            continue
        outcome = "correct" if trade.pnl > 0 else "incorrect"
        updated.append(record.model_copy(update={"outcome": outcome, "resolved_at": _now_iso()}))
    return updated


def expire_stale_proposals(proposals: list[TradeProposal], now_sim_minutes: int) -> tuple[list[TradeProposal], list[TradeProposal]]:
    """Returns (still-pending proposals, proposals that just expired) —
    callers turn each expired proposal into a real "wait" CeoDecisionRecord
    via resolve_proposal, same as an explicit CEO wait, rather than
    silently dropping it."""
    keep: list[TradeProposal] = []
    expired: list[TradeProposal] = []
    for p in proposals:
        if now_sim_minutes - p.created_sim_minutes >= PROPOSAL_EXPIRY_SIM_MINUTES:
            expired.append(p)
        else:
            keep.append(p)
    return keep, expired
