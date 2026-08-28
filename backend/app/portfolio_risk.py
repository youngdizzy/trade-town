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
from app.risk_engine import evaluate_all_sentinel_checks, evaluate_guardian_exposure, portfolio_equity
from app.schemas import (
    DailyCircuitBreakerTier,
    PaperPortfolio,
    PortfolioIntelligence,
    PortfolioRiskSnapshot,
    PortfolioRiskState,
    PretradeRiskDecision,
    PretradeRiskVerdict,
    RiskLimits,
)

# A correlated cluster at or above this share of equity is treated as a
# real concentration concern in its own right, on top of whatever
# per-symbol concentration limit already exists — the CEO brief's own
# "the firm may effectively be making one large risk bet" language.
_RESTRICTED_CLUSTER_PCT = 40.0


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
