"""Covers app/research_experiment.py — CEO directive "Professional Quant
Trading Firm — Quant Intelligence + Market Analysis Completion Phase
(Next Research + Validation Pass)," item 11. Assertions check internal
consistency and the real conclusion-synthesis rule, never a specific
backtest outcome (the same house convention
TestRunEmaPullbackResearchIntegration documents in
tests/test_ema_pullback_research.py).
"""
from __future__ import annotations

from app.research_experiment import _synthesize_conclusion, run_research_experiment
from app.strategy_compiler import compile_strategy_text

_CEO_TEXT = (
    "Buy when price closes above the 50 EMA, then wait for at least two bearish candles, "
    "then enter when price closes above the previous swing high. Place the stop at the "
    "Chandelier Stop and target 2R."
)


class TestSynthesizeConclusion:
    def test_a_look_ahead_violation_always_overrides_everything_else(self) -> None:
        conclusion = _synthesize_conclusion(("approved", "stable", "robust", "cost_resilient", "violations_found"))
        assert conclusion.startswith("INVALID")

    def test_a_rejected_model_validation_overrides_everything_but_a_real_leak(self) -> None:
        conclusion = _synthesize_conclusion(("rejected", "stable", "robust", "cost_resilient", "clean"))
        assert conclusion.startswith("REJECTED")

    def test_missing_evidence_anywhere_reads_insufficient_never_a_silent_pass(self) -> None:
        conclusion = _synthesize_conclusion(("needs_more_evidence", "stable", "robust", "cost_resilient", "clean"))
        assert conclusion.startswith("INSUFFICIENT EVIDENCE")
        assert "model validation" in conclusion

    def test_walk_forward_insufficient_data_also_reads_insufficient_evidence(self) -> None:
        conclusion = _synthesize_conclusion(("approved", "insufficient_data", "robust", "cost_resilient", "clean"))
        assert conclusion.startswith("INSUFFICIENT EVIDENCE")
        assert "walk-forward" in conclusion

    def test_any_fragile_axis_with_full_evidence_elsewhere_reads_fragile(self) -> None:
        conclusion = _synthesize_conclusion(("approved", "unstable", "robust", "cost_resilient", "clean"))
        assert conclusion.startswith("FRAGILE")
        assert "walk-forward stability" in conclusion

    def test_multiple_fragile_axes_are_all_named(self) -> None:
        conclusion = _synthesize_conclusion(("approved", "unstable", "fragile", "cost_sensitive", "clean"))
        assert conclusion.startswith("FRAGILE")
        assert "walk-forward stability" in conclusion
        assert "parameter robustness" in conclusion
        assert "cost resilience" in conclusion

    def test_every_real_axis_favorable_reads_credible_preliminary_evidence(self) -> None:
        conclusion = _synthesize_conclusion(("approved", "stable", "robust", "cost_resilient", "clean"))
        assert conclusion.startswith("CREDIBLE")
        assert "NOT a claim of certainty" in conclusion

    def test_needs_more_evidence_model_validation_alongside_a_look_ahead_violation_still_reads_invalid(self) -> None:
        conclusion = _synthesize_conclusion((None, "insufficient_data", "insufficient_data", "insufficient_data", "violations_found"))
        assert conclusion.startswith("INVALID")


class TestRunResearchExperimentIntegration:
    def test_the_record_bundles_every_real_axis_for_the_same_definition(self) -> None:
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL", "MSFT"], candles_per_symbol=6000)
        assert record.definition_id == definition.id
        assert record.definition_version == definition.version
        assert record.source_text == definition.source_text
        assert record.backtest.definition_id == definition.id
        assert record.walk_forward.definition_id == definition.id
        assert record.parameter_sensitivity.definition_id == definition.id
        assert record.cost_sensitivity.definition_id == definition.id
        assert record.look_ahead_audit.definition_id == definition.id
        assert record.conclusion  # a real, non-empty synthesized conclusion
        assert record.symbols_tested == ["AAPL", "MSFT"]
        # Feature 39 — overfitting_diagnosis is a real relabeling of the same three verdicts.
        assert record.overfitting_diagnosis.walk_forward_verdict == record.walk_forward.verdict
        assert record.overfitting_diagnosis.parameter_sensitivity_verdict == record.parameter_sensitivity.verdict
        assert record.overfitting_diagnosis.cost_sensitivity_verdict == record.cost_sensitivity.verdict

    def test_an_invalid_definition_still_produces_a_full_record_with_every_axis_honestly_refusing(self) -> None:
        definition = compile_strategy_text(name="x", source_text="Buy when the moon is full.")
        record = run_research_experiment(definition, symbols=["AAPL"])
        assert record.backtest.overall.trade_count == 0
        assert record.walk_forward.verdict == "insufficient_data"
        assert record.parameter_sensitivity.verdict == "insufficient_data"
        assert record.cost_sensitivity.verdict == "insufficient_data"
        assert record.look_ahead_audit.verdict == "insufficient_data"
        assert record.conclusion  # still a real, honest conclusion, never a crash
        assert record.overfitting_diagnosis.verdict == "insufficient_data"

    def test_the_conclusion_is_consistent_with_the_records_own_real_verdicts(self) -> None:
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL", "MSFT", "SPY", "QQQ"], candles_per_symbol=6000)
        model_verdict = record.backtest.model_validation.verdict if record.backtest.model_validation is not None else None
        expected = _synthesize_conclusion((model_verdict, record.walk_forward.verdict, record.parameter_sensitivity.verdict, record.cost_sensitivity.verdict, record.look_ahead_audit.verdict))
        assert record.conclusion == expected
