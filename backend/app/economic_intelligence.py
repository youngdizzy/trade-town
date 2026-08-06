"""Economic Intelligence Center (EIC) — Design Bible Chapter 71.

THE HONESTY BOUNDARY (read this before adding anything to the brief's
much longer list of sections):

This codebase has no real macroeconomic data source anywhere. There are
no API keys, no live feed of any kind — app/market_data.py's own module
docstring already establishes this for prices ("this repo holds no API
keys"), and app/market_intelligence.py's own docstring goes further,
naming "any real economic calendar" as something explicitly NOT built
because no real data source exists. Nothing in this pass changes that.

So the Chapter 71 brief's biggest sections are cut outright, the same
way market_intelligence.py already cut its own overlapping list:

  - Central Bank Intelligence (Fed/ECB/BOJ/BOE/PBOC rate decisions,
    minutes, speeches, press conferences) — no real data source.
  - A real Economic Calendar (CPI, PPI, NFP, FOMC, GDP releases, Retail
    Sales, Treasury Auctions, earnings seasons, consensus estimates) —
    already an explicit prior cut in market_intelligence.py; not
    reopened here.
  - Global Event Intelligence (wars, elections, disasters, geopolitical
    conflicts) with estimated probability/severity/market impact — no
    real geopolitical data source; inventing probabilities for events
    that don't exist here would be exactly the kind of fabrication
    app/confidence.py's own docstring already refuses to do.
  - Real macro indicators (Inflation, Interest Rates, GDP Growth,
    Unemployment, Treasury Yields, Consumer/Business Confidence, PMI,
    Retail Sales, Housing, DXY, Global Liquidity) and any AI forecast of
    them (inflation direction, rate expectations, recession probability)
    — no real data source, and no mechanic anywhere in this codebase
    these would even feed (no bond market, no currency market, no
    interest-rate-sensitive position exists to make an invented interest
    rate meaningful rather than decorative).
  - A Sector Impact Engine keyed to real named sectors (Technology,
    Financials, Healthcare, ...) — this codebase has no real sector
    taxonomy anywhere (app/portfolio_intelligence.py's own
    CategoryExposure docstring and app/risk_engine.py's
    evaluate_guardian_exposure() both already establish this identical
    honesty note). Category-based exposure (below) is the real thing
    this codebase actually has.
  - Scenario Planning (Bull/Base/Bear/Black Swan cases) tied to macro
    outcomes this module doesn't forecast — cut; app/whatif.py's own
    "SIMULATED"-labeled Simulation Lab is the closer real fit for
    hypothetical position outcomes and already exists.

What IS real and newly built here — a genuine cross-signal SYNTHESIS
layer over state this codebase already computes honestly, tying together
what today sits in three separate departments with no shared read:

  - Regime Favorability -> app/market_environment.py's real 5-way regime
    (Chapter 65), derived from real (mock) watchlist price action.
  - Market Quality -> app/market_intelligence.py's real MarketQualityScore
    (0-100, already a real published blend of regime/volatility/session/
    momentum/liquidity reads).
  - News Risk -> app/market_intelligence.py's real NewsRiskRead (a named
    proxy: the count of real market-category NewsItem records on file).
  - Correlation Clustering -> app/portfolio_intelligence.py's real
    CorrelationPair list (real Pearson correlation from real (mock)
    candle returns, already filtered to only pairs clearing
    CORRELATION_CLUSTER_THRESHOLD).
  - Concentration -> app/portfolio_intelligence.py's real PortfolioHeat
    tier (largest position / hottest category / drawdown blend).

Every factor is its own named, published multiplier — never a hidden
blend (this Design Bible's "no black-box composite" convention). The
Economic Confidence Engine (EconomicConfidenceRead) wraps the resulting
score honestly: confidence, evidence quality, and named supporting/
contradicting evidence, exactly matching the brief's own "never present
forecasts as facts" requirement, applied to a synthesis of real signals
rather than to a fabricated macro forecast.

The Market Narrative Engine (generate_market_narrative) never invents
causality like "the Fed cut rates" — it diffs today's real read against
the company's own last stored EconomicIntelligenceReport and names the
specific real signal(s) that actually moved. This is, by construction,
this codebase's honest answer to "explain why, not just what happened."

Scope note: this module does not become a new Executive Board voting
seat in this pass (ExecutiveDepartmentRole is unchanged). Its own real
signal set already overlaps heavily with Market Intelligence's (both
read the same regime); adding a structurally-near-duplicate vote would
cut against this Design Bible's "avoid duplicate systems and overlapping
responsibilities" principle. EIC ships here as a real, standalone
dashboard/report layer — see the Chapter 70 Part 3 addendum for the
precedent of wiring an advisory system into a decision pipeline only as
an explicit follow-up, not bundled into its first pass.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from app.schemas import (
    EconomicConfidenceRead,
    EconomicHealthScore,
    EconomicHealthTier,
    EconomicIntelligenceReport,
    EconomicIntelligenceState,
    EconomicSignalFactor,
    MarketEnvironmentState,
    MarketIntelligenceState,
    MarketNarrativeEntry,
    PortfolioIntelligence,
)

MAX_ECONOMIC_INTELLIGENCE_REPORTS = 60

# Same 80/65/45/25/0 boundaries app/market_intelligence.py's own
# _QUALITY_TIER_THRESHOLDS already uses — EIC's score lives on the exact
# same 0-100 scale over the exact same kind of real, computed signals.
_HEALTH_TIER_THRESHOLDS: tuple[tuple[float, EconomicHealthTier], ...] = (
    (80.0, "thriving"),
    (65.0, "stable"),
    (45.0, "cautious"),
    (25.0, "stressed"),
    (0.0, "critical"),
)

# Published, disclosed regime->score table (never derived from a
# backtest this codebase doesn't have) — directionally honest: bull
# scores highest, bear lowest, high volatility scores below low
# volatility since it represents more uncertainty, not less.
_REGIME_FAVORABILITY: dict[str, float] = {
    "bull": 85.0,
    "low_volatility": 65.0,
    "sideways": 60.0,
    "high_volatility": 40.0,
    "bear": 30.0,
}
_NEWS_RISK_SCORE: dict[str, float] = {"low": 85.0, "moderate": 55.0, "elevated": 25.0}
_HEAT_TIER_SCORE: dict[str, float] = {
    "cool": 90.0,
    "warm": 70.0,
    "hot": 45.0,
    "overheated": 15.0,
}

# Regime + Market Quality are the broadest real reads of the operating
# environment, so they carry the most weight; the three portfolio-
# specific overlay signals (news risk, correlation, concentration) carry
# less. A disclosed, published split — never a fitted/backtested one.
_WEIGHTS = {
    "regime": 0.25,
    "quality": 0.25,
    "news_risk": 0.20,
    "correlation": 0.15,
    "concentration": 0.15,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _health_tier(score: float) -> EconomicHealthTier:
    return next(tier for threshold, tier in _HEALTH_TIER_THRESHOLDS if score >= threshold)


def compute_economic_health(
    market_environment: MarketEnvironmentState,
    market_intelligence: MarketIntelligenceState,
    portfolio_intelligence: PortfolioIntelligence,
) -> EconomicHealthScore:
    regime_score = _REGIME_FAVORABILITY.get(market_environment.current, 60.0)
    regime_factor = EconomicSignalFactor(
        name="Regime Favorability",
        score=regime_score,
        weight=_WEIGHTS["regime"],
        detail=f"Market Environment regime is {market_environment.label} — {market_environment.detail}",
    )

    quality = market_intelligence.quality
    quality_factor = EconomicSignalFactor(
        name="Market Quality",
        score=quality.score,
        weight=_WEIGHTS["quality"],
        detail=f"Market Intelligence rates current conditions {quality.tier} ({quality.score:.0f}/100) — {quality.reasoning}",
    )

    news_risk = market_intelligence.news_risk
    news_score = _NEWS_RISK_SCORE.get(news_risk.risk_level, 55.0)
    news_factor = EconomicSignalFactor(
        name="News Risk",
        score=news_score,
        weight=_WEIGHTS["news_risk"],
        detail=f"{news_risk.active_market_news_count} active market-category news item(s) on file — {news_risk.risk_level} risk level.",
    )

    clustered_pairs = len(portfolio_intelligence.correlation_pairs)
    correlation_score = max(20.0, 100.0 - 20.0 * clustered_pairs)
    correlation_factor = EconomicSignalFactor(
        name="Correlation Clustering",
        score=correlation_score,
        weight=_WEIGHTS["correlation"],
        detail=(
            f"{clustered_pairs} held-position pair(s) currently correlated above this company's own clustering threshold."
            if clustered_pairs
            else "No held-position pairs are currently correlated above this company's own clustering threshold."
        ),
    )

    heat = portfolio_intelligence.heat
    concentration_score = _HEAT_TIER_SCORE.get(heat.tier, 70.0)
    concentration_factor = EconomicSignalFactor(
        name="Concentration",
        score=concentration_score,
        weight=_WEIGHTS["concentration"],
        detail=f"Portfolio Heat reads {heat.tier} — largest position {heat.largest_position_pct:.1f}% of equity, {heat.total_capital_at_risk_pct:.1f}% of equity at risk.",
    )

    factors = [regime_factor, quality_factor, news_factor, correlation_factor, concentration_factor]
    overall = round(sum(f.score * f.weight for f in factors), 1)
    tier = _health_tier(overall)
    reasoning = (
        f"Economic Health reads {tier} ({overall:.1f}/100): "
        + "; ".join(f"{f.name} {f.score:.0f}" for f in factors)
        + "."
    )
    return EconomicHealthScore(overall=overall, tier=tier, factors=factors, reasoning=reasoning)


def compute_economic_confidence(
    health: EconomicHealthScore, portfolio_intelligence: PortfolioIntelligence
) -> EconomicConfidenceRead:
    """Never presents the health read as fact — real evidence quality
    tied to how many factors were computed from genuine measurement
    rather than a "nothing to measure yet" default (correlation needs at
    least 2 open positions to be a real read; concentration needs at
    least 1)."""
    open_count = sum(e.position_count for e in portfolio_intelligence.category_exposure)
    real_factor_count = 3  # regime, quality, news risk are always real reads
    real_factor_count += 1 if open_count >= 1 else 0  # concentration
    real_factor_count += 1 if open_count >= 2 else 0  # correlation

    confidence_pct = round(min(100.0, 40.0 + 12.0 * real_factor_count), 1)
    evidence_quality: Literal["thin", "moderate", "strong"]
    if real_factor_count >= 5:
        evidence_quality = "strong"
    elif real_factor_count >= 4:
        evidence_quality = "moderate"
    else:
        evidence_quality = "thin"

    supporting = [f"{f.name}: {f.detail}" for f in health.factors if f.score >= 60.0]
    contradicting = [f"{f.name}: {f.detail}" for f in health.factors if f.score < 60.0]

    key_assumptions = [
        "Regime and Market Quality are derived from this company's own simulated (mock) price data, not a live market feed.",
        "No real macroeconomic data (inflation, interest rates, GDP, employment) is tracked anywhere in this codebase; this score reflects only real, internally-computed trading-environment signals.",
        "Correlation and Concentration reflect this company's own current open positions, not the full market.",
    ]

    if health.factors:
        worst = min(health.factors, key=lambda f: f.score)
        recomputed = sum(
            (60.0 if f is worst else f.score) * f.weight for f in health.factors
        )
        recomputed_tier = _health_tier(round(recomputed, 1))
        if recomputed_tier != health.tier:
            alternative_outcome = (
                f"If {worst.name} alone improved to a neutral reading, Economic Health would likely move from "
                f"{health.tier} toward {recomputed_tier}."
            )
        else:
            alternative_outcome = (
                f"No single factor is currently close to shifting Economic Health out of the {health.tier} tier "
                f"on its own — even a neutral {worst.name} reading would not change the tier."
            )
    else:
        alternative_outcome = "No factors computed yet."

    return EconomicConfidenceRead(
        confidencePct=confidence_pct,
        evidenceQuality=evidence_quality,
        supportingEvidence=supporting,
        contradictingEvidence=contradicting,
        keyAssumptions=key_assumptions,
        alternativeOutcome=alternative_outcome,
    )


def compute_economic_intelligence(
    market_environment: MarketEnvironmentState,
    market_intelligence: MarketIntelligenceState,
    portfolio_intelligence: PortfolioIntelligence,
) -> EconomicIntelligenceState:
    health = compute_economic_health(market_environment, market_intelligence, portfolio_intelligence)
    confidence = compute_economic_confidence(health, portfolio_intelligence)
    return EconomicIntelligenceState(
        regime=market_environment.current,
        regimeLabel=market_environment.label,
        marketQualityTier=market_intelligence.quality.tier,
        health=health,
        confidence=confidence,
        correlationPairs=portfolio_intelligence.correlation_pairs,
        categoryExposure=portfolio_intelligence.category_exposure,
        newsRisk=market_intelligence.news_risk,
        updatedAt=_now_iso(),
    )


def generate_market_narrative(
    current: EconomicIntelligenceState,
    previous_report: EconomicIntelligenceReport | None,
    sim_day: int,
) -> MarketNarrativeEntry:
    """Diffs against the most recent stored daily report (never the
    previous tick — a whole day's baseline keeps this from re-narrating
    the same read every five simulated minutes). Cites only real,
    computed deltas — never invented external causality."""
    if previous_report is None:
        headline = "Economic Intelligence Center online — establishing baseline."
        body = (
            f"First Economic Intelligence read on file. Regime: {current.regime_label}. "
            f"Economic Health: {current.health.tier} ({current.health.overall:.0f}/100)."
        )
        evidence = [f"{f.name}: {f.detail}" for f in current.health.factors]
        return MarketNarrativeEntry(id=f"narrative-{sim_day}-baseline", headline=headline, body=body, evidence=evidence, simDay=sim_day, createdAt=_now_iso())

    prev = previous_report.snapshot
    deltas: list[str] = []
    if current.regime != prev.regime:
        deltas.append(f"Market regime shifted from {prev.regime_label} to {current.regime_label}.")
    if current.health.tier != prev.health.tier:
        deltas.append(
            f"Economic Health moved from {prev.health.tier} ({prev.health.overall:.0f}) to {current.health.tier} ({current.health.overall:.0f})."
        )
    elif abs(current.health.overall - prev.health.overall) >= 5.0:
        deltas.append(
            f"Economic Health held in the {current.health.tier} tier but moved {current.health.overall - prev.health.overall:+.0f} points to {current.health.overall:.0f}."
        )
    if current.news_risk.risk_level != prev.news_risk.risk_level:
        deltas.append(f"News Risk moved from {prev.news_risk.risk_level} to {current.news_risk.risk_level}.")
    if len(current.correlation_pairs) != len(prev.correlation_pairs):
        deltas.append(
            f"Portfolio correlation clustering changed from {len(prev.correlation_pairs)} flagged pair(s) to {len(current.correlation_pairs)}."
        )

    if not deltas:
        headline = f"Economic environment steady — {current.health.tier} ({current.health.overall:.0f}/100)."
        body = f"No material change since Day {previous_report.sim_day}'s report. Regime remains {current.regime_label}; Economic Health remains {current.health.tier}."
        evidence = [f"{f.name}: {f.detail}" for f in current.health.factors]
    else:
        headline = deltas[0]
        body = " ".join(deltas)
        evidence = deltas

    return MarketNarrativeEntry(id=f"narrative-{sim_day}", headline=headline, body=body, evidence=evidence, simDay=sim_day, createdAt=_now_iso())


def generate_economic_intelligence_report(
    current: EconomicIntelligenceState,
    previous_report: EconomicIntelligenceReport | None,
    sim_day: int,
) -> EconomicIntelligenceReport:
    narrative = generate_market_narrative(current, previous_report, sim_day)
    return EconomicIntelligenceReport(
        id=f"eic-report-{sim_day}",
        simDay=sim_day,
        snapshot=current,
        narrative=narrative,
        createdAt=_now_iso(),
    )


def record_economic_intelligence_report(
    history: list[EconomicIntelligenceReport], report: EconomicIntelligenceReport
) -> list[EconomicIntelligenceReport]:
    updated = [*history, report]
    if len(updated) > MAX_ECONOMIC_INTELLIGENCE_REPORTS:
        del updated[: len(updated) - MAX_ECONOMIC_INTELLIGENCE_REPORTS]
    return updated
