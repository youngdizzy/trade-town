"""app/war_room.py — the Executive Decision Simulator's Digital War Room
(v0.7, brief self-numbered "Feature 54" by its author, but that number is
already in use in this codebase for the Decision Memory System — see
app/decision_vault.py and CHANGELOG.md; referred to here and in commit
history as Feature 55 to avoid the collision).

GOAL (from the brief): "Before risking company capital, every significant
decision must be stress-tested, challenged, debated, and simulated" in a
"Digital War Room" where multiple departments contribute independent
analysis, tested against multiple realistic future scenarios, scored on
expected value, challenged by a Devil's Advocate, given a contingency
plan, and compared against the company's own trading history.

RESEARCHED FIRST. Every one of the brief's asks was checked against this
codebase's existing systems before writing a line of this module — the
overwhelming majority already exist as real, separate artifacts:

  Department analysis / "Digital War Room" -> app/executive_intelligence.py's
                                               generate_department_opinions()
                                               / compute_executive_recommendation()
                                               (9 real department seats)
  Devil's Advocate                          -> app/devils_advocate.py's
                                               generate_challenge_report()
                                               (already assigns one real
                                               employee per proposal)
  Multi-scenario simulation                 -> app/whatif.py's
                                               run_whatif_simulation() —
                                               12 real bootstrap-resampled
                                               scenarios, closely matching
                                               the brief's own 12-item list
                                               (see the mapping note below)
  Historical comparison /
  "Institutional Knowledge Graph"           -> app/decision_vault.py's
                                               find_similar_vault_entries()/
                                               summarize_similarity() —
                                               real rule-based tiered
                                               matching, never a
                                               fabricated similarity score
  Evidence Score vs. Confidence Score       -> app/decision_vault.py's
                                               compute_evidence_score() +
                                               app/confidence.py's
                                               DecisionConfidence — and
                                               "confidence may never
                                               exceed evidence" already
                                               holds by construction
                                               (Evidence Score is a strict
                                               subset average of
                                               Confidence Score's own
                                               factors)

This module's real, novel job is exactly three things the brief asked
for that genuinely did not exist anywhere: (1) a permanent WarRoomSession
that JOINS all of the above into one addressable record per new
TradeProposal, (2) a real Expected Value / Statistical Edge / Risk-to-
Reward read computed from the 12 real scenarios' own probability-weighted
outcomes, and (3) a real, signal-grounded Contingency Plan.

SCENARIO MAPPING — the brief names 12 scenarios; app/whatif.py already
has 12, built for the same "stress-test a trade candidate" purpose. They
are not identical, but map closely enough that building a second scenario
engine would be exactly the kind of duplication this codebase's own rule
forbids:

  Brief's scenario            -> whatif.py's real equivalent
  Best Case                   -> best_case_scenario (computed: whichever
                                  real scenario has the highest reward range)
  Expected Case                -> baseline (organic, unbiased resample)
  Worst Case / Difficult Case -> worst_case_scenario / bearish_reversal
  Black Swan                  -> flash_crash
  High Volatility              -> high_volatility
  Low Liquidity                -> liquidity_sweep
  Trend Continuation          -> bullish_continuation
  Trend Reversal               -> trend_failure
  Range Expansion              -> breakout_confirmation
  Range Compression            -> sideways_consolidation
  News Shock                  -> news_shock

  (whatif.py additionally has low_volatility/gap_up/gap_down, real extras
  beyond the brief's list — kept, not removed, since trimming a working
  real signal to match a brief's exact count would be its own kind of
  dishonesty.)

WHAT'S DELIBERATELY NOT HERE, and why:

  R-Multiple                  - same gap DecisionVaultEntry.rMultiple
                                 already documents: no stop-loss/initial-
                                 risk basis exists anywhere in this
                                 codebase's real risk engine
                                 (app/risk_engine.py's recommended_quantity()
                                 sizes purely off equity%, never a stop
                                 distance). ExpectedValueAnalysis.riskToReward
                                 is a real reward/drawdown-magnitude ratio,
                                 deliberately labeled Risk-to-Reward, not
                                 "R-Multiple."
  Historical Expectancy        - only exists at the Strategy level
                                 (app/strategy_lab.py's expectancy, over
                                 many backtested trades); no ordinary
                                 Trading Floor TradeProposal links back to
                                 a tested Strategy (confirmed via
                                 app/decision_vault.py's own established
                                 gap) — DecisionScoreBreakdown.strategyHealthScore
                                 is null for every ordinary proposal, and
                                 the composite renormalizes over only the
                                 real sub-scores available rather than
                                 substituting a fabricated placeholder.
  Auto-failing negative-EV
  trades                       - this codebase's own real gate
                                 (app/gatekeeper.py) already hard-blocks a
                                 trade on real, checkable conditions;
                                 adding a second automatic reject path off
                                 a heuristic EV estimate would contradict
                                 "risk is measured and displayed, never
                                 auto-corrected without the player"
                                 (docs/ROADMAP.md's own v0.8 stop
                                 condition) — DecisionScoreBreakdown.passed
                                 is a real, visible flag the CEO sees, not
                                 an automatic veto.
  LLM-generated analysis text  - no LLM/HTTP client dependency exists
                                 anywhere (backend/requirements.txt has
                                 none) — every string here is templated
                                 from real computed values, the same
                                 convention every other module in this
                                 codebase already uses.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.decision_vault import compute_evidence_score, find_similar_vault_entries, summarize_similarity
from app.evidence_confluence import assess_evidence_confluence
from app.executive_intelligence import compute_executive_recommendation, generate_department_opinions
from app.schemas import (
    AnalystChoice,
    ChallengeReport,
    CoachReport,
    ContingencyStep,
    DecisionScoreBreakdown,
    DecisionVaultEntry,
    EvidenceConfluenceRead,
    EvidenceDirection,
    ExpectedValueAnalysis,
    LiquidityRead,
    MarketIntelligenceState,
    PaperTrade,
    RiskLimits,
    RiskWarning,
    ScenarioOutcomeComparison,
    TradeProposal,
    WarRoomSession,
    WhatIfSimulation,
)
from app.whatif import run_whatif_simulation

MAX_WAR_ROOM_SESSIONS = 60

# The company threshold a Decision Score must clear to be considered
# genuinely well-supported — the same 70-point "good decision" bar
# app/discipline.py's tier_for_score() and app/executive.py's
# compute_decision_grade() already use for a C-tier-or-better read,
# reused here rather than inventing a second threshold convention.
DECISION_SCORE_THRESHOLD = 70.0

PROPOSAL_TIMEFRAME = "1h"
PROPOSAL_CANDLE_COUNT = 30


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_expected_value_analysis(simulation: WhatIfSimulation) -> ExpectedValueAnalysis:
    """A real, probability-weighted read over every real scenario
    WhatIfSimulation already computed — the midpoint of each scenario's
    own real reward range, weighted by its own real probability of
    profit, averaged across all 12. `edgePct` isolates whatever real
    skew the scenario mix adds over the organic, unbiased baseline."""
    scenario_midpoints = [(s.reward_range_low_pct + s.reward_range_high_pct) / 2 * (s.probability_of_profit_pct / 100) for s in simulation.scenarios]
    expected_value_pct = round(sum(scenario_midpoints) / len(scenario_midpoints), 2) if scenario_midpoints else 0.0
    baseline_midpoint = (simulation.baseline.reward_range_low_pct + simulation.baseline.reward_range_high_pct) / 2
    edge_pct = round(expected_value_pct - baseline_midpoint, 2)

    avg_reward = sum(s.reward_range_high_pct for s in simulation.scenarios) / len(simulation.scenarios) if simulation.scenarios else 0.0
    avg_drawdown = sum(abs(s.typical_drawdown_pct) for s in simulation.scenarios) / len(simulation.scenarios) if simulation.scenarios else 0.0
    risk_to_reward = round(avg_reward / avg_drawdown, 2) if avg_drawdown > 0 else 0.0

    positive_expectancy = expected_value_pct > 0
    detail = (
        f"Expected value of {expected_value_pct:+.2f}% across the 12 real simulated scenarios "
        f"({'a real edge of' if edge_pct >= 0 else 'a real shortfall of'} {edge_pct:+.2f}% vs. the unbiased baseline)."
    )
    return ExpectedValueAnalysis(
        expectedValuePct=expected_value_pct,
        edgePct=edge_pct,
        riskToReward=risk_to_reward,
        positiveExpectancy=positive_expectancy,
        detail=detail,
    )


def _risk_score(proposal: TradeProposal, risk_warnings: list[RiskWarning]) -> float:
    """Real, checkable — reads Guardian's own already-computed standing
    warnings for this exact symbol rather than inventing a second risk
    model."""
    matching = [w for w in risk_warnings if w.symbol == proposal.symbol]
    if any(w.severity == "critical" for w in matching):
        return 20.0
    if any(w.severity == "warning" for w in matching):
        return 60.0
    return 100.0


def _portfolio_compatibility_score(proposal: TradeProposal, correlated_open_positions: int) -> float:
    """Real — reads the same category-concentration signal
    app/gatekeeper.py's _correlation_check() already computes (this
    codebase's honest stand-in for real sector correlation; see that
    module's own docstring), penalized per already-open correlated
    position rather than a hard pass/fail gate."""
    return max(0.0, 100.0 - correlated_open_positions * 25.0)


# CEO directive "Professional Quant Firm Phase 41-45" — "CONFLUENCE
# QUALITY... prevent double-counting." The real count of DIRECTIONAL
# evidence families app/evidence_confluence.py's own module docstring
# establishes — `levels` (Fibonacci) is deliberately excluded there as
# informational-only, never a directional claim, so it is excluded from
# this real denominator too.
TOTAL_DIRECTIONAL_EVIDENCE_FAMILIES = 6


def _evidence_confluence_score(confluence: EvidenceConfluenceRead | None, overall: AnalystChoice) -> float | None:
    """A real 0-100 read of how much INDEPENDENT evidence (distinct
    families, never raw signal count — see TOTAL_DIRECTIONAL_EVIDENCE_
    FAMILIES above) actually supports THIS proposal's own chosen
    direction — never app/evidence_confluence.py's own internal
    majority direction taken at face value, since a proposal can
    legitimately go against the raw indicators' own majority (e.g. a
    contrarian/mean-reversion thesis). `None` only when this symbol's
    own real candle history was unavailable this tick — never a
    fabricated neutral default standing in for missing data."""
    if confluence is None:
        return None
    proposal_direction: EvidenceDirection = "bullish" if overall == "buy" else "bearish" if overall == "sell" else "neutral"
    if confluence.majority_direction == "neutral" or proposal_direction == "neutral":
        return 50.0
    if confluence.majority_direction != proposal_direction:
        # The real, independent evidence actively disagrees with this proposal's own
        # direction — a genuine red flag, never softened into a middling score.
        return 0.0
    return round(min(100.0, confluence.independent_family_count / TOTAL_DIRECTIONAL_EVIDENCE_FAMILIES * 100), 1)


def build_decision_score(
    proposal: TradeProposal,
    *,
    risk_warnings: list[RiskWarning],
    correlated_open_positions: int,
    expected_value: ExpectedValueAnalysis,
    market_intelligence: MarketIntelligenceState,
    liquidity: LiquidityRead | None,
    evidence_confluence: EvidenceConfluenceRead | None = None,
) -> DecisionScoreBreakdown:
    evidence_score = compute_evidence_score(proposal.confidence_engine.factors)
    confidence_score = proposal.confidence_engine.score
    risk_score = _risk_score(proposal, risk_warnings)
    # A real, bounded linear mapping from Expected Value % onto a 0-100
    # score (50 = breakeven) — an honest heuristic, documented as such,
    # not a claim of statistical precision.
    expected_value_score = max(0.0, min(100.0, 50.0 + expected_value.expected_value_pct * 5.0))
    market_quality_score = market_intelligence.quality.score
    liquidity_quality_score = liquidity.liquidity_score if liquidity is not None else 50.0
    portfolio_compatibility_score = _portfolio_compatibility_score(proposal, correlated_open_positions)
    evidence_confluence_score = _evidence_confluence_score(evidence_confluence, proposal.overall_recommendation)

    # strategy_health_score is always None here — no ordinary Trading
    # Floor TradeProposal links back to a tested Strategy (see this
    # module's own docstring) — so the composite renormalizes over only
    # the real sub-scores that exist for every proposal (7, or 8 when
    # evidence_confluence_score is real).
    sub_scores = [evidence_score, confidence_score, risk_score, expected_value_score, market_quality_score, liquidity_quality_score, portfolio_compatibility_score]
    if evidence_confluence_score is not None:
        sub_scores.append(evidence_confluence_score)
    overall = round(sum(sub_scores) / len(sub_scores), 1)

    return DecisionScoreBreakdown(
        evidenceScore=evidence_score,
        confidenceScore=confidence_score,
        riskScore=risk_score,
        expectedValueScore=round(expected_value_score, 1),
        strategyHealthScore=None,
        marketQualityScore=market_quality_score,
        liquidityQualityScore=liquidity_quality_score,
        portfolioCompatibilityScore=portfolio_compatibility_score,
        evidenceConfluenceScore=evidence_confluence_score,
        overall=overall,
        threshold=DECISION_SCORE_THRESHOLD,
        passed=overall >= DECISION_SCORE_THRESHOLD,
    )


def build_contingency_plan(market_intelligence: MarketIntelligenceState, liquidity: LiquidityRead | None) -> list[ContingencyStep]:
    """Every step here is a real IF/THEN response tied to a real signal
    already computed for this symbol this tick — never an invented
    playbook. `triggered` reports whether that condition is true right
    now, so the CEO can see at a glance which contingencies are already
    live versus merely standing by."""
    steps = [
        ContingencyStep(
            condition="Liquidity sweep detected",
            action="Wait for confirmation before adding size — a sweep can be a trap, not a real breakout.",
            triggered=bool(liquidity and liquidity.sweep_detected),
        ),
        ContingencyStep(
            condition="Market regime reads high volatility",
            action="Tighten position size and widen the mental stop before entering.",
            triggered=market_intelligence.regime == "high_volatility",
        ),
        ContingencyStep(
            condition="Market regime reads liquidity hunt",
            action="Reduce exposure — the market is actively hunting resting orders.",
            triggered=market_intelligence.regime == "liquidity_hunt",
        ),
        ContingencyStep(
            condition="News risk reads elevated",
            action="Exit immediately if a real headline moves the market against this position.",
            triggered=market_intelligence.news_risk.risk_level == "elevated",
        ),
        ContingencyStep(
            condition="Market Quality reads Avoid Trading",
            action="Pause management and reassess — the desk itself is already reading this environment as unfavorable.",
            triggered=market_intelligence.quality.tier == "avoid_trading",
        ),
    ]
    return steps


def build_war_room_session(
    session_id: str,
    proposal: TradeProposal,
    *,
    challenge_report: ChallengeReport | None,
    coach_reports: list[CoachReport],
    market_intelligence: MarketIntelligenceState,
    decision_vault: list[DecisionVaultEntry],
    risk_warnings: list[RiskWarning],
    correlated_open_positions: int,
    candles: list,
    risk_limits: RiskLimits,
) -> WarRoomSession:
    opinions = generate_department_opinions(proposal, challenge_report, coach_reports, market_intelligence, decision_vault)
    recommendation = compute_executive_recommendation(proposal, opinions)

    simulation = run_whatif_simulation(proposal.symbol, candles)
    expected_value = build_expected_value_analysis(simulation)

    liquidity = next((liq for liq in market_intelligence.liquidity if liq.symbol == proposal.symbol), None)
    # CEO directive "Professional Quant Firm Phase 41-45" — "CONFLUENCE
    # QUALITY." Real, already-tested app/evidence_confluence.py, wired
    # into a live decision for the first time (see that module's own
    # docstring — it was previously "never wired into a live decision").
    # `None` (never a fabricated zero-signal read) when this tick's own
    # candles fetch came back empty (see the caller's `except ValueError`
    # fallback).
    evidence_confluence = assess_evidence_confluence(proposal.symbol, candles) if candles else None
    decision_score = build_decision_score(
        proposal,
        risk_warnings=risk_warnings,
        correlated_open_positions=correlated_open_positions,
        expected_value=expected_value,
        market_intelligence=market_intelligence,
        liquidity=liquidity,
        evidence_confluence=evidence_confluence,
    )
    contingency_plan = build_contingency_plan(market_intelligence, liquidity)

    matches, matched_on = find_similar_vault_entries(
        decision_vault,
        symbol=proposal.symbol,
        market_regime=market_intelligence.regime,
        confidence_tier=proposal.confidence_engine.tier,
        min_matches=risk_limits.min_similar_matches,
    )
    similar_trades = summarize_similarity(matches, matched_on, mistake_warning_share=risk_limits.mistake_warning_share_pct / 100)

    return WarRoomSession(
        id=session_id,
        proposalId=proposal.id,
        symbol=proposal.symbol,
        departmentOpinions=opinions,
        recommendation=recommendation,
        scenarioSimulation=simulation,
        similarTrades=similar_trades,
        expectedValue=expected_value,
        decisionScore=decision_score,
        contingencyPlan=contingency_plan,
        confidenceValidated=evidence_never_exceeds_confidence(proposal),
        evidenceConfluence=evidence_confluence,
        outcomeComparison=None,
        createdAt=_now_iso(),
    )


def evidence_never_exceeds_confidence(proposal: TradeProposal) -> bool:
    """Always True by construction — see this module's own docstring and
    WarRoomSession.confidenceValidated's field comment. Computed (not
    hardcoded) so a future change to compute_evidence_score() that ever
    broke the invariant would show up here honestly rather than silently."""
    evidence_score = compute_evidence_score(proposal.confidence_engine.factors)
    return evidence_score <= proposal.confidence_engine.score + 0.01  # floating-point tolerance


def compare_scenario_to_outcome(simulation: WhatIfSimulation, trade: PaperTrade) -> ScenarioOutcomeComparison:
    """A real comparison, filled in once the linked trade actually
    closes — finds whichever real scenario's predicted range midpoint is
    numerically closest to what actually happened, then reports whether
    the real outcome fell inside that scenario's own real predicted
    range. Never a claim that the scenario "predicted" the trade — see
    the field's own docstring."""
    all_results = [*simulation.scenarios, simulation.baseline]
    closest = min(all_results, key=lambda s: abs((s.reward_range_low_pct + s.reward_range_high_pct) / 2 - trade.pnl_pct))
    within_range = closest.reward_range_low_pct <= trade.pnl_pct <= closest.reward_range_high_pct
    detail = (
        f"The real outcome ({trade.pnl_pct:+.1f}%) landed closest to the \"{closest.label}\" scenario's predicted "
        f"{closest.reward_range_low_pct:+.1f}% to {closest.reward_range_high_pct:+.1f}% range"
        f"{' and fell inside it' if within_range else ', but outside it'}."
    )
    return ScenarioOutcomeComparison(
        matchedScenario=closest.scenario_type,
        matchedLabel=closest.label,
        predictedRangeLowPct=closest.reward_range_low_pct,
        predictedRangeHighPct=closest.reward_range_high_pct,
        actualPnlPct=trade.pnl_pct,
        withinPredictedRange=within_range,
        detail=detail,
    )


def record_war_room_session(sessions: list[WarRoomSession], session: WarRoomSession) -> list[WarRoomSession]:
    updated = [*sessions, session]
    if len(updated) > MAX_WAR_ROOM_SESSIONS:
        del updated[: len(updated) - MAX_WAR_ROOM_SESSIONS]
    return updated
