"""Covers "Memecoin Sniper AI Shadow Reasoning Burn-In 1.0" — Part IV/
XXIV's explicit request for structural negative-space tests proving the
Sniper AI's shadow-only boundary: tests that would FAIL if someone later
accidentally gave the Sniper AI reasoning pathway any execution/mutation
capability. These are deliberately NOT duplicates of the shared
build_reasoning_result() adversarial coverage already in
tests/test_ai_reasoning.py (invalid JSON/citations/confidence/hostile
text) — Sniper reuses that function verbatim, so it inherits that
protection automatically (see tests/test_sniper_ai_reasoning.py's own
test_result_reuses_the_shared_citation_validation). This file instead
proves the END-TO-END real entry point (GameState
.submit_sniper_ai_reasoning_request()) cannot mutate any authoritative
Sniper state, survives concurrent/duplicate/restart scenarios safely,
and never leaks provider secrets anywhere a real caller could observe."""
from __future__ import annotations

import asyncio

import pytest

import app.state as state_module
from app.ai_provider import AI_PROVIDER_API_KEY_ENV_VAR, AnthropicAIProvider, ProviderCallResult, get_ai_provider
from app.schemas import AIReasoningResult, SniperCandidate, SniperEngineConfig, SniperScoreComponent
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


class _FakeProvider:
    provider_name = "fake"

    def __init__(self, raw_text: str = '{"thesis": "A real thesis.", "recommendation": "buy", "confidence": 70}') -> None:
        self._raw_text = raw_text
        self.call_count = 0

    async def call(self, *, system_prompt: str, user_content: str) -> ProviderCallResult:
        self.call_count += 1
        return ProviderCallResult(status="ok", provider="fake", model="fake-model", raw_text=self._raw_text, input_tokens=1, output_tokens=1, latency_ms=1.0, detail=None)


class TestExecutionAndRiskBoundary:
    """Part XXIV — negative-space proof: a real reasoning request changes
    NOTHING about authoritative Sniper state except appending one
    non-authoritative AIReasoningResult."""

    def test_reasoning_request_leaves_risk_state_byte_identical(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider())

        async def _run() -> None:
            state = GameState()
            candidate = _candidate()
            state.data = state.data.model_copy(update={"sniper_candidates": [candidate]})
            risk_before = state.data.sniper_risk_state
            await state.submit_sniper_ai_reasoning_request(candidate.id)
            assert state.data.sniper_risk_state == risk_before

        asyncio.run(_run())

    def test_reasoning_request_leaves_engine_config_byte_identical(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider())

        async def _run() -> None:
            state = GameState()
            candidate = _candidate()
            config = SniperEngineConfig(status="running", mode="dry_run", turbo=True, copyTradingEnabled=True)  # type: ignore[arg-type]
            state.data = state.data.model_copy(update={"sniper_candidates": [candidate], "sniper_engine_config": config})
            await state.submit_sniper_ai_reasoning_request(candidate.id)
            assert state.data.sniper_engine_config == config

        asyncio.run(_run())

    def test_reasoning_request_creates_no_position_and_no_trade(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider('{"thesis": "Strong buy signal.", "recommendation": "buy", "confidence": 99}'))

        async def _run() -> None:
            state = GameState()
            candidate = _candidate()
            state.data = state.data.model_copy(update={"sniper_candidates": [candidate]})
            await state.submit_sniper_ai_reasoning_request(candidate.id)
            assert state.data.sniper_positions == []
            assert state.data.sniper_trade_history == []

        asyncio.run(_run())

    def test_reasoning_request_leaves_wallets_untouched(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider())

        async def _run() -> None:
            state = GameState()
            candidate = _candidate()
            wallets_before = list(state.data.sniper_wallets)
            state.data = state.data.model_copy(update={"sniper_candidates": [candidate]})
            await state.submit_sniper_ai_reasoning_request(candidate.id)
            assert state.data.sniper_wallets == wallets_before

        asyncio.run(_run())

    def test_reasoning_request_cannot_arm_live_trading(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Even an AI recommendation of "buy" with maximum confidence must
        never change live-arming status — that is governed exclusively by
        real RPC/Jupiter/wallet/validation prerequisites, never by any AI
        opinion."""
        monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider('{"thesis": "Strong buy signal.", "recommendation": "buy", "confidence": 100}'))

        async def _run() -> None:
            state = GameState()
            candidate = _candidate()
            state.data = state.data.model_copy(update={"sniper_candidates": [candidate]})
            _updated, result = await state.submit_sniper_ai_reasoning_request(candidate.id)
            assert result.recommendation == "buy"
            # The AI result itself carries no live-arming field and
            # exposes no code path back into evaluate_live_arming() —
            # structurally impossible for it to arm live trading.
            assert not hasattr(result, "live_arming")
            assert not hasattr(result, "liveArming")

        asyncio.run(_run())

    def test_only_the_ai_reasoning_results_list_changes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The strongest single assertion: diff the ENTIRE GameSaveState
        before/after, excluding only the one field this call is
        documented to append to."""
        monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider())

        async def _run() -> None:
            state = GameState()
            candidate = _candidate()
            state.data = state.data.model_copy(update={"sniper_candidates": [candidate]})
            before = state.data.model_dump(exclude={"ai_reasoning_results", "updated_at"})
            await state.submit_sniper_ai_reasoning_request(candidate.id)
            after = state.data.model_dump(exclude={"ai_reasoning_results", "updated_at"})
            assert before == after

        asyncio.run(_run())


class TestConcurrencyAndDuplicateSafety:
    """Part XXI/XXVIII item 22 — two concurrent requests for the same
    candidate must not corrupt state; each produces its own real,
    independently-valid result, never a merged/duplicated/corrupted one."""

    def test_two_concurrent_requests_for_the_same_candidate_both_complete_independently(self, monkeypatch: pytest.MonkeyPatch) -> None:
        provider = _FakeProvider()
        monkeypatch.setattr(state_module, "get_ai_provider", lambda: provider)

        async def _run() -> None:
            state = GameState()
            candidate = _candidate()
            state.data = state.data.model_copy(update={"sniper_candidates": [candidate]})
            (_s1, r1), (_s2, r2) = await asyncio.gather(
                state.submit_sniper_ai_reasoning_request(candidate.id),
                state.submit_sniper_ai_reasoning_request(candidate.id),
            )
            assert r1.id != r2.id
            assert r1.status == "completed"
            assert r2.status == "completed"
            assert len(state.data.ai_reasoning_results) == 2

        asyncio.run(_run())


class TestPersistenceAndRestartSafety:
    """Part XXX — save/restart must never corrupt or fabricate an
    AIReasoningResult; a genuinely interrupted request must never look
    like a successful one."""

    def test_result_survives_a_simulated_save_reload_cycle(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(state_module, "get_ai_provider", lambda: _FakeProvider())

        async def _run() -> None:
            state = GameState()
            candidate = _candidate()
            state.data = state.data.model_copy(update={"sniper_candidates": [candidate]})
            _updated, result = await state.submit_sniper_ai_reasoning_request(candidate.id)
            dumped = state.data.model_dump(by_alias=True)
            from app.schemas import GameSaveState

            reloaded = GameSaveState.model_validate(dumped)
            reloaded_result = next(r for r in reloaded.ai_reasoning_results if r.id == result.id)
            assert reloaded_result == result

        asyncio.run(_run())

    def test_old_save_missing_the_new_field_defaults_honestly_false(self) -> None:
        """A save persisted before this pass added
        requested_after_outcome_known must load cleanly, defaulting to
        False (never crash, never a fabricated True)."""
        from app.state import default_state

        state = default_state()
        dumped = state.model_dump(by_alias=True)
        # Simulate an old save with a pre-existing result lacking the new field.
        old_result = {
            "id": "res-old", "agentId": "quant", "role": "sniper_analyst", "domain": "memecoin_sniper", "task": "x",
            "evidencePacketId": "pkt-old", "modelProvider": "fake", "modelVersion": "fake", "promptVersion": "v1",
            "status": "provider_unavailable", "createdAt": _CREATED_AT,
        }
        dumped["aiReasoningResults"] = [old_result]
        from app.schemas import GameSaveState

        reloaded = GameSaveState.model_validate(dumped)
        assert reloaded.ai_reasoning_results[0].requested_after_outcome_known is False


class TestSecretsNeverLeak:
    """Part III — the provider API key must never reach any field a real
    caller (frontend, another AI reasoning result, a log line built from
    these objects) could observe."""

    def test_provider_call_result_has_no_credential_field(self) -> None:
        result = ProviderCallResult(status="ok", provider="anthropic", model="m", raw_text="{}", input_tokens=1, output_tokens=1, latency_ms=1.0, detail=None)
        fields = set(result.__dataclass_fields__.keys())
        assert not any("key" in f.lower() or "secret" in f.lower() or "token" in f.lower() and "input" not in f.lower() and "output" not in f.lower() for f in fields if f not in {"input_tokens", "output_tokens"})

    def test_ai_reasoning_result_schema_has_no_credential_field(self) -> None:
        fields = set(AIReasoningResult.model_fields.keys())
        assert not any("api_key" in f or "secret" in f or "credential" in f for f in fields)

    def test_get_ai_provider_reads_key_only_from_environment_never_from_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(AI_PROVIDER_API_KEY_ENV_VAR, "sk-test-fake-key-never-real")
        provider = get_ai_provider()
        assert isinstance(provider, AnthropicAIProvider)
        # The key lives only in a private instance attribute, never a
        # public field that model_dump()/repr() could surface into a log.
        assert "api_key" not in AnthropicAIProvider.__dict__.get("__annotations__", {})

    def test_unavailable_when_env_var_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(AI_PROVIDER_API_KEY_ENV_VAR, raising=False)
        provider = get_ai_provider()
        assert provider.provider_name == "unavailable"
