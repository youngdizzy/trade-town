"""Covers app/nexus.py's real wiring of CEO directive "TradeTown —
Memecoin Sniper AI 1.0," Part XIX: a genuinely NEW SniperLesson (a real,
sample-gated statistical correlation from
app/memecoin_sniper.py::generate_lesson_from_history() — nothing
AI-generated) must be bridged into the SAME canonical institutional-
memory hub every other domain's lessons already promote into, tagged
domain="memecoin_sniper", through one real `nexus.tick()` call — the
exact same wiring convention every other lesson-promotion path in this
codebase already uses (see tests/test_knowledge_application_loop.py's
own nexus.tick() wiring tests)."""
from __future__ import annotations

from app.nexus import tick as nexus_tick
from app.schemas import SniperEngineConfig, SniperTrade, TimeState
from app.state import default_state

_NOW = "2026-01-01T00:00:00+00:00"


def _good_trade(i: int) -> SniperTrade:
    return SniperTrade(
        id=f"t{i}", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=1.1, stopPrice=0.88,
        targetPrice=1.55, sizeSol=1.0, riskSol=0.12, rMultiple=0.8, pnlSol=0.1, maxFavorableExcursionPct=10.0,
        maxAdverseExcursionPct=0.0, holdTimeSeconds=10.0, exitReason="take_profit", failureCodes=[], thesis="x", thesisValidated=True,
    )


def _timing_failure_trade(i: int) -> SniperTrade:
    return SniperTrade(
        id=f"tf{i}", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=0.95, stopPrice=0.88,
        targetPrice=1.55, sizeSol=1.0, riskSol=0.12, rMultiple=-0.4, pnlSol=-0.05, maxFavorableExcursionPct=0.0,
        maxAdverseExcursionPct=-5.0, holdTimeSeconds=70.0, exitReason="max_hold", failureCodes=["timing_failure"], thesis="x", thesisValidated=False,
    )


def test_a_new_sniper_lesson_is_promoted_into_institutional_memory_during_a_real_tick() -> None:
    # 15 good + 5 timing-failure = 20 total, a multiple of
    # tick_sniper_engine()'s own real `len(trade_history) % 20 == 0`
    # cadence check, and >= generate_lesson_from_history()'s own real
    # min_sample=20 floor with >=5 late_entries — the same real trade mix
    # test_memecoin_sniper.py's own direct-call test already established
    # produces a real lesson.
    trade_history = [_good_trade(i) for i in range(15)] + [_timing_failure_trade(i) for i in range(5)]
    state = default_state().model_copy(
        update={"sniper_trade_history": trade_history, "sniper_engine_config": SniperEngineConfig(status="paused")}  # type: ignore[arg-type]
    )
    result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)

    assert len(result.sniper_lessons) == 1
    lesson = result.sniper_lessons[0]

    promoted = [m for m in result.institutional_memory if m.event_ref == lesson.id]
    assert len(promoted) == 1
    assert promoted[0].domain == "memecoin_sniper"
    assert promoted[0].source == "research_lesson"
    assert promoted[0].observation == lesson.observation

    assert any(e.type == "lesson_created" and e.lesson_id == promoted[0].id for e in result.knowledge_events)


def test_a_lesson_already_on_file_is_never_re_promoted() -> None:
    """A second tick with the SAME trade_history (no new trades) must not
    regenerate/re-promote the same lesson — generate_lesson_from_history()
    itself already guards on `not any(existing.observation == lesson.observation ...)`;
    this test confirms the promotion wiring doesn't undo that guard."""
    trade_history = [_good_trade(i) for i in range(15)] + [_timing_failure_trade(i) for i in range(5)]
    state = default_state().model_copy(
        update={"sniper_trade_history": trade_history, "sniper_engine_config": SniperEngineConfig(status="paused")}  # type: ignore[arg-type]
    )
    once = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
    twice = nexus_tick(once, TimeState(day=2, hour=0, minute=5), 5)
    assert len(twice.sniper_lessons) == len(once.sniper_lessons)
    assert len([m for m in twice.institutional_memory if m.domain == "memecoin_sniper"]) == len(
        [m for m in once.institutional_memory if m.domain == "memecoin_sniper"]
    )
