"""app/opportunity_gatekeeper.py — Institutional Trade Filter &
Opportunity Gatekeeper (v0.7 Design Bible Chapter 58).

GOAL (from the chapter): TradeTown should never feel pressured to
trade. This engine rejects poor opportunities BEFORE they ever become a
CEO-facing TradeProposal — the CEO should only ever see candidates that
have already earned that attention, never do all the filtering
personally.

RESEARCHED FIRST. Almost every real signal this needs already exists.
`app/war_room.py`'s `build_decision_score()` already computes exactly
the 0-100 "Trade Quality Score" composite the chapter's brief asks for
(Evidence/Confidence/Risk/Expected Value/Market Quality/Liquidity/
Portfolio Compatibility), checked against a real `DECISION_SCORE_
THRESHOLD` — and `build_expected_value_analysis()` already computes a
real, probability-weighted Expected Value read. THE REAL GAP: today
those two real scores are purely informational, computed only AFTER a
candidate already became a real TradeProposal
(`app/nexus.py`'s `_generate_trade_proposals()` has exactly one real
pre-proposal filter — a single confidence threshold — and never
consults Evidence, Expected Value, or Market Quality at all). This
module does not duplicate either function; it is called with their
already-computed real output and decides whether the candidate is
allowed to become CEO-visible at all.

`app/gatekeeper.py`'s Trade Gatekeeper (v0.7 Feature 20) is a real,
separate, LATER-stage check — it runs only after the CEO has already
picked buy/sell, against a different checklist entirely (confidence,
risk-manager alignment, multi-agent agreement, the AI Debate outcome,
exposure, correlation, active risk warnings, Market Intelligence
quality). This module is a new, EARLIER sibling in the same real
pipeline, not a replacement for it — both stay real, both stay separate,
matching the Design Bible chapter's own explicit "does not own" boundary
against Feature 20.

HONESTY BOUNDARY — what this module deliberately does NOT build, and why
(see the Design Bible chapter's own Implementation Notes for the fuller
version):

  Promoting app/gatekeeper.py's hardcoded MAX_CORRELATED_POSITIONS to a
  real CEO-configurable RiskLimits field, and a matching pre-proposal
  correlation check here — a real, named gap the chapter's own CEO
  Controls table flags, but a genuinely separate small change to
  Feature 20's own module, not required to close the specific gap this
  pass targets (Evidence/Expected Value/Market Quality never gating
  proposal creation at all). Not built in this pass.

  A true two-phase "cheap pre-check first, expensive enrichment only if
  it might pass" pipeline — the real Decision Score/Expected Value this
  module gates on are computed as part of building the candidate's full
  WarRoomSession (department opinions, Devil's Advocate challenge
  report and all) in app/nexus.py's tick(), same as today, BEFORE this
  module's verdict is known, and simply discarded (never stored, never
  shown) if rejected. The alternative — a second, lighter-weight
  computation of the same real signal used only for gating — would risk
  the two computations drifting apart, since app/whatif.py's own
  bootstrap resampling is genuinely randomized per call (see
  app/whatif.py's module docstring): computing Expected Value twice for
  the same candidate could legitimately produce two different numbers,
  meaning a candidate could be approved by one draw and shown a
  different (possibly failing) number in the WARROOM tab. Accepting a
  small, bounded CPU cost on rejected candidates (a department-opinions
  computation that gets thrown away) is the honest trade-off, the same
  "cheap, close enough" precedent Chapter 57's own Portfolio Heat
  staleness note already establishes for this codebase.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.gatekeeper import GATEKEEPER_EVAL_WINDOW_MINUTES
from app.schemas import (
    DecisionScoreBreakdown,
    ExpectedValueAnalysis,
    MarketIntelligenceState,
    OpportunityRejection,
    RiskLimits,
    TradeProposal,
    WatchlistEntry,
)

# Reuses Feature 20's own real evaluation window rather than inventing a
# second magic number — the same "how long until we honestly know if
# this direction was right" question, asked at an earlier stage.
OPPORTUNITY_EVAL_WINDOW_MINUTES = GATEKEEPER_EVAL_WINDOW_MINUTES


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def evaluate_opportunity(
    *,
    decision_score: DecisionScoreBreakdown,
    expected_value: ExpectedValueAnalysis,
    market_intelligence: MarketIntelligenceState,
    risk_limits: RiskLimits,
) -> tuple[bool, list[str]]:
    """The engine's one real decision: does this candidate earn the
    right to become a CEO-facing TradeProposal? Every reason for a
    rejection is real and named — never a bare "no" with no trail (the
    same convention app/gatekeeper.py's own GatekeeperVerdict already
    establishes for its later-stage checks)."""
    reasons: list[str] = []
    if market_intelligence.quality.tier == "avoid_trading":
        reasons.append(f"Market Quality reads avoid trading ({market_intelligence.quality.score:.0f}/100) — {market_intelligence.quality.reasoning}")
    if expected_value.expected_value_pct < risk_limits.min_expected_value_pct:
        reasons.append(f"Expected Value {expected_value.expected_value_pct:+.2f}% is below the required {risk_limits.min_expected_value_pct:+.2f}% minimum.")
    if decision_score.overall < risk_limits.min_trade_quality_score:
        reasons.append(f"Trade Quality Score {decision_score.overall:.0f}/100 is below the required {risk_limits.min_trade_quality_score:.0f} minimum.")
    return not reasons, reasons


def build_opportunity_rejection(
    proposal: TradeProposal,
    *,
    decision_score: DecisionScoreBreakdown,
    expected_value: ExpectedValueAnalysis,
    reasons: list[str],
    price_at_rejection: float,
    now_sim_minutes: int,
) -> OpportunityRejection:
    return OpportunityRejection(
        id=f"oppreject-{proposal.id}",
        symbol=proposal.symbol,
        wouldHaveRecommended=proposal.overall_recommendation,
        reasons=reasons,
        decisionScoreAtRejection=decision_score.overall,
        expectedValueAtRejectionPct=expected_value.expected_value_pct,
        priceAtRejection=price_at_rejection,
        rejectedSimMinutes=now_sim_minutes,
        createdAt=_now_iso(),
    )


def grade_opportunity_rejections(rejections: list[OpportunityRejection], watchlist: list[WatchlistEntry], now_sim_minutes: int) -> list[OpportunityRejection]:
    """Resolves any "pending" rejection whose evaluation window has
    elapsed, purely from the real difference between the symbol's
    watchlist price now and at rejection time — the exact same honest
    mechanism app/gatekeeper.py's own grade_gatekeeper_rejections()
    already uses, applied to this earlier rejection stage. A "wait"
    would-have-recommended has no real direction to grade against and
    is deliberately left "pending" forever rather than arbitrarily
    treated as a "sell" — an ordinary desk recommendation is buy or
    sell in practice, so this only matters for the rare split-vote
    case."""
    if not rejections:
        return rejections
    prices = {w.symbol: w.last_price for w in watchlist}
    updated: list[OpportunityRejection] = []
    for rejection in rejections:
        if rejection.would_have_recommended == "wait":
            updated.append(rejection)
            continue
        if rejection.outcome != "pending" or now_sim_minutes - rejection.rejected_sim_minutes < OPPORTUNITY_EVAL_WINDOW_MINUTES:
            updated.append(rejection)
            continue
        current_price = prices.get(rejection.symbol)
        if current_price is None or rejection.price_at_rejection <= 0:
            updated.append(rejection)
            continue
        change_pct = (current_price - rejection.price_at_rejection) / rejection.price_at_rejection * 100
        would_have_won = change_pct > 0 if rejection.would_have_recommended == "buy" else change_pct < 0
        updated.append(
            rejection.model_copy(
                update={
                    "outcome": "would_have_won" if would_have_won else "would_have_lost",
                    "resolved_price_change_pct": round(change_pct, 2),
                    "resolved_at": _now_iso(),
                }
            )
        )
    return updated
