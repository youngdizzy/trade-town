"""The Research Sandbox (v0.7 Feature 45). See app/sandbox.py's module
docstring for what this feature extends vs. builds new.
"""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.champion_challenger import get_current_champion
from app.cost_sensitivity import run_cost_sensitivity
from app.data_quality import validate_candle_series
from app.dataset_registry import build_dataset_metadata
from app.ema_pullback_research import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME, run_ema_pullback_research
from app.evaluation_simulator import compare_evaluation_policies
from app.evidence_quality import build_evidence_quality_report
from app.failure_taxonomy import compute_top_failure_modes
from app.feature_registry import feature_versions_for_definition
from app.holdout import freeze_strategy, partition_candles_chronologically, run_holdout_evaluation, validate_holdout
from app.leakage_audit import audit_definition_for_look_ahead
from app.lineage import check_lineage_integrity
from app.market_data import ExternalMarketDataProvider, market_data_provider
from app.market_intelligence import compute_strategy_match
from app.paper_readiness import evaluate_paper_readiness
from app.risk_survival import RISK_PROFILE_TEMPLATES, build_risk_survival_scorecard
from app.portfolio_analyst import analyze_portfolio
from app.parameter_sensitivity import run_parameter_sensitivity
from app.persistence import persist_modules
from app.research_experiment import run_research_experiment
from app.research_discovery import compute_family_research_stats
from app.research_factory import summarize_lesson_evidence
from app.research_loop import compute_benchmark_comparisons, compute_outlier_dependence, derive_research_failure_codes
from app.failure_taxonomy import find_similar_failed_strategies
from app.quant_research_lab import classify_research_relationship, count_experiments_for_family, find_similar_experiments
from app.strategy_families import SUPPORTED_FAMILIES, UNSUPPORTED_FAMILIES
from app.schemas import (
    AdversarialResearchResult,
    AgentId,
    AgentStrategySurvivalScore,
    BacktestSession,
    CandidacyBinning,
    ChallengerComparison,
    ChampionRecord,
    CompiledStrategyBacktestResult,
    CompiledStrategyDefinition,
    CompileStrategyRequest,
    CostSensitivityResult,
    DataQualityReport,
    EmaPullbackTradeRecord,
    EmaPullbackResearchResult,
    EvaluationPolicyComparisonReport,
    EvidenceQualityReport,
    FactoryRunRecord,
    FactoryStatsRead,
    FailedStrategyArchiveEntry,
    FailureModeCount,
    FamilyResearchStats,
    HoldoutEvaluationResult,
    HoldoutValidationReport,
    LessonEvidenceSummary,
    LineageIntegrityIssue,
    LookAheadAuditResult,
    PaperReadinessReport,
    PortfolioResearchReport,
    ResearchDiscoveryCycleRecord,
    ResearchLessonRecord,
    ResearchLoopIterationRecord,
    RiskProfileTemplate,
    RiskSurvivalScorecard,
    StrategyFamily,
    StrategyHypothesis,
    ModelValidationReport,
    ParameterSensitivityResult,
    QuantResearchExperiment,
    QuantResearchExperimentSimilarity,
    ResearchCategory,
    ResearchExperimentRecord,
    Strategy,
    StrategyCertification,
    StrategyComplexityScore,
    StrategyDossier,
    StrategyExecutiveDashboard,
    StrategyExecutiveReview,
    StrategyFounderApproval,
    StrategyHallOfFameEntry,
    StrategyMatch,
    StrategyReview,
    StrategyTournamentResult,
    SubmitQuantResearchExperimentResult,
    SurvivorshipBiasRead,
    TestScenario,
    WalkForwardValidationResult,
)
from app.state import game_state
from app.strategy_compiler import compile_strategy_text, strategy_definition_slug
from app.strategy_complexity import compute_strategy_complexity
from app.strategy_engine import DEFAULT_CANDLES_PER_SYMBOL as ENGINE_DEFAULT_CANDLES_PER_SYMBOL
from app.strategy_engine import run_compiled_strategy_backtest
from app.strategy_lab import compute_agent_strategy_survival, compute_strategy_certification, compute_strategy_executive_dashboard, generate_strategy_dossier
from app.strategy_tournament import run_strategy_tournament
from app.survivorship import check_survivorship_bias
from app.walk_forward import DEFAULT_WINDOW_BARS, run_walk_forward_validation

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


class BacktestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategy_id: str = Field(alias="strategyId")
    scenario: TestScenario = "historical"
    custom_return_bias_pct: float = Field(default=0.0, alias="customReturnBiasPct")
    custom_volatility_bias: float = Field(default=1.0, alias="customVolatilityBias")


class BacktestResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    backtest_sessions: list[BacktestSession] = Field(alias="backtestSessions")


class StrategyIdRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategy_id: str = Field(alias="strategyId")


class LimitedLiveRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategy_id: str = Field(alias="strategyId")
    amount: float


class DecideReviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    review_id: str = Field(alias="reviewId")
    approve: bool


class RetireStrategyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategy_id: str = Field(alias="strategyId")
    reason: str


class RegisterStrategyVersionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    source_text: str = Field(alias="sourceText")
    timeframe: str = "1h"
    created_by: AgentId = Field(default="quant", alias="createdBy")


# CEO directive "TradeTown — Phase 10: Real Data + True Holdout +
# Portfolio Intelligence."
class HoldoutEvaluateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    definition: CompiledStrategyDefinition
    symbol: str = "AAPL"
    timeframe: str | None = None
    candles_per_symbol: int = Field(default=ENGINE_DEFAULT_CANDLES_PER_SYMBOL, alias="candlesPerSymbol")


class PortfolioAnalyzeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    definitions: list[CompiledStrategyDefinition]
    symbols: list[str] | None = None
    timeframe: str | None = None
    candles_per_symbol: int = Field(default=ENGINE_DEFAULT_CANDLES_PER_SYMBOL, alias="candlesPerSymbol")


class EvidenceQualityRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    definition: CompiledStrategyDefinition
    symbols: list[str] | None = None
    timeframe: str | None = None
    candles_per_symbol: int = Field(default=ENGINE_DEFAULT_CANDLES_PER_SYMBOL, alias="candlesPerSymbol")


# CEO directive "TradeTown — Paper-Trading Readiness + Professional
# Strategy Validation Hardening," Section 1.
class PaperReadinessRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    definition: CompiledStrategyDefinition
    symbols: list[str] | None = None
    timeframe: str | None = None
    candles_per_symbol: int = Field(default=ENGINE_DEFAULT_CANDLES_PER_SYMBOL, alias="candlesPerSymbol")
    # Optional — pass a prior `POST /holdout/evaluate` result to include
    # holdout as a real readiness axis. `None` (the default) is honest:
    # this endpoint never runs holdout evaluation automatically.
    holdout: HoldoutValidationReport | None = None


# CEO directive "TradeTown — Phase 11: Strategy Intelligence + Hard-Risk
# Refinement," Section 7. `holdout`/`adversarial`/`portfolio` are all
# optional and never auto-computed here — adversarial testing alone
# costs real, meaningful compute (~40s, per this directive's own
# Section 25 performance note), so this endpoint stays a fast,
# stateless combination layer; pass a prior real result from
# `POST /holdout/evaluate` / a Research Factory candidate's own
# `adversarialResult` / `POST /portfolio-analyst/analyze` to include
# each as a real axis.
class RiskSurvivalRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    definition: CompiledStrategyDefinition
    symbols: list[str] | None = None
    timeframe: str | None = None
    candles_per_symbol: int = Field(default=ENGINE_DEFAULT_CANDLES_PER_SYMBOL, alias="candlesPerSymbol")
    holdout: HoldoutValidationReport | None = None
    adversarial: AdversarialResearchResult | None = None
    portfolio: PortfolioResearchReport | None = None


class CompareChampionChallengerRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    champion_definition: CompiledStrategyDefinition = Field(alias="championDefinition")
    challenger_definition: CompiledStrategyDefinition = Field(alias="challengerDefinition")
    strategy_family: str = Field(alias="strategyFamily")
    hypothesis: str
    proposed_by: AgentId = Field(alias="proposedBy")
    symbols: list[str] | None = None
    timeframe: str | None = None
    candles_per_symbol: int | None = Field(default=None, alias="candlesPerSymbol")


class SubmitResearchLoopIterationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    hypothesis: StrategyHypothesis
    definition: CompiledStrategyDefinition
    symbols: list[str] | None = None
    timeframe: str | None = None
    candles_per_symbol: int | None = Field(default=None, alias="candlesPerSymbol")


class SubmitResearchFactoryRunRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    hypothesis: StrategyHypothesis
    definition: CompiledStrategyDefinition
    max_generations: int | None = Field(default=None, alias="maxGenerations")
    max_total_backtests: int | None = Field(default=None, alias="maxTotalBacktests")
    symbols: list[str] | None = None
    timeframe: str | None = None
    candles_per_symbol: int | None = Field(default=None, alias="candlesPerSymbol")
    # CEO directive "TradeTown — Phase 9: Full Autonomous Quant Research
    # Factory," Phase 5 — `None` (the default) lets app/state.py's
    # submit_research_factory_run() apply its own real, richer defaults
    # (app/research_factory.py's MAX_CHILDREN_PER_PARENT/
    # MAX_RUNTIME_SECONDS) for every NEW live run.
    max_children_per_parent: int | None = Field(default=None, alias="maxChildrenPerParent")
    max_runtime_seconds: int | None = Field(default=None, alias="maxRuntimeSeconds")


class SubmitResearchDiscoveryCycleRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    concept_name: str = Field(alias="conceptName")
    population_size: int = Field(alias="populationSize")
    seed: str
    proposed_by: AgentId = Field(alias="proposedBy")
    families: list[StrategyFamily] | None = None
    symbols: list[str] | None = None
    timeframe: str | None = None
    candles_per_symbol: int | None = Field(default=None, alias="candlesPerSymbol")


class PromoteChallengerRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    comparison_id: str = Field(alias="comparisonId")
    promoted_by: AgentId = Field(alias="promotedBy")
    reasoning: str


class ChampionChallengerFamilyRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    current: ChampionRecord | None
    history: list[ChampionRecord]
    comparisons: list[ChallengerComparison]


class RegisterResearchableStrategyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str
    source_text: str = Field(alias="sourceText")
    timeframe: str = "1h"
    created_by: AgentId = Field(default="quant", alias="createdBy")
    focus_category: ResearchCategory = Field(default="stock", alias="focusCategory")


class RegisterResearchableStrategyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    definition: CompiledStrategyDefinition
    strategy: Strategy | None


class SubmitQuantResearchExperimentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    definition: CompiledStrategyDefinition
    hypothesis: str
    # CEO directive "Quant Research Factory / Strategy Discovery
    # Engine," Phase 1 — required (not Optional) on every NEW filing
    # through the real API, enforcing the directive's own "the agent
    # must explain what would prove the hypothesis wrong" discipline.
    # The underlying persisted QuantResearchExperiment field stays
    # optional only for the experiments filed before this requirement
    # existed — never backfilled, never guessed.
    expected_mechanism: str = Field(alias="expectedMechanism")
    falsification_criteria: str = Field(alias="falsificationCriteria")
    researcher_agent_id: AgentId = Field(alias="researcherAgentId")
    symbols: list[str] | None = None
    timeframe: str | None = None
    candles_per_symbol: int | None = Field(default=None, alias="candlesPerSymbol")


class StrategyTournamentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    definitions: list[CompiledStrategyDefinition]
    symbols: list[str] | None = None
    timeframe: str | None = None
    candles_per_symbol: int | None = Field(default=None, alias="candlesPerSymbol")


class StrategyStateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategies: list[Strategy]
    strategy_reviews: list[StrategyReview] = Field(alias="strategyReviews")
    # v0.7 Feature 52 (Part 1) — only populated by /request-review, which is
    # the one CEO action that files these in the same real moment (see
    # app/state.py's request_strategy_company_review()); every other
    # action here leaves them empty rather than re-sending the whole list.
    strategy_executive_reviews: list[StrategyExecutiveReview] = Field(default_factory=list, alias="strategyExecutiveReviews")
    strategy_founder_approvals: list[StrategyFounderApproval] = Field(default_factory=list, alias="strategyFounderApprovals")
    # v0.7 Quantitative Research & Intelligence System, Piece 4 — Meridian/
    # CIO's independent, advisory-only ModelValidationReport. Only
    # populated by /request-review, the one action that files it (see
    # app/state.py's request_strategy_company_review()); every other
    # action here leaves it empty rather than re-sending the whole list.
    strategy_model_validation: ModelValidationReport | None = Field(default=None, alias="strategyModelValidation")
    # v0.7 Feature 52 (Part 2) — only populated by /retire; exactly one of
    # the two is ever non-empty for a given retirement (see
    # app/strategy_lab.py's generate_strategy_retirement_outcome()).
    strategy_hall_of_fame_entry: StrategyHallOfFameEntry | None = Field(default=None, alias="strategyHallOfFameEntry")
    strategy_failed_archive_entry: FailedStrategyArchiveEntry | None = Field(default=None, alias="strategyFailedArchiveEntry")


@router.post("/backtest", response_model=BacktestResponse)
async def queue_backtest(payload: BacktestRequest) -> BacktestResponse:
    state, error = await game_state.queue_sandbox_backtest(payload.strategy_id, payload.scenario, payload.custom_return_bias_pct, payload.custom_volatility_bias)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return BacktestResponse(backtestSessions=state.backtest_sessions)


@router.post("/begin-paper-trial", response_model=StrategyStateResponse)
async def begin_paper_trial(payload: StrategyIdRequest) -> StrategyStateResponse:
    state, error = await game_state.begin_strategy_paper_trial(payload.strategy_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return StrategyStateResponse(strategies=state.strategies, strategyReviews=state.strategy_reviews)


@router.post("/begin-limited-live", response_model=StrategyStateResponse)
async def begin_limited_live(payload: LimitedLiveRequest) -> StrategyStateResponse:
    state, error = await game_state.begin_strategy_limited_live(payload.strategy_id, payload.amount)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return StrategyStateResponse(strategies=state.strategies, strategyReviews=state.strategy_reviews)


@router.post("/request-review", response_model=StrategyStateResponse)
async def request_company_review(payload: StrategyIdRequest) -> StrategyStateResponse:
    state, error = await game_state.request_strategy_company_review(payload.strategy_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    latest_executive_review = [r for r in state.strategy_executive_reviews if r.strategy_id == payload.strategy_id][-1:]
    latest_founder_approval = [a for a in state.strategy_founder_approvals if a.strategy_id == payload.strategy_id][-1:]
    latest_model_validation = next((r for r in reversed(state.strategy_model_validations) if r.strategy_id == payload.strategy_id), None)
    return StrategyStateResponse(
        strategies=state.strategies,
        strategyReviews=state.strategy_reviews,
        strategyExecutiveReviews=latest_executive_review,
        strategyFounderApprovals=latest_founder_approval,
        strategyModelValidation=latest_model_validation,
    )


@router.post("/decide", response_model=StrategyStateResponse)
async def decide_review(payload: DecideReviewRequest) -> StrategyStateResponse:
    state, error = await game_state.decide_strategy_review(payload.review_id, payload.approve)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return StrategyStateResponse(strategies=state.strategies, strategyReviews=state.strategy_reviews)


@router.post("/retire", response_model=StrategyStateResponse)
async def retire_strategy(payload: RetireStrategyRequest) -> StrategyStateResponse:
    """v0.7 Feature 52 (Part 2) — the only real way a strategy's stage
    ever reaches "retired" (see app/state.py's retire_strategy())."""
    state, error = await game_state.retire_strategy(payload.strategy_id, payload.reason)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    hall_of_fame_entry = next((e for e in reversed(state.strategy_hall_of_fame) if e.strategy_id == payload.strategy_id), None)
    failed_archive_entry = next((e for e in reversed(state.strategy_failed_archive) if e.strategy_id == payload.strategy_id), None)
    return StrategyStateResponse(
        strategies=state.strategies,
        strategyReviews=state.strategy_reviews,
        strategyHallOfFameEntry=hall_of_fame_entry,
        strategyFailedArchiveEntry=failed_archive_entry,
    )


@router.get("/failure-modes", response_model=list[FailureModeCount])
async def top_failure_modes() -> list[FailureModeCount]:
    """CEO directive "TradeTown — Statistical Validation + Research
    Failure Taxonomy," Part 2 (Failure Clustering) — "the CEO should be
    able to see TOP REPEATED FAILURE MODES." A real, computed-fresh
    aggregation over every real `failureCodes` entry across the whole
    permanent Failed Archive (see app/failure_taxonomy.py's
    compute_top_failure_modes()). Read-only, no state mutated."""
    state = await game_state.snapshot()
    return compute_top_failure_modes(state.strategy_failed_archive)


@router.get("/dashboard", response_model=StrategyExecutiveDashboard)
async def strategy_executive_dashboard() -> StrategyExecutiveDashboard:
    """v0.7 Feature 52 (Part 2) — the brief's Executive Dashboard.
    Read-only and computed fresh every call (see app/strategy_lab.py's
    compute_strategy_executive_dashboard()), same reasoning as
    GET /api/sandbox/dossier."""
    state = await game_state.snapshot()
    return compute_strategy_executive_dashboard(
        state.strategies,
        state.simulation_results,
        state.strategy_reviews,
        state.strategy_monte_carlo_results,
        state.strategy_regime_tests,
        state.strategy_executive_reviews,
        state.strategy_hall_of_fame,
        state.strategy_failed_archive,
        sim_day=state.time.day,
    )


@router.get("/agent-survival", response_model=list[AgentStrategySurvivalScore])
async def agent_strategy_survival() -> list[AgentStrategySurvivalScore]:
    """CEO directive "Professional Quant Portfolio Intelligence + Alpha
    Research Engine," Phase 6 (Agent Talent System) — per-agent
    strategy survival, mirroring GET /api/executive/agent-accuracy's
    own real per-agent evidence-floor convention one level up. See
    app/strategy_lab.py's compute_agent_strategy_survival(). Read-only,
    computed fresh every call."""
    state = await game_state.snapshot()
    return compute_agent_strategy_survival(state.strategies, state.strategy_hall_of_fame, state.strategy_failed_archive)


@router.get("/live-strategy-eligibility", response_model=StrategyMatch)
async def live_strategy_eligibility() -> StrategyMatch:
    """CEO directive "Strategy Intelligence + Live Strategy Attribution,"
    Phase 11 — "TODAY: strategies currently eligible / strategies
    currently blocked." `app/market_intelligence.py`'s
    `compute_strategy_match()` already computes exactly this real read
    (which real strategies have real evidence of working, or losing,
    under today's specific regime), but was previously only ever
    computed once per sim-day inside `MarketIntelligenceReport` — which
    that schema's own docstring already discloses "can be up to a day
    stale by the time a proposal fires." This endpoint runs the exact
    same real function fresh, against `state.market_intelligence.regime`
    (the always-current live regime `TradeProposal`/the Gatekeeper
    themselves actually read — see `MarketIntelligenceState`'s own
    docstring), never a second, independently-computed regime read.
    Read-only, computed fresh every call, nothing persisted."""
    state = await game_state.snapshot()
    return compute_strategy_match(state.market_intelligence.regime, state.strategies, state.strategy_reports)


@router.get("/ema-pullback-research", response_model=EmaPullbackResearchResult)
async def ema_pullback_research(
    timeframe: str = Query(DEFAULT_TIMEFRAME),
    candles_per_symbol: int = Query(DEFAULT_CANDLES_PER_SYMBOL, alias="candlesPerSymbol", ge=200, le=20000),
) -> EmaPullbackResearchResult:
    """CEO directive "Professional Trading Firm — Market-Analysis
    Knowledge + Session Intelligence Expansion," Phase 15 — the 50 EMA
    breakout + pullback strategy, converted into a formal, reproducible
    research hypothesis and independently backtested against this
    codebase's own real (mock) candle history (see
    app/ema_pullback_research.py's module docstring for the full rule
    definitions and the SOURCE CLAIM vs. TRADETOWN EVIDENCE distinction
    this endpoint exists to keep honest). Read-only, computed fresh every
    call — nothing here is persisted, and no agent or live trading
    decision is ever wired to this endpoint's result."""
    state = await game_state.snapshot()
    return run_ema_pullback_research(timeframe=timeframe, candles_per_symbol=candles_per_symbol, sim_day=state.time.day)


@router.post("/compile-strategy", response_model=CompiledStrategyDefinition)
async def compile_strategy(payload: CompileStrategyRequest) -> CompiledStrategyDefinition:
    """CEO directive "Professional Quant Trading Firm — Quant
    Intelligence + Market Analysis Completion Phase," Phase F — compiles
    real English-language strategy text into a structured, deterministic,
    reproducible `CompiledStrategyDefinition` (see app/strategy_
    compiler.py's module docstring for exactly what vocabulary this
    recognizes and why ambiguous phrases are refused rather than
    guessed). Stateless — compilation is computed fresh every call and
    nothing is persisted; `status != "compiled"` means the definition is
    not yet backtestable (see its own `detail`/`ambiguities`)."""
    return compile_strategy_text(
        name=payload.name,
        source_text=payload.source_text,
        timeframe=payload.timeframe,
        previous_version=payload.previous_version,
    )


@router.post("/backtest-compiled-strategy", response_model=CompiledStrategyBacktestResult)
async def backtest_compiled_strategy(
    definition: CompiledStrategyDefinition,
    candles_per_symbol: int = Query(ENGINE_DEFAULT_CANDLES_PER_SYMBOL, alias="candlesPerSymbol", ge=200, le=20000),
) -> CompiledStrategyBacktestResult:
    """Same directive, Phase F — the generic backtest runner
    (app/strategy_engine.py) for a `CompiledStrategyDefinition` this
    endpoint's own `POST /compile-strategy` produced. Refuses (with a
    clear, honest reason in `dataHonestyNote`) rather than silently
    guessing whenever `definition.status != "compiled"` or the
    definition references an indicator outside this engine's current v1
    scope — see that module's own module docstring. Read-only, computed
    fresh every call; reuses the existing Monte Carlo bootstrap and
    Model Validator unchanged, never a second risk or validation engine,
    and never wired into any live trading decision."""
    state = await game_state.snapshot()
    return run_compiled_strategy_backtest(definition, timeframe=definition.timeframe, candles_per_symbol=candles_per_symbol, sim_day=state.time.day)


@router.post("/walk-forward-validation", response_model=WalkForwardValidationResult)
async def walk_forward_validation(
    definition: CompiledStrategyDefinition,
    candles_per_symbol: int = Query(ENGINE_DEFAULT_CANDLES_PER_SYMBOL, alias="candlesPerSymbol", ge=200, le=20000),
    window_bars: int = Query(DEFAULT_WINDOW_BARS, alias="windowBars", ge=200, le=20000),
) -> WalkForwardValidationResult:
    """CEO directive "...Quant Intelligence + Market Analysis Completion
    Phase (Next Research + Validation Pass)," item 4 — genuine walk-
    forward validation (see app/walk_forward.py's own module docstring
    for the real, disjoint-chronological-window methodology and its
    disclosed scope boundary vs. walk-forward optimization). Read-only,
    computed fresh every call."""
    return run_walk_forward_validation(definition, timeframe=definition.timeframe, candles_per_symbol=candles_per_symbol, window_bars=window_bars)


@router.post("/parameter-sensitivity", response_model=ParameterSensitivityResult)
async def parameter_sensitivity(
    definition: CompiledStrategyDefinition,
    candles_per_symbol: int = Query(ENGINE_DEFAULT_CANDLES_PER_SYMBOL, alias="candlesPerSymbol", ge=200, le=20000),
) -> ParameterSensitivityResult:
    """Same directive, item 5 — real, one-parameter-at-a-time stop/target
    sensitivity (see app/parameter_sensitivity.py's own module docstring
    for the disclosed sweep methodology). Never surfaces a "best"
    combination by design."""
    return run_parameter_sensitivity(definition, timeframe=definition.timeframe, candles_per_symbol=candles_per_symbol)


@router.post("/cost-sensitivity", response_model=CostSensitivityResult)
async def cost_sensitivity(
    definition: CompiledStrategyDefinition,
    candles_per_symbol: int = Query(ENGINE_DEFAULT_CANDLES_PER_SYMBOL, alias="candlesPerSymbol", ge=200, le=20000),
) -> CostSensitivityResult:
    """Same directive, item 6 — real transaction-cost/slippage
    sensitivity, reusing this codebase's own existing real cost
    constants (see app/cost_sensitivity.py's own module docstring)."""
    return run_cost_sensitivity(definition, timeframe=definition.timeframe, candles_per_symbol=candles_per_symbol)


@router.post("/look-ahead-audit", response_model=LookAheadAuditResult)
async def look_ahead_audit(
    definition: CompiledStrategyDefinition,
    candles_per_symbol: int = Query(ENGINE_DEFAULT_CANDLES_PER_SYMBOL, alias="candlesPerSymbol", ge=200, le=20000),
) -> LookAheadAuditResult:
    """Same directive, item 7 — a real, structural look-ahead audit (the
    truncate-and-re-detect methodology; see app/leakage_audit.py's own
    module docstring)."""
    return audit_definition_for_look_ahead(definition, timeframe=definition.timeframe, candles_per_symbol=candles_per_symbol)


@router.post("/complexity-score", response_model=StrategyComplexityScore)
async def complexity_score(definition: CompiledStrategyDefinition) -> StrategyComplexityScore:
    """CEO directive "TradeTown — 11/10 Strategy Factory + Ruthless
    Backtesting Engine," Section 13 — a real structural complexity
    count over the definition's own compiled rule sequence, needing no
    market data at all (see app/strategy_complexity.py's
    compute_strategy_complexity()). Same already-real number
    `POST /research-experiment` below packages into its own record;
    exposed standalone too for a caller that only wants this one axis.
    Stateless, computed fresh every call, nothing persisted."""
    return compute_strategy_complexity(definition)


@router.get("/survivorship-bias", response_model=SurvivorshipBiasRead)
async def survivorship_bias(symbol: str = Query(..., min_length=1, max_length=16)) -> SurvivorshipBiasRead:
    """Same directive, item 8 — a real, disclosed data-availability
    interface, not a real check (see app/survivorship.py's own module
    docstring for exactly why this codebase has no historical-universe
    data to audit yet)."""
    return check_survivorship_bias(symbol)


@router.get("/data-quality", response_model=DataQualityReport)
async def data_quality(
    symbol: str = Query(..., min_length=1, max_length=16),
    timeframe: str = Query(DEFAULT_TIMEFRAME),
    candles_per_symbol: int = Query(ENGINE_DEFAULT_CANDLES_PER_SYMBOL, alias="candlesPerSymbol", ge=1, le=20000),
) -> DataQualityReport:
    """CEO directive "Phase 9 / Real Market Data + Evidence Integrity
    Foundation," Section 3 — real, mechanical structural checks (never
    an ML "quality score") over one symbol/timeframe's actual retrieved
    candle series (see app/data_quality.py's own module docstring for
    the exact real checks). Read-only, computed fresh every call,
    nothing persisted."""
    candles = market_data_provider.get_candles(symbol, timeframe, candles_per_symbol)
    return validate_candle_series(candles, symbol=symbol, timeframe=timeframe)


@router.post("/research-experiment", response_model=ResearchExperimentRecord)
async def research_experiment(
    definition: CompiledStrategyDefinition,
    candles_per_symbol: int = Query(ENGINE_DEFAULT_CANDLES_PER_SYMBOL, alias="candlesPerSymbol", ge=200, le=20000),
) -> ResearchExperimentRecord:
    """Same directive, item 11 — the Research Desk's one real,
    reproducible experiment record: bundles a real backtest, walk-
    forward validation, parameter sensitivity, cost sensitivity, and a
    look-ahead audit for the same compiled definition into one packaged
    result with a real, disclosed conclusion-synthesis rule (see
    app/research_experiment.py's own module docstring). Read-only,
    computed fresh every call — nothing here is persisted."""
    return run_research_experiment(definition, timeframe=definition.timeframe, candles_per_symbol=candles_per_symbol)


@router.get("/external-market-data/status")
async def external_market_data_status() -> dict[str, object]:
    """CEO directive "TradeTown — Phase 10: Real Data + True Holdout +
    Portfolio Intelligence," Section A — the one real, honest
    self-report (see app/market_data.py's `ExternalMarketDataProvider.
    status()`). No API credentials exist in this environment, so this
    honestly reports `available: false` — never silently swapped for
    the mock provider's own status."""
    status = ExternalMarketDataProvider().status()
    return {"available": status.available, "providerName": status.provider_name, "reason": status.reason}


@router.post("/holdout/evaluate", response_model=HoldoutEvaluationResult)
async def holdout_evaluate(payload: HoldoutEvaluateRequest) -> HoldoutEvaluationResult:
    """CEO directive "Phase 10," Section B — a real, opt-in, structurally
    leak-proof TRAIN/VALIDATION/HOLDOUT evaluation (see
    app/holdout.py's own module docstring). NEVER called automatically
    by the Research Factory's mutation loop — this is a separate,
    explicit call a CEO/agent makes to freeze-and-evaluate one already-
    decided candidate. `status` is honestly `"valid"` only when every
    real structural check in `validate_holdout()` passes; a mock-data
    partition can be a genuinely `"valid"` SPLIT even though the
    underlying candles are simulated — see that function's own
    docstring for why those are different, both-honest claims."""
    definition = payload.definition
    resolved_timeframe = payload.timeframe if payload.timeframe is not None else (definition.timeframe or DEFAULT_TIMEFRAME)
    candles = market_data_provider.get_candles(payload.symbol, resolved_timeframe, payload.candles_per_symbol)
    dataset_metadata = build_dataset_metadata(
        {payload.symbol: candles}, symbols=[payload.symbol], timeframe=resolved_timeframe, candles_per_symbol_requested=payload.candles_per_symbol
    )
    train, validation, holdout = partition_candles_chronologically(candles)
    freeze = freeze_strategy(definition, dataset_version=dataset_metadata.dataset_version, feature_versions=feature_versions_for_definition(definition))
    report = validate_holdout(
        definition,
        train=train,
        validation=validation,
        holdout=holdout,
        dataset_id=dataset_metadata.dataset_id,
        dataset_version=dataset_metadata.dataset_version,
        freeze=freeze,
        report_id=f"holdout-{definition.id}-v{definition.version}",
    )
    return run_holdout_evaluation(definition, payload.symbol, report=report, holdout_candles=holdout, result_id=f"holdout-eval-{definition.id}-v{definition.version}")


@router.post("/portfolio-analyst/analyze", response_model=PortfolioResearchReport)
async def portfolio_analyst_analyze(payload: PortfolioAnalyzeRequest) -> PortfolioResearchReport:
    """CEO directive "Phase 10," Sections C/D — a real cross-strategy
    RESEARCH report over the real per-trade sequences
    `run_compiled_strategy_backtest()` already computes for each
    definition (no second backtest engine — see
    app/portfolio_analyst.py's own module docstring). RESEARCH
    INFORMATION ONLY: never promotes anything, never touches Champion/
    Challenger, Certification, or any risk gate."""
    resolved_timeframe = payload.timeframe or DEFAULT_TIMEFRAME
    candidate_trades: dict[str, list[EmaPullbackTradeRecord]] = {}
    for definition in payload.definitions:
        result = run_compiled_strategy_backtest(definition, symbols=payload.symbols, timeframe=resolved_timeframe, candles_per_symbol=payload.candles_per_symbol)
        candidate_trades[f"{definition.id}-v{definition.version}"] = result.trades
    report_id = "portfolio-" + "-".join(sorted(candidate_trades.keys()))[:120]
    return analyze_portfolio(candidate_trades, candidate_failure_codes={}, report_id=report_id)


@router.post("/evidence-quality", response_model=EvidenceQualityReport)
async def evidence_quality_endpoint(payload: EvidenceQualityRequest) -> EvidenceQualityReport:
    """CEO directive "Phase 10," Section E — a real, structured
    aggregation of already-computed real signals into one disclosed
    evidence STATE (never a blended quality score — see
    app/evidence_quality.py's own module docstring). `holdoutStatus` is
    always `None` here — this endpoint never runs holdout evaluation
    automatically; call `POST /holdout/evaluate` separately and pass
    its own real `status` into a future, richer read if desired."""
    resolved_timeframe = payload.timeframe or payload.definition.timeframe
    record = run_research_experiment(payload.definition, symbols=payload.symbols, timeframe=resolved_timeframe, candles_per_symbol=payload.candles_per_symbol)
    primary_symbol = record.symbols_tested[0] if record.symbols_tested else "AAPL"
    candles = market_data_provider.get_candles(primary_symbol, record.timeframe, payload.candles_per_symbol)
    quality_report = validate_candle_series(candles, symbol=primary_symbol, timeframe=record.timeframe)
    return build_evidence_quality_report(
        definition_id=payload.definition.id,
        definition_version=payload.definition.version,
        data_provenance=(record.dataset_metadata.data_category if record.dataset_metadata is not None else "unavailable"),
        data_quality_valid=quality_report.data_valid,
        point_in_time_verified=record.point_in_time_verified,
        holdout_status=None,
        sample_size=record.backtest.overall.trade_count,
        external_provider_available=ExternalMarketDataProvider().is_available(),
        benchmark_available=len(record.buy_and_hold_baseline) > 0,
        adversarial_coverage=False,
        report_id=f"evidence-{payload.definition.id}-v{payload.definition.version}",
    )


@router.post("/paper-readiness/evaluate", response_model=PaperReadinessReport)
async def paper_readiness_evaluate(payload: PaperReadinessRequest) -> PaperReadinessReport:
    """CEO directive "Paper-Trading Readiness + Professional Strategy
    Validation Hardening," Section 1 — one real, disclosed Paper-Trading
    Readiness verdict combining the existing real research-candidacy
    classification (`app/research_loop.py::classify_candidacy()`) with
    the real Phase 10 evidence-quality state, never a fabricated third
    judgment. See app/paper_readiness.py's own module docstring for the
    exact real reuse and why RNG-only Sandbox `SimulationResult`
    evidence has no path into this endpoint at all — it accepts only a
    `CompiledStrategyDefinition`, which always flows through the real
    `run_research_experiment()` pipeline."""
    resolved_timeframe = payload.timeframe or payload.definition.timeframe
    record = run_research_experiment(payload.definition, symbols=payload.symbols, timeframe=resolved_timeframe, candles_per_symbol=payload.candles_per_symbol)
    primary_symbol = record.symbols_tested[0] if record.symbols_tested else "AAPL"
    candles = market_data_provider.get_candles(primary_symbol, record.timeframe, payload.candles_per_symbol)
    quality_report = validate_candle_series(candles, symbol=primary_symbol, timeframe=record.timeframe)
    evidence_quality = build_evidence_quality_report(
        definition_id=payload.definition.id,
        definition_version=payload.definition.version,
        data_provenance=(record.dataset_metadata.data_category if record.dataset_metadata is not None else "unavailable"),
        data_quality_valid=quality_report.data_valid,
        point_in_time_verified=record.point_in_time_verified,
        holdout_status=payload.holdout.status if payload.holdout is not None else None,
        sample_size=record.backtest.overall.trade_count,
        external_provider_available=ExternalMarketDataProvider().is_available(),
        benchmark_available=len(record.buy_and_hold_baseline) > 0,
        adversarial_coverage=False,
        report_id=f"evidence-{payload.definition.id}-v{payload.definition.version}",
    )

    state = await game_state.snapshot()
    benchmark_comparisons = compute_benchmark_comparisons(record, risk_per_trade_pct=state.risk_limits.risk_per_trade_pct)
    outlier_dependent, _largest_win_share = compute_outlier_dependence(record.backtest.overall)
    similar_experiments = find_similar_experiments(state.quant_research_experiments, hypothesis=payload.definition.source_text, definition_id=payload.definition.id, timeframe=resolved_timeframe)
    similar_failed = find_similar_failed_strategies(state.strategy_failed_archive, hypothesis=payload.definition.source_text, strategy_name=payload.definition.name)
    research_relationship = classify_research_relationship(similar_experiments, similar_failed)
    research_family_experiment_count = count_experiments_for_family(state.quant_research_experiments, definition_name=payload.definition.name)

    return evaluate_paper_readiness(
        record,
        evidence_quality=evidence_quality,
        outlier_dependent=outlier_dependent,
        benchmark_comparisons=benchmark_comparisons,
        research_relationship=research_relationship,
        research_family_experiment_count=research_family_experiment_count,
        tuning_version=payload.definition.version,
        holdout=payload.holdout,
        report_id=f"paper-readiness-{payload.definition.id}-v{payload.definition.version}",
        generated_at=record.generated_at,
    )


@router.get("/risk-profile-templates", response_model=dict[str, RiskProfileTemplate])
async def risk_profile_templates() -> dict[str, RiskProfileTemplate]:
    """CEO directive "Phase 11: Strategy Intelligence + Hard-Risk
    Refinement," Section 2 — the three named, REFERENCE-ONLY risk
    templates. Nothing reads these automatically into any live risk
    limit; the one real, already-centralized live risk gate remains the
    CEO-configured `RiskLimits` + `app/gatekeeper.py`, both untouched by
    this endpoint."""
    return RISK_PROFILE_TEMPLATES


@router.post("/risk-survival/evaluate", response_model=RiskSurvivalScorecard)
async def risk_survival_evaluate(payload: RiskSurvivalRequest) -> RiskSurvivalScorecard:
    """CEO directive "Phase 11," Section 7 — the one real, itemized
    evidence breakdown, never a fake single AI quality score (see
    app/risk_survival.py's own module docstring). `adversarial`/
    `portfolio` are optional and never auto-computed here (adversarial
    testing alone costs real, meaningful compute) — pass a prior real
    result to include each as a real axis; omitting one produces an
    honest `not_available` check, never a silent pass."""
    resolved_timeframe = payload.timeframe or payload.definition.timeframe
    record = run_research_experiment(payload.definition, symbols=payload.symbols, timeframe=resolved_timeframe, candles_per_symbol=payload.candles_per_symbol)
    primary_symbol = record.symbols_tested[0] if record.symbols_tested else "AAPL"
    candles = market_data_provider.get_candles(primary_symbol, record.timeframe, payload.candles_per_symbol)
    quality_report = validate_candle_series(candles, symbol=primary_symbol, timeframe=record.timeframe)
    evidence_quality = build_evidence_quality_report(
        definition_id=payload.definition.id,
        definition_version=payload.definition.version,
        data_provenance=(record.dataset_metadata.data_category if record.dataset_metadata is not None else "unavailable"),
        data_quality_valid=quality_report.data_valid,
        point_in_time_verified=record.point_in_time_verified,
        holdout_status=payload.holdout.status if payload.holdout is not None else None,
        sample_size=record.backtest.overall.trade_count,
        external_provider_available=ExternalMarketDataProvider().is_available(),
        benchmark_available=len(record.buy_and_hold_baseline) > 0,
        adversarial_coverage=payload.adversarial is not None,
        report_id=f"evidence-{payload.definition.id}-v{payload.definition.version}",
    )

    state = await game_state.snapshot()
    benchmark_comparisons = compute_benchmark_comparisons(record, risk_per_trade_pct=state.risk_limits.risk_per_trade_pct)
    outlier_dependent, _largest_win_share = compute_outlier_dependence(record.backtest.overall)
    similar_experiments = find_similar_experiments(state.quant_research_experiments, hypothesis=payload.definition.source_text, definition_id=payload.definition.id, timeframe=resolved_timeframe)
    similar_failed = find_similar_failed_strategies(state.strategy_failed_archive, hypothesis=payload.definition.source_text, strategy_name=payload.definition.name)
    research_relationship = classify_research_relationship(similar_experiments, similar_failed)
    research_family_experiment_count = count_experiments_for_family(state.quant_research_experiments, definition_name=payload.definition.name)
    failure_codes = derive_research_failure_codes(
        record,
        outlier_dependent=outlier_dependent,
        benchmark_comparisons=benchmark_comparisons,
        research_relationship=research_relationship,
        research_family_experiment_count=research_family_experiment_count,
        tuning_version=payload.definition.version,
        risk_per_trade_pct=state.risk_limits.risk_per_trade_pct,
    )

    return build_risk_survival_scorecard(
        record,
        evidence_quality=evidence_quality,
        benchmark_comparisons=benchmark_comparisons,
        failure_codes=failure_codes,
        risk_per_trade_pct=state.risk_limits.risk_per_trade_pct,
        holdout=payload.holdout,
        adversarial=payload.adversarial,
        portfolio=payload.portfolio,
        report_id=f"risk-survival-{payload.definition.id}-v{payload.definition.version}",
        generated_at=record.generated_at,
    )


@router.get("/lineage/check", response_model=list[LineageIntegrityIssue])
async def lineage_check(run_id: str = Query(..., alias="runId")) -> list[LineageIntegrityIssue]:
    """CEO directive "Phase 10," Section H — real, structural lineage
    verification over one already-persisted factory run's own real
    candidates (see app/lineage.py's own module docstring). An empty
    result is itself a real, honest "no break found," never assumed
    without checking."""
    state = await game_state.snapshot()
    run = next((r for r in state.factory_runs if r.id == run_id), None)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No factory run with id {run_id!r}.")
    return check_lineage_integrity(run.candidates)


@router.post("/register-strategy-version", response_model=CompiledStrategyDefinition)
async def register_strategy_version_endpoint(payload: RegisterStrategyVersionRequest) -> CompiledStrategyDefinition:
    """CEO directive "Professional Quant Firm Phase," Feature 37 — real,
    persisted strategy version history (see app/strategy_registry.py).
    Unlike `POST /compile-strategy` (stateless preview, unchanged), this
    endpoint computes the real next version from this strategy's own
    persisted history and permanently records it — `version` on the
    response is never a caller-supplied guess."""
    state, new_definition = await game_state.register_compiled_strategy_version(
        name=payload.name, source_text=payload.source_text, timeframe=payload.timeframe, created_by=payload.created_by
    )
    persist_modules(state)
    return new_definition


@router.get("/strategy-versions", response_model=list[CompiledStrategyDefinition])
async def strategy_versions(name: str = Query(..., min_length=1)) -> list[CompiledStrategyDefinition]:
    """Same directive, Feature 37 — the full, real, persisted version
    history for one strategy name (oldest first), so a CEO/agent can see
    every prior version rather than only the latest. An empty list
    means this strategy has never been registered via
    `POST /register-strategy-version` (a `POST /compile-strategy`
    preview alone never appears here)."""
    state = await game_state.snapshot()
    return state.compiled_strategy_versions.get(strategy_definition_slug(name), [])


@router.post("/champion-challenger/compare", response_model=ChallengerComparison)
async def compare_champion_challenger_endpoint(payload: CompareChampionChallengerRequest) -> ChallengerComparison:
    """CEO directive "TradeTown — 11/10 Self-Improving Quant Agent
    System," Section 1 — real head-to-head comparison. Both real
    backtests run over the IDENTICAL real symbols/timeframe/candle
    window (the directive's own Section 5 Step 5) via the same real
    `run_research_experiment()` pipeline every other research endpoint
    already trusts. Permanently persisted (never deleted, even a
    "champion_retained"/"insufficient_evidence" outcome) — see
    app/champion_challenger.py's own module docstring for the real,
    disclosed promotion rule this does NOT auto-apply."""
    state, comparison = await game_state.submit_champion_challenger_comparison(
        payload.champion_definition,
        payload.challenger_definition,
        strategy_family=payload.strategy_family,
        hypothesis=payload.hypothesis,
        proposed_by=payload.proposed_by,
        symbols=payload.symbols,
        timeframe=payload.timeframe,
        candles_per_symbol=payload.candles_per_symbol,
    )
    persist_modules(state)
    return comparison


@router.post("/champion-challenger/promote", response_model=ChampionRecord)
async def promote_challenger_endpoint(payload: PromoteChallengerRequest) -> ChampionRecord:
    """Same directive, Section 1 — the one real, explicit CEO/agent
    action that ever changes the current champion for a strategy
    family (matching Section 31: "agents cannot... secretly change
    production strategies"). `400` when the named comparison doesn't
    exist or its own real verdict was not "challenger_recommended" —
    see app/champion_challenger.py's promote_challenger()."""
    try:
        state, record = await game_state.promote_champion_challenger(comparison_id=payload.comparison_id, promoted_by=payload.promoted_by, reasoning=payload.reasoning)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    persist_modules(state)
    return record


@router.get("/champion-challenger/{strategy_family}", response_model=ChampionChallengerFamilyRead)
async def champion_challenger_family(strategy_family: str) -> ChampionChallengerFamilyRead:
    """Same directive, Section 1 — the real, full picture for one
    strategy family: the current champion (derived as the most recent
    real promotion, never a separate driftable pointer — see
    app/champion_challenger.py's get_current_champion()), its full real
    promotion history, and every real comparison ever run for this
    family (including ones that retained the champion — never deleted,
    matching Section 16 "never delete rejected versions"). Read-only,
    computed fresh every call."""
    state = await game_state.snapshot()
    current = get_current_champion(state.champion_history, strategy_family=strategy_family)
    history = [c for c in state.champion_history if c.strategy_family == strategy_family]
    comparisons = [c for c in state.challenger_comparisons if c.strategy_family == strategy_family]
    return ChampionChallengerFamilyRead(current=current, history=history, comparisons=comparisons)


@router.post("/research-loop/run", response_model=ResearchLoopIterationRecord)
async def run_research_loop_iteration_endpoint(payload: SubmitResearchLoopIterationRequest) -> ResearchLoopIterationRecord:
    """CEO directive "TradeTown — Next Major Implementation Pass, Phase
    4-6: Self-Improving Strategy Factory + Validation Funnel" — the one
    real entry point for the full research funnel (see
    app/research_loop.py's own module docstring for the complete real
    architecture and its disclosed scope boundaries). Runs the real,
    already-existing `run_research_experiment()` pipeline (no duplicate
    backtest math), computes a real benchmark comparison/scorecard/
    failure-code diagnosis/candidacy binning, checks the permanent
    Failed Archive and prior experiments for research memory, and
    permanently persists both the iteration and a real, templated
    self-improvement lesson. Purely informational triage — never
    gates or feeds Certification/Hall-of-Fame/Champion-Challenger,
    which stay the sole, unmodified, authoritative promotion path."""
    state, iteration = await game_state.submit_research_loop_iteration(
        payload.hypothesis,
        payload.definition,
        symbols=payload.symbols,
        timeframe=payload.timeframe,
        candles_per_symbol=payload.candles_per_symbol,
    )
    persist_modules(state)
    return iteration


@router.get("/research-loop/iterations", response_model=list[ResearchLoopIterationRecord])
async def research_loop_iterations(
    strategy_family: str | None = Query(default=None), candidacy: CandidacyBinning | None = Query(default=None)
) -> list[ResearchLoopIterationRecord]:
    """Same directive — the full, real, permanent iteration history,
    optionally filtered to one real strategy family and/or one real
    candidacy binning. CEO directive "TradeTown — Phase 7: Autonomous
    Strategy Evolution Engine," Section 18 — `candidacy` is the real,
    reused way to "inspect rejected candidates"/"inspect survivors"
    (e.g. `?candidacy=accepted`) without a second, duplicate endpoint.
    Read-only."""
    state = await game_state.snapshot()
    iterations = state.research_iterations
    if strategy_family is not None:
        iterations = [i for i in iterations if i.strategy_family == strategy_family]
    if candidacy is not None:
        iterations = [i for i in iterations if i.candidacy == candidacy]
    return iterations


@router.get("/research-loop/lessons", response_model=list[ResearchLessonRecord])
async def research_loop_lessons(strategy_family: str | None = Query(default=None)) -> list[ResearchLessonRecord]:
    """Same directive, Section 9 — the real, permanent self-improvement
    memory, optionally filtered to one real strategy family. Read-only."""
    state = await game_state.snapshot()
    lessons = state.research_lessons
    if strategy_family is not None:
        lessons = [lesson for lesson in lessons if lesson.strategy_family == strategy_family]
    return lessons


@router.get("/research-loop/lessons/evidence", response_model=list[LessonEvidenceSummary])
async def research_loop_lesson_evidence(strategy_family: str | None = Query(default=None)) -> list[LessonEvidenceSummary]:
    """CEO directive "TradeTown — Phase 7: Autonomous Strategy Evolution
    Engine," Section 12 — "memory is evidence, not truth." Computed
    fresh (see app/research_factory.py's own `summarize_lesson_evidence()`
    docstring for the exact real methodology); never stored on
    ResearchLessonRecord itself, so it always reflects the current full
    archive."""
    state = await game_state.snapshot()
    lessons = state.research_lessons
    if strategy_family is not None:
        lessons = [lesson for lesson in lessons if lesson.strategy_family == strategy_family]
    return summarize_lesson_evidence(lessons)


@router.post("/research-factory/run", response_model=FactoryRunRecord)
async def run_research_factory_run_endpoint(payload: SubmitResearchFactoryRunRequest) -> FactoryRunRecord:
    """CEO directive "TradeTown — Phase 7: Autonomous Strategy Evolution
    Engine" — the one real entry point for the full, bounded,
    multi-generation OBSERVE->GENERATE->MUTATE->COMPILE->BACKTEST->
    VALIDATE->STRESS->COMPARE->ACCEPT-OR-BIN->LEARN loop (see
    app/research_factory.py's own module docstring for the complete
    real architecture and disclosed scope boundaries). Every generation
    reuses the exact same real funnel `POST /research-loop/run` already
    uses — this endpoint's only new behavior is automatically compiling
    and re-testing each real, bounded, deterministic mutation. Never
    calls Champion/Challenger or any promotion path — a real survivor
    is only ever LABELED eligible; a separate, explicit, unmodified
    `POST /champion-challenger/compare` call is still required.

    CEO directive "TradeTown — Phase 9: Full Autonomous Quant Research
    Factory" — every generation now also runs a real adversarial attack
    + Research Council pass (see app/research_factory.py's own updated
    module docstring), and `maxChildrenPerParent`/`maxRuntimeSeconds`
    (both optional; `None` applies this codebase's own real, disclosed
    defaults) enable real, bounded tree-shaped branching: up to that
    many real sibling mutation candidates per generation, ranked by a
    robustness-first (never raw-return-first) comparator."""
    state, run = await game_state.submit_research_factory_run(
        payload.hypothesis,
        payload.definition,
        max_generations=payload.max_generations,
        max_total_backtests=payload.max_total_backtests,
        symbols=payload.symbols,
        timeframe=payload.timeframe,
        candles_per_symbol=payload.candles_per_symbol,
        max_children_per_parent=payload.max_children_per_parent,
        max_runtime_seconds=payload.max_runtime_seconds,
    )
    persist_modules(state)
    return run


@router.get("/research-factory/runs", response_model=list[FactoryRunRecord])
async def research_factory_runs(strategy_family: str | None = Query(default=None)) -> list[FactoryRunRecord]:
    """Same directive — the full, real, permanent factory-run history,
    optionally filtered to one real strategy family. Read-only."""
    state = await game_state.snapshot()
    runs = state.factory_runs
    if strategy_family is not None:
        runs = [r for r in runs if r.strategy_family == strategy_family]
    return runs


@router.get("/research-factory/runs/{run_id}", response_model=FactoryRunRecord)
async def research_factory_run_detail(run_id: str) -> FactoryRunRecord:
    """Same directive, Section 18 — one real factory run's full detail:
    every candidate, its real lineage, and its real decision reason.
    404 when no run with this id exists."""
    state = await game_state.snapshot()
    run = next((r for r in state.factory_runs if r.id == run_id), None)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No real factory run found with id '{run_id}'.")
    return run


@router.get("/research-factory/lineage/{strategy_family}", response_model=list[ResearchLoopIterationRecord])
async def research_factory_lineage(strategy_family: str) -> list[ResearchLoopIterationRecord]:
    """Same directive, Section 18 — "inspect strategy lineage." Reuses
    the already-real, already-persisted `research_iterations` (every
    factory generation's own real `ResearchLoopIterationRecord` is
    appended there, never stored twice) rather than a second lineage
    store; the real lineage chain itself is reconstructable from each
    iteration's own `hypothesis.parent_definition_id`/
    `hypothesis.generation` fields. Oldest first, so ancestry reads
    top-to-bottom."""
    state = await game_state.snapshot()
    return [i for i in state.research_iterations if i.strategy_family == strategy_family]


@router.get("/research-factory/stats", response_model=FactoryStatsRead)
async def research_factory_stats() -> FactoryStatsRead:
    """Same directive, Section 20 — real, decomposable, factory-wide
    observability across every persisted `FactoryRunRecord`. Never a
    fabricated "AI quality score" — every field is a direct count or a
    direct pass-through of already-real per-run fields."""
    state = await game_state.snapshot()
    runs = state.factory_runs
    # A real, disclosed, simple tally: how many real runs listed this
    # exact failure code among their own top-5 rejection reasons — never
    # a fabricated cross-run sum of the per-run counts embedded in each
    # reason string (which would double-count differently-sized runs).
    rejection_counter: Counter[str] = Counter()
    for run in runs:
        for reason in run.top_rejection_reasons:
            code = reason.rsplit(" (", 1)[0]
            rejection_counter[code] += 1
    return FactoryStatsRead(
        totalRuns=len(runs),
        totalCandidates=sum(r.candidates_generated for r in runs),
        totalSurvivors=sum(len(r.survivor_candidate_ids) for r in runs),
        totalRejected=sum(r.candidates_rejected for r in runs),
        totalCompileRejected=sum(1 for r in runs for c in r.candidates if c.lifecycle_stage == "compile_rejected"),
        topRejectionReasons=[code for code, _count in rejection_counter.most_common(5)],
    )


@router.post("/research-discovery/run", response_model=ResearchDiscoveryCycleRecord)
async def run_research_discovery_cycle_endpoint(payload: SubmitResearchDiscoveryCycleRequest) -> ResearchDiscoveryCycleRecord:
    """CEO directive "TradeTown — Phase 8: Autonomous Strategy Discovery
    + Adversarial Research Engine" — the one real entry point for a full
    discovery cycle: a controlled, deterministic candidate POPULATION
    across multiple real, compiler-supported strategy families (see
    app/strategy_families.py), each real near-duplicate pruned before
    spending real research budget, each real survivor independently
    backtested through the unmodified existing funnel AND attacked via
    app/adversarial_research.py's real outlier/worst-period/sequence/
    extended-cost/regime attack suite. Never calls Champion/Challenger
    or any promotion path — see app/research_discovery.py's own module
    docstring for the complete real architecture and disclosed scope
    boundary (one real generation per population member, never full
    recursive multi-generation evolution — any promising candidate can
    still be hand-picked and evolved further via the existing,
    unmodified `POST /research-factory/run`)."""
    state, record = await game_state.submit_research_discovery_cycle(
        concept_name=payload.concept_name,
        population_size=payload.population_size,
        seed=payload.seed,
        proposed_by=payload.proposed_by,
        families=tuple(payload.families) if payload.families else None,
        symbols=payload.symbols,
        timeframe=payload.timeframe,
        candles_per_symbol=payload.candles_per_symbol,
    )
    persist_modules(state)
    return record


@router.get("/research-discovery/cycles", response_model=list[ResearchDiscoveryCycleRecord])
async def research_discovery_cycles() -> list[ResearchDiscoveryCycleRecord]:
    """Same directive — the full, real, permanent discovery-cycle
    history, never overwritten. Read-only."""
    state = await game_state.snapshot()
    return state.discovery_cycles


@router.get("/research-discovery/cycles/{cycle_id}", response_model=ResearchDiscoveryCycleRecord)
async def research_discovery_cycle_detail(cycle_id: str) -> ResearchDiscoveryCycleRecord:
    """Same directive — one real discovery cycle's full detail,
    including every candidate's real adversarial attack results and
    failure boundaries. 404 when no cycle with this id exists."""
    state = await game_state.snapshot()
    cycle = next((c for c in state.discovery_cycles if c.id == cycle_id), None)
    if cycle is None:
        raise HTTPException(status_code=404, detail=f"No real discovery cycle found with id '{cycle_id}'.")
    return cycle


@router.get("/research-discovery/families", response_model=list[FamilyResearchStats])
async def research_discovery_family_stats() -> list[FamilyResearchStats]:
    """Same directive, Section 8J — real, computed-fresh per-family
    statistics across every real candidate ever generated, over every
    real, persisted `ResearchDiscoveryCycleRecord`. Read-only."""
    state = await game_state.snapshot()
    all_candidates = [c for cycle in state.discovery_cycles for c in cycle.candidates]
    return compute_family_research_stats(all_candidates)


@router.get("/research-discovery/supported-families")
async def research_discovery_supported_families() -> dict[str, object]:
    """Same directive, Section 8A — the real, disclosed set of
    compiler-supported families this codebase can safely generate, and
    the real, disclosed reasons every requested-but-unsupported family
    (mean_reversion/volatility_expansion/volatility_contraction/
    regime_conditioned) was NOT faked. See app/strategy_families.py's
    own module docstring for the full real trace."""
    return {"supported": list(SUPPORTED_FAMILIES), "unsupported": UNSUPPORTED_FAMILIES}


@router.post("/register-researchable-strategy", response_model=RegisterResearchableStrategyResponse)
async def register_researchable_strategy_endpoint(payload: RegisterResearchableStrategyRequest) -> RegisterResearchableStrategyResponse:
    """CEO directive "Strategy Intelligence + Live Strategy Attribution"
    — the real Strategy Lab <-> CompiledStrategyDefinition identity
    bridge (see app/strategy_registry.py's own module docstring and
    register_researchable_strategy() for the full real logic). Unlike
    `POST /register-strategy-version` (persists rules only), this also
    creates a real, new Strategy Lab `Strategy` — but only when
    `source_text` actually compiled (`status == "compiled"`); an
    ambiguous/invalid text still returns its own real `definition` (with
    real `ambiguities`/`detail` explaining why) and a `null` `strategy`,
    never a fabricated link. 400 if a Strategy with this exact real name
    already exists — this endpoint is for genuinely new strategies."""
    try:
        state, new_definition, new_strategy = await game_state.register_researchable_strategy(
            name=payload.name,
            description=payload.description,
            source_text=payload.source_text,
            timeframe=payload.timeframe,
            created_by=payload.created_by,
            focus_category=payload.focus_category,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    persist_modules(state)
    return RegisterResearchableStrategyResponse(definition=new_definition, strategy=new_strategy)


@router.post("/quant-research-lab/experiments", response_model=SubmitQuantResearchExperimentResult)
async def submit_quant_research_experiment(payload: SubmitQuantResearchExperimentRequest) -> SubmitQuantResearchExperimentResult:
    """CEO directive "Professional Quant Firm Phase," Feature 36 — files
    a real, hypothesis-driven experiment into the Quant Research Lab.
    Runs the same real `run_research_experiment()` pipeline as
    `POST /research-experiment` (no duplicate backtest math), then
    permanently persists the result — a deliberate, disclosed departure
    from this directive family's usual CAGS convention (see
    `QuantResearchExperiment`'s own docstring). `similarExperiments` on
    the response surfaces any real near-duplicate already on file (the
    directive's own "check before creating a new experiment whether an
    equivalent one exists") without blocking the new filing.

    CEO directive "Quant Research Factory / Strategy Discovery Engine,"
    Phase 1 — `expectedMechanism`/`falsificationCriteria` are now
    required on the request: real discipline, not free-text padding —
    a filing must state what would prove it wrong before it's accepted."""
    state, result = await game_state.submit_quant_research_experiment(
        payload.definition,
        hypothesis=payload.hypothesis,
        researcher_agent_id=payload.researcher_agent_id,
        symbols=payload.symbols,
        timeframe=payload.timeframe,
        candles_per_symbol=payload.candles_per_symbol,
        expected_mechanism=payload.expected_mechanism,
        falsification_criteria=payload.falsification_criteria,
    )
    persist_modules(state)
    return result


@router.get("/quant-research-lab/experiments", response_model=list[QuantResearchExperiment])
async def search_quant_research_experiments(
    symbol: str | None = Query(default=None),
    definition_id: str | None = Query(default=None, alias="definitionId"),
    timeframe: str | None = Query(default=None),
    agent_id: str | None = Query(default=None, alias="agentId"),
    outcome: str | None = Query(default=None),
) -> list[QuantResearchExperiment]:
    """Same directive, Feature 36 — real search over every permanently-
    persisted experiment (most recent first), so a CEO/agent can check
    prior research before commissioning new work. Every filter is
    optional and real (a direct field match against the persisted
    record); an empty result is itself a real, honest answer ("nothing
    on file"), never fabricated evidence."""
    state = await game_state.snapshot()
    results = list(reversed(state.quant_research_experiments))
    if symbol is not None:
        results = [e for e in results if symbol in e.record.symbols_tested]
    if definition_id is not None:
        results = [e for e in results if e.record.definition_id == definition_id]
    if timeframe is not None:
        results = [e for e in results if e.record.timeframe == timeframe]
    if agent_id is not None:
        results = [e for e in results if e.researcher_agent_id == agent_id]
    if outcome is not None:
        results = [e for e in results if e.outcome == outcome]
    return results


@router.get("/quant-research-lab/similar", response_model=list[QuantResearchExperimentSimilarity])
async def check_similar_quant_research_experiments(
    hypothesis: str = Query(..., min_length=1),
    definition_id: str = Query(..., alias="definitionId"),
    timeframe: str = Query(...),
) -> list[QuantResearchExperimentSimilarity]:
    """Same directive, Feature 36 — a real, standalone duplicate check a
    CEO/agent can run BEFORE spending real compute on
    `POST /quant-research-lab/experiments` (that endpoint also runs
    this same check and surfaces it on its own response)."""
    state = await game_state.snapshot()
    return find_similar_experiments(state.quant_research_experiments, hypothesis=hypothesis, definition_id=definition_id, timeframe=timeframe)


@router.post("/strategy-tournament", response_model=StrategyTournamentResult)
async def strategy_tournament(payload: StrategyTournamentRequest) -> StrategyTournamentResult:
    """CEO directive "Professional Quant Firm Phase," Feature 40 — the
    Quant Strategy Tournament (see app/strategy_tournament.py's own
    module docstring for the full, disclosed round-by-round rule and
    the one architecturally-blocked round). Read-only and computed
    fresh every call — every candidate is run through the same real
    `run_research_experiment()` pipeline once each, no duplicate
    backtest math, nothing persisted."""
    if len(payload.definitions) < 2:
        raise HTTPException(status_code=400, detail="A tournament needs at least 2 candidate strategies to compare.")
    return run_strategy_tournament(payload.definitions, symbols=payload.symbols, timeframe=payload.timeframe, candles_per_symbol=payload.candles_per_symbol)


@router.get("/certification", response_model=StrategyCertification)
async def strategy_certification(strategy_id: str = Query(..., alias="strategyId")) -> StrategyCertification:
    """v0.7 Feature 53 — Company Certification. Read-only and computed
    fresh every call (see app/strategy_lab.py's
    compute_strategy_certification()): every requirement reads an
    already-real Feature 52 artifact, so "certified" is always a live
    read of the strategy's own current real state — including a real,
    automatic drop to uncertified the moment its Health degrades. No
    game-state lock needed — nothing here mutates the save."""
    state = await game_state.snapshot()
    strategy = next((s for s in state.strategies if s.id == strategy_id), None)
    if strategy is None:
        raise HTTPException(status_code=404, detail="No strategy found with that id.")
    review = next((r for r in reversed(state.strategy_reviews) if r.strategy_id == strategy_id), None)
    monte_carlo = next((r for r in reversed(state.strategy_monte_carlo_results) if r.strategy_id == strategy_id), None)
    regime_test = next((r for r in reversed(state.strategy_regime_tests) if r.strategy_id == strategy_id), None)
    executive_review = next((r for r in reversed(state.strategy_executive_reviews) if r.strategy_id == strategy_id), None)
    founder_approval = next((r for r in reversed(state.strategy_founder_approvals) if r.strategy_id == strategy_id), None)
    health = next((r for r in reversed(state.strategy_health_assessments) if r.strategy_id == strategy_id), None)
    # CEO directive "Professional Research → Certification → Paper →
    # Capital Allocation Pipeline" — reuses the exact same real Research
    # Desk modules the Sandbox's own on-demand endpoints below already
    # call, so a strategy's certification finally reflects real
    # look-ahead/cost-sensitivity/walk-forward validation instead of
    # only this module's own placeholder-RNG simulations. None of the
    # three when the strategy has no compiled_definition_id yet — see
    # compute_strategy_certification()'s own docstring for why that's
    # an honest failure, not a silent pass.
    look_ahead_audit: LookAheadAuditResult | None = None
    cost_sensitivity_result: CostSensitivityResult | None = None
    walk_forward_result: WalkForwardValidationResult | None = None
    if strategy.compiled_definition_id is not None:
        versions = state.compiled_strategy_versions.get(strategy.compiled_definition_id, [])
        definition = versions[-1] if versions else None
        if definition is not None:
            look_ahead_audit = audit_definition_for_look_ahead(definition)
            cost_sensitivity_result = run_cost_sensitivity(definition)
            walk_forward_result = run_walk_forward_validation(definition)
    return compute_strategy_certification(
        strategy, state.simulation_results, review, monte_carlo, regime_test, executive_review, founder_approval, health, look_ahead_audit, cost_sensitivity_result, walk_forward_result
    )


@router.get("/model-validation", response_model=ModelValidationReport | None)
async def strategy_model_validation(strategy_id: str = Query(..., alias="strategyId")) -> ModelValidationReport | None:
    """v0.7 Quantitative Research & Intelligence System, Piece 4 —
    Meridian/CIO's most recent independent, advisory-only validation
    report for this strategy. Read-only; returns None if the strategy
    has never been through Company Review yet (see app/state.py's
    request_strategy_company_review(), the one real place this is
    generated)."""
    state = await game_state.snapshot()
    strategy = next((s for s in state.strategies if s.id == strategy_id), None)
    if strategy is None:
        raise HTTPException(status_code=404, detail="No strategy found with that id.")
    return next((r for r in reversed(state.strategy_model_validations) if r.strategy_id == strategy_id), None)


@router.get("/dossier", response_model=StrategyDossier)
async def strategy_dossier(strategy_id: str = Query(..., alias="strategyId")) -> StrategyDossier:
    """v0.7 Feature 52 (Part 1) — the brief's auto-generated professional
    Strategy Report. Read-only and computed fresh every call (see
    app/strategy_lab.py's generate_strategy_dossier()): every field it
    returns already lives somewhere permanent (StrategyReport/Review/
    MonteCarloResult/RegimeTestReport/LiquidityValidation/
    ExecutiveReview/FounderApproval), so this is a synthesis, not a
    second source of truth — matches GET /api/executive/intelligence's
    same no-lock-needed, compute-on-request pattern."""
    state = await game_state.snapshot()
    strategy = next((s for s in state.strategies if s.id == strategy_id), None)
    if strategy is None:
        raise HTTPException(status_code=404, detail="No strategy found with that id.")
    return generate_strategy_dossier(
        strategy,
        state.strategy_reports,
        state.strategy_reviews,
        state.strategy_monte_carlo_results,
        state.strategy_regime_tests,
        state.strategy_liquidity_validations,
        state.strategy_executive_reviews,
        state.strategy_founder_approvals,
    )


@router.get("/evaluation-policy-comparison", response_model=EvaluationPolicyComparisonReport | None)
async def evaluation_policy_comparison(
    strategy_id: str = Query(..., alias="strategyId"),
    account_id: str | None = Query(default=None, alias="accountId"),
) -> EvaluationPolicyComparisonReport | None:
    """Quantitative Research & Intelligence System, Requirements
    21/22/23/25 (Piece 10) — a real, on-demand Monte Carlo comparison of
    four named evaluation-stage risk policies for this strategy. None
    when the strategy has no completed simulation runs yet — nothing
    real to bootstrap from (same honesty boundary as GET /model-
    validation and .../monte-carlo). Read-only and computed fresh every
    call — nothing here is persisted or auto-generated in the background
    sim tick, unlike StrategyMonteCarloResult; see app/
    evaluation_simulator.py's own module docstring for why this piece
    stays a real, on-demand research computation rather than a second
    autonomous background pipeline."""
    state = await game_state.snapshot()
    strategy = next((s for s in state.strategies if s.id == strategy_id), None)
    if strategy is None:
        raise HTTPException(status_code=404, detail="No strategy found with that id.")
    account = None
    if account_id is not None:
        account = next((a for a in state.accounts if a.id == account_id), None)
        if account is None:
            raise HTTPException(status_code=404, detail=f"No account with id {account_id!r}.")
    return compare_evaluation_policies(strategy, state.simulation_results, account=account, sim_day=state.time.day)
