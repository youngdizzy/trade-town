"""Covers app/save_modules.py — the v0.7 Save Architecture Redesign Phase 2
module map. The most important property here isn't any one behavior, it's
completeness: every GameSaveState field must belong to exactly one module,
enforced at import time by save_modules._validate_module_map() and pinned
again here so a future field addition without a module assignment fails a
test explicitly, not just a startup crash discovered later.
"""
from __future__ import annotations

from app.save_modules import ALL_MODULES, MODULE_FIELDS, assemble_state, module_defaults, split_state
from app.schemas import GameSaveState
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
