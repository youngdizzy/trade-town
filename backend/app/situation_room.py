"""Mobile Command Center & Remote Operations — Design Bible Chapter 73.5
(see docs/DesignBible/volumes/09-departments/chapter-73-5-mobile-
command-center-remote-operations.md for the full honesty boundary).

The Executive Situation Room is a real, read-only aggregate — computed
fresh every request from state this game already persists or already
computes fresh elsewhere. Confirmed by direct inspection before writing
this module: eleven of the thirteen fields the brief asks for already
have exactly one real, existing computed source and are reused
verbatim (Company Health, Portfolio Health via `PortfolioIntelligence.
heat.tier`, Cash Position, Open Risk, Market Regime, Trading Mode,
Economic Health, Black Swan Risk, Broker Status, Automation Status,
Emergency Alerts); only Pending CEO Decisions and Executive Consensus
are computed fresh here, because no single existing field already
answers them (see module docstring notes on each below). This module
never recomputes any of the eleven reused numbers independently — the
same "cross-cutting, computed-fresh, never a second stale copy"
convention Chapter 73's Compliance Overview already established.

Severity-band mapping table (the only new judgment this module makes,
disclosed and simple by design, matching Chapter 73's Compliance Score
honesty):

- Company Health (`CompanyHealth.overall`, 0-100): >=80 good, >=60
  caution, >=40 elevated, >=20 severe, else critical.
- Portfolio Health (`PortfolioHeat.tier`): cool good, warm caution, hot
  elevated, overheated critical.
- Cash Position (% of equity currently deployed in open positions):
  <=50 good, <=70 caution, <=85 elevated, <=95 severe, else critical.
- Open Risk (open positions as a % of `RiskLimits.max_open_positions`,
  forced to `critical`/`severe` at Circuit Breaker tier4/tier3
  regardless of the ratio): <=50 good, <=70 caution, <=85 elevated,
  <=100 severe, else critical.
- Market Regime (`MarketEnvironmentRegime`): bull/sideways/
  low_volatility good, high_volatility caution, bear elevated — a
  regime read is directional context, not itself an emergency signal
  (that's Black Swan Risk's job), so this field never reaches
  severe/critical.
- Trading Mode (folds in the Daily Circuit Breaker tier — the real,
  active constraint on the CEO's chosen mode right now): none good,
  tier1 caution, tier2 elevated, tier3 severe, tier4 critical.
- Economic Health (`EconomicHealthTier`): thriving good, stable
  caution, cautious elevated, stressed severe, critical critical.
- Black Swan Risk (`BlackSwanRiskTier`): green good, yellow caution,
  orange elevated, red severe, critical critical.
- Executive Consensus (agreement % across the most recently created
  pending `TradeProposal`'s own real `analyst_votes` — `Weighted
  ExecutiveRecommendation.consensus_pct` is computed transiently at
  decision-resolution time and never persisted, confirmed by direct
  inspection, so there is no "most recent" value to read back; a
  pending proposal's own votes are the honest substitute. `good` with
  no pending proposal to disagree about): >=80 good, >=60 caution,
  >=40 elevated, >=20 severe, else critical.
- Pending CEO Decisions (count — `TradeProposal` has no `status`
  field; presence in `trade_proposals` *is* "pending," confirmed by
  direct inspection): 0 good, 1-2 caution, 3-4 elevated, 5-6 severe,
  else critical.
- Broker Status: always `SIMULATED` / good — the same honest constant
  `GlobalStatusBar.tsx` already hardcodes; there is no second, real
  broker connection to read a status from (`PaperBroker`'s own module
  docstring: "no brokerage SDK import anywhere in this file... no code
  path that reaches a real order-execution endpoint").
- Automation Status: `critical` whenever Emergency Stop is active,
  otherwise `good` (the current Operating Mode is disclosed as
  `value`, never itself treated as risky).
- Emergency Alerts: `critical` if Emergency Stop is active or any
  `critical`-severity `RiskWarning` is on file, else `good`.
"""
from __future__ import annotations

from app.schemas import (
    BlackSwanRiskTier,
    CompanyHealth,
    DailyCircuitBreakerRead,
    DailyCircuitBreakerTier,
    EconomicHealthTier,
    EconomicIntelligenceState,
    EmergencyStopState,
    MarketEnvironmentRegime,
    MarketEnvironmentState,
    OperatingMode,
    PaperPortfolio,
    PortfolioIntelligence,
    PriorityItem,
    RiskLimits,
    RiskWarning,
    SituationRoomField,
    SituationRoomSeverity,
    SituationRoomState,
    TradeProposal,
    TradingModeState,
)

_REGIME_BAND: dict[MarketEnvironmentRegime, SituationRoomSeverity] = {
    "bull": "good",
    "sideways": "good",
    "low_volatility": "good",
    "high_volatility": "caution",
    "bear": "elevated",
}

_PORTFOLIO_HEAT_BAND: dict[str, SituationRoomSeverity] = {
    "cool": "good",
    "warm": "caution",
    "hot": "elevated",
    "overheated": "critical",
}

_ECONOMIC_BAND: dict[EconomicHealthTier, SituationRoomSeverity] = {
    "thriving": "good",
    "stable": "caution",
    "cautious": "elevated",
    "stressed": "severe",
    "critical": "critical",
}

_BLACK_SWAN_BAND: dict[BlackSwanRiskTier, SituationRoomSeverity] = {
    "green": "good",
    "yellow": "caution",
    "orange": "elevated",
    "red": "severe",
    "critical": "critical",
}

_TIER_BAND: dict[DailyCircuitBreakerTier, SituationRoomSeverity] = {
    "none": "good",
    "tier1": "caution",
    "tier2": "elevated",
    "tier3": "severe",
    "tier4": "critical",
}


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _band_desc(value: float, good: float, caution: float, elevated: float, severe: float) -> SituationRoomSeverity:
    if value >= good:
        return "good"
    if value >= caution:
        return "caution"
    if value >= elevated:
        return "elevated"
    if value >= severe:
        return "severe"
    return "critical"


def _band_count(count: int, caution_at: int, elevated_at: int, severe_at: int, critical_at: int) -> SituationRoomSeverity:
    if count < caution_at:
        return "good"
    if count < elevated_at:
        return "caution"
    if count < severe_at:
        return "elevated"
    if count < critical_at:
        return "severe"
    return "critical"


def _executive_consensus_pct(pending_proposals: list[TradeProposal]) -> float | None:
    """The most recently created pending proposal's own real agreement
    rate across its `analyst_votes` — None only when there is nothing
    pending to have a consensus about."""
    if not pending_proposals:
        return None
    latest = max(pending_proposals, key=lambda p: p.created_sim_minutes)
    total = len(latest.analyst_votes)
    if total == 0:
        return None
    agreeing = sum(1 for v in latest.analyst_votes if v.choice == latest.overall_recommendation)
    return round(agreeing / total * 100, 1)


def compute_situation_room(
    *,
    company_health: CompanyHealth,
    portfolio: PaperPortfolio,
    portfolio_intelligence: PortfolioIntelligence,
    risk_limits: RiskLimits,
    daily_circuit_breaker: DailyCircuitBreakerRead,
    risk_warnings: list[RiskWarning],
    market_environment: MarketEnvironmentState,
    trading_mode_state: TradingModeState,
    economic_intelligence: EconomicIntelligenceState,
    black_swan_tier: BlackSwanRiskTier,
    trade_proposals: list[TradeProposal],
    emergency_stop: EmergencyStopState,
    operating_mode: OperatingMode,
) -> SituationRoomState:
    deployed_pct = portfolio_intelligence.deployed_pct_of_equity
    open_ratio_pct = round(len(portfolio.positions) / risk_limits.max_open_positions * 100, 1) if risk_limits.max_open_positions > 0 else 0.0
    critical_warnings = [w for w in risk_warnings if w.severity == "critical"]
    consensus_pct = _executive_consensus_pct(trade_proposals)

    open_risk_band = _band_desc(100 - open_ratio_pct, 50, 30, 15, 0)
    if daily_circuit_breaker.tier == "tier4":
        open_risk_band = "critical"
    elif daily_circuit_breaker.tier == "tier3" and open_risk_band not in ("severe", "critical"):
        open_risk_band = "severe"

    priorities = rank_priorities(
        emergency_stop=emergency_stop,
        risk_warnings=risk_warnings,
        black_swan_tier=black_swan_tier,
        trade_proposals=trade_proposals,
        daily_circuit_breaker=daily_circuit_breaker,
        economic_band=_ECONOMIC_BAND[economic_intelligence.health.tier],
    )

    return SituationRoomState(
        companyHealth=SituationRoomField(
            label="Company Health",
            value=f"{company_health.overall:.0f}/100",
            band=_band_desc(company_health.overall, 80, 60, 40, 20),
            detail="The company's own ten-metric composite score.",
        ),
        portfolioHealth=SituationRoomField(
            label="Portfolio Health",
            value=portfolio_intelligence.heat.tier.title(),
            band=_PORTFOLIO_HEAT_BAND[portfolio_intelligence.heat.tier],
            detail=f"{portfolio_intelligence.heat.total_capital_at_risk_pct:.0f}% of equity at risk across open positions.",
        ),
        cashPosition=SituationRoomField(
            label="Cash Position",
            value=f"${portfolio.cash_balance:,.0f} ({100 - deployed_pct:.0f}% of equity)",
            band=_band_desc(100 - deployed_pct, 50, 30, 15, 5),
            detail=f"{deployed_pct:.0f}% of equity currently deployed across {len(portfolio.positions)} open position(s).",
        ),
        openRisk=SituationRoomField(
            label="Open Risk",
            value=f"{len(portfolio.positions)}/{risk_limits.max_open_positions} positions",
            band=open_risk_band,
            detail=f"Daily Circuit Breaker reads {daily_circuit_breaker.tier} ({daily_circuit_breaker.daily_pnl_pct:+.1f}% today).",
        ),
        marketRegime=SituationRoomField(
            label="Market Regime",
            value=market_environment.label,
            band=_REGIME_BAND[market_environment.current],
            detail=market_environment.detail,
        ),
        tradingMode=SituationRoomField(
            label="Trading Mode",
            value=f"{trading_mode_state.mode.replace('_', ' ').title()} — Circuit Breaker {daily_circuit_breaker.tier}",
            band=_TIER_BAND[daily_circuit_breaker.tier],
            detail="The CEO's chosen Trading Mode and the Daily Circuit Breaker's real, active tier.",
        ),
        economicHealth=SituationRoomField(
            label="Economic Health",
            value=f"{economic_intelligence.health.overall:.0f}/100 — {economic_intelligence.health.tier}",
            band=_ECONOMIC_BAND[economic_intelligence.health.tier],
            detail=economic_intelligence.health.reasoning,
        ),
        blackSwanRisk=SituationRoomField(
            label="Black Swan Risk",
            value=black_swan_tier.upper(),
            band=_BLACK_SWAN_BAND[black_swan_tier],
            detail="Black Swan Intelligence's real, current stress-signal tier.",
        ),
        executiveConsensus=SituationRoomField(
            label="Executive Consensus",
            value=f"{consensus_pct:.0f}% agreement" if consensus_pct is not None else "No pending proposal",
            band=_band_desc(consensus_pct, 80, 60, 40, 20) if consensus_pct is not None else "good",
            detail="Analyst agreement rate on the most recently generated pending trade proposal.",
        ),
        pendingCeoDecisions=SituationRoomField(
            label="Pending CEO Decisions",
            value=str(len(trade_proposals)),
            band=_band_count(len(trade_proposals), 1, 3, 5, 7),
            detail=f"{len(trade_proposals)} trade proposal(s) awaiting the CEO's Approve/Reject/Modify/Hold/Delegate choice.",
        ),
        brokerStatus=SituationRoomField(
            label="Broker Status",
            value="SIMULATED",
            band="good",
            detail="PaperBroker — fully simulated, no external broker connection exists in this codebase.",
        ),
        automationStatus=SituationRoomField(
            label="Automation Status",
            value=f"{operating_mode.title()}{' — Emergency Stop active' if emergency_stop.active else ''}",
            band="critical" if emergency_stop.active else "good",
            detail="The company's real Operating Mode and whether Emergency Stop is currently active.",
        ),
        emergencyAlerts=SituationRoomField(
            label="Emergency Alerts",
            value=str(len(critical_warnings) + (1 if emergency_stop.active else 0)),
            band="critical" if emergency_stop.active or critical_warnings else "good",
            detail=f"{len(critical_warnings)} critical Risk Warning(s) on file" + (", Emergency Stop is active." if emergency_stop.active else "."),
        ),
        priorities=priorities,
        generatedAt=_now_iso(),
    )


def rank_priorities(
    *,
    emergency_stop: EmergencyStopState,
    risk_warnings: list[RiskWarning],
    black_swan_tier: BlackSwanRiskTier,
    trade_proposals: list[TradeProposal],
    daily_circuit_breaker: DailyCircuitBreakerRead,
    economic_band: SituationRoomSeverity,
) -> list[PriorityItem]:
    """The CEO Priority Engine — formalizes Chapter 67's existing
    critical/high/normal toast tiers into a ranked, typed list, adding a
    fourth `low` tier for items that are real but never worth an
    interruption. Only ever reads real backend signals — never the
    frontend's own toast/alert history, a client-side view built from
    the same underlying signals."""
    items: list[PriorityItem] = []

    if emergency_stop.active:
        items.append(
            PriorityItem(
                id="priority-emergency-stop",
                tier="critical",
                title="Emergency Stop is active",
                detail="Trading is halted company-wide. Only the CEO can resume it.",
                source="emergency_stop",
            )
        )

    for warning in risk_warnings:
        if warning.severity != "critical":
            continue
        items.append(
            PriorityItem(
                id=f"priority-risk-{warning.id}",
                tier="critical",
                title=f"Critical risk warning — {warning.symbol}",
                detail=warning.message,
                source="risk_warning",
                relatedId=warning.id,
            )
        )

    if black_swan_tier in ("red", "critical"):
        items.append(
            PriorityItem(
                id="priority-black-swan",
                tier="critical",
                title=f"Black Swan risk reads {black_swan_tier.upper()}",
                detail="Black Swan Intelligence's real, current stress-signal tier has reached a severe level.",
                source="black_swan",
            )
        )
    elif black_swan_tier == "orange":
        items.append(
            PriorityItem(
                id="priority-black-swan",
                tier="high",
                title="Black Swan risk reads ORANGE",
                detail="Black Swan Intelligence's real, current stress-signal tier is elevated.",
                source="black_swan",
            )
        )

    breaker_tier_rank = ("none", "tier1", "tier2", "tier3", "tier4")
    if breaker_tier_rank.index(daily_circuit_breaker.tier) >= breaker_tier_rank.index("tier2"):
        items.append(
            PriorityItem(
                id="priority-circuit-breaker",
                tier="high",
                title=f"Daily Circuit Breaker at {daily_circuit_breaker.tier}",
                detail=f"Today's realized P&L is {daily_circuit_breaker.daily_pnl_pct:+.1f}%.",
                source="circuit_breaker",
            )
        )

    for proposal in trade_proposals:
        tier = "high" if breaker_tier_rank.index(daily_circuit_breaker.tier) >= breaker_tier_rank.index("tier2") else "medium"
        items.append(
            PriorityItem(
                id=f"priority-proposal-{proposal.id}",
                tier=tier,  # type: ignore[arg-type]
                title=f"Pending decision — {proposal.symbol}",
                detail=f"{proposal.overall_recommendation.upper()} recommended at {proposal.confidence:.0f}% confidence.",
                source="pending_decision",
                relatedId=proposal.id,
            )
        )

    if economic_band in ("elevated", "severe"):
        items.append(
            PriorityItem(
                id="priority-economic-health",
                tier="medium",
                title="Economic Health is deteriorating",
                detail="The Economic Intelligence Center's real cross-signal health read has slipped.",
                source="economic_health",
            )
        )

    if daily_circuit_breaker.tier == "tier1":
        items.append(
            PriorityItem(
                id="priority-circuit-breaker-tier1",
                tier="low",
                title="Daily Circuit Breaker at tier1",
                detail=f"Today's realized P&L is {daily_circuit_breaker.daily_pnl_pct:+.1f}% — logged, not interrupting.",
                source="circuit_breaker",
            )
        )

    tier_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    items.sort(key=lambda i: tier_rank[i.tier])
    return items
