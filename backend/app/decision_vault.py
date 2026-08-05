"""app/decision_vault.py — the Decision Memory System's Decision Vault,
Trade Report Card, and Similarity Engine (v0.7, brief self-numbered
"Feature 53" by its author, but that number is already in use in this
codebase for Company Certification — see CHANGELOG.md; referred to here
and in commit history as Feature 54 to avoid the collision).

GOAL (from the brief): "TradeTown should never make the same mistake
twice... every meaningful trading decision is automatically archived...
Nothing should ever be deleted." Paired with a Performance Analytics
brief asking for a per-trade Trade Report Card (Evidence/Confidence/
Capital Allocation/Decision/Discipline/Patience grades) and a Similarity
Engine ("this setup closely matches N historical trades").

RESEARCHED FIRST. Before writing a line of this module, every existing
trade/decision-review system in this codebase was mapped (see the
CHANGELOG entry this ships with for the full inventory). The overwhelming
majority of the brief's asks already exist as real, separate artifacts:

  Decision Grade              -> app/executive.py's compute_decision_grade()
  Discipline / Patience score -> app/discipline.py's DisciplineReview
  Evidence / Confidence       -> app/confidence.py's DecisionConfidence
  Mistake detection           -> app/mistakes.py's CaseStudy
  Lessons learned             -> app/journal.py's PaperTrade.lessonsLearned
  Executive notes             -> app/executive_intelligence.py's
                                  ExecutiveMeetingLogEntry
  Company DNA update          -> app/company_dna.py's nudge_legacy()

This module's real, novel job is exactly two things the brief asked for
that genuinely did not exist anywhere: (1) a permanent Decision Vault
that JOINS all of the above into one addressable record per closed
trade, and (2) a Similarity Engine that can honestly answer "have we
seen this before."

WHAT'S DELIBERATELY NOT HERE, and why:

  R-Multiple                  - no stop-loss/initial-risk basis exists
                                 anywhere in this codebase's real risk
                                 engine. app/risk_engine.py's
                                 recommended_quantity() sizes a position
                                 directly off equity% (risk_budget =
                                 equity * risk_per_trade_pct / 100), never
                                 off a stop distance — there is no "1R"
                                 to divide anything by. DecisionVaultEntry.
                                 rMultiple is always None, never
                                 backfilled with a fabricated value.
  strategyId                  - no ordinary Trading Floor trade links
                                 back to a specific Strategy object (only
                                 Research Sandbox-tested strategies do —
                                 see app/sandbox.py). Always None.
  Execution Grade,
  Psychology Grade            - no real signal anywhere in this codebase
                                 measures order-execution quality
                                 separately from the decision itself, or
                                 reads literal emotion (confirmed
                                 repeatedly elsewhere, e.g. the
                                 Probability First Trading Philosophy's
                                 own "TradeTown honestly can't read
                                 literal emotion"). Not on TradeReportCard.
  True NLP / natural-language
  search over the vault        - no LLM/HTTP client dependency exists
                                 anywhere in this codebase (confirmed via
                                 backend/requirements.txt + a fresh grep
                                 for openai/anthropic/requests/httpx — all
                                 hits are unrelated prose). Building a
                                 fake "understands your question" layer
                                 out of keyword matching would be exactly
                                 the kind of fabrication this project's
                                 discipline exists to prevent. The
                                 frontend instead gets real structured
                                 filters (symbol / regime / confidence
                                 tier / grade / date range) — an honest,
                                 less glamorous substitute, stated as such.
  True vector/embedding
  similarity                   - same dependency gap. find_similar_
                                 vault_entries() below is real, rule-based
                                 bucket matching (symbol / market regime /
                                 confidence tier), never a fabricated
                                 "94% similar" score with no real basis.

WHAT'S GENUINELY NEW CONTEXT, computed fresh at trade-close time (not
stamped at the original decision, since nothing in this codebase stamps
either of these onto a proposal or decision at the moment it's made —
both are honestly "as of trade close," documented as such on
DecisionVaultEntry itself):

  marketRegime      - app/market_intelligence.py's own real, already-
                       computed-every-tick MarketIntelligenceState.regime
                       (the same regime a TradeProposal and the Trade
                       Gatekeeper actually read).
  liquidityContext   - app/market_intelligence.py's compute_liquidity(),
                       called fresh for the trade's own symbol using the
                       same PROPOSAL_TIMEFRAME/PROPOSAL_CANDLE_COUNT
                       convention app/devils_advocate.py already
                       established, never a second liquidity engine.

DEFERRED TO A LATER SLICE (not built here — see CHANGELOG.md):
Recurring Mistake Detection as a real frequency/trend signal (today's
wisdom.py only has a plain most-common-category count, not a trend);
Strength Detection as a first-class parallel to mistakes.py; a
continuous per-employee Improvement Profile trajectory; dedicated
Executive After-Action Review / CEO Dashboard exposure (the underlying
numbers already exist in app/company_health.py's Executive tier and
app/executive_review.py/app/founders.py — this slice doesn't duplicate
them, a later one surfaces them). Each of these already has a real
signal to build on; none needed a new measurement invented here.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.executive import GRADE_THRESHOLDS, grade_for_score
from app.market_data import MarketDataProvider
from app.market_intelligence import compute_liquidity
from app.schemas import (
    CaseStudy,
    CaseStudyCategory,
    CeoDecisionRecord,
    ConfidenceTier,
    DecisionVaultEntry,
    DisciplineReview,
    ExecutiveMeetingLogEntry,
    LiquidityRead,
    MarketIntelligenceRegime,
    PaperTrade,
    SimilarTradeMatch,
    SimilarTradesSummary,
    TradeDecision,
    TradeReportCard,
)

MAX_DECISION_VAULT_ENTRIES = 200

# The three DecisionConfidence factors (app/confidence.py) that
# represent gathered EVIDENCE about the opportunity, as opposed to
# consensus/portfolio-state (Multi-Agent Agreement, Risk Conditions,
# Portfolio Exposure) — see compute_evidence_score()'s own docstring.
# Exact strings match confidence.py's own ConfidenceFactor.name values.
EVIDENCE_FACTOR_NAMES = {"Technical Alignment", "Research Confidence", "News, Macro & Sentiment"}

# The Similarity Engine tries these tiers in order, using the first one
# that yields at least this many matches — see find_similar_vault_entries().
MIN_SIMILAR_MATCHES = 3
# A real mistake pattern is only surfaced as a warning when it accounts
# for at least this share of the matched trades' own linked case studies
# — high enough that a single unlucky trade never triggers a warning.
MISTAKE_WARNING_SHARE = 0.3

PROPOSAL_TIMEFRAME = "1h"
PROPOSAL_CANDLE_COUNT = 30


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_evidence_score(factors: list) -> float:  # noqa: ANN001 - list[ConfidenceFactor], avoids importing the type just for this signature
    """A real sub-aggregate of DecisionConfidence's own evidence-oriented
    factors, renormalized over just their own real weights so the result
    is still a genuine 0-100 weighted average — not the full composite
    (which also folds in Multi-Agent Agreement/Risk Conditions/Portfolio
    Exposure), so evidenceScore and confidenceScore on a DecisionVaultEntry
    always mean two different real things."""
    evidence_factors = [f for f in factors if f.name in EVIDENCE_FACTOR_NAMES]
    total_weight = sum(f.weight for f in evidence_factors)
    if total_weight <= 0:
        return 0.0
    return round(sum(f.score * f.weight for f in evidence_factors) / total_weight, 1)


def _factor_score(factors: list, factor_id: str) -> float | None:  # noqa: ANN001
    return next((f.score for f in factors if f.id == factor_id), None)


def build_vault_entry(
    *,
    entry_id: str,
    trade: PaperTrade,
    decision: TradeDecision,
    discipline_review: DisciplineReview,
    market_regime: MarketIntelligenceRegime,
    market_regime_label: str,
    provider: MarketDataProvider,
    case_study: CaseStudy | None,
    meeting_log_entry: ExecutiveMeetingLogEntry | None,
    ceo_decision: CeoDecisionRecord | None,
    company_dna_change: str | None,
    sim_day: int,
    now: datetime | None = None,
) -> DecisionVaultEntry:
    """Builds one permanent DecisionVaultEntry for a trade that just
    closed this tick, joining every real artifact already generated for
    it (see module docstring). Called once per closed trade with a real
    matched decision_id and discipline_review — the same precondition
    app/nexus.py's own Feature 26 hook already requires, so this never
    runs on a trade with no real process trail to honestly join."""
    now = now or datetime.now(timezone.utc)
    from app.market_intelligence import compute_session  # local import avoids a module-level cycle with market_intelligence's own schemas usage

    session = compute_session(now)
    candles = provider.get_candles(trade.symbol, PROPOSAL_TIMEFRAME, PROPOSAL_CANDLE_COUNT)
    liquidity: LiquidityRead = compute_liquidity(trade.symbol, candles)

    confidence_engine = decision.confidence_engine
    if confidence_engine is not None:
        evidence_score = compute_evidence_score(confidence_engine.factors)
        confidence_score = confidence_engine.score
        confidence_tier: ConfidenceTier = confidence_engine.tier
    else:
        # No real DecisionConfidence exists for this decision (a rare
        # pre-Feature-15 shape) — fall back to the desk's own raw
        # confidence float for both rather than fabricating factors.
        evidence_score = decision.confidence
        confidence_score = decision.confidence
        confidence_tier = "moderate"

    position_sizing_score = _factor_score(discipline_review.factors, "position_sizing_discipline") or 0.0
    patience_score = _factor_score(discipline_review.factors, "patience") or 0.0

    # decision_grade/decision_grade_score are None only for decisions
    # that predate Feature 50 (Part 2/3) — see TradeDecision's own doc
    # comment. Every current trade sets both; this fallback only matters
    # for a save carried forward from before that feature shipped.
    decision_grade = decision.decision_grade or "C"
    decision_grade_score = decision.decision_grade_score if decision.decision_grade_score is not None else 70.0

    return DecisionVaultEntry(
        id=entry_id,
        tradeId=trade.id,
        decisionId=decision.id,
        symbol=trade.symbol,
        simDay=sim_day,
        session=session.current,
        strategyId=None,
        marketRegime=market_regime,
        marketRegimeLabel=market_regime_label,
        liquidityContext=liquidity,
        evidenceScore=evidence_score,
        confidenceScore=confidence_score,
        confidenceTier=confidence_tier,
        capitalAllocationGrade=grade_for_score(position_sizing_score),
        decisionGrade=decision_grade,
        decisionGradeScore=decision_grade_score,
        disciplineTier=discipline_review.tier,
        disciplineScore=discipline_review.score,
        patienceGrade=grade_for_score(patience_score),
        positionSize=trade.quantity,
        entryPrice=trade.entry_price,
        exitPrice=trade.exit_price,
        pnl=trade.pnl,
        pnlPct=trade.pnl_pct,
        holdDurationMinutes=trade.duration_minutes,
        rMultiple=None,
        caseStudyId=case_study.id if case_study else None,
        caseStudyCategory=case_study.category if case_study else None,
        executiveNotes=meeting_log_entry.recommendation_reason if meeting_log_entry else None,
        lessonsLearned=trade.lessons_learned or "",
        companyDnaChange=company_dna_change,
        ceoOverride=bool(ceo_decision and not ceo_decision.agreed_with_ai),
        createdAt=_now_iso(),
    )


def record_vault_entry(vault: list[DecisionVaultEntry], entry: DecisionVaultEntry) -> list[DecisionVaultEntry]:
    """Appends and caps at MAX_DECISION_VAULT_ENTRIES — the same
    "permanent, but a real memory ceiling" resolution every other capped
    history list in this codebase already uses (CaseStudy, CeoDecisionRecord,
    ...), oldest evicted first."""
    updated = [*vault, entry]
    if len(updated) > MAX_DECISION_VAULT_ENTRIES:
        del updated[: len(updated) - MAX_DECISION_VAULT_ENTRIES]
    return updated


def compute_trade_report_card(entry: DecisionVaultEntry) -> TradeReportCard:
    """Pure relabeling of a DecisionVaultEntry's own real fields — see
    TradeReportCard's own doc comment in schemas.py for why Execution/
    Psychology grades aren't here, and why overallTradeQuality is
    deliberately the same value as decisionGrade rather than a third,
    separately-invented composite.

    wouldTakeAgain is a real, checkable rule, never a vibe: True only
    when the Decision Grade cleared B- (the same threshold band
    GRADE_THRESHOLDS already uses) AND no real mistake CaseStudy was
    filed against this exact trade."""
    grade_rank = {grade: i for i, (_, grade) in enumerate(GRADE_THRESHOLDS)}
    decision_rank = grade_rank.get(entry.decision_grade, len(GRADE_THRESHOLDS))
    b_minus_rank = next(i for i, (_, grade) in enumerate(GRADE_THRESHOLDS) if grade == "B-")
    cleared_bar = decision_rank <= b_minus_rank
    had_mistake = entry.case_study_category is not None and entry.case_study_category not in ("disciplined_process", "rigorous_cross_examination", "patient_execution")
    would_take_again = cleared_bar and not had_mistake

    if would_take_again:
        recommendation = f"Yes — Decision Grade {entry.decision_grade} with no filed mistake case study. This is the process to repeat."
    elif had_mistake:
        recommendation = f'No — a real mistake case study ("{entry.case_study_category}") was filed against this exact trade. Review it before repeating this setup.'
    else:
        recommendation = f"No — Decision Grade {entry.decision_grade} falls below the company's B- bar for process quality, regardless of this trade's own P&L."

    return TradeReportCard(
        vaultEntryId=entry.id,
        symbol=entry.symbol,
        evidenceScore=entry.evidence_score,
        confidenceScore=entry.confidence_score,
        capitalAllocationGrade=entry.capital_allocation_grade,
        decisionGrade=entry.decision_grade,
        disciplineGrade=entry.discipline_tier,
        patienceGrade=entry.patience_grade,
        overallTradeQuality=entry.decision_grade,
        wouldTakeAgain=would_take_again,
        recommendation=recommendation,
    )


def find_similar_vault_entries(
    vault: list[DecisionVaultEntry],
    *,
    symbol: str,
    market_regime: MarketIntelligenceRegime,
    confidence_tier: ConfidenceTier,
    exclude_id: str | None = None,
    min_matches: int = MIN_SIMILAR_MATCHES,
) -> tuple[list[DecisionVaultEntry], list[str]]:
    """The Similarity Engine — real, rule-based bucket matching, never a
    fabricated similarity score. Tries three tiers, from most to least
    specific, stopping at the first tier with at least `min_matches`
    real matches (falling through to a broader tier only when the
    narrower one is too thin to be statistically meaningful):

      1. same symbol AND same market regime AND same confidence tier
      2. same market regime AND same confidence tier (any symbol)
      3. same confidence tier alone (broadest — only reached if 1 and 2
         both come up short)

    `min_matches` defaults to the module constant but is a real,
    CEO-configurable read (v0.7 Design Bible Chapter 61's Pattern
    Detection Sensitivity control — see RiskLimits.minSimilarMatches) —
    every other caller keeps today's exact default behavior.

    Returns (matches, matchedOn) — matchedOn names exactly which real
    dimensions this tier used, so the CEO always sees why these trades
    were considered "similar," never a black box."""
    pool = [e for e in vault if e.id != exclude_id]

    tier1 = [e for e in pool if e.symbol == symbol and e.market_regime == market_regime and e.confidence_tier == confidence_tier]
    if len(tier1) >= min_matches:
        return tier1, ["symbol", "marketRegime", "confidenceTier"]

    tier2 = [e for e in pool if e.market_regime == market_regime and e.confidence_tier == confidence_tier]
    if len(tier2) >= min_matches:
        return tier2, ["marketRegime", "confidenceTier"]

    tier3 = [e for e in pool if e.confidence_tier == confidence_tier]
    if tier3:
        return tier3, ["confidenceTier"]

    # Tier 1 still wins over an empty tier3 result — a handful of exact
    # symbol+regime+tier matches is more meaningful than zero results.
    return tier1, ["symbol", "marketRegime", "confidenceTier"]


def summarize_similarity(matches: list[DecisionVaultEntry], matched_on: list[str], *, mistake_warning_share: float = MISTAKE_WARNING_SHARE) -> SimilarTradesSummary:
    """Real aggregate statistics over the Similarity Engine's own match
    set — win rate, average/worst P&L, which regime performed best and
    worst among the matches, and a real Mistake Prevention warning when
    one mistake category dominates the matched trades' own linked case
    studies. `mistake_warning_share` defaults to the module constant but
    is a real, CEO-configurable read (v0.7 Design Bible Chapter 61's
    Pattern Detection Sensitivity control — see
    RiskLimits.mistakeWarningSharePct)."""
    if not matches:
        return SimilarTradesSummary(matchCount=0, matchedOn=matched_on, winRatePct=0.0, avgPnlPct=0.0, worstPnlPct=0.0, examples=[])

    wins = sum(1 for m in matches if m.pnl > 0)
    win_rate_pct = round(wins / len(matches) * 100, 1)
    avg_pnl_pct = round(sum(m.pnl_pct for m in matches) / len(matches), 2)
    worst_pnl_pct = round(min(m.pnl_pct for m in matches), 2)

    by_regime: dict[MarketIntelligenceRegime, list[float]] = {}
    for m in matches:
        by_regime.setdefault(m.market_regime, []).append(m.pnl_pct)
    regime_avgs = {regime: sum(pcts) / len(pcts) for regime, pcts in by_regime.items()}
    best_regime: MarketIntelligenceRegime | None = None
    worst_regime: MarketIntelligenceRegime | None = None
    if regime_avgs:
        ranked = sorted(regime_avgs.items(), key=lambda pair: pair[1])
        worst_regime = ranked[0][0]
        best_regime = ranked[-1][0]

    mistake_categories = [m.case_study_category for m in matches if m.case_study_category is not None and m.case_study_category not in ("disciplined_process", "rigorous_cross_examination", "patient_execution")]
    most_common_mistake: CaseStudyCategory | None = None
    warning: str | None = None
    if mistake_categories:
        counts: dict[CaseStudyCategory, int] = {}
        for c in mistake_categories:
            counts[c] = counts.get(c, 0) + 1
        top_category = max(counts, key=lambda c: counts[c])
        share = counts[top_category] / len(matches)
        if share >= mistake_warning_share:
            most_common_mistake = top_category
            warning = f'{counts[top_category]} of {len(matches)} similar past trades ({share * 100:.0f}%) were "{top_category.replace("_", " ")}" mistakes. Review before proceeding.'

    examples = [
        SimilarTradeMatch(vaultEntryId=m.id, symbol=m.symbol, simDay=m.sim_day, pnlPct=m.pnl_pct, decisionGrade=m.decision_grade)
        for m in sorted(matches, key=lambda m: m.sim_day, reverse=True)[:10]
    ]

    return SimilarTradesSummary(
        matchCount=len(matches),
        matchedOn=matched_on,
        winRatePct=win_rate_pct,
        avgPnlPct=avg_pnl_pct,
        worstPnlPct=worst_pnl_pct,
        bestRegime=best_regime,
        worstRegime=worst_regime,
        mostCommonMistakeCategory=most_common_mistake,
        warning=warning,
        examples=examples,
    )
