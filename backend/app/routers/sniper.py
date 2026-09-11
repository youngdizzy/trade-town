"""CEO directive "TradeTown — Memecoin Sniper Agent." Paper-only,
simulated data throughout — see app/memecoin_sniper.py's own module
docstring for the full honesty boundary."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.memecoin_sniper import build_engine_status_read, build_sniper_pnl_history
from app.persistence import persist_modules
from app.schemas import (
    SniperCandidate,
    SniperEngineStatusRead,
    SniperEquitySnapshot,
    SniperEvent,
    SniperLead,
    SniperLesson,
    SniperLiveArmingStatus,
    SniperPnlHistoryPoint,
    SniperPosition,
    SniperRiskState,
    SniperStrategyDefinition,
    SniperStrategyPerformanceSummary,
    SniperTrade,
    SniperWallet,
)
from app.sniper_strategy_performance import compute_sniper_strategy_performance
from app.sniper_strategy_registry import ensure_default_sniper_strategies
from app.state import game_state

router = APIRouter(prefix="/api/sniper", tags=["sniper"])


def _today_start_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _has_active_wallet(wallets: list[SniperWallet]) -> bool:
    return any(w.is_active for w in wallets)


@router.get("/status", response_model=SniperEngineStatusRead)
async def sniper_status() -> SniperEngineStatusRead:
    state = await game_state.snapshot()
    return build_engine_status_read(
        state.sniper_engine_config,
        state.sniper_risk_state,
        state.sniper_positions,
        state.sniper_trade_history,
        today_start_iso=_today_start_iso(),
        has_active_wallet=_has_active_wallet(state.sniper_wallets),
    )


@router.get("/candidates", response_model=list[SniperCandidate])
async def sniper_candidates(limit: int = Query(default=30, ge=1, le=60)) -> list[SniperCandidate]:
    state = await game_state.snapshot()
    return state.sniper_candidates[:limit]


@router.get("/positions", response_model=list[SniperPosition])
async def sniper_positions(open_only: bool = Query(default=False, alias="openOnly")) -> list[SniperPosition]:
    state = await game_state.snapshot()
    if open_only:
        return [p for p in state.sniper_positions if p.status == "open"]
    return state.sniper_positions


@router.get("/trades", response_model=list[SniperTrade])
async def sniper_trades(limit: int = Query(default=100, ge=1, le=500)) -> list[SniperTrade]:
    state = await game_state.snapshot()
    return list(reversed(state.sniper_trade_history))[:limit]


@router.get("/pnl-history", response_model=list[SniperPnlHistoryPoint])
async def sniper_pnl_history() -> list[SniperPnlHistoryPoint]:
    """"Terminal 2.2" directive — the real, oldest-first cumulative
    realized P&L curve, built fresh from the same permanent trade
    journal `/status`'s Performance card reads (see
    build_sniper_pnl_history's own docstring for why this is
    realized-only, not a mark-to-market equity curve)."""
    state = await game_state.snapshot()
    return build_sniper_pnl_history(state.sniper_trade_history)


@router.get("/equity-history", response_model=list[SniperEquitySnapshot])
async def sniper_equity_history(limit: int = Query(default=500, ge=1, le=7_200)) -> list[SniperEquitySnapshot]:
    """"Equity Snapshot Telemetry 1.0" directive — the real, chronological
    (oldest first), already-persisted account-equity history (see
    `SniperEquitySnapshot`'s own docstring). Bounded server-side
    (`limit`, default 500 — a few minutes to over an hour of real time
    depending on how much history exists) so the frontend never has to
    request or render the full 7,200-snapshot cap in one response; the
    most RECENT `limit` snapshots are returned, still oldest-first."""
    state = await game_state.snapshot()
    return state.sniper_equity_history[-limit:]


@router.get("/events", response_model=list[SniperEvent])
async def sniper_events(mint: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=300)) -> list[SniperEvent]:
    """Professional Trading Terminal directive, Part VII — the real,
    persisted event timeline (see SniperEvent's own docstring). Newest
    first; `mint` filters to one token's own history (used by the
    terminal's focused-trade timeline)."""
    state = await game_state.snapshot()
    events = state.sniper_events
    if mint is not None:
        events = [e for e in events if e.mint == mint]
    return list(reversed(events))[:limit]


@router.get("/leads", response_model=list[SniperLead])
async def sniper_leads() -> list[SniperLead]:
    state = await game_state.snapshot()
    return state.sniper_leads


@router.get("/lessons", response_model=list[SniperLesson])
async def sniper_lessons() -> list[SniperLesson]:
    state = await game_state.snapshot()
    return state.sniper_lessons


@router.get("/risk", response_model=SniperRiskState)
async def sniper_risk() -> SniperRiskState:
    state = await game_state.snapshot()
    return state.sniper_risk_state


@router.get("/live-arming", response_model=SniperLiveArmingStatus)
async def sniper_live_arming() -> SniperLiveArmingStatus:
    """Section 23/24 — always honestly `armed: false` in this
    environment. See app/memecoin_sniper.py::evaluate_live_arming()."""
    from app.memecoin_sniper import evaluate_live_arming

    state = await game_state.snapshot()
    return evaluate_live_arming(has_active_wallet=_has_active_wallet(state.sniper_wallets))


@router.get("/wallets", response_model=list[SniperWallet])
async def sniper_wallets() -> list[SniperWallet]:
    """"Terminal 2.1" directive, Phase 5 — real wallet METADATA only. See
    `SniperWallet`'s own docstring for why no secret ever appears here."""
    state = await game_state.snapshot()
    return state.sniper_wallets


class AddSniperWalletRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    label: str
    public_address: str = Field(alias="publicAddress")
    network: str = "solana-mainnet"


@router.post("/wallets", response_model=SniperWallet)
async def add_sniper_wallet(payload: AddSniperWalletRequest) -> SniperWallet:
    state, wallet, error = await game_state.add_sniper_wallet(label=payload.label, public_address=payload.public_address, network=payload.network)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    assert wallet is not None
    return wallet


@router.delete("/wallets/{wallet_id}")
async def remove_sniper_wallet(wallet_id: str) -> dict[str, bool]:
    state, error = await game_state.remove_sniper_wallet(wallet_id)
    if error is not None:
        raise HTTPException(status_code=404, detail=error)
    persist_modules(state)
    return {"removed": True}


@router.post("/wallets/{wallet_id}/activate", response_model=list[SniperWallet])
async def activate_sniper_wallet(wallet_id: str) -> list[SniperWallet]:
    state, error = await game_state.set_active_sniper_wallet(wallet_id)
    if error is not None:
        raise HTTPException(status_code=404, detail=error)
    persist_modules(state)
    return state.sniper_wallets


@router.get("/strategies", response_model=list[SniperStrategyDefinition])
async def sniper_strategies() -> list[SniperStrategyDefinition]:
    """CEO directive "TradeTown — Sniper Strategy Engine + Registry
    1.0," generalized by "Sniper Multi-Strategy Dispatch Proof 1.0" —
    the real, persisted strategy registry (see
    `SniperStrategyDefinition`'s own docstring).
    `ensure_default_sniper_strategies()` is the same self-heal/back-
    fill read `app/nexus.py::tick()`/`GameState.set_sniper_strategy_
    status()` already use, so a save that predates the registry
    entirely, or that predates just the newer default strategy, never
    under-reports what's really registered here either."""
    state = await game_state.snapshot()
    return ensure_default_sniper_strategies(state.sniper_strategies)


@router.get("/strategy-performance", response_model=SniperStrategyPerformanceSummary)
async def sniper_strategy_performance() -> SniperStrategyPerformanceSummary:
    """CEO directive "TradeTown — Sniper Per-Strategy Performance
    Observability 1.0" — read-only. Pure aggregation
    (`app/sniper_strategy_performance.py::compute_sniper_strategy_
    performance()`) over the existing, already-persisted `sniper_
    trade_history` journal, grouped by each trade's own historical
    `strategy_id` — never a second trade ledger, never a validation or
    ranking verdict. GET only; this endpoint cannot change strategy
    selection, enable/disable state, risk, firewall behavior, or
    Emergency Stop."""
    state = await game_state.snapshot()
    return compute_sniper_strategy_performance(state.sniper_trade_history, ensure_default_sniper_strategies(state.sniper_strategies))


class SetSniperStrategyStatusRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str


@router.post("/strategies/{strategy_id}/status", response_model=list[SniperStrategyDefinition])
async def set_sniper_strategy_status(strategy_id: str, payload: SetSniperStrategyStatusRequest) -> list[SniperStrategyDefinition]:
    """The CEO's real enable/disable control. DISABLED stops new
    discovery/entries under this strategy exactly like the global
    Emergency Stop does (see `app/memecoin_sniper.py::
    tick_sniper_engine()`'s own docstring) — it never deletes the
    strategy or affects any already-open position."""
    state, error = await game_state.set_sniper_strategy_status(strategy_id, payload.status)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return ensure_default_sniper_strategies(state.sniper_strategies)


class UpdateSniperEngineRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str | None = None
    mode: str | None = None
    turbo: bool | None = None
    # Regression: this field had no Field(alias=...), unlike its
    # response-side counterpart (SniperEngineConfig.copy_trading_enabled
    # already has alias="copyTradingEnabled") — the real frontend sends
    # {"copyTradingEnabled": ...} (see SniperApp.tsx's toggle()), which
    # never bound to this field, so update_sniper_engine_config()'s
    # `if copy_trading_enabled is not None` branch never fired and the
    # Quick Controls "Copy ON/OFF" button silently did nothing.
    copy_trading_enabled: bool | None = Field(default=None, alias="copyTradingEnabled")


@router.post("/engine", response_model=SniperEngineStatusRead)
async def update_sniper_engine(payload: UpdateSniperEngineRequest) -> SniperEngineStatusRead:
    """The CEO's real engine control surface (start/stop/pause, turbo,
    copy-trading toggle). `mode="live"` is always rejected — see
    `GameState.update_sniper_engine_config()`'s own docstring for why."""
    state, error = await game_state.update_sniper_engine_config(
        status=payload.status, mode=payload.mode, turbo=payload.turbo, copy_trading_enabled=payload.copy_trading_enabled
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return build_engine_status_read(
        state.sniper_engine_config,
        state.sniper_risk_state,
        state.sniper_positions,
        state.sniper_trade_history,
        today_start_iso=_today_start_iso(),
        has_active_wallet=_has_active_wallet(state.sniper_wallets),
    )


@router.post("/positions/{position_id}/close", response_model=SniperTrade)
async def close_sniper_position(position_id: str) -> SniperTrade:
    """Section 18's manual exit path — closes at the position's own
    real, already-simulated current price."""
    state, trade, error = await game_state.close_sniper_position(position_id, reason="manual_exit")
    if error is not None:
        raise HTTPException(status_code=404, detail=error)
    persist_modules(state)
    assert trade is not None
    return trade
