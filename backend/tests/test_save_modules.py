"""Covers app/save_modules.py — the v0.7 Save Architecture Redesign Phase 2
module map. The most important property here isn't any one behavior, it's
completeness: every GameSaveState field must belong to exactly one module,
enforced at import time by save_modules._validate_module_map() and pinned
again here so a future field addition without a module assignment fails a
test explicitly, not just a startup crash discovered later.
"""
from __future__ import annotations

from app.save_modules import ALL_MODULES, ARCHIVE_MODULES, CORE_MODULES, MODULE_FIELDS, assemble_state, module_defaults, split_state
from app.schemas import GameSaveState, TradeDecision
from app.state import default_state


def test_every_gamesavestate_field_is_assigned_to_exactly_one_module():
    mapped = [field for fields in MODULE_FIELDS.values() for field in fields]
    assert len(mapped) == len(set(mapped)), "a field is listed in more than one module"
    assert set(mapped) == set(GameSaveState.model_fields.keys())


def test_module_fields_keys_match_all_modules():
    assert set(MODULE_FIELDS.keys()) == set(ALL_MODULES)


def test_split_then_assemble_round_trips_real_state():
    state = default_state()
    assembled = assemble_state(split_state(state))
    assert assembled == state


def test_assemble_with_no_modules_falls_back_to_real_defaults_not_a_crash():
    assembled = assemble_state({})
    assert isinstance(assembled, GameSaveState)


def test_assemble_with_one_missing_module_only_defaults_that_module():
    state = default_state()
    modules = split_state(state)
    del modules["research"]  # simulates a module missing entirely (e.g. never persisted yet)

    assembled = assemble_state(modules)
    assert assembled.time == state.time  # every other module's real data survives
    assert len(assembled.research) == len(default_state().research)  # the missing module fell back to defaults


def test_module_defaults_returns_every_field_for_that_module():
    for module, fields in MODULE_FIELDS.items():
        defaults = module_defaults(module)
        assert set(defaults.keys()) == {_alias(f) for f in fields}


def _alias(field_name: str) -> str:
    field = GameSaveState.model_fields[field_name]
    return field.alias or field_name


# ---------------------------------------------------------------------------
# CEO directive "Controlled Paper Trading Readiness Audit + Burn-in 1.0" —
# root-cause regression for the previously-observed "decisions-count
# anomaly": GET /api/load (app/routers/save.py) deliberately filters
# split_state(snapshot) down to CORE_MODULES only, then re-assembles
# through assemble_state() — which fills any module NOT present with real,
# honest defaults (see test_assemble_with_one_missing_module_only_defaults_
# that_module above). `decisions`/`ceo_decisions`/`trade_proposals`/
# `risk_decisions` all live in the "trade_history" ARCHIVE module (see
# MODULE_FIELDS below), so GET /api/load ALWAYS returns them empty — not a
# bug, not data loss, not a race: this is that endpoint's own documented
# behavior (its own docstring: "the archive modules... come back empty
# here, not omitted or fabricated"). The real data is only ever reachable
# via GET /api/load/archive/{module} or the WebSocket tick broadcast. This
# test pins that architecture down as a checkable invariant so it can never
# silently regress into an actual bug (e.g. a future field move that
# forgets to update the router's own docstring), and so a live observer
# reading GET /api/load never mistakes this documented gap for evidence
# that decisions/proposals were lost or double-counted.
# ---------------------------------------------------------------------------


def _decision_record() -> TradeDecision:
    return TradeDecision(
        id="decision-1",
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
        orderId="pos-1",
        createdAt="2026-01-01T00:00:00+00:00",
    )


class TestArchiveModulesExcludedFromCoreLoad:
    def test_decisions_and_proposals_live_in_the_trade_history_archive_module(self) -> None:
        archive_only_fields = {"decisions", "ceo_decisions", "trade_proposals", "risk_decisions"}
        assert archive_only_fields <= set(MODULE_FIELDS["trade_history"])
        assert "trade_history" in ARCHIVE_MODULES
        assert "trade_history" not in CORE_MODULES

    def test_get_load_pipeline_returns_real_decisions_and_proposals_as_empty_by_design(self) -> None:
        # Simulates exactly what app/routers/save.py's GET /api/load does:
        # filter split_state() down to CORE_MODULES, then re-assemble.
        state = default_state().model_copy(
            update={
                "decisions": [_decision_record()],
                "trade_proposals": [],
            }
        )
        core_only = {module: data for module, data in split_state(state).items() if module in CORE_MODULES}
        loaded = assemble_state(core_only)
        # The real decision is genuinely gone from THIS response — by
        # design, never fabricated back, never silently dropped from the
        # underlying state (see the next test).
        assert loaded.decisions == []

    def test_the_real_data_is_never_actually_lost_only_excluded_from_this_one_response(self) -> None:
        # The SAME real snapshot's own split_state() output (what GET
        # /api/load/archive/{module} reads — see routers/save.py) still
        # carries the real record — proving app/routers/save.py's own
        # claim ("not omitted or fabricated") rather than just trusting it.
        state = default_state().model_copy(update={"decisions": [_decision_record()]})
        archive_view = split_state(state)["trade_history"]
        assert len(archive_view["decisions"]) == 1
        assert archive_view["decisions"][0]["id"] == "decision-1"

    def test_a_core_module_field_survives_the_same_core_only_load_pipeline(self) -> None:
        # Control: proves the filtering is real and selective (archive-only
        # excluded), not a symptom of a broader assemble_state() defect —
        # paper_portfolio lives in the CORE "company" module and must
        # survive the identical pipeline the two tests above exercise.
        state = default_state()
        portfolio = state.paper_portfolio.model_copy(update={"cash_balance": 42.0})
        state = state.model_copy(update={"paper_portfolio": portfolio})
        core_only = {module: data for module, data in split_state(state).items() if module in CORE_MODULES}
        loaded = assemble_state(core_only)
        assert loaded.paper_portfolio.cash_balance == 42.0
