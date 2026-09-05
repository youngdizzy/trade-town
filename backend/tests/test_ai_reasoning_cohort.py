"""Covers `app/ai_reasoning.py`'s `compute_cohort_id()` and its wiring
into `build_reasoning_result()` — CEO directive "TradeTown — Memecoin
Sniper AI Burn-In Cohort Identity 1.0." This is a shared, domain-agnostic
capability (both equities and Sniper reuse the one
`build_reasoning_result()` function), so these tests exercise the shared
function directly rather than duplicating coverage per domain; domain-
specific end-to-end wiring is confirmed separately in
tests/test_state_sniper_ai_reasoning.py and
tests/test_sniper_ai_shadow_boundary.py.

Proves the directive's own explicit invariants (Phase 23): determinism,
differentiation on every one of the six configuration axes, independence
from candidate/timestamp/outcome/randomness, result-id/cohort-id
distinctness, immutability across outcome-refresh and restart, and that
no client- or model-supplied value can ever influence the computed
identity.
"""
from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass

from app.ai_provider import ProviderCallResult
from app.ai_reasoning import REASONING_SCHEMA_VERSION, build_reasoning_result, compute_cohort_id, run_researcher_reasoning
from app.routers.ai_reasoning import run_ai_reasoning
from app.routers.sniper_ai_reasoning import run_sniper_ai_reasoning
from app.schemas import AIEvidenceItem, AIEvidencePacket, GameSaveState
from app.sniper_ai_reasoning import run_sniper_analyst_reasoning

_CREATED_AT = "2026-01-01T00:00:00+00:00"

_BASE_CONFIG = dict(
    domain="memecoin_sniper", provider="anthropic", model="claude-sonnet-4-5",
    prompt_version="sniper-analyst-prompt-1.0", context_version="sniper-ai-context-builder-1.0",
    reasoning_schema_version=REASONING_SCHEMA_VERSION,
)


def _packet(*, packet_id: str = "pkt-1", task: str = "Evaluate MEWPEPE", proposal_id: str = "m" * 32, created_at: str = _CREATED_AT) -> AIEvidencePacket:
    return AIEvidencePacket(
        id=packet_id, task=task, agentRole="sniper_analyst", domain="memecoin_sniper", proposalId=proposal_id,
        symbol="MEWPEPE", knowledgeCutoffSimMinutes=0,
        items=[AIEvidenceItem(id="fact-symbol", kind="fact", label="Symbol", detail="MEWPEPE", asOfSimMinutes=0)],
        knownLimitations=["test limitation"], contextBuilderVersion="sniper-ai-context-builder-1.0", createdAt=created_at,
    )


def _equities_packet() -> AIEvidencePacket:
    return AIEvidencePacket(
        id="pkt-eq-1", task="Evaluate NEXA", agentRole="researcher", domain="equities", proposalId="proposal-1",
        symbol="NEXA", knowledgeCutoffSimMinutes=0,
        items=[AIEvidenceItem(id="fact-symbol", kind="fact", label="Symbol", detail="NEXA", asOfSimMinutes=0)],
        knownLimitations=["test limitation"], contextBuilderVersion="ai-context-builder-1.0", createdAt=_CREATED_AT,
    )


def _ok_call_result(*, provider: str = "anthropic", model: str = "claude-sonnet-4-5", payload: dict[str, object] | None = None) -> ProviderCallResult:
    payload = payload if payload is not None else {"thesis": "A real thesis.", "recommendation": "buy"}
    return ProviderCallResult(status="ok", provider=provider, model=model, raw_text=json.dumps(payload), input_tokens=1, output_tokens=1, latency_ms=1.0, detail=None)


def _completed_result(**overrides: object) -> object:
    call_result = overrides.pop("call_result", None) or _ok_call_result()
    packet = overrides.pop("packet", None) or _packet()
    kwargs: dict[str, object] = dict(
        call_result=call_result, packet=packet, agent_id="quant", role="sniper_analyst", domain="memecoin_sniper",
        task=packet.task, prompt_version="sniper-analyst-prompt-1.0", deterministic_recommendation=None,
    )
    kwargs.update(overrides)
    return build_reasoning_result(**kwargs)  # type: ignore[arg-type]


class TestCohortDeterminism:
    def test_same_configuration_produces_the_same_cohort_id(self) -> None:
        assert compute_cohort_id(**_BASE_CONFIG) == compute_cohort_id(**_BASE_CONFIG)

    def test_different_domain_produces_a_different_cohort_id(self) -> None:
        assert compute_cohort_id(**{**_BASE_CONFIG, "domain": "equities"}) != compute_cohort_id(**_BASE_CONFIG)

    def test_different_provider_produces_a_different_cohort_id(self) -> None:
        assert compute_cohort_id(**{**_BASE_CONFIG, "provider": "unavailable"}) != compute_cohort_id(**_BASE_CONFIG)

    def test_different_model_produces_a_different_cohort_id(self) -> None:
        assert compute_cohort_id(**{**_BASE_CONFIG, "model": "claude-opus-4"}) != compute_cohort_id(**_BASE_CONFIG)

    def test_different_prompt_version_produces_a_different_cohort_id(self) -> None:
        assert compute_cohort_id(**{**_BASE_CONFIG, "prompt_version": "sniper-analyst-prompt-2.0"}) != compute_cohort_id(**_BASE_CONFIG)

    def test_different_context_version_produces_a_different_cohort_id(self) -> None:
        assert compute_cohort_id(**{**_BASE_CONFIG, "context_version": "sniper-ai-context-builder-2.0"}) != compute_cohort_id(**_BASE_CONFIG)

    def test_different_reasoning_schema_version_produces_a_different_cohort_id(self) -> None:
        assert compute_cohort_id(**{**_BASE_CONFIG, "reasoning_schema_version": "ai-reasoning-schema-2.0"}) != compute_cohort_id(**_BASE_CONFIG)

    def test_cohort_id_is_a_stable_readable_string_not_a_raw_uuid(self) -> None:
        cohort_id = compute_cohort_id(**_BASE_CONFIG)
        assert cohort_id.startswith("cohort-")
        # Deterministic across repeated calls in the same process — not
        # random.uuid4()-derived, not time-seeded.
        assert cohort_id == compute_cohort_id(**_BASE_CONFIG)


class TestBuildReasoningResultCohortWiring:
    def test_a_completed_result_gets_a_real_cohort_id_and_constituent_versions(self) -> None:
        result = _completed_result()
        assert result.status == "completed"
        assert result.cohort_id == compute_cohort_id(
            domain="memecoin_sniper", provider="anthropic", model="claude-sonnet-4-5",
            prompt_version="sniper-analyst-prompt-1.0", context_version="sniper-ai-context-builder-1.0",
            reasoning_schema_version=REASONING_SCHEMA_VERSION,
        )
        assert result.context_builder_version == "sniper-ai-context-builder-1.0"
        assert result.reasoning_schema_version == REASONING_SCHEMA_VERSION

    def test_provider_unavailable_result_has_no_cohort_identity(self) -> None:
        call_result = ProviderCallResult(status="unavailable", provider="unavailable", model=None, raw_text=None, input_tokens=None, output_tokens=None, latency_ms=0.0, detail="no key")
        result = _completed_result(call_result=call_result)
        assert result.status == "provider_unavailable"
        assert result.cohort_id is None
        assert result.context_builder_version is None
        assert result.reasoning_schema_version is None

    def test_provider_timeout_result_has_no_cohort_identity(self) -> None:
        call_result = ProviderCallResult(status="timeout", provider="anthropic", model="claude-sonnet-4-5", raw_text=None, input_tokens=None, output_tokens=None, latency_ms=30000.0, detail="timed out")
        result = _completed_result(call_result=call_result)
        assert result.status == "provider_timeout"
        assert result.cohort_id is None

    def test_provider_error_result_has_no_cohort_identity(self) -> None:
        call_result = ProviderCallResult(status="error", provider="anthropic", model="claude-sonnet-4-5", raw_text=None, input_tokens=None, output_tokens=None, latency_ms=1.0, detail="HTTP 500")
        result = _completed_result(call_result=call_result)
        assert result.status == "provider_error"
        assert result.cohort_id is None

    def test_invalid_json_output_has_no_cohort_identity(self) -> None:
        call_result = ProviderCallResult(status="ok", provider="anthropic", model="claude-sonnet-4-5", raw_text="not json", input_tokens=1, output_tokens=1, latency_ms=1.0, detail=None)
        result = _completed_result(call_result=call_result)
        assert result.status == "invalid_output"
        assert result.cohort_id is None

    def test_cohort_id_is_independent_of_candidate_proposal_task_and_timestamp(self) -> None:
        """Two results under the identical real configuration but a
        completely different candidate/proposal/task/packet-creation-time
        must share the same cohort — the cohort is configuration
        identity, never candidate identity (Phase 11)."""
        result_a = _completed_result(packet=_packet(packet_id="pkt-a", task="Evaluate MEWPEPE", proposal_id="m" * 32, created_at="2026-01-01T00:00:00+00:00"))
        result_b = _completed_result(packet=_packet(packet_id="pkt-b", task="Evaluate a totally different token DOGE2", proposal_id="d" * 32, created_at="2026-06-15T12:34:56+00:00"))
        assert result_a.cohort_id == result_b.cohort_id
        assert result_a.proposal_id != result_b.proposal_id
        assert result_a.task != result_b.task

    def test_result_id_is_distinct_from_cohort_id_and_from_every_other_result_id(self) -> None:
        """Phase 12: resultId != cohortId, and many results share one
        cohort while each keeps its own unique result id."""
        results = [_completed_result() for _ in range(10)]
        result_ids = {r.id for r in results}
        cohort_ids = {r.cohort_id for r in results}
        assert len(result_ids) == 10
        assert cohort_ids == {results[0].cohort_id}
        assert all(r.id != r.cohort_id for r in results)

    def test_model_supplied_cohort_fields_in_the_raw_response_are_never_used(self) -> None:
        """Security/trust-boundary (Phase 14): even if the model's own
        JSON output contains keys shaped like cohort/version fields, they
        are never read — `build_reasoning_result()` has no code path that
        looks them up from `parsed`."""
        hostile_payload = {
            "thesis": "A real thesis.", "recommendation": "buy",
            "cohort_id": "cohort-attacker-controlled", "cohortId": "cohort-attacker-controlled",
            "context_builder_version": "fake-context-version", "contextBuilderVersion": "fake-context-version",
            "reasoning_schema_version": "fake-schema-version", "reasoningSchemaVersion": "fake-schema-version",
            "provider": "fake-provider", "model": "fake-model",
        }
        result = _completed_result(call_result=_ok_call_result(payload=hostile_payload))
        assert result.cohort_id != "cohort-attacker-controlled"
        assert result.context_builder_version != "fake-context-version"
        assert result.reasoning_schema_version != "fake-schema-version"
        assert result.model_provider == "anthropic"
        assert result.model_version == "claude-sonnet-4-5"
        assert result.cohort_id == compute_cohort_id(
            domain="memecoin_sniper", provider="anthropic", model="claude-sonnet-4-5",
            prompt_version="sniper-analyst-prompt-1.0", context_version="sniper-ai-context-builder-1.0",
            reasoning_schema_version=REASONING_SCHEMA_VERSION,
        )

    def test_no_public_reasoning_function_accepts_a_cohort_related_parameter(self) -> None:
        """Phase 14: no caller-facing signature — including the two real
        HTTP-triggered router endpoints (`POST /api/ai-reasoning/run`,
        `POST /api/sniper/ai-reasoning/run`) themselves, not just their
        internal callees — exposes any parameter a caller could use to
        set/override cohort_id/context_builder_version/
        reasoning_schema_version. The backend derives all three entirely
        server-side; a malicious request body/query string has no field
        name that could ever reach any of these functions' parameters."""
        cohort_param_names = {"cohort_id", "cohortId", "context_builder_version", "contextBuilderVersion", "reasoning_schema_version", "reasoningSchemaVersion"}
        for fn in (build_reasoning_result, run_researcher_reasoning, run_sniper_analyst_reasoning, run_ai_reasoning, run_sniper_ai_reasoning):
            params = set(inspect.signature(fn).parameters)
            assert not (params & cohort_param_names), f"{fn.__name__} unexpectedly accepts a cohort-related parameter"

    def test_sniper_and_equities_share_no_cohort_even_with_matching_provider_and_model(self) -> None:
        """Phase 9/23 Invariant 10: domain isolation extends to cohort
        identity — the SAME provider/model, run under each domain's own
        real prompt/context version, must never collide."""
        sniper_result = _completed_result()
        equities_result = build_reasoning_result(
            call_result=_ok_call_result(), packet=_equities_packet(), agent_id="nova", role="researcher", domain="equities",
            task="Evaluate NEXA", prompt_version="researcher-prompt-1.0", deterministic_recommendation=None,
        )
        assert sniper_result.domain == "memecoin_sniper"
        assert equities_result.domain == "equities"
        assert sniper_result.cohort_id != equities_result.cohort_id

    def test_concurrent_calls_under_identical_configuration_share_one_cohort(self) -> None:
        """Phase 20: concurrency must never make the cohort computation
        race-dependent — it is a pure function of already-known inputs,
        never derived from call order or timing."""
        async def _run() -> list[object]:
            return await asyncio.gather(*[_async_completed_result() for _ in range(5)])

        results = asyncio.run(_run())
        result_ids = {r.id for r in results}
        cohort_ids = {r.cohort_id for r in results}
        assert len(result_ids) == 5
        assert len(cohort_ids) == 1

    def test_outcome_refresh_style_update_never_touches_cohort_fields(self) -> None:
        """Mirrors the exact real mutation shape
        `refresh_sniper_ai_reasoning_outcomes()`/`refresh_ai_reasoning_outcomes()`
        perform (`model_copy(update={"outcome_status": ..., ...})`) —
        proves that path structurally cannot alter cohort identity since
        it never appears in either function's own update dict, and even a
        direct model_copy that only touches outcome fields leaves cohort
        fields byte-identical."""
        original = _completed_result()
        refreshed = original.model_copy(update={"outcome_status": "evaluated", "outcome": "supported", "outcome_ref": "trade-1", "evaluated_at": _CREATED_AT})
        assert refreshed.cohort_id == original.cohort_id
        assert refreshed.context_builder_version == original.context_builder_version
        assert refreshed.reasoning_schema_version == original.reasoning_schema_version

    def test_cohort_fields_survive_a_simulated_save_reload_cycle(self) -> None:
        """Phase 18: restart must not recompute or discard the cohort —
        it is a real persisted fact, not a derived-on-read view."""
        result = _completed_result()
        dumped = result.model_dump(by_alias=True)
        from app.schemas import AIReasoningResult

        reloaded = AIReasoningResult.model_validate(dumped)
        assert reloaded.cohort_id == result.cohort_id
        assert reloaded.context_builder_version == result.context_builder_version
        assert reloaded.reasoning_schema_version == result.reasoning_schema_version

    def test_a_historical_cohort_is_not_recomputed_from_todays_live_constants_on_reload(self) -> None:
        """Phase 5/24: a save containing a result computed under an OLD
        prompt/context version (simulating a since-bumped constant) must
        reload with that exact historical identity intact — never
        silently re-derived from whatever the CURRENT constants are."""
        from app.state import default_state

        historical_cohort_id = compute_cohort_id(
            domain="memecoin_sniper", provider="anthropic", model="claude-3-5-sonnet-legacy",
            prompt_version="sniper-analyst-prompt-0.1-legacy", context_version="sniper-ai-context-builder-0.1-legacy",
            reasoning_schema_version="ai-reasoning-schema-0.1-legacy",
        )
        state = default_state()
        dumped = state.model_dump(by_alias=True)
        historical_result = {
            "id": "res-historical", "agentId": "quant", "role": "sniper_analyst", "domain": "memecoin_sniper",
            "task": "x", "evidencePacketId": "pkt-old", "modelProvider": "anthropic", "modelVersion": "claude-3-5-sonnet-legacy",
            "promptVersion": "sniper-analyst-prompt-0.1-legacy", "contextBuilderVersion": "sniper-ai-context-builder-0.1-legacy",
            "reasoningSchemaVersion": "ai-reasoning-schema-0.1-legacy", "cohortId": historical_cohort_id,
            "status": "completed", "thesis": "historical thesis", "createdAt": _CREATED_AT,
        }
        dumped["aiReasoningResults"] = [historical_result]
        reloaded = GameSaveState.model_validate(dumped)
        loaded_result = reloaded.ai_reasoning_results[0]
        assert loaded_result.cohort_id == historical_cohort_id
        assert loaded_result.cohort_id != compute_cohort_id(
            domain="memecoin_sniper", provider="anthropic", model="claude-sonnet-4-5",
            prompt_version="sniper-analyst-prompt-1.0", context_version="sniper-ai-context-builder-1.0",
            reasoning_schema_version=REASONING_SCHEMA_VERSION,
        )

    def test_old_save_predating_this_field_defaults_all_three_to_none(self) -> None:
        from app.state import default_state

        state = default_state()
        dumped = state.model_dump(by_alias=True)
        old_result = {
            "id": "res-old", "agentId": "quant", "role": "sniper_analyst", "domain": "memecoin_sniper", "task": "x",
            "evidencePacketId": "pkt-old", "modelProvider": "fake", "modelVersion": "fake", "promptVersion": "v1",
            "status": "completed", "thesis": "old thesis", "createdAt": _CREATED_AT,
        }
        dumped["aiReasoningResults"] = [old_result]
        reloaded = GameSaveState.model_validate(dumped)
        loaded_result = reloaded.ai_reasoning_results[0]
        assert loaded_result.cohort_id is None
        assert loaded_result.context_builder_version is None
        assert loaded_result.reasoning_schema_version is None


@dataclass
class _FakeProvider:
    provider_name: str = "anthropic"

    async def call(self, *, system_prompt: str, user_content: str) -> ProviderCallResult:
        return _ok_call_result()


async def _async_completed_result() -> object:
    return await run_sniper_analyst_reasoning(_packet(), provider=_FakeProvider())
