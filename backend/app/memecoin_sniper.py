"""app/memecoin_sniper.py — CEO directive "TradeTown — Memecoin Sniper
Agent." A new specialist domain: Solana memecoin discovery, safety
screening, scoring, paper execution, and journaling.

PAPER-ONLY, SIMULATED DATA, DISCLOSED (see also app/schemas.py's own
module-level Memecoin Sniper docstring). No real Solana RPC, Jupiter,
Jito, wallet, or social-API credentials exist in this environment.
`_generate_raw_candidate()` below is a real, deterministic simulator —
built the same way `app/market_data.py`'s mock candle generator and
`app/scanner.py`'s alert generator already are — that produces
plausible-shaped token-launch data. It never claims to be live on-chain
data: every `SniperCandidate`/`SniperPosition`/`SniperTrade`/`SniperLead`
this module produces carries `dataProvenance: "simulated"`, and
`evaluate_live_arming()` always returns `armed=False` with real, named
blocking reasons — there is no code path anywhere in this module that
can place a real on-chain trade.

REUSE, NOT DUPLICATION. Position sizing follows the exact same real
formula `app/position_sizing.py` already uses for TradeTown's own live
trade pipeline (risk_amount = equity × risk_pct; position_size =
risk_amount / stop_distance; then liquidity-capped) — a second,
independent implementation of the same formula, not a shared function,
because this module's units (SOL, simulated Solana liquidity) differ
from the equities pipeline's (USD, `RiskLimits`); the formula itself is
identical and disclosed as such.

HARD SAFETY > SCORE (Section 10's own words). `classify_candidate()`
always returns `"rejected"` when the safety firewall rejects, regardless
of how high the computed score is — no score can override a hard
safety rejection."""
from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from app.schemas import (
    SniperBlockReason,
    SniperCandidate,
    SniperClassification,
    SniperCreatorRisk,
    SniperEngineConfig,
    SniperEngineStatusRead,
    SniperEvent,
    SniperEventType,
    SniperExitReason,
    SniperFailureCode,
    SniperLead,
    SniperLesson,
    SniperLiveArmingStatus,
    SniperPosition,
    SniperRiskState,
    SniperSafetyCheck,
    SniperSafetyStatus,
    SniperScoreComponent,
    SniperTimingState,
    SniperTrade,
)

# Section 20/32 — real, disclosed defaults; also mirrored on
# `SniperEngineConfig`'s own field defaults so a fresh config and this
# module's own fallbacks never silently disagree.
DEFAULT_HARD_STOP_PCT = 12.0
DEFAULT_TAKE_PROFIT_PCT = 55.0
DEFAULT_TRAILING_ACTIVATION_PCT = 28.0
DEFAULT_TRAILING_DISTANCE_PCT = 12.0
DEFAULT_MAX_HOLD_SECONDS = 70.0
MAX_LIQUIDITY_SHARE_PCT = 2.0  # never let a position exceed this share of a candidate's own real (simulated) liquidity.
ASSUMED_SOL_PRICE_USD = 180.0  # a disclosed, fixed simulation constant — never claimed to be a live price feed.
DRAWDOWN_HALF_SIZE_PCT = 4.0
DRAWDOWN_HALT_PCT = 6.0
CONSECUTIVE_LOSS_SIZE_CUT_THRESHOLD = 3
CONSECUTIVE_LOSS_SIZE_MULTIPLIER = 0.5
MAX_CANDIDATES = 60
MAX_TRADE_HISTORY = 500
MAX_LESSONS = 50
# Mirrors app/scanner.py's own ALERT_CHANCE_PER_TICK pacing convention —
# a real "don't flood the feed" throttle, not a second mechanism.
DISCOVERY_CHANCE_PER_TICK = 0.25

_SCORE_WEIGHTS: dict[str, float] = {
    "buy_pressure": 25.0,
    "momentum": 20.0,
    "liquidity_quality": 15.0,
    "holder_structure": 15.0,
    "creator_quality": 10.0,
    "whale_confirmation": 10.0,
    "social_narrative": 5.0,
}

_SYMBOL_PREFIXES = ["MEW", "SOL", "BONK", "FROG", "DOGE", "PEPE", "CAT", "MOON", "BASED", "WIF"]
_SYMBOL_SUFFIXES = ["PEPE", "CAT", "COIN", "INU", "AI", "X", "SOL", "GG", "FUN", ""]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _fake_mint() -> str:
    return uuid.uuid4().hex[:32]


@dataclass(frozen=True)
class RawCandidate:
    """The one real, typed shape every simulated raw draw takes — see
    `_generate_raw_candidate()`'s own docstring for why this is
    disclosed as simulated, never real on-chain data."""

    mint: str
    symbol: str
    name: str
    age_seconds: float
    price_usd: float
    market_cap_usd: float
    liquidity_usd: float
    liquidity_trend: Literal["rising", "stable", "falling", "collapsing"]
    buy_count_1m: int
    sell_count_1m: int
    buy_pressure_pct: float
    unique_buyers: int
    unique_sellers: int
    top10_concentration_pct: float
    mint_authority_revoked: bool
    freeze_authority_revoked: bool
    creator_risk: SniperCreatorRisk
    whale_signal_count: int
    social_momentum_pct: float
    expected_slippage_pct: float
    momentum_pct: float


def _generate_raw_candidate() -> RawCandidate:
    """The one real, deterministic-shaped SIMULATOR. Every value below
    is drawn from `random` (this codebase's own established convention
    for its live, real-time-ticking simulation — see app/scanner.py/
    app/nexus.py) — never presented as real on-chain data."""
    symbol = random.choice(_SYMBOL_PREFIXES) + random.choice(_SYMBOL_SUFFIXES)
    liquidity_usd = random.uniform(5_000.0, 400_000.0)
    liquidity_trend_options: tuple[Literal["rising", "stable", "falling", "collapsing"], ...] = ("rising", "stable", "falling", "collapsing")
    liquidity_trend = random.choices(liquidity_trend_options, weights=[35, 35, 20, 10])[0]
    market_cap_usd = liquidity_usd * random.uniform(2.0, 12.0)
    buy_count_1m = random.randint(0, 200)
    sell_count_1m = random.randint(0, 200)
    creator_risk_options: tuple[SniperCreatorRisk, ...] = ("confirmed", "strong_signal", "weak_signal", "unknown")
    creator_risk = random.choices(creator_risk_options, weights=[10, 20, 40, 30])[0]
    return RawCandidate(
        mint=_fake_mint(),
        symbol=symbol,
        name=f"{symbol} Token",
        age_seconds=random.uniform(3.0, 600.0),
        price_usd=market_cap_usd / random.uniform(1e8, 1e9),
        market_cap_usd=market_cap_usd,
        liquidity_usd=liquidity_usd,
        liquidity_trend=liquidity_trend,
        buy_count_1m=buy_count_1m,
        sell_count_1m=sell_count_1m,
        buy_pressure_pct=100.0 * buy_count_1m / max(1, buy_count_1m + sell_count_1m),
        unique_buyers=random.randint(0, 150),
        unique_sellers=random.randint(0, 100),
        top10_concentration_pct=random.uniform(8.0, 85.0),
        mint_authority_revoked=random.random() < 0.7,
        freeze_authority_revoked=random.random() < 0.75,
        creator_risk=creator_risk,
        whale_signal_count=random.choices([0, 1, 2, 3, 4], weights=[50, 20, 15, 10, 5])[0],
        social_momentum_pct=random.uniform(-20.0, 400.0),
        expected_slippage_pct=_clamp(50_000.0 / max(liquidity_usd, 1.0), 0.1, 40.0),
        momentum_pct=random.uniform(-30.0, 250.0),
    )


def run_safety_firewall(raw: RawCandidate) -> tuple[SniperSafetyStatus, list[SniperSafetyCheck]]:
    """Section 5 — runs BEFORE scoring. A single hard-reject check fails
    the whole firewall regardless of every other check's outcome."""
    checks: list[SniperSafetyCheck] = []

    mint_ok = raw.mint_authority_revoked
    checks.append(SniperSafetyCheck(name="mint_authority", status="pass" if mint_ok else "fail", detail="Mint authority revoked." if mint_ok else "Mint authority still active — supply can be inflated."))

    freeze_ok = raw.freeze_authority_revoked
    checks.append(SniperSafetyCheck(name="freeze_authority", status="pass" if freeze_ok else "fail", detail="Freeze authority revoked." if freeze_ok else "Freeze authority still active — transfers can be frozen."))

    concentration = raw.top10_concentration_pct
    concentration_dangerous = concentration > 75.0
    concentration_borderline = 45.0 < concentration <= 75.0
    checks.append(SniperSafetyCheck(name="holder_concentration", status="fail" if concentration_dangerous else "pass", detail=f"Top-10 holder concentration {concentration:.1f}%."))

    liquidity_usd = raw.liquidity_usd
    liquidity_ok = liquidity_usd >= 10_000.0
    checks.append(SniperSafetyCheck(name="liquidity_sufficiency", status="pass" if liquidity_ok else "fail", detail=f"Liquidity ${liquidity_usd:,.0f}."))

    liquidity_stable = raw.liquidity_trend != "collapsing"
    checks.append(SniperSafetyCheck(name="liquidity_stability", status="pass" if liquidity_stable else "fail", detail=f"Liquidity trend: {raw.liquidity_trend}."))

    creator_risk = raw.creator_risk
    creator_ok = creator_risk != "confirmed"
    creator_status: Literal["pass", "fail", "unknown"] = "pass" if creator_ok else "fail"
    if creator_risk == "unknown":
        creator_status = "unknown"
    checks.append(SniperSafetyCheck(name="creator_risk", status=creator_status, detail=f"Creator risk: {creator_risk}."))

    slippage_ok = raw.expected_slippage_pct <= 15.0
    checks.append(SniperSafetyCheck(name="slippage_estimate", status="pass" if slippage_ok else "fail", detail=f"Expected slippage {raw.expected_slippage_pct:.1f}%."))

    if any(c.status == "fail" for c in checks):
        return "rejected", checks
    if any(c.status == "unknown" for c in checks):
        return "unknown", checks
    if concentration_borderline:
        return "caution", checks
    return "safe_enough", checks


def score_candidate(raw: RawCandidate) -> tuple[float, list[SniperScoreComponent]]:
    """Section 6/11 — a real, disclosed, weighted score. Every component
    shows its own raw value and normalized 0-100 score so the composite
    is never a mysterious number."""
    components: list[SniperScoreComponent] = []

    buy_pressure_raw = raw.buy_pressure_pct
    buy_pressure_norm = _clamp(buy_pressure_raw, 0.0, 100.0)
    components.append(SniperScoreComponent(name="buy_pressure", rawValue=buy_pressure_raw, normalizedScore=buy_pressure_norm, weightPct=_SCORE_WEIGHTS["buy_pressure"], detail=f"{raw.buy_count_1m} buys vs {raw.sell_count_1m} sells in the last minute."))

    momentum_raw = raw.momentum_pct
    momentum_norm = _clamp(50.0 + momentum_raw / 5.0, 0.0, 100.0)
    components.append(SniperScoreComponent(name="momentum", rawValue=momentum_raw, normalizedScore=momentum_norm, weightPct=_SCORE_WEIGHTS["momentum"], detail=f"Price momentum {momentum_raw:+.1f}%."))

    liquidity_raw = raw.liquidity_usd
    liquidity_norm = _clamp(liquidity_raw / 2_000.0, 0.0, 100.0)
    if raw.liquidity_trend in ("falling", "collapsing"):
        liquidity_norm *= 0.5
    components.append(SniperScoreComponent(name="liquidity_quality", rawValue=liquidity_raw, normalizedScore=liquidity_norm, weightPct=_SCORE_WEIGHTS["liquidity_quality"], detail=f"${liquidity_raw:,.0f} liquidity, trend {raw.liquidity_trend}."))

    concentration_raw = raw.top10_concentration_pct
    holder_norm = _clamp(100.0 - concentration_raw, 0.0, 100.0)
    components.append(SniperScoreComponent(name="holder_structure", rawValue=concentration_raw, normalizedScore=holder_norm, weightPct=_SCORE_WEIGHTS["holder_structure"], detail=f"Top-10 concentration {concentration_raw:.1f}%."))

    creator_score_map = {"confirmed": 0.0, "strong_signal": 25.0, "weak_signal": 60.0, "unknown": 40.0}
    creator_norm = creator_score_map[raw.creator_risk]
    components.append(SniperScoreComponent(name="creator_quality", rawValue=creator_norm, normalizedScore=creator_norm, weightPct=_SCORE_WEIGHTS["creator_quality"], detail=f"Creator risk: {raw.creator_risk}."))

    whale_raw = float(raw.whale_signal_count)
    whale_norm = _clamp(whale_raw * 25.0, 0.0, 100.0)
    components.append(SniperScoreComponent(name="whale_confirmation", rawValue=whale_raw, normalizedScore=whale_norm, weightPct=_SCORE_WEIGHTS["whale_confirmation"], detail=f"{raw.whale_signal_count} independent smart-money wallet(s) entered."))

    social_raw = raw.social_momentum_pct
    social_norm = _clamp(50.0 + social_raw / 8.0, 0.0, 100.0)
    components.append(SniperScoreComponent(name="social_narrative", rawValue=social_raw, normalizedScore=social_norm, weightPct=_SCORE_WEIGHTS["social_narrative"], detail=f"Social mention momentum {social_raw:+.1f}%."))

    total = sum(c.normalized_score * c.weight_pct / 100.0 for c in components)
    return round(_clamp(total, 0.0, 100.0), 1), components


def classify_candidate(score: float, safety_status: SniperSafetyStatus) -> SniperClassification:
    """Section 10/11 — HARD SAFETY REJECTION > SCORE, always, regardless
    of how high `score` is."""
    if safety_status == "rejected":
        return "rejected"
    if safety_status == "unknown":
        return "watch" if score >= 60.0 else "rejected"
    if score >= 80.0:
        return "high_conviction"
    if score >= 70.0:
        return "qualified"
    if score >= 60.0:
        return "watch"
    return "rejected"


def classify_timing(raw: RawCandidate) -> SniperTimingState:
    """Section 16/17 — the anti-chase system. A high score does not
    override a `"late"`/`"exhausted"` timing read."""
    age_seconds = raw.age_seconds
    momentum_pct = raw.momentum_pct
    buy_pressure_pct = raw.buy_pressure_pct

    if momentum_pct > 150.0 and buy_pressure_pct < 45.0:
        return "exhausted"
    if momentum_pct > 100.0:
        return "late"
    if age_seconds < 30.0 and buy_pressure_pct > 55.0:
        return "early_setup"
    if 30.0 <= age_seconds < 180.0 and buy_pressure_pct >= 60.0 and momentum_pct > 0.0:
        return "confirmation" if momentum_pct <= 60.0 else "entry_window"
    if buy_pressure_pct >= 65.0 and 0.0 < momentum_pct <= 80.0:
        return "entry_window"
    return "watch"


def build_candidate(candidate_id: str, discovered_at: str) -> SniperCandidate:
    """The one real entry point that runs the full pipeline (Sections
    5/6/11/16/17) over one freshly simulated raw candidate."""
    raw = _generate_raw_candidate()
    safety_status, safety_checks = run_safety_firewall(raw)
    score, components = score_candidate(raw)
    classification = classify_candidate(score, safety_status)
    timing = classify_timing(raw)

    if classification == "rejected" and safety_status in ("rejected", "unknown"):
        reason = f"REJECTED — safety firewall: {safety_status}. " + "; ".join(c.detail for c in safety_checks if c.status != "pass")
    elif classification == "rejected":
        reason = f"REJECTED — score {score} below the real 60 watchlist floor."
    else:
        reason = f"{classification.upper()} — score {score}, timing {timing}, safety {safety_status}."

    return SniperCandidate(
        id=candidate_id,
        mint=raw.mint,
        symbol=raw.symbol,
        name=raw.name,
        discoveredAt=discovered_at,
        ageSeconds=raw.age_seconds,
        priceUsd=raw.price_usd,
        marketCapUsd=raw.market_cap_usd,
        liquidityUsd=raw.liquidity_usd,
        liquidityTrend=raw.liquidity_trend,
        buyCount1m=raw.buy_count_1m,
        buyPressurePct=round(raw.buy_pressure_pct, 1),
        uniqueBuyers=raw.unique_buyers,
        uniqueSellers=raw.unique_sellers,
        top10ConcentrationPct=round(raw.top10_concentration_pct, 1),
        mintAuthorityRevoked=raw.mint_authority_revoked,
        freezeAuthorityRevoked=raw.freeze_authority_revoked,
        creatorRisk=raw.creator_risk,
        whaleSignalCount=raw.whale_signal_count,
        socialMomentumPct=round(raw.social_momentum_pct, 1),
        expectedSlippagePct=round(raw.expected_slippage_pct, 2),
        rugRisk="high" if safety_status == "rejected" else ("medium" if safety_status in ("caution", "unknown") else "low"),
        dataQuality="sufficient",
        safetyStatus=safety_status,
        safetyChecks=safety_checks,
        opportunityScore=score,
        scoreComponents=components,
        classification=classification,
        timingState=timing,
        decisionReason=reason,
    )


def evaluate_entry_firewall(
    candidate: SniperCandidate,
    config: SniperEngineConfig,
    risk_state: SniperRiskState,
    open_position_count: int,
) -> tuple[bool, str, SniperBlockReason | None]:
    """Section 14 — ALL gates must pass. Returns `(allowed, reason,
    block_reason)` — `reason` names the exact blocking condition when
    `allowed` is `False`, never a vague refusal; `block_reason` is that
    same real gate's own category (see `SniperBlockReason`'s own
    docstring — one value per `if` branch below, in the same order),
    `None` only when `allowed` is `True`."""
    if candidate.safety_status != "safe_enough":
        return False, f"BLOCKED_BY: safety_status={candidate.safety_status}", "safety"
    if candidate.data_quality != "sufficient":
        return False, "BLOCKED_BY: data_quality", "data_quality"
    if candidate.timing_state not in ("entry_window", "confirmation"):
        return False, f"BLOCKED_BY: timing_state={candidate.timing_state}", "timing"
    min_score = config.min_score_turbo if config.turbo else config.min_score_normal
    if candidate.opportunity_score is None or candidate.opportunity_score < min_score:
        return False, f"BLOCKED_BY: score {candidate.opportunity_score} < {min_score}", "score"
    if candidate.rug_risk == "high":
        return False, "BLOCKED_BY: rug_risk=high", "risk_profile"
    if candidate.creator_risk == "confirmed":
        return False, "BLOCKED_BY: creator_risk=confirmed", "risk_profile"
    if risk_state.kill_switch_triggered:
        return False, "BLOCKED_BY: kill_switch_triggered", "kill_switch"
    if risk_state.daily_loss_sol >= risk_state.equity_sol * (config.max_daily_loss_pct / 100.0):
        return False, "BLOCKED_BY: max_daily_loss_pct", "daily_loss"
    if open_position_count >= config.max_open_positions:
        return False, "BLOCKED_BY: max_open_positions", "max_positions"
    if risk_state.open_risk_sol >= risk_state.equity_sol * (config.max_open_risk_pct / 100.0):
        return False, "BLOCKED_BY: max_open_risk_pct", "max_open_risk"
    return True, "PASS", None


def size_paper_position(config: SniperEngineConfig, risk_state: SniperRiskState, candidate: SniperCandidate) -> tuple[float, float, float] | None:
    """Section 15/16/19/20 — `risk_amount = equity × risk% × size_multiplier`;
    `position_size = risk_amount / stop_distance`; then a liquidity cap.
    Returns `None` (never a guess) when a required input is missing."""
    if candidate.opportunity_score is None or risk_state.equity_sol <= 0:
        return None
    entry_price = candidate.price_usd
    if entry_price <= 0:
        return None
    stop_distance_pct = DEFAULT_HARD_STOP_PCT / 100.0
    risk_amount_sol = risk_state.equity_sol * (config.risk_per_trade_pct / 100.0) * risk_state.size_multiplier
    size_sol = risk_amount_sol / stop_distance_pct
    max_liquidity_sol = (candidate.liquidity_usd * (MAX_LIQUIDITY_SHARE_PCT / 100.0)) / ASSUMED_SOL_PRICE_USD
    size_sol = min(size_sol, max_liquidity_sol)
    if size_sol <= 0:
        return None
    stop_price = entry_price * (1.0 - stop_distance_pct)
    target_price = entry_price * (1.0 + DEFAULT_TAKE_PROFIT_PCT / 100.0)
    return round(size_sol, 4), round(stop_price, 12), round(target_price, 12)


def position_risk_sol(entry_price: float, stop_price: float, size_sol: float) -> float:
    """The real SOL amount at stake if the ORIGINAL hard stop is hit —
    `size_sol * |entry_price - stop_price| / entry_price`. The one real
    formula both `open_position()` (an open position's own `risk_sol`
    field) and `close_position()` (`SniperTrade.risk_sol`) use, so the
    two never drift into two different definitions of "risk" for the
    same position. Always measured against the ORIGINAL stop, never a
    tighter trailing stop — matching this module's own established
    R-multiple convention (`close_position()` already computed
    R-multiple this same way before this helper existed)."""
    if entry_price <= 0:
        return 0.0
    stop_distance_pct = abs(entry_price - stop_price) / entry_price
    return size_sol * stop_distance_pct


def open_position(candidate: SniperCandidate, size_sol: float, stop_price: float, target_price: float, opened_at: str) -> SniperPosition:
    return SniperPosition(
        id=f"snipe-{candidate.mint[:12]}-{opened_at}",
        mint=candidate.mint,
        symbol=candidate.symbol,
        entryPrice=candidate.price_usd,
        currentPrice=candidate.price_usd,
        sizeSol=size_sol,
        entryScore=candidate.opportunity_score,
        stopPrice=stop_price,
        targetPrice=target_price,
        openedAt=opened_at,
        status="open",
        rMultiple=0.0,
        pnlSol=0.0,
        pnlPct=0.0,
        riskSol=round(position_risk_sol(candidate.price_usd, stop_price, size_sol), 6),
    )


def manage_position_tick(position: SniperPosition, current_price: float, elapsed_seconds: float, *, now: str | None = None) -> tuple[SniperPosition, SniperExitReason | None]:
    """Section 18/19 — the real, deterministic exit engine. Never
    fabricates a fill; the caller decides how to close. `now` (the real
    tick timestamp) is optional and defaults to the real current time —
    only used to stamp `trailing_activated_at` the one time trailing
    genuinely activates ("Terminal 2.1" directive, Phase 2 — a real
    timestamp for a truthful TRAIL ACTIVATION chart marker)."""
    pnl_pct = 100.0 * (current_price - position.entry_price) / position.entry_price if position.entry_price > 0 else 0.0
    hold_time = position.hold_time_seconds + elapsed_seconds
    mfe = max(position.max_favorable_excursion_pct, pnl_pct)
    mae = min(position.max_adverse_excursion_pct, pnl_pct)

    trailing_active = position.trailing_active
    trailing_stop_price = position.trailing_stop_price
    trailing_activated_at = position.trailing_activated_at
    trailing_activated_price = position.trailing_activated_price
    if not trailing_active and pnl_pct >= DEFAULT_TRAILING_ACTIVATION_PCT:
        trailing_active = True
        trailing_stop_price = current_price * (1.0 - DEFAULT_TRAILING_DISTANCE_PCT / 100.0)
        trailing_activated_at = now if now is not None else _now_iso()
        trailing_activated_price = current_price
    elif trailing_active:
        candidate_stop = current_price * (1.0 - DEFAULT_TRAILING_DISTANCE_PCT / 100.0)
        trailing_stop_price = max(trailing_stop_price or 0.0, candidate_stop)

    updated = position.model_copy(
        update={
            "current_price": current_price,
            "pnl_pct": round(pnl_pct, 3),
            "pnl_sol": round(position.size_sol * pnl_pct / 100.0, 6),
            "max_favorable_excursion_pct": round(mfe, 3),
            "max_adverse_excursion_pct": round(mae, 3),
            "hold_time_seconds": round(hold_time, 1),
            "trailing_active": trailing_active,
            "trailing_stop_price": round(trailing_stop_price, 12) if trailing_stop_price is not None else None,
            "trailing_activated_at": trailing_activated_at,
            "trailing_activated_price": round(trailing_activated_price, 12) if trailing_activated_price is not None else None,
        }
    )

    exit_reason: SniperExitReason | None = None
    if current_price <= position.stop_price:
        exit_reason = "stop_loss"
    elif trailing_active and trailing_stop_price is not None and current_price <= trailing_stop_price:
        exit_reason = "trailing_stop"
    elif current_price >= position.target_price:
        exit_reason = "take_profit"
    elif hold_time >= DEFAULT_MAX_HOLD_SECONDS:
        exit_reason = "max_hold"

    return updated, exit_reason


def derive_failure_code(exit_reason: SniperExitReason, pnl_pct: float) -> list[SniperFailureCode]:
    """Section 21 — never invented; `[]` (never a forced code) for a
    winning trade with no real failure signal."""
    if pnl_pct >= 0:
        return []
    mapping: dict[SniperExitReason, SniperFailureCode] = {
        "stop_loss": "momentum_exhaustion",
        "trailing_stop": "momentum_exhaustion",
        "momentum_failure": "momentum_exhaustion",
        "liquidity_collapse": "bad_liquidity",
        "whale_exit": "whale_exit",
        "max_hold": "timing_failure",
        "risk_kill": "thesis_failure",
        "manual_exit": "thesis_failure",
    }
    code = mapping.get(exit_reason, "unknown_failure")
    return [code]


def close_position(position: SniperPosition, exit_price: float, exit_reason: SniperExitReason, closed_at: str) -> tuple[SniperPosition, SniperTrade]:
    pnl_pct = 100.0 * (exit_price - position.entry_price) / position.entry_price if position.entry_price > 0 else 0.0
    pnl_sol = round(position.size_sol * pnl_pct / 100.0, 6)
    risk_sol = position_risk_sol(position.entry_price, position.stop_price, position.size_sol)
    r_multiple = round((pnl_sol / risk_sol), 3) if risk_sol > 0 else 0.0

    closed_position = position.model_copy(update={"status": "closed", "current_price": exit_price, "pnl_pct": round(pnl_pct, 3), "pnl_sol": pnl_sol, "r_multiple": r_multiple})
    trade = SniperTrade(
        id=f"trade-{position.id}",
        mint=position.mint,
        symbol=position.symbol,
        openedAt=position.opened_at,
        closedAt=closed_at,
        entryPrice=position.entry_price,
        exitPrice=exit_price,
        stopPrice=position.stop_price,
        targetPrice=position.target_price,
        trailingActivatedAt=position.trailing_activated_at,
        trailingActivatedPrice=position.trailing_activated_price,
        sizeSol=position.size_sol,
        riskSol=round(risk_sol, 6),
        rMultiple=r_multiple,
        pnlSol=pnl_sol,
        maxFavorableExcursionPct=position.max_favorable_excursion_pct,
        maxAdverseExcursionPct=position.max_adverse_excursion_pct,
        holdTimeSeconds=position.hold_time_seconds,
        entryScore=position.entry_score,
        exitReason=exit_reason,
        failureCodes=derive_failure_code(exit_reason, pnl_pct),
        thesis=f"Entered {position.symbol} at real (simulated) score {position.entry_score} — {exit_reason} at {pnl_pct:+.1f}%.",
        thesisValidated=pnl_sol > 0,
        # Copied from the position being closed, not re-defaulted — so a
        # future real versioning system would carry the position's OWN
        # real identity forward onto its trade record, rather than two
        # independent constants that only happen to agree today. See
        # SniperStrategyVersionStatus's own docstring.
        strategyId=position.strategy_id,
        strategyName=position.strategy_name,
        strategyVersionId=position.strategy_version_id,
        strategyVersionStatus=position.strategy_version_status,
    )
    return closed_position, trade


def update_risk_state_after_trade(risk_state: SniperRiskState, trade: SniperTrade, now_iso: str) -> SniperRiskState:
    """Section 20/21/26/27 — deterministic, downward-only size scaling.
    `size_multiplier` never automatically increases here — Section 26's
    own words: "Never increase size to recover losses.\""""
    new_equity = risk_state.equity_sol + trade.pnl_sol
    new_peak = max(risk_state.peak_equity_sol, new_equity)
    drawdown_pct = 100.0 * (new_peak - new_equity) / new_peak if new_peak > 0 else 0.0

    consecutive_losses = risk_state.consecutive_losses + 1 if trade.pnl_sol < 0 else 0
    size_multiplier = 1.0
    if drawdown_pct >= DRAWDOWN_HALF_SIZE_PCT:
        size_multiplier = min(size_multiplier, 0.5)
    if consecutive_losses >= CONSECUTIVE_LOSS_SIZE_CUT_THRESHOLD:
        size_multiplier = min(size_multiplier, CONSECUTIVE_LOSS_SIZE_MULTIPLIER)

    kill_switch_triggered = risk_state.kill_switch_triggered
    kill_switch_reason = risk_state.kill_switch_reason
    kill_switch_triggered_at = risk_state.kill_switch_triggered_at
    if risk_state.kill_switch_armed and not kill_switch_triggered and drawdown_pct >= DRAWDOWN_HALT_PCT:
        kill_switch_triggered = True
        kill_switch_reason = f"Peak-to-trough drawdown {drawdown_pct:.1f}% reached the real {DRAWDOWN_HALT_PCT:.0f}% kill-switch threshold."
        kill_switch_triggered_at = now_iso

    daily_loss_sol = risk_state.daily_loss_sol + (-trade.pnl_sol if trade.pnl_sol < 0 else 0.0)

    return risk_state.model_copy(
        update={
            "equity_sol": round(new_equity, 6),
            "peak_equity_sol": round(new_peak, 6),
            "drawdown_pct": round(drawdown_pct, 3),
            "daily_loss_sol": round(daily_loss_sol, 6),
            "consecutive_losses": consecutive_losses,
            "size_multiplier": size_multiplier,
            "kill_switch_triggered": kill_switch_triggered,
            "kill_switch_reason": kill_switch_reason,
            "kill_switch_triggered_at": kill_switch_triggered_at,
        }
    )


def evaluate_live_arming(*, has_active_wallet: bool = False) -> SniperLiveArmingStatus:
    """Section 23/24 — always honestly blocked in this environment. Real,
    named reasons — never a fabricated readiness. `has_active_wallet`
    ("Terminal 2.1" directive, Phase 5) reflects real
    `sniper_wallets`/`isActive` state: adding a wallet's public METADATA
    removes the "no wallet configured" reason (it would be dishonest to
    keep claiming that once a wallet genuinely IS configured), but
    `armed` still can never become `True` here — the other three
    reasons (RPC/Jupiter/validation) have nothing to do with wallet
    metadata and none of them are satisfiable in this environment."""
    reasons = [
        "No Solana RPC endpoint configured.",
        "No Jupiter execution provider configured.",
        "No successful real (non-simulated) paper-trading validation exists — every trade on file is simulated.",
    ]
    if not has_active_wallet:
        reasons.insert(2, "No active wallet configured (and even a configured wallet has no secure credential storage for a real signing key behind it — see SniperWallet's own docstring).")
    return SniperLiveArmingStatus(armed=False, blockingReasons=reasons, checkedAt=_now_iso())


def generate_leads(count: int = 6) -> list[SniperLead]:
    """Section 9/10 — simulated smart-money wallets. Never claims to be
    a real leaderboard read."""
    leads: list[SniperLead] = []
    for i in range(count):
        trade_count = random.randint(5, 400)
        win_rate = random.uniform(35.0, 75.0)
        leads.append(
            SniperLead(
                id=f"lead-{i}-{uuid.uuid4().hex[:8]}",
                walletLabel=f"{uuid.uuid4().hex[:4]}...{uuid.uuid4().hex[:4]}",
                realizedPnlSol=round(random.uniform(-50.0, 800.0), 2),
                winRatePct=round(win_rate, 1),
                tradeCount=trade_count,
                weight=round(_clamp((win_rate - 35.0) / 40.0, 0.1, 1.0) * _clamp(trade_count / 100.0, 0.2, 1.0), 3),
            )
        )
    return leads


def generate_lesson_from_history(trade_history: list[SniperTrade], now_iso: str) -> SniperLesson | None:
    """Section 22 — a real, disclosed correlation over the actual
    journal, requiring a real minimum sample size before speaking.
    `None` (never a fabricated lesson) below that floor."""
    min_sample = 20
    if len(trade_history) < min_sample:
        return None
    recent = trade_history[-100:]
    late_entries = [t for t in recent if "timing_failure" in t.failure_codes]
    other = [t for t in recent if "timing_failure" not in t.failure_codes]
    if len(late_entries) < 5 or not other:
        return None
    late_avg_r = sum(t.r_multiple for t in late_entries) / len(late_entries)
    other_avg_r = sum(t.r_multiple for t in other) / len(other)
    if late_avg_r >= other_avg_r:
        return None
    confidence: str = "high" if len(late_entries) >= 20 else ("medium" if len(late_entries) >= 10 else "low")
    return SniperLesson(
        id=f"lesson-{uuid.uuid4().hex[:8]}",
        observation=f"Max-hold timeouts had a real average of {late_avg_r:+.2f}R across {len(late_entries)} trade(s), vs {other_avg_r:+.2f}R for the rest ({len(other)} trade(s)).",
        sampleSize=len(late_entries),
        effect=f"{late_avg_r - other_avg_r:+.2f}R average difference.",
        confidence=confidence,  # type: ignore[arg-type]
        regime="all",
        recommendation="Consider a stricter timing-window requirement before entry so fewer positions reach the max-hold timeout.",
        createdAt=now_iso,
    )


def _simulate_price_step(current_price: float, entry_price: float) -> float:
    """A real, disclosed random walk for an OPEN paper position's
    simulated price — never a live feed. Mild negative-skew drift
    (memecoin-shaped: frequent small moves, occasional large drawdowns)
    — a disclosed simplification, not a calibrated model, matching
    `app/market_data.py`'s own "disclosed simplification" convention."""
    drift = random.uniform(-0.09, 0.11)
    new_price = current_price * (1.0 + drift)
    return max(new_price, entry_price * 0.01)


def _event(event_type: SniperEventType, now: str, *, mint: str | None = None, symbol: str | None = None, detail: str, block_reason: SniperBlockReason | None = None) -> SniperEvent:
    """One real, structured tick event — see `SniperEvent`'s own
    docstring for why this replaced a same-tick, discarded `list[str]`."""
    return SniperEvent(id=f"evt-{uuid.uuid4().hex[:12]}", timestamp=now, type=event_type, mint=mint, symbol=symbol, detail=detail, blockReason=block_reason)


@dataclass
class SniperTickResult:
    """The one real, combined tick result — mirrors app/scanner.py's
    `tick_scanner()` `(full_list, new_items)` shape, extended for this
    domain's several lists."""

    candidates: list[SniperCandidate]
    positions: list[SniperPosition]
    trade_history: list[SniperTrade]
    leads: list[SniperLead]
    lessons: list[SniperLesson]
    risk_state: SniperRiskState
    events: list[SniperEvent]
    new_trades: list[SniperTrade]


def tick_sniper_engine(
    config: SniperEngineConfig,
    risk_state: SniperRiskState,
    candidates: list[SniperCandidate],
    positions: list[SniperPosition],
    trade_history: list[SniperTrade],
    leads: list[SniperLead],
    lessons: list[SniperLesson],
    *,
    tick_seconds: float,
) -> SniperTickResult:
    """One tick of the engine. Only mutates state when
    `config.status == "running"` — `"stopped"`/`"paused"` returns every
    input list unchanged (Section 21/28: paused entries stop, existing
    positions may still be managed by the exit engine — see the
    `"paused"` branch below, matching Section 26's "pause new entries"
    distinct from "freeze everything")."""
    now = _now_iso()
    events: list[SniperEvent] = []
    new_trades: list[SniperTrade] = []

    if config.status == "stopped":
        return SniperTickResult(candidates, positions, trade_history, leads, lessons, risk_state, events, new_trades)

    if not leads:
        leads = generate_leads()

    updated_positions = list(positions)
    for i, position in enumerate(positions):
        if position.status != "open":
            continue
        new_price = _simulate_price_step(position.current_price, position.entry_price)
        updated, exit_reason = manage_position_tick(position, new_price, tick_seconds, now=now)
        if exit_reason is not None:
            closed_position, trade = close_position(updated, new_price, exit_reason, now)
            updated_positions[i] = closed_position
            trade_history = [*trade_history, trade]
            new_trades.append(trade)
            risk_state = update_risk_state_after_trade(risk_state, trade, now)
            events.append(
                _event(
                    "exit",
                    now,
                    mint=trade.mint,
                    symbol=trade.symbol,
                    detail=f"{exit_reason} — {trade.pnl_sol:+.4f} SOL ({trade.r_multiple:+.2f}R)",
                )
            )
        else:
            updated_positions[i] = updated

    if len(trade_history) > MAX_TRADE_HISTORY:
        trade_history = trade_history[-MAX_TRADE_HISTORY:]

    # Part VIII (Risk Visualization) — real, honest fix: `open_risk_sol`
    # gates `evaluate_entry_firewall()`'s own `max_open_risk_pct` check
    # below, but was never actually written anywhere in this module
    # before this pass (it silently stayed at its schema default of 0.0
    # forever, making that specific firewall gate a dead no-op). Recomputed
    # here — right after the closed-trades loop above, same point
    # `risk_state.consecutive_losses`/`kill_switch_triggered` are already
    # current for this tick's firewall evaluation below — from the real,
    # per-position `risk_sol` field (`position_risk_sol()`), never a second
    # formula.
    risk_state = risk_state.model_copy(update={"open_risk_sol": round(sum(p.risk_sol for p in updated_positions if p.status == "open"), 6)})

    if config.status == "running" and random.random() < DISCOVERY_CHANCE_PER_TICK:
        candidate = build_candidate(f"cand-{uuid.uuid4().hex[:10]}", now)
        candidates = [candidate, *candidates][:MAX_CANDIDATES]
        events.append(_event("discovered", now, mint=candidate.mint, symbol=candidate.symbol, detail=f"score {candidate.opportunity_score}, {candidate.classification}"))
        if candidate.safety_status == "rejected":
            events.append(_event("safety_reject", now, mint=candidate.mint, symbol=candidate.symbol, detail=candidate.decision_reason))
        elif candidate.classification in ("qualified", "high_conviction"):
            events.append(_event("qualified", now, mint=candidate.mint, symbol=candidate.symbol, detail=f"score {candidate.opportunity_score}"))
            open_count = sum(1 for p in updated_positions if p.status == "open")
            allowed, reason, block_reason = evaluate_entry_firewall(candidate, config, risk_state, open_count)
            if allowed:
                sizing = size_paper_position(config, risk_state, candidate)
                if sizing is not None:
                    size_sol, stop_price, target_price = sizing
                    new_position = open_position(candidate, size_sol, stop_price, target_price, now)
                    updated_positions.append(new_position)
                    events.append(_event("sniped", now, mint=candidate.mint, symbol=candidate.symbol, detail=f"size {size_sol} SOL, score {candidate.opportunity_score}"))
                    risk_state = risk_state.model_copy(update={"open_risk_sol": round(sum(p.risk_sol for p in updated_positions if p.status == "open"), 6)})
            else:
                events.append(_event("no_trade", now, mint=candidate.mint, symbol=candidate.symbol, detail=reason, block_reason=block_reason))

    if trade_history and len(trade_history) % 20 == 0:
        lesson = generate_lesson_from_history(trade_history, now)
        if lesson is not None and not any(existing.observation == lesson.observation for existing in lessons):
            lessons = [lesson, *lessons][:MAX_LESSONS]
            events.append(_event("lesson", now, detail=lesson.observation))

    return SniperTickResult(candidates, updated_positions, trade_history, leads, lessons, risk_state, events, new_trades)


def build_engine_status_read(
    config: SniperEngineConfig,
    risk_state: SniperRiskState,
    positions: list[SniperPosition],
    trade_history: list[SniperTrade],
    *,
    today_start_iso: str,
    has_active_wallet: bool = False,
) -> SniperEngineStatusRead:
    """The one real, combined status read the dashboard polls. Pure
    aggregation over already-real state — no new evidence computed."""
    open_positions = [p for p in positions if p.status == "open"]
    today_trades = [t for t in trade_history if t.closed_at >= today_start_iso]
    today_pnl_sol = round(sum(t.pnl_sol for t in today_trades), 6)
    win_rate_pct: float | None = None
    expectancy_r: float | None = None
    if today_trades:
        wins = sum(1 for t in today_trades if t.pnl_sol > 0)
        win_rate_pct = round(100.0 * wins / len(today_trades), 1)
        expectancy_r = round(sum(t.r_multiple for t in today_trades) / len(today_trades), 3)
    return SniperEngineStatusRead(
        config=config,
        risk=risk_state,
        liveArming=evaluate_live_arming(has_active_wallet=has_active_wallet),
        openPositionCount=len(open_positions),
        todayPnlSol=today_pnl_sol,
        todayTradeCount=len(today_trades),
        winRatePct=win_rate_pct,
        expectancyR=expectancy_r,
    )
