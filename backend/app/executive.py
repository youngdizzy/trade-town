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
from typing import Literal

from app.confidence import compute_confidence
from app.gatekeeper import MIN_CONFIDENCE, evaluate_gatekeeper
from app.market_data import Candle as ProviderCandle
from app.market_data import MarketDataProvider
from app.market_data import trend_pct, volatility_pct
from app.portfolio import open_position
from app.risk_engine import portfolio_equity, recommended_quantity
from app.schemas import (
    AgentId,
    AgentVote,
    AnalystChoice,
    AnalystRole,
    AnalystVote,
    CeoDecisionRecord,
    Debate,
    DecisionGrade,
    GatekeeperVerdict,
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
# v0.7 Feature 40.5 — the Expert Consultation System's "Request More
# Research" / "Delay Decision" CEO actions. A proposal can be held at
# most twice before the CEO must actually decide (or let it expire the
# normal way) — real and bounded, never an indefinite deferral.
MAX_PROPOSAL_HOLDS = 2

# v0.7 Feature 50 (Part 2/3) — Decision Grade, a standard academic-scale
# letter grade on the DECISION-MAKING PROCESS at the moment it's made
# (never the trade's own P&L — that stays app/discipline.py's separate,
# already-real Discipline Score). Real, checkable inputs only: the
# Decision Confidence Engine's own score (process quality), the real
# multi-agent agreement rate among the six analyst votes, and whether
# the trade actually cleared the Trade Gatekeeper.
_GRADE_THRESHOLDS: tuple[tuple[float, DecisionGrade], ...] = (
    (97.0, "A+"),
    (93.0, "A"),
    (90.0, "A-"),
    (87.0, "B+"),
    (83.0, "B"),
    (80.0, "B-"),
    (77.0, "C+"),
    (73.0, "C"),
    (70.0, "C-"),
    (67.0, "D+"),
    (60.0, "D"),
)


def _grade_for_score(score: float) -> DecisionGrade:
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def compute_decision_grade(proposal: TradeProposal, gatekeeper_verdict: GatekeeperVerdict | None) -> tuple[DecisionGrade, float]:
    """50% the real Decision Confidence Engine score, 25% the real share
    of the six analyst votes that agreed with the desk's own overall
    recommendation, 25% whether the Trade Gatekeeper actually approved
    the trade (100 if it did, or if the CEO chose WAIT and never reached
    the gate — nothing to penalize; 40 if the Gatekeeper vetoed it)."""
    confidence_component = proposal.confidence_engine.score
    total_votes = len(proposal.analyst_votes) or 1
    agreeing = sum(1 for v in proposal.analyst_votes if v.choice == proposal.overall_recommendation)
    agreement_component = agreeing / total_votes * 100.0
    gatekeeper_component = 100.0 if gatekeeper_verdict is None or gatekeeper_verdict.approved else 40.0
    score = confidence_component * 0.5 + agreement_component * 0.25 + gatekeeper_component * 0.25
    return _grade_for_score(score), round(score, 1)


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
    portfolio: PaperPortfolio,
    risk_limits: RiskLimits,
) -> TradeProposal:
    assert item.symbol is not None
    votes, overall = generate_analyst_votes(
        item, news=news, scanner_alerts=scanner_alerts, sentinel_warning=sentinel_warning, guardian_warning=guardian_warning, provider=provider
    )
    risk_summary = (
        sentinel_warning.message if sentinel_warning else guardian_warning.message if guardian_warning else f"{item.symbol} is within all configured risk limits."
    )
    confidence_engine = compute_confidence(votes, overall, item.confidence, portfolio, risk_limits)
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
        confidenceEngine=confidence_engine,
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
    debate: Debate | None = None,
    risk_warnings: list[RiskWarning] | None = None,
    resolved_by: Literal["ceo", "auto"] = "ceo",
) -> tuple[PaperPortfolio, TradeDecision, CeoDecisionRecord]:
    """Applies the CEO's real decision: buy opens a real long, sell opens
    a real short, wait does nothing — subject to the Trade Gatekeeper's
    final approval (v0.7 Feature 20, app/gatekeeper.py), which can veto
    even a real buy/sell the CEO chose. Always produces a permanent
    TradeDecision (so every existing consumer — DecisionsPanel,
    DecisionDetail, Player vs AI — keeps working unchanged) and a
    CeoDecisionRecord (the accuracy-tracking side of this feature).
    `resolved_by` is honest provenance (v0.7 Feature 21) — "auto" for a
    Company Operating Mode auto-resolution or a stale-proposal expiry
    (see app/nexus.py), "ceo" only for a real POST /api/executive/decide
    click; it never changes what actually happens, only what gets
    recorded about who decided it."""
    decision_id = f"decision-{proposal.id}"
    order_id: str | None = None
    price = current_price if current_price and current_price > 0 else proposal.price
    gatekeeper_verdict: GatekeeperVerdict | None = None

    if ceo_choice in ("buy", "sell"):
        quantity = recommended_quantity(risk_limits, portfolio, price)
        if quantity <= 0:
            # Sized to zero (portfolio too small / budget floor) — falls
            # back to "wait" honestly rather than pretending a trade of
            # size zero happened.
            ceo_choice = "wait"
        else:
            gatekeeper_verdict = evaluate_gatekeeper(proposal, ceo_choice, debate, portfolio, risk_limits, risk_warnings or [])
            if gatekeeper_verdict.approved:
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
            # else: the Gatekeeper vetoed it — ceo_choice is deliberately
            # NOT downgraded to "wait" here (unlike the zero-quantity
            # fallback above) so the CeoDecisionRecord still reflects the
            # CEO's real original call; order_id staying None is what
            # actually signals no trade happened.

    if ceo_choice == "wait":
        final_reasoning = f"CEO chose to WAIT on {proposal.symbol} — no trade placed."
    elif gatekeeper_verdict is not None and not gatekeeper_verdict.approved:
        final_reasoning = f"CEO chose {ceo_choice.upper()} on {proposal.symbol}, but the Trade Gatekeeper rejected it: {gatekeeper_verdict.summary}"
    else:
        final_reasoning = (
            f"CEO {'approved' if ceo_choice == proposal.overall_recommendation else 'overrode the desk and chose'} "
            f"{ceo_choice.upper()} on {proposal.symbol}."
        )
    supporting = [v.agent_id for v in proposal.analyst_votes if v.choice == ceo_choice]
    opposing = [v.agent_id for v in proposal.analyst_votes if v.choice != ceo_choice]
    technical_vote = next((v for v in proposal.analyst_votes if v.role == "technical"), None)
    decision_grade, decision_grade_score = compute_decision_grade(proposal, gatekeeper_verdict)
    decision = TradeDecision(
        id=decision_id,
        symbol=proposal.symbol,
        outcome="trade" if order_id is not None else "no_trade",
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
        confidenceEngine=proposal.confidence_engine,
        gatekeeperVerdict=gatekeeper_verdict,
        decisionGrade=decision_grade,
        decisionGradeScore=decision_grade_score,
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
        outcome="pending" if order_id is not None else "undecidable",
        resolvedBy=resolved_by,
        createdAt=_now_iso(),
    )
    return portfolio, decision, record


# v0.7 Feature 21 — Company Operating Modes. Assisted Mode auto-resolves
# every "routine" proposal via resolve_proposal(resolved_by="auto") and
# only leaves a "significant" one pending for the CEO — see app/nexus.py's
# tick(). Executive Mode auto-resolves regardless of significance;
# Learning Mode never calls this at all (every proposal stays pending,
# the pre-Feature-21 behavior). Reuses real, already-configured
# thresholds (the Gatekeeper's own MIN_CONFIDENCE, the desk's own
# RiskLimits.maxPositionPct) rather than inventing new magic numbers.
def is_significant_proposal(
    proposal: TradeProposal,
    portfolio: PaperPortfolio,
    risk_limits: RiskLimits,
    risk_warnings: list[RiskWarning],
) -> tuple[bool, list[str]]:
    """Returns (significant, reasons) — reasons is always the real,
    explainable cause, mirroring app/gatekeeper.py's own check style. A
    "wait" recommendation is never significant (nothing to interrupt the
    player over — there's no trade to auto-approve either way)."""
    if proposal.overall_recommendation == "wait":
        return False, []

    reasons: list[str] = []
    if proposal.confidence_engine.score < MIN_CONFIDENCE:
        reasons.append(f"Confidence is only {proposal.confidence_engine.score:.0f}/100 — below the {MIN_CONFIDENCE:.0f} threshold.")
    if any(w.symbol == proposal.symbol and w.severity == "critical" for w in risk_warnings):
        reasons.append(f"An active critical risk warning is open on {proposal.symbol}.")
    equity = portfolio_equity(portfolio)
    if equity > 0 and risk_limits.max_position_pct > 0:
        notional_pct = proposal.quantity * proposal.price / equity * 100
        if notional_pct >= risk_limits.max_position_pct:
            reasons.append(f"Position size is {notional_pct:.0f}% of portfolio equity — at or above the {risk_limits.max_position_pct:.0f}% max position limit.")
    return len(reasons) > 0, reasons


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


def hold_proposal(proposal: TradeProposal, *, now_sim_minutes: int) -> TradeProposal | None:
    """v0.7 Feature 40.5 — "Request More Research" and "Delay Decision"
    are both real applications of the same mechanism: reset the
    proposal's own real expiry clock (created_sim_minutes — the same
    field expire_stale_proposals already reads) so it doesn't go stale
    while the CEO waits, rather than inventing a second timer or a fake
    "research in progress" state with no real signal behind it. Returns
    None if the proposal has already been held MAX_PROPOSAL_HOLDS times
    — the caller must reject the request rather than deferring forever.
    Never produces a TradeDecision/CeoDecisionRecord: nothing has
    actually been decided yet, so the proposal simply stays pending."""
    if proposal.hold_count >= MAX_PROPOSAL_HOLDS:
        return None
    return proposal.model_copy(update={"created_sim_minutes": now_sim_minutes, "hold_count": proposal.hold_count + 1})


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
