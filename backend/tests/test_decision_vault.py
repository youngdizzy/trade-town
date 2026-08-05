"""Covers app/decision_vault.py — the Decision Memory System's Decision
Vault, Trade Report Card, and Similarity Engine (v0.7, "Feature 54" in
commit history — see the module's own docstring for the naming collision
with the already-shipped "Feature 53" Company Certification work).
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.decision_vault import (
    MAX_DECISION_VAULT_ENTRIES,
    MIN_SIMILAR_MATCHES,
    MISTAKE_WARNING_SHARE,
    build_vault_entry,
    compute_evidence_score,
    compute_trade_report_card,
    find_similar_vault_entries,
    record_vault_entry,
    summarize_similarity,
)
from app.market_data import MockMarketDataProvider
from app.schemas import (
    AgentVote,
    CaseStudy,
    CeoDecisionRecord,
    ConfidenceFactor,
    DecisionConfidence,
    DecisionVaultEntry,
    DisciplineFactor,
    DisciplineReview,
    PaperTrade,
    PostDecisionReview,
    TradeDecision,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confidence_engine(
    *,
    score: float = 80.0,
    tier: str = "strong",
    technical: float = 80.0,
    research: float = 80.0,
    news: float = 80.0,
    agreement: float = 80.0,
    risk: float = 80.0,
    exposure: float = 80.0,
) -> DecisionConfidence:
    return DecisionConfidence(
        score=score,
        tier=tier,  # type: ignore[arg-type]
        summary="test summary",
        factors=[
            ConfidenceFactor(
                name="Multi-Agent Agreement",
                score=agreement,
                weight=0.30,
                detail="test",
            ),
            ConfidenceFactor(
                name="Technical Alignment", score=technical, weight=0.20, detail="test"
            ),
            ConfidenceFactor(
                name="Risk Conditions", score=risk, weight=0.20, detail="test"
            ),
            ConfidenceFactor(
                name="Research Confidence", score=research, weight=0.15, detail="test"
            ),
            ConfidenceFactor(
                name="News, Macro & Sentiment", score=news, weight=0.10, detail="test"
            ),
            ConfidenceFactor(
                name="Portfolio Exposure", score=exposure, weight=0.05, detail="test"
            ),
        ],
    )


def _decision(
    *,
    decision_id: str = "decision-proposal-1",
    symbol: str = "NEXA",
    confidence_engine: DecisionConfidence | None = None,
    decision_grade: str | None = "B",
    decision_grade_score: float | None = 85.0,
) -> TradeDecision:
    return TradeDecision(
        id=decision_id,
        symbol=symbol,
        outcome="trade",
        votes=[AgentVote(agentId="echo", choice="buy", reason="trend confirmed")],  # type: ignore[arg-type]
        researchSummary="test research summary",
        technicalSummary="test technical summary",
        fundamentalSummary="test fundamental summary",
        riskSummary="test risk summary",
        supportingAgents=["echo"],  # type: ignore[arg-type]
        opposingAgents=[],  # type: ignore[arg-type]
        confidence=80.0,
        finalReasoning="CEO approved BUY.",
        orderId="pos-1",
        confidenceEngine=confidence_engine
        if confidence_engine is not None
        else _confidence_engine(),
        decisionGrade=decision_grade,  # type: ignore[arg-type]
        decisionGradeScore=decision_grade_score,
        createdAt=_now_iso(),
    )


def _trade(
    *,
    trade_id: str = "trade-1",
    symbol: str = "NEXA",
    pnl: float = 100.0,
    pnl_pct: float = 2.0,
    decision_id: str = "decision-proposal-1",
) -> PaperTrade:
    return PaperTrade(
        id=trade_id,
        symbol=symbol,
        side="buy",  # type: ignore[arg-type]
        quantity=10.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl / 10.0,
        pnl=pnl,
        pnlPct=pnl_pct,
        durationMinutes=120,
        confidence=80.0,
        reason="test reason",
        marketConditions="test conditions",
        supportingAgents=["echo"],  # type: ignore[arg-type]
        opposingAgents=[],  # type: ignore[arg-type]
        lessonsLearned="test lesson learned",
        decisionId=decision_id,
        openedAt=_now_iso(),
        closedAt=_now_iso(),
    )


def _discipline_review(
    *,
    review_id: str = "discipline-1",
    decision_id: str = "decision-proposal-1",
    symbol: str = "NEXA",
    score: float = 80.0,
    tier: str = "sound",
    position_sizing_score: float = 90.0,
    patience_score: float = 70.0,
    outcome: str = "win",
) -> DisciplineReview:
    return DisciplineReview(
        id=review_id,
        decisionId=decision_id,
        symbol=symbol,
        score=score,
        tier=tier,  # type: ignore[arg-type]
        factors=[
            DisciplineFactor(
                id="position_sizing_discipline",
                name="Position Sizing Discipline",
                score=position_sizing_score,
                weight=0.2,
                detail="test",
            ),  # type: ignore[arg-type]
            DisciplineFactor(
                id="patience",
                name="Patience",
                score=patience_score,
                weight=0.2,
                detail="test",
            ),  # type: ignore[arg-type]
        ],
        attendees=["echo"],  # type: ignore[arg-type]
        summary="test summary",
        postDecisionReview=PostDecisionReview(),
        outcome=outcome,  # type: ignore[arg-type]
        tradePnlPct=2.0,
        holdDurationMinutes=120,
        simDay=1,
        createdAt=_now_iso(),
    )


def _case_study(
    *,
    category: str = "acted_too_quickly",
    trade_id: str = "trade-1",
    symbol: str = "NEXA",
) -> CaseStudy:
    return CaseStudy(
        id=f"case-{trade_id}",
        category=category,  # type: ignore[arg-type]
        title="test case study",
        symbol=symbol,
        decisionId="decision-proposal-1",
        timeline=[],
        background="test background",
        decisionProcess="test decision process",
        departmentOpinions=[],
        missedInformation="test missed information",
        lessonsLearned="test lesson",
        recommendedImprovements="test improvement",
        relatedPrinciples=[],
        tradePnlPct=-2.0,
        simDay=1,
        createdAt=_now_iso(),
    )


class TestComputeEvidenceScore:
    def test_renormalizes_over_only_the_three_evidence_factors(self) -> None:
        engine = _confidence_engine(
            technical=100.0,
            research=100.0,
            news=100.0,
            agreement=0.0,
            risk=0.0,
            exposure=0.0,
        )
        assert compute_evidence_score(engine.factors) == 100.0

    def test_ignores_consensus_and_portfolio_factors_entirely(self) -> None:
        low_evidence_high_consensus = _confidence_engine(
            technical=10.0,
            research=10.0,
            news=10.0,
            agreement=100.0,
            risk=100.0,
            exposure=100.0,
        )
        assert compute_evidence_score(low_evidence_high_consensus.factors) == 10.0

    def test_empty_factor_list_returns_zero_rather_than_dividing_by_zero(self) -> None:
        assert compute_evidence_score([]) == 0.0


class TestBuildVaultEntry:
    def test_joins_the_real_artifacts_already_computed_for_the_trade(self) -> None:
        decision = _decision()
        trade = _trade()
        review = _discipline_review()
        entry = build_vault_entry(
            entry_id="vault-trade-1",
            trade=trade,
            decision=decision,
            discipline_review=review,
            market_regime="strong_bull_trend",
            market_regime_label="Strong Bull Trend",
            provider=MockMarketDataProvider(),
            case_study=None,
            meeting_log_entry=None,
            ceo_decision=None,
            company_dna_change=None,
            sim_day=5,
        )
        assert entry.trade_id == "trade-1"
        assert entry.decision_id == "decision-proposal-1"
        assert entry.symbol == "NEXA"
        assert entry.sim_day == 5
        assert entry.market_regime == "strong_bull_trend"
        assert entry.pnl == 100.0
        assert entry.strategy_id is None
        assert entry.r_multiple is None

    def test_evidence_and_confidence_scores_are_genuinely_different_numbers(
        self,
    ) -> None:
        engine = _confidence_engine(
            technical=100.0,
            research=100.0,
            news=100.0,
            agreement=20.0,
            risk=20.0,
            exposure=20.0,
            score=55.0,
        )
        decision = _decision(confidence_engine=engine)
        entry = build_vault_entry(
            entry_id="vault-trade-1",
            trade=_trade(),
            decision=decision,
            discipline_review=_discipline_review(),
            market_regime="sideways_range",
            market_regime_label="Sideways Range",
            provider=MockMarketDataProvider(),
            case_study=None,
            meeting_log_entry=None,
            ceo_decision=None,
            company_dna_change=None,
            sim_day=1,
        )
        assert entry.evidence_score == 100.0
        assert entry.confidence_score == 55.0
        assert entry.evidence_score != entry.confidence_score

    def test_capital_allocation_and_patience_grades_reuse_the_executive_grade_scale(
        self,
    ) -> None:
        review = _discipline_review(position_sizing_score=97.0, patience_score=60.0)
        entry = build_vault_entry(
            entry_id="vault-trade-1",
            trade=_trade(),
            decision=_decision(),
            discipline_review=review,
            market_regime="sideways_range",
            market_regime_label="Sideways Range",
            provider=MockMarketDataProvider(),
            case_study=None,
            meeting_log_entry=None,
            ceo_decision=None,
            company_dna_change=None,
            sim_day=1,
        )
        assert entry.capital_allocation_grade == "A+"
        assert entry.patience_grade == "D"

    def test_missing_decision_grade_falls_back_to_c_for_a_pre_feature_50_decision(
        self,
    ) -> None:
        decision = _decision(decision_grade=None, decision_grade_score=None)
        entry = build_vault_entry(
            entry_id="vault-trade-1",
            trade=_trade(),
            decision=decision,
            discipline_review=_discipline_review(),
            market_regime="sideways_range",
            market_regime_label="Sideways Range",
            provider=MockMarketDataProvider(),
            case_study=None,
            meeting_log_entry=None,
            ceo_decision=None,
            company_dna_change=None,
            sim_day=1,
        )
        assert entry.decision_grade == "C"
        assert entry.decision_grade_score == 70.0

    def test_ceo_override_true_only_when_ceo_disagreed_with_ai(self) -> None:
        agreed = CeoDecisionRecord(
            id="ceo-1",
            proposalId="proposal-1",
            symbol="NEXA",
            category="stock",
            aiRecommendation="buy",
            ceoDecision="buy",
            agreedWithAi=True,
            decisionId="decision-proposal-1",
            createdAt=_now_iso(),
        )  # type: ignore[arg-type]
        disagreed = CeoDecisionRecord(
            id="ceo-2",
            proposalId="proposal-1",
            symbol="NEXA",
            category="stock",
            aiRecommendation="buy",
            ceoDecision="sell",
            agreedWithAi=False,
            decisionId="decision-proposal-1",
            createdAt=_now_iso(),
        )  # type: ignore[arg-type]
        kwargs = dict(
            entry_id="vault-trade-1",
            trade=_trade(),
            decision=_decision(),
            discipline_review=_discipline_review(),
            market_regime="sideways_range",
            market_regime_label="Sideways Range",
            provider=MockMarketDataProvider(),
            case_study=None,
            meeting_log_entry=None,
            company_dna_change=None,
            sim_day=1,
        )
        assert build_vault_entry(ceo_decision=agreed, **kwargs).ceo_override is False
        assert build_vault_entry(ceo_decision=disagreed, **kwargs).ceo_override is True

    def test_case_study_id_and_category_are_stamped_when_one_was_filed(self) -> None:
        case_study = _case_study(category="acted_too_quickly")
        entry = build_vault_entry(
            entry_id="vault-trade-1",
            trade=_trade(),
            decision=_decision(),
            discipline_review=_discipline_review(),
            market_regime="sideways_range",
            market_regime_label="Sideways Range",
            provider=MockMarketDataProvider(),
            case_study=case_study,
            meeting_log_entry=None,
            ceo_decision=None,
            company_dna_change=None,
            sim_day=1,
        )
        assert entry.case_study_id == case_study.id
        assert entry.case_study_category == "acted_too_quickly"


class TestRecordVaultEntry:
    def test_caps_at_max_decision_vault_entries_oldest_evicted_first(self) -> None:
        vault: list[DecisionVaultEntry] = []
        base = build_vault_entry(
            entry_id="vault-0",
            trade=_trade(),
            decision=_decision(),
            discipline_review=_discipline_review(),
            market_regime="sideways_range",
            market_regime_label="Sideways Range",
            provider=MockMarketDataProvider(),
            case_study=None,
            meeting_log_entry=None,
            ceo_decision=None,
            company_dna_change=None,
            sim_day=1,
        )
        for i in range(MAX_DECISION_VAULT_ENTRIES + 10):
            entry = base.model_copy(update={"id": f"vault-{i}"})
            vault = record_vault_entry(vault, entry)
        assert len(vault) == MAX_DECISION_VAULT_ENTRIES
        assert vault[-1].id == f"vault-{MAX_DECISION_VAULT_ENTRIES + 9}"
        assert vault[0].id == "vault-10"

    def test_ceo_configured_max_entries_caps_at_a_lower_real_ceiling(self) -> None:
        vault: list[DecisionVaultEntry] = []
        base = build_vault_entry(
            entry_id="vault-0",
            trade=_trade(),
            decision=_decision(),
            discipline_review=_discipline_review(),
            market_regime="sideways_range",
            market_regime_label="Sideways Range",
            provider=MockMarketDataProvider(),
            case_study=None,
            meeting_log_entry=None,
            ceo_decision=None,
            company_dna_change=None,
            sim_day=1,
        )
        for i in range(15):
            entry = base.model_copy(update={"id": f"vault-{i}"})
            vault = record_vault_entry(vault, entry, max_entries=5)
        assert len(vault) == 5
        assert vault[-1].id == "vault-14"
        assert vault[0].id == "vault-10"

    def test_ceo_configured_max_entries_allows_a_higher_real_ceiling(self) -> None:
        vault: list[DecisionVaultEntry] = []
        base = build_vault_entry(
            entry_id="vault-0",
            trade=_trade(),
            decision=_decision(),
            discipline_review=_discipline_review(),
            market_regime="sideways_range",
            market_regime_label="Sideways Range",
            provider=MockMarketDataProvider(),
            case_study=None,
            meeting_log_entry=None,
            ceo_decision=None,
            company_dna_change=None,
            sim_day=1,
        )
        for i in range(MAX_DECISION_VAULT_ENTRIES + 10):
            entry = base.model_copy(update={"id": f"vault-{i}"})
            vault = record_vault_entry(vault, entry, max_entries=MAX_DECISION_VAULT_ENTRIES + 5)
        assert len(vault) == MAX_DECISION_VAULT_ENTRIES + 5
        assert vault[0].id == "vault-5"


def _vault_entry(
    *,
    entry_id: str,
    symbol: str = "NEXA",
    market_regime: str = "sideways_range",
    confidence_tier: str = "strong",
    decision_grade: str = "B",
    pnl: float = 10.0,
    pnl_pct: float = 1.0,
    case_study_category: str | None = None,
    sim_day: int = 1,
) -> DecisionVaultEntry:
    from app.schemas import LiquidityRead

    return DecisionVaultEntry(
        id=entry_id,
        tradeId=f"trade-{entry_id}",
        decisionId=f"decision-{entry_id}",
        symbol=symbol,
        simDay=sim_day,
        session="new_york",  # type: ignore[arg-type]
        strategyId=None,
        marketRegime=market_regime,  # type: ignore[arg-type]
        marketRegimeLabel="test regime",
        liquidityContext=LiquidityRead(
            symbol=symbol,
            zones=[],
            sweepDetected=False,
            sweepDirection="none",
            liquidityScore=50.0,
            detail="test",
        ),  # type: ignore[arg-type]
        evidenceScore=70.0,
        confidenceScore=70.0,
        confidenceTier=confidence_tier,  # type: ignore[arg-type]
        capitalAllocationGrade="B",  # type: ignore[arg-type]
        decisionGrade=decision_grade,  # type: ignore[arg-type]
        decisionGradeScore=80.0,
        disciplineTier="sound",  # type: ignore[arg-type]
        disciplineScore=75.0,
        patienceGrade="B",  # type: ignore[arg-type]
        positionSize=10.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl / 10.0,
        pnl=pnl,
        pnlPct=pnl_pct,
        holdDurationMinutes=60,
        rMultiple=None,
        caseStudyId=f"case-{entry_id}" if case_study_category else None,
        caseStudyCategory=case_study_category,  # type: ignore[arg-type]
        executiveNotes=None,
        lessonsLearned="test lesson",
        companyDnaChange=None,
        ceoOverride=False,
        createdAt=_now_iso(),
    )


class TestComputeTradeReportCard:
    def test_would_take_again_when_grade_clears_b_minus_and_no_mistake_filed(
        self,
    ) -> None:
        entry = _vault_entry(
            entry_id="v1", decision_grade="A", case_study_category=None
        )
        card = compute_trade_report_card(entry)
        assert card.would_take_again is True
        assert "Yes" in card.recommendation

    def test_not_would_take_again_when_a_real_mistake_was_filed_even_with_a_good_grade(
        self,
    ) -> None:
        entry = _vault_entry(
            entry_id="v1", decision_grade="A", case_study_category="acted_too_quickly"
        )
        card = compute_trade_report_card(entry)
        assert card.would_take_again is False
        assert "acted_too_quickly" in card.recommendation

    def test_not_would_take_again_when_grade_falls_below_b_minus_even_with_no_mistake(
        self,
    ) -> None:
        entry = _vault_entry(
            entry_id="v1", decision_grade="D", case_study_category=None
        )
        card = compute_trade_report_card(entry)
        assert card.would_take_again is False
        assert "B-" in card.recommendation

    def test_a_success_case_study_category_never_counts_as_a_mistake(self) -> None:
        entry = _vault_entry(
            entry_id="v1", decision_grade="A", case_study_category="disciplined_process"
        )
        card = compute_trade_report_card(entry)
        assert card.would_take_again is True

    def test_overall_trade_quality_mirrors_decision_grade_not_a_separately_invented_composite(
        self,
    ) -> None:
        entry = _vault_entry(entry_id="v1", decision_grade="C+")
        card = compute_trade_report_card(entry)
        assert card.overall_trade_quality == "C+"


class TestFindSimilarVaultEntries:
    def test_tier1_exact_symbol_regime_and_tier_match_wins_when_it_has_enough_matches(
        self,
    ) -> None:
        vault = [
            _vault_entry(
                entry_id=f"v{i}",
                symbol="NEXA",
                market_regime="sideways_range",
                confidence_tier="strong",
            )
            for i in range(3)
        ]
        vault += [
            _vault_entry(
                entry_id="other",
                symbol="ZYX",
                market_regime="sideways_range",
                confidence_tier="strong",
            )
        ]
        matches, matched_on = find_similar_vault_entries(
            vault,
            symbol="NEXA",
            market_regime="sideways_range",
            confidence_tier="strong",
        )
        assert len(matches) == 3
        assert matched_on == ["symbol", "marketRegime", "confidenceTier"]

    def test_falls_through_to_tier2_any_symbol_when_tier1_is_too_thin(self) -> None:
        vault = [
            _vault_entry(
                entry_id=f"v{i}",
                symbol="NEXA",
                market_regime="sideways_range",
                confidence_tier="strong",
            )
            for i in range(1)
        ]
        vault += [
            _vault_entry(
                entry_id=f"o{i}",
                symbol="ZYX",
                market_regime="sideways_range",
                confidence_tier="strong",
            )
            for i in range(3)
        ]
        matches, matched_on = find_similar_vault_entries(
            vault,
            symbol="NEXA",
            market_regime="sideways_range",
            confidence_tier="strong",
        )
        assert len(matches) == 4
        assert matched_on == ["marketRegime", "confidenceTier"]

    def test_falls_through_to_tier3_confidence_tier_alone_when_tier2_is_also_too_thin(
        self,
    ) -> None:
        vault = [
            _vault_entry(
                entry_id="v0",
                symbol="NEXA",
                market_regime="sideways_range",
                confidence_tier="strong",
            )
        ]
        vault += [
            _vault_entry(
                entry_id=f"o{i}",
                symbol="ZYX",
                market_regime="expansion",
                confidence_tier="strong",
            )
            for i in range(3)
        ]
        matches, matched_on = find_similar_vault_entries(
            vault,
            symbol="NEXA",
            market_regime="sideways_range",
            confidence_tier="strong",
        )
        assert len(matches) == 4
        assert matched_on == ["confidenceTier"]

    def test_exclude_id_removes_the_trade_comparing_against_itself(self) -> None:
        vault = [
            _vault_entry(
                entry_id=f"v{i}",
                symbol="NEXA",
                market_regime="sideways_range",
                confidence_tier="strong",
            )
            for i in range(MIN_SIMILAR_MATCHES)
        ]
        matches, _ = find_similar_vault_entries(
            vault,
            symbol="NEXA",
            market_regime="sideways_range",
            confidence_tier="strong",
            exclude_id="v0",
        )
        assert all(m.id != "v0" for m in matches)

    def test_no_matches_anywhere_returns_empty(self) -> None:
        matches, matched_on = find_similar_vault_entries(
            [], symbol="NEXA", market_regime="sideways_range", confidence_tier="strong"
        )
        assert matches == []
        assert matched_on == ["symbol", "marketRegime", "confidenceTier"]

    def test_ceo_lowered_min_matches_lets_a_thin_tier1_win(self) -> None:
        # v0.7 Chapter 61 — Pattern Detection Sensitivity. Two tier1
        # matches would normally fall through to tier2 (default
        # MIN_SIMILAR_MATCHES=3); a CEO-lowered floor of 2 keeps tier1.
        vault = [
            _vault_entry(
                entry_id=f"v{i}",
                symbol="NEXA",
                market_regime="sideways_range",
                confidence_tier="strong",
            )
            for i in range(2)
        ]
        vault += [
            _vault_entry(
                entry_id=f"o{i}",
                symbol="ZYX",
                market_regime="sideways_range",
                confidence_tier="strong",
            )
            for i in range(3)
        ]
        matches, matched_on = find_similar_vault_entries(
            vault,
            symbol="NEXA",
            market_regime="sideways_range",
            confidence_tier="strong",
            min_matches=2,
        )
        assert len(matches) == 2
        assert matched_on == ["symbol", "marketRegime", "confidenceTier"]

    def test_ceo_raised_min_matches_forces_a_thinner_tier_to_fall_through(self) -> None:
        vault = [
            _vault_entry(
                entry_id=f"v{i}",
                symbol="NEXA",
                market_regime="sideways_range",
                confidence_tier="strong",
            )
            for i in range(3)
        ]
        vault += [
            _vault_entry(
                entry_id=f"o{i}",
                symbol="ZYX",
                market_regime="sideways_range",
                confidence_tier="strong",
            )
            for i in range(2)
        ]
        matches, matched_on = find_similar_vault_entries(
            vault,
            symbol="NEXA",
            market_regime="sideways_range",
            confidence_tier="strong",
            min_matches=5,
        )
        assert len(matches) == 5
        assert matched_on == ["marketRegime", "confidenceTier"]


class TestSummarizeSimilarity:
    def test_empty_matches_returns_a_real_honest_zero_summary(self) -> None:
        summary = summarize_similarity([], ["symbol"])
        assert summary.match_count == 0
        assert summary.win_rate_pct == 0.0
        assert summary.examples == []

    def test_win_rate_and_avg_pnl_are_computed_from_the_real_matches(self) -> None:
        matches = [
            _vault_entry(entry_id="v1", pnl=10.0, pnl_pct=2.0),
            _vault_entry(entry_id="v2", pnl=-5.0, pnl_pct=-1.0),
        ]
        summary = summarize_similarity(matches, ["symbol"])
        assert summary.match_count == 2
        assert summary.win_rate_pct == 50.0
        assert summary.avg_pnl_pct == 0.5
        assert summary.worst_pnl_pct == -1.0

    def test_best_and_worst_regime_are_ranked_by_real_average_pnl(self) -> None:
        matches = [
            _vault_entry(entry_id="v1", market_regime="strong_bull_trend", pnl_pct=5.0),
            _vault_entry(entry_id="v2", market_regime="strong_bull_trend", pnl_pct=5.0),
            _vault_entry(entry_id="v3", market_regime="high_volatility", pnl_pct=-5.0),
        ]
        summary = summarize_similarity(matches, ["symbol"])
        assert summary.best_regime == "strong_bull_trend"
        assert summary.worst_regime == "high_volatility"

    def test_warning_fires_only_once_a_mistake_category_clears_the_share_threshold(
        self,
    ) -> None:
        below_threshold = [
            _vault_entry(entry_id="v1", case_study_category="acted_too_quickly")
        ] + [_vault_entry(entry_id=f"v{i}") for i in range(2, 6)]
        summary_below = summarize_similarity(below_threshold, ["symbol"])
        assert summary_below.warning is None
        assert summary_below.most_common_mistake_category is None

        n = 5
        mistake_count = int(n * MISTAKE_WARNING_SHARE) + 1
        above_threshold = [
            _vault_entry(entry_id=f"m{i}", case_study_category="acted_too_quickly")
            for i in range(mistake_count)
        ]
        above_threshold += [
            _vault_entry(entry_id=f"c{i}") for i in range(n - mistake_count)
        ]
        summary_above = summarize_similarity(above_threshold, ["symbol"])
        assert summary_above.most_common_mistake_category == "acted_too_quickly"
        assert summary_above.warning is not None
        assert "acted too quickly" in summary_above.warning

    def test_ceo_configured_mistake_warning_share_is_real_and_respected(self) -> None:
        # v0.7 Chapter 61 — Pattern Detection Sensitivity. 1 of 5 matches
        # (20%) is a mistake — below the default 30% share, but a CEO who
        # wants earlier warnings can lower the threshold to catch it.
        matches = [
            _vault_entry(entry_id="m0", case_study_category="acted_too_quickly")
        ] + [_vault_entry(entry_id=f"c{i}") for i in range(1, 5)]
        default_summary = summarize_similarity(matches, ["symbol"])
        assert default_summary.warning is None

        sensitive_summary = summarize_similarity(
            matches, ["symbol"], mistake_warning_share=0.15
        )
        assert sensitive_summary.most_common_mistake_category == "acted_too_quickly"
        assert sensitive_summary.warning is not None

    def test_success_case_study_categories_never_count_toward_the_mistake_warning(
        self,
    ) -> None:
        matches = [
            _vault_entry(entry_id=f"v{i}", case_study_category="disciplined_process")
            for i in range(5)
        ]
        summary = summarize_similarity(matches, ["symbol"])
        assert summary.most_common_mistake_category is None
        assert summary.warning is None

    def test_examples_are_capped_at_ten_and_sorted_most_recent_first(self) -> None:
        matches = [_vault_entry(entry_id=f"v{i}", sim_day=i) for i in range(15)]
        summary = summarize_similarity(matches, ["symbol"])
        assert len(summary.examples) == 10
        assert summary.examples[0].sim_day == 14
        assert summary.examples[-1].sim_day == 5
