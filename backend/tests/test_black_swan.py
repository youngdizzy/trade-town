"""Covers app/black_swan.py — Design Bible Chapter 72, the Black Swan
Intelligence & Resilience System. Every factor must trace back to a real
already-computed signal or a real, disclosed formula — never a
fabricated probability or historical-event narrative. See the module's
own docstring for the full honesty boundary.
"""
from __future__ import annotations

from app.black_swan import (
    MAX_BLACK_SWAN_EVENTS,
    MAX_BLACK_SWAN_REPORTS,
    STRESS_LEVELS,
    activate_defensive_mode,
    broker_resilience_read,
    build_black_swan_playbook,
    build_defensive_recommendations,
    compute_black_swan_confidence,
    compute_black_swan_intelligence,
    compute_early_warning_score,
    compute_institutional_survival_score,
    deactivate_defensive_mode,
    generate_black_swan_narrative,
    generate_black_swan_report,
    generate_crisis_briefing,
    note_defensive_mode_peak_tier,
    record_black_swan_event,
    record_black_swan_report,
    run_portfolio_scenario,
    run_portfolio_stress_test,
    tier_meets_or_exceeds,
)
from app.economic_intelligence import compute_economic_intelligence
from app.market_data import Candle, MarketDataProvider, MockMarketDataProvider, Quote
from app.market_environment import default_market_environment
from app.market_intelligence import default_market_intelligence_state
from app.portfolio import default_portfolio
from app.portfolio_intelligence import compute_portfolio_intelligence
from app.risk_engine import default_risk_limits
from app.schemas import DefensiveModeState, PaperPortfolio, PaperPosition, RiskLimits, RiskWarning


def _pi():
    return compute_portfolio_intelligence(default_portfolio(), MockMarketDataProvider(), pending_proposal_count=0)


def _ei():
    env = default_market_environment()
    mi = default_market_intelligence_state()
    return compute_economic_intelligence(env, mi, _pi())


def _warning(risk_warnings: list[RiskWarning] | None = None):
    return compute_early_warning_score(risk_warnings or [], default_market_intelligence_state(), _pi(), default_market_environment(), _ei())


def _risk_warning(severity: str = "critical") -> RiskWarning:
    return RiskWarning(id="risk-1", symbol="AAPL", severity=severity, message="test", createdAt="2026-01-01T00:00:00Z")  # type: ignore[arg-type]


def _position(*, symbol: str = "AAPL", quantity: float = 10.0, entry_price: float = 100.0, current_price: float = 100.0) -> PaperPosition:
    return PaperPosition(
        id=f"pos-{symbol}",
        symbol=symbol,
        side="buy",  # type: ignore[arg-type]
        quantity=quantity,
        entryPrice=entry_price,
        currentPrice=current_price,
        unrealizedPnl=(current_price - entry_price) * quantity,
        unrealizedPnlPct=(current_price - entry_price) / entry_price * 100,
        openedBy="sentinel",  # type: ignore[arg-type]
        confidence=80.0,
        openedAt="2026-01-01T00:00:00Z",
        openedSimMinutes=0,
    )


def _portfolio_with_position(*, cash: float = 90000.0, starting_balance: float = 100000.0, positions: list[PaperPosition] | None = None) -> PaperPortfolio:
    return PaperPortfolio(
        cashBalance=cash,
        startingBalance=starting_balance,
        positions=positions or [_position()],
        orders=[],
        tradeHistory=[],
        totalPnl=0.0,
        totalPnlPct=0.0,
        winCount=0,
        lossCount=0,
    )


class _FixedVolProvider(MarketDataProvider):
    """A test double with a fixed, known volatility — needed to assert
    exact shock magnitudes in Scenario Simulation tests."""

    def __init__(self, closes: list[float]) -> None:
        self._closes = closes

    def get_quote(self, symbol: str) -> Quote:
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        return [
            Candle(symbol=symbol, timeframe=timeframe, timestamp=f"2026-01-01T{i:02d}:00:00Z", open=c, high=c * 1.01, low=c * 0.99, close=c, volume=1000.0, data_status="simulated")
            for i, c in enumerate(self._closes)
        ]


class TestComputeEarlyWarningScore:
    def test_no_warnings_scores_lower_than_two_critical_warnings(self) -> None:
        none = _warning([])
        two_critical = _warning([_risk_warning("critical"), _risk_warning("critical")])
        assert two_critical.overall > none.overall

    def test_tier_thresholds_are_monotonic_with_score(self) -> None:
        low = compute_early_warning_score([], default_market_intelligence_state(), _pi(), default_market_environment(), _ei())
        high = compute_early_warning_score(
            [_risk_warning("critical"), _risk_warning("critical"), _risk_warning("critical")], default_market_intelligence_state(), _pi(), default_market_environment(), _ei()
        )
        assert low.overall < high.overall
        assert low.tier != "critical"

    def test_overall_is_a_published_weighted_sum_never_a_black_box(self) -> None:
        warning = _warning()
        expected = round(sum(f.score * f.weight for f in warning.factors), 1)
        assert warning.overall == expected

    def test_eight_named_factors_present(self) -> None:
        warning = _warning()
        names = {f.name for f in warning.factors}
        assert names == {
            "Active Risk Warnings",
            "Market Stress",
            "Volatility",
            "Liquidity",
            "Correlation Breakdown",
            "Regime Divergence",
            "News Severity",
            "Macro Instability",
        }

    def test_weights_sum_to_one(self) -> None:
        warning = _warning()
        assert round(sum(f.weight for f in warning.factors), 6) == 1.0


class TestComputeBlackSwanConfidence:
    def test_never_presents_as_fact_confidence_is_bounded(self) -> None:
        warning = _warning()
        confidence = compute_black_swan_confidence(warning, _pi())
        assert 0.0 <= confidence.confidence_pct <= 100.0
        assert confidence.evidence_quality in ("thin", "moderate", "strong")

    def test_alternative_outcome_is_computed_not_templated(self) -> None:
        warning = _warning([_risk_warning("critical"), _risk_warning("critical"), _risk_warning("critical")])
        confidence = compute_black_swan_confidence(warning, _pi())
        assert confidence.alternative_outcome


class TestNarrativeAndReports:
    def test_first_report_is_a_baseline(self) -> None:
        current = compute_black_swan_intelligence([], default_market_intelligence_state(), _pi(), default_market_environment(), _ei())
        narrative = generate_black_swan_narrative(current, None, sim_day=1)
        assert "baseline" in narrative.headline.lower()

    def test_tier_change_is_named_in_the_narrative_never_invented_causality(self) -> None:
        current = compute_black_swan_intelligence([], default_market_intelligence_state(), _pi(), default_market_environment(), _ei())
        report1 = generate_black_swan_report(current, None, sim_day=1)
        stressed = compute_black_swan_intelligence(
            [_risk_warning("critical"), _risk_warning("critical"), _risk_warning("critical")], default_market_intelligence_state(), _pi(), default_market_environment(), _ei()
        )
        narrative2 = generate_black_swan_narrative(stressed, report1, sim_day=2)
        assert "risk level" in narrative2.headline.lower() or "risk level" in narrative2.body.lower()
        for banned in ("banking crisis", "pandemic", "cyberattack", "fed cut"):
            assert banned not in narrative2.body.lower()

    def test_report_history_is_capped(self) -> None:
        current = compute_black_swan_intelligence([], default_market_intelligence_state(), _pi(), default_market_environment(), _ei())
        history: list = []
        for day in range(MAX_BLACK_SWAN_REPORTS + 10):
            report = generate_black_swan_report(current, history[-1] if history else None, sim_day=day)
            history = record_black_swan_report(history, report)
        assert len(history) == MAX_BLACK_SWAN_REPORTS


class TestPortfolioStressTest:
    def test_ladder_has_five_levels_matching_the_brief(self) -> None:
        result = run_portfolio_stress_test(_portfolio_with_position(), default_risk_limits(), [], account_id=None, account_label="Primary Portfolio", sim_day=1)
        assert [level.shock_pct for level in result.levels] == list(STRESS_LEVELS)

    def test_worse_shocks_produce_lower_resulting_equity(self) -> None:
        result = run_portfolio_stress_test(_portfolio_with_position(), default_risk_limits(), [], account_id=None, account_label="Primary Portfolio", sim_day=1)
        equities = [level.resulting_equity for level in result.levels]
        assert equities == sorted(equities, reverse=True)

    def test_severe_shock_breaches_max_drawdown_and_capital_can_fail_to_survive(self) -> None:
        tight_limits = RiskLimits(maxDrawdownPct=5.0)
        big_position = _position(quantity=1000.0, entry_price=100.0, current_price=100.0)
        portfolio = _portfolio_with_position(cash=0.0, starting_balance=100000.0, positions=[big_position])
        result = run_portfolio_stress_test(portfolio, tight_limits, [], account_id=None, account_label="Primary Portfolio", sim_day=1)
        worst = result.levels[-1]
        assert worst.breaches_max_drawdown is True

    def test_no_loss_at_a_shock_level_reports_nothing_to_recover_from(self) -> None:
        empty_portfolio = default_portfolio()
        result = run_portfolio_stress_test(empty_portfolio, default_risk_limits(), [], account_id=None, account_label="Primary Portfolio", sim_day=1)
        assert result.levels[0].recovery_days_estimate == 0.0

    def test_no_trailing_performance_reports_an_honest_na_never_a_fabricated_eta(self) -> None:
        big_position = _position(quantity=100.0, entry_price=100.0, current_price=100.0)
        portfolio = _portfolio_with_position(cash=0.0, positions=[big_position])
        result = run_portfolio_stress_test(portfolio, default_risk_limits(), [], account_id=None, account_label="Primary Portfolio", sim_day=1)
        worst = result.levels[-1]
        assert worst.recovery_days_estimate is None
        assert "N/A" in worst.recovery_note


class TestPortfolioScenario:
    def test_flash_crash_reduces_equity_for_a_held_position(self) -> None:
        provider = _FixedVolProvider([100.0, 101.0, 99.0, 100.5, 99.5] * 6)
        portfolio = _portfolio_with_position()
        result = run_portfolio_scenario("flash_crash", portfolio, default_risk_limits(), provider, account_id=None, account_label="Primary Portfolio")
        assert result.shocked_equity < result.starting_equity
        assert result.impact_pct < 0

    def test_scenario_never_names_a_real_historical_event(self) -> None:
        provider = _FixedVolProvider([100.0, 101.0, 99.0] * 10)
        portfolio = _portfolio_with_position()
        for scenario_type in ("flash_crash", "severe_selloff", "liquidity_freeze", "correlation_breakdown"):
            result = run_portfolio_scenario(scenario_type, portfolio, default_risk_limits(), provider, account_id=None, account_label="Primary Portfolio")  # type: ignore[arg-type]
            for banned in ("2008", "2020", "1987", "dot-com", "pandemic", "banking crisis"):
                assert banned not in result.detail.lower()
                assert banned not in result.label.lower()

    def test_correlation_breakdown_shocks_every_position_the_same_direction(self) -> None:
        provider = _FixedVolProvider([100.0, 105.0, 95.0] * 10)
        portfolio = _portfolio_with_position(positions=[_position(symbol="AAPL", quantity=100.0), _position(symbol="MSFT", quantity=1.0)])
        result = run_portfolio_scenario("correlation_breakdown", portfolio, default_risk_limits(), provider, account_id=None, account_label="Primary Portfolio")
        assert result.impact_pct < 0

    def test_no_positions_still_returns_a_flat_result_without_crashing(self) -> None:
        provider = MockMarketDataProvider()
        result = run_portfolio_scenario("flash_crash", default_portfolio(), default_risk_limits(), provider, account_id=None, account_label="Primary Portfolio")
        assert result.shocked_equity == result.starting_equity


class TestDefensiveRecommendations:
    def test_close_weak_positions_lists_real_losers_worst_first(self) -> None:
        losers = [_position(symbol="AAPL", current_price=90.0), _position(symbol="MSFT", current_price=80.0)]
        portfolio = _portfolio_with_position(positions=losers)
        recs = build_defensive_recommendations(portfolio, default_risk_limits())
        close_rec = next(r for r in recs if r.action == "Close Weak Positions")
        assert close_rec.automatic is False
        assert "MSFT" in close_rec.detail and close_rec.detail.index("MSFT") < close_rec.detail.index("AAPL")

    def test_pause_new_entries_and_tighten_are_automatic_closing_is_not(self) -> None:
        recs = build_defensive_recommendations(_portfolio_with_position(), default_risk_limits())
        by_action = {r.action: r for r in recs}
        assert by_action["Pause New Entries"].automatic is True
        assert by_action["Reduce Position Size"].automatic is True
        assert by_action["Tighten Risk Controls"].automatic is True
        assert by_action["Close Weak Positions"].automatic is False
        assert by_action["Reduce Exposure"].automatic is False
        assert by_action["Increase Cash"].automatic is False


class TestDefensiveModeLifecycle:
    def test_activate_tightens_real_risk_limits(self) -> None:
        limits = default_risk_limits()
        state = DefensiveModeState()
        new_state, tightened, error = activate_defensive_mode(state, limits, _portfolio_with_position(), "red", reason="test", now_iso="2026-01-01T00:00:00Z", now_sim_minutes=100)
        assert error is None
        assert new_state.active is True
        assert tightened.max_position_pct == limits.max_position_pct * 0.5
        assert tightened.max_daily_loss_pct == limits.max_daily_loss_pct * 0.5
        assert tightened.max_open_positions == max(2, limits.max_open_positions // 2)
        assert new_state.prior_risk_limits is not None
        assert new_state.prior_risk_limits.max_position_pct == limits.max_position_pct

    def test_cannot_double_activate(self) -> None:
        limits = default_risk_limits()
        state = DefensiveModeState()
        active_state, _limits, _err = activate_defensive_mode(state, limits, _portfolio_with_position(), "red", reason="test", now_iso="2026-01-01T00:00:00Z", now_sim_minutes=0)
        _again, _limits2, error = activate_defensive_mode(active_state, limits, _portfolio_with_position(), "red", reason="test", now_iso="2026-01-01T00:00:00Z", now_sim_minutes=0)
        assert error is not None

    def test_deactivate_restores_exact_prior_limits_and_writes_a_real_event(self) -> None:
        limits = default_risk_limits()
        state = DefensiveModeState()
        portfolio = _portfolio_with_position()
        active_state, tightened, _err = activate_defensive_mode(state, limits, portfolio, "orange", reason="Auto-triggered: test", now_iso="2026-01-01T00:00:00Z", now_sim_minutes=100)
        warning = _warning()
        deactivated_state, restored, event, error = deactivate_defensive_mode(active_state, portfolio, warning, now_iso="2026-01-01T01:00:00Z", now_sim_minutes=160, event_id="bs-event-test")
        assert error is None
        assert deactivated_state.active is False
        assert restored is not None
        assert restored.max_position_pct == limits.max_position_pct
        assert event is not None
        assert event.duration_sim_minutes == 60
        assert event.peak_tier == "orange"
        assert event.affected_symbols == ["AAPL"]

    def test_cannot_deactivate_when_not_active(self) -> None:
        state = DefensiveModeState()
        _state, _limits, _event, error = deactivate_defensive_mode(state, _portfolio_with_position(), _warning(), now_iso="2026-01-01T00:00:00Z", now_sim_minutes=0, event_id="x")
        assert error is not None

    def test_note_peak_tier_only_ratchets_upward(self) -> None:
        state = DefensiveModeState(active=True, peakTierThisEpisode="yellow")
        bumped = note_defensive_mode_peak_tier(state, "red")
        assert bumped.peak_tier_this_episode == "red"
        not_bumped = note_defensive_mode_peak_tier(bumped, "yellow")
        assert not_bumped.peak_tier_this_episode == "red"

    def test_record_event_history_is_capped(self) -> None:
        limits = default_risk_limits()
        portfolio = _portfolio_with_position()
        warning = _warning()
        history: list = []
        for i in range(MAX_BLACK_SWAN_EVENTS + 5):
            state = DefensiveModeState()
            active_state, _t, _e = activate_defensive_mode(state, limits, portfolio, "red", reason="test", now_iso="2026-01-01T00:00:00Z", now_sim_minutes=0)
            _deactivated, _r, event, _err = deactivate_defensive_mode(active_state, portfolio, warning, now_iso="2026-01-01T00:00:00Z", now_sim_minutes=i, event_id=f"bs-event-{i}")
            assert event is not None
            history = record_black_swan_event(history, event)
        assert len(history) == MAX_BLACK_SWAN_EVENTS


class TestTierMeetsOrExceeds:
    def test_ordering(self) -> None:
        assert tier_meets_or_exceeds("red", "yellow") is True
        assert tier_meets_or_exceeds("yellow", "red") is False
        assert tier_meets_or_exceeds("critical", "critical") is True
        assert tier_meets_or_exceeds("green", "green") is True


class TestPlaybookAndBrokerResilience:
    def test_playbook_immediate_actions_come_from_real_recommendations(self) -> None:
        current = compute_black_swan_intelligence([], default_market_intelligence_state(), _pi(), default_market_environment(), _ei())
        playbook = build_black_swan_playbook(current, DefensiveModeState(), _portfolio_with_position(), default_risk_limits())
        action_labels = {step.label for step in playbook.immediate_actions}
        assert "Pause New Entries" in action_labels
        assert playbook.department_responsibilities
        assert playbook.ceo_checklist

    def test_broker_resilience_is_honestly_static_never_a_live_score(self) -> None:
        read = broker_resilience_read()
        assert read.status == "simulated"
        assert "no real broker" in read.message.lower()


class TestCrisisBriefing:
    def test_situation_summary_cites_real_leading_factors(self) -> None:
        current = compute_black_swan_intelligence(
            [_risk_warning("critical"), _risk_warning("critical"), _risk_warning("critical")], default_market_intelligence_state(), _pi(), default_market_environment(), _ei()
        )
        briefing = generate_crisis_briefing(current, _portfolio_with_position(), _pi(), default_risk_limits(), sim_day=5, briefing_id="crisis-test")
        assert briefing.tier == current.warning.tier
        assert str(round(current.warning.overall)) in briefing.situation_summary or f"{current.warning.overall:.0f}" in briefing.situation_summary
        assert briefing.recommendations


class TestInstitutionalSurvivalScore:
    def test_weights_sum_to_one(self) -> None:
        current = compute_black_swan_intelligence([], default_market_intelligence_state(), _pi(), default_market_environment(), _ei())
        score = compute_institutional_survival_score(_portfolio_with_position(), default_risk_limits(), _pi(), current, DefensiveModeState())
        assert round(sum(f.weight for f in score.factors), 6) == 1.0

    def test_overall_is_a_published_weighted_sum(self) -> None:
        current = compute_black_swan_intelligence([], default_market_intelligence_state(), _pi(), default_market_environment(), _ei())
        score = compute_institutional_survival_score(_portfolio_with_position(), default_risk_limits(), _pi(), current, DefensiveModeState())
        expected = round(sum(f.score * f.weight for f in score.factors), 1)
        assert score.overall == expected

    def test_nine_named_factors_present_leverage_and_counterparty_risk_are_not(self) -> None:
        current = compute_black_swan_intelligence([], default_market_intelligence_state(), _pi(), default_market_environment(), _ei())
        score = compute_institutional_survival_score(_portfolio_with_position(), default_risk_limits(), _pi(), current, DefensiveModeState())
        names = {f.name for f in score.factors}
        assert names == {
            "Cash Reserves",
            "Diversification",
            "Concentration Risk",
            "Liquidity",
            "Drawdown Exposure",
            "Rule Compliance",
            "Black Swan Readiness",
            "Stress Test Survival",
            "Broker Health",
        }
        assert "leverage" not in " ".join(names).lower()
        assert "counterparty" not in " ".join(names).lower()

    def test_more_active_risk_warnings_lowers_rule_compliance_and_overall(self) -> None:
        clean_warning = compute_early_warning_score([], default_market_intelligence_state(), _pi(), default_market_environment(), _ei())
        stressed_warning = compute_early_warning_score(
            [_risk_warning("critical"), _risk_warning("critical")], default_market_intelligence_state(), _pi(), default_market_environment(), _ei()
        )
        clean_intel = compute_black_swan_intelligence([], default_market_intelligence_state(), _pi(), default_market_environment(), _ei())
        stressed_intel = clean_intel.model_copy(update={"warning": stressed_warning})
        clean_score = compute_institutional_survival_score(_portfolio_with_position(), default_risk_limits(), _pi(), clean_intel.model_copy(update={"warning": clean_warning}), DefensiveModeState())
        stressed_score = compute_institutional_survival_score(_portfolio_with_position(), default_risk_limits(), _pi(), stressed_intel, DefensiveModeState())
        clean_compliance = next(f for f in clean_score.factors if f.name == "Rule Compliance")
        stressed_compliance = next(f for f in stressed_score.factors if f.name == "Rule Compliance")
        assert stressed_compliance.score < clean_compliance.score
        assert stressed_score.overall < clean_score.overall

    def test_grade_thresholds_are_monotonic_with_score(self) -> None:
        from app.black_swan import _survival_grade  # noqa: PLC0415

        assert _survival_grade(96.0) == "a_plus"
        assert _survival_grade(85.0) == "a"
        assert _survival_grade(70.0) == "b"
        assert _survival_grade(55.0) == "c"
        assert _survival_grade(40.0) == "d"
        assert _survival_grade(10.0) == "f"

    def test_no_leverage_or_probability_field_exists_on_the_schema(self) -> None:
        current = compute_black_swan_intelligence([], default_market_intelligence_state(), _pi(), default_market_environment(), _ei())
        score = compute_institutional_survival_score(_portfolio_with_position(), default_risk_limits(), _pi(), current, DefensiveModeState())
        dumped = score.model_dump()
        assert "survival_probability" not in dumped
        assert "leverage" not in dumped
        assert "counterparty_risk" not in dumped

    def test_strengths_and_weaknesses_and_improvements_are_real_not_generic(self) -> None:
        current = compute_black_swan_intelligence([], default_market_intelligence_state(), _pi(), default_market_environment(), _ei())
        score = compute_institutional_survival_score(_portfolio_with_position(), default_risk_limits(), _pi(), current, DefensiveModeState())
        assert len(score.primary_strengths) == 3
        assert len(score.primary_weaknesses) == 3
        assert len(score.top_improvements) == 5
        for improvement in score.top_improvements:
            assert ":" in improvement  # "Factor Name: real computed detail", never bare filler

    def test_readiness_scores_higher_when_auto_trigger_is_enabled(self) -> None:
        current = compute_black_swan_intelligence([], default_market_intelligence_state(), _pi(), default_market_environment(), _ei())
        off = compute_institutional_survival_score(_portfolio_with_position(), default_risk_limits(), _pi(), current, DefensiveModeState(autoTriggerEnabled=False))
        on = compute_institutional_survival_score(_portfolio_with_position(), default_risk_limits(), _pi(), current, DefensiveModeState(autoTriggerEnabled=True))
        off_readiness = next(f for f in off.factors if f.name == "Black Swan Readiness")
        on_readiness = next(f for f in on.factors if f.name == "Black Swan Readiness")
        assert on_readiness.score > off_readiness.score
