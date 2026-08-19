"""Weighted Executive Decision Engine (WEDE) — Design Bible Chapter 70
Part 3.

Researched first (see the Design Bible chapter's own Part 3 Ownership
table): no per-department influence/weight concept existed anywhere in
this codebase before this module. The brief names eight weighting
inputs; only two have a real, honestly computable source today, and
this module uses only those two rather than fabricating the other six:

  Historical Accuracy -> ExecutiveAccuracyScore (app/executive_
                          intelligence.py's compute_executive_accuracy_
                          scores) — closed-trade-only, never a
                          counterfactual judgment on a trade never taken.
  Market Conditions    -> MarketEnvironmentRegime (app/market_
                          environment.py, Chapter 65) — the real, live
                          5-way regime classifier.

Prediction Quality, Current Expertise, Department Performance, Recent
Reliability, Rule Compliance, and Specialization have no real per-
department measure anywhere in this codebase and are deliberately not
invented here.

Every weight this module computes is the product of small, named,
published multipliers — never a hidden blend, matching this Design
Bible's "no black-box composite" convention throughout
(CompanyHealth.overall, PropFirmComplianceScore, compute_executive_
recommendation() itself). This module itself never gates, blocks, or
resolves a trade — it only computes a real, published recommendation.
A follow-up Design Bible addendum required that recommendation to
actually reach the Trade Gatekeeper rather than sit disconnected; see
app/gatekeeper.py's _weighted_executive_check() for how — as one more
unconditional check in evaluate_gatekeeper()'s existing all(checks)
list, with exactly the same authority as every other check (can
contribute to a rejection, can never force an approval or override any
other check). The Trade Gatekeeper's real, unconditional veto (Chapters
58/66) is otherwise untouched and stays the only thing that actually
decides whether a trade executes — see the Design Bible chapter's own
Safety Systems section for the verified boundary.
"""
from __future__ import annotations

from app.schemas import (
    DepartmentInfluence,
    DepartmentOpinion,
    ExecutiveAccuracyScore,
    ExecutiveAction,
    ExecutiveDepartmentRole,
    MarketEnvironmentRegime,
    WeightedExecutiveRecommendation,
    WeightProfile,
)

# Chapter 65's real, live 5-way regime classifier boosts a department's
# weight when its stated specialty (see the Design Bible chapter's own
# "Executive Weight System" section) matches current conditions. A
# published table, not a formula — every entry is independently
# readable and editable. Departments not listed for a given regime get
# the neutral 1.0 multiplier (see compute_market_multiplier below).
MARKET_CONDITION_BOOSTS: dict[MarketEnvironmentRegime, dict[ExecutiveDepartmentRole, float]] = {
    "bull": {"research": 1.3, "market_intelligence": 1.2, "founders": 0.9},
    "bear": {"risk": 1.4, "devils_advocate": 1.3, "simulation": 1.2},
    "high_volatility": {"risk": 1.4, "quant": 1.2, "devils_advocate": 1.2},
    "low_volatility": {"research": 1.2, "decision_intelligence": 1.1},
    "sideways": {},
}

# The four "emphasis" Weight Profiles the brief names — a CEO-declared
# priority for THIS decision, not a performance read. Static, published
# multipliers; departments not listed get the neutral 1.0.
WEIGHT_PROFILE_STATIC_PRESETS: dict[WeightProfile, dict[ExecutiveDepartmentRole, float]] = {
    "risk_first": {"risk": 2.0, "devils_advocate": 1.5, "simulation": 1.3},
    "growth_first": {"research": 1.5, "market_intelligence": 1.5, "quant": 1.2},
    "research_first": {"research": 2.0, "decision_intelligence": 1.3},
    "capital_preservation": {"risk": 2.0, "simulation": 1.5, "devils_advocate": 1.3},
}

# Maps each department's categorical stance onto the same six-value
# ExecutiveAction space compute_executive_recommendation() already uses
# for the Raw Vote — so Weighted vs. Raw is a real, direct, same-
# vocabulary comparison, never two different classification schemes.
STANCE_TO_ACTION: dict[str, ExecutiveAction] = {
    "agree": "trade_normally",
    "disagree": "pause_trading",
    "recommend_rejecting": "pause_trading",
    "recommend_position_change": "reduce_risk",
    "recommend_waiting": "wait",
    "request_more_research": "research_more",
}

# Published tie-break order when two actions score identically — the
# same survival-first bias Chapter 66's own priority chain already
# uses (a caution-leaning action wins a tie over a green light).
ACTION_TIE_BREAK_ORDER: tuple[ExecutiveAction, ...] = (
    "pause_trading",
    "reduce_risk",
    "research_more",
    "wait",
    "focus_on_simulation",
    "trade_normally",
)


def compute_accuracy_multiplier(score: ExecutiveAccuracyScore) -> float:
    """A department with no tracked decisions yet gets the neutral 1.0 —
    never penalized for a track record that simply doesn't exist yet
    (this codebase's own "no fake progression" rule). Otherwise a real,
    published 0.5-1.5 range centered on 50% accuracy."""
    if score.decisions_tracked == 0 or score.accuracy_pct is None:
        return 1.0
    return round(0.5 + (score.accuracy_pct / 100.0), 3)


def compute_market_multiplier(role: ExecutiveDepartmentRole, regime: MarketEnvironmentRegime) -> float:
    return MARKET_CONDITION_BOOSTS.get(regime, {}).get(role, 1.0)


def _preset_multiplier(role: ExecutiveDepartmentRole, profile: WeightProfile) -> float:
    return WEIGHT_PROFILE_STATIC_PRESETS.get(profile, {}).get(role, 1.0)


def compute_department_influence(
    role: ExecutiveDepartmentRole,
    department_label: str,
    accuracy_score: ExecutiveAccuracyScore | None,
    *,
    regime: MarketEnvironmentRegime,
    profile: WeightProfile,
    custom_weights: dict[ExecutiveDepartmentRole, float],
) -> DepartmentInfluence:
    accuracy_multiplier = compute_accuracy_multiplier(accuracy_score) if accuracy_score is not None else 1.0
    market_multiplier = compute_market_multiplier(role, regime)
    preset_multiplier = _preset_multiplier(role, profile)

    if profile == "equal_voting":
        final_weight = 1.0
        reasoning = "Equal Voting — every department counts identically; weighting disabled."
    elif profile == "performance_weighted":
        final_weight = accuracy_multiplier
        reasoning = (
            f"Performance Weighted — {accuracy_multiplier:.2f}× from Historical Accuracy "
            f"({accuracy_score.accuracy_pct:.0f}% over {accuracy_score.decisions_tracked} tracked decisions)."
            if accuracy_score is not None and accuracy_score.decisions_tracked > 0
            else "Performance Weighted — no closed-trade track record yet; neutral 1.00×."
        )
    elif profile in WEIGHT_PROFILE_STATIC_PRESETS:
        final_weight = preset_multiplier
        reasoning = f"{profile.replace('_', ' ').title()} — {preset_multiplier:.2f}× preset emphasis for this department."
    elif profile == "custom":
        final_weight = custom_weights.get(role, 1.0)
        reasoning = f"Custom CEO Profile — {final_weight:.2f}× CEO-set weight." if role in custom_weights else "Custom CEO Profile — no weight set for this department; neutral 1.00×."
    else:  # "balanced_institutional" — the default, and the closest real
        # match to the brief's own "Dynamic Influence Score": both real
        # dynamic inputs blended, transparently, by multiplication.
        final_weight = round(accuracy_multiplier * market_multiplier, 3)
        accuracy_note = (
            f"{accuracy_multiplier:.2f}× Historical Accuracy ({accuracy_score.accuracy_pct:.0f}% over {accuracy_score.decisions_tracked} tracked decisions)"
            if accuracy_score is not None and accuracy_score.decisions_tracked > 0
            else "1.00× Historical Accuracy (no closed-trade track record yet)"
        )
        market_note = f"{market_multiplier:.2f}× current {regime.replace('_', ' ')} conditions" if market_multiplier != 1.0 else "1.00× current conditions (no boost this regime)"
        reasoning = f"Balanced Institutional — {accuracy_note} × {market_note} = {final_weight:.2f}×."

    return DepartmentInfluence(
        role=role,
        departmentLabel=department_label,
        accuracyMultiplier=accuracy_multiplier,
        marketMultiplier=market_multiplier,
        presetMultiplier=preset_multiplier,
        finalWeight=round(final_weight, 3),
        reasoning=reasoning,
    )


def compute_weighted_recommendation(
    proposal_id: str,
    opinions: list[DepartmentOpinion],
    accuracy_scores: list[ExecutiveAccuracyScore],
    *,
    regime: MarketEnvironmentRegime,
    profile: WeightProfile,
    custom_weights: dict[ExecutiveDepartmentRole, float],
    raw_action: ExecutiveAction,
) -> WeightedExecutiveRecommendation:
    accuracy_by_role = {s.role: s for s in accuracy_scores}
    influences: list[DepartmentInfluence] = []
    score_by_action: dict[ExecutiveAction, float] = {}
    max_possible: dict[ExecutiveAction, float] = {}

    for opinion in opinions:
        influence = compute_department_influence(
            opinion.role,
            opinion.department_label,
            accuracy_by_role.get(opinion.role),
            regime=regime,
            profile=profile,
            custom_weights=custom_weights,
        )
        influences.append(influence)
        action = STANCE_TO_ACTION[opinion.stance]
        contribution = influence.final_weight * opinion.confidence_pct
        score_by_action[action] = score_by_action.get(action, 0.0) + contribution
        max_possible[action] = max_possible.get(action, 0.0) + influence.final_weight * 100.0

    # Normalize each bucket to a 0-100 scale (its share of the maximum
    # that bucket could have scored if every department in it had voted
    # at 100% confidence) — a real, published formula, not raw sums that
    # would otherwise be hard to compare across buckets with different
    # department counts.
    normalized_scores: dict[ExecutiveAction, float] = {action: round(raw / max_possible[action] * 100.0, 1) if max_possible[action] > 0 else 0.0 for action, raw in score_by_action.items()}

    weighted_action: ExecutiveAction
    if normalized_scores:
        best_score = max(normalized_scores.values())
        tied = [a for a, s in normalized_scores.items() if s == best_score]
        weighted_action = next((a for a in ACTION_TIE_BREAK_ORDER if a in tied), tied[0])
    else:
        weighted_action = raw_action

    return WeightedExecutiveRecommendation(
        proposalId=proposal_id,
        profile=profile,
        marketRegime=regime,
        departmentInfluences=influences,
        rawAction=raw_action,
        weightedAction=weighted_action,
        scoreByAction={str(action): value for action, value in normalized_scores.items()},
        agreesWithRaw=weighted_action == raw_action,
    )
