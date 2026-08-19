"""app/overfitting_diagnostics.py — CEO directive "Professional Quant
Firm Phase," Feature 39: a real, deterministic classifier that relabels
three already-real, already-tested verdicts (walk-forward stability,
parameter-sensitivity robustness, cost-sensitivity resilience) into the
directive's own requested six-term vocabulary: ROBUST / FRAGILE /
INSUFFICIENT_DATA / OVERFIT_SUSPECTED / OOS_FAILURE / PENDING_VALIDATION.

RESEARCH FIRST. app/walk_forward.py, app/parameter_sensitivity.py, and
app/cost_sensitivity.py already each compute a real, independent verdict
over their own real evidence — this module invents no new statistic, no
new backtest, no new threshold. It exists purely because those three
verdicts use three different words ("unstable"/"fragile"/
"cost_sensitive") for overlapping ideas, and a CEO or agent reading the
directive's own requested vocabulary should not have to reconcile that
by hand every time.

THE CLASSIFICATION RULE, DISCLOSED AND DETERMINISTIC (checked top to
bottom; the first matching rule wins):

1. Walk-forward reads "unstable" — a real edge that does NOT hold up
   window-to-window across real, disjoint chronological windows is, by
   definition, a real out-of-sample failure. -> OOS_FAILURE.
2. Parameter sensitivity reads "fragile" OR cost sensitivity reads
   "cost_sensitive" — the edge's sign flips under a neighboring real
   parameter choice, or evaporates under this codebase's own real
   transaction-cost/slippage constants. Both are real, disclosed
   overfitting red flags (the directive's own examples: "excessive
   parameter sensitivity," "performance disappearing after realistic
   costs") that fall short of the stronger walk-forward-instability
   evidence above. -> OVERFIT_SUSPECTED.
3. All three verdicts read "insufficient_data" — no real axis produced
   enough evidence to classify anything. -> INSUFFICIENT_DATA.
4. Any (but not all) of the three verdicts reads "insufficient_data" —
   real evidence exists on some axes but the picture is not yet
   complete; this classification cannot be finalized honestly.
   -> PENDING_VALIDATION.
5. Otherwise every axis with a real verdict reads favorably (walk-
   forward "stable", parameter sensitivity "robust", cost sensitivity
   "cost_resilient"). -> ROBUST.

Never "automatically call a strategy fraudulent/bad" per the directive's
own instruction — OVERFIT_SUSPECTED and OOS_FAILURE are read-outs of
existing real evidence, never an accusation, and both are reachable only
through a real, cited verdict from an already-tested module.
"""
from __future__ import annotations

from app.schemas import CostSensitivityResult, OverfittingDiagnosis, ParameterSensitivityResult, WalkForwardValidationResult


def classify_overfitting_risk(
    walk_forward: WalkForwardValidationResult,
    parameter_sensitivity: ParameterSensitivityResult,
    cost_sensitivity: CostSensitivityResult,
) -> OverfittingDiagnosis:
    """The one real entry point — see this module's own docstring for
    the exact, disclosed priority rule."""
    verdicts = (walk_forward.verdict, parameter_sensitivity.verdict, cost_sensitivity.verdict)

    if walk_forward.verdict == "unstable":
        verdict = "oos_failure"
        detail = (
            "Walk-forward validation found this edge does not hold up across real, disjoint chronological windows "
            f"({walk_forward.detail}) — a real out-of-sample failure, whatever the full-series backtest alone reported."
        )
    elif parameter_sensitivity.verdict == "fragile" or cost_sensitivity.verdict == "cost_sensitive":
        red_flags = [
            label
            for label, is_flagged in (
                ("parameter sensitivity (edge sign is not stable across neighboring parameter values)", parameter_sensitivity.verdict == "fragile"),
                ("cost sensitivity (edge does not survive this codebase's own real transaction-cost/slippage constants)", cost_sensitivity.verdict == "cost_sensitive"),
            )
            if is_flagged
        ]
        verdict = "overfit_suspected"
        detail = f"Real evidence flags: {'; '.join(red_flags)}. Walk-forward itself did not read unstable, but this is a genuine, disclosed overfitting red flag."
    elif all(v == "insufficient_data" for v in verdicts):
        verdict = "insufficient_data"
        detail = "None of walk-forward, parameter-sensitivity, or cost-sensitivity produced enough real closed trades yet to classify generalization risk at all."
    elif any(v == "insufficient_data" for v in verdicts):
        verdict = "pending_validation"
        missing = [
            label
            for label, v in (("walk-forward", walk_forward.verdict), ("parameter sensitivity", parameter_sensitivity.verdict), ("cost sensitivity", cost_sensitivity.verdict))
            if v == "insufficient_data"
        ]
        detail = f"Real, favorable evidence exists on some axes, but {', '.join(missing)} could not yet reach a real verdict — this classification is not yet complete."
    else:
        verdict = "robust"
        detail = (
            "Every real axis this module reads (walk-forward stability, parameter-sensitivity robustness, cost-sensitivity resilience) "
            "reads favorably. Not a claim of certainty or live profitability — only that no real generalization-risk check this codebase "
            "runs found a reason to doubt it yet."
        )

    return OverfittingDiagnosis(
        verdict=verdict,  # type: ignore[arg-type]
        detail=detail,
        walkForwardVerdict=walk_forward.verdict,
        parameterSensitivityVerdict=parameter_sensitivity.verdict,
        costSensitivityVerdict=cost_sensitivity.verdict,
    )
