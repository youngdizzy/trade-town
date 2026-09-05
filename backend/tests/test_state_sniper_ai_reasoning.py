"""Covers app/state.py's GameState.submit_sniper_ai_reasoning_request()
and GameState.refresh_sniper_ai_reasoning_outcomes() — CEO directive
"TradeTown — Memecoin Sniper AI 1.0." Confirms the real, live entry
point: (1) raises for an unknown candidate rather than fabricating a
result; (2) appends exactly one new AIReasoningResult to the SAME shared
`ai_reasoning_results` list the equities layer uses (no second,
duplicated list for this domain); (3) `deterministic_recommendation` is
correctly derived from real position/trade state at request time; (4)
refresh grades a pending Sniper result against real trade evidence and
never touches an equities-domain result.
"""
from __future__ import annotations

import asyncio

import pytest

import app.state as state_module
from app.ai_provider import ProviderCallResult
from app.schemas import AIReasoningResult, SniperCandidate, SniperScoreComponent, SniperTrade
from app.state import GameState

_CREATED_AT = "2026-01-01T00:00:00+00:00"


def _candidate(*, candidate_id: str = "cand-1", mint: str = "m" * 32) -> SniperCandidate:
    return SniperCandidate(
        id=candidate_id, mint=mint, symbol="MEWPEPE", name="MEWPEPE Token", discoveredAt=_CREATED_AT, ageSeconds=20.0,
        priceUsd=0.0001, marketCapUsd=100_000.0, liquidityUsd=80_000.0, liquidityTrend="rising", buyCount1m=40,
        buyPressurePct=80.0, uniqueBuyers=30, uniqueSellers=8, top10ConcentrationPct=25.0, mintAuthorityRevoked=True,
        freezeAuthorityRevoked=True, creatorRisk="weak_signal", whaleSignalCount=2, socialMomentumPct=50.0,
        expectedSlippagePct=2.0, rugRisk="low", dataQuality="sufficient", safetyStatus="safe_enough", safetyChecks=[],
        opportunityScore=82.0, scoreComponents=[SniperScoreComponent(name="momentum", rawValue=20.0, normalizedScore=54.0, weightPct=20.0, detail="x")],
        classification="high_conviction", timingState="entry_window", decisionReason="test reason",  # type: ignore[arg-type]
    )


def _trade(*, mint: str, pnl_sol: float) -> SniperTrade:
    return SniperTrade(
        id=f"trade-{mint[:8]}", mint=mint, symbol="MEWPEPE", openedAt=_CREATED_AT, closedAt=_CREATED_AT, entryPrice=0.0001,
        exitPrice=0.00012, stopPrice=0.000088, targetPrice=0.000155, sizeSol=1.0, riskSol=0.012, rMultiple=pnl_sol / 0.012,
        pnlSol=pnl_sol, maxFavorableExcursionPct=20.0, maxAdverseExcursionPct=-5.0, holdTimeSeconds=30.0,
        exitReason="take_profit" if pnl_sol >= 0 else "stop_loss", thesis="x",
    )


def _existing_result(*, result_id: str, domain: str = "memecoin_sniper", proposal_id: str = "m" * 32, outcome_status: str = "not_applicable") -> AIReasoningResult:
    return AIReasoningResult(
        id=result_id, agentId="quant", role="sniper_analyst", domain=domain, task="x", evidencePacketId="pkt-old",  # type: ignore[arg-type]
        proposalId=proposal_id, symbol="MEWPEPE", modelProvider="fake", modelName="fake-model", modelVersion="fake-model",
        promptVersion="test-1.0", status="completed", createdAt=_CREATED_AT, outcomeStatus=outcome_status,  # type: ignore[arg-type]
    )


class _FakeProvider:
    provider_name = "fake"

    def __init__(self, raw_text: str = '{"thesis": "A real thesis.", "recommendation": "buy"}') -> None:
        self._raw_text = raw_text

    async def call(self, *, system_prompt: str, user_content: str) -> ProviderCallResult:
        return ProviderCallResult(status="ok", provider="fake", model="fake-model", raw_text=self._raw_text, input_tokens=1, output_tokens=1, latency_ms=1.0, detail=None)


def test_unknown_candidate_raises_rather_than_fabricating() -> None:
    async def _run() -> None:
        state = GameState()
        try:
            await state.submit_sniper_ai_reasoning_request("no-such-candidate")
        except KeyError:
            return
        raise AssertionError("expected KeyError for an unknown candidate id")

    asyncio.run(_run())


def test_reasoning_request_appends_to_the_shared_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider())

    async def _run() -> None:
        state = GameState()
        candidate = _candidate()
        state.data = state.data.model_copy(update={"sniper_candidates": [candidate]})
        updated, result = await state.submit_sniper_ai_reasoning_request(candidate.id)
        assert result.status == "completed"
        assert result.role == "sniper_analyst"
        assert result.domain == "memecoin_sniper"
        assert result.agent_id == "quant"
        assert result.proposal_id == candidate.mint
        assert result.id in [r.id for r in updated.ai_reasoning_results]
        assert result.id in [r.id for r in state.data.ai_reasoning_results]

    asyncio.run(_run())


def test_deterministic_recommendation_reflects_real_trade_history(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider())

    async def _run() -> None:
        state = GameState()
        candidate = _candidate()
        trade = _trade(mint=candidate.mint, pnl_sol=0.05)
        state.data = state.data.model_copy(update={"sniper_candidates": [candidate], "sniper_trade_history": [trade]})
        _updated, result = await state.submit_sniper_ai_reasoning_request(candidate.id)
        assert result.deterministic_recommendation == "buy"

    asyncio.run(_run())


def test_requested_after_outcome_known_true_when_trade_already_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """"Sniper AI Shadow Reasoning Burn-In 1.0" directive, Part XI/XXVI —
    the real, disclosed flag must reflect real request-time state: a
    candidate whose trade already closed before the request was made."""
    monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider())

    async def _run() -> None:
        state = GameState()
        candidate = _candidate()
        trade = _trade(mint=candidate.mint, pnl_sol=0.05)
        state.data = state.data.model_copy(update={"sniper_candidates": [candidate], "sniper_trade_history": [trade]})
        _updated, result = await state.submit_sniper_ai_reasoning_request(candidate.id)
        assert result.requested_after_outcome_known is True

    asyncio.run(_run())


def test_requested_after_outcome_known_false_when_never_entered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider())

    async def _run() -> None:
        state = GameState()
        candidate = _candidate()
        state.data = state.data.model_copy(update={"sniper_candidates": [candidate]})
        _updated, result = await state.submit_sniper_ai_reasoning_request(candidate.id)
        assert result.requested_after_outcome_known is False

    asyncio.run(_run())


def test_deterministic_recommendation_is_wait_when_never_entered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider())

    async def _run() -> None:
        state = GameState()
        candidate = _candidate()
        state.data = state.data.model_copy(update={"sniper_candidates": [candidate]})
        _updated, result = await state.submit_sniper_ai_reasoning_request(candidate.id)
        assert result.deterministic_recommendation == "wait"

    asyncio.run(_run())


def test_refresh_outcomes_grades_a_pending_sniper_result() -> None:
    async def _run() -> None:
        state = GameState()
        mint = "m" * 32
        pending = _existing_result(result_id="res-1", proposal_id=mint, outcome_status="pending")
        trade = _trade(mint=mint, pnl_sol=0.05)
        state.data = state.data.model_copy(update={"ai_reasoning_results": [pending], "sniper_trade_history": [trade]})
        updated = await state.refresh_sniper_ai_reasoning_outcomes()
        graded = next(r for r in updated.ai_reasoning_results if r.id == "res-1")
        assert graded.outcome_status == "evaluated"
        assert graded.outcome == "supported"
        assert graded.outcome_ref == trade.id

    asyncio.run(_run())


def test_refresh_outcomes_never_touches_an_equities_domain_result() -> None:
    async def _run() -> None:
        state = GameState()
        equities_result = _existing_result(result_id="res-equities", domain="equities", proposal_id="proposal-1", outcome_status="pending")
        state.data = state.data.model_copy(update={"ai_reasoning_results": [equities_result]})
        updated = await state.refresh_sniper_ai_reasoning_outcomes()
        still = next(r for r in updated.ai_reasoning_results if r.id == "res-equities")
        assert still.outcome_status == "pending"
        assert still.outcome is None

    asyncio.run(_run())


def test_refresh_outcomes_never_touches_an_already_evaluated_result() -> None:
    async def _run() -> None:
        state = GameState()
        evaluated = _existing_result(result_id="res-1", outcome_status="evaluated").model_copy(update={"outcome": "contradicted", "outcome_ref": "trade-old"})
        state.data = state.data.model_copy(update={"ai_reasoning_results": [evaluated]})
        updated = await state.refresh_sniper_ai_reasoning_outcomes()
        still = next(r for r in updated.ai_reasoning_results if r.id == "res-1")
        assert still.outcome == "contradicted"
        assert still.outcome_ref == "trade-old"

    asyncio.run(_run())
