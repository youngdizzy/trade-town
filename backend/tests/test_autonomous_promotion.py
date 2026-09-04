"""Covers app/autonomous_promotion.py — CEO directive "TradeTown —
Autonomous Quant Company 2.0," Phase 5 (Automatic Promotion). Every test
proves the real guarantee this module's own docstring makes: it invents
no new evidence gate (promote_challenger()'s own real `verdict ==
"challenger_recommended"` check is untouched and still authoritative),
it never promotes a comparison twice, and a comparison whose real
verdict is anything else is never promoted regardless of how this
module is called.
"""
from __future__ import annotations

import asyncio

from app.autonomous_promotion import AUTONOMOUS_PROMOTION_AGENT, apply_autonomous_promotions, find_promotable_comparisons
from app.champion_challenger import compare_champion_challenger
from app.schemas import ChallengerComparison, ChampionRecord
from app.state import GameState
from app.strategy_compiler import compile_strategy_text

_CHAMPION_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
_CHALLENGER_TEXT = "Buy when price closes above the 50 EMA and RSI is above 70, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."


def _real_comparison(*, comparison_id: str, verdict: str, strategy_family: str = "AP Family") -> ChallengerComparison:
    """One real ChallengerComparison from the real compare_champion_
    challenger() (real backtest, real evidence fields) with only the
    final `verdict` force-set for test determinism — the exact same
    lightweight convention tests/test_champion_challenger.py's own
    TestPromoteChallenger already establishes, reused here rather than
    hand-building a fabricated comparison from scratch."""
    champion_definition = compile_strategy_text(name=f"AP Champion {comparison_id}", source_text=_CHAMPION_TEXT)
    challenger_definition = compile_strategy_text(name=f"AP Challenger {comparison_id}", source_text=_CHALLENGER_TEXT)
    comparison = compare_champion_challenger(
        champion_definition,
        challenger_definition,
        strategy_family=strategy_family,
        hypothesis="RSI confirmation may cut false breakouts.",
        proposed_by="quant",
        comparison_id=comparison_id,
        generated_at="2024-01-01T00:00:00+00:00",
        symbols=["AAPL"],
    )
    return comparison.model_copy(update={"verdict": verdict})


class TestFindPromotableComparisons:
    def test_a_recommended_comparison_with_no_champion_record_is_promotable(self) -> None:
        comparison = _real_comparison(comparison_id="cmp-1", verdict="challenger_recommended")
        promotable = find_promotable_comparisons([comparison], [])
        assert promotable == [comparison]

    def test_a_champion_retained_comparison_is_never_promotable(self) -> None:
        comparison = _real_comparison(comparison_id="cmp-2", verdict="champion_retained")
        assert find_promotable_comparisons([comparison], []) == []

    def test_an_insufficient_evidence_comparison_is_never_promotable(self) -> None:
        comparison = _real_comparison(comparison_id="cmp-3", verdict="insufficient_evidence")
        assert find_promotable_comparisons([comparison], []) == []

    def test_an_already_promoted_comparison_is_not_promotable_again(self) -> None:
        comparison = _real_comparison(comparison_id="cmp-4", verdict="challenger_recommended")
        already = ChampionRecord(
            id="champion-cmp-4", strategyFamily="AP Family", definitionId=comparison.challenger_definition_id,
            definitionVersion=comparison.challenger_definition_version, sourceComparisonId="cmp-4",
            promotedBy="quant", reasoning="already handled", promotedAt="2024-01-01T00:00:00+00:00",
        )
        assert find_promotable_comparisons([comparison], [already]) == []

    def test_a_champion_record_with_no_source_comparison_never_blocks_an_unrelated_comparison(self) -> None:
        # The very first real champion ever recorded for a family has
        # source_comparison_id=None (see ChampionRecord's own docstring)
        # — must never be mistaken for "comparison id None is promoted."
        comparison = _real_comparison(comparison_id="cmp-5", verdict="challenger_recommended")
        first_ever = ChampionRecord(
            id="champion-0", strategyFamily="AP Family", definitionId="def-0", definitionVersion=1,
            sourceComparisonId=None, promotedBy="quant", reasoning="first ever", promotedAt="2024-01-01T00:00:00+00:00",
        )
        assert find_promotable_comparisons([comparison], [first_ever]) == [comparison]


class TestApplyAutonomousPromotions:
    def test_a_qualifying_comparison_is_really_promoted(self) -> None:
        comparison = _real_comparison(comparison_id="cmp-10", verdict="challenger_recommended")
        history, promoted = apply_autonomous_promotions([comparison], [])
        assert len(history) == 1
        assert history[0].source_comparison_id == "cmp-10"
        assert history[0].promoted_by == AUTONOMOUS_PROMOTION_AGENT
        assert promoted == [comparison]

    def test_a_non_qualifying_comparison_is_never_promoted(self) -> None:
        comparison = _real_comparison(comparison_id="cmp-11", verdict="insufficient_evidence")
        history, promoted = apply_autonomous_promotions([comparison], [])
        assert history == []
        assert promoted == []

    def test_reasoning_cites_the_real_comparison_reasoning_not_a_fabricated_one(self) -> None:
        comparison = _real_comparison(comparison_id="cmp-12", verdict="challenger_recommended")
        history, _ = apply_autonomous_promotions([comparison], [])
        assert comparison.reasoning in history[0].reasoning

    def test_input_lists_are_never_mutated(self) -> None:
        comparison = _real_comparison(comparison_id="cmp-13", verdict="challenger_recommended")
        comparisons_in = [comparison]
        history_in: list[ChampionRecord] = []
        apply_autonomous_promotions(comparisons_in, history_in)
        assert comparisons_in == [comparison]
        assert history_in == []

    def test_calling_twice_never_double_promotes(self) -> None:
        comparison = _real_comparison(comparison_id="cmp-14", verdict="challenger_recommended")
        history, _ = apply_autonomous_promotions([comparison], [])
        history_again, promoted_again = apply_autonomous_promotions([comparison], history)
        assert history_again == history
        assert promoted_again == []

    def test_deterministic_record_id_derived_from_the_real_comparison_id(self) -> None:
        comparison = _real_comparison(comparison_id="cmp-15", verdict="challenger_recommended")
        history, _ = apply_autonomous_promotions([comparison], [])
        assert history[0].id == "champion-cmp-15"


class TestAutonomousPromotionWiredIntoState:
    """Real, persisted end-to-end wiring through app/state.py's
    submit_champion_challenger_comparison() — mirrors test_champion_
    challenger.py's own TestChampionChallengerState convention."""

    def test_a_pending_qualifying_comparison_is_swept_and_promoted_when_a_new_one_is_submitted(self) -> None:
        state = GameState()
        pre_seeded = _real_comparison(comparison_id="cmp-pending", verdict="challenger_recommended", strategy_family="Pending Family")
        state.data = state.data.model_copy(update={"challenger_comparisons": [pre_seeded]})

        champion_definition = compile_strategy_text(name="Wired Champion", source_text=_CHAMPION_TEXT)
        challenger_definition = compile_strategy_text(name="Wired Challenger", source_text=_CHALLENGER_TEXT)
        saved, _new_comparison = asyncio.run(
            state.submit_champion_challenger_comparison(
                champion_definition, challenger_definition, strategy_family="Wired Family", hypothesis="h", proposed_by="quant", symbols=["AAPL"]
            )
        )
        promoted_ids = {r.source_comparison_id for r in saved.champion_history}
        assert "cmp-pending" in promoted_ids

    def test_manual_promotion_of_an_already_autonomously_promoted_comparison_is_refused(self) -> None:
        state = GameState()
        comparison = _real_comparison(comparison_id="cmp-dup", verdict="challenger_recommended", strategy_family="Dup Family")
        history, _ = apply_autonomous_promotions([comparison], [])
        state.data = state.data.model_copy(update={"challenger_comparisons": [comparison], "champion_history": history})
        try:
            asyncio.run(state.promote_champion_challenger(comparison_id="cmp-dup", promoted_by="cio", reasoning="a human tries anyway"))
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "already promoted" in str(exc)
