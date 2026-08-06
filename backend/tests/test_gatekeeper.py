"""Covers app/gatekeeper.py — v0.7 Feature 20, the Trade Gatekeeper. Every
check reads real state already computed elsewhere (analyst votes, the
Decision Confidence Engine score, an AI Debate outcome, the portfolio's
real open positions, Sentinel/Guardian's real risk warnings); nothing
here is a fabricated pass/fail. grade_gatekeeper_rejections must only
ever resolve a rejection from the symbol's own real subsequent watchlist
price, never a placed order's P&L (a rejected trade never executes).
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.gatekeeper import (
    GATEKEEPER_EVAL_WINDOW_MINUTES,
    MAX_CORRELATED_POSITIONS,
    MIN_CONFIDENCE,
    _agreement_check,
    _confidence_check,
    _correlation_check,
    _debate_check,
    _exposure_check,
    _risk_manager_check,
    _risk_warning_check,
    evaluate_gatekeeper,
    grade_gatekeeper_rejections,
)
from app.market_intelligence import default_market_intelligence_state
from app.portfolio import default_portfolio
from app.schemas import (
    AnalystVote,
    ConfidenceFactor,
    Debate,
    DebateTurn,
    DecisionConfidence,
    GatekeeperRejection,
    PaperPosition,
    RiskLimits,
    RiskWarning,
    TradeProposal,
    WatchlistEntry,
    WeightedExecutiveRecommendation,
)

ROLE_TO_AGENT = {"technical": "echo", "news": "scout", "macro": "nova", "risk": "sentinel", "sentiment": "pulse", "execution": "atlas"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _vote(role: str, choice: str, reasoning: str = "test reasoning") -> AnalystVote:
    return AnalystVote(role=role, agentId=ROLE_TO_AGENT[role], choice=choice, reasoning=reasoning, evidence=["real evidence line"])  # type: ignore[arg-type]


def _six_votes(choices: dict[str, str]) -> list[AnalystVote]:
    return [_vote(role, choices.get(role, "wait")) for role in ROLE_TO_AGENT]


def _proposal(*, symbol: str = "NEXA", confidence_score: float = 80.0, votes: list[AnalystVote] | None = None, overall: str = "buy") -> TradeProposal:
    return TradeProposal(
        id=f"proposal-{symbol}",
        symbol=symbol,
        category="stock",
        quantity=10.0,
        price=100.0,
        confidence=90.0,
        analystVotes=votes if votes is not None else _six_votes({r: "buy" for r in ROLE_TO_AGENT}),
        overallRecommendation=overall,  # type: ignore[arg-type]
        researchSummary="test research summary",
        riskSummary="test risk summary",
        confidenceEngine=DecisionConfidence(
            score=confidence_score, tier="strong", summary="test summary", factors=[ConfidenceFactor(name="test", score=confidence_score, weight=1.0, detail="test")]
        ),
        createdAt=_now_iso(),
        createdSimMinutes=0,
    )


def _position(symbol: str, position_id: str | None = None) -> PaperPosition:
    return PaperPosition(
        id=position_id or f"pos-{symbol}",
        symbol=symbol,
        side="buy",
        quantity=1.0,
        entryPrice=100.0,
        currentPrice=100.0,
        unrealizedPnl=0.0,
        unrealizedPnlPct=0.0,
        openedBy="atlas",
        confidence=80.0,
        openedAt=_now_iso(),
        openedSimMinutes=0,
    )


def _debate(final_recommendation: str = "buy") -> Debate:
    return Debate(
        id="debate-1",
        proposalId="proposal-NEXA",
        symbol="NEXA",
        turns=[DebateTurn(agentId="echo", role="technical", stance="opening", respondingTo=None, text="test")],
        finalRecommendation=final_recommendation,  # type: ignore[arg-type]
        finalSummary="test summary",
        createdAt=_now_iso(),
    )


class TestConfidenceCheck:
    def test_passes_at_or_above_threshold(self) -> None:
        proposal = _proposal(confidence_score=MIN_CONFIDENCE)
        assert _confidence_check(proposal).passed is True

    def test_fails_below_threshold(self) -> None:
        proposal = _proposal(confidence_score=MIN_CONFIDENCE - 0.1)
        assert _confidence_check(proposal).passed is False


class TestRiskManagerCheck:
    def test_passes_when_risk_analyst_agrees(self) -> None:
        proposal = _proposal(votes=_six_votes({"risk": "buy"}))
        assert _risk_manager_check(proposal, "buy").passed is True

    def test_fails_when_risk_analyst_dissents(self) -> None:
        proposal = _proposal(votes=_six_votes({"risk": "sell"}))
        assert _risk_manager_check(proposal, "buy").passed is False

    def test_passes_when_no_risk_vote_present(self) -> None:
        votes = [v for v in _six_votes({r: "buy" for r in ROLE_TO_AGENT}) if v.role != "risk"]
        proposal = _proposal(votes=votes)
        assert _risk_manager_check(proposal, "buy").passed is True


class TestAgreementCheck:
    def test_passes_with_majority_agreement(self) -> None:
        proposal = _proposal(votes=_six_votes({"technical": "buy", "news": "buy", "macro": "buy", "risk": "buy", "sentiment": "sell", "execution": "sell"}))
        assert _agreement_check(proposal, "buy").passed is True

    def test_fails_without_majority_agreement(self) -> None:
        proposal = _proposal(votes=_six_votes({"technical": "sell", "news": "sell", "macro": "sell", "risk": "sell", "sentiment": "buy", "execution": "buy"}))
        assert _agreement_check(proposal, "buy").passed is False


class TestDebateCheck:
    def test_passes_when_debate_matches_ceo_choice(self) -> None:
        assert _debate_check(_debate("buy"), "buy").passed is True

    def test_fails_when_debate_contradicts_ceo_choice(self) -> None:
        assert _debate_check(_debate("sell"), "buy").passed is False

    def test_passes_when_no_debate_on_record(self) -> None:
        assert _debate_check(None, "buy").passed is True


class TestExposureCheck:
    def test_passes_under_the_limit(self) -> None:
        portfolio = default_portfolio().model_copy(update={"positions": [_position("AAPL")]})
        assert _exposure_check(portfolio, RiskLimits(maxOpenPositions=8)).passed is True

    def test_fails_at_the_limit(self) -> None:
        portfolio = default_portfolio().model_copy(update={"positions": [_position(f"SYM{i}") for i in range(8)]})
        assert _exposure_check(portfolio, RiskLimits(maxOpenPositions=8)).passed is False


class TestCorrelationCheck:
    # SEED_SYMBOLS (SYMBOL_CATEGORY's real source — see app/watchlist.py)
    # assigns exactly one symbol per category, so the only way to exercise
    # "more than MAX_CORRELATED_POSITIONS already share this category"
    # with real category data is multiple positions on the same symbol.
    def test_passes_within_the_correlated_limit(self) -> None:
        proposal = _proposal(symbol="AAPL")
        portfolio = default_portfolio().model_copy(update={"positions": [_position("AAPL", "pos-1"), _position("AAPL", "pos-2")]})
        assert MAX_CORRELATED_POSITIONS == 2
        assert _correlation_check(proposal, portfolio).passed is True

    def test_fails_beyond_the_correlated_limit(self) -> None:
        proposal = _proposal(symbol="AAPL")
        portfolio = default_portfolio().model_copy(
            update={"positions": [_position("AAPL", "pos-1"), _position("AAPL", "pos-2"), _position("AAPL", "pos-3")]}
        )
        assert _correlation_check(proposal, portfolio).passed is False

    def test_passes_when_proposal_symbol_has_no_known_category(self) -> None:
        proposal = _proposal(symbol="UNKNOWNSYM")
        portfolio = default_portfolio().model_copy(
            update={"positions": [_position("AAPL", "pos-1"), _position("AAPL", "pos-2"), _position("AAPL", "pos-3")]}
        )
        assert _correlation_check(proposal, portfolio).passed is True


class TestRiskWarningCheck:
    def test_passes_with_no_warnings(self) -> None:
        proposal = _proposal(symbol="NEXA")
        assert _risk_warning_check(proposal, []).passed is True

    def test_fails_on_a_critical_warning_for_this_symbol(self) -> None:
        proposal = _proposal(symbol="NEXA")
        warning = RiskWarning(id="w1", symbol="NEXA", severity="critical", message="Too concentrated.", createdAt=_now_iso())
        assert _risk_warning_check(proposal, [warning]).passed is False

    def test_passes_on_a_critical_warning_for_a_different_symbol(self) -> None:
        proposal = _proposal(symbol="NEXA")
        warning = RiskWarning(id="w1", symbol="OTHER", severity="critical", message="Too concentrated.", createdAt=_now_iso())
        assert _risk_warning_check(proposal, [warning]).passed is True

    def test_passes_on_a_non_critical_warning(self) -> None:
        proposal = _proposal(symbol="NEXA")
        warning = RiskWarning(id="w1", symbol="NEXA", severity="warning", message="Elevated exposure.", createdAt=_now_iso())
        assert _risk_warning_check(proposal, [warning]).passed is True


class TestEvaluateGatekeeper:
    def test_approves_when_every_check_passes(self) -> None:
        proposal = _proposal(confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio()
        verdict = evaluate_gatekeeper(proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state())
        assert verdict.approved is True
        # Design Bible Chapter 70 Part 3 addendum — 9th check: the
        # Weighted Executive Decision Engine, vacuously passing here
        # since no weighted_recommendation was supplied (see
        # TestWeightedExecutiveCheck below for the real behavior).
        assert len(verdict.checks) == 9
        assert all(c.passed for c in verdict.checks)
        assert "APPROVED" in verdict.summary

    def test_rejects_and_names_the_failed_check_when_confidence_is_too_low(self) -> None:
        proposal = _proposal(confidence_score=10.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio()
        verdict = evaluate_gatekeeper(proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state())
        assert verdict.approved is False
        assert "REJECTED" in verdict.summary
        assert "Decision Confidence" in verdict.summary
        confidence_check = next(c for c in verdict.checks if c.id == "confidence")
        assert confidence_check.passed is False

    def test_rejects_when_a_critical_risk_warning_is_active(self) -> None:
        proposal = _proposal(symbol="NEXA", confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio()
        warning = RiskWarning(id="w1", symbol="NEXA", severity="critical", message="Too concentrated.", createdAt=_now_iso())
        verdict = evaluate_gatekeeper(proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [warning], default_market_intelligence_state())
        assert verdict.approved is False
        assert any(c.id == "risk_warning" and not c.passed for c in verdict.checks)

    def test_rejects_when_market_intelligence_reads_avoid_trading(self) -> None:
        proposal = _proposal(confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio()
        poor_market = default_market_intelligence_state().model_copy(
            update={"quality": default_market_intelligence_state().quality.model_copy(update={"tier": "avoid_trading", "score": 10.0})}
        )
        verdict = evaluate_gatekeeper(proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], poor_market)
        assert verdict.approved is False
        assert any(c.id == "market_intelligence" and not c.passed for c in verdict.checks)


def _weighted_recommendation(weighted_action: str) -> WeightedExecutiveRecommendation:
    return WeightedExecutiveRecommendation(
        proposalId="proposal-NEXA",
        profile="balanced_institutional",
        marketRegime="sideways",
        departmentInfluences=[],
        rawAction="trade_normally",
        weightedAction=weighted_action,  # type: ignore[arg-type]
        scoreByAction={weighted_action: 100.0},
        agreesWithRaw=weighted_action == "trade_normally",
    )


class TestWeightedExecutiveCheck:
    """Design Bible Chapter 70 Part 3 addendum — the Weighted Executive
    Decision Engine must feed the Trade Gatekeeper while remaining
    advisory only: it can contribute to a rejection like any other real
    check, but it can never approve a trade or bypass any of the other
    eight checks on its own."""

    def test_passes_when_no_recommendation_supplied(self) -> None:
        proposal = _proposal(confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio()
        verdict = evaluate_gatekeeper(proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state())
        check = next(c for c in verdict.checks if c.id == "weighted_executive")
        assert check.passed is True
        assert "not evaluated" in check.detail

    def test_passes_when_weighted_action_favors_trading(self) -> None:
        proposal = _proposal(confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio()
        verdict = evaluate_gatekeeper(
            proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state(), _weighted_recommendation("trade_normally")
        )
        check = next(c for c in verdict.checks if c.id == "weighted_executive")
        assert check.passed is True
        assert verdict.approved is True

    def test_rejects_the_whole_trade_when_weighted_action_advises_caution(self) -> None:
        proposal = _proposal(confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio()
        verdict = evaluate_gatekeeper(
            proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state(), _weighted_recommendation("pause_trading")
        )
        check = next(c for c in verdict.checks if c.id == "weighted_executive")
        assert check.passed is False
        assert verdict.approved is False
        assert "Weighted Executive Recommendation" in verdict.summary

    def test_a_favorable_weighted_recommendation_cannot_rescue_a_failing_confidence_check(self) -> None:
        """WEDE is advisory-only both ways — it can never override the
        other eight real checks, only ever add to them."""
        proposal = _proposal(confidence_score=10.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio()
        verdict = evaluate_gatekeeper(
            proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state(), _weighted_recommendation("trade_normally")
        )
        assert verdict.approved is False
        confidence_check = next(c for c in verdict.checks if c.id == "confidence")
        assert confidence_check.passed is False


class TestGradeGatekeeperRejections:
    def _rejection(self, *, symbol: str = "NEXA", choice: str = "buy", price_at_rejection: float = 100.0, rejected_sim_minutes: int = 0) -> GatekeeperRejection:
        return GatekeeperRejection(
            id="gkreject-1",
            proposalId="proposal-NEXA",
            symbol=symbol,
            ceoChoice=choice,  # type: ignore[arg-type]
            reasons=["Decision Confidence: too low."],
            priceAtRejection=price_at_rejection,
            rejectedSimMinutes=rejected_sim_minutes,
            createdAt=_now_iso(),
        )

    def test_stays_pending_before_the_evaluation_window_elapses(self) -> None:
        rejection = self._rejection()
        watchlist = [WatchlistEntry(symbol="NEXA", name="Nexa Corp", lastPrice=110.0, dailyChangePct=10.0, status="completed", researchProgress=1.0, assignedAgent=None)]
        graded = grade_gatekeeper_rejections([rejection], watchlist, now_sim_minutes=GATEKEEPER_EVAL_WINDOW_MINUTES - 1)
        assert graded[0].outcome == "pending"

    def test_resolves_would_have_won_when_a_blocked_buy_rallied(self) -> None:
        rejection = self._rejection(choice="buy", price_at_rejection=100.0)
        watchlist = [WatchlistEntry(symbol="NEXA", name="Nexa Corp", lastPrice=110.0, dailyChangePct=10.0, status="completed", researchProgress=1.0, assignedAgent=None)]
        graded = grade_gatekeeper_rejections([rejection], watchlist, now_sim_minutes=GATEKEEPER_EVAL_WINDOW_MINUTES)
        assert graded[0].outcome == "would_have_won"
        assert graded[0].resolved_price_change_pct == 10.0
        assert graded[0].resolved_at is not None

    def test_resolves_would_have_lost_when_a_blocked_buy_dropped(self) -> None:
        rejection = self._rejection(choice="buy", price_at_rejection=100.0)
        watchlist = [WatchlistEntry(symbol="NEXA", name="Nexa Corp", lastPrice=90.0, dailyChangePct=-10.0, status="completed", researchProgress=1.0, assignedAgent=None)]
        graded = grade_gatekeeper_rejections([rejection], watchlist, now_sim_minutes=GATEKEEPER_EVAL_WINDOW_MINUTES)
        assert graded[0].outcome == "would_have_lost"

    def test_sell_direction_is_inverted(self) -> None:
        rejection = self._rejection(choice="sell", price_at_rejection=100.0)
        watchlist = [WatchlistEntry(symbol="NEXA", name="Nexa Corp", lastPrice=90.0, dailyChangePct=-10.0, status="completed", researchProgress=1.0, assignedAgent=None)]
        graded = grade_gatekeeper_rejections([rejection], watchlist, now_sim_minutes=GATEKEEPER_EVAL_WINDOW_MINUTES)
        assert graded[0].outcome == "would_have_won"

    def test_stays_pending_when_symbol_no_longer_on_the_watchlist(self) -> None:
        rejection = self._rejection(symbol="DELISTED")
        graded = grade_gatekeeper_rejections([rejection], [], now_sim_minutes=GATEKEEPER_EVAL_WINDOW_MINUTES)
        assert graded[0].outcome == "pending"

    def test_leaves_already_resolved_rejections_untouched(self) -> None:
        rejection = self._rejection().model_copy(update={"outcome": "would_have_lost", "resolved_price_change_pct": -5.0})
        watchlist = [WatchlistEntry(symbol="NEXA", name="Nexa Corp", lastPrice=999.0, dailyChangePct=0.0, status="completed", researchProgress=1.0, assignedAgent=None)]
        graded = grade_gatekeeper_rejections([rejection], watchlist, now_sim_minutes=GATEKEEPER_EVAL_WINDOW_MINUTES * 10)
        assert graded[0].outcome == "would_have_lost"
        assert graded[0].resolved_price_change_pct == -5.0
