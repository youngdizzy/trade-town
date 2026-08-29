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

R-Multiple graduated from "deliberately not here" to real: CEO
directive "Hard Risk Gates 2.0 — Stop-Loss / Position-Risk Enforcement"
gave every real trade a real, ATR-based stop PRICE
(PaperPosition.stopPrice/PaperTrade.stopPrice), so `rMultiple` is now a
genuine `pnl_per_share / risk_per_share` computation (see `_r_multiple()`
below) for any trade closed after that directive — still `None`, never
backfilled or guessed, for every trade closed before it.

WHAT'S DELIBERATELY NOT HERE, and why:

  strategyId                  - CEO directive "Live Trade -> Strategy
                                 Provenance": real, but only ever set
                                 when the CEO explicitly selected a real
                                 Strategy Lab strategy at the moment of
                                 deciding this trade (see
                                 CeoDecisionRecord.strategyId). None for
                                 every trade closed before this field
                                 existed, and for every trade where no
                                 strategy was selected — the honest
                                 majority, never backfilled.
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

from app.exit_efficiency import compute_exit_efficiency
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
    KnowledgeQualityScore,
    LiquidityRead,
    MarketIntelligenceRegime,
    PaperTrade,
    SimilarTradeMatch,
    SimilarTradesSummary,
    TradeDecision,
    TradeReportCard,
)
from app.trade_attribution import compute_trade_attribution

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

# The Knowledge Quality Score's Pattern Frequency component normalizes
# against this cap — reusing the exact same "top 10" figure
# summarize_similarity() already uses for SimilarTradesSummary.examples,
# rather than inventing a new arbitrary number.
PATTERN_FREQUENCY_CAP = 10

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


def _r_multiple(trade: PaperTrade) -> float | None:
    """CEO directive "Hard Risk Gates 2.0 — Stop-Loss / Position-Risk
    Enforcement" — real for the first time: PaperTrade.stop_price (set
    once at open_position() time from app/position_sizing.py's own real
    ATR-based stop distance) is this trade's actual planned risk-per-
    share. `None` (never a fabricated value) whenever no real stop
    existed for this trade — every trade closed before this directive,
    and the honest minority of real trades where no ATR evidence
    existed at open time either."""
    if trade.stop_price is None or trade.entry_price <= 0:
        return None
    risk_per_share = abs(trade.entry_price - trade.stop_price)
    if risk_per_share <= 0:
        return None
    direction = 1 if trade.side == "buy" else -1
    pnl_per_share = (trade.exit_price - trade.entry_price) * direction
    return round(pnl_per_share / risk_per_share, 4)


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
        strategyId=ceo_decision.strategy_id if ceo_decision else None,
        strategyCompiledDefinitionId=ceo_decision.strategy_compiled_definition_id if ceo_decision else None,
        strategyCompiledDefinitionVersion=ceo_decision.strategy_compiled_definition_version if ceo_decision else None,
        decisionSession=ceo_decision.decision_session if ceo_decision else None,
        decisionMarketRegime=ceo_decision.decision_market_regime if ceo_decision else None,
        decisionPrice=ceo_decision.decision_price if ceo_decision else None,
        decisionVolatilityPct=ceo_decision.decision_volatility_pct if ceo_decision else None,
        decisionSessionContext=ceo_decision.decision_session_context if ceo_decision else None,
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
        rMultiple=_r_multiple(trade),
        caseStudyId=case_study.id if case_study else None,
        caseStudyCategory=case_study.category if case_study else None,
        executiveNotes=meeting_log_entry.recommendation_reason if meeting_log_entry else None,
        lessonsLearned=trade.lessons_learned or "",
        companyDnaChange=company_dna_change,
        ceoOverride=bool(ceo_decision and not ceo_decision.agreed_with_ai),
        createdAt=_now_iso(),
    )


def record_vault_entry(
    vault: list[DecisionVaultEntry], entry: DecisionVaultEntry, max_entries: int = MAX_DECISION_VAULT_ENTRIES
) -> list[DecisionVaultEntry]:
    """Appends and caps at max_entries (Design Bible Chapter 61's
    Knowledge Retention Rules CEO control, RiskLimits.maxDecisionVaultEntries
    — defaults to the module constant so every other caller keeps today's
    exact behavior) — the same "permanent, but a real memory ceiling"
    resolution every other capped history list in this codebase already
    uses (CaseStudy, CeoDecisionRecord, ...), oldest evicted first."""
    updated = [*vault, entry]
    if len(updated) > max_entries:
        del updated[: len(updated) - max_entries]
    return updated


TRADE_REPORT_CARD_DATA_HONESTY_NOTE = (
    "Real evidence joined from three sources by this trade's own real tradeId — DecisionVaultEntry, "
    "TradeExitEfficiency, and TradeAttributionRecord. strategyId/strategyProvenanceState reflect the "
    "CEO's own real, explicit strategy selection at decision time (POST /api/executive/decide) — "
    "'known' only when the CEO actually picked one, 'unknown' otherwise (the honest majority; live "
    "proposals still come from the Analyst Desk, not a compiled Strategy Lab definition, so no "
    "strategy is ever assumed). Still genuinely missing, disclosed rather than fabricated: WHY this "
    "trade was exited (no exit-reason taxonomy exists anywhere), its SETUP (no setup taxonomy "
    "exists), and an EXPECTED-vs-ACTUAL comparison (no per-trade expected-outcome record is "
    "persisted)."
)


def compute_trade_report_card(
    entry: DecisionVaultEntry,
    *,
    trade_history: list[PaperTrade],
    decisions: list[TradeDecision],
    ceo_decisions: list[CeoDecisionRecord],
) -> TradeReportCard:
    """Pure relabeling of a DecisionVaultEntry's own real fields — see
    TradeReportCard's own doc comment in schemas.py for why a
    Psychology grade isn't here, and why overallTradeQuality is
    deliberately the same value as decisionGrade rather than a third,
    separately-invented composite.

    wouldTakeAgain is a real, checkable rule, never a vibe: True only
    when the Decision Grade cleared B- (the same threshold band
    GRADE_THRESHOLDS already uses) AND no real mistake CaseStudy was
    filed against this exact trade.

    CEO directive "Command Center + Professional Quant Trading Firm
    Upgrade" — Post-Trade Intelligence: joins in TradeExitEfficiency
    (MAE/MFE/capture) and TradeAttributionRecord (slippage/transaction
    cost/agent contributions/Gatekeeper approval) for this SAME real
    trade, by its own real tradeId — reusing compute_exit_efficiency()/
    compute_trade_attribution() directly rather than re-deriving either.
    `None` on any of the new fields means the real PaperTrade this
    vault entry cites is no longer in trade_history (never fabricated)."""
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

    exit_efficiency = next((r for r in compute_exit_efficiency(trade_history).reads if r.trade_id == entry.trade_id), None)
    trade = next((t for t in trade_history if t.id == entry.trade_id), None)
    attribution = compute_trade_attribution(trade, decisions, ceo_decisions) if trade is not None else None

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
        maePct=exit_efficiency.mae_pct if exit_efficiency is not None else None,
        mfePct=exit_efficiency.mfe_pct if exit_efficiency is not None else None,
        capturePct=exit_efficiency.capture_pct if exit_efficiency is not None else None,
        exitEfficiencyState=exit_efficiency.state if exit_efficiency is not None else None,
        entrySlippageBps=attribution.entry_slippage_bps if attribution is not None else None,
        exitSlippageBps=attribution.exit_slippage_bps if attribution is not None else None,
        transactionCostUsd=attribution.transaction_cost_usd if attribution is not None else None,
        supportingAgents=attribution.supporting_agents if attribution is not None else [],
        opposingAgents=attribution.opposing_agents if attribution is not None else [],
        gatekeeperApproved=attribution.gatekeeper_approved if attribution is not None else None,
        strategyId=attribution.strategy_id if attribution is not None else None,
        strategyProvenanceState=attribution.strategy_provenance_state if attribution is not None else "unavailable",
        strategyCompiledDefinitionId=attribution.strategy_compiled_definition_id if attribution is not None else None,
        strategyCompiledDefinitionVersion=attribution.strategy_compiled_definition_version if attribution is not None else None,
        decisionSession=entry.decision_session,
        decisionMarketRegime=entry.decision_market_regime,
        decisionPrice=entry.decision_price,
        decisionVolatilityPct=entry.decision_volatility_pct,
        decisionSessionContext=entry.decision_session_context,
        dataHonestyNote=TRADE_REPORT_CARD_DATA_HONESTY_NOTE,
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


def compute_knowledge_quality_score(
    entry: DecisionVaultEntry,
    vault: list[DecisionVaultEntry],
    current_sim_day: int,
    *,
    min_matches: int = MIN_SIMILAR_MATCHES,
) -> KnowledgeQualityScore:
    """Design Bible Chapter 61's Knowledge Quality Score. Three real,
    checkable signals — never the brief's own Accuracy/Usefulness/
    Validation dimensions, since no signal anywhere in this codebase
    measures any of those:

      Historical Success — the real win rate of every OTHER Vault entry
      sharing this entry's own symbol/marketRegime/confidenceTier
      profile, reusing the exact same three-tier Similarity Engine bucket
      match the War Room already uses (find_similar_vault_entries()).
      None when the Vault has no comparable entry at all.

      Pattern Frequency — how many other Vault entries share that same
      profile (the match count itself). This is a real proxy for "how
      often has this kind of situation recurred," NOT a literal usage
      counter — nothing in this codebase tracks how many times a
      specific entry was actually shown to the CEO in a real War Room
      session (SimilarTradesSummary is computed fresh per request, never
      logged). Normalized against PATTERN_FREQUENCY_CAP for the
      composite below; the raw count is still returned unnormalized.

      Relevance — how recent this entry is relative to the Vault's own
      real age span (its oldest entry's simDay to `current_sim_day`),
      not an arbitrary fixed decay window.

    overallScore averages whichever of the three are real. When Pattern
    Frequency is 0 (no comparable entry exists at all), Historical
    Success is also None by construction (the Similarity Engine has
    nothing to compute a win rate over) — overallScore falls back to
    Relevance alone rather than letting an empty cohort drag the score
    down, since "no precedent yet" honestly means "not enough evidence,"
    not "poor quality."
    """
    matches, matched_on = find_similar_vault_entries(
        vault,
        symbol=entry.symbol,
        market_regime=entry.market_regime,
        confidence_tier=entry.confidence_tier,
        exclude_id=entry.id,
        min_matches=min_matches,
    )
    summary = summarize_similarity(matches, matched_on)

    oldest_sim_day = min((e.sim_day for e in vault), default=entry.sim_day)
    span = max(current_sim_day - oldest_sim_day, 1)
    age = max(current_sim_day - entry.sim_day, 0)
    relevance_pct = round(max(0.0, min(1.0, 1 - age / span)) * 100, 1)

    if summary.match_count == 0:
        return KnowledgeQualityScore(
            vaultEntryId=entry.id,
            matchedOn=[],
            historicalSuccessPct=None,
            patternFrequency=0,
            relevancePct=relevance_pct,
            overallScore=relevance_pct,
        )

    frequency_component = min(summary.match_count, PATTERN_FREQUENCY_CAP) / PATTERN_FREQUENCY_CAP * 100
    overall_score = round((summary.win_rate_pct + frequency_component + relevance_pct) / 3, 1)
    return KnowledgeQualityScore(
        vaultEntryId=entry.id,
        matchedOn=matched_on,
        historicalSuccessPct=summary.win_rate_pct,
        patternFrequency=summary.match_count,
        relevancePct=relevance_pct,
        overallScore=overall_score,
    )
