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

from app.risk_engine import SIM_MINUTES_PER_DAY, portfolio_equity
from app.schemas import (
    DecisionScoreBreakdown,
    ExpectedValueAnalysis,
    PaperPortfolio,
    PositionSizingResult,
    PositionTier,
    PortfolioHeat,
    RiskLimits,
    RiskWarning,
    TradeProposal,
)

WEEKLY_DEPLOYMENT_WINDOW_DAYS = 7

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
    order to force a same-tick recompute."""
    equity = portfolio_equity(portfolio)
    price = proposal.price
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

    final_quantity = max(0.0, min(candidate_quantity, weekly_cap_quantity, heat_cap_quantity, cash_cap_quantity))
    final_quantity = round(final_quantity, 4)
    capital_deployed_pct = round(final_quantity * price / equity * 100, 2) if equity > 0 else 0.0
    reduced_from_ceiling = final_quantity < round(ceiling_quantity, 4)

    binding_constraint = (
        "the tier's own evidence-based fraction of the risk ceiling" if scaled_quantity <= tier_cap_quantity + 1e-9 else "the tier's absolute allocation cap"
    )
    if final_quantity < candidate_quantity - 1e-9:
        if not weekly_ok and weekly_cap_quantity <= heat_cap_quantity and weekly_cap_quantity <= cash_cap_quantity:
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
        weeklyDeploymentPct=round(weekly_deployed_before_pct + capital_deployed_pct, 2),
        weeklyDeploymentCapPct=risk_limits.max_weekly_deployment_pct,
        cashReserveOk=cash_reserve_ok,
        portfolioHeatCapOk=portfolio_heat_cap_ok,
        institutionalGatesPassed=institutional_gates_passed,
        reducedFromCeiling=reduced_from_ceiling,
        detail=detail,
    )
