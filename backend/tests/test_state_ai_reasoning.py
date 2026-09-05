"""Covers app/state.py's GameState.submit_ai_reasoning_request() and
GameState.refresh_ai_reasoning_outcomes() — CEO directive "TradeTown —
True AI Agent Reasoning Foundation 1.0." Confirms the real, live entry
point: (1) raises for an unknown proposal rather than fabricating a
result; (2) appends exactly one new, persisted AIReasoningResult per
call, never mutating the proposal/decision/risk state; (3) Devil's
Advocate agent identity rotates through the exact same
ELIGIBLE_DEVILS_ADVOCATES tuple app/devils_advocate.py's own rotation
already uses; (4) a prior completed Researcher result for the SAME
proposal is passed through to the Devil's Advocate call as an unverified
claim; (5) MAX_AI_REASONING_RESULTS caps the persisted list, dropping the
oldest, never the newest; (6) refresh_ai_reasoning_outcomes() grades a
pending result against real decision/journal evidence and never re-grades
an already-evaluated one.
"""
from __future__ import annotations

import asyncio
import json

import pytest

import app.state as state_module
from app.ai_provider import ProviderCallResult
from app.schemas import (
    AIReasoningResult,
    AnalystVote,
    ConfidenceFactor,
    DecisionConfidence,
    PaperTradeJournalEntry,
    TradeDecision,
    TradeProposal,
)
from app.state import MAX_AI_REASONING_RESULTS, GameState

_CREATED_AT = "2026-01-01T00:00:00+00:00"


def _proposal(*, proposal_id: str = "proposal-1") -> TradeProposal:
    vote = AnalystVote(role="technical", agentId="echo", choice="buy", reasoning="test reasoning", evidence=["real evidence"])
    return TradeProposal(
        id=proposal_id, symbol="NEXA", category="stock", quantity=10.0, price=100.0, confidence=80.0,
        analystVotes=[vote], overallRecommendation="buy", researchSummary="test research summary",
        riskSummary="NEXA is within all configured risk limits.",
        confidenceEngine=DecisionConfidence(score=80.0, tier="strong", summary="test", factors=[ConfidenceFactor(name="agreement", score=80.0, weight=1.0, detail="test")]),
        createdAt=_CREATED_AT, createdSimMinutes=60,
    )


class _FakeProvider:
    provider_name = "fake"

    def __init__(self, raw_text: str = '{"thesis": "A real thesis.", "recommendation": "buy"}') -> None:
        self._raw_text = raw_text

    async def call(self, *, system_prompt: str, user_content: str) -> ProviderCallResult:
        return ProviderCallResult(status="ok", provider="fake", model="fake-model", raw_text=self._raw_text, input_tokens=1, output_tokens=1, latency_ms=1.0, detail=None)


def _existing_result(*, result_id: str, role: str = "devils_advocate", proposal_id: str = "proposal-1", status: str = "completed", outcome_status: str = "not_applicable") -> AIReasoningResult:
    return AIReasoningResult(
        id=result_id, agentId="scribe", role=role, task="Evaluate NEXA", evidencePacketId="pkt-old",  # type: ignore[arg-type]
        proposalId=proposal_id, symbol="NEXA", modelProvider="fake", modelName="fake-model", modelVersion="fake-model",
        promptVersion="test-1.0", status=status, createdAt=_CREATED_AT, outcomeStatus=outcome_status,  # type: ignore[arg-type]
    )


def test_unknown_proposal_raises_rather_than_fabricating() -> None:
    async def _run() -> None:
        state = GameState()
        try:
            await state.submit_ai_reasoning_request("no-such-proposal", role="researcher")
        except KeyError:
            return
        raise AssertionError("expected KeyError for an unknown proposal id")

    asyncio.run(_run())


def test_researcher_request_appends_one_persisted_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider())

    async def _run() -> None:
        state = GameState()
        state.data = state.data.model_copy(update={"trade_proposals": [_proposal()]})
        updated, result = await state.submit_ai_reasoning_request("proposal-1", role="researcher")
        assert result.status == "completed"
        assert result.role == "researcher"
        assert result.agent_id == "nova"
        assert result.proposal_id == "proposal-1"
        assert result.deterministic_recommendation == "buy"
        assert result.id in [r.id for r in updated.ai_reasoning_results]
        assert result.id in [r.id for r in state.data.ai_reasoning_results]

    asyncio.run(_run())


def test_researcher_request_end_to_end_gets_a_real_cohort_id_distinct_from_sniper(monkeypatch: pytest.MonkeyPatch) -> None:
    """"Sniper AI Burn-In Cohort Identity 1.0" directive, Phase 9 — the
    equities entry point must ALSO get a real cohort identity (this is a
    shared, domain-agnostic capability, not a Sniper-only add-on), and it
    must never collide with a Sniper-domain cohort even under the same
    fake provider/model, because domain is one of the six real
    configuration axes."""
    from app.ai_context_builder import CONTEXT_BUILDER_VERSION as EQUITIES_CONTEXT_BUILDER_VERSION
    from app.ai_reasoning import REASONING_SCHEMA_VERSION, RESEARCHER_PROMPT_VERSION, compute_cohort_id

    monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider())

    async def _run() -> None:
        state = GameState()
        state.data = state.data.model_copy(update={"trade_proposals": [_proposal()]})
        _updated, result = await state.submit_ai_reasoning_request("proposal-1", role="researcher")
        assert result.status == "completed"
        expected_cohort_id = compute_cohort_id(
            domain="equities", provider="fake", model="fake-model",
            prompt_version=RESEARCHER_PROMPT_VERSION, context_version=EQUITIES_CONTEXT_BUILDER_VERSION,
            reasoning_schema_version=REASONING_SCHEMA_VERSION,
        )
        assert result.cohort_id == expected_cohort_id
        sniper_cohort_id = compute_cohort_id(
            domain="memecoin_sniper", provider="fake", model="fake-model",
            prompt_version=RESEARCHER_PROMPT_VERSION, context_version=EQUITIES_CONTEXT_BUILDER_VERSION,
            reasoning_schema_version=REASONING_SCHEMA_VERSION,
        )
        assert result.cohort_id != sniper_cohort_id

    asyncio.run(_run())


def test_devils_advocate_rotates_through_the_same_eligible_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.devils_advocate import ELIGIBLE_DEVILS_ADVOCATES

    monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider())

    async def _run() -> None:
        state = GameState()
        state.data = state.data.model_copy(update={"trade_proposals": [_proposal()]})
        _updated1, result1 = await state.submit_ai_reasoning_request("proposal-1", role="devils_advocate")
        assert result1.agent_id == ELIGIBLE_DEVILS_ADVOCATES[0]
        _updated2, result2 = await state.submit_ai_reasoning_request("proposal-1", role="devils_advocate")
        assert result2.agent_id == ELIGIBLE_DEVILS_ADVOCATES[1]

    asyncio.run(_run())


def test_devils_advocate_receives_the_prior_researcher_result_as_a_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    class _CapturingProvider(_FakeProvider):
        async def call(self, *, system_prompt: str, user_content: str) -> ProviderCallResult:
            captured["user_content"] = user_content
            return await super().call(system_prompt=system_prompt, user_content=user_content)

    monkeypatch.setattr(state_module, "get_ai_provider", lambda: _CapturingProvider())

    async def _run() -> None:
        state = GameState()
        state.data = state.data.model_copy(update={"trade_proposals": [_proposal()]})
        await state.submit_ai_reasoning_request("proposal-1", role="researcher")
        await state.submit_ai_reasoning_request("proposal-1", role="devils_advocate")
        sent = json.loads(captured["user_content"])
        assert "researcher_claim_to_verify_independently" in sent
        assert sent["researcher_claim_to_verify_independently"]["thesis"] == "A real thesis."

    asyncio.run(_run())


def test_max_ai_reasoning_results_caps_and_drops_the_oldest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider())

    async def _run() -> None:
        state = GameState()
        state.data = state.data.model_copy(update={"trade_proposals": [_proposal()]})
        oldest = [_existing_result(result_id=f"old-{i}") for i in range(MAX_AI_REASONING_RESULTS)]
        state.data = state.data.model_copy(update={"ai_reasoning_results": oldest})
        _updated, result = await state.submit_ai_reasoning_request("proposal-1", role="researcher")
        assert len(state.data.ai_reasoning_results) == MAX_AI_REASONING_RESULTS
        assert "old-0" not in [r.id for r in state.data.ai_reasoning_results]
        assert result.id in [r.id for r in state.data.ai_reasoning_results]

    asyncio.run(_run())


def _decision(*, decision_id: str, outcome: str) -> TradeDecision:
    return TradeDecision(
        id=decision_id, symbol="NEXA", outcome=outcome, votes=[], researchSummary="x", technicalSummary="x",  # type: ignore[arg-type]
        fundamentalSummary="x", riskSummary="x", supportingAgents=[], opposingAgents=[], confidence=60.0,
        finalReasoning="x", createdAt=_CREATED_AT,
    )


def _journal_entry(*, proposal_id: str, pnl: float) -> PaperTradeJournalEntry:
    return PaperTradeJournalEntry(
        id=f"journal-{proposal_id}", createdAt=_CREATED_AT, tradeId=f"trade-{proposal_id}", decisionId=f"decision-{proposal_id}",
        proposalId=proposal_id, symbol="NEXA", side="buy", quantity=2.0, entryPrice=100.0, exitPrice=125.0,
        pnl=25.0, pnlPct=25.0, maePct=-1.0, mfePct=26.0, durationMinutes=30, openedAt=_CREATED_AT, closedAt=_CREATED_AT,
    )


def test_refresh_outcomes_grades_a_pending_result_against_real_evidence() -> None:
    async def _run() -> None:
        state = GameState()
        pending = _existing_result(result_id="res-1", outcome_status="pending")
        decision = _decision(decision_id="decision-proposal-1", outcome="trade")
        journal = _journal_entry(proposal_id="proposal-1", pnl=25.0)
        state.data = state.data.model_copy(update={"ai_reasoning_results": [pending], "decisions": [decision], "paper_trade_journal": [journal]})
        updated = await state.refresh_ai_reasoning_outcomes()
        graded = next(r for r in updated.ai_reasoning_results if r.id == "res-1")
        assert graded.outcome_status == "evaluated"
        assert graded.outcome == "supported"
        assert graded.outcome_ref == journal.id

    asyncio.run(_run())


def test_refresh_outcomes_never_touches_an_already_evaluated_result() -> None:
    async def _run() -> None:
        state = GameState()
        evaluated = _existing_result(result_id="res-1", outcome_status="evaluated").model_copy(update={"outcome": "contradicted", "outcome_ref": "journal-old"})
        state.data = state.data.model_copy(update={"ai_reasoning_results": [evaluated]})
        updated = await state.refresh_ai_reasoning_outcomes()
        still = next(r for r in updated.ai_reasoning_results if r.id == "res-1")
        assert still.outcome == "contradicted"
        assert still.outcome_ref == "journal-old"

    asyncio.run(_run())


def test_refresh_outcomes_leaves_a_result_with_no_real_decision_yet_pending() -> None:
    async def _run() -> None:
        state = GameState()
        fresh = _existing_result(result_id="res-1", outcome_status="not_applicable")
        state.data = state.data.model_copy(update={"ai_reasoning_results": [fresh]})
        updated = await state.refresh_ai_reasoning_outcomes()
        still = next(r for r in updated.ai_reasoning_results if r.id == "res-1")
        assert still.outcome_status == "pending"
        assert still.outcome is None

    asyncio.run(_run())


def test_refresh_outcomes_never_touches_a_sniper_domain_result() -> None:
    """CEO directive "TradeTown — Memecoin Sniper AI 1.0" added a second
    domain onto this SAME shared `ai_reasoning_results` list. A Sniper
    result's `proposal_id` holds a real token mint, never a real
    TradeDecision id — this equities-only pass must skip it entirely
    (never misgrade it against unrelated equities decisions/journal
    entries), leaving it for `refresh_sniper_ai_reasoning_outcomes()`
    instead."""
    async def _run() -> None:
        state = GameState()
        sniper_result = _existing_result(result_id="res-sniper", outcome_status="not_applicable").model_copy(
            update={"domain": "memecoin_sniper", "proposal_id": "m" * 32}
        )
        state.data = state.data.model_copy(update={"ai_reasoning_results": [sniper_result]})
        updated = await state.refresh_ai_reasoning_outcomes()
        still = next(r for r in updated.ai_reasoning_results if r.id == "res-sniper")
        assert still.outcome_status == "not_applicable"
        assert still.outcome is None

    asyncio.run(_run())
