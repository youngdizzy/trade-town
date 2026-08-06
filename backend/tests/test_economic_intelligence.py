"""Covers app/economic_intelligence.py — Design Bible Chapter 71, the
Economic Intelligence Center. Every factor must trace back to a real
already-computed signal (Market Environment regime, Market Intelligence
quality/news-risk, Portfolio Intelligence correlation/heat) — never a
fabricated macro number. See the module's own docstring for the full
honesty boundary.
"""
from __future__ import annotations

import asyncio

from app.economic_intelligence import (
    MAX_ECONOMIC_INTELLIGENCE_REPORTS,
    compute_economic_confidence,
    compute_economic_health,
    compute_economic_intelligence,
    generate_economic_intelligence_report,
    generate_market_narrative,
    record_economic_intelligence_report,
)
from app.market_environment import default_market_environment
from app.market_intelligence import default_market_intelligence_state
from app.portfolio import default_portfolio
from app.portfolio_intelligence import compute_portfolio_intelligence
from app.market_data import MockMarketDataProvider
from app.schemas import CategoryExposure, CorrelationPair, PortfolioIntelligence


def _portfolio_intelligence(
    *, correlation_pairs: list[CorrelationPair] | None = None, category_exposure: list[CategoryExposure] | None = None, heat_tier: str = "cool"
) -> PortfolioIntelligence:
    base = compute_portfolio_intelligence(default_portfolio(), MockMarketDataProvider(), pending_proposal_count=0)
    heat = base.heat.model_copy(update={"tier": heat_tier})
    return base.model_copy(update={"correlation_pairs": correlation_pairs or [], "category_exposure": category_exposure or [], "heat": heat})


def _pair(symbol_a: str = "AAPL", symbol_b: str = "MSFT", correlation: float = 0.8) -> CorrelationPair:
    return CorrelationPair(symbolA=symbol_a, symbolB=symbol_b, correlation=correlation, direction="positive")


def _exposure(category: str = "stock", position_count: int = 1) -> CategoryExposure:
    return CategoryExposure(category=category, positionCount=position_count, value=1000.0, pctOfEquity=10.0)


class TestComputeEconomicHealth:
    def test_bull_regime_scores_higher_than_bear(self) -> None:
        mi = default_market_intelligence_state()
        pi = _portfolio_intelligence()
        bull = compute_economic_health(default_market_environment().model_copy(update={"current": "bull"}), mi, pi)
        bear = compute_economic_health(default_market_environment().model_copy(update={"current": "bear"}), mi, pi)
        assert bull.overall > bear.overall

    def test_market_quality_factor_passes_through_the_real_score(self) -> None:
        mi = default_market_intelligence_state().model_copy(update={"quality": default_market_intelligence_state().quality.model_copy(update={"score": 90.0, "tier": "excellent"})})
        health = compute_economic_health(default_market_environment(), mi, _portfolio_intelligence())
        quality_factor = next(f for f in health.factors if f.name == "Market Quality")
        assert quality_factor.score == 90.0

    def test_elevated_news_risk_scores_lower_than_low(self) -> None:
        env = default_market_environment()
        pi = _portfolio_intelligence()
        low = default_market_intelligence_state().model_copy(update={"news_risk": default_market_intelligence_state().news_risk.model_copy(update={"risk_level": "low"})})
        elevated = default_market_intelligence_state().model_copy(update={"news_risk": default_market_intelligence_state().news_risk.model_copy(update={"risk_level": "elevated"})})
        low_health = compute_economic_health(env, low, pi)
        elevated_health = compute_economic_health(env, elevated, pi)
        assert low_health.overall > elevated_health.overall

    def test_more_correlated_pairs_lowers_the_correlation_factor(self) -> None:
        env = default_market_environment()
        mi = default_market_intelligence_state()
        none = compute_economic_health(env, mi, _portfolio_intelligence(correlation_pairs=[]))
        clustered = compute_economic_health(env, mi, _portfolio_intelligence(correlation_pairs=[_pair(), _pair("SPY", "QQQ")]))
        none_factor = next(f for f in none.factors if f.name == "Correlation Clustering")
        clustered_factor = next(f for f in clustered.factors if f.name == "Correlation Clustering")
        assert clustered_factor.score < none_factor.score

    def test_heat_tier_ordering_maps_to_descending_concentration_score(self) -> None:
        env = default_market_environment()
        mi = default_market_intelligence_state()
        scores = {}
        for tier in ("cool", "warm", "hot", "overheated"):
            health = compute_economic_health(env, mi, _portfolio_intelligence(heat_tier=tier))
            scores[tier] = next(f for f in health.factors if f.name == "Concentration").score
        assert scores["cool"] > scores["warm"] > scores["hot"] > scores["overheated"]

    def test_overall_is_never_a_black_box_it_is_a_published_weighted_sum(self) -> None:
        env = default_market_environment()
        mi = default_market_intelligence_state()
        pi = _portfolio_intelligence()
        health = compute_economic_health(env, mi, pi)
        expected = round(sum(f.score * f.weight for f in health.factors), 1)
        assert health.overall == expected

    def test_weights_sum_to_one(self) -> None:
        health = compute_economic_health(default_market_environment(), default_market_intelligence_state(), _portfolio_intelligence())
        assert round(sum(f.weight for f in health.factors), 6) == 1.0

    def test_tier_boundaries(self) -> None:
        from app.economic_intelligence import _health_tier

        assert _health_tier(85.0) == "thriving"
        assert _health_tier(70.0) == "stable"
        assert _health_tier(50.0) == "cautious"
        assert _health_tier(30.0) == "stressed"
        assert _health_tier(10.0) == "critical"


class TestComputeEconomicConfidence:
    def test_no_open_positions_is_thin_or_moderate_never_strong(self) -> None:
        health = compute_economic_health(default_market_environment(), default_market_intelligence_state(), _portfolio_intelligence())
        confidence = compute_economic_confidence(health, _portfolio_intelligence())
        assert confidence.evidence_quality != "strong"

    def test_two_or_more_open_positions_raises_evidence_quality_to_strong(self) -> None:
        pi = _portfolio_intelligence(category_exposure=[_exposure(position_count=2)])
        health = compute_economic_health(default_market_environment(), default_market_intelligence_state(), pi)
        confidence = compute_economic_confidence(health, pi)
        assert confidence.evidence_quality == "strong"
        assert confidence.confidence_pct == 100.0

    def test_supporting_and_contradicting_evidence_partition_by_score(self) -> None:
        mi = default_market_intelligence_state().model_copy(update={"news_risk": default_market_intelligence_state().news_risk.model_copy(update={"risk_level": "elevated"})})
        health = compute_economic_health(default_market_environment().model_copy(update={"current": "bull"}), mi, _portfolio_intelligence())
        confidence = compute_economic_confidence(health, _portfolio_intelligence())
        assert any("Regime Favorability" in e for e in confidence.supporting_evidence)
        assert any("News Risk" in e for e in confidence.contradicting_evidence)

    def test_never_presents_the_read_as_fact_assumptions_are_always_disclosed(self) -> None:
        health = compute_economic_health(default_market_environment(), default_market_intelligence_state(), _portfolio_intelligence())
        confidence = compute_economic_confidence(health, _portfolio_intelligence())
        assert confidence.key_assumptions
        assert confidence.alternative_outcome


class TestGenerateMarketNarrative:
    def test_first_report_establishes_a_baseline(self) -> None:
        current = compute_economic_intelligence(default_market_environment(), default_market_intelligence_state(), _portfolio_intelligence())
        narrative = generate_market_narrative(current, None, sim_day=1)
        assert "baseline" in narrative.headline.lower()

    def test_regime_change_is_named_in_the_narrative(self) -> None:
        prev_state = compute_economic_intelligence(default_market_environment().model_copy(update={"current": "sideways"}), default_market_intelligence_state(), _portfolio_intelligence())
        prev_report = generate_economic_intelligence_report(prev_state, None, sim_day=1)
        current = compute_economic_intelligence(default_market_environment().model_copy(update={"current": "bull"}), default_market_intelligence_state(), _portfolio_intelligence())
        narrative = generate_market_narrative(current, prev_report, sim_day=2)
        assert "regime shifted" in narrative.body.lower()

    def test_no_material_change_reports_steady(self) -> None:
        state = compute_economic_intelligence(default_market_environment(), default_market_intelligence_state(), _portfolio_intelligence())
        report = generate_economic_intelligence_report(state, None, sim_day=1)
        narrative = generate_market_narrative(state, report, sim_day=2)
        assert "steady" in narrative.headline.lower()

    def test_never_invents_external_causality(self) -> None:
        """The one thing this module must never do: attribute a change to
        something this codebase has no real data for."""
        prev_state = compute_economic_intelligence(default_market_environment().model_copy(update={"current": "bull"}), default_market_intelligence_state(), _portfolio_intelligence())
        prev_report = generate_economic_intelligence_report(prev_state, None, sim_day=1)
        current = compute_economic_intelligence(default_market_environment().model_copy(update={"current": "bear"}), default_market_intelligence_state(), _portfolio_intelligence())
        narrative = generate_market_narrative(current, prev_report, sim_day=2)
        for banned in ("fed", "interest rate", "inflation", "gdp", "central bank"):
            assert banned not in narrative.body.lower()
            assert banned not in narrative.headline.lower()


class TestRecordEconomicIntelligenceReport:
    def test_caps_history_at_max(self) -> None:
        history: list = []
        state = compute_economic_intelligence(default_market_environment(), default_market_intelligence_state(), _portfolio_intelligence())
        for day in range(1, MAX_ECONOMIC_INTELLIGENCE_REPORTS + 10):
            report = generate_economic_intelligence_report(state, history[-1] if history else None, sim_day=day)
            history = record_economic_intelligence_report(history, report)
        assert len(history) == MAX_ECONOMIC_INTELLIGENCE_REPORTS

    def test_evicts_oldest_first(self) -> None:
        history: list = []
        state = compute_economic_intelligence(default_market_environment(), default_market_intelligence_state(), _portfolio_intelligence())
        for day in range(1, MAX_ECONOMIC_INTELLIGENCE_REPORTS + 5):
            report = generate_economic_intelligence_report(state, history[-1] if history else None, sim_day=day)
            history = record_economic_intelligence_report(history, report)
        assert history[0].sim_day == 5
        assert history[-1].sim_day == MAX_ECONOMIC_INTELLIGENCE_REPORTS + 4


class TestComputeEconomicIntelligenceEndToEnd:
    def test_produces_a_fully_formed_state(self) -> None:
        state = compute_economic_intelligence(default_market_environment(), default_market_intelligence_state(), _portfolio_intelligence())
        assert 0.0 <= state.health.overall <= 100.0
        assert state.health.tier in ("thriving", "stable", "cautious", "stressed", "critical")
        assert state.confidence.evidence_quality in ("thin", "moderate", "strong")
        assert state.regime == "sideways"


class TestNexusDailyCadence:
    """Confirms the real production wiring, not just the module in
    isolation: app/nexus.py's tick() actually records one Economic
    Intelligence Brief per real in-game evening, the same cadence proven
    for Market Intelligence's own Executive Market Brief."""

    def test_workday_end_records_exactly_one_daily_report(self) -> None:
        from app.state import GameState

        state = GameState()
        assert state.data.economic_intelligence_reports == []
        saved, error = asyncio.run(state.advance_time("workday_end", None))
        assert error is None
        assert len(saved.economic_intelligence_reports) == 1
        assert saved.economic_intelligence_reports[0].sim_day == saved.time.day

    def test_current_economic_intelligence_is_always_present(self) -> None:
        from app.state import GameState

        state = GameState()
        saved, error = asyncio.run(state.advance_time("workday_end", None))
        assert error is None
        assert saved.economic_intelligence.health.overall >= 0.0
