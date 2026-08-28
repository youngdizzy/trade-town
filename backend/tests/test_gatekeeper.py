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
    MIN_CONFIDENCE,
    _account_halt_check,
    _agreement_check,
    _behavioral_check,
    _confidence_check,
    _correlation_check,
    _debate_check,
    _exposure_check,
    _failure_boundary_check,
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
    PaperTrade,
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


def _loss_trade(*, symbol: str = "NEXA", quantity: float = 10.0, entry_price: float = 100.0, closed_sim_minutes: int = 0, opened_sim_minutes: int = 0) -> PaperTrade:
    """A real closed losing trade — app/behavioral_risk.py's own real
    signal input (never a fabricated behavioral read)."""
    return PaperTrade(
        id=f"trade-{symbol}-{closed_sim_minutes}",
        symbol=symbol,
        side="buy",
        quantity=quantity,
        entryPrice=entry_price,
        exitPrice=entry_price * 0.9,
        pnl=-100.0,
        pnlPct=-10.0,
        durationMinutes=closed_sim_minutes - opened_sim_minutes,
        confidence=80.0,
        reason="test loss",
        marketConditions="test conditions",
        openedAt=_now_iso(),
        closedAt=_now_iso(),
        openedSimMinutes=opened_sim_minutes,
        closedSimMinutes=closed_sim_minutes,
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
    # "more than max_correlated_positions already share this category"
    # with real category data is multiple positions on the same symbol.
    def test_passes_within_the_correlated_limit(self) -> None:
        proposal = _proposal(symbol="AAPL")
        portfolio = default_portfolio().model_copy(update={"positions": [_position("AAPL", "pos-1"), _position("AAPL", "pos-2")]})
        risk_limits = RiskLimits()
        assert risk_limits.max_correlated_positions == 2
        assert _correlation_check(proposal, portfolio, risk_limits).passed is True

    def test_fails_beyond_the_correlated_limit(self) -> None:
        proposal = _proposal(symbol="AAPL")
        portfolio = default_portfolio().model_copy(
            update={"positions": [_position("AAPL", "pos-1"), _position("AAPL", "pos-2"), _position("AAPL", "pos-3")]}
        )
        assert _correlation_check(proposal, portfolio, RiskLimits()).passed is False

    def test_passes_when_proposal_symbol_has_no_known_category(self) -> None:
        proposal = _proposal(symbol="UNKNOWNSYM")
        portfolio = default_portfolio().model_copy(
            update={"positions": [_position("AAPL", "pos-1"), _position("AAPL", "pos-2"), _position("AAPL", "pos-3")]}
        )
        assert _correlation_check(proposal, portfolio, RiskLimits()).passed is True

    def test_a_ceo_configured_higher_limit_widens_what_passes(self) -> None:
        # CEO directive "Portfolio Construction, Capital Allocation &
        # Execution Realism," Phase 4 — the promoted, real
        # risk_limits.max_correlated_positions actually changes this
        # check's real behavior, proving it's no longer a hardcoded
        # constant.
        proposal = _proposal(symbol="AAPL")
        portfolio = default_portfolio().model_copy(
            update={"positions": [_position("AAPL", "pos-1"), _position("AAPL", "pos-2"), _position("AAPL", "pos-3")]}
        )
        assert _correlation_check(proposal, portfolio, RiskLimits(maxCorrelatedPositions=5)).passed is True


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

    def test_fails_on_a_portfolio_wide_critical_warning_regardless_of_symbol(self) -> None:
        """Live end-to-end QA pass (2026-08-26) — before this fix, this
        check could never fail against real production data: Guardian's
        standing monitor (app/risk_engine.py's monitor_portfolio) tags
        its one critical warning symbol="PORTFOLIO", which never equals
        a real proposal.symbol. A real critical drawdown breach must
        still block a trade on any symbol."""
        proposal = _proposal(symbol="NEXA")
        warning = RiskWarning(id="w1", symbol="PORTFOLIO", severity="critical", message="Portfolio drawdown breach.", createdAt=_now_iso())
        assert _risk_warning_check(proposal, [warning]).passed is False


class TestBehavioralCheck:
    """app/behavioral_risk.py's real revenge-trading signals, wired as the
    Gatekeeper's tenth check. The CEO's own review required this
    corroboration rule proven directly: "a legitimate setup immediately
    following a loss must remain possible" — timing alone must never
    fail this check, only timing plus a real corroborating signal
    (same-instrument or loss-driven size increase)."""

    def test_case_a_true_revenge_behavior_fails(self) -> None:
        proposal = _proposal(symbol="NEXA", confidence_score=90.0)
        loss = _loss_trade(symbol="NEXA", quantity=10.0, entry_price=100.0, closed_sim_minutes=100)
        check = _behavioral_check(proposal, [loss], now_sim_minutes=110, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert check.passed is False

    def test_case_b_legitimate_follow_up_never_fails(self) -> None:
        """Different instrument, normal size, even though rapid."""
        proposal = _proposal(symbol="DIFFERENT", confidence_score=90.0)
        loss = _loss_trade(symbol="NEXA", quantity=10.0, entry_price=100.0, closed_sim_minutes=100)
        check = _behavioral_check(proposal, [loss], now_sim_minutes=110, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert check.passed is True

    def test_enough_time_passed_never_fails(self) -> None:
        proposal = _proposal(symbol="NEXA", confidence_score=90.0)
        loss = _loss_trade(symbol="NEXA", quantity=10.0, entry_price=100.0, closed_sim_minutes=0)
        check = _behavioral_check(proposal, [loss], now_sim_minutes=60, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert check.passed is True

    def test_no_previous_trade_never_fails(self) -> None:
        proposal = _proposal(symbol="NEXA", confidence_score=90.0)
        check = _behavioral_check(proposal, [], now_sim_minutes=0, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert check.passed is True

    def test_previous_win_never_fails(self) -> None:
        proposal = _proposal(symbol="NEXA", confidence_score=90.0)
        win = _loss_trade(symbol="NEXA", closed_sim_minutes=0).model_copy(update={"pnl": 100.0})
        check = _behavioral_check(proposal, [win], now_sim_minutes=10, cooldown_minutes=60, size_increase_threshold_pct=50.0)
        assert check.passed is True

    def test_a_triggered_read_fails_the_whole_gatekeeper_verdict(self) -> None:
        proposal = _proposal(symbol="NEXA", confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        loss = _loss_trade(symbol="NEXA", closed_sim_minutes=100)
        portfolio = default_portfolio().model_copy(update={"trade_history": [loss]})
        verdict = evaluate_gatekeeper(proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state(), now_sim_minutes=110)
        assert verdict.approved is False
        assert any(c.id == "behavioral" and not c.passed for c in verdict.checks)
        # Every other real check still ran and passed independently —
        # a triggered behavioral read fails only its own check.
        assert all(c.passed for c in verdict.checks if c.id != "behavioral")


class TestFailureBoundaryCheck:
    """CEO Company Health + Live Market Realism directive, Feature 23 —
    the Gatekeeper's eleventh check. Reuses app/portfolio.py's own
    real max(0, max_drawdown_pct - lifetime_drawdown_pct) formula
    (Piece 10b), read before the trade instead of after."""

    def test_passes_with_full_room_remaining(self) -> None:
        check = _failure_boundary_check(default_portfolio(), RiskLimits())
        assert check.passed is True

    def test_passes_when_meaningful_room_remains_despite_a_real_drawdown(self) -> None:
        portfolio = default_portfolio().model_copy(update={"total_pnl_pct": -5.0})
        # 20% ceiling - 5% real drawdown = 15% remaining, well above the 2% default risk-per-trade.
        check = _failure_boundary_check(portfolio, RiskLimits())
        assert check.passed is True

    def test_fails_when_remaining_room_is_smaller_than_this_trades_own_risk(self) -> None:
        portfolio = default_portfolio().model_copy(update={"total_pnl_pct": -19.0})
        # 20% ceiling - 19% real drawdown = 1% remaining, below the 2% default risk-per-trade.
        check = _failure_boundary_check(portfolio, RiskLimits())
        assert check.passed is False

    def test_fails_once_the_ceiling_is_already_breached(self) -> None:
        portfolio = default_portfolio().model_copy(update={"total_pnl_pct": -25.0})
        check = _failure_boundary_check(portfolio, RiskLimits())
        assert check.passed is False
        assert "0.00%" in check.detail

    def test_a_smaller_risk_per_trade_can_still_pass_near_the_ceiling(self) -> None:
        portfolio = default_portfolio().model_copy(update={"total_pnl_pct": -19.5})
        # 20% ceiling - 19.5% real drawdown = 0.5% remaining.
        limits = RiskLimits(riskPerTradePct=0.25)
        check = _failure_boundary_check(portfolio, limits)
        assert check.passed is True

    def test_a_triggered_read_fails_only_its_own_check(self) -> None:
        proposal = _proposal(symbol="NEXA", confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio().model_copy(update={"total_pnl_pct": -25.0})
        verdict = evaluate_gatekeeper(proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state(), now_sim_minutes=0)
        assert verdict.approved is False
        assert any(c.id == "failure_boundary" and not c.passed for c in verdict.checks)
        assert all(c.passed for c in verdict.checks if c.id != "failure_boundary")


class TestAccountHaltCheck:
    """Live end-to-end QA pass (2026-08-26), 12th check — re-runs
    app/risk_engine.py's evaluate_sentinel_risk() fresh at resolution
    time, since every other check here trusts a signal frozen at
    proposal-creation time (the risk analyst's own vote), and a
    proposal can sit pending long enough for the account's real
    daily/weekly/monthly loss halt or lifetime drawdown ceiling to be
    crossed by an unrelated trade in the meantime."""

    def test_vacuously_passes_when_quantity_price_or_sim_day_is_missing(self) -> None:
        proposal = _proposal(symbol="NEXA")
        check = _account_halt_check(proposal, default_portfolio(), RiskLimits(), None, None, None)
        assert check.passed is True

    def test_passes_when_no_halt_condition_is_active(self) -> None:
        proposal = _proposal(symbol="NEXA")
        check = _account_halt_check(proposal, default_portfolio(), RiskLimits(), 10.0, 100.0, 0)
        assert check.passed is True

    def test_fails_when_the_lifetime_drawdown_ceiling_is_already_breached(self) -> None:
        """CEO directive "Portfolio Risk Engine + Firm-Wide Risk
        Governance" — evaluate_sentinel_risk()'s drawdown check now
        measures a REAL peak-to-trough drawdown (app/analytics.py::
        max_drawdown_pct(), folding in live equity), not the bare
        `total_pnl_pct` field, so this needs a real held position with a
        real unrealized loss rather than a fabricated summary override.
        Built as an OPEN position specifically (not a closed trade) so
        this exercises the fix's other real half — a large unrealized
        loss that's never been realized still trips this gate — and so
        it stays isolated from sim_day=0's daily/weekly/monthly loss
        checks above it (which only ever look at CLOSED trade_history)."""
        proposal = _proposal(symbol="NEXA")
        losing_position = PaperPosition(
            id="pos-losing",
            symbol="OTHER",
            side="buy",
            quantity=1_000.0,
            entryPrice=50.0,
            currentPrice=25.0,
            unrealizedPnl=-25_000.0,
            unrealizedPnlPct=-50.0,
            openedBy="atlas",
            confidence=80.0,
            openedAt=_now_iso(),
            openedSimMinutes=0,
        )
        portfolio = default_portfolio().model_copy(update={"cash_balance": 50_000.0, "positions": [losing_position]})
        check = _account_halt_check(proposal, portfolio, RiskLimits(), 10.0, 100.0, 0)
        assert check.passed is False
        assert "drawdown" in check.detail.lower()

    def test_a_triggered_read_fails_only_its_own_check_in_the_full_verdict(self) -> None:
        proposal = _proposal(symbol="NEXA", confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        losing_position = PaperPosition(
            id="pos-losing",
            symbol="OTHER",
            side="buy",
            quantity=1_000.0,
            entryPrice=50.0,
            currentPrice=25.0,
            unrealizedPnl=-25_000.0,
            unrealizedPnlPct=-50.0,
            openedBy="atlas",
            confidence=80.0,
            openedAt=_now_iso(),
            openedSimMinutes=0,
        )
        portfolio = default_portfolio().model_copy(update={"cash_balance": 50_000.0, "positions": [losing_position]})
        verdict = evaluate_gatekeeper(
            proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state(), now_sim_minutes=0, quantity=10.0, price=100.0, sim_day=0
        )
        assert verdict.approved is False
        assert any(c.id == "account_halt" and not c.passed for c in verdict.checks)


class TestEvaluateGatekeeper:
    def test_approves_when_every_check_passes(self) -> None:
        proposal = _proposal(confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio()
        verdict = evaluate_gatekeeper(proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state(), now_sim_minutes=0)
        assert verdict.approved is True
        # Design Bible Chapter 70 Part 3 addendum — 9th check: the
        # Weighted Executive Decision Engine, vacuously passing here
        # since no weighted_recommendation was supplied (see
        # TestWeightedExecutiveCheck below for the real behavior).
        # 10th check: the Behavioral Circuit Breaker, vacuously passing
        # here since this portfolio has no trade history at all.
        # 11th check: Failure Boundary Distance — a fresh portfolio has
        # 0% lifetime drawdown, so the full 20% default ceiling is
        # remaining room, well above the 2% default risk-per-trade.
        # 12th check: Account Risk Halt (live) — vacuously passing here
        # since no quantity/price/sim_day was supplied (see
        # TestAccountHaltCheck below for the real behavior).
        assert len(verdict.checks) == 12
        assert all(c.passed for c in verdict.checks)
        assert "APPROVED" in verdict.summary
        # CEO directive "Professional Quant Firm Phase 41-45," Critical Task #0's No-Trade
        # Reason Taxonomy — every real check carries its own real "gatekeeper_{id}" code,
        # regardless of pass/fail, so a rejection is always taxonomy-classifiable.
        assert {c.code for c in verdict.checks} == {f"gatekeeper_{c.id}" for c in verdict.checks}
        assert None not in {c.code for c in verdict.checks}

    def test_rejects_and_names_the_failed_check_when_confidence_is_too_low(self) -> None:
        proposal = _proposal(confidence_score=10.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio()
        verdict = evaluate_gatekeeper(proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state(), now_sim_minutes=0)
        assert verdict.approved is False
        assert "REJECTED" in verdict.summary
        assert "Decision Confidence" in verdict.summary
        confidence_check = next(c for c in verdict.checks if c.id == "confidence")
        assert confidence_check.passed is False

    def test_rejects_when_a_critical_risk_warning_is_active(self) -> None:
        proposal = _proposal(symbol="NEXA", confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio()
        warning = RiskWarning(id="w1", symbol="NEXA", severity="critical", message="Too concentrated.", createdAt=_now_iso())
        verdict = evaluate_gatekeeper(proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [warning], default_market_intelligence_state(), now_sim_minutes=0)
        assert verdict.approved is False
        assert any(c.id == "risk_warning" and not c.passed for c in verdict.checks)

    def test_rejects_when_market_intelligence_reads_avoid_trading(self) -> None:
        proposal = _proposal(confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio()
        poor_market = default_market_intelligence_state().model_copy(
            update={"quality": default_market_intelligence_state().quality.model_copy(update={"tier": "avoid_trading", "score": 10.0})}
        )
        verdict = evaluate_gatekeeper(proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], poor_market, now_sim_minutes=0)
        assert verdict.approved is False
        assert any(c.id == "market_intelligence" and not c.passed for c in verdict.checks)

    def test_rejects_when_the_behavioral_circuit_breaker_triggers_even_if_every_other_check_passes(self) -> None:
        proposal = _proposal(confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}), symbol="NEXA")
        loss = _loss_trade(symbol="NEXA", closed_sim_minutes=100)
        portfolio = default_portfolio().model_copy(update={"trade_history": [loss]})
        verdict = evaluate_gatekeeper(proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state(), now_sim_minutes=110)
        assert verdict.approved is False
        behavioral_check = next(c for c in verdict.checks if c.id == "behavioral")
        assert behavioral_check.passed is False
        assert "Behavioral Circuit Breaker" in verdict.summary

    def test_a_clear_or_warning_behavioral_read_never_blocks(self) -> None:
        proposal = _proposal(confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}), symbol="DIFFERENT")
        loss = _loss_trade(symbol="NEXA", closed_sim_minutes=100)
        portfolio = default_portfolio().model_copy(update={"trade_history": [loss]})
        # Different instrument, normal size, rapid timing — corroboration
        # rule keeps this at "warning" at most, never "triggered".
        verdict = evaluate_gatekeeper(proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state(), now_sim_minutes=110)
        assert verdict.approved is True
        behavioral_check = next(c for c in verdict.checks if c.id == "behavioral")
        assert behavioral_check.passed is True


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
        verdict = evaluate_gatekeeper(proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state(), now_sim_minutes=0)
        check = next(c for c in verdict.checks if c.id == "weighted_executive")
        assert check.passed is True
        assert "not evaluated" in check.detail

    def test_passes_when_weighted_action_favors_trading(self) -> None:
        proposal = _proposal(confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio()
        verdict = evaluate_gatekeeper(
            proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state(), now_sim_minutes=0, weighted_recommendation=_weighted_recommendation("trade_normally")
        )
        check = next(c for c in verdict.checks if c.id == "weighted_executive")
        assert check.passed is True
        assert verdict.approved is True

    def test_rejects_the_whole_trade_when_weighted_action_advises_caution(self) -> None:
        proposal = _proposal(confidence_score=90.0, votes=_six_votes({r: "buy" for r in ROLE_TO_AGENT}))
        portfolio = default_portfolio()
        verdict = evaluate_gatekeeper(
            proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state(), now_sim_minutes=0, weighted_recommendation=_weighted_recommendation("pause_trading")
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
            proposal, "buy", _debate("buy"), portfolio, RiskLimits(), [], default_market_intelligence_state(), now_sim_minutes=0, weighted_recommendation=_weighted_recommendation("trade_normally")
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
