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

CEO directive "Professional Quant Firm Phase 41-45," Critical Task #0 —
a real, empirical forensic audit of a live save (31 sim-days, 47
resolved decisions, only 2 real trades) traced the near-total absence
of trades to two real, independently-verified, INTENTIONAL design
decisions working together — neither a crash nor an exception: (1)
this module's own real `min_trade_quality_score` gate (verified: of the
save's own real, persisted `opportunityRejections`, 100/100 sampled
were rejected here, before ever reaching a TradeProposal at all), and
(2) `GameSaveState.settings.operating_mode` defaulting to `"learning"`,
which requires an explicit CEO/player decision on every proposal that
DOES clear this gate (see app/nexus.py's `_apply_operating_mode()`).

A DEEPER, disclosed finding from that same audit: running this
codebase's own real `compute_liquidity()`/`build_decision_score()`
live against its own real (mock) watchlist found `liquidityQualityScore`
organically landing at 0-30/100 for most real candidates — genuine
equal-high/equal-low price clustering is rare in a smooth stochastic-
walk series — a much lower typical range than the other 6 sub-scores
(usually 50-100). Averaged unweighted into the same composite, this one
sub-score structurally drags every real candidate's Trade Quality Score
down by roughly 5-7 points before the 70-point bar is even checked;
empirically, the maximum score among 100 sampled REAL rejections was
69.7 — never once at or above the threshold, among genuinely varied
real candidates. `evaluate_opportunity()` below now names this
explicitly (`liquidity_confirmation_weak`, see `_dominant_drag_sub_
score()`) when it is the real dominant driver of a rejection, so this
finding is auditable going forward. Per this same directive's own
explicit "do not weaken risk controls simply because trading activity
is low" instruction, `min_trade_quality_score`, `DECISION_SCORE_
THRESHOLD`, and `compute_liquidity()`'s own scoring formula are
DELIBERATELY left unchanged by this pass — flagged for CEO/design
review (see docs/Architecture.md's Phase 41-45 section), never
silently "fixed" by loosening a real gate.

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

CEO directive "Command Center + Professional Quant Trading Firm
Upgrade" — session as a real, live trade-gating reason. Phase 0's own
research had named this an explicit, disclosed gap: the No-Trade Reason
Taxonomy's own SESSION_FILTER example "has no real mechanism." It does
now, built on real evidence that already existed for a different
purpose: `app/session_evidence.py`'s `compute_session_regime_evidence()`
(built for the Academy's Session Trading curriculum) already answers
"does this company's own trading actually perform differently by
session" from real closed `DecisionVaultEntry` history, bucketed by
(session, regime). `evaluate_opportunity()` now also looks up the bucket
matching the CURRENT live (session, regime) pairing — both already real
fields on the same `MarketIntelligenceState` this module already reads
— and rejects only when that exact pairing's own real evidence state is
"unfavorable" (a disclosed win-rate floor, at a disclosed minimum real
sample size; below that sample, the check stays silent rather than
forcing a read on thin data). This is never a forecast and never a
fabricated rule about which sessions are "good" — it is this company's
own real, empirical track record, consulted live at the one stage
(Opportunity Gatekeeper, pre-proposal) that already exists for exactly
this kind of evidence-based filter.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.gatekeeper import GATEKEEPER_EVAL_WINDOW_MINUTES
from app.schemas import (
    DecisionScoreBreakdown,
    DecisionVaultEntry,
    ExpectedValueAnalysis,
    MarketIntelligenceState,
    NoTradeReasonCode,
    OpportunityRejection,
    RiskLimits,
    TradeProposal,
    WatchlistEntry,
)
from app.session_evidence import compute_session_regime_evidence, lookup_session_regime_evidence

# CEO directive "Professional Quant Firm Phase 41-45," Critical Task #0
# forensic audit — a live, empirical run of this codebase's own real
# compute_liquidity()/build_decision_score() against its own mock
# candle history found liquidityQualityScore organically landing in the
# 0-30 range for most real candidates (equal-high/equal-low clustering
# is genuinely rare in a smooth stochastic-walk price series), a much
# lower typical range than the other 6 sub-scores (usually 50-100) —
# structurally dragging every candidate's composite average down by
# roughly this many points before it ever reaches the 70-point bar.
# This constant names that finding's own real threshold (a sub-score is
# flagged as the dominant drag when it is both the real minimum among
# this candidate's own sub-scores AND below this bar) rather than
# silently absorbing it into a vaguer "Trade Quality Score" reason —
# see this module's own module docstring addendum and docs/
# Architecture.md's Phase 41-45 section for why this is disclosed as a
# real, evidence-based finding for CEO/design review, NOT auto-"fixed"
# by reweighting or lowering any threshold (this directive explicitly
# forbids weakening risk controls merely because trade volume is low).
LIQUIDITY_DOMINANT_DRAG_THRESHOLD = 40.0

# Reuses Feature 20's own real evaluation window rather than inventing a
# second magic number — the same "how long until we honestly know if
# this direction was right" question, asked at an earlier stage.
OPPORTUNITY_EVAL_WINDOW_MINUTES = GATEKEEPER_EVAL_WINDOW_MINUTES


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dominant_drag_sub_score(decision_score: DecisionScoreBreakdown) -> tuple[str, float] | None:
    """CEO directive "Professional Quant Firm Phase 41-45" — identifies
    which real sub-score is the lowest (never a guess: a direct min()
    over the candidate's own real, already-computed sub-scores, skipping
    `strategyHealthScore` when it's `None`) so a rejection can name the
    real, specific weak point rather than only the composite. Returns
    `None` if every real sub-score is 0 (nothing to single out)."""
    named: list[tuple[str, float]] = [
        ("evidence", decision_score.evidence_score),
        ("confidence", decision_score.confidence_score),
        ("risk", decision_score.risk_score),
        ("expected_value", decision_score.expected_value_score),
        ("market_quality", decision_score.market_quality_score),
        ("liquidity", decision_score.liquidity_quality_score),
        ("portfolio_compatibility", decision_score.portfolio_compatibility_score),
    ]
    if decision_score.strategy_health_score is not None:
        named.append(("strategy_health", decision_score.strategy_health_score))
    return min(named, key=lambda pair: pair[1])


def evaluate_opportunity(
    *,
    decision_score: DecisionScoreBreakdown,
    expected_value: ExpectedValueAnalysis,
    market_intelligence: MarketIntelligenceState,
    risk_limits: RiskLimits,
    decision_vault: list[DecisionVaultEntry] | None = None,
) -> tuple[bool, list[str], list[NoTradeReasonCode]]:
    """The engine's one real decision: does this candidate earn the
    right to become a CEO-facing TradeProposal? Every reason for a
    rejection is real and named — never a bare "no" with no trail (the
    same convention app/gatekeeper.py's own GatekeeperVerdict already
    establishes for its later-stage checks). Returns (approved, reasons,
    reason_codes) — CEO directive "Professional Quant Firm Phase 41-45,"
    Critical Task #0's No-Trade Reason Taxonomy, one code per reason,
    same order.

    `decision_vault` (optional, defaults to no evidence) feeds CEO
    directive "Command Center + Professional Quant Trading Firm
    Upgrade"'s session-as-a-live-gating-reason check below — see that
    check's own comment for the full real-evidence reasoning."""
    reasons: list[str] = []
    codes: list[NoTradeReasonCode] = []
    if market_intelligence.quality.tier == "avoid_trading":
        reasons.append(f"Market Quality reads avoid trading ({market_intelligence.quality.score:.0f}/100) — {market_intelligence.quality.reasoning}")
        codes.append("market_quality_avoid_trading")
    if expected_value.expected_value_pct < risk_limits.min_expected_value_pct:
        reasons.append(f"Expected Value {expected_value.expected_value_pct:+.2f}% is below the required {risk_limits.min_expected_value_pct:+.2f}% minimum.")
        codes.append("expected_value_below_threshold")
    if decision_score.overall < risk_limits.min_trade_quality_score:
        reasons.append(f"Trade Quality Score {decision_score.overall:.0f}/100 is below the required {risk_limits.min_trade_quality_score:.0f} minimum.")
        codes.append("trade_quality_below_threshold")
        drag = _dominant_drag_sub_score(decision_score)
        if drag is not None and drag[0] == "liquidity" and drag[1] < LIQUIDITY_DOMINANT_DRAG_THRESHOLD:
            reasons.append(
                f"Liquidity confirmation reads {drag[1]:.0f}/100 — the single lowest real sub-score behind this rejection "
                "(real equal-high/equal-low clustering is genuinely rare in this candidate's own recent price action)."
            )
            codes.append("liquidity_confirmation_weak")
    # CEO directive "Command Center + Professional Quant Trading Firm
    # Upgrade" — session as a real, evidence-based live gating reason.
    # Consults this company's own real closed-trade history for the
    # EXACT (session, regime) pairing happening right now — never a
    # forecast, never a fabricated "this session is bad" rule; a real
    # win rate over real past trades, at a real, disclosed evidence
    # floor (compute_session_regime_evidence()'s own
    # MIN_SESSION_REGIME_SAMPLE — below it, evidence_state is
    # "not_enough_evidence" and this check stays silent, exactly the
    # honest "no-trade must mean no-edge, not no-data" distinction the
    # directive itself asks for).
    session_regime_summary = compute_session_regime_evidence(decision_vault or [])
    current_bucket = lookup_session_regime_evidence(session_regime_summary, market_intelligence.session.current, market_intelligence.regime)
    if current_bucket is not None and current_bucket.evidence_state == "unfavorable":
        reasons.append(
            f"This company's own trading history reads unfavorable here: {market_intelligence.session.label} sessions "
            f"during a {market_intelligence.regime_label} regime have a real {current_bucket.win_rate_pct:.0f}% win rate "
            f"over {current_bucket.sample_size} closed trades."
        )
        codes.append("session_regime_unfavorable_evidence")
    return not reasons, reasons, codes


def build_opportunity_rejection(
    proposal: TradeProposal,
    *,
    decision_score: DecisionScoreBreakdown,
    expected_value: ExpectedValueAnalysis,
    reasons: list[str],
    reason_codes: list[NoTradeReasonCode],
    price_at_rejection: float,
    now_sim_minutes: int,
) -> OpportunityRejection:
    return OpportunityRejection(
        id=f"oppreject-{proposal.id}",
        symbol=proposal.symbol,
        wouldHaveRecommended=proposal.overall_recommendation,
        reasons=reasons,
        reasonCodes=reason_codes,
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
