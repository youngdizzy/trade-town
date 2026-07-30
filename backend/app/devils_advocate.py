"""DevilsAdvocateManager — v0.7 Feature 41, the Intelligent Devil's
Advocate System.

The AI Debate Room (Feature 17, app/debate.py) already has every analyst
who genuinely disagrees challenge the proposal in real time. This module
deliberately does not duplicate that. Instead it produces a single
structured artifact — a ChallengeReport — for one specific employee,
temporarily assigned, whose real job is to actively try to break the
trade thesis. Every field is built from real signals already computed
elsewhere:

  bull/bear case        - the real AnalystVote reasoning of whichever
                           analysts agreed/disagreed with the desk's
                           overall recommendation.
  hidden risks           - the proposal's own real risk_summary
                           (app/executive.py already carries the real
                           Sentinel/Guardian warning message there, or
                           "within all configured risk limits").
  weak assumptions        - any real DecisionConfidence factor scoring
                           below WEAK_FACTOR_THRESHOLD.
  missing evidence        - any real AnalystVote with an empty evidence
                           list.
  historical comparisons - real past CaseStudy titles (Library of
                           Mistakes, app/mistakes.py) for this same
                           symbol — an honest empty list if none exist.
  worst case scenario     - one line drawn from the What-If Simulation
                           Lab's own real worst named scenario
                           (app/whatif.py). Only that one line is kept —
                           never the full WhatIfSimulation, which this
                           codebase has already been bitten once by
                           persisting unbounded computed data (see
                           nexus.py's MAX_DECISIONS history).

`severity` is a real, checkable classification (never a fabricated
judgment call): it counts how many of the concern categories above
actually found something. Zero concerns is genuinely "no significant
weaknesses found" — the brief's own Outcome 1, and the company's
confidence should genuinely rise, not just because a report was filed.

The assigned agent rotates deterministically through a fixed pool of
employees who are never one of the six analyst seats already on this
proposal's own desk (echo/scout/nova/sentinel/pulse/atlas) and are never
Keystone/Compass (the Founders, who — per Feature 39 — never route
through this kind of operational work). Rotation is derived from the
existing report count, the same "no extra counter needed" convention
app/academy_research.py already established for its own project/agent
rotation.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.constitution import articles_for_challenge
from app.market_data import MarketDataProvider
from app.schemas import AgentId, CaseStudy, ChallengeReport, ChallengeSeverity, TradeProposal
from app.whatif import run_whatif_simulation

MAX_CHALLENGE_REPORTS = 60
PROPOSAL_TIMEFRAME = "1h"
PROPOSAL_CANDLE_COUNT = 30
WEAK_FACTOR_THRESHOLD = 50.0

ELIGIBLE_DEVILS_ADVOCATES: tuple[AgentId, ...] = ("scribe", "coach", "guardian", "cio", "sage")

_NO_RISK_MESSAGE_FRAGMENT = "within all configured risk limits"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assign_devils_advocate(existing_count: int) -> AgentId:
    return ELIGIBLE_DEVILS_ADVOCATES[existing_count % len(ELIGIBLE_DEVILS_ADVOCATES)]


def generate_challenge_report(
    proposal: TradeProposal,
    *,
    provider: MarketDataProvider,
    case_studies: list[CaseStudy],
    existing_count: int,
) -> ChallengeReport:
    assigned = _assign_devils_advocate(existing_count)

    agreeing = [v for v in proposal.analyst_votes if v.choice == proposal.overall_recommendation]
    dissenting = [v for v in proposal.analyst_votes if v.choice != proposal.overall_recommendation]

    trade_summary = (
        f"{proposal.symbol}: the desk recommends {proposal.overall_recommendation.upper()} "
        f"at {proposal.confidence_engine.score:.0f}/100 confidence. {proposal.research_summary}"
    )
    bull_case = " ".join(v.reasoning for v in agreeing) or proposal.research_summary
    bear_case = (
        " ".join(f"{v.role.title()}: {v.reasoning}" for v in dissenting)
        if dissenting
        else f"No analyst on the desk dissented from {proposal.overall_recommendation.upper()} — the case against has to be built independently."
    )

    hidden_risks: list[str] = [] if _NO_RISK_MESSAGE_FRAGMENT in proposal.risk_summary else [proposal.risk_summary]

    weak_assumptions = [
        f"{factor.name}: only {factor.score:.0f}/100 — {factor.detail}" for factor in proposal.confidence_engine.factors if factor.score < WEAK_FACTOR_THRESHOLD
    ]

    missing_evidence = [f"The {v.role} vote has no supporting evidence on record." for v in proposal.analyst_votes if not v.evidence]

    historical_comparisons = [cs.title for cs in case_studies if cs.symbol == proposal.symbol][:3]

    candles = provider.get_candles(proposal.symbol, PROPOSAL_TIMEFRAME, PROPOSAL_CANDLE_COUNT)
    whatif = run_whatif_simulation(proposal.symbol, candles)
    worst = next((s for s in whatif.scenarios if s.scenario_type == whatif.worst_case_scenario), whatif.baseline)
    worst_case_scenario = (
        f"{worst.label}: as low as {worst.reward_range_low_pct:+.1f}% with a typical drawdown of "
        f"{worst.typical_drawdown_pct:.1f}% if {worst.invalidation.lower()}"
    )

    suggested_improvements: list[str] = []
    if hidden_risks:
        suggested_improvements.append("Resolve the flagged risk warning before entering.")
    if missing_evidence:
        suggested_improvements.append("Gather supporting evidence for the vote(s) currently missing it.")
    if weak_assumptions:
        suggested_improvements.append("Revisit the weakest confidence factor(s) above before sizing up.")

    # A real, checkable count — never a judgment call: each non-empty
    # concern bucket is one signal, and real analyst dissent is itself
    # one more (see module docstring's Outcome 1/2/3 mapping).
    concern_signals = sum(1 for bucket in (hidden_risks, weak_assumptions, missing_evidence) if bucket) + (1 if dissenting else 0)
    if concern_signals == 0:
        severity: ChallengeSeverity = "none_found"
        final_recommendation = "I attempted to disprove this trade but found no major weaknesses. The setup holds up under scrutiny."
    elif concern_signals == 1:
        severity = "minor"
        final_recommendation = "Minor weaknesses only — address the item(s) above, then proceed at the CEO's discretion."
    else:
        severity = "major"
        final_recommendation = "Real weaknesses found. Consider Request More Research, Delay Decision, or rejecting outright before committing capital."

    return ChallengeReport(
        id=f"challenge-{proposal.id}-{existing_count}",
        proposalId=proposal.id,
        symbol=proposal.symbol,
        assignedAgent=assigned,
        tradeSummary=trade_summary,
        bullCase=bull_case,
        bearCase=bear_case,
        hiddenRisks=hidden_risks,
        weakAssumptions=weak_assumptions,
        missingEvidence=missing_evidence,
        historicalComparisons=historical_comparisons,
        worstCaseScenario=worst_case_scenario,
        suggestedImprovements=suggested_improvements,
        severity=severity,
        finalRecommendation=final_recommendation,
        citedArticleIds=articles_for_challenge(
            hidden_risks=hidden_risks, weak_assumptions=weak_assumptions, missing_evidence=missing_evidence, historical_comparisons=historical_comparisons
        ),
        createdAt=_now_iso(),
    )
