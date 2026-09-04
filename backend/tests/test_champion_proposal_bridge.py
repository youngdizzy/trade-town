"""Covers CEO directive "TradeTown — Champion-Sourced Trade Proposal
Provenance + Shadow Bridge 1.0": `app/executive.py::build_champion_trade_proposal()`
(the thin champion-signal -> TradeProposal adapter) and its wiring into
`app/nexus.py::tick()` — merged into the SAME `candidate_proposals` list
the heuristic path already produces, so it passes through the identical,
unmodified Opportunity Gatekeeper/War Room/Risk Contract funnel. Every
champion fixture is built via the real `compare_champion_challenger()`/
`promote_challenger()` pipeline, never a hand-built `ChampionRecord`.
"""
from __future__ import annotations

import json

from app.champion_challenger import compare_champion_challenger, promote_challenger
from app.executive import build_champion_trade_proposal
from app.market_intelligence import default_market_intelligence_state
from app.nexus import tick as nexus_tick
from app.portfolio import default_portfolio
from app.schemas import LiveSetupSignal, RiskLimits, TimeState, TradeProposal
from app.state import default_state
from app.strategy_compiler import compile_strategy_text, strategy_definition_slug

_CREATED_AT = "2024-01-01T00:00:00+00:00"
_EMA_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
_WEAK_TEXT = "Buy when the RSI is above 70. Enter when price closes above the previous swing high. Place a 5% stop. Target 2R."

_SIGNAL = LiveSetupSignal(direction="long", entryTimestamp="2024-06-01T09:00:00+00:00", entryPrice=100.0, stopPrice=95.0, targetPrice=112.0)
_SHORT_SIGNAL = LiveSetupSignal(direction="short", entryTimestamp="2024-06-01T09:00:00+00:00", entryPrice=100.0, stopPrice=105.0, targetPrice=88.0)


def _promote_real_champion(strategy_family_name: str, *, verdict: str = "challenger_recommended"):  # type: ignore[no-untyped-def]
    """Real, end-to-end: two real compiled strategies through the real
    compare_champion_challenger()/promote_challenger() pipeline —
    verdict force-set for determinism, matching this session's own
    established convention (tests/test_champion_live_signal.py)."""
    champion_seed = compile_strategy_text(name=f"{strategy_family_name} Seed", source_text=_WEAK_TEXT)
    challenger_definition = compile_strategy_text(name=strategy_family_name, source_text=_EMA_TEXT)
    comparison = compare_champion_challenger(
        champion_seed, challenger_definition, strategy_family=strategy_family_name, hypothesis="h", proposed_by="quant",
        comparison_id=f"cmp-{strategy_family_name}", generated_at=_CREATED_AT, symbols=["AAPL"],
    )
    comparison = comparison.model_copy(update={"verdict": "challenger_recommended"})
    record = promote_challenger(comparison, promoted_by="quant", reasoning="test promotion", record_id=f"champion-{strategy_family_name}", promoted_at=_CREATED_AT)
    return record, challenger_definition, comparison


class TestBuildChampionTradeProposal:
    def test_returns_none_when_position_sizing_resolves_to_zero(self) -> None:
        record, definition, comparison = _promote_real_champion("Zero Size Family")
        tiny_limits = RiskLimits(riskPerTradePct=0.0, maxPositionPct=0.0)
        proposal = build_champion_trade_proposal(
            record, definition, _SIGNAL, "AAPL", price=100.0, comparison=comparison, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=tiny_limits, market_intelligence=default_market_intelligence_state(),
        )
        assert proposal is None

    def test_a_real_proposal_carries_correct_truthful_provenance(self) -> None:
        record, definition, comparison = _promote_real_champion("Provenance Family")
        proposal = build_champion_trade_proposal(
            record, definition, _SIGNAL, "AAPL", price=100.0, comparison=comparison, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=1234, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        assert proposal is not None
        assert proposal.source == "champion"
        assert proposal.source_champion_id == record.id
        assert proposal.source_strategy_family == record.strategy_family
        assert proposal.source_definition_id == definition.id
        assert proposal.source_definition_version == definition.version
        assert proposal.source_signal_bar_timestamp == _SIGNAL.entry_timestamp

    def test_long_signal_maps_to_buy_recommendation(self) -> None:
        record, definition, comparison = _promote_real_champion("Long Family")
        proposal = build_champion_trade_proposal(
            record, definition, _SIGNAL, "AAPL", price=100.0, comparison=comparison, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        assert proposal is not None
        assert proposal.overall_recommendation == "buy"
        assert proposal.analyst_votes[0].choice == "buy"

    def test_short_signal_maps_to_sell_recommendation(self) -> None:
        record, definition, comparison = _promote_real_champion("Short Family")
        proposal = build_champion_trade_proposal(
            record, definition, _SHORT_SIGNAL, "AAPL", price=100.0, comparison=comparison, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        assert proposal is not None
        assert proposal.overall_recommendation == "sell"
        assert proposal.analyst_votes[0].choice == "sell"

    def test_the_one_real_vote_is_honestly_attributed_to_quant_not_echo(self) -> None:
        """ROLE_TO_AGENT maps a heuristic 'technical' vote to Echo — a
        champion signal must NOT borrow that attribution, since Echo
        produced nothing here."""
        record, definition, comparison = _promote_real_champion("Attribution Family")
        proposal = build_champion_trade_proposal(
            record, definition, _SIGNAL, "AAPL", price=100.0, comparison=comparison, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        assert proposal is not None
        assert len(proposal.analyst_votes) == 1
        assert proposal.analyst_votes[0].role == "technical"
        assert proposal.analyst_votes[0].agent_id == "quant"

    def test_entry_stop_target_are_reflected_as_real_evidence(self) -> None:
        record, definition, comparison = _promote_real_champion("Evidence Family")
        proposal = build_champion_trade_proposal(
            record, definition, _SIGNAL, "AAPL", price=100.0, comparison=comparison, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        assert proposal is not None
        evidence_text = " ".join(proposal.analyst_votes[0].evidence)
        assert "100.0000" in evidence_text
        assert "95.0000" in evidence_text
        assert "112.0000" in evidence_text

    def test_confidence_reflects_real_classification_when_a_comparison_exists(self) -> None:
        record, definition, comparison = _promote_real_champion("Classified Family")
        proposal = build_champion_trade_proposal(
            record, definition, _SIGNAL, "AAPL", price=100.0, comparison=comparison, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        assert proposal is not None
        assert comparison.classification in proposal.confidence_engine.factors[0].detail
        assert proposal.confidence_engine.score > 0

    def test_confidence_uses_an_honest_neutral_default_with_no_comparison(self) -> None:
        record, definition, _comparison = _promote_real_champion("No Comparison Family")
        proposal = build_champion_trade_proposal(
            record, definition, _SIGNAL, "AAPL", price=100.0, comparison=None, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        assert proposal is not None
        assert proposal.confidence_engine.score == 58.0
        assert "No promotion comparison" in proposal.confidence_engine.factors[0].detail

    def test_risk_summary_prefers_sentinel_over_guardian_over_default(self) -> None:
        from app.schemas import RiskWarning

        record, definition, comparison = _promote_real_champion("Risk Summary Family")
        sentinel = RiskWarning(id="warn-1", symbol="AAPL", severity="warning", message="Sentinel real warning.", createdAt=_CREATED_AT)
        proposal = build_champion_trade_proposal(
            record, definition, _SIGNAL, "AAPL", price=100.0, comparison=comparison, research=[],
            sentinel_warning=sentinel, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        assert proposal is not None
        assert proposal.risk_summary == "Sentinel real warning."

    def test_deterministic_id_from_champion_symbol_and_bar_timestamp(self) -> None:
        record, definition, comparison = _promote_real_champion("Deterministic Id Family")
        first = build_champion_trade_proposal(
            record, definition, _SIGNAL, "AAPL", price=100.0, comparison=comparison, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        second = build_champion_trade_proposal(
            record, definition, _SIGNAL, "AAPL", price=100.0, comparison=comparison, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=999, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        assert first is not None and second is not None
        assert first.id == second.id  # same champion+symbol+bar => same id, regardless of when evaluated

    def test_provenance_survives_json_serialization_round_trip(self) -> None:
        record, definition, comparison = _promote_real_champion("Serialization Family")
        proposal = build_champion_trade_proposal(
            record, definition, _SIGNAL, "AAPL", price=100.0, comparison=comparison, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        assert proposal is not None
        raw = proposal.model_dump_json(by_alias=True)
        reloaded = TradeProposal.model_validate(json.loads(raw))
        assert reloaded.source == "champion"
        assert reloaded.source_champion_id == record.id
        assert reloaded.source_definition_version == definition.version


class TestBackwardCompatibleProvenanceDefault:
    def test_a_pre_existing_proposal_with_no_source_field_defaults_honestly_to_heuristic(self) -> None:
        """Old saves never had a `source` key at all — this must parse
        as "heuristic" (a true historical fact: no other proposal path
        existed before this directive), never crash, never default to
        "champion"."""
        raw = {
            "id": "proposal-legacy-1", "symbol": "AAPL", "category": "stock", "quantity": 1.0, "price": 100.0,
            "confidence": 80.0, "analystVotes": [], "overallRecommendation": "wait", "researchSummary": "x",
            "riskSummary": "x", "confidenceEngine": {"score": 80.0, "tier": "good", "summary": "x", "factors": []},
            "createdAt": _CREATED_AT, "createdSimMinutes": 0,
        }
        proposal = TradeProposal.model_validate(raw)
        assert proposal.source == "heuristic"
        assert proposal.source_champion_id is None
        assert proposal.source_definition_version is None


class TestChampionProposalBridgeWiring:
    """Real end-to-end wiring through app/nexus.py::tick() — a real
    promoted champion, never a hand-built ChampionRecord."""

    def test_no_champion_produces_no_champion_sourced_proposals(self) -> None:
        state = default_state()
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        assert all(p.source == "heuristic" for p in result.trade_proposals)

    def test_a_forced_signal_never_produces_a_proposal_with_wrong_provenance(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """Regardless of whether the (real, unmodified) Opportunity
        Gatekeeper approves or rejects this candidate, ANY champion-
        sourced proposal that DOES reach trade_proposals must carry
        exactly this champion's own real identity — never a bypass,
        never fabricated identity."""
        import app.nexus as nexus_module

        record, definition, comparison = _promote_real_champion("Wired Family")
        forced_signal = LiveSetupSignal(direction="long", entryTimestamp="2024-06-01T09:00:00+00:00", entryPrice=50.0, stopPrice=45.0, targetPrice=60.0)
        monkeypatch.setattr(nexus_module, "detect_live_setup_at_latest_bar", lambda definition, symbol, candles: forced_signal)

        slug = strategy_definition_slug("Wired Family")
        state = default_state().model_copy(
            update={"champion_history": [record], "compiled_strategy_versions": {slug: [definition]}, "challenger_comparisons": [comparison]}
        )
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)

        champion_proposals = [p for p in result.trade_proposals if p.source == "champion"]
        for p in champion_proposals:
            assert p.source_champion_id == record.id
            assert p.source_strategy_family == "Wired Family"
            assert p.source_definition_id == definition.id
            assert p.source_definition_version == definition.version

    def test_emergency_stop_blocks_champion_proposal_progression(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import app.nexus as nexus_module

        record, definition, comparison = _promote_real_champion("Halted Family")
        forced_signal = LiveSetupSignal(direction="long", entryTimestamp="2024-06-01T09:00:00+00:00", entryPrice=50.0, stopPrice=45.0, targetPrice=60.0)
        monkeypatch.setattr(nexus_module, "detect_live_setup_at_latest_bar", lambda definition, symbol, candles: forced_signal)

        slug = strategy_definition_slug("Halted Family")
        state = default_state().model_copy(
            update={
                "champion_history": [record],
                "compiled_strategy_versions": {slug: [definition]},
                "challenger_comparisons": [comparison],
                "emergency_stop": default_state().emergency_stop.model_copy(update={"active": True}),
            }
        )
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        assert all(p.source != "champion" for p in result.trade_proposals)
        # The shadow capture itself is NOT gated by Emergency Stop (it
        # observes, it never trades) — this proves Emergency Stop
        # specifically blocked PROPOSAL progression, not signal detection.
        assert len(result.champion_live_signal_captures) >= 1

    def test_an_already_pending_champion_proposal_is_never_duplicated(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import app.nexus as nexus_module

        record, definition, comparison = _promote_real_champion("Dedup Pending Family")
        forced_signal = LiveSetupSignal(direction="long", entryTimestamp="2024-06-01T09:00:00+00:00", entryPrice=50.0, stopPrice=45.0, targetPrice=60.0)
        monkeypatch.setattr(nexus_module, "detect_live_setup_at_latest_bar", lambda definition, symbol, candles: forced_signal)

        existing_proposal = build_champion_trade_proposal(
            record, definition, forced_signal, "AAPL", price=50.0, comparison=comparison, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        assert existing_proposal is not None
        slug = strategy_definition_slug("Dedup Pending Family")
        state = default_state().model_copy(
            update={
                "champion_history": [record],
                "compiled_strategy_versions": {slug: [definition]},
                "challenger_comparisons": [comparison],
                "trade_proposals": [existing_proposal],
            }
        )
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        matching = [p for p in result.trade_proposals if p.id == existing_proposal.id]
        assert len(matching) == 1  # never duplicated

    def test_an_already_resolved_champion_signal_is_never_re_proposed(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """Covers the CEO-decided / auto-resolved / expired-to-wait case
        — expire_stale_proposals() always produces a real decision, so a
        matching `decision-<id>` entry is the correct, complete
        "already resolved" signal, without needing to inspect HOW it
        was resolved."""
        import app.nexus as nexus_module
        from app.schemas import TradeDecision

        record, definition, comparison = _promote_real_champion("Dedup Resolved Family")
        forced_signal = LiveSetupSignal(direction="long", entryTimestamp="2024-06-01T09:00:00+00:00", entryPrice=50.0, stopPrice=45.0, targetPrice=60.0)
        monkeypatch.setattr(nexus_module, "detect_live_setup_at_latest_bar", lambda definition, symbol, candles: forced_signal)

        candidate_id = f"proposal-champion-{record.id}-AAPL-{forced_signal.entry_timestamp}"
        resolved_decision = TradeDecision(
            id=f"decision-{candidate_id}", symbol="AAPL", outcome="no_trade", votes=[], researchSummary="x",
            technicalSummary="x", fundamentalSummary="x", riskSummary="x", supportingAgents=[], opposingAgents=[],
            confidence=58.0, finalReasoning="x", createdAt=_CREATED_AT,
        )
        slug = strategy_definition_slug("Dedup Resolved Family")
        state = default_state().model_copy(
            update={
                "champion_history": [record],
                "compiled_strategy_versions": {slug: [definition]},
                "challenger_comparisons": [comparison],
                "decisions": [resolved_decision],
            }
        )
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        assert all(p.id != candidate_id for p in result.trade_proposals)

    def test_a_different_bar_timestamp_is_a_genuinely_distinct_signal(self) -> None:
        record, definition, _comparison = _promote_real_champion("Distinct Bar Family")
        signal_a = LiveSetupSignal(direction="long", entryTimestamp="2024-06-01T09:00:00+00:00", entryPrice=50.0, stopPrice=45.0, targetPrice=60.0)
        proposal_a = build_champion_trade_proposal(
            record, definition, signal_a, "AAPL", price=50.0, comparison=None, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        signal_b = signal_a.model_copy(update={"entry_timestamp": "2024-06-01T10:00:00+00:00"})
        proposal_b = build_champion_trade_proposal(
            record, definition, signal_b, "AAPL", price=50.0, comparison=None, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        assert proposal_a is not None and proposal_b is not None
        assert proposal_a.id != proposal_b.id

    def test_champion_change_produces_a_different_source_definition(self) -> None:
        """A later, superseded champion for the same family must never
        have its proposals attributed to the earlier champion's identity."""
        first_record, first_definition, _c1 = _promote_real_champion("Superseded Bridge Family")
        second_definition = compile_strategy_text(name="Superseded Bridge Family", source_text=_EMA_TEXT, previous_version=1)
        second_comparison = compare_champion_challenger(
            first_definition, second_definition, strategy_family="Superseded Bridge Family", hypothesis="h", proposed_by="quant",
            comparison_id="cmp-superseded-bridge-2", generated_at=_CREATED_AT, symbols=["AAPL"],
        ).model_copy(update={"verdict": "challenger_recommended"})
        second_record = promote_challenger(second_comparison, promoted_by="quant", reasoning="second", record_id="champion-superseded-bridge-2", promoted_at=_CREATED_AT)

        proposal = build_champion_trade_proposal(
            second_record, second_definition, _SIGNAL, "AAPL", price=100.0, comparison=second_comparison, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        assert proposal is not None
        assert proposal.source_definition_id == second_definition.id
        assert proposal.source_definition_version == second_definition.version
        assert proposal.source_definition_version != first_definition.version

    def test_no_new_top_level_risk_or_order_engine_is_introduced(self) -> None:
        """Structural safety check: the champion adapter must construct
        ONLY a TradeProposal — never place an order, open a position, or
        touch a second risk engine directly."""
        import inspect

        from app import executive

        source = inspect.getsource(executive.build_champion_trade_proposal)
        assert "place_order(" not in source
        assert "open_position(" not in source
        assert "PaperPosition(" not in source


class TestChampionSignalDisposition:
    """CEO directive "TradeTown — Champion → Live Signal → TradeProposal
    / Forensic Architecture Gate + Safe Production Bridge 1.0" — every
    real fresh signal must resolve to an observable
    `ChampionLiveSignalCapture.disposition` (app/schemas.py's
    `ChampionSignalDisposition`), never a bare, unrecorded `continue` in
    app/nexus.py's tick(). One test per disposition value, all through
    the real, unmodified `nexus.tick()` wiring — never asserting on a
    hand-built capture."""

    def _wire_forced_signal(self, monkeypatch, family: str, **state_overrides):  # type: ignore[no-untyped-def]
        import app.nexus as nexus_module

        record, definition, comparison = _promote_real_champion(family)
        forced_signal = LiveSetupSignal(direction="long", entryTimestamp="2024-06-01T09:00:00+00:00", entryPrice=50.0, stopPrice=45.0, targetPrice=60.0)
        monkeypatch.setattr(nexus_module, "detect_live_setup_at_latest_bar", lambda definition, symbol, candles: forced_signal)
        slug = strategy_definition_slug(family)
        update = {"champion_history": [record], "compiled_strategy_versions": {slug: [definition]}, "challenger_comparisons": [comparison]}
        update.update(state_overrides)
        state = default_state().model_copy(update=update)
        return state, record, definition, forced_signal

    def test_created_proposal_candidate_disposition(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        state, record, _definition, forced_signal = self._wire_forced_signal(monkeypatch, "Disposition Created Family")
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        candidate_id = f"proposal-champion-{record.id}-AAPL-{forced_signal.entry_timestamp}"
        captures = [c for c in result.champion_live_signal_captures if c.champion_id == record.id and c.symbol == "AAPL"]
        assert captures and all(c.disposition == "created_proposal_candidate" for c in captures)
        assert any(p.id == candidate_id for p in result.trade_proposals) or any(r.id == f"oppreject-{candidate_id}" for r in result.opportunity_rejections)

    def test_duplicate_pending_disposition(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        state, record, definition, forced_signal = self._wire_forced_signal(monkeypatch, "Disposition Duplicate Pending Family")
        comparison = state.challenger_comparisons[0]
        existing_proposal = build_champion_trade_proposal(
            record, definition, forced_signal, "AAPL", price=50.0, comparison=comparison, research=[],
            sentinel_warning=None, guardian_warning=None, now_sim_minutes=0, portfolio=default_portfolio(),
            risk_limits=RiskLimits(), market_intelligence=default_market_intelligence_state(),
        )
        assert existing_proposal is not None
        state = state.model_copy(update={"trade_proposals": [existing_proposal]})
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        captures = [c for c in result.champion_live_signal_captures if c.champion_id == record.id and c.symbol == "AAPL"]
        assert captures and all(c.disposition == "duplicate_pending" for c in captures)

    def test_duplicate_resolved_disposition(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        from app.schemas import TradeDecision

        state, record, _definition, forced_signal = self._wire_forced_signal(monkeypatch, "Disposition Duplicate Resolved Family")
        candidate_id = f"proposal-champion-{record.id}-AAPL-{forced_signal.entry_timestamp}"
        resolved_decision = TradeDecision(
            id=f"decision-{candidate_id}", symbol="AAPL", outcome="no_trade", votes=[], researchSummary="x",
            technicalSummary="x", fundamentalSummary="x", riskSummary="x", supportingAgents=[], opposingAgents=[],
            confidence=58.0, finalReasoning="x", createdAt=_CREATED_AT,
        )
        state = state.model_copy(update={"decisions": [resolved_decision]})
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        captures = [c for c in result.champion_live_signal_captures if c.champion_id == record.id and c.symbol == "AAPL"]
        assert captures and all(c.disposition == "duplicate_resolved" for c in captures)

    def test_blocked_trading_restriction_disposition(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        from app.schemas import TradingRestriction

        restriction = TradingRestriction(id="restrict-aapl", scope="symbol", target="AAPL", reason="test", activatedAt=_CREATED_AT)
        state, record, _definition, _forced_signal = self._wire_forced_signal(
            monkeypatch, "Disposition Restricted Family", trading_restrictions=[restriction]
        )
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        captures = [c for c in result.champion_live_signal_captures if c.champion_id == record.id and c.symbol == "AAPL"]
        assert captures and all(c.disposition == "blocked_trading_restriction" for c in captures)

    def test_no_price_available_disposition(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """`tick_watchlist()` (real, unmodified) refreshes every symbol's
        `last_price` from the real market data provider EARLY in tick(),
        before the champion block ever runs — a zeroed `last_price` set
        on the incoming state is always overwritten by a real positive
        price before `prices` is built. That refresh has to be
        monkeypatched directly to exercise this branch at all, which is
        itself real, disclosed evidence that `no_price_available` is not
        reachable in today's actual production data path (the mock
        provider never returns a non-positive price) — kept as an honest
        fail-safe for a future real-data provider outage, not a
        currently-exercised production case."""
        import app.nexus as nexus_module

        state, record, _definition, _forced_signal = self._wire_forced_signal(monkeypatch, "Disposition No Price Family")

        def _zeroed_tick_watchlist(watchlist, research, provider):  # type: ignore[no-untyped-def]
            return [w.model_copy(update={"last_price": 0.0}) if w.symbol == "AAPL" else w for w in watchlist]

        monkeypatch.setattr(nexus_module, "tick_watchlist", _zeroed_tick_watchlist)
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        captures = [c for c in result.champion_live_signal_captures if c.champion_id == record.id and c.symbol == "AAPL"]
        assert captures and all(c.disposition == "no_price_available" for c in captures)

    def test_zero_quantity_sizing_disposition(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        zero_limits = default_state().risk_limits.model_copy(update={"risk_per_trade_pct": 0.0, "max_position_pct": 0.0})
        state, record, _definition, _forced_signal = self._wire_forced_signal(
            monkeypatch, "Disposition Zero Quantity Family", risk_limits=zero_limits
        )
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        captures = [c for c in result.champion_live_signal_captures if c.champion_id == record.id and c.symbol == "AAPL"]
        assert captures and all(c.disposition == "zero_quantity_sizing" for c in captures)

    def test_every_disposition_value_is_a_real_member_of_the_declared_literal(self) -> None:
        """Structural check: the schema's own declared set of dispositions
        is exactly what this test class exercises above — if a new value
        is ever added to ChampionSignalDisposition, this test starts
        failing until a real test for it is added too."""
        from typing import get_args

        from app.schemas import ChampionSignalDisposition

        declared = set(get_args(ChampionSignalDisposition))
        exercised = {
            "created_proposal_candidate",
            "duplicate_pending",
            "duplicate_resolved",
            "blocked_trading_restriction",
            "no_price_available",
            "zero_quantity_sizing",
        }
        assert declared == exercised
