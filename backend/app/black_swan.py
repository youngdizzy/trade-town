"""Black Swan Intelligence & Resilience System (BSIRS) — Design Bible
Chapter 72.

THE HONESTY BOUNDARY (read this before adding anything to the brief's
much longer list of sections):

This codebase has no historical black-swan dataset (no 2008/2020/1987/
Dot-Com data to calibrate against), no real broker connection
(app/broker.py's own docstring: "no code path that reaches a real
order-execution endpoint"), no macro/credit/funding data (Chapter 71
already established this), and no sector/asset-class taxonomy (Chapters
56/65/71 all already established this — this codebase only has
`ResearchCategory`). So the brief's biggest sections are cut outright:

  - Named historical scenarios (2008 Financial Crisis, 2020 Pandemic
    Crash, Dot-Com Collapse, 1987 Crash, Regional Banking Crisis,
    Interest Rate Shock, Oil Crisis, Currency Collapse) — no real
    calibration data exists for any of them.
  - Banking Failure / Pandemic / Cyberattack / Sovereign Debt Crisis
    scenario types specifically — would require fabricating sector,
    macro, or security data this codebase has zero real source for.
  - A calibrated "Black Swan probability" — no historical base rate
    exists. The Early Warning Score and Risk Level are real-time stress
    readings, never a probability of a specific future event.
    "Likely Duration" and "Affected Asset Classes" are cut for the same
    reason.
  - Live Broker Resilience monitoring (API failure, order delays,
    connection loss) — no real broker connection exists to monitor.
  - Automatic emergency Executive Board meetings — Chapter 70 Part 1
    already confirmed no automatic meeting-trigger mechanism and no
    general-purpose non-trade Decision Center exist anywhere in this
    codebase. A Crisis Briefing (real, structured, permanent) ships
    instead of a fabricated vote.
  - Automatic position closing — app/portfolio_intelligence.py's own
    docstring already states this codebase's binding principle: "risk is
    measured and displayed, never auto-hedged or auto-corrected without
    the player." Nothing in this module ever closes, resizes, or
    otherwise touches an open position automatically.
  - "Reduce Leverage" — no margin/leverage concept exists anywhere.
  - 8 distinct named Playbooks — one real, generically-named Elevated
    Risk Response Playbook ships instead, live-populated with today's
    actual Defensive Mode recommendations.

What IS real and newly built here — a genuine STRESS-AND-RESILIENCE
SYNTHESIS layer over state this codebase already computes honestly:

  - Early Warning Score -> eight named factors, each reused from an
    already-real department (Risk Engine's live warnings, Market
    Intelligence's quality/volatility/liquidity/news reads, Portfolio
    Intelligence's correlation/heat reads, Regime Reconciliation's
    aligned/diverging read, Economic Intelligence's health tier) —
    never recomputed, always read from what nexus.py already computed
    this tick.
  - Black Swan Risk Level -> a genuinely new named tier (GREEN through
    CRITICAL), the exact "Safety Level / Capital Defense Mode" gap
    Chapter 66's own Ownership table and Chapter 70 Part 1's Emergency
    Board Meeting table both already named and left unbuilt.
  - Portfolio Stress Tests -> the brief's own -10/-20/-35/-50/-70% ladder,
    real arithmetic against a chosen portfolio's real positions and real
    RiskLimits, with an honestly-capped recovery-time projection (never
    a fabricated ETA when there's no positive trailing performance to
    project from).
  - Scenario Simulations -> four scenarios named for their real
    mechanism (never a real historical event), reusing app/whatif.py's
    own convention of expressing every shock as a multiple of a symbol's
    real measured volatility — extended here from one candidate trade to
    the whole portfolio at once, as a single instantaneous equity shock
    rather than whatif.py's own bar-by-bar Monte Carlo hold (a
    deliberate simplification: this module answers "what would this
    event do to the book right now," not "how might a candidate trade's
    N-bar hold play out").
  - Defensive Mode -> a real, CEO-controllable posture that tightens
    real RiskLimits and pauses new AI-generated trade proposals, with a
    real recommendation list — closing a position always stays a manual
    CEO action, never automatic, at any tier.
  - Crisis Briefings and Post-Event Analysis -> real, permanent records
    written through app/memory.py's existing record() path and a new
    Knowledge Graph node type, never a second parallel memory system.

Scope note: this module does not become a new Executive Board voting
seat or a Trade Gatekeeper check in this pass — see the Design Bible
chapter's own Future Expansion section for the Chapter 70 Part 3/
Chapter 71 precedent that would govern doing so later.

PART 2 — INSTITUTIONAL SURVIVAL SCORE. A second brief asked for a
continuously-updating 0-100 survival score with a letter grade, real
named strengths/weaknesses, computed improvement suggestions, and an
"Estimated Survival Probability." Built honestly: `compute_institutional_
survival_score()` reuses three of the Early Warning Score's own factors
(Active Risk Warnings, Liquidity, Correlation Breakdown — inverted back
to "how resilient" instead of "how stressed", never recomputed from
scratch) plus five genuinely new real factors (Cash Reserves,
Concentration Risk, Drawdown Exposure, Black Swan Readiness, Stress Test
Survival — the last a real, cheap pass over the same shock ladder
run_portfolio_stress_test() uses). Two of the brief's named inputs are
cut outright: "Leverage" (no margin/leverage concept exists anywhere in
this codebase) and "Counterparty Risk" (no real broker/counterparty
relationship exists — app/broker.py is pure in-process logic). Broker
Health is scored at a fixed, disclosed baseline rather than a fabricated
live number, for the same reason BrokerResilienceRead above is static.
"Estimated Survival Probability" is cut entirely — this codebase has no
historical black-swan dataset to calibrate a probability against, the
same honesty rule that already cut a calibrated "Black Swan probability"
in Part 1. The Survival Score itself, with its named factors, is the
honest answer to "how prepared is this company" — a real, transparent
reading, never a fabricated statistical forecast.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timezone

from app.analytics import real_peak_equity
from app.market_data import MarketDataProvider, volatility_pct
from app.regime_reconciliation import compute_regime_reconciliation
from app.risk_engine import SIM_MINUTES_PER_DAY, portfolio_equity
from app.schemas import (
    BlackSwanConfidenceRead,
    BlackSwanEventRecord,
    BlackSwanIntelligenceState,
    BlackSwanNarrativeEntry,
    BlackSwanPlaybook,
    BlackSwanReport,
    BlackSwanRiskTier,
    BlackSwanScenarioType,
    BlackSwanSignalFactor,
    BrokerResilienceRead,
    CategoryExposure,
    CrisisBriefing,
    DefensiveModeRecommendation,
    DefensiveModeState,
    EarlyWarningScore,
    EconomicIntelligenceState,
    InstitutionalSurvivalGrade,
    InstitutionalSurvivalScore,
    LiquidityRead,
    MarketEnvironmentState,
    MarketIntelligenceState,
    PaperPortfolio,
    PaperPosition,
    PlaybookStep,
    PortfolioIntelligence,
    PortfolioScenarioResult,
    PortfolioStressTestResult,
    ResearchCategory,
    RiskLimits,
    RiskWarning,
    StressTestLevelResult,
    SurvivalScoreFactor,
)
from app.watchlist import SYMBOL_CATEGORY

MAX_BLACK_SWAN_REPORTS = 60
MAX_BLACK_SWAN_EVENTS = 40

PROPOSAL_TIMEFRAME = "1h"
PROPOSAL_CANDLE_COUNT = 30

STRESS_LEVELS: tuple[float, ...] = (-10.0, -20.0, -35.0, -50.0, -70.0)

DEFENSIVE_TIGHTEN_FACTOR = 0.5
MIN_DEFENSIVE_MAX_OPEN_POSITIONS = 2

_RISK_TIER_THRESHOLDS: tuple[tuple[float, BlackSwanRiskTier], ...] = (
    (85.0, "critical"),
    (65.0, "red"),
    (45.0, "orange"),
    (25.0, "yellow"),
    (0.0, "green"),
)

_MARKET_STRESS_SCORE: dict[str, float] = {
    "excellent": 5.0,
    "good": 20.0,
    "average": 45.0,
    "poor": 75.0,
    "avoid_trading": 95.0,
}
_NEWS_SEVERITY_SCORE: dict[str, float] = {"low": 15.0, "moderate": 50.0, "elevated": 85.0}
_MACRO_INSTABILITY_SCORE: dict[str, float] = {
    "thriving": 10.0,
    "stable": 25.0,
    "cautious": 50.0,
    "stressed": 75.0,
    "critical": 95.0,
}

# Disclosed, published weights (sum to 1.0) — never a fitted/backtested
# blend, the same convention app/economic_intelligence.py's own _WEIGHTS
# already established. Active Risk Warnings carries the most weight
# since it is the most direct, already-enforced real signal this company
# has (Sentinel/Guardian's own live gates).
_WEIGHTS: dict[str, float] = {
    "risk_warnings": 0.20,
    "market_stress": 0.15,
    "volatility": 0.15,
    "liquidity": 0.10,
    "correlation": 0.10,
    "regime_divergence": 0.10,
    "news_severity": 0.10,
    "macro_instability": 0.10,
}

_SCENARIO_LABEL: dict[BlackSwanScenarioType, str] = {
    "flash_crash": "Flash Crash",
    "severe_selloff": "Severe Selloff",
    "liquidity_freeze": "Liquidity Freeze",
    "correlation_breakdown": "Correlation Breakdown Shock",
}

# Each shock is a disclosed multiple of the affected symbol's own real
# measured per-bar volatility (app/market_data.py's volatility_pct()) —
# never an absolute invented percentage, the same convention app/
# whatif.py's own _SCENARIO_PARAMS already established. These multiples
# are BSIRS's own, sized for a single instantaneous portfolio-wide
# event rather than whatif.py's bar-by-bar 20-bar hold.
_SCENARIO_SHOCK_MULT: dict[BlackSwanScenarioType, float] = {
    "flash_crash": -6.0,
    "severe_selloff": -3.0,
    "liquidity_freeze": -3.5,
    "correlation_breakdown": -2.5,
}
_SCENARIO_DETAIL: dict[BlackSwanScenarioType, str] = {
    "flash_crash": "An instant, single-event price shock across every open position, sized at 6x each symbol's own real measured volatility.",
    "severe_selloff": "A sustained decline modeled as a 3x-volatility equity shock across every open position.",
    "liquidity_freeze": "A sharp spike-and-fail-to-recover move, sized at 3.5x each symbol's own real measured volatility.",
    "correlation_breakdown": "Every open position shocked in the same direction, at the largest single position's own real measured volatility x2.5 — modeling diversification failing exactly when it's needed.",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _risk_tier(score: float) -> BlackSwanRiskTier:
    return next(tier for threshold, tier in _RISK_TIER_THRESHOLDS if score >= threshold)


_TIER_ORDER: dict[BlackSwanRiskTier, int] = {"green": 0, "yellow": 1, "orange": 2, "red": 3, "critical": 4}


def tier_meets_or_exceeds(tier: BlackSwanRiskTier, threshold: BlackSwanRiskTier) -> bool:
    return _TIER_ORDER.get(tier, 0) >= _TIER_ORDER.get(threshold, 0)


def compute_early_warning_score(
    risk_warnings: list[RiskWarning],
    market_intelligence: MarketIntelligenceState,
    portfolio_intelligence: PortfolioIntelligence,
    market_environment: MarketEnvironmentState,
    economic_intelligence: EconomicIntelligenceState,
) -> EarlyWarningScore:
    critical_count = sum(1 for w in risk_warnings if w.severity == "critical")
    warning_count = sum(1 for w in risk_warnings if w.severity == "warning")
    risk_score = min(100.0, 35.0 * critical_count + 15.0 * warning_count)
    risk_factor = BlackSwanSignalFactor(
        name="Active Risk Warnings",
        score=risk_score,
        weight=_WEIGHTS["risk_warnings"],
        detail=(
            f"{critical_count} critical and {warning_count} warning-level RiskWarning(s) currently on file from Sentinel/Guardian."
            if (critical_count or warning_count)
            else "No active RiskWarnings from Sentinel/Guardian."
        ),
    )

    quality = market_intelligence.quality
    market_stress_score = _MARKET_STRESS_SCORE.get(quality.tier, 45.0)
    market_stress_factor = BlackSwanSignalFactor(
        name="Market Stress",
        score=market_stress_score,
        weight=_WEIGHTS["market_stress"],
        detail=f"Market Intelligence rates current conditions {quality.tier} ({quality.score:.0f}/100).",
    )

    vol = market_intelligence.volatility
    vol_ratio = (vol.current_pct / vol.historical_avg_pct) if vol.historical_avg_pct > 0 else 1.0
    volatility_score = max(0.0, min(100.0, 30.0 + (vol_ratio - 1.0) * 70.0))
    volatility_factor = BlackSwanSignalFactor(
        name="Volatility",
        score=round(volatility_score, 1),
        weight=_WEIGHTS["volatility"],
        detail=f"Current volatility {vol.current_pct:.2f}% vs. historical average {vol.historical_avg_pct:.2f}% ({vol_ratio:.1f}x).",
    )

    liquidity_scores = [lr.liquidity_score for lr in market_intelligence.liquidity]
    if liquidity_scores:
        avg_liquidity = statistics.mean(liquidity_scores)
        liquidity_stress_score = max(0.0, 100.0 - avg_liquidity)
        liquidity_detail = f"Average per-symbol liquidity score {avg_liquidity:.0f}/100 across {len(liquidity_scores)} tracked symbol(s)."
    else:
        liquidity_stress_score = 30.0
        liquidity_detail = "No LiquidityRead on file yet — neutral default."
    liquidity_factor = BlackSwanSignalFactor(
        name="Liquidity",
        score=round(liquidity_stress_score, 1),
        weight=_WEIGHTS["liquidity"],
        detail=liquidity_detail,
    )

    clustered_pairs = len(portfolio_intelligence.correlation_pairs)
    correlation_score = min(100.0, 20.0 * clustered_pairs)
    correlation_factor = BlackSwanSignalFactor(
        name="Correlation Breakdown",
        score=correlation_score,
        weight=_WEIGHTS["correlation"],
        detail=(
            f"{clustered_pairs} held-position pair(s) currently correlated above this company's own clustering threshold."
            if clustered_pairs
            else "No held-position pairs are currently correlated above this company's own clustering threshold."
        ),
    )

    reconciliation = compute_regime_reconciliation(market_environment, market_intelligence)
    divergence_score = 70.0 if reconciliation.agreement == "diverging" else 25.0
    if reconciliation.posture == "cautious":
        divergence_score = min(100.0, divergence_score + 15.0)
    elif reconciliation.posture == "opportunistic":
        divergence_score = max(0.0, divergence_score - 15.0)
    regime_divergence_factor = BlackSwanSignalFactor(
        name="Regime Divergence",
        score=divergence_score,
        weight=_WEIGHTS["regime_divergence"],
        detail=reconciliation.rationale,
    )

    news_risk = market_intelligence.news_risk
    news_score = _NEWS_SEVERITY_SCORE.get(news_risk.risk_level, 50.0)
    news_factor = BlackSwanSignalFactor(
        name="News Severity",
        score=news_score,
        weight=_WEIGHTS["news_severity"],
        detail=f"{news_risk.active_market_news_count} active market-category news item(s) on file — {news_risk.risk_level} risk level.",
    )

    macro_score = _MACRO_INSTABILITY_SCORE.get(economic_intelligence.health.tier, 50.0)
    macro_factor = BlackSwanSignalFactor(
        name="Macro Instability",
        score=macro_score,
        weight=_WEIGHTS["macro_instability"],
        detail=f"Economic Intelligence reads {economic_intelligence.health.tier} ({economic_intelligence.health.overall:.0f}/100).",
    )

    factors = [
        risk_factor,
        market_stress_factor,
        volatility_factor,
        liquidity_factor,
        correlation_factor,
        regime_divergence_factor,
        news_factor,
        macro_factor,
    ]
    overall = round(sum(f.score * f.weight for f in factors), 1)
    tier = _risk_tier(overall)
    reasoning = f"Early Warning Score reads {tier.upper()} ({overall:.1f}/100): " + "; ".join(f"{f.name} {f.score:.0f}" for f in factors) + "."
    return EarlyWarningScore(overall=overall, tier=tier, factors=factors, reasoning=reasoning)


def compute_black_swan_confidence(warning: EarlyWarningScore, portfolio_intelligence: PortfolioIntelligence) -> BlackSwanConfidenceRead:
    """Never presents the stress read as fact — same evidence-quality
    convention as app/economic_intelligence.py's compute_economic_
    confidence(), applied to a stress read instead of a favorability
    read (contradicting/supporting are swapped: here, a HIGH score is
    the concerning one)."""
    open_count = sum(e.position_count for e in portfolio_intelligence.category_exposure)
    real_factor_count = 6  # risk warnings, market stress, volatility, regime divergence, news, macro are always real
    real_factor_count += 1 if portfolio_intelligence.correlation_pairs or open_count >= 2 else 0
    real_factor_count += 1 if open_count >= 1 else 0  # liquidity needs at least one held symbol to be a real read

    confidence_pct = round(min(100.0, 50.0 + 6.25 * real_factor_count), 1)
    evidence_quality: str
    if real_factor_count >= 8:
        evidence_quality = "strong"
    elif real_factor_count >= 6:
        evidence_quality = "moderate"
    else:
        evidence_quality = "thin"

    concerning = [f"{f.name}: {f.detail}" for f in warning.factors if f.score >= 50.0]
    reassuring = [f"{f.name}: {f.detail}" for f in warning.factors if f.score < 50.0]

    key_assumptions = [
        "Volatility, Market Stress, and Liquidity are derived from this company's own simulated (mock) price data, not a live market feed.",
        "No historical black-swan dataset exists anywhere in this codebase; this score is a real-time stress reading, never a calibrated probability of a specific future event.",
        "Correlation and Liquidity reflect this company's own current open positions, not the full market.",
    ]

    if warning.factors:
        worst = max(warning.factors, key=lambda f: f.score)
        recomputed = sum((50.0 if f is worst else f.score) * f.weight for f in warning.factors)
        recomputed_tier = _risk_tier(round(recomputed, 1))
        if recomputed_tier != warning.tier:
            alternative_outcome = f"If {worst.name} alone eased to a neutral reading, the Risk Level would likely move from {warning.tier.upper()} toward {recomputed_tier.upper()}."
        else:
            alternative_outcome = f"No single factor is currently close to moving the Risk Level out of {warning.tier.upper()} on its own — even a neutral {worst.name} reading would not change the tier."
    else:
        alternative_outcome = "No factors computed yet."

    return BlackSwanConfidenceRead(
        confidencePct=confidence_pct,
        evidenceQuality=evidence_quality,  # type: ignore[arg-type]
        supportingEvidence=reassuring,
        contradictingEvidence=concerning,
        keyAssumptions=key_assumptions,
        alternativeOutcome=alternative_outcome,
    )


def compute_black_swan_intelligence(
    risk_warnings: list[RiskWarning],
    market_intelligence: MarketIntelligenceState,
    portfolio_intelligence: PortfolioIntelligence,
    market_environment: MarketEnvironmentState,
    economic_intelligence: EconomicIntelligenceState,
) -> BlackSwanIntelligenceState:
    warning = compute_early_warning_score(risk_warnings, market_intelligence, portfolio_intelligence, market_environment, economic_intelligence)
    confidence = compute_black_swan_confidence(warning, portfolio_intelligence)
    return BlackSwanIntelligenceState(warning=warning, confidence=confidence, updatedAt=_now_iso())


def generate_black_swan_narrative(current: BlackSwanIntelligenceState, previous_report: BlackSwanReport | None, sim_day: int) -> BlackSwanNarrativeEntry:
    """Diffs against the most recently stored daily report — cites only
    real, computed deltas, never invented causality like "a banking
    crisis began." Same pattern as app/economic_intelligence.py's
    generate_market_narrative()."""
    if previous_report is None:
        headline = "Black Swan Intelligence online — establishing baseline."
        body = f"First Early Warning read on file. Risk Level: {current.warning.tier.upper()} ({current.warning.overall:.0f}/100)."
        evidence = [f"{f.name}: {f.detail}" for f in current.warning.factors]
        return BlackSwanNarrativeEntry(id=f"bsn-{sim_day}-baseline", headline=headline, body=body, evidence=evidence, simDay=sim_day, createdAt=_now_iso())

    prev = previous_report.snapshot.warning
    deltas: list[str] = []
    if current.warning.tier != prev.tier:
        deltas.append(f"Risk Level moved from {prev.tier.upper()} ({prev.overall:.0f}) to {current.warning.tier.upper()} ({current.warning.overall:.0f}).")
    elif abs(current.warning.overall - prev.overall) >= 5.0:
        deltas.append(f"Risk Level held at {current.warning.tier.upper()} but moved {current.warning.overall - prev.overall:+.0f} points to {current.warning.overall:.0f}.")

    prev_by_name = {f.name: f for f in prev.factors}
    for factor in current.warning.factors:
        prior = prev_by_name.get(factor.name)
        if prior is not None and abs(factor.score - prior.score) >= 15.0:
            deltas.append(f"{factor.name} moved {factor.score - prior.score:+.0f} points to {factor.score:.0f}.")

    if not deltas:
        headline = f"Stress environment steady — {current.warning.tier.upper()} ({current.warning.overall:.0f}/100)."
        body = f"No material change since Day {previous_report.sim_day}'s report. Risk Level remains {current.warning.tier.upper()}."
        evidence = [f"{f.name}: {f.detail}" for f in current.warning.factors]
    else:
        headline = deltas[0]
        body = " ".join(deltas)
        evidence = deltas

    return BlackSwanNarrativeEntry(id=f"bsn-{sim_day}", headline=headline, body=body, evidence=evidence, simDay=sim_day, createdAt=_now_iso())


def generate_black_swan_report(current: BlackSwanIntelligenceState, previous_report: BlackSwanReport | None, sim_day: int) -> BlackSwanReport:
    narrative = generate_black_swan_narrative(current, previous_report, sim_day)
    return BlackSwanReport(id=f"bs-report-{sim_day}", simDay=sim_day, snapshot=current, narrative=narrative, createdAt=_now_iso())


def record_black_swan_report(history: list[BlackSwanReport], report: BlackSwanReport) -> list[BlackSwanReport]:
    updated = [*history, report]
    if len(updated) > MAX_BLACK_SWAN_REPORTS:
        del updated[: len(updated) - MAX_BLACK_SWAN_REPORTS]
    return updated


# ---------------------------------------------------------------------------
# Portfolio Stress Test
# ---------------------------------------------------------------------------


def _recovery_estimate(loss_amount: float, portfolio: PaperPortfolio, sim_day: int) -> tuple[float | None, str]:
    if loss_amount <= 0:
        return 0.0, "No loss to recover from at this shock level."
    window_start_day = max(0, sim_day - 30)
    recent = [t for t in portfolio.trade_history if t.closed_sim_minutes // SIM_MINUTES_PER_DAY >= window_start_day]
    if not recent:
        return None, "N/A — no trailing closed-trade history to project a recovery from."
    days_elapsed = max(1, sim_day - window_start_day + 1)
    avg_daily_pnl = sum(t.pnl for t in recent) / days_elapsed
    if avg_daily_pnl <= 0:
        return None, "N/A — no positive trailing performance to project a recovery from."
    days = round(loss_amount / avg_daily_pnl, 1)
    return days, f"At this portfolio's own trailing realized average (${avg_daily_pnl:,.2f}/day), recovering this loss would take an estimated {days:.0f} day(s)."


def run_portfolio_stress_test(
    portfolio: PaperPortfolio,
    limits: RiskLimits,
    liquidity_reads: list[LiquidityRead],
    *,
    account_id: str | None,
    account_label: str,
    sim_day: int,
) -> PortfolioStressTestResult:
    starting_equity = portfolio_equity(portfolio)
    held_symbols = {p.symbol for p in portfolio.positions}
    liquidity_scores = [lr.liquidity_score for lr in liquidity_reads if lr.symbol in held_symbols]
    held_liquidity = round(statistics.mean(liquidity_scores), 1) if liquidity_scores else None

    # CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance"
    # — the real high-water mark this shock ladder measures resulting
    # drawdown against, not `portfolio.starting_balance` (loss from the
    # account's original balance, which understates real drawdown risk
    # for any account that ran up a real gain before this shock). Same
    # real peak app/risk_engine.py's own gates now measure against (see
    # app/analytics.py::real_peak_equity()).
    real_peak = real_peak_equity(portfolio.trade_history, portfolio.starting_balance, current_equity=starting_equity)

    levels: list[StressTestLevelResult] = []
    for shock_pct in STRESS_LEVELS:
        positions_value = sum(p.quantity * p.current_price * (1 + shock_pct / 100) for p in portfolio.positions)
        resulting_equity = portfolio.cash_balance + positions_value
        drawdown_pct = round(max(0.0, (real_peak - resulting_equity) / real_peak * 100), 2) if real_peak > 0 else 0.0
        breaches = drawdown_pct >= limits.max_drawdown_pct
        survives = resulting_equity > 0
        loss_amount = max(0.0, starting_equity - resulting_equity)
        recovery_days, recovery_note = _recovery_estimate(loss_amount, portfolio, sim_day)
        levels.append(
            StressTestLevelResult(
                shockPct=shock_pct,
                resultingEquity=round(resulting_equity, 2),
                resultingDrawdownPct=drawdown_pct,
                breachesMaxDrawdown=breaches,
                capitalSurvives=survives,
                recoveryDaysEstimate=recovery_days,
                recoveryNote=recovery_note,
            )
        )

    return PortfolioStressTestResult(
        accountId=account_id,
        accountLabel=account_label,
        startingEquity=round(starting_equity, 2),
        heldPositionLiquidityScore=held_liquidity,
        levels=levels,
        computedAt=_now_iso(),
    )


# ---------------------------------------------------------------------------
# Scenario Simulation
# ---------------------------------------------------------------------------


def _category_impact(shocked_positions: list[tuple[PaperPosition, float]], equity: float) -> list[CategoryExposure]:
    totals: dict[ResearchCategory, float] = {}
    counts: dict[ResearchCategory, int] = {}
    for pos, value in shocked_positions:
        category = SYMBOL_CATEGORY.get(pos.symbol)
        if category is None:
            continue
        totals[category] = totals.get(category, 0.0) + value
        counts[category] = counts.get(category, 0) + 1
    exposures = [
        CategoryExposure(category=c, positionCount=counts[c], value=round(v, 2), pctOfEquity=round(v / equity * 100, 1) if equity > 0 else 0.0) for c, v in totals.items()
    ]
    exposures.sort(key=lambda e: e.pct_of_equity, reverse=True)
    return exposures


def run_portfolio_scenario(
    scenario_type: BlackSwanScenarioType,
    portfolio: PaperPortfolio,
    limits: RiskLimits,
    provider: MarketDataProvider,
    *,
    account_id: str | None,
    account_label: str,
) -> PortfolioScenarioResult:
    starting_equity = portfolio_equity(portfolio)
    mult = _SCENARIO_SHOCK_MULT[scenario_type]

    vols: dict[str, float] = {}
    for pos in portfolio.positions:
        if pos.symbol in vols:
            continue
        try:
            candles = provider.get_candles(pos.symbol, PROPOSAL_TIMEFRAME, PROPOSAL_CANDLE_COUNT)
            vols[pos.symbol] = volatility_pct(candles) / 100
        except ValueError:
            vols[pos.symbol] = 0.01

    if scenario_type == "correlation_breakdown" and portfolio.positions:
        largest = max(portfolio.positions, key=lambda p: p.quantity * p.current_price)
        shared_vol = vols.get(largest.symbol, 0.01)
        shocked_positions = [(p, p.quantity * p.current_price * (1 + mult * shared_vol)) for p in portfolio.positions]
    else:
        shocked_positions = [(p, p.quantity * p.current_price * (1 + mult * vols.get(p.symbol, 0.01))) for p in portfolio.positions]

    shocked_positions_value = sum(v for _, v in shocked_positions)
    shocked_equity = portfolio.cash_balance + shocked_positions_value
    impact_amount = round(shocked_equity - starting_equity, 2)
    impact_pct = round((shocked_equity - starting_equity) / starting_equity * 100, 2) if starting_equity > 0 else 0.0
    # Same real-peak fix as compute_portfolio_stress_test() above — see
    # that function's own comment.
    real_peak = real_peak_equity(portfolio.trade_history, portfolio.starting_balance, current_equity=starting_equity)
    resulting_drawdown_pct = max(0.0, (real_peak - shocked_equity) / real_peak * 100) if real_peak > 0 else 0.0
    breaches = resulting_drawdown_pct >= limits.max_drawdown_pct
    survives = shocked_equity > 0

    return PortfolioScenarioResult(
        scenarioType=scenario_type,
        label=_SCENARIO_LABEL[scenario_type],
        accountId=account_id,
        accountLabel=account_label,
        startingEquity=round(starting_equity, 2),
        shockedEquity=round(shocked_equity, 2),
        impactPct=impact_pct,
        impactAmount=impact_amount,
        categoryImpact=_category_impact(shocked_positions, shocked_equity),
        breachesMaxDrawdown=breaches,
        capitalSurvives=survives,
        detail=_SCENARIO_DETAIL[scenario_type],
        computedAt=_now_iso(),
    )


# ---------------------------------------------------------------------------
# Defensive Mode
# ---------------------------------------------------------------------------


def build_defensive_recommendations(portfolio: PaperPortfolio, limits: RiskLimits) -> list[DefensiveModeRecommendation]:
    equity = portfolio_equity(portfolio)
    recommendations: list[DefensiveModeRecommendation] = []

    total_at_risk_pct = (sum(p.quantity * p.current_price for p in portfolio.positions) / equity * 100) if equity > 0 else 0.0
    recommendations.append(
        DefensiveModeRecommendation(
            action="Reduce Exposure",
            detail=f"{total_at_risk_pct:.0f}% of equity is currently deployed across {len(portfolio.positions)} open position(s).",
            automatic=False,
        )
    )

    losers = sorted((p for p in portfolio.positions if p.unrealized_pnl_pct < 0), key=lambda p: p.unrealized_pnl_pct)[:3]
    if losers:
        detail = "; ".join(f"{p.symbol} {p.unrealized_pnl_pct:+.1f}%" for p in losers)
        recommendations.append(
            DefensiveModeRecommendation(action="Close Weak Positions", detail=f"Worst open positions by unrealized P&L: {detail}. Closing always requires a manual CEO action.", automatic=False)
        )
    else:
        recommendations.append(DefensiveModeRecommendation(action="Close Weak Positions", detail="No open position is currently showing an unrealized loss.", automatic=False))

    cash_pct = (portfolio.cash_balance / equity * 100) if equity > 0 else 100.0
    recommendations.append(DefensiveModeRecommendation(action="Increase Cash", detail=f"Cash is currently {cash_pct:.0f}% of equity.", automatic=False))

    recommendations.append(
        DefensiveModeRecommendation(action="Pause New Entries", detail="While Defensive Mode is active, no new AI-generated trade proposals are created.", automatic=True)
    )

    tightened_position_pct = round(limits.max_position_pct * DEFENSIVE_TIGHTEN_FACTOR, 1)
    recommendations.append(
        DefensiveModeRecommendation(
            action="Reduce Position Size", detail=f"Max position size tightens from {limits.max_position_pct:.0f}% to {tightened_position_pct:.0f}% of equity while active.", automatic=True
        )
    )

    tightened_loss_pct = round(limits.max_daily_loss_pct * DEFENSIVE_TIGHTEN_FACTOR, 1)
    tightened_open_positions = max(MIN_DEFENSIVE_MAX_OPEN_POSITIONS, limits.max_open_positions // 2)
    recommendations.append(
        DefensiveModeRecommendation(
            action="Tighten Risk Controls",
            detail=f"Daily loss limit tightens from {limits.max_daily_loss_pct:.0f}% to {tightened_loss_pct:.0f}%; max open positions from {limits.max_open_positions} to {tightened_open_positions}.",
            automatic=True,
        )
    )

    return recommendations


def _tightened_risk_limits(limits: RiskLimits) -> RiskLimits:
    return limits.model_copy(
        update={
            "max_position_pct": round(limits.max_position_pct * DEFENSIVE_TIGHTEN_FACTOR, 2),
            "max_daily_loss_pct": round(limits.max_daily_loss_pct * DEFENSIVE_TIGHTEN_FACTOR, 2),
            "risk_per_trade_pct": round(limits.risk_per_trade_pct * DEFENSIVE_TIGHTEN_FACTOR, 2),
            "max_open_positions": max(MIN_DEFENSIVE_MAX_OPEN_POSITIONS, limits.max_open_positions // 2),
        }
    )


def activate_defensive_mode(
    state: DefensiveModeState,
    limits: RiskLimits,
    portfolio: PaperPortfolio,
    tier: BlackSwanRiskTier,
    *,
    reason: str,
    now_iso: str,
    now_sim_minutes: int,
) -> tuple[DefensiveModeState, RiskLimits, str | None]:
    if state.active:
        return state, limits, "Defensive Mode is already active."
    new_state = DefensiveModeState(
        active=True,
        triggerTier=state.trigger_tier,
        autoTriggerEnabled=state.auto_trigger_enabled,
        activatedAt=now_iso,
        deactivatedAt=None,
        activationReason=reason,
        priorRiskLimits=limits.model_copy(),
        equityAtActivation=round(portfolio_equity(portfolio), 2),
        peakTierThisEpisode=tier,
        activatedSimMinutes=now_sim_minutes,
        recommendations=build_defensive_recommendations(portfolio, limits),
    )
    return new_state, _tightened_risk_limits(limits), None


def note_defensive_mode_peak_tier(state: DefensiveModeState, tier: BlackSwanRiskTier) -> DefensiveModeState:
    """Keeps peak_tier_this_episode as the worst tier seen while an
    episode is active, so Post-Event Analysis reports the real high-water
    mark, not just whatever tier happened to be current at deactivation."""
    if not state.active:
        return state
    current_peak = state.peak_tier_this_episode or tier
    if _TIER_ORDER.get(tier, 0) > _TIER_ORDER.get(current_peak, 0):
        return state.model_copy(update={"peak_tier_this_episode": tier})
    return state


def deactivate_defensive_mode(
    state: DefensiveModeState,
    portfolio: PaperPortfolio,
    warning: EarlyWarningScore,
    *,
    now_iso: str,
    now_sim_minutes: int,
    event_id: str,
) -> tuple[DefensiveModeState, RiskLimits | None, BlackSwanEventRecord | None, str | None]:
    if not state.active:
        return state, None, None, "Defensive Mode is not active."

    equity_now = round(portfolio_equity(portfolio), 2)
    equity_start = state.equity_at_activation if state.equity_at_activation is not None else equity_now
    equity_change_pct = round((equity_now - equity_start) / equity_start * 100, 2) if equity_start else 0.0
    peak_tier = state.peak_tier_this_episode or warning.tier
    duration_minutes = max(0, now_sim_minutes - (state.activated_sim_minutes or now_sim_minutes))
    largest_factor = max(warning.factors, key=lambda f: f.score).name if warning.factors else "Active Risk Warnings"
    affected_symbols = sorted({p.symbol for p in portfolio.positions})

    event = BlackSwanEventRecord(
        id=event_id,
        triggerReason=state.activation_reason or "Manually activated by the CEO.",
        peakTier=peak_tier,
        activatedAt=state.activated_at or now_iso,
        deactivatedAt=now_iso,
        durationSimMinutes=duration_minutes,
        equityAtActivation=equity_start,
        equityAtDeactivation=equity_now,
        equityChangePct=equity_change_pct,
        largestContributingFactor=largest_factor,
        affectedSymbols=affected_symbols,
        lesson=(
            f"Defensive Mode was active for {duration_minutes} sim minute(s), peaking at {peak_tier.upper()}. "
            f"Portfolio equity moved {equity_change_pct:+.2f}% across the episode. "
            f"{largest_factor} was the largest contributing stress factor when the episode ended."
        ),
        createdAt=now_iso,
    )
    new_state = DefensiveModeState(
        active=False,
        triggerTier=state.trigger_tier,
        autoTriggerEnabled=state.auto_trigger_enabled,
        activatedAt=None,
        deactivatedAt=now_iso,
        activationReason=None,
        priorRiskLimits=None,
        equityAtActivation=None,
        peakTierThisEpisode=None,
        activatedSimMinutes=None,
        recommendations=[],
    )
    return new_state, state.prior_risk_limits, event, None


def record_black_swan_event(history: list[BlackSwanEventRecord], event: BlackSwanEventRecord) -> list[BlackSwanEventRecord]:
    updated = [*history, event]
    if len(updated) > MAX_BLACK_SWAN_EVENTS:
        del updated[: len(updated) - MAX_BLACK_SWAN_EVENTS]
    return updated


# ---------------------------------------------------------------------------
# Playbook, Broker Resilience, Crisis Briefing
# ---------------------------------------------------------------------------

_DEPARTMENT_RESPONSIBILITIES: list[PlaybookStep] = [
    PlaybookStep(label="Risk (Sentinel / Guardian)", detail="Continues enforcing every real RiskLimits gate; reviews the live RiskWarning list for the factor(s) driving the current tier."),
    PlaybookStep(label="Research", detail="Pauses new speculative thesis generation; prioritizes reviewing already-open positions' original research."),
    PlaybookStep(label="Quant", detail="Reviews current position sizing against the tightened Defensive Mode limits, if active."),
    PlaybookStep(label="Portfolio Intelligence", detail="Surfaces the current Portfolio Heat, correlation clustering, and category exposure reads driving the Correlation Breakdown and Concentration factors."),
]


def build_black_swan_playbook(current: BlackSwanIntelligenceState, defensive_mode: DefensiveModeState, portfolio: PaperPortfolio, limits: RiskLimits) -> BlackSwanPlaybook:
    recommendations = defensive_mode.recommendations if defensive_mode.active else build_defensive_recommendations(portfolio, limits)
    immediate_actions = [PlaybookStep(label=r.action, detail=r.detail) for r in recommendations]

    ceo_checklist = [
        PlaybookStep(label="Review the Early Warning Score's factor breakdown", detail="Identify the specific real factor(s) driving the current Risk Level — never act on the tier alone."),
        PlaybookStep(label="Run a Portfolio Stress Test", detail="See the real drawdown and rule-violation impact of a -10/-20/-35/-50/-70% shock before deciding."),
        PlaybookStep(label="Review Defensive Mode's recommendations", detail="Decide which manual actions (closing weak positions, raising cash) to take."),
        PlaybookStep(label="Consider the Global Emergency Stop", detail="For a full trading halt beyond Defensive Mode's scope (also blocks the CEO's own manual trades) — see app/emergency_stop.py."),
    ]

    return BlackSwanPlaybook(
        currentTier=current.warning.tier,
        immediateActions=immediate_actions,
        departmentResponsibilities=_DEPARTMENT_RESPONSIBILITIES,
        ceoChecklist=ceo_checklist,
        recoveryPlan="Run a Portfolio Stress Test at the current shock ladder for a real, computed recovery-time estimate based on this portfolio's own trailing realized performance — never a fabricated ETA.",
        updatedAt=_now_iso(),
    )


def broker_resilience_read() -> BrokerResilienceRead:
    """The honest answer to the brief's Broker Resilience section — a
    static read, never a live monitor of a broker connection that
    doesn't exist. See BrokerResilienceRead's own docstring."""
    return BrokerResilienceRead()


def generate_crisis_briefing(
    current: BlackSwanIntelligenceState, portfolio: PaperPortfolio, portfolio_intelligence: PortfolioIntelligence, limits: RiskLimits, sim_day: int, briefing_id: str
) -> CrisisBriefing:
    """Fires once when the Risk Level first reaches RED/CRITICAL since
    the last briefing — the honest answer to "automatically trigger
    emergency Executive Board meetings" (Chapter 70 Part 1 already
    confirmed no such mechanism, or any general-purpose non-trade
    Decision Center, exists to convene a real vote through)."""
    equity = portfolio_equity(portfolio)
    top_factors = sorted(current.warning.factors, key=lambda f: f.score, reverse=True)[:3]
    situation_summary = (
        f"Risk Level {current.warning.tier.upper()} ({current.warning.overall:.0f}/100). "
        f"Leading factors: " + "; ".join(f"{f.name} ({f.score:.0f})" for f in top_factors) + "."
    )
    return CrisisBriefing(
        id=briefing_id,
        simDay=sim_day,
        tier=current.warning.tier,
        overallScore=current.warning.overall,
        situationSummary=situation_summary,
        portfolioEquity=round(equity, 2),
        categoryExposure=portfolio_intelligence.category_exposure,
        recommendations=build_defensive_recommendations(portfolio, limits),
        createdAt=_now_iso(),
    )


# ---------------------------------------------------------------------------
# Institutional Survival Score (Part 2)
# ---------------------------------------------------------------------------

_SURVIVAL_GRADE_THRESHOLDS: tuple[tuple[float, InstitutionalSurvivalGrade], ...] = (
    (95.0, "a_plus"),
    (85.0, "a"),
    (70.0, "b"),
    (55.0, "c"),
    (40.0, "d"),
    (0.0, "f"),
)
_SURVIVAL_GRADE_LABEL: dict[InstitutionalSurvivalGrade, str] = {"a_plus": "A+", "a": "A", "b": "B", "c": "C", "d": "D", "f": "F"}
_SURVIVAL_HEAT_SCORE: dict[str, float] = {"cool": 90.0, "warm": 65.0, "hot": 40.0, "overheated": 15.0}

# Disclosed, published weights (sum to 1.0) — never a fitted/backtested
# blend. Cash Reserves, Drawdown Exposure, and Stress Test Survival carry
# the most weight since they are the most direct measures of whether the
# company could actually absorb a real shock right now.
_SURVIVAL_WEIGHTS: dict[str, float] = {
    "cash_reserves": 0.15,
    "diversification": 0.10,
    "concentration": 0.10,
    "liquidity": 0.10,
    "drawdown_exposure": 0.15,
    "rule_compliance": 0.10,
    "black_swan_readiness": 0.10,
    "stress_test_survival": 0.15,
    "broker_health": 0.05,
}


def _survival_grade(score: float) -> InstitutionalSurvivalGrade:
    return next(grade for threshold, grade in _SURVIVAL_GRADE_THRESHOLDS if score >= threshold)


def _stress_test_survival_score(portfolio: PaperPortfolio, limits: RiskLimits) -> tuple[float, int]:
    """Real, cheap arithmetic over the same STRESS_LEVELS ladder
    run_portfolio_stress_test() uses (no bootstrap resampling needed) —
    how many of the 5 levels the current book would survive: positive
    resulting equity and no RiskLimits.max_drawdown_pct breach."""
    # Same real-peak fix as compute_portfolio_stress_test() — see that
    # function's own comment.
    real_peak = real_peak_equity(portfolio.trade_history, portfolio.starting_balance, current_equity=portfolio_equity(portfolio))
    survived = 0
    for shock_pct in STRESS_LEVELS:
        positions_value = sum(p.quantity * p.current_price * (1 + shock_pct / 100) for p in portfolio.positions)
        resulting_equity = portfolio.cash_balance + positions_value
        resulting_drawdown_pct = max(0.0, (real_peak - resulting_equity) / real_peak * 100) if real_peak > 0 else 0.0
        if resulting_equity > 0 and resulting_drawdown_pct < limits.max_drawdown_pct:
            survived += 1
    return round(survived / len(STRESS_LEVELS) * 100, 1), survived


def compute_institutional_survival_score(
    portfolio: PaperPortfolio,
    limits: RiskLimits,
    portfolio_intelligence: PortfolioIntelligence,
    black_swan_intelligence: BlackSwanIntelligenceState,
    defensive_mode: DefensiveModeState,
) -> InstitutionalSurvivalScore:
    factors_by_name = {f.name: f for f in black_swan_intelligence.warning.factors}

    cash_pct = portfolio_intelligence.cash_pct_of_equity
    if cash_pct >= 30.0:
        cash_score = 90.0
    elif cash_pct >= 15.0:
        cash_score = 70.0
    elif cash_pct >= 5.0:
        cash_score = 45.0
    else:
        cash_score = 20.0
    cash_factor = SurvivalScoreFactor(name="Cash Reserves", score=cash_score, weight=_SURVIVAL_WEIGHTS["cash_reserves"], detail=f"Cash is {cash_pct:.0f}% of equity.")

    correlation_factor_ew = factors_by_name.get("Correlation Breakdown")
    diversification_score = 100.0 - correlation_factor_ew.score if correlation_factor_ew else 70.0
    category_count = len(portfolio_intelligence.category_exposure)
    diversification_factor = SurvivalScoreFactor(
        name="Diversification",
        score=diversification_score,
        weight=_SURVIVAL_WEIGHTS["diversification"],
        detail=f"{category_count} distinct held categor{'y' if category_count == 1 else 'ies'}. " + (correlation_factor_ew.detail if correlation_factor_ew else "No correlation read on file."),
    )

    heat = portfolio_intelligence.heat
    concentration_score = _SURVIVAL_HEAT_SCORE.get(heat.tier, 65.0)
    concentration_factor = SurvivalScoreFactor(
        name="Concentration Risk", score=concentration_score, weight=_SURVIVAL_WEIGHTS["concentration"], detail=f"Portfolio Heat reads {heat.tier} — largest position {heat.largest_position_pct:.1f}% of equity."
    )

    liquidity_factor_ew = factors_by_name.get("Liquidity")
    liquidity_score = 100.0 - liquidity_factor_ew.score if liquidity_factor_ew else 70.0
    liquidity_factor = SurvivalScoreFactor(name="Liquidity", score=liquidity_score, weight=_SURVIVAL_WEIGHTS["liquidity"], detail=liquidity_factor_ew.detail if liquidity_factor_ew else "No LiquidityRead on file yet.")

    # CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance" —
    # reuses Portfolio Heat's own real peak-to-trough drawdown reading
    # (app/portfolio_intelligence.py's `_heat()`, itself fixed this same
    # pass to use app/analytics.py::max_drawdown_pct()) rather than the
    # old `total_pnl_pct`-based proxy, so the Survival Score never
    # disagrees with the Portfolio Heat card or app/risk_engine.py's own
    # gates about the same real state.
    current_drawdown_pct = heat.unrealized_drawdown_pct
    room_pct = max(0.0, limits.max_drawdown_pct - current_drawdown_pct)
    drawdown_score = round(min(100.0, room_pct / limits.max_drawdown_pct * 100), 1) if limits.max_drawdown_pct > 0 else 0.0
    drawdown_factor = SurvivalScoreFactor(
        name="Drawdown Exposure",
        score=drawdown_score,
        weight=_SURVIVAL_WEIGHTS["drawdown_exposure"],
        detail=f"Current drawdown {current_drawdown_pct:.1f}% against a {limits.max_drawdown_pct:.0f}% max — {room_pct:.1f} points of room remain.",
    )

    risk_factor_ew = factors_by_name.get("Active Risk Warnings")
    compliance_score = 100.0 - risk_factor_ew.score if risk_factor_ew else 90.0
    compliance_factor = SurvivalScoreFactor(name="Rule Compliance", score=compliance_score, weight=_SURVIVAL_WEIGHTS["rule_compliance"], detail=risk_factor_ew.detail if risk_factor_ew else "No active RiskWarnings.")

    readiness_score = round(0.5 * (100.0 if defensive_mode.auto_trigger_enabled else 40.0) + 0.5 * (100.0 - black_swan_intelligence.warning.overall), 1)
    readiness_factor = SurvivalScoreFactor(
        name="Black Swan Readiness",
        score=readiness_score,
        weight=_SURVIVAL_WEIGHTS["black_swan_readiness"],
        detail=f"Defensive Mode auto-trigger is {'enabled' if defensive_mode.auto_trigger_enabled else 'disabled'}; current Early Warning Score is {black_swan_intelligence.warning.overall:.0f}/100 ({black_swan_intelligence.warning.tier.upper()}).",
    )

    stress_score, survived_levels = _stress_test_survival_score(portfolio, limits)
    stress_factor = SurvivalScoreFactor(
        name="Stress Test Survival",
        score=stress_score,
        weight=_SURVIVAL_WEIGHTS["stress_test_survival"],
        detail=f"Survives {survived_levels}/{len(STRESS_LEVELS)} of the standard -10/-20/-35/-50/-70% shock ladder without breaching the max drawdown limit.",
    )

    broker_factor = SurvivalScoreFactor(
        name="Broker Health",
        score=80.0,
        weight=_SURVIVAL_WEIGHTS["broker_health"],
        detail="PaperBroker is fully simulated — not a real monitored counterparty risk. Scored at a fixed, disclosed baseline rather than a fabricated live health number.",
    )

    factors = [cash_factor, diversification_factor, concentration_factor, liquidity_factor, drawdown_factor, compliance_factor, readiness_factor, stress_factor, broker_factor]
    overall = round(sum(f.score * f.weight for f in factors), 1)
    grade = _survival_grade(overall)

    ranked = sorted(factors, key=lambda f: f.score, reverse=True)
    primary_strengths = [f"{f.name} ({f.score:.0f}/100)" for f in ranked[:3]]
    primary_weaknesses = [f"{f.name} ({f.score:.0f}/100)" for f in reversed(ranked[-3:])]
    top_improvements = [f"{f.name}: {f.detail}" for f in reversed(ranked[-5:])]

    reasoning = f"Institutional Survival Score reads {overall:.1f}/100 ({_SURVIVAL_GRADE_LABEL[grade]}): " + "; ".join(f"{f.name} {f.score:.0f}" for f in factors) + "."

    return InstitutionalSurvivalScore(
        overall=overall,
        grade=grade,
        factors=factors,
        primaryStrengths=primary_strengths,
        primaryWeaknesses=primary_weaknesses,
        topImprovements=top_improvements,
        reasoning=reasoning,
        updatedAt=_now_iso(),
    )
