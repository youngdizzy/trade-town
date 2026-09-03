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
from app.nexus import MAX_DECISIONS, MAX_RISK_DECISIONS, _apply_operating_mode, _generate_trade_proposals, _trim_decisions
from app.nexus import tick as nexus_tick
from app.portfolio import default_portfolio, open_position
from app.risk_contract import activate_risk_contract, apply_active_risk_contract, create_draft_risk_contract, mark_validated
from app.schemas import AnalystVote, ConfidenceFactor, DecisionConfidence, ResearchItem, RiskContract, RiskLimits, TimeState, TradeDecision, TradeProposal
from app.state import default_state
from app.trading_restrictions import activate_trading_restriction

_NOW = "2026-01-01T00:00:00+00:00"


def _active_risk_contract(*, limits: RiskLimits | None = None) -> tuple[RiskContract, list[RiskContract]]:
    draft = create_draft_risk_contract(history=[], contract_id="rc-1", limits=limits or RiskLimits(), created_by="ceo", reason="Initial contract.", created_at=_NOW)
    validated = mark_validated(draft, now_iso=_NOW)
    return activate_risk_contract([validated], validated.id, now_iso=_NOW)


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


class TestAutoResolutionRiskDecisionAuditTrail:
    """CEO directive "Auto-Resolution Risk Decision Audit Trail 1.0" —
    closes the real, disclosed gap the prior "Controlled Paper Trading
    Readiness Audit + Burn-in 1.0" milestone found and named (auto-
    resolved trades were always correctly RiskContract-scaled, but never
    produced a RiskDecision audit record — only a manual/delegated CEO
    click did). `_apply_operating_mode()` now builds one via the exact
    same `app/risk_contract.py::build_risk_decision()` the manual path
    uses, whenever a real `active_risk_contract`/`risk_contract_scaling`/
    `risk_decisions` are supplied — see that function's own docstring
    for why omitting them (as every OTHER test in this file does)
    changes nothing about which trades execute."""

    def _call(self, *, risk_decisions: list, risk_limits: RiskLimits = RiskLimits(), active_risk_contract=None, risk_contract_scaling=None, quantity: float = 5.0):  # type: ignore[no-untyped-def]
        proposal = _proposal().model_copy(update={"quantity": quantity})
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
            active_risk_contract=active_risk_contract,
            risk_contract_scaling=risk_contract_scaling,
            risk_decisions=risk_decisions,
        )

    def test_omitting_the_new_params_still_produces_zero_risk_decisions(self) -> None:
        """Backward-compatible default — every other test in this file
        (and every real caller before this directive) calls without
        these params; behavior must stay exactly what it was."""
        risk_decisions: list = []
        remaining, portfolio, _meeting_log = self._call(risk_decisions=risk_decisions)
        assert remaining == []
        assert len(portfolio.positions) == 1
        assert risk_decisions == []

    def test_a_real_active_contract_produces_a_real_risk_decision_for_an_approved_auto_resolved_trade(self) -> None:
        active, history = _active_risk_contract()
        limits, contract, scaling = apply_active_risk_contract(RiskLimits(), risk_contracts=history, drawdown_pct=0.0, consecutive_losses=0)
        risk_decisions: list = []
        remaining, portfolio, _meeting_log = self._call(risk_decisions=risk_decisions, risk_limits=limits, active_risk_contract=contract, risk_contract_scaling=scaling)
        assert remaining == []
        assert len(portfolio.positions) == 1
        assert len(risk_decisions) == 1
        risk_decision = risk_decisions[0]
        assert risk_decision.rejected is False
        assert risk_decision.approved_quantity == portfolio.positions[0].quantity
        assert risk_decision.symbol == "NEXA"

    def test_scaled_risk_decision_reflects_the_real_drawdown_band(self) -> None:
        """The persisted RiskDecision must reflect ACTUAL applied limits
        — not a fixed/normal band regardless of real drawdown state."""
        active, history = _active_risk_contract()
        limits, contract, scaling = apply_active_risk_contract(RiskLimits(), risk_contracts=history, drawdown_pct=5.0, consecutive_losses=0)
        assert scaling is not None and scaling.drawdown_band_label == "moderate_drawdown"
        risk_decisions: list = []
        self._call(risk_decisions=risk_decisions, risk_limits=limits, active_risk_contract=contract, risk_contract_scaling=scaling)
        assert len(risk_decisions) == 1
        assert risk_decisions[0].scaling.drawdown_band_label == "moderate_drawdown"

    def test_a_missing_contract_produces_no_risk_decision_fails_closed_like_before(self) -> None:
        """A missing contract must never fabricate a RiskDecision — the
        real fail-closed guard lives one layer up (risk_contract_available),
        this just confirms build_risk_decision()'s own None-safety holds
        even if a caller somehow reached this point without one."""
        risk_decisions: list = []
        remaining, portfolio, _meeting_log = self._call(risk_decisions=risk_decisions, active_risk_contract=None, risk_contract_scaling=None)
        assert remaining == []
        assert len(portfolio.positions) == 1  # enforcement/execution unchanged
        assert risk_decisions == []  # but no audit record without a real contract

    def test_a_rejected_auto_resolved_candidate_is_not_flattened_by_downstream_use(self) -> None:
        """A candidate the real Gatekeeper vetoes (sized to zero via the
        kill-switch band) still gets audited — rejected=True, no position."""
        active, history = _active_risk_contract()
        limits, contract, scaling = apply_active_risk_contract(RiskLimits(), risk_contracts=history, drawdown_pct=15.0, consecutive_losses=0)
        assert scaling is not None and scaling.kill_switch_triggered
        risk_decisions: list = []
        remaining, portfolio, _meeting_log = self._call(risk_decisions=risk_decisions, risk_limits=limits, active_risk_contract=contract, risk_contract_scaling=scaling)
        assert remaining == []
        assert portfolio.positions == []
        assert len(risk_decisions) == 1
        assert risk_decisions[0].rejected is True
        assert risk_decisions[0].approved_quantity == 0.0

    def test_risk_decisions_list_is_capped_at_max_risk_decisions(self) -> None:
        """Same real permanent-audit-list cap discipline as gatekeeper_
        rejections/decisions elsewhere in this same loop — never
        unbounded growth."""
        active, history = _active_risk_contract()
        limits, contract, scaling = apply_active_risk_contract(RiskLimits(), risk_contracts=history, drawdown_pct=0.0, consecutive_losses=0)
        risk_decisions = [
            __import__("app.schemas", fromlist=["RiskDecision"]).RiskDecision(
                id=f"riskdecision-pre-{i}", createdAt="2026-01-01T00:00:00+00:00", proposalId=f"p{i}", decisionId=f"d{i}", symbol="AAA",
                scaling=scaling, requestedQuantity=1.0, approvedQuantity=1.0, rejected=False,
            )
            for i in range(MAX_RISK_DECISIONS)
        ]
        self._call(risk_decisions=risk_decisions, risk_limits=limits, active_risk_contract=contract, risk_contract_scaling=scaling)
        assert len(risk_decisions) == MAX_RISK_DECISIONS
        assert risk_decisions[-1].symbol == "NEXA"  # the newest one — oldest was evicted, not this one

    def test_pre_existing_risk_decisions_are_not_rewritten_by_a_new_tick(self) -> None:
        """Historical preservation — a real, already-persisted RiskDecision
        must come out byte-identical after a tick that adds a new one."""
        active, history = _active_risk_contract()
        limits, contract, scaling = apply_active_risk_contract(RiskLimits(), risk_contracts=history, drawdown_pct=0.0, consecutive_losses=0)
        RiskDecisionModel = __import__("app.schemas", fromlist=["RiskDecision"]).RiskDecision
        historical = RiskDecisionModel(
            id="riskdecision-historical-1", createdAt="2025-01-01T00:00:00+00:00", proposalId="old-proposal", decisionId="old-decision",
            symbol="OLDSYM", scaling=scaling, requestedQuantity=3.0, approvedQuantity=3.0, rejected=False,
        )
        historical_copy = historical.model_copy()
        risk_decisions: list = [historical]
        self._call(risk_decisions=risk_decisions, risk_limits=limits, active_risk_contract=contract, risk_contract_scaling=scaling)
        assert len(risk_decisions) == 2
        assert risk_decisions[0] == historical_copy

    def test_a_second_call_on_the_returned_still_pending_list_cannot_duplicate(self) -> None:
        """Idempotency — once a proposal resolves, it's removed from the
        pending list the real tick() loop actually persists; replaying
        _apply_operating_mode() against that SAME (now-empty-of-it)
        returned list can never re-resolve the same proposal twice."""
        active, history = _active_risk_contract()
        limits, contract, scaling = apply_active_risk_contract(RiskLimits(), risk_contracts=history, drawdown_pct=0.0, consecutive_losses=0)
        risk_decisions: list = []
        remaining, portfolio, _meeting_log = self._call(risk_decisions=risk_decisions, risk_limits=limits, active_risk_contract=contract, risk_contract_scaling=scaling)
        assert len(risk_decisions) == 1
        assert remaining == []

        # Replay: call again with the real, now-empty remaining list — the
        # exact real shape app/nexus.py's tick() would pass on the next
        # real tick (or a duplicate-event replay of this same one).
        remaining_2, portfolio_2, _meeting_log_2 = _apply_operating_mode(
            "executive", remaining, [], portfolio, limits, [], {"NEXA": 100.0}, 0, [], [], [], [], [], [], [], [], [], [], 1,
            default_market_intelligence_state(), [], "sideways", "balanced_institutional", {},
            active_risk_contract=contract, risk_contract_scaling=scaling, risk_decisions=risk_decisions,
        )
        assert len(risk_decisions) == 1  # unchanged — nothing left to resolve
        assert portfolio_2 == portfolio


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
