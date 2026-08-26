"""Market data endpoints — the v0.6.2 Market Data Abstraction. Chart data
is deliberately never part of GameSaveState: it's fully regenerable from
the provider on demand, not game progress (see v0.6.2's save-payload-size
fix), so it lives behind its own REST endpoint instead of riding along on
/api/save or the WebSocket state broadcast.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.data_provenance import compute_data_provenance_report
from app.evidence_confluence import assess_evidence_confluence
from app.market_data import TIMEFRAME_ORDER, market_data_provider
from app.regime_reconciliation import compute_regime_reconciliation
from app.schemas import (
    Candle,
    DataProvenanceReport,
    EconomicIntelligenceReport,
    EconomicIntelligenceState,
    EvidenceConfluenceRead,
    RegimeReconciliation,
    SessionRangeRead,
    SessionRegimeEvidenceSummary,
    SymbolTrendRanking,
    TechnicalAnalysisRead,
    TradingSession,
    TrendDefinitionMethod,
    TrendEnsembleReading,
    TrendRegimeBreakdown,
    TrendWeightingMethod,
)
from app.session_evidence import compute_session_regime_evidence
from app.state import game_state
from app.technical_analysis import compute_technical_analysis
from app.technical_patterns import compute_session_range
from app.trend_engine import compute_trend_ensemble, compute_trend_regime_breakdown, rank_symbols_by_trend
from app.watchlist import SYMBOL_CATEGORY

router = APIRouter(prefix="/api/market", tags=["market"])

MIN_LIMIT = 10
MAX_LIMIT = 500


@router.get("/timeframes", response_model=list[str])
async def get_timeframes() -> list[str]:
    """Only the timeframes the currently-configured provider actually
    supports — never a hardcoded list a real provider might not honor."""
    return TIMEFRAME_ORDER


@router.get("/candles", response_model=list[Candle])
async def get_candles(
    symbol: str = Query(..., min_length=1, max_length=16),
    timeframe: str = Query(...),
    limit: int = Query(150, ge=MIN_LIMIT, le=MAX_LIMIT),
) -> list[Candle]:
    if timeframe not in TIMEFRAME_ORDER:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe {timeframe!r}. Supported: {TIMEFRAME_ORDER}")
    try:
        candles = market_data_provider.get_candles(symbol.upper(), timeframe, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return [Candle.model_validate(c.__dict__) for c in candles]


@router.get("/technical-analysis", response_model=TechnicalAnalysisRead)
async def get_technical_analysis(
    symbol: str = Query(..., min_length=1, max_length=16),
    timeframe: str = Query("1h"),
    limit: int = Query(100, ge=MIN_LIMIT, le=MAX_LIMIT),
) -> TechnicalAnalysisRead:
    """CEO directive "Professional Trading Firm — Market-Analysis
    Knowledge + Session Intelligence Expansion," Phases 1-3 — one bundled
    real "technical desk briefing" for a symbol (see
    app/technical_analysis.py). Computed fresh per request over the same
    real (mock) candle series GET /api/market/candles returns; never
    persisted, never wired into any live trading decision."""
    if timeframe not in TIMEFRAME_ORDER:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe {timeframe!r}. Supported: {TIMEFRAME_ORDER}")
    try:
        candles = market_data_provider.get_candles(symbol.upper(), timeframe, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return compute_technical_analysis(symbol.upper(), candles, timeframe)


@router.get("/session-range", response_model=SessionRangeRead)
async def get_session_range(
    symbol: str = Query(..., min_length=1, max_length=16),
    session: TradingSession = Query(...),
    timeframe: str = Query("1h"),
    limit: int = Query(100, ge=MIN_LIMIT, le=MAX_LIMIT),
) -> SessionRangeRead:
    """CEO directive "Professional Trading Firm — Market-Analysis
    Knowledge + Session Intelligence Expansion," Phase 4 — a symbol's
    real high/low and retest status for one trading session, computed
    only from that session's own real candles (see
    app/technical_patterns.py::compute_session_range(), which reuses
    app/market_intelligence.py's existing session-boundary detection)."""
    if timeframe not in TIMEFRAME_ORDER:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe {timeframe!r}. Supported: {TIMEFRAME_ORDER}")
    try:
        candles = market_data_provider.get_candles(symbol.upper(), timeframe, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return compute_session_range(symbol.upper(), candles, session)


@router.get("/evidence-confluence", response_model=EvidenceConfluenceRead)
async def get_evidence_confluence(
    symbol: str = Query(..., min_length=1, max_length=16),
    timeframe: str = Query("1h"),
    limit: int = Query(100, ge=MIN_LIMIT, le=MAX_LIMIT),
) -> EvidenceConfluenceRead:
    """CEO directive "Professional Quant Trading Firm — Quant
    Intelligence + Market Analysis Completion Phase," Phase D — the
    evidence-family confluence layer over raw indicator/pattern signals
    (see app/evidence_confluence.py's module docstring for exactly which
    real signals are grouped into which family and why). Distinct from
    GET /api/executive/confluence, which operates one layer up on the
    six analyst VOTES. Computed fresh per request; never wired into any
    live trading decision."""
    if timeframe not in TIMEFRAME_ORDER:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe {timeframe!r}. Supported: {TIMEFRAME_ORDER}")
    try:
        candles = market_data_provider.get_candles(symbol.upper(), timeframe, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return assess_evidence_confluence(symbol.upper(), candles)


@router.get("/regime-reconciliation", response_model=RegimeReconciliation)
async def get_regime_reconciliation() -> RegimeReconciliation:
    """Design Bible Chapter 65 — reconciles app/market_environment.py's
    real 5-way regime read with app/market_intelligence.py's real 13-way
    read (and its own real Regime Confidence Score) into one CEO-facing
    answer, plus a read-only posture recommendation. Computed fresh per
    request from the current real state — never a second persisted
    copy, and never a write to any RiskLimits field (see
    app/regime_reconciliation.py's own module docstring)."""
    state = await game_state.snapshot()
    return compute_regime_reconciliation(state.market_environment, state.market_intelligence)


@router.get("/session-evidence", response_model=SessionRegimeEvidenceSummary)
async def get_session_regime_evidence() -> SessionRegimeEvidenceSummary:
    """CEO directive "Session Trading Education & Agent Training" — real
    SESSION x REGIME evidence over this company's own closed trades (see
    app/session_evidence.py). Computed fresh per request from the
    already-persisted Decision Vault — never a second persisted copy,
    never a fabricated statistic for a pairing this company hasn't
    actually traded under yet."""
    state = await game_state.snapshot()
    return compute_session_regime_evidence(state.decision_vault)


@router.get("/data-provenance", response_model=DataProvenanceReport)
async def get_data_provenance() -> DataProvenanceReport:
    """CEO directive "Next Professional Trading Firm Phase," Priority 5
    (see app/data_provenance.py). A whole-codebase audit of which named
    subsystem's data is REAL/SYNTHETIC/SIMULATED/USER_PROVIDED/
    UNAVAILABLE — the live candle check re-runs against the currently-
    configured provider on every request; never a hardcoded assumption."""
    state = await game_state.snapshot()
    return compute_data_provenance_report(state.watchlist, market_data_provider)


@router.get("/economic-intelligence", response_model=EconomicIntelligenceState)
async def get_economic_intelligence() -> EconomicIntelligenceState:
    """Design Bible Chapter 71 — the Economic Intelligence Center's
    always-current cross-signal read (recomputed every tick, already on
    the game state snapshot — never a second copy computed here). See
    app/economic_intelligence.py's module docstring for the full honesty
    boundary: a real synthesis of Market Environment/Market Intelligence/
    Portfolio Intelligence, never a real macro data feed."""
    state = await game_state.snapshot()
    return state.economic_intelligence


@router.get("/economic-intelligence/reports", response_model=list[EconomicIntelligenceReport])
async def get_economic_intelligence_reports() -> list[EconomicIntelligenceReport]:
    """The permanent daily Economic Intelligence Brief history, oldest
    first, capped at MAX_ECONOMIC_INTELLIGENCE_REPORTS."""
    state = await game_state.snapshot()
    return state.economic_intelligence_reports


# CEO directive "AHL-Inspired Systematic Trend & Momentum Research
# Engine" — three new, real, read-only Research Desk endpoints over
# app/trend_engine.py. Same CAGS convention as every other endpoint in
# this file (computed fresh per request, never persisted, never wired
# into any live trading decision) — these are research evidence reads,
# not a trading signal API.
@router.get("/trend-engine", response_model=TrendEnsembleReading)
async def get_trend_engine_reading(
    symbol: str = Query(..., min_length=1, max_length=16),
    timeframe: str = Query("1h"),
    limit: int = Query(200, ge=MIN_LIMIT, le=MAX_LIMIT),
    method: TrendDefinitionMethod = Query("endpoint_slope"),
    weighting: TrendWeightingMethod = Query("equal"),
) -> TrendEnsembleReading:
    """The Fast/Medium/Slow decomposed Multi-Horizon Trend Score for one
    symbol — real, versioned, never collapsed into a single mysterious
    number. See app/trend_engine.py's own module docstring for the full
    "AHL-inspired, not AHL" disclosure and point-in-time-correctness
    discipline."""
    if timeframe not in TIMEFRAME_ORDER:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe {timeframe!r}. Supported: {TIMEFRAME_ORDER}")
    try:
        candles = market_data_provider.get_candles(symbol.upper(), timeframe, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return compute_trend_ensemble(candles, symbol.upper(), timeframe, method=method, weighting=weighting)


@router.get("/trend-engine/cross-sectional", response_model=list[SymbolTrendRanking])
async def get_trend_engine_cross_sectional(
    timeframe: str = Query("1h"),
    limit: int = Query(200, ge=MIN_LIMIT, le=MAX_LIMIT),
    method: TrendDefinitionMethod = Query("endpoint_slope"),
) -> list[SymbolTrendRanking]:
    """Real cross-sectional research evidence: which currently-watched
    symbols show the strongest, most persistent, best risk-adjusted
    trend agreement — sorted by real composite score, descending. Never
    an automatic trade selection; a Research Desk read only."""
    if timeframe not in TIMEFRAME_ORDER:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe {timeframe!r}. Supported: {TIMEFRAME_ORDER}")
    state = await game_state.snapshot()
    symbol_candles = {entry.symbol: market_data_provider.get_candles(entry.symbol, timeframe, limit) for entry in state.watchlist}
    return rank_symbols_by_trend(symbol_candles, SYMBOL_CATEGORY, method=method, timeframe=timeframe)


@router.get("/trend-engine/regime-breakdown", response_model=TrendRegimeBreakdown)
async def get_trend_engine_regime_breakdown(
    symbol: str = Query(..., min_length=1, max_length=16),
    timeframe: str = Query("1h"),
    limit: int = Query(MAX_LIMIT, ge=MIN_LIMIT, le=MAX_LIMIT),
    method: TrendDefinitionMethod = Query("endpoint_slope"),
    forward_bars: int = Query(10, ge=1, le=100),
) -> TrendRegimeBreakdown:
    """Real, historical regime-conditional forward-return evidence for
    this symbol's own strong-signal bars (see app/trend_engine.py's own
    point-in-time-correctness discipline — every bucket only ever used
    data available at its own signal bar)."""
    if timeframe not in TIMEFRAME_ORDER:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe {timeframe!r}. Supported: {TIMEFRAME_ORDER}")
    try:
        candles = market_data_provider.get_candles(symbol.upper(), timeframe, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return compute_trend_regime_breakdown(candles, symbol.upper(), timeframe, method=method, forward_bars=forward_bars)
