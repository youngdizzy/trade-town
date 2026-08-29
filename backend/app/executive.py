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

from app.broker import place_order
from app.confidence import compute_confidence
from app.multi_timeframe import compute_multi_timeframe_confirmation
from app.execution_quality import apply_slippage
from app.gatekeeper import MIN_CONFIDENCE, evaluate_gatekeeper
from app.market_data import Candle as ProviderCandle
from app.market_data import MarketDataProvider, market_data_provider
from app.market_data import trend_pct, volatility_pct
from app.portfolio import open_position
from app.position_sizing import compute_volatility_sizing
from app.risk_engine import portfolio_equity, recommended_quantity
from app.trend_engine import compute_multi_horizon_trend_score
from app.schemas import (
    AgentId,
    AgentVote,
    AgentVoteAccuracyScore,
    AnalystChoice,
    AnalystRole,
    AnalystVote,
    CeoDecisionRecord,
    Debate,
    DecisionGrade,
    DecisionSessionContext,
    GatekeeperVerdict,
    MarketIntelligenceState,
    NewsItem,
    OrderSide,
    PaperPortfolio,
    PaperTrade,
    RiskLimits,
    RiskWarning,
    ResearchItem,
    ScannerAlert,
    TradeDecision,
    TradeProposal,
    TradingRestriction,
    WeightedExecutiveRecommendation,
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

# CEO directive "Hard Risk Gates 2.0 — Stop-Loss / Position-Risk
# Enforcement" — a real, disclosed policy choice, not a fabricated or
# backtested number: the take-profit target sits this many multiples of
# the same real ATR-based stop DISTANCE (app/position_sizing.py's
# compute_volatility_sizing()) beyond entry, on the reward side. 2.0 is
# a conventional, honestly-arbitrary reward:risk convention — a real,
# disclosed choice, never the only valid one a researcher could pick
# (mirrors this codebase's own "real, disclosed, simple formula" idiom
# already established for _REGIME_SUITABILITY_HIT_RATE_FLOOR_PCT and
# _SESSION_SUITABILITY_HIT_RATE_FLOOR_PCT in app/position_sizing.py).
TARGET_REWARD_RISK_MULTIPLE = 2.0
# CEO directive "AHL-Inspired Systematic Trend & Momentum Research
# Engine" follow-up — a locally-scoped horizon set for the Technical
# Analyst's multi-horizon evidence below. app/trend_engine.py's own
# DEFAULT_HORIZONS labels ("1_week"/"2_month"/etc.) assume a
# DAILY-timeframe candle series (its own module docstring says so
# explicitly); this proposal's real candles are hourly
# (PROPOSAL_TIMEFRAME) and bounded to PROPOSAL_CANDLE_COUNT=30 bars, so
# reusing those daily labels here would misdescribe what was actually
# measured. These three horizons are honestly labeled in hours and all
# fit inside the existing 30-bar sample — no second, larger candle
# fetch needed.
PROPOSAL_TREND_HORIZONS: list[tuple[str, int]] = [("6h", 6), ("12h", 12), ("24h", 24)]
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
# Public (no leading underscore) — app/decision_vault.py reuses this
# exact scale for Capital Allocation Grade / Patience Grade, rather than
# defining a second, possibly-drifting letter-grade scale.
GRADE_THRESHOLDS: tuple[tuple[float, DecisionGrade], ...] = (
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


def grade_for_score(score: float) -> DecisionGrade:
    for threshold, grade in GRADE_THRESHOLDS:
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
    return grade_for_score(score), round(score, 1)


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
    evidence = [f"Trend: {trend:+.1f}% over the last {PROPOSAL_CANDLE_COUNT} {PROPOSAL_TIMEFRAME} bars.", f"Volatility: {volatility:.1f}% average bar range."]
    # CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    # Engine" follow-up — real, structured Multi-Horizon Trend Engine
    # evidence (app/trend_engine.py, same real formula the Strategy Lab
    # already validates) reused as ONE MORE piece of evidence for the
    # Technical Analyst, never a second decision input: `choice`/
    # `reasoning` above are unchanged, still driven only by the
    # existing trend_pct/volatility_pct read. Because AnalystVote is
    # the exact real substance app/debate.py's AI Debate Room quotes
    # verbatim, this is the one real, non-invasive place this evidence
    # reaches agents' own research/debate flow — no new plumbing
    # through the Executive Department Opinions call sites, which would
    # need a MarketDataProvider threaded through 7+ existing call sites
    # for the same real data this vote already has in hand.
    if len(candles) >= 2 and item.symbol is not None:
        trend_score = compute_multi_horizon_trend_score(candles, item.symbol, PROPOSAL_TIMEFRAME, horizons=PROPOSAL_TREND_HORIZONS, method="endpoint_slope")
        horizon_summary = ", ".join(f"{h.horizon_label}: {'up' if h.direction > 0 else 'down' if h.direction < 0 else 'flat'}" for h in trend_score.horizons)
        evidence.append(f"Multi-Horizon Trend Engine composite: {trend_score.composite_score:+.0f}/{len(trend_score.horizons)} ({horizon_summary}).")
    return AnalystVote(
        role="technical",
        agentId="echo",
        choice=choice,
        reasoning=reasoning,
        evidence=evidence,
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
    market_intelligence: MarketIntelligenceState,
    agent_vote_accuracy: list[AgentVoteAccuracyScore],
) -> TradeProposal:
    assert item.symbol is not None
    votes, overall = generate_analyst_votes(
        item, news=news, scanner_alerts=scanner_alerts, sentinel_warning=sentinel_warning, guardian_warning=guardian_warning, provider=provider
    )
    risk_summary = (
        sentinel_warning.message if sentinel_warning else guardian_warning.message if guardian_warning else f"{item.symbol} is within all configured risk limits."
    )
    multi_timeframe = compute_multi_timeframe_confirmation(provider, item.symbol, overall)
    confidence_engine = compute_confidence(votes, overall, item.confidence, portfolio, risk_limits, multi_timeframe, agent_vote_accuracy)
    # v0.7 Feature 51 — a real one-line citation of the Market Intelligence
    # Department's current read, attached to every new proposal so it
    # literally carries real market context (see app/market_intelligence.py).
    market_intelligence_summary = (
        f"{market_intelligence.regime_label} — Market Quality {market_intelligence.quality.tier.replace('_', ' ')} "
        f"({market_intelligence.quality.score:.0f}/100, {market_intelligence.quality.confidence_pct:.0f}% confidence)."
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
        confidenceEngine=confidence_engine,
        createdAt=_now_iso(),
        createdSimMinutes=now_sim_minutes,
        marketIntelligenceSummary=market_intelligence_summary,
    )


def resolve_proposal(
    proposal: TradeProposal,
    ceo_choice: AnalystChoice,
    *,
    portfolio: PaperPortfolio,
    risk_limits: RiskLimits,
    current_price: float | None,
    now_sim_minutes: int,
    market_intelligence: MarketIntelligenceState,
    debate: Debate | None = None,
    risk_warnings: list[RiskWarning] | None = None,
    resolved_by: Literal["ceo", "auto", "delegated"] = "ceo",
    weighted_recommendation: WeightedExecutiveRecommendation | None = None,
    min_confidence_override: float | None = None,
    behavioral_cooldown_minutes: int | None = None,
    behavioral_size_increase_threshold_pct: float | None = None,
    trading_restrictions: list[TradingRestriction] | None = None,
    provider: MarketDataProvider = market_data_provider,
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
    (see app/nexus.py), "ceo" for a real POST /api/executive/decide
    click, "delegated" (Design Bible Chapter 70 Part 2) for a CEO click
    that explicitly asked the Executive Intelligence Network's own
    recommendation to decide; it never changes what actually happens,
    only what gets recorded about who decided it.

    `weighted_recommendation` (Design Bible Chapter 70 Part 3 addendum)
    — the caller's already-computed Weighted Executive Decision Engine
    read for this exact proposal, if any. Passed straight through to
    evaluate_gatekeeper() below as one more real, unconditional check —
    advisory in the sense that it can only ever contribute to a
    rejection alongside every other check, never approve a trade or
    bypass any of them. This function never computes it itself (the
    caller already has the department opinions, accuracy scores, and
    active Weight Profile in scope — see app/state.py's
    submit_ceo_decision and app/nexus.py's _apply_operating_mode).

    `behavioral_cooldown_minutes`/`behavioral_size_increase_threshold_pct`
    — the CEO's own real Behavioral Circuit Breaker thresholds
    (TradingModeState), passed straight through to evaluate_gatekeeper()'s
    tenth check. None (the default) falls back to that function's own
    disclosed defaults, mirroring min_confidence_override's convention.

    `trading_restrictions` (CEO directive "Layered Kill Switches," see
    app/trading_restrictions.py) — passed straight through to
    evaluate_gatekeeper()'s Trading Restriction check. None/empty
    behaves exactly as before this parameter existed.

    `provider` (CEO directive "Hard Risk Gates 2.0 — Stop-Loss /
    Position-Risk Enforcement") — feeds a fresh, real
    compute_volatility_sizing() read (app/position_sizing.py) computed
    HERE, not trusted from a possibly-stale WarRoomSession the CEO's own
    decision may have sat pending against for a while (the same
    "recompute fresh, never stale" guarantee this function already
    makes for the position-sizing ceiling above). Defaults to the real
    global market_data_provider singleton — the same default every
    other real production call site already resolves to (app/nexus.py,
    app/state.py) — so no existing caller needs to change unless it
    wants to inject a fake provider for a test."""
    decision_id = f"decision-{proposal.id}"
    order_id: str | None = None
    price = current_price if current_price and current_price > 0 else proposal.price
    gatekeeper_verdict: GatekeeperVerdict | None = None

    if ceo_choice in ("buy", "sell"):
        # v0.7 Design Bible Chapter 57 — the Institutional Position Sizing
        # & Capital Deployment Engine (app/position_sizing.py) already
        # narrowed proposal.quantity down from this same ceiling formula
        # at proposal-creation time, using real evidence/confidence/
        # portfolio-context this function has no access to. Re-deriving
        # the ceiling fresh here (never trusting a possibly-stale one)
        # and taking the smaller of the two preserves both real
        # properties at once: the engine's evidence-based narrowing
        # survives, and a portfolio that's shrunk since the proposal was
        # created still gets a genuinely fresh, tighter cap — the same
        # "recompute fresh, never stale" guarantee this function already
        # made before this engine existed.
        ceiling_quantity = recommended_quantity(risk_limits, portfolio, price)
        quantity = min(ceiling_quantity, proposal.quantity)
        if quantity <= 0:
            # Sized to zero (portfolio too small / budget floor) — falls
            # back to "wait" honestly rather than pretending a trade of
            # size zero happened.
            ceo_choice = "wait"
        else:
            # CEO directive "Hard Risk Gates 2.0 — Stop-Loss / Position-
            # Risk Enforcement," Gate 3 — a real, ATR-based stop distance
            # must exist BEFORE the Gatekeeper's final approval, not
            # computed only after (a rejected trade must never have
            # already opened a position). Reuses app/position_sizing.py's
            # own real Chandelier-ATR distance verbatim — no second,
            # independently-tuned computation.
            equity = portfolio_equity(portfolio)
            volatility_sizing = compute_volatility_sizing(proposal, provider, equity, risk_limits)
            stop_distance = volatility_sizing.stop_distance if volatility_sizing.available else None
            gatekeeper_verdict = evaluate_gatekeeper(
                proposal,
                ceo_choice,
                debate,
                portfolio,
                risk_limits,
                risk_warnings or [],
                market_intelligence,
                now_sim_minutes,
                weighted_recommendation,
                min_confidence_override,
                behavioral_cooldown_minutes,
                behavioral_size_increase_threshold_pct,
                quantity=quantity,
                price=price,
                sim_day=now_sim_minutes // 1440,
                trading_restrictions=trading_restrictions,
                stop_distance=stop_distance,
                stop_evaluated=True,
            )
            if gatekeeper_verdict.approved:
                position_id = f"pos-{proposal.id}"
                # CEO directive "Next Professional Trading Firm Phase,"
                # Priority 1 (Execution Realism) — the CEO's own direct
                # buy/sell is a market-style instant fill (no order book,
                # no queued latency), so it gets real, disclosed slippage
                # exactly like a "market" order placed through
                # app/broker.py does. `price` (used above for the
                # position-sizing ceiling) stays the real signal price;
                # only the actual fill uses the slipped price, matching
                # the SIGNAL PRICE -> ACTUAL FILL distinction this
                # directive asked for.
                fill_side: OrderSide = "buy" if ceo_choice == "buy" else "sell"
                fill_price, entry_slippage_bps = apply_slippage(
                    price, action_side=fill_side, market_intelligence=market_intelligence, symbol=proposal.symbol
                )
                # CEO directive "Hard Risk Gates 2.0" — the real stop/
                # target PRICE, derived from the ACTUAL fill (never the
                # pre-slippage signal price) so the stored risk boundary
                # matches what the position actually paid. The Valid
                # Stop-Loss gate above already guarantees stop_distance
                # is a real, positive, finite number whenever this branch
                # is reached (gatekeeper_verdict.approved could not be
                # True otherwise).
                stop_price: float | None = None
                target_price: float | None = None
                if stop_distance is not None:
                    if fill_side == "buy":
                        stop_price = round(fill_price - stop_distance, 4)
                        target_price = round(fill_price + TARGET_REWARD_RISK_MULTIPLE * stop_distance, 4)
                    else:
                        stop_price = round(fill_price + stop_distance, 4)
                        target_price = round(fill_price - TARGET_REWARD_RISK_MULTIPLE * stop_distance, 4)
                portfolio = open_position(
                    portfolio,
                    position_id=position_id,
                    symbol=proposal.symbol,
                    price=fill_price,
                    opened_by="atlas",
                    confidence=proposal.confidence,
                    opened_sim_minutes=now_sim_minutes,
                    side=fill_side,
                    quantity=quantity,
                    trading_style=proposal.trading_style,
                    entry_slippage_bps=entry_slippage_bps,
                    proposal_id=proposal.id,
                    stop_price=stop_price,
                    target_price=target_price,
                )
                # CEO directive "Hard Risk Gates 2.0," Phase 5 — a stop-
                # loss is not merely UI metadata; the system must treat it
                # as an actual risk boundary. app/broker.py's real
                # stop_loss/take_profit order machinery (gap-through
                # worse-of-trigger-price fill, real slippage on trigger,
                # automatic cancellation if the position already closed
                # some other way) already existed fully built but had no
                # live caller — this is that caller. The exit order's own
                # side is the OPPOSITE of the position's side (selling to
                # exit a long, buying to cover a short), matching
                # app/broker.py's own _fill_price() convention exactly.
                if stop_price is not None:
                    exit_side: OrderSide = "sell" if fill_side == "buy" else "buy"
                    portfolio = place_order(
                        portfolio,
                        order_id=f"order-stop-{position_id}",
                        symbol=proposal.symbol,
                        side=exit_side,
                        order_type="stop_loss",
                        quantity=quantity,
                        price=stop_price,
                        placed_by="sentinel",
                        reason=f"Protective stop for {position_id} — real ATR-based distance of {stop_distance:.4f}.",
                        confidence=proposal.confidence,
                        linked_position_id=position_id,
                    )
                    if target_price is not None:
                        portfolio = place_order(
                            portfolio,
                            order_id=f"order-target-{position_id}",
                            symbol=proposal.symbol,
                            side=exit_side,
                            order_type="take_profit",
                            quantity=quantity,
                            price=target_price,
                            placed_by="sentinel",
                            reason=f"Take-profit for {position_id} — {TARGET_REWARD_RISK_MULTIPLE:.1f}x the real ATR-based stop distance.",
                            confidence=proposal.confidence,
                            linked_position_id=position_id,
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
        # CEO directive "Complete Trade Provenance," Part 8 —
        # Decision-Time Snapshot. Unconditional (buy/sell/wait alike —
        # real market context regardless of the choice made), and set
        # here so every one of this function's three real call sites
        # (a CEO click, an Operating Mode auto-resolution, a
        # stale-proposal expiry) gets it for free rather than
        # duplicating this three times. Reads the same
        # `market_intelligence`/`current_price` this function already
        # received as real parameters — never a second, independently
        # computed reading of either.
        decisionSession=market_intelligence.session.current,
        decisionMarketRegime=market_intelligence.regime,
        decisionPrice=current_price,
        decisionVolatilityPct=market_intelligence.volatility.current_pct,
        # CEO directive "Complete Trade Provenance," Part 5 — Session
        # Context, mirroring the same real SessionRead/VolatilityRead
        # fields market_intelligence.session/volatility already carry —
        # never a second, independently-computed reading.
        decisionSessionContext=DecisionSessionContext(
            startedAt=market_intelligence.session.session_started_at,
            closesAt=market_intelligence.session.session_closes_at,
            minutesSinceOpen=market_intelligence.session.minutes_since_session_open,
            minutesUntilClose=market_intelligence.session.minutes_until_session_close,
            overlapsActive=market_intelligence.session.overlaps_active,
            sessionVolatilityPct=market_intelligence.volatility.session_pct,
        ),
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
    priority_score: float | None = None,
) -> tuple[bool, list[str]]:
    """Returns (significant, reasons) — reasons is always the real,
    explainable cause, mirroring app/gatekeeper.py's own check style. A
    "wait" recommendation is never significant (nothing to interrupt the
    player over — there's no trade to auto-approve either way).

    `priority_score` is v0.7 Design Bible Chapter 59's real Minimum
    Priority Score control (app/capital_priority.py's `priority_score`,
    the same reused `decisionScore.overall` shown everywhere else — never
    a second read). Optional and defaulting to None/no-check keeps every
    existing caller honest: a caller with no War Room session to look up
    a score from simply can't apply a floor it has no real number for."""
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
    if priority_score is not None and risk_limits.min_priority_score > 0 and priority_score < risk_limits.min_priority_score:
        reasons.append(f"Priority Score is only {priority_score:.0f}/100 — below the CEO's {risk_limits.min_priority_score:.0f} minimum allocation floor.")
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


# Design Bible Chapter 70 Part 2 — "Modify" as a real CEO decision
# action, distinct from buy/sell/wait/hold. Downsize-only, on purpose:
# app/position_sizing.py's Institutional Position Sizing & Capital
# Deployment Engine (Chapter 57) already narrowed proposal.quantity down
# from its own real evidence-based ceiling at proposal-creation time —
# letting the CEO size *up* here would let a hand-typed number bypass
# that real ceiling. The proposal stays pending afterward (same as
# hold_proposal below) — Modify resizes the trade, it doesn't decide it;
# the CEO still buys/sells/waits on the resized proposal separately.
def modify_proposal(proposal: TradeProposal, new_quantity: float) -> TradeProposal | None:
    """Returns None for an invalid resize (non-positive, or larger than
    the proposal's own already-computed ceiling) — the caller must
    reject the request rather than silently clamping it."""
    if new_quantity <= 0 or new_quantity > proposal.quantity:
        return None
    return proposal.model_copy(update={"quantity": new_quantity})


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
