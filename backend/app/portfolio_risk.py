"""app/portfolio_risk.py — CEO directive "Portfolio Risk Engine +
Firm-Wide Risk Governance."

WHAT THIS IS. A real COMPOSITION layer over risk state this codebase
already computes honestly — never a second, parallel risk engine.
`compute_portfolio_risk_snapshot()` packages already-real reads
(app/portfolio_intelligence.py's exposure/correlation/heat, app/
risk_engine.py's real peak-to-trough drawdown, the real daily circuit
breaker, the real Emergency Stop flag) into one canonical, timestamped
snapshot. `evaluate_pretrade_risk_decision()` composes every real
Sentinel/Guardian check for one candidate trade
(app/risk_engine.py::evaluate_all_sentinel_checks()/
evaluate_guardian_exposure()) into a single, fully-explained
APPROVED/APPROVED_WITH_REDUCTION/REJECTED/HALTED decision — never a
black-box "Risk = 72" score.

A Phase 0 audit for this directive found most of the requested
capability already real and working: hard position/drawdown/daily-loss/
weekly-loss/monthly-loss/open-position/concentration gates
(app/risk_engine.py), real Pearson correlation and portfolio heat
(app/portfolio_intelligence.py), a real -10/-20/-35/-50/-70% portfolio
stress-test ladder and four named scenario simulations
(app/black_swan.py), a real firm-wide kill switch that genuinely blocks
new proposals/CEO decisions and requires an explicit resume
(app/emergency_stop.py), and a real escalating daily circuit breaker
(app/trading_modes.py). This module's job is to UNIFY those into one
canonical read and one fully-explained pre-trade decision, and to fix
the one real, disclosed bug the audit found (see app/analytics.py's
`max_drawdown_pct()`/`real_peak_equity()` — the old drawdown proxy
measured loss from the account's ORIGINAL starting balance, not from
its own real peak, and ignored unrealized loss on still-open positions).

NEVER ENFORCEMENT ITSELF. `evaluate_pretrade_risk_decision()` is
advisory/explanatory — it reads the exact same real checks
app/gatekeeper.py's vote pipeline already runs and already enforces;
this module never bypasses, duplicates, or weakens that enforcement.

TREND ENGINE NEVER OVERRIDES RISK. app/trend_engine.py (this session's
prior directive) is not imported here and has no path into any decision
this module makes — trend strength is evidence for a strategy/agent to
weigh, never risk permission.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.analytics import max_drawdown_pct
from app.backtest_primitives import regime_trend_at
from app.ema_pullback_research import CHANDELIER_ATR_MULTIPLIER, CHANDELIER_ATR_PERIOD
from app.market_data import MarketDataProvider
from app.portfolio_intelligence import PROPOSAL_CANDLE_COUNT, PROPOSAL_TIMEFRAME, compute_portfolio_intelligence, pearson_correlation, returns
from app.risk_engine import compute_risk_budget_status, evaluate_all_sentinel_checks, evaluate_guardian_exposure, portfolio_equity
from app.schemas import (
    CorrelationRegimeState,
    DailyCircuitBreakerTier,
    LiquidityStatus,
    MarginalRiskVerdict,
    OrderSide,
    PaperPortfolio,
    PaperPosition,
    PortfolioIntelligence,
    PortfolioMarginalRiskDecision,
    PortfolioRiskSnapshot,
    PortfolioRiskState,
    PretradeRiskDecision,
    PretradeRiskVerdict,
    RiskImpactLevel,
    RiskLimits,
)
from app.technical_indicators import atr, ema_series
from app.volume_analysis import relative_volume

# A correlated cluster at or above this share of equity is treated as a
# real concentration concern in its own right, on top of whatever
# per-symbol concentration limit already exists — the CEO brief's own
# "the firm may effectively be making one large risk bet" language.
_RESTRICTED_CLUSTER_PCT = 40.0

# "Portfolio Risk Engine + Cross-Trade Capital Allocation" — the one
# versioned rule this module's Marginal Risk Test ships today. A future
# methodology change must bump this so an old PortfolioMarginalRiskDecision
# is never silently reinterpreted under different math.
MARGINAL_RISK_POLICY_VERSION = "marginal_risk_v1"

# Real, disclosed thresholds — not fabricated to look sophisticated, but
# real choices this module makes and names. `_LIQUIDITY_LIMITED_RVOL`
# reuses app/volume_analysis.py's own relative-volume convention (1.0 =
# exactly average volume); below half of average is treated as thin.
_LIQUIDITY_LIMITED_RVOL = 0.5
# Average |pairwise correlation| across every currently-held pair
# (never just the candidate's own) — thresholds chosen so "elevated"
# starts noticeably above CORRELATION_CLUSTER_THRESHOLD's own 0.6
# cluster-membership bar (a portfolio can have zero real clusters and
# still show broadly elevated correlation), "extreme" only once the
# book is behaving like one undiversified bet.
_CORRELATION_REGIME_ELEVATED = 0.5
_CORRELATION_REGIME_EXTREME = 0.8
# How many times the reduction search recomputes real portfolio
# intelligence at a shrinking candidate size — each iteration halves the
# search interval, so 8 iterations resolves `allowed_value` to within
# proposed_value/256, plenty fine-grained for a dollar allocation while
# keeping the real per-iteration correlation recomputation cost bounded.
_REDUCTION_SEARCH_ITERATIONS = 8
# Below this dollar value a "reduced" allocation is treated as
# economically meaningless — the candidate is vetoed outright rather
# than approved for a token size nobody would actually want to trade.
_MIN_MEANINGFUL_ALLOCATION_USD = 1.0
# Same real regime proxy app/trend_engine.py's own regime-breakdown
# research already uses (app/backtest_primitives.py::regime_trend_at) —
# never a second, independently-tuned regime classifier.
_REGIME_EMA_PERIOD = 50
_REGIME_SLOPE_LOOKBACK = 20
_REGIME_SLOPE_THRESHOLD_PCT = 0.5


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_portfolio_risk_snapshot(
    portfolio: PaperPortfolio,
    limits: RiskLimits,
    intelligence: PortfolioIntelligence,
    *,
    daily_circuit_breaker_tier: DailyCircuitBreakerTier,
    daily_pnl_pct: float,
    emergency_stop_active: bool,
) -> PortfolioRiskSnapshot:
    """The one canonical portfolio risk read. Every field traces to a
    real, already-computed source — see this module's own docstring.
    `intelligence` (app/portfolio_intelligence.py::
    compute_portfolio_intelligence()) is passed in rather than
    recomputed, since it already needs a live MarketDataProvider this
    module has no reason to depend on separately."""
    equity = portfolio_equity(portfolio)
    drawdown_pct = max_drawdown_pct(portfolio.trade_history, portfolio.starting_balance, current_equity=equity)
    largest_cluster_pct = max((c.total_exposure_pct for c in intelligence.correlated_clusters), default=0.0)

    reasons: list[str] = []
    state: PortfolioRiskState
    if emergency_stop_active:
        state = "halted"
        reasons.append("Emergency Stop is active — no new trades until explicitly resumed.")
    elif daily_circuit_breaker_tier == "tier4":
        state = "halted"
        reasons.append(f"Daily circuit breaker at tier4 — the {limits.max_daily_loss_pct:.0f}% daily loss limit has been reached.")
    elif drawdown_pct >= limits.max_drawdown_pct:
        state = "halted"
        reasons.append(f"Portfolio drawdown ({drawdown_pct:.1f}%) is at or above the {limits.max_drawdown_pct:.0f}% limit.")
    else:
        if daily_circuit_breaker_tier in ("tier2", "tier3"):
            reasons.append(f"Daily circuit breaker at {daily_circuit_breaker_tier} — today's real loss is approaching the daily limit.")
        if limits.max_drawdown_pct > 0 and drawdown_pct >= limits.max_drawdown_pct * 0.75:
            reasons.append(f"Portfolio drawdown ({drawdown_pct:.1f}%) has reached 75%+ of the {limits.max_drawdown_pct:.0f}% limit.")
        if largest_cluster_pct >= _RESTRICTED_CLUSTER_PCT:
            reasons.append(f"The largest correlated cluster is {largest_cluster_pct:.1f}% of equity — effectively one concentrated bet.")
        if reasons:
            state = "restricted"
        else:
            warning_reasons: list[str] = []
            if daily_circuit_breaker_tier == "tier1":
                warning_reasons.append("Daily circuit breaker at tier1 — a real early warning, not yet a restriction.")
            if limits.max_drawdown_pct > 0 and drawdown_pct >= limits.max_drawdown_pct * 0.5:
                warning_reasons.append(f"Portfolio drawdown ({drawdown_pct:.1f}%) has reached 50%+ of the {limits.max_drawdown_pct:.0f}% limit.")
            state = "warning" if warning_reasons else "normal"
            reasons = warning_reasons

    return PortfolioRiskSnapshot(
        computedAt=_now_iso(),
        equity=round(equity, 2),
        cashBalance=round(portfolio.cash_balance, 2),
        startingBalance=portfolio.starting_balance,
        grossExposureUsd=round(intelligence.exposure.gross_exposure, 2),
        netExposureUsd=round(intelligence.exposure.net_exposure, 2),
        grossExposurePct=intelligence.exposure.gross_exposure_pct,
        netExposurePct=intelligence.exposure.net_exposure_pct,
        leverage=round(intelligence.exposure.gross_exposure / equity, 3) if equity > 0 else 0.0,
        openPositionsCount=len(portfolio.positions),
        maxOpenPositions=limits.max_open_positions,
        currentDrawdownPct=round(drawdown_pct, 2),
        maxDrawdownLimitPct=limits.max_drawdown_pct,
        dailyPnlPct=round(daily_pnl_pct, 2),
        maxDailyLossPct=limits.max_daily_loss_pct,
        correlatedClusters=intelligence.correlated_clusters,
        largestCorrelatedClusterPct=round(largest_cluster_pct, 1),
        dailyCircuitBreakerTier=daily_circuit_breaker_tier,
        emergencyStopActive=emergency_stop_active,
        riskState=state,
        riskStateReasons=reasons,
    )


def evaluate_pretrade_risk_decision(
    limits: RiskLimits,
    portfolio: PaperPortfolio,
    *,
    symbol: str,
    proposed_value: float,
    sim_day: int,
    emergency_stop_active: bool,
) -> PretradeRiskDecision:
    """The one authoritative, fully-explained pre-trade risk read for a
    candidate trade — composes app/risk_engine.py's own real
    `evaluate_all_sentinel_checks()` (every real hard-gate violation) and
    `evaluate_guardian_exposure()` (the real concentration warning) into
    one decision with every real reason attached. ADVISORY/EXPLANATORY
    ONLY: the real enforcement path (app/gatekeeper.py's vote pipeline,
    which already calls the single-reason `evaluate_sentinel_risk()`/
    `evaluate_guardian_exposure()`) is unchanged and unbypassed by this
    function — this exists so a rejected or reduced trade can show its
    FULL real reason list (Phase 17's "do not return only 'Risk = 72'"
    requirement), not to make or override the actual go/no-go call."""
    if emergency_stop_active:
        return PretradeRiskDecision(
            verdict="halted",
            symbol=symbol,
            proposedValue=proposed_value,
            reasons=["Emergency Stop is active — no new trades until explicitly resumed."],
            reasonCodes=["emergency_stop_active"],
            detail="Firm-wide Emergency Stop blocks every new trade candidate, regardless of this candidate's own real risk profile.",
        )

    sentinel_checks = evaluate_all_sentinel_checks(limits, portfolio, symbol=symbol, proposed_value=proposed_value, sim_day=sim_day)
    guardian_check = evaluate_guardian_exposure(limits, portfolio, symbol=symbol)
    all_checks = [*sentinel_checks, *([guardian_check] if guardian_check is not None else [])]

    if not all_checks:
        return PretradeRiskDecision(
            verdict="approved",
            symbol=symbol,
            proposedValue=proposed_value,
            reasons=[],
            reasonCodes=[],
            detail="No real risk check found a violation for this candidate.",
        )

    has_critical = any(c.severity == "critical" for c in all_checks)
    verdict: PretradeRiskVerdict = "rejected" if has_critical else "approved_with_reduction"
    return PretradeRiskDecision(
        verdict=verdict,
        symbol=symbol,
        proposedValue=proposed_value,
        reasons=[c.message for c in all_checks],
        reasonCodes=[c.code for c in all_checks if c.code is not None],
        detail=f"{len(all_checks)} real risk check(s) flagged this candidate ({'blocking' if has_critical else 'advisory-only'}).",
    )


def _average_pairwise_correlation(portfolio: PaperPortfolio, provider: MarketDataProvider) -> float | None:
    """The real average |correlation| across EVERY currently-held pair —
    deliberately NOT `PortfolioIntelligence.correlation_pairs` (that
    field only ever holds pairs that already cleared app/portfolio_
    intelligence.py's own CORRELATION_CLUSTER_THRESHOLD, so averaging it
    would silently bias upward). Reuses that same module's own public
    `pearson_correlation()`/`returns()` — never a second, independently-
    tuned correlation formula, just an unfiltered view over the same
    real data. None (never a fabricated 0.0) when fewer than two held
    symbols have enough real candle history to compare."""
    symbols = sorted({pos.symbol for pos in portfolio.positions})
    if len(symbols) < 2:
        return None
    returns_by_symbol: dict[str, list[float]] = {}
    for symbol in symbols:
        try:
            candles = provider.get_candles(symbol, PROPOSAL_TIMEFRAME, PROPOSAL_CANDLE_COUNT)
        except ValueError:
            continue
        returns_by_symbol[symbol] = returns([c.close for c in candles])
    magnitudes: list[float] = []
    for i, symbol_a in enumerate(symbols):
        for symbol_b in symbols[i + 1 :]:
            a, b = returns_by_symbol.get(symbol_a), returns_by_symbol.get(symbol_b)
            if not a or not b:
                continue
            magnitudes.append(abs(pearson_correlation(a, b)))
    if not magnitudes:
        return None
    return sum(magnitudes) / len(magnitudes)


def _classify_correlation_regime(avg_abs_correlation: float | None) -> CorrelationRegimeState:
    """Phase 7's explicit NORMAL/ELEVATED/EXTREME ask. `None` (fewer
    than two held pairs with real data to compare) reads as `normal` —
    the honest default, since there is no real evidence of elevated
    co-movement, not a claim that correlation is literally zero."""
    if avg_abs_correlation is None:
        return "normal"
    if avg_abs_correlation >= _CORRELATION_REGIME_EXTREME:
        return "extreme"
    if avg_abs_correlation >= _CORRELATION_REGIME_ELEVATED:
        return "elevated"
    return "normal"


def _candidate_liquidity_status(candles: list) -> LiquidityStatus:
    """Reuses app/volume_analysis.py's own real `relative_volume()` —
    the exact same relative-volume convention (and its own NaN/negative/
    infinite-volume guards from this session's earlier chaos-hardening
    pass) every other real liquidity read in this codebase already
    uses. `data_unavailable` (never a fabricated "valid") when there
    isn't yet enough real volume history."""
    rvol = relative_volume(candles)
    if rvol is None:
        return "data_unavailable"
    if rvol < _LIQUIDITY_LIMITED_RVOL:
        return "limited"
    return "valid"


def _candidate_regime_status(candles: list) -> str:
    """The same real, disclosed regime proxy app/trend_engine.py's own
    regime-conditional research already uses (app/backtest_primitives.
    py::regime_trend_at()) — never a second, independently-tuned regime
    classifier for this one candidate."""
    ema_values = ema_series(candles, _REGIME_EMA_PERIOD)
    if not ema_values or len(candles) < 2:
        return "unknown — insufficient real candle history"
    return regime_trend_at(ema_values, _REGIME_EMA_PERIOD, len(candles) - 1, slope_lookback=_REGIME_SLOPE_LOOKBACK, slope_threshold_pct=_REGIME_SLOPE_THRESHOLD_PCT)


def _candidate_individual_risk_usd(candles: list, quantity: float) -> float | None:
    """The exact same real Chandelier-Stop convention app/portfolio_
    intelligence.py's own per-position capital-at-risk read already
    uses (CHANDELIER_ATR_MULTIPLIER * real ATR), applied to this
    hypothetical candidate. None (never a fabricated number) when there
    isn't yet enough real candle history for a real ATR read."""
    atr_value = atr(candles, period=CHANDELIER_ATR_PERIOD)
    if atr_value is None or atr_value <= 0:
        return None
    return quantity * (CHANDELIER_ATR_MULTIPLIER * atr_value)


def _synthetic_portfolio(portfolio: PaperPortfolio, *, symbol: str, side: OrderSide, quantity: float, price: float) -> PaperPortfolio:
    """A hypothetical hold-through of one candidate position, used ONLY
    to recompute real portfolio intelligence for the Marginal Risk
    Test's own AFTER state — never persisted, never a real trade, never
    returned to any caller. Cash-secured simplification (disclosed in
    `PortfolioMarginalRiskDecision`'s own docstring): cash is reduced by
    the requested notional regardless of side, mirroring app/
    portfolio.py::open_position()'s own real cash-commitment behavior
    for this codebase's cash-secured paper-account model (no true
    margin/short-borrowing concept exists here)."""
    synthetic_position = PaperPosition(
        id=f"marginal-risk-synthetic-{symbol}",
        symbol=symbol,
        side=side,
        quantity=quantity,
        entryPrice=price,
        currentPrice=price,
        unrealizedPnl=0.0,
        unrealizedPnlPct=0.0,
        openedBy="quant",
        confidence=0.0,
        openedAt=_now_iso(),
    )
    return portfolio.model_copy(update={"positions": [*portfolio.positions, synthetic_position], "cash_balance": portfolio.cash_balance - quantity * price})


def _concentration_impact(candidate_value: float, equity_after: float, limits: RiskLimits) -> RiskImpactLevel:
    """Reuses the EXACT existing single-symbol concentration limit
    Guardian's own `evaluate_guardian_exposure()` already enforces
    (`RiskLimits.max_sector_concentration_pct`) — never a new, invented
    threshold."""
    if equity_after <= 0:
        return "low"
    pct = candidate_value / equity_after * 100
    if pct >= limits.max_sector_concentration_pct:
        return "high"
    if pct >= limits.max_sector_concentration_pct * 0.5:
        return "medium"
    return "low"


def _symbol_cluster_pct(intelligence: PortfolioIntelligence, symbol: str) -> float:
    """The real correlated-cluster share of equity for the specific
    cluster `symbol` itself belongs to — `0.0` if it isn't a member of
    any real cluster (a lone, uncorrelated candidate is never a
    cluster-concentration concern by this specific mechanism; its own
    single-symbol size is what `_concentration_impact()` measures
    instead). Deliberately narrower than the portfolio-WIDE
    `max(c.total_exposure_pct for c in ...)` read
    (`largest_cluster_pct_before/after` on the decision object) — that
    wider read can be driven by a real cluster this candidate has
    nothing to do with, which must never gate or explain THIS
    candidate's own decision."""
    return next((c.total_exposure_pct for c in intelligence.correlated_clusters if symbol in c.symbols), 0.0)


def _correlation_impact(candidate_cluster_pct_after: float) -> RiskImpactLevel:
    """Reuses this module's own `_RESTRICTED_CLUSTER_PCT` threshold —
    the same one `compute_portfolio_risk_snapshot()` above already
    treats as a real concentration concern — applied to the CANDIDATE's
    own real cluster share (see `_symbol_cluster_pct()`), never the
    portfolio-wide maximum (which could be driven by an unrelated
    cluster this candidate never joins)."""
    if candidate_cluster_pct_after >= _RESTRICTED_CLUSTER_PCT:
        return "high"
    if candidate_cluster_pct_after >= _RESTRICTED_CLUSTER_PCT * 0.5:
        return "medium"
    return "low"


def evaluate_marginal_portfolio_risk(
    limits: RiskLimits,
    portfolio: PaperPortfolio,
    provider: MarketDataProvider,
    *,
    symbol: str,
    proposed_value: float,
    sim_day: int,
    emergency_stop_active: bool,
    side: OrderSide = "buy",
) -> PortfolioMarginalRiskDecision:
    """The real, full, CEO-facing Marginal Risk Test (CEO directive
    "Portfolio Risk Engine + Cross-Trade Capital Allocation," Phase 17)
    — see `PortfolioMarginalRiskDecision`'s own docstring for the full
    real methodology and disclosed simplifications. Composes (never
    duplicates) `evaluate_pretrade_risk_decision()` above: a
    halted/rejected individual decision always vetoes the marginal one
    too, before any portfolio-level simulation runs. Used by the CEO's
    own Trade Approval view and the `/marginal-decision` endpoint —
    NOT by app/position_sizing.py's own sizing cap chain, which calls
    `compute_correlation_concentration_cap()` below instead (see that
    function's own docstring for why)."""
    return _marginal_portfolio_risk(
        limits, portfolio, provider, symbol=symbol, proposed_value=proposed_value, sim_day=sim_day, emergency_stop_active=emergency_stop_active, side=side, enforce_individual_risk_gates=True
    )


def compute_correlation_concentration_cap(
    limits: RiskLimits,
    portfolio: PaperPortfolio,
    provider: MarketDataProvider,
    *,
    symbol: str,
    proposed_value: float,
    sim_day: int,
    side: OrderSide = "buy",
) -> PortfolioMarginalRiskDecision:
    """The real read app/position_sizing.py's own real sizing cap chain
    uses — deliberately narrower than `evaluate_marginal_portfolio_
    risk()` above: `.allowed_value` here ONLY ever narrows for the real
    correlation/concentration-cluster reduction that function also
    computes, and deliberately never inherits its emergency-stop/
    critical-Sentinel-violation veto path. Composing that FULL veto here
    would make position_sizing.py — whose own module docstring is
    explicit that it answers "how much," never "whether" — silently
    start rejecting candidates on drawdown/daily-loss/position-size
    grounds that remain exclusively app/gatekeeper.py's real job
    downstream. `.decision` can still read `"data_blocked"` (no real
    candle history — the caller narrows to `proposed_value` unchanged in
    that case, matching every other cap's own "no evidence, no cap"
    convention) but never `"vetoed"` from a Sentinel/emergency-stop
    cause the way the full function's own veto path can. Returns the
    full decision object (not just the dollar figure) so
    `PositionSizingResult.marginal_risk_decision` can show the CEO
    exactly the same real reduction reasoning this cap actually
    applied — never a second, differently-scoped explanation."""
    return _marginal_portfolio_risk(
        limits, portfolio, provider, symbol=symbol, proposed_value=proposed_value, sim_day=sim_day, emergency_stop_active=False, side=side, enforce_individual_risk_gates=False
    )


def _marginal_portfolio_risk(
    limits: RiskLimits,
    portfolio: PaperPortfolio,
    provider: MarketDataProvider,
    *,
    symbol: str,
    proposed_value: float,
    sim_day: int,
    emergency_stop_active: bool,
    side: OrderSide,
    enforce_individual_risk_gates: bool,
) -> PortfolioMarginalRiskDecision:
    computed_at = _now_iso()
    try:
        candles = provider.get_candles(symbol, PROPOSAL_TIMEFRAME, PROPOSAL_CANDLE_COUNT)
    except ValueError:
        candles = []

    if not candles or candles[-1].close <= 0:
        return PortfolioMarginalRiskDecision(
            decision="data_blocked",
            symbol=symbol,
            requestedValue=proposed_value,
            allowedValue=0.0,
            reductionFactor=0.0,
            individualRiskUsd=None,
            portfolioCapitalAtRiskPctBefore=0.0,
            portfolioCapitalAtRiskPctAfter=0.0,
            grossExposureUsdBefore=0.0,
            grossExposureUsdAfter=0.0,
            netExposureUsdBefore=0.0,
            netExposureUsdAfter=0.0,
            leverageBefore=0.0,
            leverageAfter=0.0,
            largestClusterPctBefore=0.0,
            largestClusterPctAfter=0.0,
            correlationImpact="low",
            concentrationImpact="low",
            correlationRegimeState="normal",
            liquidityStatus="data_unavailable",
            regimeStatus="unknown — no real candle history",
            drawdownStatus="unknown — no real candle history for this candidate",
            dailyLossStatus="unknown — no real candle history for this candidate",
            vetoReasons=[f"No real candle history available for {symbol} — cannot evaluate portfolio risk impact."],
            warnings=[],
            riskPolicyVersion=MARGINAL_RISK_POLICY_VERSION,
            computedAt=computed_at,
        )

    price = candles[-1].close
    intelligence_before = compute_portfolio_intelligence(portfolio, provider, pending_proposal_count=0)
    equity_before = intelligence_before.equity
    largest_cluster_before = max((c.total_exposure_pct for c in intelligence_before.correlated_clusters), default=0.0)
    leverage_before = (intelligence_before.exposure.gross_exposure / equity_before) if equity_before > 0 else 0.0

    individual_decision = evaluate_pretrade_risk_decision(
        limits, portfolio, symbol=symbol, proposed_value=proposed_value, sim_day=sim_day, emergency_stop_active=emergency_stop_active
    )

    budget = compute_risk_budget_status(limits, portfolio, sim_day)
    drawdown_status = f"{budget.lifetime_drawdown_pct:.1f}% of {budget.max_drawdown_pct:.0f}% lifetime drawdown limit ({budget.remaining_drawdown_budget_pct:.1f}% remaining)."
    daily_loss_status = (
        f"Trading halted for today — {budget.halt_reason or 'a real daily objective has already been resolved'}."
        if budget.trading_halted
        else f"{budget.daily_loss_pct_today:.1f}% of {budget.max_daily_loss_pct:.0f}% daily loss limit ({budget.remaining_daily_loss_budget_pct:.1f}% remaining)."
    )
    correlation_regime_state = _classify_correlation_regime(_average_pairwise_correlation(portfolio, provider))
    liquidity_status = _candidate_liquidity_status(candles)
    regime_status = _candidate_regime_status(candles)
    quantity_full = proposed_value / price if price > 0 else 0.0
    individual_risk_usd = _candidate_individual_risk_usd(candles, quantity_full)

    if enforce_individual_risk_gates and (emergency_stop_active or individual_decision.verdict in ("halted", "rejected")):
        return PortfolioMarginalRiskDecision(
            decision="vetoed",
            symbol=symbol,
            requestedValue=proposed_value,
            allowedValue=0.0,
            reductionFactor=0.0,
            individualRiskUsd=individual_risk_usd,
            portfolioCapitalAtRiskPctBefore=intelligence_before.heat.estimated_capital_at_risk_pct,
            portfolioCapitalAtRiskPctAfter=intelligence_before.heat.estimated_capital_at_risk_pct,
            grossExposureUsdBefore=intelligence_before.exposure.gross_exposure,
            grossExposureUsdAfter=intelligence_before.exposure.gross_exposure,
            netExposureUsdBefore=intelligence_before.exposure.net_exposure,
            netExposureUsdAfter=intelligence_before.exposure.net_exposure,
            leverageBefore=leverage_before,
            leverageAfter=leverage_before,
            largestClusterPctBefore=largest_cluster_before,
            largestClusterPctAfter=largest_cluster_before,
            correlationImpact="low",
            concentrationImpact="low",
            correlationRegimeState=correlation_regime_state,
            liquidityStatus=liquidity_status,
            regimeStatus=regime_status,
            drawdownStatus=drawdown_status,
            dailyLossStatus=daily_loss_status,
            vetoReasons=individual_decision.reasons or ["Emergency Stop is active — no new trades until explicitly resumed."],
            warnings=[],
            riskPolicyVersion=MARGINAL_RISK_POLICY_VERSION,
            computedAt=computed_at,
        )

    def _intelligence_at(value: float) -> PortfolioIntelligence:
        if value <= 0:
            return intelligence_before
        quantity = value / price if price > 0 else 0.0
        synthetic = _synthetic_portfolio(portfolio, symbol=symbol, side=side, quantity=quantity, price=price)
        return compute_portfolio_intelligence(synthetic, provider, pending_proposal_count=0)

    intelligence_full = _intelligence_at(proposed_value)
    candidate_cluster_pct_full = _symbol_cluster_pct(intelligence_full, symbol)

    allowed_value = proposed_value
    intelligence_after = intelligence_full
    if candidate_cluster_pct_full >= _RESTRICTED_CLUSTER_PCT:
        lo, hi = 0.0, proposed_value
        for _ in range(_REDUCTION_SEARCH_ITERATIONS):
            mid = (lo + hi) / 2
            mid_intel = _intelligence_at(mid)
            if _symbol_cluster_pct(mid_intel, symbol) >= _RESTRICTED_CLUSTER_PCT:
                hi = mid
            else:
                lo = mid
        allowed_value = lo
        intelligence_after = _intelligence_at(allowed_value)

    largest_cluster_after = max((c.total_exposure_pct for c in intelligence_after.correlated_clusters), default=0.0)
    candidate_cluster_pct_after = _symbol_cluster_pct(intelligence_after, symbol)
    equity_after = intelligence_after.equity
    leverage_after = (intelligence_after.exposure.gross_exposure / equity_after) if equity_after > 0 else 0.0

    warnings: list[str] = []
    veto_reasons: list[str] = []
    if allowed_value < _MIN_MEANINGFUL_ALLOCATION_USD:
        decision: MarginalRiskVerdict = "vetoed"
        allowed_value = 0.0
        veto_reasons.append(
            f"{symbol}'s own correlated partners already make up {candidate_cluster_pct_full:.1f}% of equity "
            f"(>= the {_RESTRICTED_CLUSTER_PCT:.0f}% restricted threshold) with no meaningful reduced size available — "
            "that cluster is already too concentrated to safely add to."
        )
        intelligence_after = intelligence_before
        largest_cluster_after = largest_cluster_before
        candidate_cluster_pct_after = 0.0
        equity_after = equity_before
        leverage_after = leverage_before
    elif allowed_value < proposed_value - 1e-9:
        decision = "approved_reduced"
        warnings.append(
            f"Reduced from ${proposed_value:,.0f} to ${allowed_value:,.0f} to keep {symbol}'s own correlated cluster under "
            f"the {_RESTRICTED_CLUSTER_PCT:.0f}% restricted threshold (would have reached {candidate_cluster_pct_full:.1f}%)."
        )
    else:
        decision = "approved"

    if decision != "vetoed" and individual_decision.verdict == "approved_with_reduction":
        warnings.extend(individual_decision.reasons)

    reduction_factor = (allowed_value / proposed_value) if proposed_value > 0 else 1.0

    return PortfolioMarginalRiskDecision(
        decision=decision,
        symbol=symbol,
        requestedValue=proposed_value,
        allowedValue=round(allowed_value, 2),
        reductionFactor=round(reduction_factor, 4),
        individualRiskUsd=round(individual_risk_usd, 2) if individual_risk_usd is not None else None,
        portfolioCapitalAtRiskPctBefore=intelligence_before.heat.estimated_capital_at_risk_pct,
        portfolioCapitalAtRiskPctAfter=intelligence_after.heat.estimated_capital_at_risk_pct,
        grossExposureUsdBefore=intelligence_before.exposure.gross_exposure,
        grossExposureUsdAfter=intelligence_after.exposure.gross_exposure,
        netExposureUsdBefore=intelligence_before.exposure.net_exposure,
        netExposureUsdAfter=intelligence_after.exposure.net_exposure,
        leverageBefore=round(leverage_before, 3),
        leverageAfter=round(leverage_after, 3),
        largestClusterPctBefore=largest_cluster_before,
        largestClusterPctAfter=largest_cluster_after,
        correlationImpact=_correlation_impact(candidate_cluster_pct_after),
        concentrationImpact=_concentration_impact(allowed_value, equity_after, limits),
        correlationRegimeState=correlation_regime_state,
        liquidityStatus=liquidity_status,
        regimeStatus=regime_status,
        drawdownStatus=drawdown_status,
        dailyLossStatus=daily_loss_status,
        vetoReasons=veto_reasons,
        warnings=warnings,
        riskPolicyVersion=MARGINAL_RISK_POLICY_VERSION,
        computedAt=computed_at,
    )
