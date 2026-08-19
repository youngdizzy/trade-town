"""The Research Sandbox (v0.7 Feature 45). See app/sandbox.py's module
docstring for what this feature extends vs. builds new.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.cost_sensitivity import run_cost_sensitivity
from app.ema_pullback_research import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME, run_ema_pullback_research
from app.evaluation_simulator import compare_evaluation_policies
from app.leakage_audit import audit_definition_for_look_ahead
from app.parameter_sensitivity import run_parameter_sensitivity
from app.persistence import persist_modules
from app.research_experiment import run_research_experiment
from app.quant_research_lab import find_similar_experiments
from app.schemas import (
    AgentId,
    BacktestSession,
    CompiledStrategyBacktestResult,
    CompiledStrategyDefinition,
    CompileStrategyRequest,
    CostSensitivityResult,
    EmaPullbackResearchResult,
    EvaluationPolicyComparisonReport,
    FailedStrategyArchiveEntry,
    LookAheadAuditResult,
    ModelValidationReport,
    ParameterSensitivityResult,
    QuantResearchExperiment,
    QuantResearchExperimentSimilarity,
    ResearchExperimentRecord,
    Strategy,
    StrategyCertification,
    StrategyDossier,
    StrategyExecutiveDashboard,
    StrategyExecutiveReview,
    StrategyFounderApproval,
    StrategyHallOfFameEntry,
    StrategyReview,
    StrategyTournamentResult,
    SubmitQuantResearchExperimentResult,
    SurvivorshipBiasRead,
    TestScenario,
    WalkForwardValidationResult,
)
from app.state import game_state
from app.strategy_compiler import compile_strategy_text, strategy_definition_slug
from app.strategy_engine import DEFAULT_CANDLES_PER_SYMBOL as ENGINE_DEFAULT_CANDLES_PER_SYMBOL
from app.strategy_engine import run_compiled_strategy_backtest
from app.strategy_lab import compute_strategy_certification, compute_strategy_executive_dashboard, generate_strategy_dossier
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


class SubmitQuantResearchExperimentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    definition: CompiledStrategyDefinition
    hypothesis: str
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


@router.get("/survivorship-bias", response_model=SurvivorshipBiasRead)
async def survivorship_bias(symbol: str = Query(..., min_length=1, max_length=16)) -> SurvivorshipBiasRead:
    """Same directive, item 8 — a real, disclosed data-availability
    interface, not a real check (see app/survivorship.py's own module
    docstring for exactly why this codebase has no historical-universe
    data to audit yet)."""
    return check_survivorship_bias(symbol)


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
    equivalent one exists") without blocking the new filing."""
    state, result = await game_state.submit_quant_research_experiment(
        payload.definition,
        hypothesis=payload.hypothesis,
        researcher_agent_id=payload.researcher_agent_id,
        symbols=payload.symbols,
        timeframe=payload.timeframe,
        candles_per_symbol=payload.candles_per_symbol,
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
    return compute_strategy_certification(strategy, state.simulation_results, review, monte_carlo, regime_test, executive_review, founder_approval, health)


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
