"""TradeGatekeeper — v0.7 Feature 20, the firm's final-approval AI.

Sits between the CEO's real buy/sell call (app/executive.py's
resolve_proposal) and the order actually being placed. Every check here
reads real state already computed elsewhere in this codebase — the same
six analyst votes, the real Decision Confidence Engine score (Feature
15), the real AI Debate outcome (Feature 17), the portfolio's real open
positions, and Sentinel/Guardian's real standing risk watch — never a
fabricated signal. The v0.7 brief's much longer checklist also names
multi-timeframe confirmation (only one timeframe is ever fetched — see
app/executive.py's PROPOSAL_TIMEFRAME), support/resistance quality,
volume confirmation, liquidity, the *timing* of upcoming news (this
codebase generates news reactively, never schedules it in advance),
reward-to-risk ratio and stop-loss placement (the paper broker never
places exit orders — see DecisionDetail's own "Trade Plan" section),
strategy match, and historical performance of similar setups — none of
these have a real data source in this codebase and none are invented
here; see app/confidence.py's module docstring for the same honesty
boundary already established for an overlapping list.

A trade the Gatekeeper blocks never executes — there is no P&L to grade.
Instead its real *hypothetical* outcome is tracked (GatekeeperRejection)
and graded later purely from the symbol's own real subsequent watchlist
price movement, once GATEKEEPER_EVAL_WINDOW_MINUTES of simulated time
has passed — see grade_gatekeeper_rejections.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.behavioral_risk import compute_behavioral_check
from app.schemas import (
    AnalystChoice,
    Debate,
    GatekeeperCheck,
    GatekeeperRejection,
    GatekeeperVerdict,
    MarketIntelligenceState,
    PaperPortfolio,
    PaperTrade,
    RiskLimits,
    RiskWarning,
    TradeProposal,
    WatchlistEntry,
    WeightedExecutiveRecommendation,
)
from app.watchlist import SYMBOL_CATEGORY

MIN_CONFIDENCE = 55.0
MAX_CORRELATED_POSITIONS = 2
GATEKEEPER_EVAL_WINDOW_MINUTES = 240  # 4 simulated hours — same order of magnitude as this sim's typical real hold durations.

# Behavioral Circuit Breaker defaults (app/behavioral_risk.py) — mirror
# TradingModeState's own behavioral_cooldown_minutes/
# behavioral_size_increase_threshold_pct defaults exactly, so a caller
# that doesn't pass an override (e.g. an existing direct test) behaves
# identically to the CEO's own out-of-the-box configuration.
BEHAVIORAL_COOLDOWN_MINUTES = 60
BEHAVIORAL_SIZE_INCREASE_THRESHOLD_PCT = 50.0

# Design Bible Chapter 70 Part 3 addendum — the execution hierarchy the
# Weighted Executive Decision Engine must feed into: Research → Executive
# Board Recommendation → WEDE → Trade Gatekeeper → Risk Authority →
# Institutional Rule Engine → Broker Management System → Order Execution.
# Mirrors app/executive_intelligence.py's own _TRADING_ACTIONS exactly
# (duplicated rather than cross-imported, matching this codebase's
# existing precedent for small, stable enums shared across modules with
# no other coupling) — "the network thinks a trade should happen at all
# right now," never a directional (buy vs. sell) judgment.
_WEDE_TRADING_ACTIONS = frozenset({"trade_normally", "reduce_risk"})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confidence_check(proposal: TradeProposal, min_confidence: float = MIN_CONFIDENCE) -> GatekeeperCheck:
    score = proposal.confidence_engine.score
    passed = score >= min_confidence
    return GatekeeperCheck(
        id="confidence",
        label="Decision Confidence",
        passed=passed,
        detail=f"{score:.0f}/100 — {'meets' if passed else 'below'} the required {min_confidence:.0f} minimum.",
    )


def _risk_manager_check(proposal: TradeProposal, ceo_choice: AnalystChoice) -> GatekeeperCheck:
    risk_vote = next((v for v in proposal.analyst_votes if v.role == "risk"), None)
    passed = risk_vote is None or risk_vote.choice == ceo_choice
    detail = risk_vote.reasoning if risk_vote else "No risk analyst read available for this proposal."
    return GatekeeperCheck(id="risk_manager", label="Risk Manager Alignment", passed=passed, detail=detail)


def _agreement_check(proposal: TradeProposal, ceo_choice: AnalystChoice) -> GatekeeperCheck:
    total = len(proposal.analyst_votes)
    agreeing = sum(1 for v in proposal.analyst_votes if v.choice == ceo_choice)
    passed = total == 0 or agreeing > total / 2
    return GatekeeperCheck(
        id="agreement",
        label="Multi-Agent Agreement",
        passed=passed,
        detail=f"{agreeing}/{total} analysts agree with {ceo_choice.upper()}.",
    )


def _debate_check(debate: Debate | None, ceo_choice: AnalystChoice) -> GatekeeperCheck:
    passed = debate is None or debate.final_recommendation == ceo_choice
    detail = (
        "No debate on record for this proposal."
        if debate is None
        else f"The committee's final recommendation was {debate.final_recommendation.upper()}."
    )
    return GatekeeperCheck(id="debate", label="AI Debate Outcome", passed=passed, detail=detail)


def _exposure_check(portfolio: PaperPortfolio, risk_limits: RiskLimits) -> GatekeeperCheck:
    open_count = len(portfolio.positions)
    passed = open_count < risk_limits.max_open_positions
    return GatekeeperCheck(
        id="exposure",
        label="Portfolio Exposure",
        passed=passed,
        detail=f"{open_count}/{risk_limits.max_open_positions} positions already open.",
    )


def _correlation_check(proposal: TradeProposal, portfolio: PaperPortfolio) -> GatekeeperCheck:
    category = SYMBOL_CATEGORY.get(proposal.symbol)
    correlated = sum(1 for p in portfolio.positions if SYMBOL_CATEGORY.get(p.symbol) == category) if category else 0
    passed = correlated <= MAX_CORRELATED_POSITIONS
    return GatekeeperCheck(
        id="correlation",
        label="Correlated Positions",
        passed=passed,
        detail=f"{correlated} existing open position(s) already share {proposal.symbol}'s {category or 'unknown'} category.",
    )


def _risk_warning_check(proposal: TradeProposal, risk_warnings: list[RiskWarning]) -> GatekeeperCheck:
    warning = next((w for w in risk_warnings if w.symbol == proposal.symbol and w.severity == "critical"), None)
    passed = warning is None
    detail = warning.message if warning else f"No active critical risk warning for {proposal.symbol}."
    return GatekeeperCheck(id="risk_warning", label="Active Risk Warnings", passed=passed, detail=detail)


# v0.7 Feature 51 — the Market Intelligence Department's real mechanical
# enforcement of the brief's own closing rule: "No department may
# recommend a trade without first explaining the current market
# environment... every recommendation must be justified before capital is
# committed." A trade cannot pass the Gatekeeper while the department's
# own real, current Market Quality Score reads "avoid_trading" — the same
# real MarketIntelligenceState every new TradeProposal already carries a
# summary of (see app/executive.py's generate_proposal), never a second,
# independently-computed read.
def _market_intelligence_check(market_intelligence: MarketIntelligenceState) -> GatekeeperCheck:
    passed = market_intelligence.quality.tier != "avoid_trading"
    detail = f"Market Quality reads {market_intelligence.quality.tier.replace('_', ' ')} ({market_intelligence.quality.score:.0f}/100) — {market_intelligence.quality.reasoning}"
    return GatekeeperCheck(id="market_intelligence", label="Market Intelligence Quality", passed=passed, detail=detail)


# Design Bible Chapter 70 Part 3 addendum — "The Weighted Executive
# Decision Engine must feed recommendations into the Trade Gatekeeper,
# while remaining advisory only." Implemented as one more unconditional
# check in the same `all(checks)` list every other real Gatekeeper check
# already uses — WEDE gets exactly the same authority as Decision
# Confidence or Portfolio Exposure: it can contribute to a REJECTION,
# never force an approval, and it cannot override or skip any other
# check. `weighted_recommendation` is None only when the caller had
# nothing to evaluate (ceo_choice == "wait" never reaches this function
# at all — see app/executive.py's resolve_proposal) or a caller predates
# this wiring (e.g. a direct unit test) — vacuously passes in that case,
# the same honest pattern `_debate_check` above already uses for a
# missing `debate`.
def _weighted_executive_check(weighted_recommendation: WeightedExecutiveRecommendation | None) -> GatekeeperCheck:
    if weighted_recommendation is None:
        return GatekeeperCheck(
            id="weighted_executive",
            label="Weighted Executive Recommendation",
            passed=True,
            detail="Weighted Executive Decision Engine not evaluated for this decision.",
        )
    passed = weighted_recommendation.weighted_action in _WEDE_TRADING_ACTIONS
    detail = (
        f"Weighted Executive Decision Engine ({weighted_recommendation.profile.replace('_', ' ')} profile, "
        f"{weighted_recommendation.market_regime.replace('_', ' ')} regime) recommends "
        f"{weighted_recommendation.weighted_action.replace('_', ' ')} — "
        f"{'consistent with' if passed else 'advises against'} proceeding."
    )
    return GatekeeperCheck(id="weighted_executive", label="Weighted Executive Recommendation", passed=passed, detail=detail)


# Behavioral Circuit Breaker — real revenge-trading detection, the tenth
# entry in evaluate_gatekeeper()'s own pure-AND check list below. See
# app/behavioral_risk.py's module docstring for the four real signals,
# the corroboration requirement, and the honesty/Account-Awareness
# boundaries. A `triggered` read fails only this one check for this one
# proposal — every other check still runs independently, and a real
# GatekeeperRejection is recorded automatically the same way any other
# failed check's rejection already is.
def _behavioral_check(
    proposal: TradeProposal,
    trade_history: list[PaperTrade],
    now_sim_minutes: int,
    cooldown_minutes: int,
    size_increase_threshold_pct: float,
) -> GatekeeperCheck:
    read = compute_behavioral_check(proposal, trade_history, now_sim_minutes, cooldown_minutes, size_increase_threshold_pct)
    passed = read.status != "triggered"
    detail = " ".join(read.reasons) if read.reasons else "No recent-loss behavioral pattern detected for this proposal."
    return GatekeeperCheck(id="behavioral", label="Behavioral Circuit Breaker", passed=passed, detail=detail)


def evaluate_gatekeeper(
    proposal: TradeProposal,
    ceo_choice: AnalystChoice,
    debate: Debate | None,
    portfolio: PaperPortfolio,
    risk_limits: RiskLimits,
    risk_warnings: list[RiskWarning],
    market_intelligence: MarketIntelligenceState,
    now_sim_minutes: int,
    weighted_recommendation: WeightedExecutiveRecommendation | None = None,
    min_confidence_override: float | None = None,
    behavioral_cooldown_minutes: int | None = None,
    behavioral_size_increase_threshold_pct: float | None = None,
) -> "GatekeeperVerdict":
    """`min_confidence_override` (Design Bible Chapter 75) — the real,
    disclosed points app/trading_modes.py's Daily Circuit Breaker adds to
    the required confidence while a tier is active. None (the default)
    means the ordinary MIN_CONFIDENCE applies, unchanged from before this
    chapter — every existing caller that doesn't pass this stays exactly
    as it was.

    `behavioral_cooldown_minutes`/`behavioral_size_increase_threshold_pct`
    — the CEO's own real, editable Behavioral Circuit Breaker thresholds
    (TradingModeState.behavioral_cooldown_minutes/
    behavioral_size_increase_threshold_pct). None (the default) falls
    back to BEHAVIORAL_COOLDOWN_MINUTES/BEHAVIORAL_SIZE_INCREASE_THRESHOLD_PCT
    above, the same "unconfigured caller behaves like the CEO's own
    out-of-the-box defaults" convention `min_confidence_override` already
    established.

    `now_sim_minutes` is required (not optional) because the Behavioral
    Circuit Breaker cannot honestly evaluate timing without it — both
    real production call sites (app/executive.py's resolve_proposal, fed
    from app/nexus.py's auto-resolution loop and app/state.py's CEO-click
    path) already have this value in scope, so this adds no new plumbing
    burden anywhere real."""
    from app.schemas import GatekeeperVerdict  # local import avoids a schemas.py forward-reference cycle at module load

    checks = [
        _confidence_check(proposal, min_confidence_override if min_confidence_override is not None else MIN_CONFIDENCE),
        _risk_manager_check(proposal, ceo_choice),
        _agreement_check(proposal, ceo_choice),
        _debate_check(debate, ceo_choice),
        _exposure_check(portfolio, risk_limits),
        _correlation_check(proposal, portfolio),
        _risk_warning_check(proposal, risk_warnings),
        _market_intelligence_check(market_intelligence),
        _weighted_executive_check(weighted_recommendation),
        _behavioral_check(
            proposal,
            portfolio.trade_history,
            now_sim_minutes,
            behavioral_cooldown_minutes if behavioral_cooldown_minutes is not None else BEHAVIORAL_COOLDOWN_MINUTES,
            behavioral_size_increase_threshold_pct if behavioral_size_increase_threshold_pct is not None else BEHAVIORAL_SIZE_INCREASE_THRESHOLD_PCT,
        ),
    ]
    approved = all(c.passed for c in checks)
    if approved:
        summary = f"APPROVED — all {len(checks)} gatekeeper checks passed."
    else:
        failed = [c.label for c in checks if not c.passed]
        summary = f"REJECTED — failed: {', '.join(failed)}."
    return GatekeeperVerdict(approved=approved, checks=checks, summary=summary, createdAt=_now_iso())


def grade_gatekeeper_rejections(rejections: list[GatekeeperRejection], watchlist: list[WatchlistEntry], now_sim_minutes: int) -> list[GatekeeperRejection]:
    """Resolves any "pending" rejection whose evaluation window has
    elapsed, purely from the real difference between the symbol's
    watchlist price now and at rejection time — never a placed order, so
    never a real P&L, just an honest "would this direction have been
    right" read using the same live price data every other real check in
    this module already uses."""
    if not rejections:
        return rejections
    prices = {w.symbol: w.last_price for w in watchlist}
    updated: list[GatekeeperRejection] = []
    for rejection in rejections:
        if rejection.outcome != "pending" or now_sim_minutes - rejection.rejected_sim_minutes < GATEKEEPER_EVAL_WINDOW_MINUTES:
            updated.append(rejection)
            continue
        current_price = prices.get(rejection.symbol)
        if current_price is None or rejection.price_at_rejection <= 0:
            updated.append(rejection)
            continue
        change_pct = (current_price - rejection.price_at_rejection) / rejection.price_at_rejection * 100
        would_have_won = change_pct > 0 if rejection.ceo_choice == "buy" else change_pct < 0
        updated.append(
            rejection.model_copy(
                update={
                    "outcome": "would_have_won" if would_have_won else "would_have_lost",
                    "resolved_price_change_pct": round(change_pct, 2),
                    "resolved_at": _now_iso(),
                }
            )
        )
    return updated
