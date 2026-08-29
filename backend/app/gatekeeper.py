"""TradeGatekeeper — v0.7 Feature 20, the firm's final-approval AI.

Sits between the CEO's real buy/sell call (app/executive.py's
resolve_proposal) and the order actually being placed. Every check here
reads real state already computed elsewhere in this codebase — the same
six analyst votes, the real Decision Confidence Engine score (Feature
15), the real AI Debate outcome (Feature 17), the portfolio's real open
positions, and Sentinel/Guardian's real standing risk watch — never a
fabricated signal. The v0.7 brief's much longer checklist also names
multi-timeframe confirmation — closed by CEO directive "Professional
Quant Trading Core," Phase B (app/multi_timeframe.py, now a real Decision
Confidence Engine factor; no dedicated Gatekeeper check was added for
it, since a confidence-engine factor already contributes to the
Gatekeeper's existing Decision Confidence check rather than needing a
second, parallel gate on the same signal) — plus support/resistance
quality, volume confirmation, liquidity, the *timing* of upcoming news
(this codebase generates news reactively, never schedules it in advance),
strategy match, and historical performance of similar setups — none of
these have a real data source in this codebase and none are invented
here; see app/confidence.py's module docstring for the same honesty
boundary already established for an overlapping list. Stop-loss
placement (formerly on this same "no real data source" list) is now
real — CEO directive "Hard Risk Gates 2.0 — Stop-Loss / Position-Risk
Enforcement" made it the fourteenth check (`_valid_stop_check`, below),
plus a fifteenth (`_max_loss_check`) enforcing the theoretical planned
loss against the account's real risk-per-trade budget as an explicit,
auditable backstop: the paper broker's real, previously-unused
stop_loss/take_profit order mechanism (app/broker.py) is now actually
placed at every real fill, using app/position_sizing.py's own real
ATR-based stop distance.

A trade the Gatekeeper blocks never executes — there is no P&L to grade.
Instead its real *hypothetical* outcome is tracked (GatekeeperRejection)
and graded later purely from the symbol's own real subsequent watchlist
price movement, once GATEKEEPER_EVAL_WINDOW_MINUTES of simulated time
has passed — see grade_gatekeeper_rejections.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from app.behavioral_risk import compute_behavioral_check
from app.risk_engine import evaluate_sentinel_risk
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
    TradingRestriction,
    WatchlistEntry,
    WeightedExecutiveRecommendation,
)
from app.trading_restrictions import find_blocking_restriction
from app.watchlist import SYMBOL_CATEGORY

MIN_CONFIDENCE = 55.0
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
        code="gatekeeper_confidence",
    )


def _risk_manager_check(proposal: TradeProposal, ceo_choice: AnalystChoice) -> GatekeeperCheck:
    risk_vote = next((v for v in proposal.analyst_votes if v.role == "risk"), None)
    passed = risk_vote is None or risk_vote.choice == ceo_choice
    detail = risk_vote.reasoning if risk_vote else "No risk analyst read available for this proposal."
    return GatekeeperCheck(id="risk_manager", label="Risk Manager Alignment", passed=passed, detail=detail, code="gatekeeper_risk_manager")


def _agreement_check(proposal: TradeProposal, ceo_choice: AnalystChoice) -> GatekeeperCheck:
    total = len(proposal.analyst_votes)
    agreeing = sum(1 for v in proposal.analyst_votes if v.choice == ceo_choice)
    passed = total == 0 or agreeing > total / 2
    return GatekeeperCheck(
        id="agreement",
        label="Multi-Agent Agreement",
        passed=passed,
        detail=f"{agreeing}/{total} analysts agree with {ceo_choice.upper()}.",
        code="gatekeeper_agreement",
    )


def _debate_check(debate: Debate | None, ceo_choice: AnalystChoice) -> GatekeeperCheck:
    passed = debate is None or debate.final_recommendation == ceo_choice
    detail = (
        "No debate on record for this proposal."
        if debate is None
        else f"The committee's final recommendation was {debate.final_recommendation.upper()}."
    )
    return GatekeeperCheck(id="debate", label="AI Debate Outcome", passed=passed, detail=detail, code="gatekeeper_debate")


def _exposure_check(portfolio: PaperPortfolio, risk_limits: RiskLimits) -> GatekeeperCheck:
    open_count = len(portfolio.positions)
    passed = open_count < risk_limits.max_open_positions
    return GatekeeperCheck(
        id="exposure",
        label="Portfolio Exposure",
        passed=passed,
        detail=f"{open_count}/{risk_limits.max_open_positions} positions already open.",
        code="gatekeeper_exposure",
    )


def _correlation_check(proposal: TradeProposal, portfolio: PaperPortfolio, risk_limits: RiskLimits) -> GatekeeperCheck:
    """Category co-occurrence — a real but crude proxy (this codebase
    has no real sector taxonomy, only each symbol's own ResearchCategory
    — see app/portfolio_intelligence.py's identical, already-established
    note). CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism," Phase 4 promoted the threshold itself
    (previously hardcoded MAX_CORRELATED_POSITIONS=2) to a real
    CEO-configurable `risk_limits.max_correlated_positions` — default
    still 2, so today's real behavior is unchanged unless the CEO
    actually adjusts it. The genuinely statistical version of this same
    question (real Pearson correlation against currently-held positions)
    now runs EARLIER, pre-proposal, in app/opportunity_gatekeeper.py's
    own `correlated_position_count` check — this later-stage check stays
    real and complementary, not replaced."""
    category = SYMBOL_CATEGORY.get(proposal.symbol)
    correlated = sum(1 for p in portfolio.positions if SYMBOL_CATEGORY.get(p.symbol) == category) if category else 0
    passed = correlated <= risk_limits.max_correlated_positions
    return GatekeeperCheck(
        id="correlation",
        label="Correlated Positions",
        passed=passed,
        detail=f"{correlated} existing open position(s) already share {proposal.symbol}'s {category or 'unknown'} category.",
        code="gatekeeper_correlation",
    )


def _risk_warning_check(proposal: TradeProposal, risk_warnings: list[RiskWarning]) -> GatekeeperCheck:
    """Live end-to-end QA pass (2026-08-26) found this check was
    structurally unsatisfiable: the only producer of `risk_warnings`
    (app/risk_engine.py's monitor_portfolio, Guardian's standing watch)
    tags its one critical warning `symbol="PORTFOLIO"` (a portfolio-wide
    drawdown breach) and every per-symbol concentration warning
    `severity="warning"` — so a match on `proposal.symbol` specifically
    with `severity == "critical"` could never fire. Fixed to also match
    the portfolio-wide marker, since a critical drawdown breach is a
    real reason to block any new trade, not just one on a specific
    symbol — the same real signal this check always intended to enforce."""
    warning = next((w for w in risk_warnings if w.symbol in (proposal.symbol, "PORTFOLIO") and w.severity == "critical"), None)
    passed = warning is None
    detail = warning.message if warning else f"No active critical risk warning for {proposal.symbol} or the portfolio as a whole."
    return GatekeeperCheck(id="risk_warning", label="Active Risk Warnings", passed=passed, detail=detail, code="gatekeeper_risk_warning")


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
    return GatekeeperCheck(id="market_intelligence", label="Market Intelligence Quality", passed=passed, detail=detail, code="gatekeeper_market_intelligence")


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
            code="gatekeeper_weighted_executive",
        )
    passed = weighted_recommendation.weighted_action in _WEDE_TRADING_ACTIONS
    detail = (
        f"Weighted Executive Decision Engine ({weighted_recommendation.profile.replace('_', ' ')} profile, "
        f"{weighted_recommendation.market_regime.replace('_', ' ')} regime) recommends "
        f"{weighted_recommendation.weighted_action.replace('_', ' ')} — "
        f"{'consistent with' if passed else 'advises against'} proceeding."
    )
    return GatekeeperCheck(id="weighted_executive", label="Weighted Executive Recommendation", passed=passed, detail=detail, code="gatekeeper_weighted_executive")


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
    return GatekeeperCheck(id="behavioral", label="Behavioral Circuit Breaker", passed=passed, detail=detail, code="gatekeeper_behavioral")


# CEO Company Health + Live Market Realism directive, Feature 23 — the
# Gatekeeper's eleventh check, and the one real gap the Prop-Firm Risk
# Intelligence Addendum (Piece 10b/Piece 11) explicitly disclosed rather
# than filled: app/prop_firm.py's compute_account_risk_budget_status()
# already computes "remaining room before the drawdown ceiling" for a
# real Account, but its own docstring names the exact reason it can't
# gate anything with that number — "no live TradeProposal execution
# routes to a secondary Account yet." app/portfolio.py's
# close_position() (Piece 10b) already snapshots the identical real
# formula — max(0, max_drawdown_pct - lifetime_drawdown_pct) — for the
# PRIMARY portfolio, but only AFTER a trade closes, for audit, never to
# gate anything. This check reuses that exact formula, read BEFORE the
# trade instead of after: does this proposal's own real
# RiskLimits.risk_per_trade_pct fit inside the room actually remaining
# before the company's own real drawdown ceiling? No new risk engine —
# same math, same inputs, read one step earlier.
def _failure_boundary_check(portfolio: PaperPortfolio, risk_limits: RiskLimits) -> GatekeeperCheck:
    lifetime_drawdown_pct = max(0.0, -portfolio.total_pnl_pct)
    remaining_pct = round(max(0.0, risk_limits.max_drawdown_pct - lifetime_drawdown_pct), 2)
    passed = risk_limits.risk_per_trade_pct < remaining_pct
    detail = (
        f"{remaining_pct:.2f}% of drawdown room remains before the {risk_limits.max_drawdown_pct:.2f}% ceiling; "
        f"this trade's own risk-per-trade is {risk_limits.risk_per_trade_pct:.2f}% — "
        f"{'within' if passed else 'would exceed'} the remaining budget."
    )
    return GatekeeperCheck(id="failure_boundary", label="Failure Boundary Distance", passed=passed, detail=detail, code="gatekeeper_failure_boundary")


# Live end-to-end QA pass (2026-08-26) found a real, evidence-based gap:
# every other check here reads a signal frozen at proposal-creation time
# (app/nexus.py's _generate_trade_proposals), including the risk
# analyst's own vote baked from a ONE-TIME evaluate_sentinel_risk() call.
# A proposal can sit pending up to PROPOSAL_EXPIRY_SIM_MINUTES (Learning
# Mode, or a slow CEO click) — long enough for an unrelated trade
# closing in the meantime to cross the account's daily/weekly/monthly
# loss halt or max-trades-per-day cap, with nothing here noticing before
# this trade executes. This check re-runs Sentinel's own real gate
# (app/risk_engine.py's evaluate_sentinel_risk — no new risk math, same
# function, read fresh) at the moment of resolution instead of trusting
# the frozen read. `quantity`/`price`/`sim_day` are None only for a
# caller with nothing to evaluate yet (mirrors `_debate_check`'s /
# `_weighted_executive_check`'s existing vacuous-pass convention for a
# proposal that hasn't reached execution, e.g. a direct unit test) —
# every real production call site (app/executive.py's resolve_proposal)
# always has all three in scope. Constitution Article I: "Protect
# capital first."
def _account_halt_check(
    proposal: TradeProposal,
    portfolio: PaperPortfolio,
    risk_limits: RiskLimits,
    quantity: float | None,
    price: float | None,
    sim_day: int | None,
) -> GatekeeperCheck:
    if quantity is None or price is None or sim_day is None:
        return GatekeeperCheck(
            id="account_halt",
            label="Account Risk Halt (live)",
            passed=True,
            detail="Not evaluated for this call — no quantity/price/sim_day in scope.",
            code="gatekeeper_account_halt",
        )
    warning = evaluate_sentinel_risk(risk_limits, portfolio, symbol=proposal.symbol, proposed_value=quantity * price, sim_day=sim_day)
    passed = warning is None or warning.severity != "critical"
    detail = warning.message if (warning is not None and not passed) else "No active account-level risk halt right now."
    return GatekeeperCheck(id="account_halt", label="Account Risk Halt (live)", passed=passed, detail=detail, code="gatekeeper_account_halt")


def _trading_restriction_check(proposal: TradeProposal, trading_restrictions: list[TradingRestriction]) -> GatekeeperCheck:
    """CEO directive "Layered Kill Switches" — the Trade Gatekeeper's own
    defense-in-depth half of app/trading_restrictions.py's two real
    enforcement points (the other is proposal generation itself, see
    app/nexus.py's `_generate_trade_proposals`). Catches a proposal that
    was already pending the instant a restriction activates."""
    restriction = find_blocking_restriction(trading_restrictions, symbol=proposal.symbol, category=proposal.category)
    passed = restriction is None
    detail = (
        f"Trading is restricted on {restriction.scope} {restriction.target}: {restriction.reason}"
        if restriction is not None
        else "No active trading restriction on this symbol or category."
    )
    return GatekeeperCheck(id="trading_restriction", label="Trading Restriction", passed=passed, detail=detail, code="gatekeeper_trading_restriction")


# CEO directive "Hard Risk Gates 2.0 — Stop-Loss / Position-Risk
# Enforcement," Gate 3 (Valid Stop) — "Every trade must have a
# measurable, enforceable risk definition BEFORE execution." Closes the
# exact gap this module's own docstring above used to disclose (stop-
# loss placement "has no real data source... none are invented here"):
# app/position_sizing.py's compute_volatility_sizing() already computes
# a real, ATR-based stop DISTANCE (the same Chandelier Stop convention
# this codebase's backtest engines already use) for every real proposal;
# app/executive.py's resolve_proposal() now evaluates it BEFORE calling
# this function and passes the result straight through, never
# recomputed here. `stop_evaluated=False` (the default) vacuously
# passes, the same convention `_debate_check`/`_weighted_executive_check`/
# `_account_halt_check` above already use for a caller that doesn't
# thread this argument through yet (a direct unit test, or a legacy call
# site) — `stop_distance` alone can't disambiguate "not evaluated" from
# "evaluated, no real evidence exists" since both are legitimately
# `None`. Every real production call (resolve_proposal) always sets
# `stop_evaluated=True`, so a genuine missing/invalid stop for a real
# trade is a real, enforced rejection, never silently waved through.
def _valid_stop_check(stop_distance: float | None, stop_evaluated: bool) -> GatekeeperCheck:
    if not stop_evaluated:
        return GatekeeperCheck(
            id="valid_stop",
            label="Valid Stop-Loss",
            passed=True,
            detail="Not evaluated for this call — no stop-distance evidence in scope.",
            code="gatekeeper_valid_stop",
        )
    passed = stop_distance is not None and math.isfinite(stop_distance) and stop_distance > 0
    detail = (
        f"Real ATR-based stop distance of {stop_distance:.4f} computed for this trade — a measurable risk boundary exists."
        if passed and stop_distance is not None
        else (
            "No real ATR-based stop-loss distance could be computed for this symbol yet (insufficient real candle "
            "history) — every trade must have a measurable, enforceable stop before execution."
        )
    )
    return GatekeeperCheck(id="valid_stop", label="Valid Stop-Loss", passed=passed, detail=detail, code="gatekeeper_valid_stop")


# CEO directive "Hard Risk Gates 2.0 — Stop-Loss / Position-Risk
# Enforcement," Gate 5 (Account Risk Limit) — "Reject if planned loss
# exceeds the permitted risk budget for the current account stage."
# `planned_loss_usd` (quantity x the real ATR stop distance) and
# `risk_budget_usd` (equity x risk_limits.risk_per_trade_pct) are both
# computed once by app/executive.py's resolve_proposal(), reusing the
# exact same real quantity/stop distance/equity `_valid_stop_check`
# above already reads — never a second, independently-derived number.
# Defense-in-depth, not a new constraint: app/position_sizing.py's own
# real ATR-based volatility cap already narrows the candidate quantity
# so planned loss stays inside this same budget by construction (see
# that module's own `_volatility_sizing`/`compute_volatility_sizing`
# docstring) — this check almost never actually fires in practice, but
# makes that guarantee an explicit, auditable, hard-enforced backstop
# rather than an implicit side effect of the sizing formula, exactly
# this directive's own "every decision must be auditable" principle.
# Same two-part "not evaluated" vs. "evaluated, no real budget" honesty
# convention `_valid_stop_check` above establishes — a bare `None` for
# either input is a legitimate real state, not just an unready caller.
def _max_loss_check(planned_loss_usd: float | None, risk_budget_usd: float | None) -> GatekeeperCheck:
    if planned_loss_usd is None or risk_budget_usd is None:
        return GatekeeperCheck(
            id="max_loss",
            label="Max Planned Loss",
            passed=True,
            detail="Not evaluated for this call — no real planned-loss/risk-budget figures in scope.",
            code="gatekeeper_max_loss",
        )
    passed = planned_loss_usd <= risk_budget_usd + 1e-6
    overage = round(max(0.0, planned_loss_usd - risk_budget_usd), 2)
    detail = (
        f"Planned loss if stopped out: ${planned_loss_usd:,.2f} against a ${risk_budget_usd:,.2f} risk-per-trade budget — "
        + (
            "within the permitted budget."
            if passed
            else f"${overage:,.2f} above the permitted budget."
        )
    )
    return GatekeeperCheck(id="max_loss", label="Max Planned Loss", passed=passed, detail=detail, code="gatekeeper_max_loss")


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
    quantity: float | None = None,
    price: float | None = None,
    sim_day: int | None = None,
    trading_restrictions: list[TradingRestriction] | None = None,
    stop_distance: float | None = None,
    stop_evaluated: bool = False,
    planned_loss_usd: float | None = None,
    risk_budget_usd: float | None = None,
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
    burden anywhere real.

    `quantity`/`price`/`sim_day` feed the Account Risk Halt check above —
    the real, final position size and fill-signal price already resolved
    by the caller, plus the sim day derived the same way every other
    real call site already does (`now_sim_minutes // 1440`). None
    vacuously passes that one check, matching this function's existing
    convention for an unready caller.

    `trading_restrictions` (CEO directive "Layered Kill Switches," see
    app/trading_restrictions.py) feeds the new Trading Restriction
    check — None/empty behaves exactly as before this parameter existed
    (nothing restricted).

    `stop_distance`/`stop_evaluated` (CEO directive "Hard Risk Gates 2.0
    — Stop-Loss / Position-Risk Enforcement") feed the Valid Stop-Loss
    check — see `_valid_stop_check()`'s own docstring for why this needs
    two arguments (a bare `None` is a legitimate real "no ATR evidence"
    read, not just "caller doesn't support this yet").

    `planned_loss_usd`/`risk_budget_usd` (same directive, Gate 5) feed
    the Max Planned Loss check — see `_max_loss_check()`'s own
    docstring. Both `None` for any caller that hasn't been threaded
    through yet, the same honest convention as every pair above."""
    from app.schemas import GatekeeperVerdict  # local import avoids a schemas.py forward-reference cycle at module load

    checks = [
        _confidence_check(proposal, min_confidence_override if min_confidence_override is not None else MIN_CONFIDENCE),
        _risk_manager_check(proposal, ceo_choice),
        _agreement_check(proposal, ceo_choice),
        _debate_check(debate, ceo_choice),
        _exposure_check(portfolio, risk_limits),
        _correlation_check(proposal, portfolio, risk_limits),
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
        _failure_boundary_check(portfolio, risk_limits),
        _account_halt_check(proposal, portfolio, risk_limits, quantity, price, sim_day),
        _trading_restriction_check(proposal, trading_restrictions or []),
        _valid_stop_check(stop_distance, stop_evaluated),
        _max_loss_check(planned_loss_usd, risk_budget_usd),
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
