"""Covers app/nexus.py's decision-log cap — added for v0.6.2's save-payload
fix. `decisions` was the one list in the whole save schema with no upper
bound (see MAX_DECISIONS' own comment in nexus.py for the full story): it
grew by one ~1.5KB record every time research crossed the trade-candidate
threshold, for as long as the process stayed up, with nothing ever
evicted — which is what silently grew real deployments' save payloads
past nginx's default 1MB limit and caused the reported 413 errors.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.market_intelligence import default_market_intelligence_state
from app.nexus import MAX_DECISIONS, _apply_operating_mode, _generate_trade_proposals, _trim_decisions
from app.nexus import tick as nexus_tick
from app.portfolio import default_portfolio, open_position
from app.schemas import AnalystVote, ConfidenceFactor, DecisionConfidence, ResearchItem, RiskLimits, TimeState, TradeDecision, TradeProposal
from app.state import default_state
from app.trading_restrictions import activate_trading_restriction


def _decision(n: int) -> TradeDecision:
    return TradeDecision(
        id=f"decision-{n}",
        symbol="AAPL",
        outcome="trade",
        votes=[],
        researchSummary="x",
        technicalSummary="x",
        fundamentalSummary="x",
        riskSummary="x",
        supportingAgents=[],
        opposingAgents=[],
        confidence=90.0,
        finalReasoning="x",
        createdAt="2026-01-01T00:00:00+00:00",
    )


def test_trim_decisions_is_a_noop_under_the_cap():
    decisions = [_decision(i) for i in range(MAX_DECISIONS - 1)]
    _trim_decisions(decisions)
    assert len(decisions) == MAX_DECISIONS - 1


def test_trim_decisions_evicts_oldest_first_down_to_the_cap():
    decisions = [_decision(i) for i in range(MAX_DECISIONS + 50)]
    _trim_decisions(decisions)
    assert len(decisions) == MAX_DECISIONS
    # The oldest 50 (ids 0..49) were evicted; the most recent MAX_DECISIONS survive.
    assert decisions[0].id == "decision-50"
    assert decisions[-1].id == f"decision-{MAX_DECISIONS + 49}"


def test_decisions_never_grow_unbounded_across_many_ticks():
    """Simulates the real failure mode: repeated appends across many
    ticks, as nexus.tick() does every sim tick a trade candidate
    resolves, with the same trim call applied after each one."""
    decisions: list[TradeDecision] = []
    for tick in range(MAX_DECISIONS * 3):
        decisions.append(_decision(tick))
        _trim_decisions(decisions)
        assert len(decisions) <= MAX_DECISIONS
    assert len(decisions) == MAX_DECISIONS


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_DEFAULT_FACTORS = [
    ConfidenceFactor(name="agreement", score=90.0, weight=0.30, detail="d"),
    ConfidenceFactor(name="technical", score=80.0, weight=0.20, detail="d"),
    ConfidenceFactor(name="risk", score=85.0, weight=0.20, detail="d"),
    ConfidenceFactor(name="research", score=80.0, weight=0.15, detail="d"),
    ConfidenceFactor(name="sentiment", score=75.0, weight=0.10, detail="d"),
    ConfidenceFactor(name="exposure", score=90.0, weight=0.05, detail="d"),
]


def _proposal() -> TradeProposal:
    # tier="elite"/score=96 with no active risk/confidence concerns is
    # not "significant" per app/executive.py's is_significant_proposal
    # — the same real, otherwise-auto-resolving proposal used in
    # test_executive_intelligence.py's own "trade_normally" case.
    return TradeProposal(
        id="proposal-1",
        symbol="NEXA",
        category="stock",
        quantity=1.0,
        price=100.0,
        confidence=96.0,
        analystVotes=[AnalystVote(role="risk", agentId="sentinel", choice="buy", reasoning="Position sized within limits.", evidence=["Real risk read"])],  # type: ignore[arg-type]
        overallRecommendation="buy",
        researchSummary="Nova's research backs this setup with a completed research item.",
        riskSummary="Within all configured risk limits.",
        confidenceEngine=DecisionConfidence(score=96.0, tier="elite", summary="A well-supported setup.", factors=_DEFAULT_FACTORS),  # type: ignore[arg-type]
        createdAt=_now_iso(),
        createdSimMinutes=0,
    )


class TestApplyOperatingModePauseTrading:
    """v0.7 Design Bible Chapter 66 — AI Consensus Safety. Closes the one
    real, precise gap that chapter's own research found: the
    pause_trading signal (app/executive_intelligence.py's
    compute_executive_recommendation()) already existed, but nothing
    enforced it before this."""

    def _call(self, *, operating_mode: str, market_intelligence):
        return _apply_operating_mode(
            operating_mode,
            [_proposal()],
            [],  # debates
            default_portfolio(),
            RiskLimits(),
            [],  # risk_warnings
            {"NEXA": 100.0},  # prices
            0,  # now_sim_minutes
            [],  # memory
            [],  # decisions
            [],  # ceo_decisions
            [],  # prediction_records
            [],  # gatekeeper_rejections
            [],  # news
            [],  # challenge_reports
            [],  # coach_reports
            [],  # meeting_log
            [],  # decision_vault
            1,  # sim_day
            market_intelligence,
            [],  # war_room_sessions
            "sideways",  # market_environment_regime
            "balanced_institutional",  # active_weight_profile
            {},  # custom_department_weights
        )

    def test_avoid_trading_regime_keeps_an_otherwise_non_significant_proposal_pending_in_assisted_mode(self) -> None:
        avoid_trading_mi = default_market_intelligence_state()
        avoid_trading_mi = avoid_trading_mi.model_copy(update={"quality": avoid_trading_mi.quality.model_copy(update={"tier": "avoid_trading"})})
        remaining, _, _ = self._call(operating_mode="assisted", market_intelligence=avoid_trading_mi)
        assert [p.id for p in remaining] == ["proposal-1"]

    def test_avoid_trading_regime_keeps_the_same_proposal_pending_even_in_executive_mode(self) -> None:
        # The real behavioral change this pass makes: previously Executive
        # Mode auto-resolved everything not flagged "significant" — a
        # real pause_trading recommendation is a safety constraint, not a
        # significance judgment, so it now applies here too.
        avoid_trading_mi = default_market_intelligence_state()
        avoid_trading_mi = avoid_trading_mi.model_copy(update={"quality": avoid_trading_mi.quality.model_copy(update={"tier": "avoid_trading"})})
        remaining, _, _ = self._call(operating_mode="executive", market_intelligence=avoid_trading_mi)
        assert [p.id for p in remaining] == ["proposal-1"]

    def test_a_normal_regime_still_auto_resolves_in_executive_mode(self) -> None:
        # Control: confirms the new gate is regime-specific, not a
        # blanket block on every proposal.
        remaining, _, _ = self._call(operating_mode="executive", market_intelligence=default_market_intelligence_state())
        assert remaining == []


class TestApplyOperatingModeEmergencyStop:
    """Design Bible Chapter 67 (TTOS) Part 3 — a CEO-triggered Emergency
    Stop keeps every pending proposal pending, in both Assisted and
    Executive mode, checked before every other significance/safety
    check (see app/emergency_stop.py)."""

    def _call(self, *, operating_mode: str, emergency_stop_active: bool):
        return _apply_operating_mode(
            operating_mode,
            [_proposal()],
            [],  # debates
            default_portfolio(),
            RiskLimits(),
            [],  # risk_warnings
            {"NEXA": 100.0},  # prices
            0,  # now_sim_minutes
            [],  # memory
            [],  # decisions
            [],  # ceo_decisions
            [],  # prediction_records
            [],  # gatekeeper_rejections
            [],  # news
            [],  # challenge_reports
            [],  # coach_reports
            [],  # meeting_log
            [],  # decision_vault
            1,  # sim_day
            default_market_intelligence_state(),
            [],  # war_room_sessions
            "sideways",  # market_environment_regime
            "balanced_institutional",  # active_weight_profile
            {},  # custom_department_weights
            emergency_stop_active=emergency_stop_active,
        )

    def test_emergency_stop_keeps_an_otherwise_non_significant_proposal_pending_in_assisted_mode(self) -> None:
        remaining, _, _ = self._call(operating_mode="assisted", emergency_stop_active=True)
        assert [p.id for p in remaining] == ["proposal-1"]

    def test_emergency_stop_keeps_the_same_proposal_pending_even_in_executive_mode(self) -> None:
        remaining, _, _ = self._call(operating_mode="executive", emergency_stop_active=True)
        assert [p.id for p in remaining] == ["proposal-1"]

    def test_inactive_emergency_stop_still_auto_resolves_normally_in_executive_mode(self) -> None:
        # Control: confirms the new gate only fires when actually active.
        remaining, _, _ = self._call(operating_mode="executive", emergency_stop_active=False)
        assert remaining == []


class TestApplyOperatingModeRiskContractFailClosed:
    """CEO directive "Risk Contract Enforcement + Dynamic Risk Scaling
    1.0," Non-Negotiable Principle 11/12 — FAIL CLOSED. `risk_contract_
    available=False` (only reachable in production via a corrupted save
    that skips app/state.py's own `_derive_active_risk_contract()`
    guarantee) must defer every buy/sell proposal to manual CEO review
    rather than silently auto-resolving it on un-scaled, un-fail-closed
    risk state — the same real safety-constraint pattern emergency_stop_
    active/force_manual_review above already establish."""

    def _call(self, *, operating_mode: str, risk_contract_available: bool):
        return _apply_operating_mode(
            operating_mode,
            [_proposal()],
            [],  # debates
            default_portfolio(),
            RiskLimits(),
            [],  # risk_warnings
            {"NEXA": 100.0},  # prices
            0,  # now_sim_minutes
            [],  # memory
            [],  # decisions
            [],  # ceo_decisions
            [],  # prediction_records
            [],  # gatekeeper_rejections
            [],  # news
            [],  # challenge_reports
            [],  # coach_reports
            [],  # meeting_log
            [],  # decision_vault
            1,  # sim_day
            default_market_intelligence_state(),
            [],  # war_room_sessions
            "sideways",  # market_environment_regime
            "balanced_institutional",  # active_weight_profile
            {},  # custom_department_weights
            risk_contract_available=risk_contract_available,
        )

    def test_missing_risk_contract_keeps_an_otherwise_non_significant_proposal_pending_in_assisted_mode(self) -> None:
        remaining, _, _ = self._call(operating_mode="assisted", risk_contract_available=False)
        assert [p.id for p in remaining] == ["proposal-1"]

    def test_missing_risk_contract_keeps_the_same_proposal_pending_even_in_executive_mode(self) -> None:
        remaining, _, _ = self._call(operating_mode="executive", risk_contract_available=False)
        assert [p.id for p in remaining] == ["proposal-1"]

    def test_a_real_risk_contract_still_auto_resolves_normally_in_executive_mode(self) -> None:
        # Control: confirms the new gate only fires when the contract is
        # genuinely unavailable, and the default (True) preserves every
        # pre-existing caller's behavior unchanged.
        remaining, _, _ = self._call(operating_mode="executive", risk_contract_available=True)
        assert remaining == []


class TestApplyOperatingModeConsumesScaledRiskLimits:
    """CEO directive "Risk Contract Enforcement + Dynamic Risk Scaling
    1.0" — proves that whatever `risk_limits` app/nexus.py's tick() now
    passes here (this tick's real `effective_risk_limits`, RiskContract
    scaling already composed in) actually governs the quantity an
    auto-resolved trade opens at, on the SAME auto-resolution path a
    real Executive/Assisted Mode company uses every tick — not just the
    CEO's own manual-click path (see TestSubmitCeoDecisionRiskContract
    Enforcement in tests/test_state.py for that one)."""

    def _call(self, *, risk_limits: RiskLimits, proposal_quantity: float):
        proposal = _proposal().model_copy(update={"quantity": proposal_quantity})
        return _apply_operating_mode(
            "executive",
            [proposal],
            [],  # debates
            default_portfolio(),
            risk_limits,
            [],  # risk_warnings
            {"NEXA": 100.0},  # prices
            0,  # now_sim_minutes
            [],  # memory
            [],  # decisions
            [],  # ceo_decisions
            [],  # prediction_records
            [],  # gatekeeper_rejections
            [],  # news
            [],  # challenge_reports
            [],  # coach_reports
            [],  # meeting_log
            [],  # decision_vault
            1,  # sim_day
            default_market_intelligence_state(),
            [],  # war_room_sessions
            "sideways",  # market_environment_regime
            "balanced_institutional",  # active_weight_profile
            {},  # custom_department_weights
        )

    def test_a_scaled_risk_limits_narrows_the_auto_resolved_order_below_the_raw_ceiling(self) -> None:
        # default_portfolio() equity is 100_000. Raw RiskLimits() ceiling:
        # min(100_000*2%, 100_000*10%)/100 price = 20.0 shares. A caller-
        # supplied, already-scaled RiskLimits (risk_per_trade_pct=1.5,
        # max_position_pct=7.5 — what apply_active_risk_contract() would
        # produce under a 0.75x drawdown band) narrows that ceiling to
        # 15.0. The proposal's own stale quantity (1_000) is nowhere near
        # either number, isolating exactly which ceiling actually governs.
        scaled = RiskLimits(riskPerTradePct=1.5, maxPositionPct=7.5)
        _remaining, portfolio, _ = self._call(risk_limits=scaled, proposal_quantity=1_000.0)
        assert len(portfolio.positions) == 1
        assert portfolio.positions[0].quantity == 15.0

    def test_the_raw_unscaled_ceiling_would_have_allowed_a_larger_order(self) -> None:
        # Control, proving the above is a real narrowing, not incidental:
        # the SAME proposal against the SAME portfolio, with no scaling
        # applied, opens the wider, unscaled 20.0-share position.
        raw = RiskLimits()
        _remaining, portfolio, _ = self._call(risk_limits=raw, proposal_quantity=1_000.0)
        assert len(portfolio.positions) == 1
        assert portfolio.positions[0].quantity == 20.0


class TestAutoResolutionEnforcesButDoesNotAuditRiskDecisions:
    """CEO directive "Controlled Paper Trading Readiness Audit + Burn-in
    1.0" — a real 6-simulated-day burn-in (Executive Mode, this
    directive's own multi-day requirement) surfaced a genuine, disclosed
    gap: auto-resolved trades ARE correctly RiskContract-scaled (see
    TestApplyOperatingModeConsumesScaledRiskLimits above — real
    enforcement), but never produce a RiskDecision audit record. Only
    app/state.py::submit_ceo_decision() (the CEO's own manual click)
    builds one. This was always true (the RiskDecision mechanism's own
    original directive scoped it to the manual path only) — this test
    pins it down as a checkable, honest invariant rather than leaving it
    an undocumented side effect, since a live burn-in is what actually
    surfaced it as worth naming explicitly. Not a safety gap (enforcement
    is real either way) — an audit-trail completeness gap, named here as
    a candidate future finding, not fixed in this pass."""

    def test_auto_resolved_trades_leave_zero_risk_decisions_even_when_a_position_opens(self) -> None:
        proposal = _proposal().model_copy(update={"quantity": 5.0})
        remaining, portfolio, _meeting_log = _apply_operating_mode(
            "executive",
            [proposal],
            [],  # debates
            default_portfolio(),
            RiskLimits(),
            [],  # risk_warnings
            {"NEXA": 100.0},  # prices
            0,  # now_sim_minutes
            [],  # memory
            [],  # decisions
            [],  # ceo_decisions
            [],  # prediction_records
            [],  # gatekeeper_rejections
            [],  # news
            [],  # challenge_reports
            [],  # coach_reports
            [],  # meeting_log
            [],  # decision_vault
            1,  # sim_day
            default_market_intelligence_state(),
            [],  # war_room_sessions
            "sideways",  # market_environment_regime
            "balanced_institutional",  # active_weight_profile
            {},  # custom_department_weights
        )
        assert remaining == []
        assert len(portfolio.positions) == 1
        # _apply_operating_mode() has no risk_decisions parameter or
        # return slot at all — the real, structural confirmation that
        # this path cannot produce one today, not just an unpopulated
        # list this test happened not to check.
        import inspect

        assert "risk_decisions" not in inspect.signature(_apply_operating_mode).parameters


class TestFlattenedTradesReachTheLearningLoop:
    """CEO directive "Next Phase: Professional Trading Firm Intelligence,"
    Phase 2 (Decision Vault coverage expansion). RESEARCH FINDING: a day-
    end flattened trade (app/trading_modes.py's flatten_day_positions())
    was appended to trade_history but never passed into
    _journal_closed_trades() — so it never got a decisionId, a
    DisciplineReview, or a DecisionVaultEntry, unlike every other real
    close path. Fixed by merging flattened_trades into the same real
    closed-trade list hold-duration/broker closes already flow through —
    no new pipeline, the existing one just wasn't being fed this data.
    This test exercises the real, full nexus.tick() rather than a unit
    of _journal_closed_trades() directly, since the bug was specifically
    in the wiring between them."""

    def test_a_day_flattened_position_gets_a_real_decision_id_discipline_review_and_vault_entry(self) -> None:
        state = default_state()
        portfolio = open_position(
            default_portfolio(),
            position_id="pos-flatten-test",
            symbol="AAPL",
            price=100.0,
            opened_by="scout",
            confidence=90.0,
            opened_sim_minutes=0,
            side="buy",
            trading_style="day",
        )
        decision = TradeDecision(
            id="decision-flatten-test",
            symbol="AAPL",
            outcome="trade",
            votes=[],
            researchSummary="x",
            technicalSummary="x",
            fundamentalSummary="x",
            riskSummary="x",
            supportingAgents=["scout"],
            opposingAgents=[],
            confidence=90.0,
            finalReasoning="x",
            createdAt="2026-01-01T00:00:00+00:00",
        )
        state = state.model_copy(update={"paper_portfolio": portfolio, "decisions": [decision]})

        # new_time.day != state.time.day (1) triggers is_new_sim_day, the
        # real condition flatten_day_positions() fires under.
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)

        flattened = next((t for t in result.paper_portfolio.trade_history if t.symbol == "AAPL" and "flattened" in t.reason.lower()), None)
        assert flattened is not None
        assert flattened.decision_id == "decision-flatten-test"
        assert any(r.id == f"discipline-{flattened.id}" for r in result.discipline_reviews)
        assert any(v.trade_id == flattened.id for v in result.decision_vault)

    def test_a_position_carrying_a_real_proposal_id_gets_a_deterministic_decision_id_not_a_symbol_guess(self) -> None:
        # Professional Quant Live Trading Desk — a position opened with a
        # real proposal_id (app/executive.py's resolve_proposal() now
        # always sets one) must resolve its decision_id deterministically
        # from that field, never from the old best-effort "most recent
        # trade decision for this symbol" match — which would silently
        # pick the wrong decision if two same-symbol trades are in
        # flight. Two decisions on the same symbol here, only one of
        # which matches this position's real proposal_id, proves the
        # fix: the fuzzy match would have picked "decision-wrong" (the
        # more recent one in the list), the real link must not.
        state = default_state()
        portfolio = open_position(
            default_portfolio(),
            position_id="pos-flatten-test-2",
            symbol="AAPL",
            price=100.0,
            opened_by="scout",
            confidence=90.0,
            opened_sim_minutes=0,
            side="buy",
            trading_style="day",
            proposal_id="proposal-real",
        )
        wrong_decision = TradeDecision(
            id="decision-wrong", symbol="AAPL", outcome="trade", votes=[], researchSummary="x", technicalSummary="x", fundamentalSummary="x",
            riskSummary="x", supportingAgents=["scout"], opposingAgents=[], confidence=90.0, finalReasoning="x", createdAt="2026-01-01T00:00:01+00:00",
        )
        real_decision = TradeDecision(
            id="decision-proposal-real", symbol="AAPL", outcome="trade", votes=[], researchSummary="x", technicalSummary="x", fundamentalSummary="x",
            riskSummary="x", supportingAgents=["scout"], opposingAgents=[], confidence=90.0, finalReasoning="x", createdAt="2026-01-01T00:00:00+00:00",
        )
        state = state.model_copy(update={"paper_portfolio": portfolio, "decisions": [real_decision, wrong_decision]})

        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)

        flattened = next((t for t in result.paper_portfolio.trade_history if t.symbol == "AAPL" and "flattened" in t.reason.lower()), None)
        assert flattened is not None
        assert flattened.proposal_id == "proposal-real"
        assert flattened.decision_id == "decision-proposal-real"


class TestGenerateTradeProposalsTradingRestrictions:
    """CEO directive "Layered Kill Switches" — the first of
    app/trading_restrictions.py's two real enforcement points: a
    restricted symbol/category never even reaches the CEO as a
    proposal."""

    def _item(self, symbol: str = "NEXA", category: str = "stock") -> ResearchItem:
        return ResearchItem(
            id=f"research-{symbol}",
            title=f"{symbol} breakout setup",
            symbol=symbol,
            category=category,  # type: ignore[arg-type]
            priority="high",
            status="completed",
            assignedAgent="nova",
            summary="Real breakout pattern.",
            confidence=90.0,
            createdAt=_now_iso(),
            updatedAt=_now_iso(),
        )

    def _generate(self, items, trading_restrictions=None) -> list[TradeProposal]:
        return _generate_trade_proposals(
            [],
            items,
            {"NEXA": 100.0, "OTHER": 50.0},
            RiskLimits(),
            default_portfolio(),
            [],
            [],
            0,
            default_market_intelligence_state(),
            [],
            trading_restrictions,
        )

    def test_generates_a_proposal_with_no_restrictions(self) -> None:
        proposals = self._generate([self._item()])
        assert len(proposals) == 1
        assert proposals[0].symbol == "NEXA"

    def test_skips_a_symbol_restricted_research_item(self) -> None:
        restrictions, _, _ = activate_trading_restriction([], scope="symbol", target="NEXA", reason="halt", now_iso=_now_iso())
        proposals = self._generate([self._item()], trading_restrictions=restrictions)
        assert proposals == []

    def test_skips_a_category_restricted_research_item(self) -> None:
        restrictions, _, _ = activate_trading_restriction([], scope="category", target="stock", reason="halt category", now_iso=_now_iso())
        proposals = self._generate([self._item()], trading_restrictions=restrictions)
        assert proposals == []

    def test_an_unrelated_restriction_does_not_block_a_different_symbol(self) -> None:
        restrictions, _, _ = activate_trading_restriction([], scope="symbol", target="NEXA", reason="halt", now_iso=_now_iso())
        proposals = self._generate([self._item(symbol="OTHER")], trading_restrictions=restrictions)
        assert len(proposals) == 1
        assert proposals[0].symbol == "OTHER"
