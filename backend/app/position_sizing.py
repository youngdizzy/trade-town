"""app/position_sizing.py — Institutional Position Sizing & Capital
Deployment Engine (v0.7 Design Bible Chapter 57).

GOAL (from the chapter): TradeTown should never decide position size
from emotion, confidence alone, or intuition — every dollar deployed
must be justified through evidence, probability, portfolio context, and
company risk policy. This engine answers "how much," never "whether":
approving or rejecting a trade outright stays app/gatekeeper.py's job.

RESEARCHED FIRST. Before this module, position sizing was exactly two
flat percent-of-equity numbers (app/risk_engine.py's
recommended_quantity()): `min(risk_per_trade_pct, max_position_pct)` of
equity, with no regard for how strong the evidence behind the trade
actually is. That function is not duplicated here — its real output
becomes this engine's CEILING, a hard cap this engine only ever narrows,
never widens (see build_position_sizing()'s own docstring). Every real
input this engine reads already exists elsewhere:

  Sizing Score (Evidence/Confidence/Expected Value/Risk/Market Quality/
  Liquidity/Portfolio composite) -> app/war_room.py's
                                     DecisionScoreBreakdown.overall,
                                     reused directly rather than
                                     recomputing a second composite.
  Portfolio Heat / Correlation    -> app/portfolio_intelligence.py's
                                     PortfolioHeat (this tick's most
                                     recent read — see build_position_
                                     sizing()'s own note on why it's one
                                     tick stale, and why that's fine).
  Historical Performance          -> the Decision Vault's Similarity
                                     Engine, already folded into the
                                     Sizing Score via Decision Score's
                                     own evidence_score.
  Risk hard limits                -> app/risk_engine.py's RiskWarning
                                     (Sentinel/Guardian's real, already-
                                     computed per-symbol severity).

HONESTY BOUNDARY — what this module deliberately does NOT build, and why
(see the Design Bible chapter's own Implementation Notes for the fuller
version):

  Position Scaling/Reduction on ALREADY-OPEN positions — would need each
  position's own entry-time evidence score stored so a later tick can
  compare "then vs. now"; PaperPosition has no such field today, and
  inventing one is a distinct, separate piece of work from sizing a NEW
  proposal. Not built in this pass.

  Day/Swing/Hybrid allocation split — this codebase's real trading
  behavior is a single mode; a CEO control that changes a label but
  nothing about how proposals are actually generated or held would be
  exactly the "no placeholder systems" violation Company Law forbids.
  Not built until those modes are real (see docs/DesignBible/volumes/
  06-trading-operating-system.md's own honest note on the same gap).

  Auto-executing any reduction, or a system-triggered Portfolio Heat
  cap — this codebase's own documented v0.8 stop condition
  (docs/ROADMAP.md: "risk is measured and displayed, never auto-hedged
  or auto-corrected without the player") forbids it. `portfolio_heat_
  cap_pct` is a real, CEO-SET, CEO-TRIGGERED ceiling (the CEO chooses the
  number and lives with its consequences); nothing here ever changes it
  or acts without it being consulted as a pass/fail gate on a CEO-visible
  quantity.
"""
from __future__ import annotations

from app.backtest_primitives import regime_trend_at
from app.ema_pullback_research import CHANDELIER_ATR_MULTIPLIER, CHANDELIER_ATR_PERIOD
from app.market_data import MarketDataProvider
from app.portfolio_risk import compute_correlation_concentration_cap
from app.risk_engine import SIM_MINUTES_PER_DAY, portfolio_equity
from app.schemas import (
    CrossPortfolioRiskParityRead,
    DecisionScoreBreakdown,
    DecisionVaultEntry,
    ExpectedValueAnalysis,
    MarketIntelligenceRegime,
    PaperPortfolio,
    PositionSizingResult,
    PositionTier,
    PortfolioHeat,
    RegimeSuitabilityRead,
    RiskLimits,
    RiskWarning,
    SessionSuitabilityRead,
    TradeProposal,
    TradingSession,
    VolatilitySizingRead,
    VolatilityScaledExposureResearch,
)
from app.session_evidence import MIN_SESSION_REGIME_SAMPLE, compute_session_regime_evidence, lookup_session_regime_evidence
from app.technical_indicators import atr, ema_series
from app.trend_engine import compute_trend_regime_breakdown, research_volatility_scaled_exposure

WEEKLY_DEPLOYMENT_WINDOW_DAYS = 7

# CEO directive "Portfolio Construction, Capital Allocation & Execution
# Realism," Phase 3 — same real candle window this codebase's own
# proposal-generation/correlation reads already use
# (app/portfolio_intelligence.py's PROPOSAL_TIMEFRAME/PROPOSAL_CANDLE_
# COUNT) — 30 hourly candles comfortably covers CHANDELIER_ATR_PERIOD's
# (22) own real minimum window, reused rather than picking a new number.
VOLATILITY_TIMEFRAME = "1h"
VOLATILITY_CANDLE_COUNT = 30

# CEO directive "Portfolio Risk Engine, 11/10 Professional Quant-Firm
# Implementation," Phase 2 — a locally-labeled hourly horizon set for
# this module's own real hourly candle cadence, the same real,
# disclosed choice app/executive.py's own PROPOSAL_TREND_HORIZONS
# already makes (app/trend_engine.py's own DEFAULT_HORIZONS labels
# assume a DAILY-timeframe series). A real regime breakdown needs
# meaningfully more history than the 30-bar window every other cap in
# this module uses — 200 real hourly bars is enough for the regime
# classifier's own 50-period EMA plus a real trailing sample of
# "strong signal" bars to bucket by regime.
REGIME_SUITABILITY_TIMEFRAME = "1h"
REGIME_SUITABILITY_HORIZONS: list[tuple[str, int]] = [("6h", 6), ("12h", 12), ("24h", 24)]
REGIME_SUITABILITY_CANDLE_COUNT = 200
# Matches app/trend_engine.py::compute_trend_regime_breakdown()'s own
# real default parameters exactly — kept as real, local values (not
# imported, avoiding a new cross-module constant for three plain
# numbers) so this function's own "what is the regime RIGHT NOW" read
# uses the exact same real classifier the breakdown's own historical
# buckets are grouped by.
_REGIME_EMA_PERIOD = 50
_REGIME_SLOPE_LOOKBACK = 20
_REGIME_SLOPE_THRESHOLD_PCT = 0.5
# Phase 2's own "small buckets shown honestly" — a regime bucket with
# fewer real historical observations than this is treated as
# insufficient evidence, never trusted for a real capital decision.
_MIN_BARS_FOR_REGIME_EVIDENCE = 5
# Below this real historical hit rate in the CURRENT regime, size
# scales down linearly toward 0 at a real 0% hit rate — one real,
# disclosed, simple formula, never the only valid one a researcher
# could choose. At or above it, no reduction (this cap only ever
# narrows, never rewards a strong regime fit with MORE than the
# ceiling already allows).
_REGIME_SUITABILITY_HIT_RATE_FLOOR_PCT = 50.0

# CEO directive "You are now entering the NEXT major TradeTown build
# phase," Phase 10 — the same real, disclosed 50%-floor narrowing
# formula as _REGIME_SUITABILITY_HIT_RATE_FLOOR_PCT above, applied to
# app/session_evidence.py's own independently-real SESSION x REGIME win
# rate rather than the regime-only forward-return hit rate. Kept as its
# own separate constant (not shared with the one above) since it scales
# a different, independently-computed real evidence axis — deliberately
# NOT the same number as session_evidence.py's own 60%/40% favorable/
# unfavorable qualitative labels, which classify a bucket for human
# reporting, not for a capital-narrowing formula.
_SESSION_SUITABILITY_HIT_RATE_FLOOR_PCT = 50.0

TIER_LABEL: dict[PositionTier, str] = {
    "exploratory": "Exploratory",
    "standard": "Standard",
    "high_conviction": "High Conviction",
    "institutional": "Institutional Allocation",
}

# The same 70-point "good decision" bar app/war_room.py's own
# DECISION_SCORE_THRESHOLD already establishes for Executive approval —
# reused here as the Sizing Score's own Standard-tier floor rather than
# inventing a second threshold convention.
STANDARD_TIER_FLOOR = 70.0
HIGH_CONVICTION_TIER_FLOOR = 82.0
INSTITUTIONAL_TIER_FLOOR = 92.0

# Real evidence-based scaling, applied as a fraction of the CEILING
# (never an independent absolute number) — see build_position_sizing()'s
# own docstring for why a fraction, not a competing absolute cap, is
# what actually makes "weak evidence -> smaller position" true
# regardless of how a CEO happens to have risk_per_trade_pct/
# max_position_pct/tier_allocation configured relative to each other.
# Institutional gets the full 1.0 — "the maximum tier this proposal's
# own numbers can justify," never more than the existing hard ceiling.
TIER_FRACTION: dict[PositionTier, float] = {
    "exploratory": 0.35,
    "standard": 0.70,
    "high_conviction": 0.90,
    "institutional": 1.0,
}


def _capital_deployed_pct_in_window(portfolio: PaperPortfolio, equity: float, sim_day: int, window_days: int) -> float:
    """Real capital newly committed in the trailing `window_days` —
    summed over every trade_history entry AND every still-open position
    whose real opened_sim_minutes falls inside the window, as a % of
    equity. This is the "spendable, decrementing" Risk Budget the
    Design Bible chapter asks for, replacing nothing (no prior field
    tracked this) — a genuinely new real read over already-real data."""
    if equity <= 0:
        return 0.0
    earliest_day = sim_day - window_days + 1
    deployed = sum(
        trade.entry_price * trade.quantity for trade in portfolio.trade_history if earliest_day <= trade.opened_sim_minutes // SIM_MINUTES_PER_DAY <= sim_day
    )
    deployed += sum(
        position.entry_price * position.quantity for position in portfolio.positions if earliest_day <= position.opened_sim_minutes // SIM_MINUTES_PER_DAY <= sim_day
    )
    return deployed / equity * 100


def _tier_for_sizing_score(
    sizing_score: float,
    *,
    decision_score: DecisionScoreBreakdown,
    expected_value: ExpectedValueAnalysis,
    portfolio_heat: PortfolioHeat,
    critical_risk_warning: bool,
) -> PositionTier:
    """No single metric determines allocation — every tier gate combines
    the Sizing Score with real portfolio-health and expected-value
    context, never Sizing Score alone. Institutional Allocation
    additionally requires the same three real approvals the chapter asks
    for: Executive approval (decision_score.passed, the War Room's own
    real Decision Score threshold), Portfolio Intelligence approval
    (portfolio_heat.tier == "cool"), and Risk Authority approval (no
    active critical risk warning for this symbol)."""
    if critical_risk_warning:
        return "exploratory"
    if sizing_score >= INSTITUTIONAL_TIER_FLOOR and decision_score.passed and expected_value.positive_expectancy and portfolio_heat.tier == "cool":
        return "institutional"
    if sizing_score >= HIGH_CONVICTION_TIER_FLOOR and expected_value.positive_expectancy and portfolio_heat.tier in ("cool", "warm"):
        return "high_conviction"
    if sizing_score >= STANDARD_TIER_FLOOR:
        return "standard"
    return "exploratory"


def _tier_allocation_pct(risk_limits: RiskLimits, tier: PositionTier) -> float:
    allocation = risk_limits.tier_allocation
    return {
        "exploratory": allocation.tier1_pct,
        "standard": allocation.tier2_pct,
        "high_conviction": allocation.tier3_pct,
        "institutional": allocation.tier4_pct,
    }[tier]


def _volatility_sizing(proposal: TradeProposal, provider: MarketDataProvider, equity: float, risk_limits: RiskLimits) -> VolatilitySizingRead:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism," Phase 3 — POSITION SIZE ~ RISK BUDGET / DISTANCE
    TO STOP. `stop_distance` is a real ATR-based read (the same
    Chandelier Stop convention already established for this codebase's
    backtest engines — CHANDELIER_ATR_PERIOD/CHANDELIER_ATR_MULTIPLIER,
    never a second, independently-tuned constant), not an actual placed
    stop order (this codebase's live positions have no real stop-loss
    order mechanism — see app/schemas.py's DecisionVaultEntry.r_multiple
    docstring for that already-disclosed, separate gap). `risk_budget_usd`
    reuses risk_limits.risk_per_trade_pct — the identical dollar figure
    app/risk_engine.py's recommended_quantity() ceiling already implies —
    so a volatile symbol gets a SMALLER real quantity at the SAME real
    dollar risk, never a larger one. `available=False` (never a
    fabricated distance) when there isn't yet enough real candle history
    for a real ATR read at this symbol."""
    try:
        candles = provider.get_candles(proposal.symbol, VOLATILITY_TIMEFRAME, VOLATILITY_CANDLE_COUNT)
    except ValueError:
        return VolatilitySizingRead(
            available=False, atrPeriod=CHANDELIER_ATR_PERIOD, detail=f"No real candle history available for {proposal.symbol} — volatility-based sizing unavailable."
        )
    atr_value = atr(candles, period=CHANDELIER_ATR_PERIOD)
    if atr_value is None or atr_value <= 0 or equity <= 0 or proposal.price <= 0:
        return VolatilitySizingRead(
            available=False, atrPeriod=CHANDELIER_ATR_PERIOD, detail=f"Not enough real candle history yet for a real {CHANDELIER_ATR_PERIOD}-period ATR on {proposal.symbol}."
        )

    stop_distance = round(CHANDELIER_ATR_MULTIPLIER * atr_value, 4)
    risk_budget_usd = round(equity * risk_limits.risk_per_trade_pct / 100, 2)
    volatility_cap_quantity = round(risk_budget_usd / stop_distance, 4) if stop_distance > 0 else 0.0
    return VolatilitySizingRead(
        available=True,
        atrValue=atr_value,
        atrPeriod=CHANDELIER_ATR_PERIOD,
        stopDistance=stop_distance,
        riskBudgetUsd=risk_budget_usd,
        volatilityCapQuantity=volatility_cap_quantity,
        detail=(
            f"Real {CHANDELIER_ATR_PERIOD}-period ATR of {atr_value:.2f} implies a {stop_distance:.2f} stop distance "
            f"({CHANDELIER_ATR_MULTIPLIER:.0f}x ATR) — ${risk_budget_usd:,.0f} risk budget / that distance caps this trade at "
            f"{volatility_cap_quantity:.2f} units, regardless of what the evidence-based tiers above allow."
        ),
    )


def _inverse_vol_sizing(proposal: TradeProposal, provider: MarketDataProvider, equity: float, risk_limits: RiskLimits, decision_score: DecisionScoreBreakdown) -> VolatilityScaledExposureResearch | None:
    """CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    Engine" follow-up — promotes app/trend_engine.py's own real,
    previously research-only `research_volatility_scaled_exposure()`
    into this live, advisory-only narrowing cap: zero new math, the
    exact same real formula and volatility floor/hard-cap that function
    already discloses. `signal_strength` reuses this proposal's own
    real Decision Score (`decision_score.overall`, 0-100) normalized to
    0-1 — the same composite evidence read every other sizing tier
    above already keys off, never a second invented confidence number.
    `target_risk_pct` reuses `risk_limits.risk_per_trade_pct`, the
    identical real risk-per-trade figure `_volatility_sizing()`'s own
    ATR-stop-budget cap already uses, so both caps are measured against
    the same real risk policy rather than two different implied
    budgets. `None` (never a fabricated cap) below the same minimum
    real candle history `_volatility_sizing()` requires.

    HONEST BOUNDARY: this scales ONE candidate's own exposure inversely
    to its OWN volatility — it does not (yet) normalize risk
    CONTRIBUTION across every simultaneously-open position (a true
    cross-portfolio `1/sigma` weighting, where a position's size also
    depends on every OTHER open position's own volatility/correlation).
    That fuller version is a real, disclosed, separate, larger lift —
    not attempted here."""
    if equity <= 0 or proposal.price <= 0:
        return None
    try:
        candles = provider.get_candles(proposal.symbol, VOLATILITY_TIMEFRAME, VOLATILITY_CANDLE_COUNT)
    except ValueError:
        return None
    if len(candles) < 2:
        return None
    return research_volatility_scaled_exposure(
        candles,
        proposal.symbol,
        signal_strength=decision_score.overall / 100.0,
        target_risk_pct=risk_limits.risk_per_trade_pct,
    )


def _cross_portfolio_inverse_vol_sizing(
    proposal: TradeProposal,
    provider: MarketDataProvider,
    portfolio: PaperPortfolio,
    equity: float,
    risk_limits: RiskLimits,
    decision_score: DecisionScoreBreakdown,
) -> CrossPortfolioRiskParityRead | None:
    """CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    Engine" follow-up — closes the honesty gap `_inverse_vol_sizing()`
    above explicitly discloses: THIS candidate's own real volatility is
    weighed against every OTHER real symbol currently held, a naive
    (uncorrelated) inverse-volatility risk-parity read, not a
    single-position-only one.

    For each real symbol currently held (deduped — multiple lots in the
    same symbol are one real volatility read, not counted twice) plus
    this candidate, computes `1 / volatility_pct` via the same real
    `research_volatility_scaled_exposure()` this module already uses
    for `_inverse_vol_sizing()` (an already-open position is read at
    signal_strength=1.0 — it is a live, fully-committed bet, not a
    candidate being sized). Normalizing those weights gives this
    candidate's own real fair SHARE of a total risk budget
    (`risk_limits.risk_per_trade_pct * position_count`, a real, disclosed
    choice picked specifically so this fair share is IDENTICAL to
    `risk_per_trade_pct` — today's existing single-position risk budget —
    whenever this candidate is the only real position). That fair-share
    risk budget is then run back through `research_volatility_scaled_
    exposure()` itself as its own real `target_risk_pct` argument to
    produce `final_exposure` — reusing its exact real formula AND real
    hard exposure ceiling verbatim, never a hand-rolled second division,
    so at `position_count == 1` this is the exact same function call
    `_inverse_vol_sizing()` itself makes.

    STILL NOT full covariance-based Equal Risk Contribution — real
    correlation between held symbols is not incorporated (see
    CrossPortfolioRiskParityRead's own docstring for the exact,
    disclosed remaining gap). `None` (never a fabricated cap) under the
    same minimum-real-candle-history convention every volatility-based
    read in this module already follows."""
    if equity <= 0 or proposal.price <= 0:
        return None
    try:
        candidate_candles = provider.get_candles(proposal.symbol, VOLATILITY_TIMEFRAME, VOLATILITY_CANDLE_COUNT)
    except ValueError:
        return None
    if len(candidate_candles) < 2:
        return None
    candidate_signal = max(0.0, min(1.0, decision_score.overall / 100.0))
    candidate_reading = research_volatility_scaled_exposure(candidate_candles, proposal.symbol, signal_strength=1.0, target_risk_pct=risk_limits.risk_per_trade_pct)
    inverse_vol_weights: dict[str, float] = {proposal.symbol: 1.0 / candidate_reading.volatility_estimate_pct}
    other_symbols = sorted({p.symbol for p in portfolio.positions if p.symbol != proposal.symbol})
    for symbol in other_symbols:
        try:
            held_candles = provider.get_candles(symbol, VOLATILITY_TIMEFRAME, VOLATILITY_CANDLE_COUNT)
        except ValueError:
            continue
        if len(held_candles) < 2:
            continue
        held_reading = research_volatility_scaled_exposure(held_candles, symbol, signal_strength=1.0, target_risk_pct=risk_limits.risk_per_trade_pct)
        inverse_vol_weights[symbol] = 1.0 / held_reading.volatility_estimate_pct

    position_count = len(inverse_vol_weights)
    total_weight = sum(inverse_vol_weights.values())
    candidate_weight = inverse_vol_weights[proposal.symbol]
    candidate_weight_pct = (candidate_weight / total_weight * 100) if total_weight > 0 else 100.0
    total_risk_budget_pct = risk_limits.risk_per_trade_pct * position_count
    fair_share_risk_pct = candidate_weight_pct / 100 * total_risk_budget_pct
    # Reuses the exact real formula AND real hard exposure ceiling
    # research_volatility_scaled_exposure() already enforces — never a
    # hand-rolled second division that would silently skip that cap.
    final_exposure = research_volatility_scaled_exposure(candidate_candles, proposal.symbol, signal_strength=candidate_signal, target_risk_pct=fair_share_risk_pct)

    other_note = f" against {position_count - 1} other real currently-held symbol(s)" if position_count > 1 else " — the only real position, so this collapses to today's single-position formula"
    detail = (
        f"Naive cross-portfolio inverse-vol risk parity{other_note}: this candidate's real volatility "
        f"({candidate_reading.volatility_estimate_pct:.3f}%) earns it {candidate_weight_pct:.1f}% of a "
        f"{total_risk_budget_pct:.2f}% total risk budget ({risk_limits.risk_per_trade_pct:.2f}% x {position_count} real symbols) = "
        f"{fair_share_risk_pct:.3f}% fair-share risk. {final_exposure.detail} "
        "Correlation between held symbols is NOT incorporated — a real, disclosed, still-larger lift."
    )
    return CrossPortfolioRiskParityRead(
        symbol=proposal.symbol,
        positionCount=position_count,
        candidateVolatilityPct=round(candidate_reading.volatility_estimate_pct, 4),
        candidateWeightPct=round(candidate_weight_pct, 2),
        fairShareRiskPct=round(fair_share_risk_pct, 4),
        totalRiskBudgetPct=round(total_risk_budget_pct, 4),
        finalExposure=final_exposure,
        detail=detail,
    )


def _regime_suitability_sizing(proposal: TradeProposal, provider: MarketDataProvider, candidate_quantity: float) -> RegimeSuitabilityRead | None:
    """Promotes app/trend_engine.py's own real, previously-unconsumed
    regime-conditional hit-rate evidence (compute_trend_regime_
    breakdown()) into a real, narrowing-only cap — CEO directive
    "Portfolio Risk Engine, 11/10 Professional Quant-Firm Implementation,"
    Phase 2's own literal ask ("a strategy should not receive capital
    simply because it passed a backtest... determine which strategies
    are historically appropriate for the CURRENT regime"). `None` (never
    a fabricated read) when there isn't yet enough real candle history to
    compute a meaningful regime breakdown at all."""
    try:
        candles = provider.get_candles(proposal.symbol, REGIME_SUITABILITY_TIMEFRAME, REGIME_SUITABILITY_CANDLE_COUNT)
    except ValueError:
        return None
    if len(candles) < _REGIME_EMA_PERIOD + _REGIME_SLOPE_LOOKBACK:
        return None
    ema_values = ema_series(candles, _REGIME_EMA_PERIOD)
    if not ema_values:
        return None
    current_regime = regime_trend_at(
        ema_values, _REGIME_EMA_PERIOD, len(candles) - 1, slope_lookback=_REGIME_SLOPE_LOOKBACK, slope_threshold_pct=_REGIME_SLOPE_THRESHOLD_PCT
    )
    breakdown = compute_trend_regime_breakdown(candles, proposal.symbol, REGIME_SUITABILITY_TIMEFRAME, horizons=REGIME_SUITABILITY_HORIZONS)
    bucket = next((b for b in breakdown.buckets if b.regime == current_regime), None)
    if bucket is None or bucket.bars_observed < _MIN_BARS_FOR_REGIME_EVIDENCE:
        return RegimeSuitabilityRead(
            available=False,
            currentRegime=current_regime,
            barsObserved=bucket.bars_observed if bucket else 0,
            detail=(
                f"Insufficient real historical evidence for the '{current_regime}' regime specifically "
                f"({bucket.bars_observed if bucket else 0} real bar(s) observed, need {_MIN_BARS_FOR_REGIME_EVIDENCE}+) — "
                "no real regime-suitability reduction applied."
            ),
        )
    scale = 1.0 if bucket.hit_rate_pct >= _REGIME_SUITABILITY_HIT_RATE_FLOOR_PCT else bucket.hit_rate_pct / _REGIME_SUITABILITY_HIT_RATE_FLOOR_PCT
    return RegimeSuitabilityRead(
        available=True,
        currentRegime=current_regime,
        barsObserved=bucket.bars_observed,
        hitRatePct=bucket.hit_rate_pct,
        meanForwardReturnPct=bucket.mean_forward_return_pct,
        suitabilityScale=round(scale, 4),
        regimeCapQuantity=round(candidate_quantity * scale, 6),
        detail=(
            f"{bucket.bars_observed} real historical bar(s) show this signal in the '{current_regime}' regime hit "
            f"{bucket.hit_rate_pct:.1f}% of the time (mean forward return {bucket.mean_forward_return_pct:+.2f}%)."
            + (f" Scaled to {scale * 100:.0f}% of the pre-regime candidate size." if scale < 1.0 else " At or above the 50% real floor — no reduction.")
        ),
    )


def _session_suitability_sizing(
    session: TradingSession,
    regime: MarketIntelligenceRegime,
    decision_vault: list[DecisionVaultEntry],
    candidate_quantity: float,
) -> SessionSuitabilityRead:
    """Promotes app/session_evidence.py's own real, previously read-only
    SESSION x REGIME win-rate evidence (computed over this company's own
    real closed trades — app/decision_vault.py's DecisionVaultEntry) into
    a real, narrowing-only cap — CEO directive "You are now entering the
    NEXT major TradeTown build phase," Phase 10's own explicit warning
    against assuming "a session automatically creates an edge" without
    it being "researched/backtested." A repo audit found the evidence
    already real and already displayed, but never fed forward into a
    live sizing decision — this closes exactly that gap, nothing more.

    Never `None`: unlike _regime_suitability_sizing() above (which can
    fail to even fetch candle history), this reads only already-resolved
    in-memory arguments, so it always returns a real, honest read —
    `available=False` is that honest read whenever this exact
    (session, regime) pairing has fewer than MIN_SESSION_REGIME_SAMPLE
    real closed trades on record, never a fabricated conclusion from an
    empty or thin sample."""
    summary = compute_session_regime_evidence(decision_vault)
    bucket = lookup_session_regime_evidence(summary, session, regime)
    if bucket is None or bucket.sample_size < MIN_SESSION_REGIME_SAMPLE or bucket.win_rate_pct is None:
        return SessionSuitabilityRead(
            available=False,
            session=session,
            regime=regime,
            sampleSize=bucket.sample_size if bucket else 0,
            evidenceState=bucket.evidence_state if bucket else "not_enough_evidence",
            detail=(
                f"Insufficient real closed-trade history for the '{session}' session under the '{regime}' regime "
                f"specifically ({bucket.sample_size if bucket else 0} real closed trade(s) on record, need "
                f"{MIN_SESSION_REGIME_SAMPLE}+) — no real session-suitability reduction applied."
            ),
        )
    scale = 1.0 if bucket.win_rate_pct >= _SESSION_SUITABILITY_HIT_RATE_FLOOR_PCT else bucket.win_rate_pct / _SESSION_SUITABILITY_HIT_RATE_FLOOR_PCT
    return SessionSuitabilityRead(
        available=True,
        session=session,
        regime=regime,
        sampleSize=bucket.sample_size,
        winRatePct=bucket.win_rate_pct,
        avgPnlPct=bucket.avg_pnl_pct,
        evidenceState=bucket.evidence_state,
        suitabilityScale=round(scale, 4),
        sessionCapQuantity=round(candidate_quantity * scale, 6),
        detail=(
            f"{bucket.sample_size} real closed trade(s) in the '{session}' session under the '{regime}' regime won "
            f"{bucket.win_rate_pct:.1f}% of the time (avg P&L {bucket.avg_pnl_pct:+.2f}%, evidence state {bucket.evidence_state.upper()})."
            + (f" Scaled to {scale * 100:.0f}% of the pre-session candidate size." if scale < 1.0 else " At or above the 50% real floor — no reduction.")
        ),
    )


def build_position_sizing(
    proposal: TradeProposal,
    *,
    ceiling_quantity: float,
    expected_value: ExpectedValueAnalysis,
    decision_score: DecisionScoreBreakdown,
    portfolio: PaperPortfolio,
    portfolio_heat: PortfolioHeat,
    risk_limits: RiskLimits,
    risk_warnings: list[RiskWarning],
    sim_day: int,
    provider: MarketDataProvider,
    session: TradingSession,
    regime: MarketIntelligenceRegime,
    decision_vault: list[DecisionVaultEntry],
) -> PositionSizingResult:
    """The engine's one real entry point — evidence-and-confidence-
    weighted sizing that only ever narrows `ceiling_quantity`
    (app/risk_engine.py's recommended_quantity(), computed by the
    caller), never widens it. `portfolio_heat` is deliberately the
    entering-tick's already-computed PortfolioIntelligence reading (one
    tick — 5 real sim-minutes — stale by the time a same-tick proposal
    is sized), the same "cheap, close enough" tradeoff every other
    same-tick consumer of a recomputed-fresh-each-tick signal in this
    codebase already accepts, rather than restructuring nexus.py's tick
    order to force a same-tick recompute. `provider` (CEO directive
    "Portfolio Construction, Capital Allocation & Execution Realism,"
    Phase 3) feeds the real ATR-based volatility cap — see
    _volatility_sizing()'s own docstring. `session`/`regime`/
    `decision_vault` (CEO directive "You are now entering the NEXT major
    TradeTown build phase," Phase 10) feed the real session-suitability
    cap — see _session_suitability_sizing()'s own docstring."""
    equity = portfolio_equity(portfolio)
    price = proposal.price
    volatility_sizing = _volatility_sizing(proposal, provider, equity, risk_limits)
    if equity <= 0 or price <= 0 or ceiling_quantity <= 0:
        return PositionSizingResult(
            tier="exploratory",
            tierLabel=TIER_LABEL["exploratory"],
            sizingScore=decision_score.overall,
            ceilingQuantity=0.0,
            tierCapQuantity=0.0,
            finalQuantity=0.0,
            capitalDeployedPct=0.0,
            weeklyDeploymentPct=0.0,
            weeklyDeploymentCapPct=risk_limits.max_weekly_deployment_pct,
            cashReserveOk=True,
            portfolioHeatCapOk=True,
            institutionalGatesPassed=False,
            reducedFromCeiling=False,
            volatilitySizing=volatility_sizing,
            detail="No real ceiling quantity available for this proposal — zero size, nothing to justify.",
        )

    critical_risk_warning = any(w.symbol == proposal.symbol and w.severity == "critical" for w in risk_warnings)
    sizing_score = decision_score.overall
    tier = _tier_for_sizing_score(
        sizing_score, decision_score=decision_score, expected_value=expected_value, portfolio_heat=portfolio_heat, critical_risk_warning=critical_risk_warning
    )
    institutional_gates_passed = tier == "institutional"

    # Evidence-based scaling is a FRACTION of the ceiling, not a second
    # absolute cap competing with it — a cap can only ever bind if a CEO
    # happens to have set it below risk_per_trade_pct's own ceiling,
    # which would make "weak evidence -> smaller position" silently do
    # nothing most of the time. The fraction always has real effect; the
    # absolute tier_allocation_pct cap remains underneath it as a
    # separate, real, CEO-configured safety guardrail.
    scaled_quantity = ceiling_quantity * TIER_FRACTION[tier]
    tier_pct = _tier_allocation_pct(risk_limits, tier)
    tier_cap_quantity = equity * tier_pct / 100 / price
    candidate_quantity = min(scaled_quantity, tier_cap_quantity)

    weekly_deployed_before_pct = _capital_deployed_pct_in_window(portfolio, equity, sim_day, WEEKLY_DEPLOYMENT_WINDOW_DAYS)
    candidate_pct = candidate_quantity * price / equity * 100
    weekly_remaining_pct = max(0.0, risk_limits.max_weekly_deployment_pct - weekly_deployed_before_pct)
    weekly_cap_quantity = equity * weekly_remaining_pct / 100 / price
    weekly_ok = candidate_pct <= weekly_remaining_pct + 1e-9

    portfolio_heat_cap_ok = True
    heat_cap_quantity = candidate_quantity
    if risk_limits.portfolio_heat_cap_pct is not None:
        heat_remaining_pct = max(0.0, risk_limits.portfolio_heat_cap_pct - portfolio_heat.total_capital_at_risk_pct)
        heat_cap_quantity = equity * heat_remaining_pct / 100 / price
        portfolio_heat_cap_ok = candidate_pct <= heat_remaining_pct + 1e-9

    min_cash = equity * risk_limits.cash_reserve_pct / 100
    available_cash = max(0.0, portfolio.cash_balance - min_cash)
    cash_cap_quantity = available_cash / price
    cash_reserve_ok = candidate_quantity * price <= available_cash + 1e-6

    # CEO directive "Portfolio Construction, Capital Allocation &
    # Execution Realism," Phase 3 — the real ATR-based volatility cap,
    # narrowing-only like every other cap here. Only ever binds when
    # real ATR evidence exists (never a fabricated cap from a missing
    # candle history — see _volatility_sizing()'s own docstring).
    volatility_cap_quantity = volatility_sizing.volatility_cap_quantity if volatility_sizing.available and volatility_sizing.volatility_cap_quantity is not None else candidate_quantity

    # CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    # Engine" follow-up — the real inverse-volatility exposure cap, also
    # narrowing-only, only ever binding when real candle evidence exists
    # (see _inverse_vol_sizing()'s own docstring for the exact honesty
    # boundary against a true cross-portfolio 1/sigma weighting).
    inverse_vol_sizing = _inverse_vol_sizing(proposal, provider, equity, risk_limits, decision_score)
    inverse_vol_cap_quantity = (equity * inverse_vol_sizing.capped_exposure_pct / 100 / price) if inverse_vol_sizing is not None else candidate_quantity

    # CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    # Engine" follow-up — the real, naive cross-portfolio inverse-vol
    # risk-parity cap, narrowing-only like every cap here. Only ever
    # binds when real candle evidence exists for this candidate (see
    # _cross_portfolio_inverse_vol_sizing()'s own docstring for the
    # exact formula and its own remaining honesty boundary against full
    # covariance-based Equal Risk Contribution).
    cross_portfolio_risk_sizing = _cross_portfolio_inverse_vol_sizing(proposal, provider, portfolio, equity, risk_limits, decision_score)
    cross_portfolio_cap_quantity = (equity * cross_portfolio_risk_sizing.final_exposure.capped_exposure_pct / 100 / price) if cross_portfolio_risk_sizing is not None else candidate_quantity

    # CEO directive "Portfolio Risk Engine, 11/10 Professional Quant-Firm
    # Implementation" — the real correlation/concentration-cluster
    # reduction the previous "Cross-Trade Capital Allocation" pass built
    # (app/portfolio_risk.py::evaluate_marginal_portfolio_risk()) reached
    # the CEO as real, live evidence in the Trade Approval view, but
    # never actually narrowed the quantity a trade executes at — "a
    # strong signal does NOT automatically get capital" was shown, not
    # enforced. Wired in here as one more real, narrowing-only cap,
    # evaluated against this candidate's own already tier/heat/cash/
    # volatility-scaled notional (never the raw, pre-scaling ceiling —
    # every other cap here narrows from that same starting point too).
    # Deliberately calls `compute_correlation_concentration_cap()`, NOT
    # `evaluate_marginal_portfolio_risk()` itself — that function also
    # composes Sentinel's own critical hard gates (drawdown/daily-loss/
    # position-size/emergency-stop) into a full veto, and this module's
    # own docstring is explicit that it answers "how much," never
    # "whether"; those gates remain exclusively app/gatekeeper.py's real
    # job downstream, never duplicated here (see that function's own
    # docstring for the full reasoning).
    marginal_risk_decision = compute_correlation_concentration_cap(
        risk_limits, portfolio, provider, symbol=proposal.symbol, proposed_value=candidate_quantity * price, sim_day=sim_day
    )
    marginal_risk_cap_quantity = (
        candidate_quantity if marginal_risk_decision.decision == "data_blocked" or price <= 0 else marginal_risk_decision.allowed_value / price
    )

    # CEO directive "Portfolio Risk Engine, 11/10 Professional Quant-Firm
    # Implementation," Phase 2 — the real regime-suitability cap. See
    # _regime_suitability_sizing()'s own docstring for the full
    # provenance. Only ever narrows (never below `available=True` real
    # evidence, and never a fabricated cap when there isn't yet enough
    # real candle history for a meaningful regime breakdown).
    regime_suitability_sizing = _regime_suitability_sizing(proposal, provider, candidate_quantity)
    regime_suitability_cap_quantity = (
        regime_suitability_sizing.regime_cap_quantity
        if regime_suitability_sizing is not None and regime_suitability_sizing.available and regime_suitability_sizing.regime_cap_quantity is not None
        else candidate_quantity
    )

    # CEO directive "You are now entering the NEXT major TradeTown build
    # phase," Phase 10 — the real session-suitability cap. See
    # _session_suitability_sizing()'s own docstring for the full
    # provenance. Only ever narrows (never below `available=True` real
    # evidence, and never a fabricated cap when this exact session/
    # regime pairing has too few real closed trades on record).
    session_suitability_sizing = _session_suitability_sizing(session, regime, decision_vault, candidate_quantity)
    session_suitability_cap_quantity = (
        session_suitability_sizing.session_cap_quantity
        if session_suitability_sizing.available and session_suitability_sizing.session_cap_quantity is not None
        else candidate_quantity
    )

    final_quantity = max(
        0.0,
        min(
            candidate_quantity,
            weekly_cap_quantity,
            heat_cap_quantity,
            cash_cap_quantity,
            volatility_cap_quantity,
            inverse_vol_cap_quantity,
            cross_portfolio_cap_quantity,
            marginal_risk_cap_quantity,
            regime_suitability_cap_quantity,
            session_suitability_cap_quantity,
        ),
    )
    final_quantity = round(final_quantity, 4)
    capital_deployed_pct = round(final_quantity * price / equity * 100, 2) if equity > 0 else 0.0
    reduced_from_ceiling = final_quantity < round(ceiling_quantity, 4)

    binding_constraint = (
        "the tier's own evidence-based fraction of the risk ceiling" if scaled_quantity <= tier_cap_quantity + 1e-9 else "the tier's absolute allocation cap"
    )
    if final_quantity < candidate_quantity - 1e-9:
        if (
            session_suitability_cap_quantity <= weekly_cap_quantity
            and session_suitability_cap_quantity <= heat_cap_quantity
            and session_suitability_cap_quantity <= cash_cap_quantity
            and session_suitability_cap_quantity <= volatility_cap_quantity
            and session_suitability_cap_quantity <= inverse_vol_cap_quantity
            and session_suitability_cap_quantity <= cross_portfolio_cap_quantity
            and session_suitability_cap_quantity <= marginal_risk_cap_quantity
            and session_suitability_cap_quantity <= regime_suitability_cap_quantity
            and session_suitability_cap_quantity < candidate_quantity - 1e-9
        ):
            binding_constraint = session_suitability_sizing.detail
        elif (
            regime_suitability_cap_quantity <= weekly_cap_quantity
            and regime_suitability_cap_quantity <= heat_cap_quantity
            and regime_suitability_cap_quantity <= cash_cap_quantity
            and regime_suitability_cap_quantity <= volatility_cap_quantity
            and regime_suitability_cap_quantity <= inverse_vol_cap_quantity
            and regime_suitability_cap_quantity <= cross_portfolio_cap_quantity
            and regime_suitability_cap_quantity <= marginal_risk_cap_quantity
            and regime_suitability_cap_quantity < candidate_quantity - 1e-9
        ):
            binding_constraint = (
                regime_suitability_sizing.detail
                if regime_suitability_sizing is not None
                else "the real regime-suitability cap (this signal's own historical hit rate in the CURRENT regime)"
            )
        elif (
            marginal_risk_cap_quantity <= weekly_cap_quantity
            and marginal_risk_cap_quantity <= heat_cap_quantity
            and marginal_risk_cap_quantity <= cash_cap_quantity
            and marginal_risk_cap_quantity <= volatility_cap_quantity
            and marginal_risk_cap_quantity <= inverse_vol_cap_quantity
            and marginal_risk_cap_quantity <= cross_portfolio_cap_quantity
            and marginal_risk_cap_quantity < candidate_quantity - 1e-9
        ):
            binding_constraint = (
                marginal_risk_decision.warnings[0]
                if marginal_risk_decision.warnings
                else (marginal_risk_decision.veto_reasons[0] if marginal_risk_decision.veto_reasons else "the real portfolio-level Marginal Risk Test (this candidate's own effect on the whole book, not just itself)")
            )
        elif (
            cross_portfolio_cap_quantity <= weekly_cap_quantity
            and cross_portfolio_cap_quantity <= heat_cap_quantity
            and cross_portfolio_cap_quantity <= cash_cap_quantity
            and cross_portfolio_cap_quantity <= volatility_cap_quantity
            and cross_portfolio_cap_quantity <= inverse_vol_cap_quantity
            and cross_portfolio_cap_quantity < candidate_quantity - 1e-9
        ):
            binding_constraint = "the real cross-portfolio inverse-volatility risk-parity budget (this symbol's own real volatility relative to every other real currently-held symbol's own volatility)"
        elif (
            inverse_vol_cap_quantity <= weekly_cap_quantity
            and inverse_vol_cap_quantity <= heat_cap_quantity
            and inverse_vol_cap_quantity <= cash_cap_quantity
            and inverse_vol_cap_quantity <= volatility_cap_quantity
            and inverse_vol_cap_quantity < candidate_quantity - 1e-9
        ):
            binding_constraint = "the real inverse-volatility exposure budget (this symbol's own real volatility relative to its evidence-implied signal strength)"
        elif volatility_cap_quantity <= weekly_cap_quantity and volatility_cap_quantity <= heat_cap_quantity and volatility_cap_quantity <= cash_cap_quantity and volatility_cap_quantity < candidate_quantity - 1e-9:
            binding_constraint = "the real ATR-based volatility risk budget (a wider stop distance than this tier's own quantity implies)"
        elif not weekly_ok and weekly_cap_quantity <= heat_cap_quantity and weekly_cap_quantity <= cash_cap_quantity:
            binding_constraint = "the weekly capital deployment budget"
        elif not portfolio_heat_cap_ok and heat_cap_quantity <= cash_cap_quantity:
            binding_constraint = "the CEO's Portfolio Heat cap"
        elif not cash_reserve_ok:
            binding_constraint = "the CEO's cash reserve requirement"

    detail = (
        f"Sizing Score {sizing_score:.0f}/100 assigns {TIER_LABEL[tier]} — "
        f"{'sized down from the risk ceiling by ' + binding_constraint if reduced_from_ceiling else 'sized at the tier ceiling, within the real risk limit'}."
    )

    return PositionSizingResult(
        tier=tier,
        tierLabel=TIER_LABEL[tier],
        sizingScore=round(sizing_score, 1),
        ceilingQuantity=round(ceiling_quantity, 4),
        tierCapQuantity=round(tier_cap_quantity, 4),
        finalQuantity=final_quantity,
        capitalDeployedPct=capital_deployed_pct,
        volatilitySizing=volatility_sizing,
        inverseVolSizing=inverse_vol_sizing,
        crossPortfolioRiskSizing=cross_portfolio_risk_sizing,
        marginalRiskDecision=marginal_risk_decision,
        regimeSuitabilitySizing=regime_suitability_sizing or RegimeSuitabilityRead(),
        sessionSuitabilitySizing=session_suitability_sizing,
        weeklyDeploymentPct=round(weekly_deployed_before_pct + capital_deployed_pct, 2),
        weeklyDeploymentCapPct=risk_limits.max_weekly_deployment_pct,
        cashReserveOk=cash_reserve_ok,
        portfolioHeatCapOk=portfolio_heat_cap_ok,
        institutionalGatesPassed=institutional_gates_passed,
        reducedFromCeiling=reduced_from_ceiling,
        detail=detail,
    )
